"""Prepare and compile the frozen immediate failed-breakout short experiment."""
from pathlib import Path
import re
import shutil
import sys
from project_paths import PROJECT_ROOT as ROOT
from prepare_gg_outside import once
from run_rtl_vwap_replay import INSTALL, digest, hidden_process, save_json

RUN = ROOT / 'Reports/rtl_failed_breakout_short_20261105'
BASE = ROOT / 'Reports/gg_red_outside_short_20261021'
PROTOCOL = ROOT / 'docs/baseline/rtl-failed-breakout-short/PROTOCOL.md'
EXPERT = 'RTL_failed_breakout_short'
TAG = 'rtlfailed_20261105'

EXTENSION = r'''
input bool UseFailedBreakout = true;
bool g_fbWatching = false;
datetime g_fbSignal = 0, g_fbBar = 0;
double g_fbHigh = 0.0, g_fbLow = 0.0;
int g_fbLog = INVALID_HANDLE;

void FailedBreakoutLog(string event, uint retcode = 0, ulong order = 0)
{
   if(g_fbLog == INVALID_HANDLE) return;
   FileWrite(g_fbLog, TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS), event,
             TimeToString(g_fbSignal, TIME_DATE|TIME_SECONDS),
             TimeToString(g_fbBar, TIME_DATE|TIME_SECONDS),
             DoubleToString(g_fbHigh, _Digits), DoubleToString(g_fbLow, _Digits),
             DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_BID), _Digits), retcode, order);
}

void TryFailedBreakout()
{
   if(!UseFailedBreakout || !g_fbWatching) return;
   // Never observe a later candle's high to qualify the immediate next candle.
   if(iTime(_Symbol, _Period, 0) != g_fbBar) return;
   if(PositionSelect(_Symbol)) { g_fbWatching = false; return; }
   if(SymbolInfoDouble(_Symbol, SYMBOL_BID) <= g_fbHigh) return;
   // One submission attempt per signal, including a rejected order. No rearming
   // after a fill, stop-out, or another crossing inside this candle.
   g_fbWatching = false;
   MqlTradeRequest req = {};
   MqlTradeResult res = {};
   req.action = TRADE_ACTION_PENDING;
   req.symbol = _Symbol;
   req.volume = Lots;
   req.type = ORDER_TYPE_SELL_STOP;
   req.price = g_fbLow;
   req.sl = g_fbHigh;
   req.deviation = Slippage;
   req.type_filling = ORDER_FILLING_RETURN;
   bool sent = OrderSend(req, res);
   FailedBreakoutLog(sent && (res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)
                     ? "armed" : "rejected", res.retcode, res.order);
}
'''


def build_source():
    source = (BASE / 'GG_red_outside_short.mq5').read_text(encoding='utf-8')
    source = '// Tester-only RTL red-signal failed-breakout short, 2026-11-05.\n' + source
    source = once(source, '// ======== HELPER FUNCTIONS ========', EXTENSION + '\n// ======== HELPER FUNCTIONS ========')
    source = once(source, 'int OnInit()\n{', '''int OnInit()
{
   if(!MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;
   if(_Period != PERIOD_M30) return INIT_PARAMETERS_INCORRECT;
   g_fbLog = FileOpen("failed_breakout_" + RunTag + ".csv", FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, '\t');
   if(g_fbLog == INVALID_HANDLE) return INIT_FAILED;
   FileWrite(g_fbLog, "time", "event", "signal_bar", "watch_bar", "signal_high", "signal_low", "bid", "retcode", "order");''')
    source = once(source, '   if(barOpen == lastBar) return;\n   lastBar = barOpen;', '''   if(barOpen == lastBar)
   {
      TryFailedBreakout();
      return;
   }
   lastBar = barOpen;
   // At a new bar, expire only the unarmed high-break watcher. An already
   // submitted sell stop retains the inherited pending-order lifetime.
   if(UseFailedBreakout && g_fbWatching)
   {
      FailedBreakoutLog("expired");
      g_fbWatching = false;
   }''')
    source = once(source, '\t   TakeResearchSnapshot();\n\n\t   MqlTradeRequest req = {};', '''\t   TakeResearchSnapshot();

       if(UseFailedBreakout)
       {
          g_fbWatching = true;
          g_fbSignal = iTime(_Symbol, _Period, 1);
          g_fbBar = barOpen;
          g_fbHigh = h1;
          g_fbLow = l1;
          FailedBreakoutLog("watch");
          TryFailedBreakout(); // A gap above the high at this first tick qualifies.
          return;
       }

\t   MqlTradeRequest req = {};''')
    source += '\nvoid OnDeinit(const int reason)\n{\n   if(g_fbLog != INVALID_HANDLE) FileClose(g_fbLog);\n}\n'
    return source


def prepare():
    assert PROTOCOL.exists(), 'Freeze protocol before preparing outcomes'
    RUN.mkdir(parents=True, exist_ok=True)
    if (RUN / 'manifest.json').exists():
        raise RuntimeError('Preserve prepared study')
    source = build_source()
    (ROOT / f'mt5/experts/shorts/{EXPERT}.cs').write_text(source, encoding='utf-8')
    (RUN / f'{EXPERT}.mq5').write_text(source, encoding='utf-8')
    shutil.copyfile(BASE / 'early_closes.mqh', RUN / 'early_closes.mqh')
    template = (BASE / 'ggredshort_20261021_control.ini').read_text(encoding='utf-16').splitlines()
    jobs = []
    for enabled in (False, True):
        variant = 'on' if enabled else 'off'
        tag = TAG + '_' + variant
        changes = {'Expert': f'CodexFailedBreakoutShort\\{EXPERT}.ex5', 'Report': tag + '.htm', 'RunTag': tag}
        lines = [k+'='+changes[k] if (k := x.split('=', 1)[0]) in changes else x for x in template]
        at = lines.index('[TesterInputs]') + 1
        extras = dict(UseFailedBreakout=str(enabled).lower(), OutsideLookback='3',
                      MinOutsideRangeRatio='1.25', MinOutsideOverhangFraction='0.0')
        lines[at:at] = [f'{k}={v}' for k, v in extras.items()]
        end = next(i for i in range(at, len(lines)) if lines[i].startswith('['))
        supplied = [x.split('=', 1)[0] for x in lines[at:end] if '=' in x]
        inputs = re.findall(r'^input\s+\w+\s+(\w+)\s*=', source, re.M)
        assert sorted(supplied) == sorted(inputs) and len(supplied) == len(set(supplied)), set(inputs) ^ set(supplied)
        (RUN / (tag + '.ini')).write_text('\n'.join(lines) + '\n', encoding='utf-16')
        jobs.append(dict(tag=tag, variant=variant, enabled=enabled, outputs=[f'runband_{tag}_1.00.csv',
                         f'runband_{tag}_1.00_stats.csv', f'failed_breakout_{tag}.csv']))
    frozen = [PROTOCOL, Path(__file__), BASE / 'GG_red_outside_short.mq5',
              BASE / 'ggredshort_20261021_control.ini', BASE / 'ggredshort_20261021_control.htm',
              BASE / 'runband_ggredshort_20261021_control_1.00.csv',
              BASE / 'runband_ggredshort_20261021_control_1.00_stats.csv']
    save_json(RUN / 'manifest.json', dict(expert=EXPERT, jobs=jobs, cost_per_trade=1.05,
              price_offsets=0, symbol='MNQcontDTBNT20102026_2',
              input_hashes={str(p): digest(p) for p in frozen},
              prepared_sha256={p.name: digest(p) for p in RUN.iterdir() if p.suffix in ('.mq5', '.mqh', '.ini')}))
    print('Prepared frozen failed-breakout OFF/ON short jobs', flush=True)


def compile():
    log = RUN / 'compile.log'
    process = hidden_process([str(INSTALL / 'MetaEditor64.exe'), '/compile:' + str(RUN / (EXPERT + '.mq5')),
                              '/log:' + str(log)], timeout=180)
    result = log.read_text(encoding='utf-16', errors='replace')
    assert 'Result: 0 errors, 0 warnings' in result, result[-2000:]
    save_json(RUN / 'compile.completed.json', dict(**process, binary_sha256=digest(RUN / (EXPERT + '.ex5')),
              inputs_sha256={p.name: digest(p) for p in RUN.iterdir() if p.suffix in ('.mq5', '.mqh')}))
    print('Compiled failed-breakout EA: 0 errors, 0 warnings', flush=True)


if __name__ == '__main__':
    {'prepare': prepare, 'compile': compile}[sys.argv[1]]()
