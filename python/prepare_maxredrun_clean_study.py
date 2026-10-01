"""Prepare the clean-data MaxRedRun train/test (protocol: docs/MAXREDRUN_CLEAN_RESULTS.md).

Step 1 (no argument): 8 training jobs, MaxRedRun 0..7 on 2016-2019.
Step 2 (--test-cap N): adds the frozen winner N and off (0) on 2020-2026.
The runner skips jobs that already completed. Run with
    .\\python\\run_exit_study.ps1 -StudyDir Reports\\maxredrun_clean_20261001 `
        -ExpertName RTL_runband_cal -InstallFolder ClaudeEarlyClose
"""

import argparse
import json
import re
import shutil

from prepare_calendar_study import STUDY as CAL_STUDY, make_ini
from prepare_flatten_study import TEMPLATE
from prepare_rr_clean_study import SYMBOL
from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / "Reports" / "maxredrun_clean_20261001"


def job(template, period, cap):
    tag = f"mrr_clean_20261001_{period}_cap{cap}"
    text = make_ini(template, tag, period, 1.0, True, symbol=SYMBOL)
    text, n = re.subn(r"(?m)^MaxRedRun=.*$", f"MaxRedRun={cap}", text)
    assert n == 1, "MaxRedRun"
    ini = STUDY / f"{tag}.ini"
    ini.write_text(text, encoding="utf-16")
    return {"tag": tag, "period": period, "cap": cap, "ini": str(ini),
            "csv": f"runband_{tag}_1.00.csv", "report": f"{tag}.htm"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-cap", type=int, help="frozen training winner to run on 2020-2026")
    args = ap.parse_args()
    STUDY.mkdir(parents=True, exist_ok=True)
    for name in ("RTL_runband_cal.mq5", "RTL_runband_cal.ex5", "early_closes.mqh"):
        shutil.copyfile(CAL_STUDY / name, STUDY / name)
    template = TEMPLATE.read_text(encoding="utf-16")
    jobs = [job(template, "train", cap) for cap in range(8)]
    if args.test_cap is not None:
        jobs += [job(template, "recent", cap) for cap in sorted({0, args.test_cap})]
    (STUDY / "manifest.json").write_text(json.dumps({"symbol": SYMBOL, "jobs": jobs}, indent=1), encoding="utf-8")
    print(f"Wrote {len(jobs)} jobs to {STUDY}")


if __name__ == "__main__":
    main()
