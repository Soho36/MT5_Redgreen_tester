"""Prepare the frozen baseline and hybrid 1R-close/2R-touch MT5 experiment."""
import hashlib
import json
import shutil
from project_paths import PROJECT_ROOT as ROOT

RUN = ROOT / 'Reports/rtl_intrabar_tp_20261027'
BASE = ROOT / 'Reports/timeframe_baseline_20261015'
PROTOCOL = ROOT / 'docs/baseline/rtl-intrabar-tp/PROTOCOL.md'
EXPERT = 'RTL_intrabar_tp'
SOURCE_SHA = '8995d0ed6f97f21b15f4ce31f862fb8f642a1eae5a4e28c6bc371cb928165810'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build_source():
    src = BASE / 'RTL_timeframe.mq5'
    assert sha(src) == SOURCE_SHA
    s = src.read_text(encoding='utf-8')
    edits = [
        ('input double RiskReward     = 1.0;',
         'input double RiskReward     = 1.0;\ninput double IntrabarTakeProfitR = 2.0; // 0 disables the resting TP; candle-close RR remains active'),
        ('int OnInit()\n{', 'int OnInit()\n{\n   if(!MQLInfoInteger(MQL_TESTER)) return INIT_FAILED; // research tester only\n   if(!MathIsValidNumber(IntrabarTakeProfitR) || IntrabarTakeProfitR < 0.0) return INIT_PARAMETERS_INCORRECT;'),
        ('\t   req.sl           = stop;\n',
         '\t   req.sl           = stop;\n'
         '\t   if(IntrabarTakeProfitR > 0.0)\n'
         '\t   {\n'
         '\t      double tick = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);\n'
         '\t      if(tick <= 0.0) tick = _Point;\n'
         '\t      req.tp = NormalizeDouble(MathCeil((entry + risk * IntrabarTakeProfitR) / tick - 1e-9) * tick, _Digits);\n'
         '\t   }\n'),
    ]
    for old, new in edits:
        assert s.count(old) == 1, repr(old)
        s = s.replace(old, new)
    # The existing close-confirmed ManageOpenPosition() function is untouched.
    return s


def main():
    assert PROTOCOL.exists()
    RUN.mkdir(parents=True, exist_ok=True)
    assert not (RUN/'manifest.json').exists(), 'Preserve the prepared study'
    (RUN/f'{EXPERT}.mq5').write_text(build_source(), encoding='utf-8')
    shutil.copyfile(BASE/'early_closes.mqh', RUN/'early_closes.mqh')
    jobs = []
    for variant, target in [('baseline', 0.0), ('tp2r', 2.0)]:
        tag = f'intrabar_tp_20261027_{variant}'
        lines = (BASE/'tf_20261015_rtl_m30_rr1p0.ini').read_text(encoding='utf-16').splitlines()
        for key, value in {'Expert':f'CodexResearch\\{EXPERT}.ex5', 'RunTag':tag, 'Report':tag+'.htm'}.items():
            assert sum(x.startswith(key+'=') for x in lines) == 1
            lines = [key+'='+value if x.startswith(key+'=') else x for x in lines]
        lines.insert(lines.index('[TesterInputs]')+1, f'IntrabarTakeProfitR={target}')
        (RUN/(tag+'.ini')).write_text('\n'.join(lines)+'\n', encoding='utf-16')
        jobs.append(dict(tag=tag, variant=variant, intrabar_rr=target, outputs=[f'runband_{tag}_1.00.csv', f'runband_{tag}_1.00_stats.csv']))
    files = [PROTOCOL, ROOT/'python/rtl_weekly_engine.py', ROOT/'python/analyze_rtl_intrabar_tp.py',
             ROOT/'python/test_rtl_intrabar_tp.py', ROOT/'python/prepare_rtl_intrabar_tp.py', BASE/'RTL_timeframe.mq5',
             BASE/'tf_20261015_rtl_m30_rr1p0.ini', *RUN.glob('*.mq5'), *RUN.glob('*.mqh'), *RUN.glob('*.ini')]
    manifest = dict(expert=EXPERT, jobs=jobs, symbol='MNQcontDTBNT20102026_2', pv=2.0,
                    model='1-minute OHLC', close_rr=1.0, cost=1.05,
                    input_hashes={str(p):sha(p) for p in files})
    (RUN/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n', encoding='utf-8')
    print('Prepared', RUN)


if __name__ == '__main__':
    main()
