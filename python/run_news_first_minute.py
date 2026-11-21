"""Prepare frozen inputs, compile, and run three native news-first-minute jobs."""
import json
import shutil
import subprocess
from pathlib import Path
import pandas as pd
from project_paths import PROJECT_ROOT as ROOT
from build_news_calendar import sha
from run_mt5_job import DATA,COMMON,INSTALL_DIR,compile_expert
from run_rtl_vwap_replay import hidden_process

RUN=ROOT/'Reports/news_first_minute_20261122'
DOC=ROOT/'docs/baseline/news-first-minute'
EXPERT='News_first_minute_research'
CAL=ROOT/'data/calendars/us_major_news_times_2010_2026.csv'

def main():
    check=subprocess.run(['powershell','-NoProfile','-Command','(Get-Process terminal64 -ErrorAction SilentlyContinue | Measure-Object).Count'],capture_output=True,text=True,check=True)
    assert check.stdout.strip()=='0','Existing terminal running; preserve it'
    manifest=RUN/'manifest.json'
    if not manifest.exists():
        events=pd.read_csv(CAL);events=events.loc[events.event.isin(['CPI','PAYROLLS']) & events.research_time.str.endswith('15:30:00')]
        flags=events.event.map({'CPI':1,'PAYROLLS':2}).groupby(events.date).sum()
        header='int NEWS_DATE[]={'+','.join(flags.index.str.replace('-',''))+'};\nint NEWS_FLAGS[]={'+','.join(map(str,flags))+'};\n'
        (RUN/'news_first_minute_dates.mqh').write_text(header)
        shutil.copyfile(ROOT/f'mt5/experts/{EXPERT}.mq5',RUN/(EXPERT+'.mq5'))
        shutil.copyfile(ROOT/'mt5/experts/early_closes.mqh',RUN/'early_closes.mqh')
        shutil.copyfile(ROOT/'Reports/rtl_news_windows_20261110/window_equity_research.mqh',RUN/'window_equity_research.mqh')
        jobs=[]
        for policy,mask in [('both',3),('cpi',1),('payrolls',2)]:
            tag='news1m_20261122_'+policy
            ini=f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=CodexResearch\\{EXPERT}.ex5
Symbol=MNQcontDTBNT20102026_2
Period=M1
Optimization=0
Model=1
FromDate=2010.06.07
ToDate=2026.10.01
Deposit=500000
Currency=USD
Leverage=100
ExecutionMode=0
Visual=0
UseLocal=1
UseRemote=0
UseCloud=0
ShutdownTerminal=1
Report={tag}.htm
ReplaceReport=1
[TesterInputs]
NewsMask={mask}
RunTag={tag}
'''
            (RUN/(tag+'.ini')).write_text(ini,encoding='utf-16')
            jobs.append(dict(tag=tag,policy=policy,mask=mask,outputs=[f'decisions_{tag}.csv',f'deals_{tag}.csv',f'stats_{tag}.csv',f'window_equity_{tag}.bin']))
        paths=[*RUN.glob('*.mq5'),*RUN.glob('*.mqh'),*RUN.glob('*.ini')]
        manifest.write_text(json.dumps(dict(jobs=jobs,calendar_sha256=sha(CAL),protocol_sha256=sha(DOC/'PROTOCOL.md'),prepared={p.name:sha(p) for p in paths}),indent=2))
    m=json.loads(manifest.read_text())
    assert sha(CAL)==m['calendar_sha256'] and sha(DOC/'PROTOCOL.md')==m['protocol_sha256']
    for n,h in m['prepared'].items():assert sha(RUN/n)==h
    compile_expert(RUN,EXPERT)
    for j in m['jobs']:
        tag=j['tag'];done=RUN/(tag+'.completed.json')
        if done.exists():
            record=json.loads(done.read_text());assert all(sha(RUN/n)==h for n,h in record['outputs'].items());continue
        assert all(not (COMMON/n).exists() for n in j['outputs'])
        print('Running',tag,flush=True)
        proc=hidden_process([str(INSTALL_DIR/'terminal64.exe'),'/config:'+str(RUN/(tag+'.ini'))],timeout=900,cwd=INSTALL_DIR)
        assert proc['returncode']==0
        for n in j['outputs']:shutil.copyfile(COMMON/n,RUN/n)
        shutil.copyfile(DATA/(tag+'.htm'),RUN/(tag+'.htm'))
        done.write_text(json.dumps(dict(**proc,outputs={n:sha(RUN/n) for n in j['outputs']},report_sha256=sha(RUN/(tag+'.htm'))),indent=2))
        print('Completed',tag,flush=True)

if __name__=='__main__':main()
