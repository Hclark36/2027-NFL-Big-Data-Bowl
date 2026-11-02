"""Within-position validation of observed 40-yard profile measurements.

No NFL target is inferred from position or inherited from the archived WR pilot.
"""
import numpy as np
import pandas as pd


def profile_feature_table(peaks, intervals, references, roster, group_columns):
    """Keep every feature status; add an observed-speed reference to peak timing."""
    peak = peaks.merge(references[group_columns + ['reference_time_s', 'reference_status']],
                       on=group_columns, how='left', validate='many_to_one')
    keep = group_columns + ['display_name', 'combine_position', 'nfl_position']
    parts = []
    specs = [
        ('peak_magnitude', 'peak_acceleration_raw_per_s', 'acceleration', 'raw speed units / s'),
        ('peak_time_recording_start_s', 'peak_time_from_recording_start_s', 'timing', 'seconds'),
        ('peak_time_speed3_reference_s', None, 'timing', 'seconds'),
    ]
    for feature, value_column, kind, unit in specs:
        part = peak[keep].copy()
        part['feature'] = feature
        part['metric_kind'] = kind
        part['unit'] = unit
        part['method'] = peak['window_frames'].astype(int).astype(str) + '-frame'
        part['status'] = peak['status']
        if value_column:
            part['value'] = pd.to_numeric(peak[value_column], errors='coerce')
        else:
            part['value'] = peak['peak_time_from_recording_start_s'] - peak['reference_time_s']
            missing = peak['status'].eq('Measured') & ~peak['reference_status'].eq('Measured')
            part.loc[missing, 'status'] = 'No supported speed reference'
        part['peak_boundary'] = peak['peak_location'].ne('Interior')
        part.loc[~part['status'].eq('Measured'), 'value'] = np.nan
        parts.append(part)
    part = intervals[keep].copy()
    part['feature'] = 'speed_interval_' + intervals['speed_band'].str.replace('-to-', '_to_', regex=False) + '_s'
    part['metric_kind'] = 'interval'
    part['unit'] = 'seconds'
    part['method'] = intervals['method']
    part['status'] = intervals['status']
    part['value'] = pd.to_numeric(intervals['interval_s'], errors='coerce')
    part['peak_boundary'] = False  # Not applicable to interval measurements.
    part.loc[~part['status'].eq('Measured'), 'value'] = np.nan
    parts.append(part)
    features = pd.concat(parts, ignore_index=True)
    extra = ['draft_year', 'nfl_id', 'official_forty_hundredths', 'recordings', 'discrepancy_review']
    features = features.merge(roster[extra], on=['draft_year', 'nfl_id'], how='left', validate='many_to_one')
    if features.duplicated(group_columns + ['feature', 'method']).any():
        raise ValueError('Duplicate attempt/feature/method measurements')
    measured = features['status'].eq('Measured')
    if not np.isfinite(features.loc[measured, 'value'].to_numpy(float)).all():
        raise ValueError('A measured feature has an invalid numerical value')
    if features.loc[measured & features['metric_kind'].eq('interval'), 'value'].le(0).any():
        raise ValueError('Measured speed intervals must be positive')
    return features


def pair_features(features, group_columns):
    """One pair per player/feature/method; single-attempt players stay in source."""
    usable = features.loc[features['status'].eq('Measured') & features['recordings'].eq(2)].copy()
    paired = []
    keys = ['combine_position', 'draft_year', 'nfl_id', 'feature', 'method', 'metric_kind', 'unit']
    for key, rows in usable.groupby(keys, dropna=False, sort=False):
        if len(rows) != 2:
            continue
        rows = rows.assign(_order=pd.to_numeric(rows['attempt'], errors='raise')).sort_values(['_order', 'event_id'])
        a, b = rows.iloc[0], rows.iloc[1]
        va, vb = float(a['value']), float(b['value'])
        mean = (va + vb) / 2
        relative_ok = a['metric_kind'] != 'timing' and abs(mean) > 1e-10
        paired.append({
            **dict(zip(keys, key)), 'display_name': a['display_name'],
            'official_forty_hundredths': a['official_forty_hundredths'],
            'event_a': a['event_id'], 'event_b': b['event_id'],
            'attempt_a': a['attempt'], 'attempt_b': b['attempt'],
            'value_a': va, 'value_b': vb, 'difference_b_minus_a': vb-va,
            'absolute_difference': abs(vb-va),
            'absolute_difference_pct': 100*abs(vb-va)/abs(mean) if relative_ok else np.nan,
            'both_peaks_interior': not bool(a['peak_boundary']) and not bool(b['peak_boundary']),
            'discrepancy_review': bool(a['discrepancy_review']) or bool(b['discrepancy_review']),
        })
    return pd.DataFrame(paired)


def summarize_pairs(features, pairs, by_year=False, bootstraps=2000, seed=2026):
    """Within-position ranking and agreement; paired-player bootstrap of median AD.

    Bootstrap preserves observed draft-year counts, conditions on measured pairs,
    and resamples players, never individual attempts or derived feature rows.
    """
    keys = ['combine_position'] + (['draft_year'] if by_year else []) + ['feature', 'method', 'metric_kind', 'unit']
    scaffold = features[keys].drop_duplicates()
    summaries = []
    for key, _ in scaffold.groupby(keys, dropna=False, sort=True):
        meta = dict(zip(keys, key))
        selected = pairs
        for column, value in meta.items():
            if column in selected:
                selected = selected.loc[selected[column].eq(value)]
        scopes = ['All measured pairs'] if meta['metric_kind'] == 'interval' else ['All measured pairs', 'Both peaks interior']
        for scope in scopes:
            rows = selected.loc[selected['both_peaks_interior']] if scope == 'Both peaks interior' and not selected.empty else selected
            n = len(rows)
            row = {**meta, 'scope': scope, 'paired_players': n}
            if n == 0:
                for col in ['pearson', 'spearman', 'mean_difference_b_minus_a', 'median_absolute_difference',
                            'p90_absolute_difference', 'median_absolute_difference_pct',
                            'conditional_median_ad_p025', 'conditional_median_ad_p975']:
                    row[col] = np.nan
            else:
                variable = n >= 3 and rows['value_a'].std() > 1e-12 and rows['value_b'].std() > 1e-12
                row.update(
                    pearson=rows['value_a'].corr(rows['value_b']) if variable else np.nan,
                    spearman=rows['value_a'].corr(rows['value_b'], method='spearman') if variable else np.nan,
                    mean_difference_b_minus_a=rows['difference_b_minus_a'].mean(),
                    median_absolute_difference=rows['absolute_difference'].median(),
                    p90_absolute_difference=rows['absolute_difference'].quantile(.9),
                    median_absolute_difference_pct=(rows['absolute_difference_pct'].median()
                                                    if meta['metric_kind'] != 'timing' else np.nan),
                    conditional_median_ad_p025=np.nan, conditional_median_ad_p975=np.nan,
                )
                if bootstraps and n >= 5:
                    rows = rows.reset_index(drop=True)
                    rng = np.random.default_rng(seed)
                    groups = [g.index.to_numpy() for _, g in rows.groupby('draft_year', sort=True)]
                    sampled = np.concatenate([rng.choice(ids, size=(bootstraps, len(ids)), replace=True) for ids in groups], axis=1)
                    ad = rows['absolute_difference'].to_numpy()
                    medians = np.median(ad[sampled], axis=1)
                    row['conditional_median_ad_p025'] = float(np.quantile(medians, .025))
                    row['conditional_median_ad_p975'] = float(np.quantile(medians, .975))
            summaries.append(row)
    return pd.DataFrame(summaries)


def exact_time_group_spread(features, within_year=False):
    """Descriptive ranges, not tests on overlapping matched pairs."""
    measured = features.loc[features['status'].eq('Measured')].dropna(subset=['official_forty_hundredths']).copy()
    per_player_keys = ['combine_position', 'draft_year', 'nfl_id', 'display_name',
                       'official_forty_hundredths', 'feature', 'method', 'metric_kind', 'unit']
    per_player = measured.groupby(per_player_keys, dropna=False).agg(
        mean_value=('value', 'mean'), measured_attempts=('value', 'size'),
        any_boundary_peak=('peak_boundary', 'any')).reset_index()
    keys = ['combine_position'] + (['draft_year'] if within_year else []) + [
        'official_forty_hundredths', 'feature', 'method', 'metric_kind', 'unit']
    summary = per_player.groupby(keys, dropna=False).agg(
        players=('nfl_id', 'nunique'), draft_years=('draft_year', 'nunique'),
        minimum_player_mean=('mean_value', 'min'), maximum_player_mean=('mean_value', 'max'),
        players_with_one_measured_attempt=('measured_attempts', lambda s: int(s.eq(1).sum())),
        players_with_boundary_peak=('any_boundary_peak', 'sum')).reset_index()
    summary['range_of_player_means'] = summary['maximum_player_mean'] - summary['minimum_player_mean']
    return per_player, summary.loc[summary['players'].ge(2)].reset_index(drop=True)
