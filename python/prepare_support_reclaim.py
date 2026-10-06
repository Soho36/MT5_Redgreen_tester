"""Prepare the Q24 support-reclaim EA and its classify-only tester jobs (protocol: docs/levels/SUPPORT_RECLAIM_PROTOCOL.md).

Copies the Q10 baseline research EA (Reports/trend_rr_20261002/RTL_trend_rr.mq5, tag f50_baseline) and replaces its
red-candle buy-stop entry with mt5/experts/support_reclaim.mqh, called at the open of every eligible bar (flat,
inside a trade window, before the flatten). SROnNewBar runs first on every new bar, before the flatten, position and
window checks, so a breakdown spends its level whether or not the bar is eligible. Jobs: `classify`
(BreakDepthA = 0, primary) and `classify_s1` (0.5), ReclaimMode = 1, no orders; verified by verify_support_reclaim.py.
"""
import json
import re
import shutil

from analyze_breach_reclaim import TAG, TREND
from analyze_price_levels import ROOT, sha256
from prepare_resistance_standalone import INSTALL, rolls_include
from prepare_trendline_breakdown import ENTRY, patch

RUN = ROOT / "Reports" / "levels" / "support_reclaim_20261007"
STEM = "support_reclaim_20261007"
EXPERT = "RTL_support_reclaim"
INCLUDE = ROOT / "mt5" / "experts" / "support_reclaim.mqh"
PROTOCOL = ROOT / "docs" / "levels" / "SUPPORT_RECLAIM_PROTOCOL.md"
COMMON = dict(ReclaimMode=1, MinRiskA=0.25, LevelN=5, LevelSessions=5)
JOBS = {"classify": dict(COMMON, BreakDepthA=0.0), "classify_s1": dict(COMMON, BreakDepthA=0.5)}


def build_source(source):
    source = patch(source, [
        ('#include "trend_rr_ledger.mqh"',
         '#include "trend_rr_ledger.mqh"\n#include "contract_rolls.mqh"\n'
         '#include "support_reclaim.mqh"   // Q24 research entry', 1),
        ("   if(!OpenTrendExports()) return INIT_FAILED;",
         "   if(!SRInit()) return INIT_FAILED;\n   if(!OpenTrendExports()) return INIT_FAILED;", 1),
        ("   FileClose(f);\n   return(0.0);\n}", "   FileClose(f);\n   SRDeinit();\n   return(0.0);\n}", 1),
        ("   lastBar = barOpen;\n",
         "   lastBar = barOpen;\n   SROnNewBar(barOpen);   // Q24: every bar, so a breakdown spends its level either way\n", 1),
    ])
    assert source.count(ENTRY) == 1 and source.rstrip().endswith("}")
    head = source[:source.index(ENTRY)]
    return head + "   // Q24: the support-reclaim buy stop replaces the red-candle buy stop.\n" \
                  "   SROnBar(barOpen);\n}\n"


def main():
    RUN.mkdir(parents=True, exist_ok=True)
    parent = TREND / "RTL_trend_rr.mq5"
    expert = RUN / f"{EXPERT}.mq5"
    files = {expert.name: build_source(parent.read_text(encoding="utf-8-sig")), INCLUDE.name: INCLUDE.read_text(encoding="utf-8"),
             "contract_rolls.mqh": rolls_include()}
    changed = any(not (RUN / n).exists() or (RUN / n).read_text(encoding="utf-8-sig") != text for n, text in files.items())
    if changed and list(RUN.glob("*.completed.json")):
        raise RuntimeError("Preserve completed runs; do not overwrite their source")
    for name, text in files.items():
        (RUN / name).write_text(text, encoding="utf-8-sig" if name == expert.name else "utf-8")
    for name in ("early_closes.mqh", "trend_rr_ledger.mqh", "trend_rr_research.mqh"):
        shutil.copyfile(TREND / name, RUN / name)
    base_ini = (TREND / f"{TAG}.ini").read_text(encoding="utf-16")
    jobs = []
    for job, inputs in JOBS.items():
        tag = f"{STEM}_{job}"
        path = RUN / f"{tag}.ini"
        if not (RUN / f"{tag}.completed.json").exists():
            ini = base_ini
            for key, value in dict(Expert=fr"{INSTALL}\{EXPERT}.ex5", RunTag=tag, Report=f"{tag}.htm").items():
                ini, n = re.subn(rf"(?m)^{key}=.*$", lambda m: f"{key}={value}", ini)
                assert n == 1, key
            ini = ini.replace("[TesterInputs]", "[TesterInputs]\n" + "\n".join(f"{k}={v}" for k, v in inputs.items()), 1)
            path.write_text(ini, encoding="utf-16")
        jobs.append(dict(tag=tag, ini=str(path), inputs=inputs, report=f"{tag}.htm",
                         outputs=[f"{tag}_reclaim.csv", f"{tag}_reclaim_stats.csv", f"runband_{tag}_1.00_stats.csv"]))
    manifest = dict(experiment="Q24 buy the reclaim of a broken swing-low level, classify-only, one-minute OHLC",
                    parent_source=str(parent), parent_sha256=sha256(parent), parent_ini=str(TREND / f"{TAG}.ini"),
                    include_source=str(INCLUDE), include_sha256=sha256(INCLUDE), expert_sha256=sha256(expert),
                    protocol_sha256=sha256(PROTOCOL), jobs=jobs)
    (RUN / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(expert, len(jobs), "jobs")


if __name__ == "__main__":
    main()
