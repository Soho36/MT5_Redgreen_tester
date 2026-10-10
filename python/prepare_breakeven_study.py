"""Prepare the break-even stop study (exploratory, 2026-10-10): once bid >= entry + 1R, move the stop to entry.

Protocol: docs/baseline/breakeven-stop/PROTOCOL.md (fixed before any run; its hash goes into the manifest).
The baseline runband EA gets one input, BreakevenAtR (text edits below, nothing else changes):
  0 = off (baseline), x > 0 = move the stop once to the entry price when bid >= entry + x * risk.
The bar-close exit and the session flatten are untouched. With the input on, the ledger gets one extra
column, be_time (when the stop was moved, empty if never); off keeps the baseline schema, so the control
must reproduce the baseline ledger exactly.

Writes Reports/breakeven_20261010/. Run with
    .\\venv\\Scripts\\python.exe python\\run_mt5_job.py Reports\\breakeven_20261010 RTL_breakeven
"""

import hashlib
import json
import shutil

from prepare_instrument_baseline import make_ini
from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / "Reports" / "breakeven_20261010"
EXPERT = "RTL_breakeven"
SYMBOL = "MNQcontDTBNT20102026_2"
SOURCE = ROOT / "mt5" / "experts" / "RR_r_MFE_buy-stop-entry_runband.cs"
PROTOCOL = ROOT / "docs" / "baseline" / "breakeven-stop" / "PROTOCOL.md"
JOBS = (("off", 0.0), ("1r", 1.0))

EDITS = (
    # input
    ("input double TrailDistanceR = 0.0;   // Trail distance behind the high, in R (0 = off)\n",
     "input double TrailDistanceR = 0.0;   // Trail distance behind the high, in R (0 = off)\n"
     "\n"
     "// ======== BREAK-EVEN STOP (research, default off) ========\n"
     "// The first time bid >= entry + BreakevenAtR x risk, the stop moves once to the\n"
     "// entry price. It does not trail. The bar-close target exit and the session\n"
     "// flatten stay active. BreakevenAtR = 0 -> off.\n"
     "input double BreakevenAtR   = 0.0;   // Move the stop to entry at this many R (0 = off)\n"),
    # state
    ("double   g_trailHigh       = 0.0; // highest bid since entry (trailing stop)\n",
     "double   g_trailHigh       = 0.0; // highest bid since entry (trailing stop)\n"
     "datetime g_beTime          = 0;   // when the stop was moved to entry (0 = not moved)\n"
     "int      g_beMoves         = 0;   // break-even moves in this pass\n"
     "int      g_beFailed        = 0;   // failed break-even modifications in this pass\n"),
    # tick-level stop move
    ("// Flatten cutoff for this bar's date, in minutes after midnight.\n",
     "// Tick-level break-even stop for the open long position (see BreakevenAtR).\n"
     "void UpdateBreakevenStop()\n"
     "{\n"
     "   if(BreakevenAtR <= 0.0 || g_beTime != 0 || !g_initialSet || g_initialRisk <= 0.0) return;\n"
     "   if(!PositionSelect(_Symbol)) return;\n"
     "\n"
     "   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);\n"
     "   if(bid < g_initialEntry + BreakevenAtR * g_initialRisk) return;\n"
     "\n"
     "   double newSl = NormalizeDouble(g_initialEntry, _Digits);\n"
     "   if(PositionGetDouble(POSITION_SL) >= newSl) return;\n"
     "\n"
     "   MqlTradeRequest req = {};\n"
     "   MqlTradeResult  res = {};\n"
     "   req.action   = TRADE_ACTION_SLTP;\n"
     "   req.symbol   = _Symbol;\n"
     "   req.position = PositionGetInteger(POSITION_TICKET);\n"
     "   req.sl       = newSl;\n"
     "   req.tp       = PositionGetDouble(POSITION_TP);\n"
     "   if(!OrderSend(req, res))\n"
     "   {\n"
     "      g_beFailed++;\n"
     "      Print(\"Breakeven SL modify failed err=\", GetLastError(), \" retcode=\", res.retcode, \" sl=\", newSl);\n"
     "      return;\n"
     "   }\n"
     "   g_beTime = TimeCurrent();\n"
     "   g_beMoves++;\n"
     "}\n"
     "\n"
     "// Flatten cutoff for this bar's date, in minutes after midnight.\n"),
    # ledger: one extra column, only when the input is on
    ("   // A new Unicode CSV may already contain its two-byte BOM.\n",
     "   if(BreakevenAtR > 0.0)\n"
     "   {\n"
     "      if(FileSize(f) <= 2)\n"
     "         FileWrite(f, \"ticket\", \"entry_time\", \"exit_time\", \"mae_money\", \"mfe_money\", \"trade_profit\",\n"
     "                   \"candle_range\", \"red_run\", \"location\", \"be_time\");\n"
     "      FileSeek(f, 0, SEEK_END);\n"
     "      FileWrite(f, (long)g_ticket,\n"
     "                TimeToString(entryTime, TIME_DATE|TIME_SECONDS),\n"
     "                TimeToString(exitTime, TIME_DATE|TIME_SECONDS),\n"
     "                g_maeMoney, g_mfeMoney, realized, candleRange, g_redRun,\n"
     "                DoubleToString(g_location, 10),\n"
     "                (g_beTime > 0 ? TimeToString(g_beTime, TIME_DATE|TIME_SECONDS) : \"\"));\n"
     "      FileClose(f);\n"
     "      return;\n"
     "   }\n"
     "\n"
     "   // A new Unicode CSV may already contain its two-byte BOM.\n"),
    # input check
    ("   if(SnapshotBars < 0)\n",
     "   if(BreakevenAtR < 0.0)\n"
     "   {\n"
     "      Print(\"BreakevenAtR must be >= 0\");\n"
     "      return INIT_PARAMETERS_INCORRECT;\n"
     "   }\n"
     "   if(SnapshotBars < 0)\n"),
    # pass summary
    ("                \"early_close_calendar\");\n",
     "                \"early_close_calendar\", \"breakeven_at_r\", \"be_moves\", \"be_failed\");\n"),
    ("                (int)UseEarlyCloseCalendar);\n",
     "                (int)UseEarlyCloseCalendar, BreakevenAtR, g_beMoves, g_beFailed);\n"),
    # per-position state
    ("g_trailHigh    = entry;\n", "g_trailHigh    = entry;\n\t\t  g_beTime       = 0;\n"),
    ("g_trailHigh    = 0.0;\n", "g_trailHigh    = 0.0;\n\t   g_beTime       = 0;\n"),
    # tick hook
    ("UpdateTrailingStop();\n", "UpdateTrailingStop();\n\tif(isInPosition)\n\t   UpdateBreakevenStop();\n"),
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_source():
    src = SOURCE.read_text(encoding="utf-8").replace("\r\n", "\n")
    for old, new in EDITS:
        assert src.count(old) == 1, f"edit anchor not unique: {old[:60]!r}"
        src = src.replace(old, new)
    return src


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    (STUDY / f"{EXPERT}.mq5").write_text(build_source(), encoding="utf-8")
    shutil.copyfile(ROOT / "mt5" / "experts" / "early_closes.mqh", STUDY / "early_closes.mqh")
    jobs = []
    for name, level in JOBS:
        tag = f"be_20261010_{name}"
        ini = make_ini(tag, SYMBOL).replace("Expert=CodexTrendlineResearch\\RTL_runband.ex5",
                                            f"Expert=CodexTrendlineResearch\\{EXPERT}.ex5")
        assert ini.count("TrailDistanceR=0\n") == 1 and f"{EXPERT}.ex5" in ini
        ini = ini.replace("TrailDistanceR=0\n", f"TrailDistanceR=0\nBreakevenAtR={level}\n")
        (STUDY / f"{tag}.ini").write_text(ini, encoding="utf-16")
        jobs.append({"tag": tag, "breakeven_at_r": level,
                     "outputs": [f"runband_{tag}_1.00.csv", f"runband_{tag}_1.00_stats.csv"]})
    manifest = {"expert": EXPERT, "symbol": SYMBOL,
                "source": SOURCE.relative_to(ROOT).as_posix(), "source_sha256": sha256(SOURCE),
                "protocol": PROTOCOL.relative_to(ROOT).as_posix(), "protocol_sha256": sha256(PROTOCOL), "jobs": jobs}
    (STUDY / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"Wrote {len(jobs)} jobs to {STUDY}")


if __name__ == "__main__":
    main()
