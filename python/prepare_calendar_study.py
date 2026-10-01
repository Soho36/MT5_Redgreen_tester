"""Prepare the early-close calendar study on the rebuilt symbol MNQcontDTBNT20102026.

Writes Reports/early_close_calendar_20261001/ (gitignored): EA source + include copy,
tester INIs and manifest. Compile RTL_runband_cal.mq5 with MetaEditor, then run
    .\\python\\run_exit_study.ps1 -StudyDir Reports\\early_close_calendar_20261001 `
        -ExpertName RTL_runband_cal -InstallFolder ClaudeEarlyClose
Jobs: calendar-off control for 2016-2026 (must match Reports/newdata_check_20261001),
then calendar off/on x RR 1.0/2.5 x 2016-2019 / 2020-2026.
"""

import hashlib
import json
import re
import shutil

from prepare_flatten_study import TEMPLATE
from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / "Reports" / "early_close_calendar_20261001"
EXPERTS = ROOT / "mt5" / "experts"
SOURCE = EXPERTS / "RR_r_MFE_buy-stop-entry_runband.cs"
EXPERT = r"ClaudeEarlyClose\RTL_runband_cal.ex5"
SYMBOL = "MNQcontDTBNT20102026"
PERIODS = {"full": ("2016.01.01", "2026.07.14"), "train": ("2016.01.01", "2020.01.01"),
           "recent": ("2020.01.02", "2026.07.14")}


def make_ini(template, tag, period, rr, calendar, symbol=SYMBOL):
    start, end = PERIODS[period]
    text = template
    for key, value in (("Expert", EXPERT), ("Symbol", symbol), ("FromDate", start), ("ToDate", end),
                       ("Report", f"{tag}.htm"), ("RiskReward", f"{rr}"), ("RunTag", tag),
                       ("SnapshotBars", "0")):
        text, n = re.subn(rf"(?m)^{key}=.*$", lambda _: f"{key}={value}", text)
        assert n == 1, key
    text, n = re.subn(r"(?m)^UseFixedTP=.*\r?\n", "", text)
    assert n == 1, "UseFixedTP"
    extra = (f"FlattenFallback=true\r\nUseEarlyCloseCalendar={'true' if calendar else 'false'}"
             "\r\nTrailStartR=1.0\r\nTrailDistanceR=0")
    text, n = re.subn(r"(?m)^(FlattenMinuteEnd=.*)$", lambda m: m.group(1) + "\r\n" + extra, text)
    assert n == 1, "inputs"
    return text


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE, STUDY / "RTL_runband_cal.mq5")
    shutil.copyfile(EXPERTS / "early_closes.mqh", STUDY / "early_closes.mqh")
    template = TEMPLATE.read_text(encoding="utf-16")
    jobs = [("full", 1.0, False)]
    jobs += [(p, rr, cal) for p in ("train", "recent") for rr in (1.0, 2.5) for cal in (False, True)]
    manifest = {"source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                "include_sha256": hashlib.sha256((EXPERTS / "early_closes.mqh").read_bytes()).hexdigest(),
                "jobs": []}
    for period, rr, cal in jobs:
        tag = f"cal_20261001_{period}_{'on' if cal else 'off'}_{rr:.2f}".replace(".", "p")
        ini = STUDY / f"{tag}.ini"
        ini.write_text(make_ini(template, tag, period, rr, cal), encoding="utf-16")
        manifest["jobs"].append({"tag": tag, "period": period, "rr": rr, "calendar": cal, "ini": str(ini),
                                 "csv": f"runband_{tag}_{rr:.2f}.csv", "report": f"{tag}.htm"})
    (STUDY / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"Wrote {len(jobs)} jobs to {STUDY}")


if __name__ == "__main__":
    main()
