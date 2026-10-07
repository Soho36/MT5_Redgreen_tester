"""Prepare the RTL baseline on MNQ and MES with identical settings (unseen-instrument check, 2026-10-08).

EA: mt5/experts/RR_r_MFE_buy-stop-entry_runband.cs (the baseline: RR 1.0, MaxRedRun 3, flatten 23:30 with
fallback, early-close calendar, trade window 01:00-23:30). Tester settings copied from the trend-RR baseline
job (Reports/trend_rr_20261002, 2010-06-07 -> 2026-07-14, Model=1 1-minute OHLC, M30).
The early-close calendar was built from NQ; ES has the same CME schedule (checked, docs/reference/DATA_BUILD.md).

Writes Reports/instrument_baseline_20261008/. Run with
    .\\venv\\Scripts\\python.exe python\\run_mt5_job.py Reports\\instrument_baseline_20261008 RTL_runband
"""

import json
import shutil

from prepare_resistance_standalone import INSTALL
from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / "Reports" / "instrument_baseline_20261008"
EXPERT = "RTL_runband"
SYMBOLS = {"mnq": "MNQcontDTBNT20102026_2", "mes": "MEScontDTBNT20102026"}
TEMPLATE = ROOT / "Reports" / "trend_rr_20261002" / "trendrr_20261002_f50_baseline.ini"
DROP = ("AverageNearStopR=", "AverageTarget=", "FastDays=", "BullRR=", "BearRR=")


def make_ini(tag, symbol):
    lines = []
    for line in TEMPLATE.read_text(encoding="utf-16").splitlines():
        if line.startswith(DROP):
            continue
        if line.startswith("Expert="):
            line = f"Expert={INSTALL}\\{EXPERT}.ex5"
        elif line.startswith("Symbol="):
            line = f"Symbol={symbol}"
        elif line.startswith("Report="):
            line = f"Report={tag}.htm"
        elif line.startswith("RunTag="):
            line = f"RunTag={tag}"
        lines.append(line)
    return "\n".join(lines) + "\n"


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "mt5" / "experts" / "RR_r_MFE_buy-stop-entry_runband.cs", STUDY / f"{EXPERT}.mq5")
    shutil.copyfile(ROOT / "mt5" / "experts" / "early_closes.mqh", STUDY / "early_closes.mqh")
    jobs = []
    for key, symbol in SYMBOLS.items():
        tag = f"instbase_20261008_{key}"
        (STUDY / f"{tag}.ini").write_text(make_ini(tag, symbol), encoding="utf-16")
        jobs.append({"tag": tag, "symbol": symbol,
                     "outputs": [f"runband_{tag}_1.00.csv", f"runband_{tag}_1.00_stats.csv"]})
    (STUDY / "manifest.json").write_text(json.dumps({"expert": EXPERT, "jobs": jobs}, indent=1), encoding="utf-8")
    print(f"Wrote {len(jobs)} jobs to {STUDY}")


if __name__ == "__main__":
    main()
