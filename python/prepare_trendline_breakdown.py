"""Prepare the Q21 trendline breakdown EA and its classify-only tester jobs
(protocol: docs/trendlines/BREAKDOWN_SHORT_PROTOCOL.md).

Copies the Q10 baseline research EA (Reports/trend_rr_20261002/RTL_trend_rr.mq5, tag f50_baseline) and replaces
its red-candle buy-stop entry with mt5/experts/trendline_breakdown.mqh, called at the open of every eligible bar
(flat, inside a trade window, before the flatten). TBOnNewBar runs first on every new bar, before the flatten,
position and window checks, so a break spends its line whether or not the bar is eligible. Jobs so far: `classify` (BreakDepthA = 0, primary) and
`classify_s1` (BreakDepthA = 0.5), BreakMode = 1, no orders; verified by python/verify_trendline_breakdown.py.
"""
import json
import re
import shutil

from analyze_breach_reclaim import TAG, TREND
from analyze_price_levels import ROOT, sha256
from prepare_resistance_standalone import INSTALL, rolls_include

RUN = ROOT / "Reports" / "trendlines" / "trendline_breakdown_20261006"
STEM = "trendline_breakdown_20261006"
EXPERT = "RTL_trendline_breakdown"
INCLUDE = ROOT / "mt5" / "experts" / "trendline_breakdown.mqh"
PROTOCOL = ROOT / "docs" / "trendlines" / "BREAKDOWN_SHORT_PROTOCOL.md"
COMMON = dict(BreakMode=1, BreakN=5, BreakSessions=5, BreakMinSep=10, BreakMinSlope=0.02)
JOBS = {"classify": dict(COMMON, BreakDepthA=0.0), "classify_s1": dict(COMMON, BreakDepthA=0.5)}
ENTRY = "   // Red candle setup (only if all filters pass)\n"


def build_source(source):
    patches = [
        ('#include "trend_rr_research.mqh"',
         '#include "contract_rolls.mqh"\n#include "trendline_breakdown.mqh"   // Q21 research entry\n'
         '#include "trend_rr_research.mqh"'),
        ("   if(!OpenTrendExports()) return INIT_FAILED;",
         "   if(!TBInit()) return INIT_FAILED;\n   if(!OpenTrendExports()) return INIT_FAILED;"),
        ("   FileClose(f);\n   return(0.0);\n}", "   FileClose(f);\n   TBDeinit();\n   return(0.0);\n}"),
        ("   lastBar = barOpen;\n",
         "   lastBar = barOpen;\n   TBOnNewBar(barOpen);   // Q21: every bar, so a break spends its line either way\n"),
    ]
    for before, after in patches:
        assert source.count(before) == 1, before
        source = source.replace(before, after, 1)
    # The red-candle entry is the tail of OnTick, the last function in the file: replace it whole.
    assert source.count(ENTRY) == 1 and source.rstrip().endswith("}")
    head = source[:source.index(ENTRY)]
    return head + "   // Q21: the rising-trendline breakdown signal replaces the red-candle buy stop.\n" \
                  "   TBOnBar(barOpen);\n}\n"


def main():
    RUN.mkdir(parents=True, exist_ok=True)
    parent = TREND / "RTL_trend_rr.mq5"
    expert = RUN / f"{EXPERT}.mq5"
    source = build_source(parent.read_text(encoding="utf-8-sig"))
    changed = not expert.exists() or expert.read_text(encoding="utf-8-sig") != source or \
        (RUN / INCLUDE.name).read_bytes() != INCLUDE.read_bytes()
    if changed and list(RUN.glob("*.completed.json")):
        raise RuntimeError("Preserve completed runs; do not overwrite their source")
    expert.write_text(source, encoding="utf-8-sig")
    for name in ("early_closes.mqh", "trend_rr_ledger.mqh", "trend_rr_research.mqh"):
        shutil.copyfile(TREND / name, RUN / name)
    shutil.copyfile(INCLUDE, RUN / INCLUDE.name)
    (RUN / "contract_rolls.mqh").write_text(rolls_include(), encoding="utf-8")
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
            ini = ini.replace("[TesterInputs]",
                              "[TesterInputs]\n" + "\n".join(f"{k}={v}" for k, v in inputs.items()), 1)
            path.write_text(ini, encoding="utf-16")
        jobs.append(dict(tag=tag, ini=str(path), inputs=inputs, report=f"{tag}.htm",
                         outputs=[f"{tag}_breakdown.csv", f"{tag}_breakdown_stats.csv",
                                  f"runband_{tag}_1.00_stats.csv"]))
    manifest = dict(experiment="Q21 short the breakdown of a rising trendline, classify-only, one-minute OHLC",
                    parent_source=str(parent), parent_sha256=sha256(parent), parent_ini=str(TREND / f"{TAG}.ini"),
                    include_source=str(INCLUDE), include_sha256=sha256(INCLUDE), expert_sha256=sha256(expert),
                    protocol_sha256=sha256(PROTOCOL), jobs=jobs)
    (RUN / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(expert, len(jobs), "jobs")


if __name__ == "__main__":
    main()
