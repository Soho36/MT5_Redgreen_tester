"""Build a tester-only averaging variant and eight frozen comparison jobs.

Compile Reports/averaging_entry_20261001/RTL_average.mq5 with MetaEditor, then:
  ./python/run_exit_study.ps1 -StudyDir Reports/averaging_entry_20261001 \
      -ExpertName RTL_average -InstallFolder CodexAveragingResearch
Source strategy defaults remain unchanged. Protocol: docs/AVERAGING_ENTRY_PROTOCOL.md.
"""
import argparse
import hashlib
import json
import re
import shutil

from prepare_calendar_study import make_ini
from prepare_flatten_study import TEMPLATE
from prepare_rr_clean_study import SYMBOL
from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / "Reports" / "averaging_entry_20261001"
SOURCE = ROOT / "mt5/experts/RR_r_MFE_buy-stop-entry_runband.cs"
HOOKS = ROOT / "mt5/experts/averaging_research.mqh"
DISTANCES = (0.0, 0.05, 0.10, 0.20)


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def build_source():
    text = SOURCE.read_text(encoding="utf-8-sig")
    text = replace_once(text, "// ======== HELPER FUNCTIONS ========",
                        '#include "averaging_research.mqh"\n\n// ======== HELPER FUNCTIONS ========')
    text = replace_once(text, "int OnInit()\n{", '''int OnInit()
{
   if(!MQLInfoInteger(MQL_TESTER) || AccountInfoInteger(ACCOUNT_MARGIN_MODE)==ACCOUNT_MARGIN_MODE_RETAIL_HEDGING
      || AverageNearStopR<0 || AverageNearStopR>=1 || TrailDistanceR!=0 || SnapshotBars!=0
      || SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE)<=0)
   {
      Print("Averaging variant requires tester, netting, 0<=fraction<1, no trailing/snapshot");
      return INIT_PARAMETERS_INCORRECT;
   }''')
    start = text.index("void SaveClosedTrackedTrade()\n{")
    end = text.index("\n}\n", start) + 3
    text = text[:start] + "void SaveClosedTrackedTrade()\n{\n   SaveAveragingBasket();\n}\n" + text[end:]
    text = replace_once(text, "g_ticket    = PositionGetInteger(POSITION_TICKET);",
                        "g_ticket    = PositionGetInteger(POSITION_IDENTIFIER);")
    text = replace_once(text, "   // ---- TRACK FLOATING MAE / MFE (tick-based, broker-safe) ----",
                        "   if(!CloseOrphanedAdd()) return;\n   // ---- TRACK FLOATING MAE / MFE (tick-based, broker-safe) ----")
    text = replace_once(text, "\t   double entry = PositionGetDouble(POSITION_PRICE_OPEN);", '''       g_addAttempted=false;
       g_addTicket=0;
       g_addLimit=0;
       g_addStatus=0;
\t   double entry = PositionGetDouble(POSITION_PRICE_OPEN);''')
    text = replace_once(text, "   if(barOpen == lastBar) return;", '''   if(isInPosition) PlaceAveragingOrder();
   else CancelAveragingOrder();
   if(barOpen == lastBar) return;''')
    text = replace_once(text, "void CloseAllPositions()\n{", "void CloseAllPositions()\n{\n   CancelAveragingOrder();")
    text = replace_once(text, "   double target = g_initialEntry + g_initialRisk * RiskReward;", '''   double target = g_initialEntry + g_initialRisk * RiskReward;
   if(AverageTarget)
   {
      double average=PositionGetDouble(POSITION_PRICE_OPEN);
      target=average + (average-(g_initialEntry-g_initialRisk))*RiskReward;
   }''')
    text = replace_once(text, "   if(barClose >= target)\n   {",
                        "   if(barClose >= target)\n   {\n      CancelAveragingOrder();")
    text = replace_once(text, '"early_close_calendar");', '''"early_close_calendar", "average_near_stop_r", "average_target",
                "adds_placed", "adds_skipped", "adds_rejected", "cancel_errors", "orphan_close_errors");''')
    text = replace_once(text, "(int)UseEarlyCloseCalendar);", '''(int)UseEarlyCloseCalendar, AverageNearStopR, (int)AverageTarget,
                g_addPlaced, g_addSkipped, g_addRejected, g_cancelErrors, g_orphanCloseErrors);''')
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--average-target", action="store_true")
    ap.add_argument("--generated-ticks", action="store_true",
                    help="Focused off/10%% modelling sensitivity in a separate directory")
    args = ap.parse_args()
    study = STUDY.with_name(STUDY.name + "_ticks") if args.generated_ticks else STUDY
    study.mkdir(parents=True, exist_ok=True)
    if list(study.glob("*.completed.json")):
        raise RuntimeError("Completed study exists; preserve it before changing the protocol")
    source = build_source()
    (study / "RTL_average.mq5").write_text(source, encoding="utf-8-sig")
    for path in (HOOKS, SOURCE.parent / "early_closes.mqh"):
        shutil.copyfile(path, study / path.name)
    template = TEMPLATE.read_text(encoding="utf-16")
    jobs = []
    for period in ("train", "recent"):
        for distance in ((0.0, 0.10) if args.generated_ticks else DISTANCES):
            tag = f"average{'ticks' if args.generated_ticks else ''}_20261001_{period}_d{distance:.2f}".replace(".", "p")
            text = make_ini(template, tag, period, 1.0, True, symbol=SYMBOL)
            text, n = re.subn(r"(?m)^Expert=.*$", lambda _: r"Expert=CodexAveragingResearch\RTL_average.ex5", text)
            assert n == 1
            if args.generated_ticks:
                text, n = re.subn(r"(?m)^Model=.*$", "Model=0", text)
                assert n == 1
            text = replace_once(text, "[TesterInputs]", f"[TesterInputs]\nAverageNearStopR={distance}\nAverageTarget={str(args.average_target).lower()}")
            ini = study / f"{tag}.ini"
            ini.write_text(text, encoding="utf-16")
            jobs.append(dict(tag=tag, period=period, distance=distance, ini=str(ini),
                             csv=f"runband_{tag}_1.00.csv", report=f"{tag}.htm"))
    manifest = dict(symbol=SYMBOL, average_target=args.average_target, model=0 if args.generated_ticks else 1,
                    source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                    hooks_sha256=hashlib.sha256(HOOKS.read_bytes()).hexdigest(), jobs=jobs)
    (study / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Prepared {len(jobs)} jobs in {study}")


if __name__ == "__main__":
    main()
