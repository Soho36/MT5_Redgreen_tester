"""Prepare the time-of-day diagnostic (protocol: docs/TIME_OF_DAY_RESULTS.md).

Baseline (RR 1.0, MaxRedRun 3, calendar on) on the clean symbol with SnapshotBars=1 so
every trade carries its signal time. Writes Reports/time_of_day_20261002/. Run with
    .\\python\\run_exit_study.ps1 -StudyDir Reports\\time_of_day_20261002 `
        -ExpertName RTL_runband_cal -InstallFolder ClaudeEarlyClose
"""

import json
import re
import shutil

from prepare_calendar_study import STUDY as CAL_STUDY, make_ini
from prepare_flatten_study import TEMPLATE
from prepare_rr_clean_study import SYMBOL
from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / "Reports" / "time_of_day_20261002"


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    for name in ("RTL_runband_cal.mq5", "RTL_runband_cal.ex5", "early_closes.mqh"):
        shutil.copyfile(CAL_STUDY / name, STUDY / name)
    template = TEMPLATE.read_text(encoding="utf-16")
    jobs = []
    for period in ("train", "recent"):
        tag = f"tod_20261002_{period}"
        text = make_ini(template, tag, period, 1.0, True, symbol=SYMBOL)
        text, n = re.subn(r"(?m)^SnapshotBars=.*$", "SnapshotBars=1", text)
        assert n == 1
        ini = STUDY / f"{tag}.ini"
        ini.write_text(text, encoding="utf-16")
        jobs.append({"tag": tag, "period": period, "ini": str(ini),
                     "csv": f"runband_{tag}_1.00.csv", "report": f"{tag}.htm"})
    (STUDY / "manifest.json").write_text(json.dumps({"symbol": SYMBOL, "jobs": jobs}, indent=1), encoding="utf-8")
    print(f"Wrote {len(jobs)} jobs to {STUDY}")


if __name__ == "__main__":
    main()
