"""Locations independent of the working directory for legacy auto-discovery."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LEGACY_DATA = PROJECT_ROOT / "data" / "legacy"


def legacy_csv_candidates():
    local = sorted(Path.cwd().glob("trade_stats_rr_*.csv"))
    return local or sorted(LEGACY_DATA.glob("trade_stats_rr_*.csv"))
