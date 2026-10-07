"""Prepare the signal-colour check on MNQ (exploratory, 2026-10-08): is the RTL edge the red candle,
any buy stop over the previous bar, or just being long NQ?

The baseline runband EA gets one input, SignalMode (text edits below, nothing else changes):
  0 = red candle (baseline), 1 = green candle (the user's GG idea), 2 = any non-doji candle,
  3 = control: market buy at every bar open while flat, stop one previous-candle range below (no pattern).
The "run" filter counts consecutive signal-coloured bars (green run in mode 1). Mode 0 with MaxRedRun 3
must reproduce the baseline ledger exactly.

Writes Reports/signal_colour_20261008/. Run with
    .\\venv\\Scripts\\python.exe python\\run_mt5_job.py Reports\\signal_colour_20261008 RTL_signal
"""

import json
import shutil

from prepare_instrument_baseline import make_ini
from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / "Reports" / "signal_colour_20261008"
EXPERT = "RTL_signal"
SYMBOL = "MNQcontDTBNT20102026_2"
JOBS = (("red_cap3", 0, 3), ("red_nocap", 0, 0), ("green_cap3", 1, 3), ("green_nocap", 1, 0),
        ("any", 2, 0), ("market_control", 3, 0))

EDITS = (
    ("input int    MaxRedRun = 0;  // Maximum consecutive reds allowed (0 = no cap)\n",
     "input int    MaxRedRun = 0;  // Maximum consecutive reds allowed (0 = no cap)\n"
     "input int    SignalMode = 0; // 0 red, 1 green, 2 any non-doji, 3 market buy every bar (control)\n"
     "\n"
     "bool IsSignalBar(int i)\n"
     "{\n"
     "   double o = iOpen(_Symbol, _Period, i), c = iClose(_Symbol, _Period, i);\n"
     "   if(SignalMode == 1) return c > o;\n"
     "   if(SignalMode == 2) return c != o;\n"
     "   if(SignalMode == 3) return true;\n"
     "   return c < o;\n"
     "}\n"),
    ("      if(iClose(_Symbol, _Period, i) < iOpen(_Symbol, _Period, i))\n",
     "      if(IsSignalBar(i))\n"),
    ("    if(c1 < o1)\n", "    if(IsSignalBar(1))\n"),
    ("\t   double entry = h1;\n\t   double stop  = l1;\n",
     "\t   double entry = (SignalMode == 3 ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : h1);\n"
     "\t   double stop  = entry - (h1 - l1);\n"),
    ("\t   req.action       = TRADE_ACTION_PENDING;\n", "\t   req.action       = (SignalMode == 3 ? TRADE_ACTION_DEAL : TRADE_ACTION_PENDING);\n"),
    ("\t   req.type         = ORDER_TYPE_BUY_STOP;\n", "\t   req.type         = (SignalMode == 3 ? ORDER_TYPE_BUY : ORDER_TYPE_BUY_STOP);\n"),
    ("\t   req.type_filling = ORDER_FILLING_RETURN;\n", "\t   if(SignalMode != 3) req.type_filling = ORDER_FILLING_RETURN;\n"),
)


def build_source():
    src = (ROOT / "mt5" / "experts" / "RR_r_MFE_buy-stop-entry_runband.cs").read_text(encoding="utf-8")
    src = src.replace("\r\n", "\n")
    for old, new in EDITS:
        assert src.count(old) == 1, f"edit anchor not unique: {old[:60]!r}"
        src = src.replace(old, new)
    return src


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    (STUDY / f"{EXPERT}.mq5").write_text(build_source(), encoding="utf-8")
    shutil.copyfile(ROOT / "mt5" / "experts" / "early_closes.mqh", STUDY / "early_closes.mqh")
    jobs = []
    for name, mode, cap in JOBS:
        tag = f"signal_20261008_{name}"
        ini = make_ini(tag, SYMBOL).replace("Expert=CodexTrendlineResearch\\RTL_runband.ex5",
                                            f"Expert=CodexTrendlineResearch\\{EXPERT}.ex5")
        assert "MaxRedRun=3\n" in ini
        ini = ini.replace("MaxRedRun=3\n", f"MaxRedRun={cap}\nSignalMode={mode}\n")
        (STUDY / f"{tag}.ini").write_text(ini, encoding="utf-16")
        jobs.append({"tag": tag, "mode": mode, "max_run": cap,
                     "outputs": [f"runband_{tag}_1.00.csv", f"runband_{tag}_1.00_stats.csv"]})
    (STUDY / "manifest.json").write_text(json.dumps({"expert": EXPERT, "symbol": SYMBOL, "jobs": jobs}, indent=1),
                                         encoding="utf-8")
    print(f"Wrote {len(jobs)} jobs to {STUDY}")


if __name__ == "__main__":
    main()
