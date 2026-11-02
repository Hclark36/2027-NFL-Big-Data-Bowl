"""Download competition files with Kaggle's configured authentication."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("KAGGLEHUB_CACHE", str(ROOT / "data" / "kagglehub"))

if __name__ == "__main__":
    import kagglehub
    path = kagglehub.competition_download("nfl-big-data-bowl-2027")
    print("Path to competition files:", path)
    print("Next: python scripts/audit_data.py --data-dir", path)
