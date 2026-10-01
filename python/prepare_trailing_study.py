"""Prepare the trailing-stop study: EA source copy, tester INIs and manifest.

Protocol: docs/TRAILING_STOP_RESULTS.md. Writes Reports/trailing_stop_20261001/
(gitignored). Compile the copied RTL_runband_trail.mq5 with MetaEditor, then run
    .\\python\\run_exit_study.ps1 -StudyDir Reports\\trailing_stop_20261001 `
        -ExpertName RTL_runband_trail -InstallFolder ClaudeTrailingStop
Jobs: trailing-off control + TrailDistanceR 0.25 / 0.5 / 1.0 (start 1.0R),
in 2015-2019 and 2020-2026, RR 1.0 with the flatten fallback on.
"""

import hashlib
import json
import re
import shutil

from prepare_flatten_study import PERIODS, TEMPLATE
from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / "Reports" / "trailing_stop_20261001"
SOURCE = ROOT / "mt5" / "experts" / "RR_r_MFE_buy-stop-entry_runband.cs"
EXPERT = r"ClaudeTrailingStop\RTL_runband_trail.ex5"
DISTANCES = (0.0, 0.25, 0.5, 1.0)


def make_ini(template, tag, period, distance):
    start, end = PERIODS[period]
    text = template
    for key, value in (("Expert", EXPERT), ("FromDate", start), ("ToDate", end),
                       ("Report", f"{tag}.htm"), ("RiskReward", "1.0"),
                       ("RunTag", tag), ("SnapshotBars", "0")):
        text, n = re.subn(rf"(?m)^{key}=.*$", lambda _: f"{key}={value}", text)
        assert n == 1, key
    text, n = re.subn(r"(?m)^UseFixedTP=.*\r?\n", "", text)
    assert n == 1, "UseFixedTP"
    extra = f"FlattenFallback=true\r\nTrailStartR=1.0\r\nTrailDistanceR={distance}"
    text, n = re.subn(r"(?m)^(FlattenMinuteEnd=.*)$", lambda m: m.group(1) + "\r\n" + extra, text)
    assert n == 1, "trailing inputs"
    return text


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE, STUDY / "RTL_runband_trail.mq5")
    template = TEMPLATE.read_text(encoding="utf-16")
    manifest = {"source": str(SOURCE.relative_to(ROOT)),
                "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                "jobs": []}
    for period in ("train", "recent"):
        for d in DISTANCES:
            tag = f"trail_20261001_{period}_d{d:.2f}".replace(".", "p")
            ini = STUDY / f"{tag}.ini"
            ini.write_text(make_ini(template, tag, period, d), encoding="utf-16")
            manifest["jobs"].append({"tag": tag, "period": period, "distance": d,
                                     "ini": str(ini), "csv": f"runband_{tag}_1.00.csv",
                                     "report": f"{tag}.htm"})
    (STUDY / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"Wrote {len(manifest['jobs'])} jobs to {STUDY}")


if __name__ == "__main__":
    main()
