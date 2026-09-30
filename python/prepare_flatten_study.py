"""Prepare the flatten-fallback rerun: EA source copy, tester INIs and manifest.

Writes Reports/flatten_fallback_20261001/ (gitignored). Compile the copied
RTL_runband_flatfix.mq5 with MetaEditor, then run
    .\\python\\run_exit_study.ps1 -StudyDir Reports\\flatten_fallback_20261001 `
        -ExpertName RTL_runband_flatfix -InstallFolder ClaudeFlattenFix
Jobs: a fallback-OFF RR1 control (must reproduce the old cap-3 run exactly)
and fallback-ON RR 1.0 / 1.1 / 2.0 / 2.5 in both periods.
"""

import hashlib
import json
import re
import shutil

from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / "Reports" / "flatten_fallback_20261001"
SOURCE = ROOT / "mt5" / "experts" / "RR_r_MFE_buy-stop-entry_runband.cs"
TEMPLATE = ROOT / "Reports" / "exit_thresholds_20260930" / "exit_20260930_recent_close_1p00.ini"
EXPERT = r"ClaudeFlattenFix\RTL_runband_flatfix.ex5"

PERIODS = {"train": ("2015.01.01", "2020.01.01"), "recent": ("2020.01.02", "2026.07.14")}


def make_ini(template, tag, period, rr, fallback):
    start, end = PERIODS[period]
    text = template
    for key, value in (("Expert", EXPERT), ("FromDate", start), ("ToDate", end),
                       ("Report", f"{tag}.htm"), ("RiskReward", f"{rr}"),
                       ("RunTag", tag), ("SnapshotBars", "0")):
        text, n = re.subn(rf"(?m)^{key}=.*$", lambda _: f"{key}={value}", text)
        assert n == 1, key
    text, n = re.subn(r"(?m)^UseFixedTP=.*\r?\n", "", text)
    assert n == 1, "UseFixedTP"
    text, n = re.subn(r"(?m)^(FlattenMinuteEnd=.*)$", rf"\1\r\nFlattenFallback={'true' if fallback else 'false'}", text)
    assert n == 1, "FlattenFallback"
    return text


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE, STUDY / "RTL_runband_flatfix.mq5")
    template = TEMPLATE.read_text(encoding="utf-16")

    jobs = [("recent", 1.0, False)]
    jobs += [(p, rr, True) for p in ("train", "recent") for rr in (1.0, 1.1, 2.0, 2.5)]
    manifest = {"source": str(SOURCE.relative_to(ROOT)),
                "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                "jobs": []}
    for period, rr, fallback in jobs:
        tag = f"flat_20261001_{period}_{'fb' if fallback else 'off'}_{rr:.2f}".replace(".", "p")
        ini = STUDY / f"{tag}.ini"
        ini.write_text(make_ini(template, tag, period, rr, fallback), encoding="utf-16")
        manifest["jobs"].append({"tag": tag, "period": period, "rr": rr, "fallback": fallback,
                                 "ini": str(ini), "csv": f"runband_{tag}_{rr:.2f}.csv",
                                 "report": f"{tag}.htm"})
    (STUDY / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"Wrote {len(jobs)} jobs to {STUDY}")


if __name__ == "__main__":
    main()
