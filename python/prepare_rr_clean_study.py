"""Prepare the clean-data RR check (protocol: docs/RR_CLEAN_DATA_RESULTS.md).

Reuses the compiled calendar-study EA (same source). Writes Reports/rr_clean_20261001/.
Run with
    .\\python\\run_exit_study.ps1 -StudyDir Reports\\rr_clean_20261001 `
        -ExpertName RTL_runband_cal -InstallFolder ClaudeEarlyClose
"""

import json
import shutil

from prepare_calendar_study import STUDY as CAL_STUDY, make_ini
from prepare_flatten_study import TEMPLATE
from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / "Reports" / "rr_clean_20261001"
SYMBOL = "MNQcontDTBNT20102026_2"
RRS = (1.0, 2.0, 2.5, 3.0)


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    for name in ("RTL_runband_cal.mq5", "RTL_runband_cal.ex5", "early_closes.mqh"):
        shutil.copyfile(CAL_STUDY / name, STUDY / name)
    template = TEMPLATE.read_text(encoding="utf-16")
    jobs = []
    for period in ("train", "recent"):
        for rr in RRS:
            tag = f"rrclean_20261001_{period}_{rr:.2f}".replace(".", "p")
            ini = STUDY / f"{tag}.ini"
            ini.write_text(make_ini(template, tag, period, rr, True, symbol=SYMBOL), encoding="utf-16")
            jobs.append({"tag": tag, "period": period, "rr": rr, "ini": str(ini),
                         "csv": f"runband_{tag}_{rr:.2f}.csv", "report": f"{tag}.htm"})
    (STUDY / "manifest.json").write_text(json.dumps({"symbol": SYMBOL, "jobs": jobs}, indent=1), encoding="utf-8")
    print(f"Wrote {len(jobs)} jobs to {STUDY}")


if __name__ == "__main__":
    main()
