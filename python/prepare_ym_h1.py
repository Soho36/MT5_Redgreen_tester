"""Prepare RTL on H1 for YM and ES (2026-10-23), matching the NQ H1 run of the 2026-10-15 timeframe study.

User's manual H1 runs on MYM used RTL_signal, which on H1 skips the 23:30 cutoff (no 23:30 bar) and can hold
overnight. This uses the timeframe study's saved RTL_timeframe EA (tick-level cutoff, identical to the installed
one) and its H1 RR 1 INI with symbol, dates, report and run tag changed. NQ H1 is reused from that study.

Writes Reports/ym_h1_20261023/. Run with
    python run_mt5_job.py Reports/ym_h1_20261023 RTL_timeframe
"""
import json
import shutil

from prepare_ym_baselines import FROM, SYMBOLS, TO, make_ini
from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / "Reports" / "ym_h1_20261023"
EXPERT = "RTL_timeframe"
SOURCE = ROOT / "Reports" / "timeframe_baseline_20261015"
TEMPLATE = SOURCE / "tf_20261015_rtl_h1_rr1p0.ini"


def main():
    if (STUDY / "manifest.json").exists():
        raise RuntimeError("Prepared manifest already exists; preserve it")
    STUDY.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE / f"{EXPERT}.mq5", STUDY / f"{EXPERT}.mq5")
    shutil.copyfile(SOURCE / "early_closes.mqh", STUDY / "early_closes.mqh")
    jobs = []
    for inst in ("es", "ym"):
        tag = f"ymh1_20261023_rtl_h1_{inst}"
        ini = make_ini(TEMPLATE, tag, SYMBOLS[inst])
        assert "Period=H1\n" in ini and "MaxRedRun=0\n" in ini and f"FromDate={FROM}\n" in ini and f"ToDate={TO}\n" in ini
        (STUDY / f"{tag}.ini").write_text(ini, encoding="utf-16")
        jobs.append({"tag": tag, "instrument": inst, "symbol": SYMBOLS[inst], "timeframe": "H1",
                     "outputs": [f"runband_{tag}_1.00.csv", f"runband_{tag}_1.00_stats.csv"]})
    (STUDY / "manifest.json").write_text(json.dumps({"expert": EXPERT, "jobs": jobs}, indent=1), encoding="utf-8")
    print(f"Wrote {len(jobs)} jobs to {STUDY}")


if __name__ == "__main__":
    main()
