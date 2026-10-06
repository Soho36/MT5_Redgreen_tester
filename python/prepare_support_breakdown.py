"""Prepare the Q23 short mirror baseline EA and its tester jobs (protocol: docs/levels/SUPPORT_BREAKDOWN_PROTOCOL.md).

Stage 0: copies the Q10 baseline research EA (Reports/trend_rr_20261002/RTL_trend_rr.mq5, tag f50_baseline), applies
the Q21 short-side patches (python/prepare_trendline_breakdown.py: direction flag, mirrored bar-close exit,
direction-aware ledger, qualified flag and orphan close, the window exit cancelling every order, RiskReward sets
the target in every regime) and replaces the red-candle buy-stop entry with the green-candle sell stop of
mt5/experts/short_mirror.mqh. Inputs are the baseline's (MaxRedRun = 3 bands the green run). One job: `baseline`.
"""
import json
import re
import shutil

from analyze_breach_reclaim import TAG, TREND
from analyze_price_levels import ROOT, sha256
from prepare_resistance_standalone import INSTALL
from prepare_trendline_breakdown import ENTRY, build_ledger, build_research, patch

RUN = ROOT / "Reports" / "levels" / "support_breakdown_20261006"
STEM = "support_breakdown_20261006"
EXPERT = "RTL_short_mirror"
INCLUDE = ROOT / "mt5" / "experts" / "short_mirror.mqh"
PROTOCOL = ROOT / "docs" / "levels" / "SUPPORT_BREAKDOWN_PROTOCOL.md"
JOBS = {"baseline": {}}


def build_source(source):
    source = patch(source, [
        ('#include "trend_rr_ledger.mqh"',
         '#include "trend_rr_ledger.mqh"\n#include "short_mirror.mqh"   // Q23 short mirror entry', 1),
        ("bool   g_initialSet   = false;\n",
         "bool   g_initialSet   = false;\nint    g_dir          = 1;       // Q21/Q23: +1 long, -1 short (set on entry)\n", 1),
        ("int OnInit()\n{", "int OnInit()\n{\n"
         "   if(!MathIsValidNumber(RiskReward) || RiskReward<=0) return INIT_PARAMETERS_INCORRECT;", 1),
        ("   if(!OpenTrendExports()) return INIT_FAILED;",
         "   if(!SMInit()) return INIT_PARAMETERS_INCORRECT;\n   if(!OpenTrendExports()) return INIT_FAILED;", 1),
        ("   FileClose(f);\n   return(0.0);\n}", "   FileClose(f);\n   SMDeinit();\n   return(0.0);\n}", 1),
        ("       FreezeTrendAtEntry();\n", "       FreezeTrendAtEntry();\n"
         "       tr_rr=RiskReward;   // one bar-close target in every regime\n", 1),
        ("\t   if(sl > 0.0 && entry > sl)\n",
         "\t   g_dir = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? 1 : -1);   // Q21/Q23\n"
         "\t   if(sl > 0.0 && g_dir * (entry - sl) > 0.0)\n", 1),
        ("\t\t  g_initialRisk  = entry - sl;\n", "\t\t  g_initialRisk  = g_dir * (entry - sl);\n", 1),
        ("   if(typ != POSITION_TYPE_BUY) return;\n",
         "   if(typ != POSITION_TYPE_BUY) { SMManageShort(vol); return; }   // short side\n", 1),
        ("      Print(\"⏱ Outside trading window → no new entries\");\n      CancelOldBuyStops();",
         "      Print(\"⏱ Outside trading window → no new entries\");\n      CancelAllOrders();   // the sell stop too", 1),
    ])
    assert source.count(ENTRY) == 1 and source.rstrip().endswith("}")
    head = source[:source.index(ENTRY)]
    return head + "   // Q23: the green-candle sell stop (short mirror) replaces the red-candle buy stop.\n" \
                  "   SMOnBar(barOpen);\n}\n"


def main():
    RUN.mkdir(parents=True, exist_ok=True)
    parent = TREND / "RTL_trend_rr.mq5"
    expert = RUN / f"{EXPERT}.mq5"
    files = {expert.name: build_source(parent.read_text(encoding="utf-8-sig")),
             "trend_rr_research.mqh": build_research((TREND / "trend_rr_research.mqh").read_text(encoding="utf-8-sig")),
             "trend_rr_ledger.mqh": build_ledger((TREND / "trend_rr_ledger.mqh").read_text(encoding="utf-8-sig")),
             INCLUDE.name: INCLUDE.read_text(encoding="utf-8")}
    changed = any(not (RUN / n).exists() or (RUN / n).read_text(encoding="utf-8-sig") != text
                  for n, text in files.items())
    if changed and list(RUN.glob("*.completed.json")):
        raise RuntimeError("Preserve completed runs; do not overwrite their source")
    for name, text in files.items():
        (RUN / name).write_text(text, encoding="utf-8-sig" if name == expert.name else "utf-8")
    shutil.copyfile(TREND / "early_closes.mqh", RUN / "early_closes.mqh")
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
            path.write_text(ini, encoding="utf-16")
        outputs = [f"runband_{tag}_1.00.csv", f"runband_{tag}_1.00_stats.csv", f"{tag}_checks.csv",
                   f"{tag}_signals.csv", f"{tag}_short_stats.csv"]
        jobs.append(dict(tag=tag, ini=str(path), inputs=inputs, report=f"{tag}.htm", outputs=outputs))
    manifest = dict(experiment="Q23 stage 0: short mirror baseline (green candle, sell stop at its low), "
                               "full-history one-minute OHLC",
                    parent_source=str(parent), parent_sha256=sha256(parent), parent_ini=str(TREND / f"{TAG}.ini"),
                    include_source=str(INCLUDE), include_sha256=sha256(INCLUDE), expert_sha256=sha256(expert),
                    research_sha256=sha256(RUN / "trend_rr_research.mqh"),
                    ledger_sha256=sha256(RUN / "trend_rr_ledger.mqh"), protocol_sha256=sha256(PROTOCOL), jobs=jobs)
    (RUN / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(expert, len(jobs), "jobs")


if __name__ == "__main__":
    main()
