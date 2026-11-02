"""CSV inventory and tracking diagnostics. Raw column mappings must be confirmed."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def inventory_files(root):
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Data directory does not exist: {root}")
    return [{"file": str(p.relative_to(root)), "bytes": p.stat().st_size,
             "is_csv": p.name.lower().endswith((".csv", ".csv.gz"))}
            for p in sorted(root.rglob("*")) if p.is_file()]


def profile_csv(path, chunk_size=100_000, max_rows=10_000):
    """Profile a leading sample, or stream the full file when max_rows=None.

    Numeric-looking values are coerced only for diagnostics, never for analysis.
    Missingness uses pandas' default CSV missing-value interpretation.
    """
    if chunk_size < 1 or (max_rows is not None and max_rows < 1):
        raise ValueError("chunk_size and max_rows must be positive")
    try:
        # Keep raw IDs as strings and leading zeros intact; infer types separately.
        reader = pd.read_csv(path, dtype="string", chunksize=chunk_size, nrows=max_rows)
        columns = list(pd.read_csv(path, nrows=0).columns)
    except pd.errors.EmptyDataError:
        return {"rows_scanned": 0, "scan_scope": "empty file", "columns": []}
    stats = {c: {"column": c, "missing": 0, "numeric_values": 0,
                 "nonfinite_numeric": 0, "numeric_min": None, "numeric_max": None,
                 "examples": []} for c in columns}
    count = 0
    for chunk in reader:
        count += len(chunk)
        for col in columns:
            values = chunk[col]
            item = stats[col]
            item["missing"] += int(values.isna().sum())
            for value in values.dropna().drop_duplicates().head(3):
                if value not in item["examples"] and len(item["examples"]) < 3:
                    item["examples"].append(str(value)[:100])
            numeric = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float, na_value=np.nan)
            parsed = ~np.isnan(numeric)
            finite = np.isfinite(numeric)
            item["numeric_values"] += int(parsed.sum())
            item["nonfinite_numeric"] += int((parsed & ~finite).sum())
            if finite.any():
                low, high = float(numeric[finite].min()), float(numeric[finite].max())
                item["numeric_min"] = low if item["numeric_min"] is None else min(low, item["numeric_min"])
                item["numeric_max"] = high if item["numeric_max"] is None else max(high, item["numeric_max"])
    for item in stats.values():
        present = count - item["missing"]
        item["missing_pct"] = round(100 * item["missing"] / count, 3) if count else None
        item["numeric_parse_pct_nonmissing"] = round(100 * item["numeric_values"] / present, 3) if present else None
        # Numeric parseability is not evidence that an ID should be used as a number.
    return {"rows_scanned": count,
            "scan_scope": "full file" if max_rows is None or count < max_rows else "leading sample (may include entire file)",
            "columns": list(stats.values())}


def audit(root, sample_rows=10_000, chunk_size=100_000):
    root = Path(root).expanduser().resolve()
    entries = inventory_files(root)
    for item in entries:
        if item["is_csv"]:
            try:
                item.update(profile_csv(root / item["file"], chunk_size, sample_rows))
            except (OSError, UnicodeError, pd.errors.ParserError) as exc:
                item["error"] = f"{type(exc).__name__}: {exc}"
    return {"created_utc": datetime.now(timezone.utc).isoformat(), "data_dir": str(root),
            "sample_limit": sample_rows,
            "note": "Leading samples are not representative. Full-file statistics require sample_limit=null. Numeric parsing does not establish units or column semantics.",
            "files": entries}


def tracking_diagnostics(frame, group_cols, time_col, speed_col=None,
                         acceleration_col=None, time_scale=1.0):
    """Attempt summaries for already selected 40-yard records.

    time_scale converts numeric timestamps to seconds (1 for seconds, .001 for
    milliseconds). Datetimes are converted explicitly. Sorting means negative
    acquisition-time jumps cannot be inferred; duplicate timestamps are counted.
    No physical-start alignment or full-40 coverage is inferred here.
    """
    if not group_cols or not np.isfinite(time_scale) or time_scale <= 0:
        raise ValueError("Supply attempt grouping columns and a positive time scale")
    required = list(dict.fromkeys(group_cols + [time_col] +
                    [c for c in [speed_col, acceleration_col] if c]))
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"Columns not found: {sorted(missing)}")
    data = frame[required].copy()
    if pd.api.types.is_datetime64_any_dtype(data[time_col]):
        times = data[time_col].astype('int64').astype(float) / 1e9
        times[data[time_col].isna()] = np.nan
    else:
        times = pd.to_numeric(data[time_col], errors="coerce") * time_scale
    data['_audit_time_s'] = times.to_numpy(dtype=float, na_value=np.nan)
    invalid_time = ~np.isfinite(data['_audit_time_s'])
    null_keys = data[group_cols].isna().any(axis=1)
    excluded = invalid_time | null_keys
    duplicate_time = data.loc[~excluded].duplicated(group_cols + [time_col], keep=False)
    global_quality = {"input_rows": len(data), "invalid_time_rows": int(invalid_time.sum()),
                      "missing_group_key_rows": int(null_keys.sum()), "excluded_rows": int(excluded.sum()),
                      "rows_in_duplicate_timestamps": int(duplicate_time.sum()),
                      "start_coverage": "UNVERIFIED: first observed frame is not necessarily launch",
                      "finish_coverage": "UNVERIFIED: confirm spatial coverage separately",
                      "speed_units": "raw units; verify against data dictionary"}
    for column in [c for c in [speed_col, acceleration_col] if c]:
        data[column] = pd.to_numeric(data[column], errors='coerce').to_numpy(dtype=float, na_value=np.nan)
        bad = ~np.isfinite(data[column])
        global_quality[f"{column}_invalid_rows"] = int(bad.sum())
        data.loc[bad, column] = np.nan
    if speed_col:
        global_quality["negative_speed_rows"] = int((data[speed_col] < 0).sum())
    summaries = []
    for key, rows in data.loc[~excluded].groupby(group_cols, dropna=False, sort=False):
        key = key if isinstance(key, tuple) else (key,)
        rows = rows.sort_values('_audit_time_s', kind='stable')
        t = rows['_audit_time_s'].to_numpy(dtype=float)
        positive_dt = np.diff(np.unique(t))
        median_dt = float(np.median(positive_dt)) if len(positive_dt) else None
        item = dict(zip(group_cols, key))
        item.update(n_frames=len(rows), n_unique_timestamps=len(np.unique(t)),
                    observed_duration_s=float(t[-1]-t[0]), median_step_s=median_dt,
                    estimated_hz=1/median_dt if median_dt else None,
                    max_gap_s=float(positive_dt.max()) if len(positive_dt) else None,
                    gaps_over_1_5x_median=int((positive_dt > 1.5*median_dt).sum()) if median_dt else 0,
                    duplicate_timestamp_rows=int(rows.duplicated('_audit_time_s', keep=False).sum()))
        if speed_col:
            item.update(first_observed_speed=rows[speed_col].iloc[0],
                        last_observed_speed=rows[speed_col].iloc[-1],
                        observed_peak_speed=rows[speed_col].max())
        if acceleration_col:
            item.update(observed_min_acceleration=rows[acceleration_col].min(),
                        observed_max_acceleration=rows[acceleration_col].max())
        summaries.append(item)
    return pd.DataFrame(summaries), global_quality


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/data_audit.json"))
    parser.add_argument("--sample-rows", type=int, default=10_000)
    parser.add_argument("--full", action="store_true", help="Stream every CSV row; can take several minutes")
    args = parser.parse_args()
    result = audit(args.data_dir, sample_rows=None if args.full else args.sample_rows)
    if not result['files']:
        parser.error('No files found')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(f"Inventoried {len(result['files'])} files: {args.output}")
