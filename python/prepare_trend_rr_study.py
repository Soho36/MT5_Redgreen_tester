"""Freeze RTL-only trend-conditioned RR, retaining its market-on-bar-close exit."""
import hashlib
import json
import re
import shutil

from prepare_averaging_study import build_source as averaging_source, HOOKS, replace_once
from prepare_calendar_study import make_ini
from prepare_flatten_study import TEMPLATE
from prepare_rr_clean_study import SYMBOL
from project_paths import PROJECT_ROOT as ROOT
from trend_regimes import FAST, VARIANTS, build_reference

STUDY = ROOT / "Reports/trend_rr_20261002"
TREND = ROOT / "mt5/experts/trend_rr_research.mqh"


def build_source():
    text = averaging_source()
    text = replace_once(text, '#include "averaging_research.mqh"',
                        '#include "trend_rr_research.mqh"\n#include "trend_rr_ledger.mqh"')
    text = replace_once(text, "int OnInit()\n{", '''int OnInit()
{
   if(AverageNearStopR!=0 || AverageTarget || GreenSignal || (FastDays!=40 && FastDays!=50 && FastDays!=60))
      return INIT_PARAMETERS_INCORRECT;''')
    text = replace_once(text, "   DisplaySettings();\n   return(INIT_SUCCEEDED);",
                        "   if(!OpenTrendExports()) return INIT_FAILED;\n   DisplaySettings();\n   return(INIT_SUCCEEDED);")
    text = replace_once(text, "       g_addAttempted=false;", "       FreezeTrendAtEntry();\n       g_addAttempted=false;")
    text = replace_once(text, "   double target = g_initialEntry + g_initialRisk * RiskReward;",
                        "   double target = g_initialEntry + g_initialRisk * tr_rr;")
    text = replace_once(text, "   if(barClose >= target)\n   {",
                        "   LogTrendCheck(barClose,target);\n   if(barClose >= target)\n   {")
    text = replace_once(text, "\t   TakeResearchSnapshot();", "\t   TakeResearchSnapshot();\n       LogTrendSignal();")
    text = replace_once(text, "      if(!OrderSend(req, res))\n         Print(\"❌ Close fail err=\", GetLastError());",
                        "      if(!OrderSend(req, res) || res.retcode!=TRADE_RETCODE_DONE)\n      { tr_closeErrors++; Print(\"TREND_CLOSE_ERROR \",res.retcode); }")
    text = replace_once(text, '"orphan_close_errors");',
                        '"orphan_close_errors", "fast_days", "bull_rr", "bear_rr", "trend_export_errors", "trend_close_errors");')
    text = replace_once(text, "g_cancelErrors, g_orphanCloseErrors);",
                        "g_cancelErrors, g_orphanCloseErrors, FastDays, BullRR, BearRR, tr_exportErrors, tr_closeErrors);")
    return text


def build_ledger():
    text = HOOKS.read_text(encoding="utf-8-sig")
    text = replace_once(text, '"add_exit_price","orphan_volume");', '''"add_exit_price","orphan_volume",
         "signal_time","signal_open","signal_high","signal_low","signal_close",
         "previous_day","previous_close","sma_fast","sma200","regime","assigned_rr","qualified_time");''')
    text = replace_once(text, "addExitPrice,orphanOutVol);", '''addExitPrice,orphanOutVol,
      TimeToString(g_signalTime,TIME_DATE|TIME_SECONDS),tr_o,tr_h,tr_l,tr_c,
      TimeToString(tr_entryPreviousDay,TIME_DATE),tr_entryClose,tr_entryFast,tr_entrySlow,tr_entryRegime,tr_rr,
      (tr_qualified>0 ? TimeToString(tr_qualified,TIME_DATE|TIME_SECONDS) : ""));''')
    return text


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    if list(STUDY.glob("*.completed.json")):
        raise RuntimeError("Preserve completed runs before rebuilding")
    source, ledger = build_source(), build_ledger()
    (STUDY/"RTL_trend_rr.mq5").write_text(source, encoding="utf-8-sig")
    (STUDY/"trend_rr_ledger.mqh").write_text(ledger, encoding="utf-8-sig")
    for path in (TREND, TREND.parent/"early_closes.mqh"):
        shutil.copyfile(path, STUDY/path.name)
    daily=build_reference(STUDY/"daily_reference.csv")
    jobs=[]
    for fast in (50, 40, 60):
        for variant, (bull, bear) in VARIANTS.items():
            if variant=="baseline" and fast!=50:
                continue # identical fixed-RR trades; relabel independently for diagnostics
            tag=f"trendrr_20261002_f{fast}_{variant}"
            text=make_ini(TEMPLATE.read_text(encoding="utf-16"),tag,"full",1.,True,symbol=SYMBOL)
            for key,value in dict(Expert=r"CodexTrendResearch\RTL_trend_rr.ex5",FromDate="2010.06.07",ToDate="2026.07.14",Model="1").items():
                text,n=re.subn(rf"(?m)^{key}=.*$",lambda _:f"{key}={value}",text)
                assert n==1
            text=replace_once(text,"[TesterInputs]",f"[TesterInputs]\nAverageNearStopR=0\nAverageTarget=false\nFastDays={fast}\nBullRR={bull}\nBearRR={bear}")
            ini=STUDY/f"{tag}.ini";ini.write_text(text,encoding="utf-16")
            jobs.append(dict(tag=tag,fast=fast,variant=variant,bull=bull,bear=bear,ini=str(ini),
                             csv=f"runband_{tag}_1.00.csv",report=f"{tag}.htm",
                             extra_csv=[f"{tag}_checks.csv",f"{tag}_signals.csv"]))
    manifest=dict(strategy="RTL",exit="bar-close-qualified market",model=1,symbol=SYMBOL,
                  commission=1.05,primary_extra_cost=0.,training_start="2010-06-07",test_years=list(range(2015,2026)),
                  first_valid_regime=str(daily.index[daily.sma200.notna()][0].date()),
                  source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                  ledger_sha256=hashlib.sha256(ledger.encode()).hexdigest(),
                  hooks_sha256=hashlib.sha256(TREND.read_bytes()).hexdigest(),jobs=jobs)
    (STUDY/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(f"Prepared {len(jobs)} full-history OHLC runs. First prior-200-day regime: {manifest['first_valid_regime']}")


if __name__=="__main__":
    main()
