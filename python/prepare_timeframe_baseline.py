"""Matched RTL/GG M30/H1 baselines; no run cap, RR 0.5/1, 2026-10-15.
H1 research copies enforce the existing session cutoff on ticks so the
half-hour cutoff cannot be skipped by the hourly new-bar gate.
"""
import hashlib
import json
import shutil
from prepare_instrument_baseline import make_ini, SYMBOLS
from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / 'Reports' / 'timeframe_baseline_20261015'
EXPERTS = {'RTL': 'RTL_timeframe', 'GG': 'GG_timeframe'}
SOURCES = {'RTL': 'RR_r_MFE_buy-stop-entry_runband.cs', 'GG': 'GG_r_MFE_buy-stop-entry_runband.cs'}
ANCHOR = '   if(barOpen == lastBar) return;\n'
CUTOFF = '''   // H1 must respect the same half-hour session cutoff as M30.
   // Use actual tester time; signals and target exits remain chart-bar based.
   if(PeriodSeconds(_Period) > 1800 && UseFlattenEnd && FlattenFallback)
   {
      datetime now = TimeCurrent();
      if(IsAtOrAfterFlattenTime(now))
      {
         datetime today = now - (now % 86400);
         if(g_lastFlattenDate != today)
         {
            g_lastFlattenDate = today;
            Print("H1 tick session cutoff -> closing everything");
            CloseAllPositions();
            CancelAllOrders();
         }
         return;
      }
   }

'''

def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    if (STUDY / 'manifest.json').exists():
        raise RuntimeError('Prepared study already exists; preserve it')
    shutil.copyfile(ROOT / 'mt5/experts/early_closes.mqh', STUDY / 'early_closes.mqh')
    jobs = []
    for strategy, expert in EXPERTS.items():
        source = ROOT / 'mt5/experts' / SOURCES[strategy]
        src = source.read_text(encoding='utf-8')
        assert src.count(ANCHOR) == 1
        (STUDY / f'{expert}.mq5').write_text(src.replace(ANCHOR, CUTOFF + ANCHOR), encoding='utf-8')
        for timeframe in ('M30', 'H1'):
            for rr in (0.5, 1.0):
                tag = f'tf_20261015_{strategy.lower()}_{timeframe.lower()}_rr{rr:.1f}'.replace('.', 'p')
                ini = make_ini(tag, SYMBOLS['mnq'])
                changes = {'Expert': f'CodexResearch\\{expert}.ex5', 'Period': timeframe,
                           'ToDate': '2026.10.15', 'MaxRedRun': '0', 'RiskReward': str(rr)}
                for key, value in changes.items():
                    lines = ini.splitlines()
                    assert sum(x.startswith(key + '=') for x in lines) == 1
                    ini = '\n'.join(f'{key}={value}' if x.startswith(key + '=') else x for x in lines) + '\n'
                (STUDY / f'{tag}.ini').write_text(ini, encoding='utf-16')
                jobs.append({'tag': tag, 'strategy': strategy, 'expert': expert, 'timeframe': timeframe, 'rr': rr,
                             'outputs': [f'runband_{tag}_{rr:.2f}.csv', f'runband_{tag}_{rr:.2f}_stats.csv']})
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in STUDY.iterdir() if p.is_file()}
    manifest = {'symbol': SYMBOLS['mnq'], 'from': '2010.06.07', 'to': '2026.10.15',
                'data_end': '2026.10.01', 'model': '1-minute OHLC', 'cost_per_trade': 1.05,
                'max_red_run': 0, 'h1_session_fix': 'tick cutoff at unchanged calendar times',
                'prepared_sha256': hashes, 'jobs': jobs}
    (STUDY / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Prepared {len(jobs)} matched jobs: {STUDY}')

if __name__ == '__main__':
    main()
