"""Prepare the baseline trade-path report (descriptive, 2026-10-10): what price does between entry and exit.

The baseline runband EA gets a passive tick log (text edits below, no input, no order, no strategy state):
every tester quote while a position is open goes to ticks_<tag>.bin as (ticket, time in ms, bid), 24 bytes
per record. A new ticket starts with two header records: time -1 = fill price, time -2 = stop price.
The trade ledger must stay byte-identical to the saved baseline.

Writes Reports/trade_paths_20261010/. Run with
    .\\venv\\Scripts\\python.exe python\\run_mt5_job.py Reports\\trade_paths_20261010 RTL_paths
"""

import hashlib
import json
import shutil

from prepare_instrument_baseline import make_ini
from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / "Reports" / "trade_paths_20261010"
EXPERT = "RTL_paths"
SYMBOL = "MNQcontDTBNT20102026_2"
SOURCE = ROOT / "mt5" / "experts" / "RR_r_MFE_buy-stop-entry_runband.cs"
TAG = "paths_20261010_baseline"

EDITS = (
    # state and the logger
    ("string   g_runTag    = \"\";   // resolved in OnInit, reused by OnTester\n",
     "string   g_runTag    = \"\";   // resolved in OnInit, reused by OnTester\n"
     "\n"
     "// ======== TICK PATH LOG (research) ========\n"
     "// Every tester quote while a position is open: ticket, time in ms, bid.\n"
     "// A new ticket starts with two header records (time -1: fill price,\n"
     "// time -2: stop price). Passive: no orders, no strategy state.\n"
     "int   g_pathFile   = INVALID_HANDLE;\n"
     "ulong g_pathTicket = 0;\n"
     "\n"
     "void PathRecord(ulong ticket, long time_msc, double price)\n"
     "{\n"
     "   FileWriteLong(g_pathFile, (long)ticket);\n"
     "   FileWriteLong(g_pathFile, time_msc);\n"
     "   FileWriteDouble(g_pathFile, price);\n"
     "}\n"
     "\n"
     "void PathLogTick()\n"
     "{\n"
     "   if(g_pathFile == INVALID_HANDLE || !PositionSelect(_Symbol)) return;\n"
     "   MqlTick tick;\n"
     "   if(!SymbolInfoTick(_Symbol, tick)) return;\n"
     "   ulong ticket = (ulong)PositionGetInteger(POSITION_TICKET);\n"
     "   if(ticket != g_pathTicket)\n"
     "   {\n"
     "      g_pathTicket = ticket;\n"
     "      PathRecord(ticket, -1, PositionGetDouble(POSITION_PRICE_OPEN));\n"
     "      PathRecord(ticket, -2, PositionGetDouble(POSITION_SL));\n"
     "   }\n"
     "   PathRecord(ticket, tick.time_msc, tick.bid);\n"
     "}\n"),
    # open
    ("   Print(\"Run tag: \", g_runTag, \"   ->   \", g_csvName);\n",
     "   Print(\"Run tag: \", g_runTag, \"   ->   \", g_csvName);\n"
     "   g_pathFile = FileOpen(\"ticks_\" + g_runTag + \".bin\", FILE_WRITE|FILE_BIN|FILE_COMMON);\n"
     "   if(g_pathFile == INVALID_HANDLE)\n"
     "   {\n"
     "      Print(\"Tick path file open failed \", GetLastError());\n"
     "      return INIT_FAILED;\n"
     "   }\n"),
    # close
    ("double OnTester()\n{\n   SaveClosedTrackedTrade();\n",
     "double OnTester()\n{\n   SaveClosedTrackedTrade();\n"
     "   if(g_pathFile != INVALID_HANDLE)\n"
     "   {\n"
     "      FileClose(g_pathFile);\n"
     "      g_pathFile = INVALID_HANDLE;\n"
     "   }\n"),
    # tick hook, before anything else
    ("   // ---- TRACK FLOATING MAE / MFE (tick-based, broker-safe) ----\n",
     "   PathLogTick();\n"
     "\n"
     "   // ---- TRACK FLOATING MAE / MFE (tick-based, broker-safe) ----\n"),
)


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
    ini = make_ini(TAG, SYMBOL).replace("Expert=CodexTrendlineResearch\\RTL_runband.ex5",
                                        f"Expert=CodexTrendlineResearch\\{EXPERT}.ex5")
    assert f"{EXPERT}.ex5" in ini
    (STUDY / f"{TAG}.ini").write_text(ini, encoding="utf-16")
    job = {"tag": TAG, "outputs": [f"runband_{TAG}_1.00.csv", f"runband_{TAG}_1.00_stats.csv", f"ticks_{TAG}.bin"]}
    manifest = {"expert": EXPERT, "symbol": SYMBOL, "source": SOURCE.relative_to(ROOT).as_posix(),
                "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(), "jobs": [job]}
    (STUDY / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"Wrote 1 job to {STUDY}")


if __name__ == "__main__":
    main()
