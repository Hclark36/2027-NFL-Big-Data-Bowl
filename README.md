Same 40, Different Burst

NFL Big Data Bowl 2027 research scaffold. No competition data has been downloaded or analyzed yet; no results are claimed.

**Question:** Among players with similar official 40 times, does the timing and shape of acceleration predict NFL movement and performance beyond the 40 and 10-yard split?

Start with wide receivers, subject to sample size and usable tracking. Keep peak acceleration and peak speed distinct. The primary scientific test is incremental predictive value, not simply finding two attractive curves.

## Setup

Run commands from this directory:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/download_data.py
python scripts/audit_data.py --data-dir /absolute/path/printed/by/download --output outputs/data_audit.json
jupyter lab
```

Kaggle may require authentication and acceptance of the competition rules. Keep credentials and raw data out of Git. The download script uses the competition's latest files; record the manifest and date for each analysis version.

## One repository, one notebook per section

| Section | Notebook | Purpose |
|---|---|---|
| 1 | [Data audit](notebooks/01_data_audit.ipynb) | Files, schema, units, joins, coverage, missingness |
| 2 | [40 preparation](notebooks/02_prepare_forties.ipynb) | Attempt boundaries, start alignment, smoothing, quality flags |
| 3 | [Acceleration profiles](notebooks/03_acceleration_profiles.ipynb) | Timing, shape, repeatability, matched 40s |
| 4 | [NFL translation](notebooks/04_nfl_translation.ipynb) | Comparable route segments and football outcomes |
| 5 | [Validation](notebooks/05_validation.ipynb) | Baseline versus added profile features, held-out players |
| 6 | [Report and replay](notebooks/06_report_and_replay.ipynb) | Selected-player replay, report figures, limitations |

Separate repositories would make shared cleaning and reproducibility harder. Link to these notebooks from the writeup; freeze the final version with a Git tag or commit permalink. This folder is ready for a dedicated GitHub repository but has not been published or initialized as a nested Git repository.

## Deliverables

- [Analysis plan](docs/analysis_plan.md): decisions to settle before examining outcomes.
- [Data contract](data/README.md): normalized input for the replay.
- [Replay exporter](scripts/export_replay.py): standalone interactive HTML from audited trajectories.
- [Writeup outline](report/writeup.md): 1,850-word allocation, up to eight combined tables/figures.
- Companion HTML dashboard: build from final results; do not use it as a replacement for Kaggle's required writeup without organizer confirmation.

## Current implementation boundary

The downloader, bounded-memory CSV audit, and normalized-trajectory replay exporter are implemented. Raw competition column mappings, feature extraction, NFL outcomes, and model fitting are deliberately left for schema inspection. The notebooks describe the work and do not fabricate analyses.
