"""Prepare the MT5 checks of the VWAP gate EA (2026-10-28).

mt5/experts/RR_r_MFE_buy-stop-entry_vwap.cs (renamed RR_GG_r_MFE_buy-stop-entry_vwap.cs on
2026-10-30, when it gained the green signal candle; this recorded run keeps the old name) either computes session VWAP and A20 from 1-minute
bars or reads precomputed labels from a file. The replay run (Reports/rtl_vwap_replay_20261026,
gate ON) read the Python labels. Two tester jobs on NQ with the replay ON settings, decision log on:
  bars - VWAP computed in the tester. The tester rebuilds 1-minute bars with synthetic volume
         (a first run, Reports/rtl_vwap_ea_20261028_firstrun, found equal weights), so this
         checks the session, anchor and A20 logic against an equal-weight VWAP.
  file - labels from the replay's feature file: must reproduce the replay ON run exactly.
Plus StoredVwapCheck.mq5, a script for the normal terminal (stored bars, real volume) that
computes the include's VWAP and A20 for September 2026; they must equal the study's.
Every EA input is written to the INIs: the tester reuses the last value of a missing input.
Run: python/run_mt5_job.py Reports/rtl_vwap_ea_20261028 RR_r_MFE_buy-stop-entry_vwap
     then python/verify_rtl_vwap_ea.py (runs the stored-bar script first, MT5 closed).
"""
import hashlib
import json
import re
import shutil

from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / 'Reports' / 'rtl_vwap_ea_20261028'
REPLAY = ROOT / 'Reports' / 'rtl_vwap_replay_20261026'
EXPERTS = ROOT / 'mt5' / 'experts'
EXPERT = 'RR_r_MFE_buy-stop-entry_vwap'
SYMBOL = 'MNQcontDTBNT20102026_2'
FEATURES = 'rtl_vwap_replay_20261026_features.csv'
INCLUDES = ('early_closes.mqh', 'stock_early_closes.mqh', 'rtl_session_vwap.mqh')
JOBS = {'bars': '', 'file': FEATURES}
STORED_FROM, STORED_TO = '2026.09.01 00:00', '2026.09.30 23:30'

STORED_SCRIPT = r'''#property strict
// Read-only check: the EA's VWAP and A20 functions on stored bars (real volume), outside the
// tester. One row per M30 bar of the symbol from FROM to TO. No trading functions.
#include "rtl_session_vwap.mqh"
string SYMBOL = "__SYMBOL__";
string FROM = "__FROM__", TO = "__TO__";

void OnStart()
{
   int f = FileOpen("vwap_stored_check.tsv", FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, '\t');
   if(f == INVALID_HANDLE) { Print("open failed"); return; }
   FileWrite(f, "bar", "close", "vwap_ok", "vwap", "a20_ok", "a20");
   MqlRates r[];
   int n = -1;
   for(int attempt = 0; attempt < 120 && n <= 0; attempt++)
   { n = CopyRates(SYMBOL, PERIOD_M30, StringToTime(FROM), StringToTime(TO), r); if(n <= 0) Sleep(250); }
   for(int i = 0; i < n; i++)
   {
      double vwap = 0.0, a20 = 0.0;
      bool okV = RtlSessionVwap(SYMBOL, r[i].time, 0, 0, VWAP_VOLUME_AUTO, vwap);
      int shift = iBarShift(SYMBOL, PERIOD_M30, r[i].time, true);
      bool okA = shift >= 0 && RtlA20(SYMBOL, shift, a20);
      FileWrite(f, TimeToString(r[i].time, TIME_DATE|TIME_MINUTES), DoubleToString(r[i].close, 2), (int)okV,
                DoubleToString(vwap, 10), (int)okA, DoubleToString(a20, 10));
   }
   FileClose(f);
   int done = FileOpen("vwap_stored_check.done", FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(done != INVALID_HANDLE) { FileWriteString(done, IntegerToString(n) + "\n"); FileClose(done); }
}
'''


def tester_ini(tag, label_file):
    lines = (REPLAY / 'vwap_replay_20261026_on.ini').read_text(encoding='utf-16').splitlines()
    lines = [x for x in lines if not x.startswith(('UseVwapReplayGate=', 'VwapReplayFeatures='))]
    for key, value in {'Expert': f'CodexResearch\\{EXPERT}.ex5', 'Report': f'{tag}.htm', 'RunTag': tag}.items():
        assert sum(x.startswith(key + '=') for x in lines) == 1, key
        lines = [f'{key}={value}' if x.startswith(key + '=') else x for x in lines]
    new = {'ServerClock': '0', 'EarlyCloseSet': '0', 'UseVwapGate': 'true', 'VwapFarBelowZ': '-1.0',
           'VwapAnchorMinute': '0', 'VwapVolume': '0', 'VwapLabelFile': label_file, 'LogVwapDecisions': 'true',
           'NotionalPerTrade': '0.0'}
    at = lines.index('[TesterInputs]') + 1
    lines[at:at] = [f'{k}={v}' for k, v in new.items()]
    end = next(i for i in range(at, len(lines)) if lines[i].startswith('['))
    given = [x.split('=', 1)[0] for x in lines[at:end] if '=' in x]
    inputs = re.findall(r'^input\s+\w+\s+(\w+)\s*=', (EXPERTS / f'{EXPERT}.cs').read_text(encoding='utf-8'), re.MULTILINE)
    assert sorted(given) == sorted(inputs) and len(inputs) == 55, set(inputs) ^ set(given)
    return '\n'.join(lines) + '\n'


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    if (STUDY / 'manifest.json').exists():
        raise RuntimeError('Prepared study already exists; preserve it')
    shutil.copyfile(EXPERTS / f'{EXPERT}.cs', STUDY / f'{EXPERT}.mq5')
    for name in INCLUDES:
        shutil.copyfile(EXPERTS / name, STUDY / name)
    assert (EXPERTS / 'early_closes.mqh').read_bytes() == (REPLAY / 'early_closes.mqh').read_bytes()
    shutil.copyfile(REPLAY / FEATURES, STUDY / FEATURES)
    jobs = []
    for variant, label_file in JOBS.items():
        tag = f'vwapea_20261028_{variant}'
        (STUDY / f'{tag}.ini').write_text(tester_ini(tag, label_file), encoding='utf-16')
        jobs.append({'tag': tag, 'expert': EXPERT, 'vwap_source': label_file or 'computed',
                     'outputs': [f'rtlvwap_{tag}_1.00.csv', f'rtlvwap_{tag}_1.00_stats.csv', f'vwap_decisions_{tag}.csv'],
                     'inputs_files': [FEATURES] if label_file else []})
    (STUDY / 'StoredVwapCheck.mq5').write_text(
        STORED_SCRIPT.replace('__SYMBOL__', SYMBOL).replace('__FROM__', STORED_FROM).replace('__TO__', STORED_TO),
        encoding='utf-8')
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in STUDY.iterdir()
              if p.is_file() and p.suffix in ('.mq5', '.mqh', '.ini', '.csv')}
    manifest = {'symbol': SYMBOL, 'model': '1-minute OHLC', 'reference': str(REPLAY.relative_to(ROOT)),
                'purpose': 'VWAP gate EA: file labels must reproduce the replay ON run; computed labels '
                           'checked in the tester (equal weights) and on stored bars (real volume)',
                'stored_check': dict(script='StoredVwapCheck.mq5', bars_from=STORED_FROM, bars_to=STORED_TO),
                'prepared_sha256': hashes, 'jobs': jobs}
    (STUDY / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Prepared {len(jobs)} jobs and the stored-bar script in {STUDY}')


if __name__ == '__main__':
    main()
