"""Prepare and run the frozen native MT5 RTL-short VWAP experiment.

Usage: prepare | compile. Then run_rtl_short_vwap_native.py off | on.
OFF must be verified before ON; no portable account context is required.
"""
from pathlib import Path
import json
import re
import shutil
import sys
import run_rtl_vwap_replay as runner
from project_paths import PROJECT_ROOT as ROOT

RUN = ROOT / 'Reports/rtl_short_vwap_20261031'
BASE = ROOT / 'Reports/ym_baselines_20261023'
PROTOCOL = ROOT / 'docs/baseline/rtl-vwap/SHORT_PROTOCOL.md'
EXPERT = 'RTL_short_vwap'
FEATURES = 'rtl_vwap_replay_20261026_features.csv'
TAG = 'rtlshortvwap_20261031'

GATE = r'''
#include "rtl_session_vwap.mqh"
input bool UseVwapGate = true;
enum VWAP_FILTER_LINE
{
   VWAP_FILTER_ORANGE = 0,  // Orange cutoff: VWAP + VwapFarBelowZ x A20
   VWAP_FILTER_BLUE = 1     // Blue line: session VWAP
};
input VWAP_FILTER_LINE VwapFilterLine = VWAP_FILTER_ORANGE;
input double VwapFarBelowZ = -1.0;
input string VwapLabelFile = "";
input bool LogVwapDecisions = true;
int g_shortVwapLog = INVALID_HANDLE;

// Same blue VWAP and orange VWAP + Z*A20 lines; only eligibility reverses.
// Unknown cannot qualify: the long gate allows unknown, so its complement does not.
bool ShortVwapAllows(datetime barOpen, double close1)
{
   if(!UseVwapGate && !LogVwapDecisions) return true;
   datetime sig = iTime(_Symbol, _Period, 1);
   datetime now = TimeCurrent(), date = now - now % 86400;
   double vwap = 0.0, a20 = 0.0;
   bool known = false;
   if(VwapLabelFile != "")
   {
      int j = RtlVwapFileRow(now);
      known = j >= 0 && g_rvKnown[j] && g_rvSession[j] == date;
      if(known && (g_rvBar[j] != sig || MathAbs(g_rvClose[j] - close1) > _Point))
      { Print("Short VWAP file mismatch; stopping"); ExpertRemove(); return false; }
      if(known) { vwap = g_rvVwap[j]; a20 = g_rvA20[j]; }
   }
   else
      known = (sig - sig % 86400 == date)
              && RtlSessionVwap(_Symbol, sig, 0, 0, VWAP_VOLUME_AUTO, vwap)
              && RtlA20(_Symbol, 1, a20);
   double cutoff = vwap + (VwapFilterLine == VWAP_FILTER_BLUE ? 0.0 : VwapFarBelowZ) * a20;
   bool eligible = known && close1 < cutoff;
   bool allowed = !UseVwapGate || eligible;
   if(g_shortVwapLog != INVALID_HANDLE)
      FileWrite(g_shortVwapLog, TimeToString(barOpen, TIME_DATE|TIME_SECONDS),
                TimeToString(sig, TIME_DATE|TIME_SECONDS), DoubleToString(close1, _Digits),
                (int)known, DoubleToString(vwap, 12), DoubleToString(a20, 12),
                DoubleToString(cutoff, 12), (int)eligible, (int)allowed, (int)VwapFilterLine);
   return allowed;
}
'''


def build_source():
    source = (BASE / 'GG_outside_short.mq5').read_text(encoding='utf-8')
    source = '// RTL-short VWAP experiment, 2026-10-31. Green signal / sell stop.\n' + source
    source = source.replace('#property strict', '#property strict\n' + GATE, 1)
    hook = 'int OnInit()\n{'
    assert source.count(hook) == 1
    source = source.replace(hook, hook + r'''
   if(!MQLInfoInteger(MQL_TESTER)) return INIT_FAILED; // Research tester only.
   if(_Period != PERIOD_M30 || !MathIsValidNumber(VwapFarBelowZ)
      || (VwapFilterLine != VWAP_FILTER_ORANGE && VwapFilterLine != VWAP_FILTER_BLUE)) return INIT_PARAMETERS_INCORRECT;
   if(VwapLabelFile != "" && (UseVwapGate || LogVwapDecisions))
      if(!RtlVwapFileLoad(VwapLabelFile)) return INIT_FAILED;
   // Historical tests require real-volume labels, never synthetic tester volume.
   if(UseVwapGate && MQLInfoInteger(MQL_TESTER) && VwapLabelFile == "") return INIT_PARAMETERS_INCORRECT;
   if(LogVwapDecisions)
   {
      g_shortVwapLog = FileOpen("short_vwap_" + RunTag + ".csv", FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, '\t');
      if(g_shortVwapLog == INVALID_HANDLE) return INIT_FAILED;
      FileWrite(g_shortVwapLog, "time", "signal_bar", "signal_close", "known", "vwap", "a20", "cutoff", "eligible", "allowed", "filter_line");
   }
''', 1)
    hook = '\t   double entry = l1;'
    assert source.count(hook) == 1
    source = source.replace(hook, '\t   if(!ShortVwapAllows(barOpen, c1)) return;\n\n' + hook)
    source += '\nvoid OnDeinit(const int reason)\n{\n   if(g_shortVwapLog != INVALID_HANDLE) FileClose(g_shortVwapLog);\n}\n'
    return source


def prepare():
    if (RUN / 'manifest.json').exists():
        raise RuntimeError('Preserve prepared study')
    RUN.mkdir(parents=True, exist_ok=True)
    source = build_source()
    (ROOT / f'mt5/experts/shorts/{EXPERT}.cs').write_text(source, encoding='utf-8')
    (RUN / f'{EXPERT}.mq5').write_text(source, encoding='utf-8')
    for name in ('early_closes.mqh', 'rtl_session_vwap.mqh'):
        shutil.copyfile(ROOT / 'mt5/experts' / name, RUN / name)
    shutil.copyfile(ROOT / 'Reports/rtl_vwap_replay_20261026' / FEATURES, RUN / FEATURES)
    template = (BASE / 'ymbase_20261023_rtl_short_nq.ini').read_text(encoding='utf-16').splitlines()
    jobs = []
    for enabled in (False, True):
        variant = 'on' if enabled else 'off'
        tag = TAG + '_' + variant
        changes = {'Expert': f'CodexShortVwap\\{EXPERT}.ex5', 'Report': tag + '.htm', 'RunTag': tag}
        lines = [k+'='+changes[k] if (k := x.split('=', 1)[0]) in changes else x for x in template]
        extras = dict(UseVwapGate=str(enabled).lower(), VwapFilterLine='0', VwapFarBelowZ='-1.0',
                      VwapLabelFile=FEATURES, LogVwapDecisions='true', OutsideLookback='3',
                      MinOutsideRangeRatio='1.25', MinOutsideOverhangFraction='0.0')
        at = lines.index('[TesterInputs]') + 1
        lines[at:at] = [f'{k}={v}' for k, v in extras.items()]
        end = next(i for i in range(at, len(lines)) if lines[i].startswith('['))
        supplied = [x.split('=', 1)[0] for x in lines[at:end] if '=' in x]
        inputs = re.findall(r'^input\s+\w+\s+(\w+)\s*=', source, re.M)
        assert sorted(supplied) == sorted(inputs) and len(supplied) == len(set(supplied)), set(inputs) ^ set(supplied)
        (RUN / (tag+'.ini')).write_text('\n'.join(lines)+'\n', encoding='utf-16')
        jobs.append(dict(tag=tag, gate=enabled, outputs=[f'runband_{tag}_1.00.csv', f'runband_{tag}_1.00_stats.csv',
                        f'short_vwap_{tag}.csv'], inputs_files=[FEATURES]))
    frozen = [PROTOCOL, Path(__file__), BASE/'GG_outside_short.mq5',
              BASE/'ymbase_20261023_rtl_short_nq.ini', BASE/'ymbase_20261023_rtl_short_nq.htm',
              BASE/'runband_ymbase_20261023_rtl_short_nq_1.00.csv',
              BASE/'runband_ymbase_20261023_rtl_short_nq_1.00_stats.csv']
    manifest = dict(expert=EXPERT, jobs=jobs, symbol=runner.SYMBOL, cost_per_trade=1.05,
                    gate='known and completed_signal_close < full_session_VWAP - arithmetic_A20',
                    input_hashes={str(p):runner.digest(p) for p in frozen},
                    prepared_sha256={p.name:runner.digest(p) for p in RUN.iterdir() if p.suffix in ('.mq5','.mqh','.csv','.ini')})
    runner.save_json(RUN/'manifest.json', manifest)
    print('Prepared frozen OFF/ON short jobs', flush=True)


def main():
    action = sys.argv[1]
    if action == 'prepare':
        prepare()
    elif action == 'compile':
        log = RUN/'compile_native.log'
        runner.hidden_process([str(runner.INSTALL/'MetaEditor64.exe'),
            '/compile:'+str(RUN/(EXPERT+'.mq5')), '/log:'+str(log)], timeout=180)
        result = log.read_text(encoding='utf-16', errors='replace')
        assert 'Result: 0 errors, 0 warnings' in result, result[-2000:]
        frozen = [PROTOCOL, ROOT/'python/run_rtl_short_vwap_native.py',
                  ROOT/'python/analyze_rtl_short_vwap.py', RUN/(EXPERT+'.mq5'),
                  RUN/(EXPERT+'.ex5'), RUN/FEATURES, RUN/(TAG+'_off.ini'),
                  RUN/(TAG+'_on.ini'), BASE/'ymbase_20261023_rtl_short_nq.htm']
        freeze = RUN/'native_input_manifest.json'
        if freeze.exists():
            # Preserve a completed study's frozen provenance when only recompiling.
            old = json.loads(freeze.read_text(encoding='utf-8'))
            assert all(runner.digest(path)==expected for path,expected in old['input_hashes'].items())
        else:
            runner.save_json(freeze, dict(protocol='Frozen threshold; require native OFF identical before ON',
                input_hashes={str(path):runner.digest(path) for path in frozen}))
        print('Compiled: 0 errors, 0 warnings; native inputs frozen', flush=True)
    else:
        raise ValueError('Use prepare or compile; native runs use run_rtl_short_vwap_native.py')


if __name__ == '__main__':
    main()
