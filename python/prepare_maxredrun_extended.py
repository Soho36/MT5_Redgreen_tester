"""Prepare the MaxRedRun check on the extended test period (2026-10-13, user question).

The original test (docs/baseline/maxredrun/RESULTS.md) ran 2020-01-02 -> 2026-07-14 on MNQcontDTBNT20102026_2.
That symbol holds data to 2026-10-01, so 2026-07-15 -> 2026-10-01 was never used by any study.

Protocol, fixed before running:
  EA and settings: the RTL baseline, unchanged. MaxRedRun off, 1 (the frozen train winner) and 3 (adopted).
  Runs: 2020-01-01 -> 2026-10-13 (the data ends 2026-10-01), same symbol.
  Check: trades entered up to 2026-07-14 must reproduce the original test ledgers.
  Reading, as in the original: the cap earns its place if net PF is higher and net DD lower than off on the
  extended test. The new slice alone (about 55 sessions) is shown with a day-resampled interval and decides nothing.

Writes Reports/maxredrun_extended_20261013/. Run with
    .\\venv\\Scripts\\python.exe python\\run_mt5_job.py Reports\\maxredrun_extended_20261013 RTL_runband
"""

import json
import shutil

from prepare_instrument_baseline import EXPERT, SYMBOLS, make_ini
from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / "Reports" / "maxredrun_extended_20261013"
CAPS = (0, 1, 3)
FROM, TO = "2020.01.01", "2026.10.13"


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "mt5" / "experts" / "RR_r_MFE_buy-stop-entry_runband.cs", STUDY / f"{EXPERT}.mq5")
    shutil.copyfile(ROOT / "mt5" / "experts" / "early_closes.mqh", STUDY / "early_closes.mqh")
    jobs = []
    for cap in CAPS:
        tag = f"mrrext_20261013_cap{cap}"
        ini = make_ini(tag, SYMBOLS["mnq"])
        for old, new in (("FromDate=2010.06.07\n", f"FromDate={FROM}\n"), ("ToDate=2026.07.14\n", f"ToDate={TO}\n"),
                         ("MaxRedRun=3\n", f"MaxRedRun={cap}\n")):
            assert ini.count(old) == 1, old
            ini = ini.replace(old, new)
        (STUDY / f"{tag}.ini").write_text(ini, encoding="utf-16")
        jobs.append({"tag": tag, "cap": cap, "outputs": [f"runband_{tag}_1.00.csv", f"runband_{tag}_1.00_stats.csv"]})
    (STUDY / "manifest.json").write_text(json.dumps({"expert": EXPERT, "symbol": SYMBOLS["mnq"], "jobs": jobs}, indent=1),
                                         encoding="utf-8")
    print(f"Wrote {len(jobs)} jobs to {STUDY}")


if __name__ == "__main__":
    main()
