"""Prepare only 1-minute-OHLC standalone-limit research jobs.

The shared basket exporter is reused with averaging forcibly disabled.
Default trigger mirrors archive/RR_r_MFE_limit-entry.cs: observe high, then limit.
Use --immediate only to test placement as soon as a qualifying red bar closes.
"""
import argparse
import hashlib
import json
import re
import shutil

from prepare_averaging_study import build_source as averaging_source, replace_once, HOOKS
from prepare_calendar_study import make_ini
from prepare_flatten_study import TEMPLATE
from prepare_rr_clean_study import SYMBOL
from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / "Reports/limit_only_20261002"
OFFSETS = (80, 90, 95)
LIMIT_HOOKS = ROOT / "mt5/experts/limit_only_research.mqh"


def build_source():
    text = averaging_source()
    text = replace_once(text, '#include "averaging_research.mqh"',
                        '#include "limit_only_research.mqh"\n#include "limit_only_ledger.mqh"')
    text = replace_once(text, "int OnInit()\n{", '''int OnInit()
{
   if(AverageNearStopR!=0 || AverageTarget || LimitOffsetPercent<=0 || LimitOffsetPercent>=100)
      return INIT_PARAMETERS_INCORRECT;''')
    text = replace_once(text, "\t   double entry = PositionGetDouble(POSITION_PRICE_OPEN);",
                        "\t   double entry = LimitOnly ? g_limitSignalHigh : PositionGetDouble(POSITION_PRICE_OPEN);")
    text = replace_once(text, "   if(barOpen == lastBar) return;",
                        "   ProcessLimitSetup();\n   if(barOpen == lastBar) return;")
    text = replace_once(text, "\t   g_trailHigh    = 0.0;",
                        "\t   g_trailHigh    = 0.0;\n       if(LimitOnly) ResetLimitSetup();")
    for function in ("CancelOldBuyStops", "CancelAllOrders"):
        text = replace_once(text, f"void {function}()\n{{", f'''void {function}()
{{
   if(LimitOnly)
   {{
      CancelLimitPending();
      g_limitArmed=false;
      // Session flatten can close the position before the next export tick.
      // Retain its signal metadata until SaveClosedTrackedTrade has run.
      if(!g_tracking) ResetLimitSetup();
      return;
   }}''')
    text = replace_once(text, "\t   TakeResearchSnapshot();", '''\t   TakeResearchSnapshot();
       if(LimitOnly)
       {
          ArmLimitSetup(h1,l1);
          return; // no buy stop is submitted in the standalone-limit mode
       }''')
    text = replace_once(text, '"orphan_close_errors");', '''"orphan_close_errors", "limit_only", "limit_offset_percent", "wait_for_high",
                "limit_setups", "limit_triggers", "limits_placed", "limits_skipped", "limits_rejected", "limit_cancel_errors");''')
    text = replace_once(text, "g_cancelErrors, g_orphanCloseErrors);", '''g_cancelErrors, g_orphanCloseErrors, (int)LimitOnly, LimitOffsetPercent, (int)WaitForHigh,
                g_limitSetups, g_limitTriggers, g_limitsPlaced, g_limitsSkipped, g_limitsRejected, g_limitCancelErrors);''')
    return text


def build_ledger():
    text = HOOKS.read_text(encoding="utf-8-sig")
    text = replace_once(text, '"add_exit_price","orphan_volume");', '''"add_exit_price","orphan_volume", "signal_high", "signal_low", "signal_time",
         "breakout_time", "limit_order_price", "target_price");''')
    text = replace_once(text, "addExitPrice,orphanOutVol);", '''addExitPrice,orphanOutVol, g_limitSignalHigh, g_limitSignalLow,
      (g_limitSignalTime>0 ? TimeToString(g_limitSignalTime,TIME_DATE|TIME_SECONDS) : ""),
      (g_limitBreakoutTime>0 ? TimeToString(g_limitBreakoutTime,TIME_DATE|TIME_SECONDS) : ""),
      g_limitOrderPrice, g_initialEntry+g_initialRisk*RiskReward);''')
    return text


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--immediate", action="store_true")
    args = ap.parse_args()
    study = STUDY.with_name(STUDY.name+"_immediate") if args.immediate else STUDY
    study.mkdir(parents=True, exist_ok=True)
    if list(study.glob("*.completed.json")):
        raise RuntimeError("Preserve completed studies before rebuilding")
    source, ledger = build_source(), build_ledger()
    (study/"RTL_limit_only.mq5").write_text(source, encoding="utf-8-sig")
    (study/"limit_only_ledger.mqh").write_text(ledger, encoding="utf-8-sig")
    for path in (LIMIT_HOOKS, LIMIT_HOOKS.parent/"early_closes.mqh"):
        shutil.copyfile(path, study/path.name)
    template=TEMPLATE.read_text(encoding="utf-16")
    jobs=[]
    for period in ("train", "recent"):
        for offset in (None, *OFFSETS):
            label="control" if offset is None else f"p{offset}"
            tag=f"limitonly_20261002_{'immediate' if args.immediate else 'high'}_{period}_{label}"
            text=make_ini(template, tag, period, 1.0, True, symbol=SYMBOL)
            text,n=re.subn(r"(?m)^Expert=.*$",lambda _:r"Expert=CodexLimitOnlyResearch\RTL_limit_only.ex5",text)
            assert n==1
            text,n=re.subn(r"(?m)^Model=.*$","Model=1",text)
            assert n==1
            inputs=f"[TesterInputs]\nAverageNearStopR=0\nAverageTarget=false\nLimitOnly={str(offset is not None).lower()}\nLimitOffsetPercent={offset or 90}\nWaitForHigh={str(not args.immediate).lower()}"
            text=replace_once(text,"[TesterInputs]",inputs)
            ini=study/f"{tag}.ini";ini.write_text(text,encoding="utf-16")
            jobs.append(dict(tag=tag,period=period,offset=offset,ini=str(ini),csv=f"runband_{tag}_1.00.csv",report=f"{tag}.htm"))
    manifest=dict(symbol=SYMBOL,model=1,wait_for_high=not args.immediate,
                  source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                  ledger_sha256=hashlib.sha256(ledger.encode()).hexdigest(),
                  hooks_sha256=hashlib.sha256(LIMIT_HOOKS.read_bytes()).hexdigest(),jobs=jobs)
    (study/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(f"Prepared {len(jobs)} OHLC jobs in {study}")


if __name__ == "__main__":
    main()
