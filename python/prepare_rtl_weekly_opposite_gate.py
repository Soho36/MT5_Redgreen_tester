"""Prepare tester-only RTL with the exact completed-week opposite-colour gate."""
import hashlib
import json
import re
import shutil
from project_paths import PROJECT_ROOT as ROOT

BASE = ROOT / 'Reports/timeframe_baseline_20261015'
RUN = ROOT / 'Reports/rtl_weekly_opposite_gate_20261117'
DOC = ROOT / 'docs/baseline/rtl-weekly-opposite-gate'
EXPERT = 'RTL_weekly_opposite_gate'
SYMBOL = 'MNQcontDTBNT20261114'
DATA = ROOT / 'Reports/nq_extension_20261117/dataset/MT5_NQ_continuous_2010-2026_ohlcv-1m.csv'
ARMS = {'baseline': False, 'weekly_gate': True}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def tag(arm):
    return 'wopp_20261117_' + arm

HEADER = r'''// Completed W1 candles only; references are the most recent earlier colour.
input bool UseWeeklyGate=false;
bool wg_enabled=true;
datetime wg_processed=0,wg_green=0,wg_red=0;
double wg_green_low=0,wg_red_high=0;
int wg_file=INVALID_HANDLE;
long wg_cancelled=0;

bool WeeklyGateInit()
{
   wg_file=FileOpen("weekly_gate_"+g_runTag+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,'\t');
   if(wg_file==INVALID_HANDLE) return false;
   FileWrite(wg_file,"effective","week","open","high","low","close","green_week","green_low",
             "red_week","red_high","before","enabled","trigger","pending_before","positions_before");
   return true;
}
void WeeklyGateUpdate()
{
   datetime completed=iTime(_Symbol,PERIOD_W1,1);
   if(completed==0 || completed==wg_processed) return;
   MqlRates w[];
   if(CopyRates(_Symbol,PERIOD_W1,1,1,w)!=1) return;
   if(w[0].time!=completed) return;
   bool before=wg_enabled;
   string trigger="none";
   if(w[0].close<w[0].open && wg_green>0 && w[0].close<wg_green_low)
   {wg_enabled=false;trigger="halt";}
   else if(w[0].close>w[0].open && wg_red>0 && w[0].close>wg_red_high)
   {wg_enabled=true;trigger="resume";}
   FileWrite(wg_file,TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),
             TimeToString(w[0].time,TIME_DATE),w[0].open,w[0].high,w[0].low,w[0].close,
             (long)wg_green,wg_green_low,(long)wg_red,wg_red_high,(int)before,(int)wg_enabled,
             trigger,OrdersTotal(),PositionsTotal());
   if(w[0].close>w[0].open) {wg_green=completed;wg_green_low=w[0].low;}
   if(w[0].close<w[0].open) {wg_red=completed;wg_red_high=w[0].high;}
   wg_processed=completed;
}
'''

def build_source():
    src = (BASE / 'RTL_timeframe.mq5').read_text(encoding='utf-8')
    assert sha(BASE/'RTL_timeframe.mq5') == '8995d0ed6f97f21b15f4ce31f862fb8f642a1eae5a4e28c6bc371cb928165810'
    edits = [
        ('// ======== EA CORE ========', '#include "weekly_opposite_gate.mqh"\n#include "window_equity_research.mqh"\n\n// ======== EA CORE ========'),
        ('int OnInit()\n{', 'int OnInit()\n{\n   if(!MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;'),
        ('   DisplaySettings();\n   return(INIT_SUCCEEDED);',
         '   if(!WeeklyGateInit() || !WindowEquityInit()) return INIT_FAILED;\n   DisplaySettings();\n   return(INIT_SUCCEEDED);'),
        ('void OnTick()', 'void StrategyTick()'),
        ('   // 🔹 time window check (ENTRY ONLY)',
         '   if(UseWeeklyGate && !wg_enabled) return; // existing position exits above remain active\n\n   // 🔹 time window check (ENTRY ONLY)'),
    ]
    for old, new in edits:
        assert src.count(old) == 1, repr(old)
        src = src.replace(old, new)
    return src + r'''
void OnTick()
{
   WeeklyGateUpdate();
   if(UseWeeklyGate && !wg_enabled && OrdersTotal()>0)
   {
      wg_cancelled+=OrdersTotal();
      CancelAllOrders();
   }
   StrategyTick();
   WindowEquitySample();
}
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,const MqlTradeResult &result)
{
   WindowEquityTransaction(trans);
}
void OnDeinit(const int reason)
{
   WindowEquityClose();
   if(wg_file!=INVALID_HANDLE) FileClose(wg_file);
   Print("WEEKLY_GATE_CANCELLED=",wg_cancelled);
}
'''

def main():
    assert (DOC/'PROTOCOL.md').exists()
    assert not (RUN/'manifest.json').exists(), 'Preserve prepared experiment'
    RUN.mkdir(parents=True, exist_ok=True)
    src = build_source()
    (RUN/(EXPERT+'.mq5')).write_text(src, encoding='utf-8')
    (ROOT/'mt5/experts'/(EXPERT+'.mq5')).write_text(src, encoding='utf-8')
    (RUN/'weekly_opposite_gate.mqh').write_text(HEADER, encoding='utf-8')
    (ROOT/'mt5/experts/weekly_opposite_gate.mqh').write_text(HEADER, encoding='utf-8')
    shutil.copyfile(BASE/'early_closes.mqh', RUN/'early_closes.mqh')
    shutil.copyfile(ROOT/'Reports/rtl_gg_exclude16_20261101/window_equity_research.mqh', RUN/'window_equity_research.mqh')
    jobs = []
    declared = set(re.findall(r'^input\s+\w+\s+(\w+)\s*=',src+'\n'+HEADER,re.M))
    for arm, enabled in ARMS.items():
        lines=(BASE/'tf_20261015_rtl_m30_rr1p0.ini').read_text(encoding='utf-16').splitlines()
        changes=dict(Expert='CodexResearch\\'+EXPERT+'.ex5',Symbol=SYMBOL,ToDate='2026.11.14',
                     RunTag=tag(arm),Report=tag(arm)+'.htm')
        for key,value in changes.items():
            assert sum(x.startswith(key+'=') for x in lines)==1
            lines=[key+'='+value if x.startswith(key+'=') else x for x in lines]
        idx=lines.index('[TesterInputs]')+1
        lines[idx:idx]=['UseWeeklyGate='+str(enabled).lower()]
        given={x.split('=')[0] for x in lines[idx:lines.index('[Experts]')] if '=' in x}
        assert declared==given,declared^given
        (RUN/(tag(arm)+'.ini')).write_text('\n'.join(lines)+'\n',encoding='utf-16')
        jobs.append(dict(tag=tag(arm),arm=arm,outputs=[f'runband_{tag(arm)}_1.00.csv',
            f'runband_{tag(arm)}_1.00_stats.csv',f'window_equity_{tag(arm)}.bin',f'weekly_gate_{tag(arm)}.csv']))
    files=[DOC/'PROTOCOL.md',DATA,BASE/'RTL_timeframe.mq5',BASE/'tf_20261015_rtl_m30_rr1p0.ini',
           ROOT/'python/prepare_rtl_weekly_opposite_gate.py',*RUN.glob('*.mq5'),*RUN.glob('*.mqh'),*RUN.glob('*.ini')]
    manifest=dict(expert=EXPERT,symbol=SYMBOL,jobs=jobs,input_hashes={str(p):sha(p) for p in files})
    (RUN/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('Prepared',RUN,flush=True)

if __name__=='__main__':
    main()

