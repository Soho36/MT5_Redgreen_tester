"""Compile/package the current EA; optionally verify all direction inputs in MT5."""
import argparse
import json
import re
import shutil
import subprocess
import zipfile
import pandas as pd
from run_news_first_minute import ROOT,EXPERT,RUN as ORIGINAL,sha
from run_mt5_job import compile_expert,INSTALL_DIR,DATA,COMMON
from run_rtl_vwap_replay import hidden_process

RUN=ROOT/'Reports/news_first_minute_direction_20261122'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    RUN.mkdir(parents=True,exist_ok=True)
    for name in [EXPERT+'.mq5','news_first_minute_dates.mqh','early_closes.mqh','window_equity_research.mqh']:
        shutil.copyfile(ROOT/'mt5/experts'/name,RUN/name)
    compile_expert(RUN,EXPERT)
    note='''News_first_minute_research: Strategy Tester Inputs
TradeDirection: Both longs and shorts (default, 0), Longs only (1), Shorts only (2).
NewsMask: 3=both CPI/payrolls, 1=CPI, 2=payrolls.
Use MNQcontDTBNT20102026_2, M1. Tester only, original research clock.
Direction-disabled signals are skipped, never inverted. Exits are unchanged.
Choose distinct RunTag values to retain each manual test's exported logs.
The original study runner uses its frozen EA; use this installer for the current EA.
'''
    (RUN/'README.txt').write_text(note,encoding='utf-8')
    with zipfile.ZipFile(RUN/'News_first_minute_EA.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in [*RUN.glob('*.mq5'),*RUN.glob('*.mqh'),*RUN.glob('*.ex5'),RUN/'README.txt']:z.write(p,p.name)
    if not args.verify:return
    check=subprocess.run(['powershell','-NoProfile','-Command','(Get-Process terminal64 -ErrorAction SilentlyContinue | Measure-Object).Count'],capture_output=True,text=True,check=True)
    assert check.stdout.strip()=='0','Existing terminal running; compiled and installed, but do not interrupt it for verification'
    original=pd.read_csv(ORIGINAL/'deals_news1m_20261122_both.csv',parse_dates=['time'])
    original=original.loc[original.time.ge('2024-01-01')&original.time.lt('2025-01-01')]
    checks=[]
    for mode,label in [(0,'both'),(1,'long'),(2,'short')]:
        tag='news1m_direction_20261122_'+label
        ini=(ORIGINAL/'news1m_20261122_both.ini').read_text(encoding='utf-16')
        for key,value in dict(FromDate='2024.01.01',ToDate='2025.01.01',RunTag=tag,Report=tag+'.htm').items():
            ini=re.sub('^'+key+'=.*$',lambda _:key+'='+value,ini,flags=re.M)
        ini=ini.replace('[TesterInputs]',f'[TesterInputs]\nTradeDirection={mode}')
        config=RUN/(tag+'.ini');config.write_text(ini,encoding='utf-16')
        names=[f'decisions_{tag}.csv',f'deals_{tag}.csv',f'stats_{tag}.csv',f'window_equity_{tag}.bin']
        assert not any((COMMON/n).exists() for n in names),'Preserve existing checks'
        print('Verifying',label,flush=True)
        proc=hidden_process([str(INSTALL_DIR/'terminal64.exe'),'/config:'+str(config)],timeout=300,cwd=INSTALL_DIR)
        assert proc['returncode']==0
        for n in names:shutil.copyfile(COMMON/n,RUN/n)
        shutil.copyfile(DATA/(tag+'.htm'),RUN/(tag+'.htm'))
        actual=pd.read_csv(RUN/f'deals_{tag}.csv',parse_dates=['time'])
        positions=original.loc[original.entry.eq(0)&(original.type.eq(mode-1) if mode else True),'position']
        expected=original.loc[original.position.isin(positions)]
        fields=['time','entry','type','price','volume','profit','commission','swap','reason','sl','tp']
        pd.testing.assert_frame_equal(actual[fields].reset_index(drop=True),expected[fields].reset_index(drop=True),check_exact=True)
        decisions=pd.read_csv(RUN/f'decisions_{tag}.csv')
        if mode:
            wrong=decisions.direction.eq(-1 if mode==1 else 1)
            assert decisions.loc[wrong,'status'].eq('direction_disabled').all()
        checks.append(dict(mode=label,trades=len(positions),exact_original_subset=True,
            blocked=int(decisions.status.eq('direction_disabled').sum()),outputs={n:sha(RUN/n) for n in names}))
    (RUN/'verification.json').write_text(json.dumps(dict(all_passed=True,checks=checks,source_sha256=sha(RUN/(EXPERT+'.mq5'))),indent=2))
    print(json.dumps(checks,indent=2))

if __name__=='__main__':main()
