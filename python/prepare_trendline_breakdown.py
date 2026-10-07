"""Prepare the Q21 trendline breakdown EA and its tester jobs (protocol: docs/setups/trendlines/uptrend-breakdown/q21-breakdown-short/PROTOCOL.md).

Copies the Q10 baseline research EA (Reports/trend_rr_20261002/RTL_trend_rr.mq5, tag f50_baseline) and replaces
its red-candle buy-stop entry with mt5/experts/trendline_breakdown.mqh, called at the open of every eligible bar
(flat, inside a trade window, before the flatten). TBOnNewBar runs first on every new bar, before the flatten,
position and window checks, so a break spends its line whether or not the bar is eligible.

The parent is long-only; these patches add the short side without changing a long trade:
- g_dir (+1 / -1) is set when a position opens; the initial risk is g_dir x (entry - sl);
- ManageOpenPosition hands a short to TBManageShort (buy to cover after a bar closes <= entry - RR x R);
- the target uses RiskReward in every regime (tr_rr = RiskReward; the Q20 audit's BullRR/BearRR bug);
- the ledger computes profit/risk with the position's direction and the stop at entry - g_dir x R, and logs g_dir;
  the qualified flag and the orphan close are direction-aware;
- leaving a trade window cancels every pending order (the sell stop too).

The verified classify-only run lives in Reports/trendlines/trendline_breakdown_20261006/ (verify_trendline_breakdown.py).
This writes Reports/trendlines/trendline_breakdown_runs_20261006/ with `classify` (BreakMode 1 again: a regression
check against that verified log), `primary` (2, BreakDepthA 0), `s1` (2, 0.5), `c1` (3) and `c2` (4).
"""
import json
import re
import shutil

from analyze_breach_reclaim import TAG, TREND
from analyze_price_levels import ROOT, sha256
from prepare_resistance_standalone import INSTALL, rolls_include

RUN = ROOT / "Reports" / "trendlines" / "trendline_breakdown_runs_20261006"
STEM = "trendline_breakdown_runs_20261006"
EXPERT = "RTL_trendline_breakdown"
INCLUDE = ROOT / "mt5" / "experts" / "trendline_breakdown.mqh"
PROTOCOL = ROOT / "docs" / "setups" / "trendlines" / "uptrend-breakdown" / "q21-breakdown-short" / "PROTOCOL.md"
COMMON = dict(BreakN=5, BreakSessions=5, BreakMinSep=10, BreakMinSlope=0.02)
JOBS = {"classify": dict(BreakMode=1, BreakDepthA=0.0), "primary": dict(BreakMode=2, BreakDepthA=0.0),
        "s1": dict(BreakMode=2, BreakDepthA=0.5), "c1": dict(BreakMode=3, BreakDepthA=0.0),
        "c2": dict(BreakMode=4, BreakDepthA=0.0)}
# Exploratory follow-up (user, after the 1R results; plan in BREAKDOWN_SHORT_RESULTS.md): the same runs at a 2R target.
JOBS.update({f"{job}_rr2": dict(JOBS[job], RiskReward=2.0) for job in ("primary", "s1", "c1", "c2")})


def rr_label(inputs):
    return f"{inputs.get('RiskReward', 1.0):.2f}"
ENTRY = "   // Red candle setup (only if all filters pass)\n"


def patch(source, patches):
    for before, after, count in patches:
        assert source.count(before) == count, before
        source = source.replace(before, after)
    return source


def build_source(source):
    source = patch(source, [
        ('#include "trend_rr_ledger.mqh"',
         '#include "trend_rr_ledger.mqh"\n#include "contract_rolls.mqh"\n'
         '#include "trendline_breakdown.mqh"   // Q21 research entry', 1),
        ("bool   g_initialSet   = false;\n",
         "bool   g_initialSet   = false;\nint    g_dir          = 1;       // Q21: +1 long, -1 short (set on entry)\n", 1),
        ("int OnInit()\n{", "int OnInit()\n{\n"
         "   if(!MathIsValidNumber(RiskReward) || RiskReward<=0) return INIT_PARAMETERS_INCORRECT;", 1),
        ("   if(!OpenTrendExports()) return INIT_FAILED;",
         "   if(!TBInit()) return INIT_FAILED;\n   if(!OpenTrendExports()) return INIT_FAILED;", 1),
        ("   FileClose(f);\n   return(0.0);\n}", "   FileClose(f);\n   TBDeinit();\n   return(0.0);\n}", 1),
        ("   lastBar = barOpen;\n",
         "   lastBar = barOpen;\n   TBOnNewBar(barOpen);   // Q21: every bar, so a break spends its line either way\n", 1),
        ("       FreezeTrendAtEntry();\n", "       FreezeTrendAtEntry();\n"
         "       tr_rr=RiskReward;   // Q21: one bar-close target in every regime\n"
         "       TBOnFill();         // Q21 fill log\n", 1),
        ("\t   if(sl > 0.0 && entry > sl)\n",
         "\t   g_dir = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? 1 : -1);   // Q21\n"
         "\t   if(sl > 0.0 && g_dir * (entry - sl) > 0.0)\n", 1),
        ("\t\t  g_initialRisk  = entry - sl;\n", "\t\t  g_initialRisk  = g_dir * (entry - sl);\n", 1),
        ("   if(typ != POSITION_TYPE_BUY) return;\n",
         "   if(typ != POSITION_TYPE_BUY) { TBManageShort(vol); return; }   // Q21 short side\n", 1),
        ("      Print(\"⏱ Outside trading window → no new entries\");\n      CancelOldBuyStops();",
         "      Print(\"⏱ Outside trading window → no new entries\");\n      CancelAllOrders();   // Q21: the sell stop too", 1),
    ])
    # The red-candle entry is the tail of OnTick, the last function in the file: replace it whole.
    assert source.count(ENTRY) == 1 and source.rstrip().endswith("}")
    head = source[:source.index(ENTRY)]
    return head + "   // Q21: the rising-trendline breakdown short replaces the red-candle buy stop.\n" \
                  "   TBOnBar(barOpen);\n}\n"


def build_research(source):
    return patch(source, [("bool qualified=barClose>=target;",
                            "bool qualified=(g_dir>0 ? barClose>=target : barClose<=target);   // Q21", 1)])


def build_ledger(source):
    return patch(source, [
        ("OrderCalcProfit(ORDER_TYPE_BUY,", "OrderCalcProfit((g_dir>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL),", 4),
        ("   double stop=g_initialEntry-g_initialRisk;\n", "   double stop=g_initialEntry-g_dir*g_initialRisk;\n", 1),
        ("   req.type=ORDER_TYPE_SELL;\n   req.price=SymbolInfoDouble(_Symbol,SYMBOL_BID);\n",
         "   bool isLong=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY);   // Q21\n"
         "   req.type=(isLong ? ORDER_TYPE_SELL : ORDER_TYPE_BUY);\n"
         "   req.price=SymbolInfoDouble(_Symbol,(isLong ? SYMBOL_BID : SYMBOL_ASK));\n", 1),
        ('"regime","assigned_rr","qualified_time");', '"regime","assigned_rr","qualified_time","direction");', 1),
        ('(tr_qualified>0 ? TimeToString(tr_qualified,TIME_DATE|TIME_SECONDS) : ""));',
         '(tr_qualified>0 ? TimeToString(tr_qualified,TIME_DATE|TIME_SECONDS) : ""),g_dir);', 1),
    ])


def main():
    RUN.mkdir(parents=True, exist_ok=True)
    parent = TREND / "RTL_trend_rr.mq5"
    expert = RUN / f"{EXPERT}.mq5"
    files = {expert.name: build_source(parent.read_text(encoding="utf-8-sig")),
             "trend_rr_research.mqh": build_research((TREND / "trend_rr_research.mqh").read_text(encoding="utf-8-sig")),
             "trend_rr_ledger.mqh": build_ledger((TREND / "trend_rr_ledger.mqh").read_text(encoding="utf-8-sig")),
             INCLUDE.name: INCLUDE.read_text(encoding="utf-8"), "contract_rolls.mqh": rolls_include()}
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
        inputs = dict(inputs, **COMMON)
        tag = f"{STEM}_{job}"
        path = RUN / f"{tag}.ini"
        if not (RUN / f"{tag}.completed.json").exists():
            ini = base_ini
            fixed = dict(Expert=fr"{INSTALL}\{EXPERT}.ex5", RunTag=tag, Report=f"{tag}.htm")
            if "RiskReward" in inputs:  # an existing tester input: replace its line, never add a duplicate key
                fixed["RiskReward"] = inputs["RiskReward"]
            for key, value in fixed.items():
                ini, n = re.subn(rf"(?m)^{key}=.*$", lambda m: f"{key}={value}", ini)
                assert n == 1, key
            ini = ini.replace("[TesterInputs]", "[TesterInputs]\n" + "\n".join(
                f"{k}={v}" for k, v in inputs.items() if k != "RiskReward"), 1)
            path.write_text(ini, encoding="utf-16")
        rr = rr_label(inputs)
        outputs = [f"{tag}_breakdown.csv", f"{tag}_breakdown_stats.csv", f"runband_{tag}_{rr}_stats.csv"]
        if inputs["BreakMode"] >= 2:
            outputs += [f"{tag}_fills.csv", f"runband_{tag}_{rr}.csv", f"{tag}_checks.csv", f"{tag}_signals.csv"]
        jobs.append(dict(tag=tag, ini=str(path), inputs=inputs, report=f"{tag}.htm", outputs=outputs))
    manifest = dict(experiment="Q21 short the breakdown of a rising trendline, full-history one-minute OHLC",
                    parent_source=str(parent), parent_sha256=sha256(parent), parent_ini=str(TREND / f"{TAG}.ini"),
                    include_source=str(INCLUDE), include_sha256=sha256(INCLUDE), expert_sha256=sha256(expert),
                    research_sha256=sha256(RUN / "trend_rr_research.mqh"),
                    ledger_sha256=sha256(RUN / "trend_rr_ledger.mqh"), protocol_sha256=sha256(PROTOCOL), jobs=jobs)
    (RUN / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(expert, len(jobs), "jobs")


if __name__ == "__main__":
    main()
