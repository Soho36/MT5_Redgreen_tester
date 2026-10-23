"""Prepare a tighter RTL stop with the target scaled to it, on NQ and YM (2026-10-23, exploratory, user request).

Research copy RTL_stopfrac of the uncapped RTL baseline with one input, StopFraction = k: the stop sits at
entry - k x signal candle range (rounded to the tick), not at the candle low. The bar-close exit is unchanged in code:
it already exits after a bar closes at entry + RiskReward x (entry - stop), so the 1R target shrinks with the stop.
The ledger's candle_range column logs the actual risk (entry - stop), so R = profit / (candle_range x $/pt) as before.
k = 1.0 must reproduce the RTL_runband ledgers of Reports/ym_baselines_20261023 exactly.

INIs: the YM study's RTL INI (server-clock research INI) with symbol, dates, report, run tag, Expert and StopFraction.
Writes Reports/stop_fraction_20261023/. Run with
    python run_mt5_job.py Reports/stop_fraction_20261023 RTL_stopfrac
"""
import json
import shutil

from prepare_ym_baselines import STRATEGIES, SYMBOLS, make_ini
from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / "Reports" / "stop_fraction_20261023"
EXPERT = "RTL_stopfrac"
FRACTIONS = (1.0, 0.75, 0.5)
INSTRUMENTS = ("nq", "ym")

EDITS = (
    ("input int    MaxRedRun = 0;  // Maximum consecutive reds allowed (0 = no cap)\n",
     "input int    MaxRedRun = 0;  // Maximum consecutive reds allowed (0 = no cap)\n"
     "input double StopFraction = 1.0; // stop at entry - k x candle range (1 = candle low); target scales with it\n"),
    ("   if(SnapshotBars < 0)\n",
     "   if(!(StopFraction > 0.0 && StopFraction <= 1.0))\n"
     "   {\n"
     "      Print(\"StopFraction must be in (0, 1]\");\n"
     "      return INIT_PARAMETERS_INCORRECT;\n"
     "   }\n\n"
     "   if(SnapshotBars < 0)\n"),
    ("\t   double stop  = l1;\n\t   double risk  = entry - stop;\n\t   g_candleRange = h1 - l1;\n",
     "\t   double stop  = l1;\n"
     "\t   if(StopFraction < 1.0)\n"
     "\t   {\n"
     "\t      double tick = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);\n"
     "\t      stop = NormalizeDouble(MathRound((h1 - StopFraction * (h1 - l1)) / tick) * tick, _Digits);\n"
     "\t      if(stop >= entry) stop = NormalizeDouble(entry - tick, _Digits);\n"
     "\t   }\n"
     "\t   double risk  = entry - stop;\n"
     "\t   g_candleRange = risk;   // logged as the trade's risk (= candle range when StopFraction = 1)\n"),
)


def build_source():
    src = (ROOT / "mt5" / "experts" / "RR_r_MFE_buy-stop-entry_runband.cs").read_text(encoding="utf-8").replace("\r\n", "\n")
    for old, new in EDITS:
        assert src.count(old) == 1, f"edit anchor not unique: {old[:60]!r}"
        src = src.replace(old, new)
    return src


def main():
    if (STUDY / "manifest.json").exists():
        raise RuntimeError("Prepared manifest already exists; preserve it")
    STUDY.mkdir(parents=True, exist_ok=True)
    (STUDY / f"{EXPERT}.mq5").write_text(build_source(), encoding="utf-8")
    shutil.copyfile(ROOT / "mt5" / "experts" / "early_closes.mqh", STUDY / "early_closes.mqh")
    template = STRATEGIES["rtl"][2]
    jobs = []
    for inst in INSTRUMENTS:
        for k in FRACTIONS:
            tag = f"stopfrac_20261023_{inst}_k{k:g}".replace(".", "p")
            ini = make_ini(template, tag, SYMBOLS[inst])
            for old, new in (("Expert=CodexBaselineResearch\\RTL_runband.ex5", f"Expert=CodexResearch\\{EXPERT}.ex5"),
                             ("MaxRedRun=0\n", f"MaxRedRun=0\nStopFraction={k}\n")):
                assert ini.count(old) == 1, old
                ini = ini.replace(old, new)
            (STUDY / f"{tag}.ini").write_text(ini, encoding="utf-16")
            jobs.append({"tag": tag, "instrument": inst, "symbol": SYMBOLS[inst], "stop_fraction": k,
                         "outputs": [f"runband_{tag}_1.00.csv", f"runband_{tag}_1.00_stats.csv"]})
    (STUDY / "manifest.json").write_text(json.dumps({"expert": EXPERT, "jobs": jobs}, indent=1), encoding="utf-8")
    print(f"Wrote {len(jobs)} jobs to {STUDY}")


if __name__ == "__main__":
    main()
