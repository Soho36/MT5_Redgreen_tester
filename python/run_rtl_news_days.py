"""Run frozen tester-only news jobs; never terminate an existing terminal."""
import json
import shutil
import subprocess
from datetime import datetime
from prepare_rtl_news_days import ROOT,RUN,DOC,OUT,BASE,TAG,EXPERT,sha
from run_rtl_vwap_replay import hidden_process
from run_mt5_job import INSTALL_DIR,DATA,COMMON,AGENT_LOGS,compile_expert,trim_log
from mt5_expert_layout import runtime_tester_config

def main():
    check=subprocess.run(['powershell','-NoProfile','-Command',
        '(Get-Process terminal64 -ErrorAction SilentlyContinue | Measure-Object).Count'],
        capture_output=True,text=True,check=True)
    assert check.stdout.strip()=='0','Existing MT5 is running; do not terminate it'
    manifest=json.loads((RUN/'manifest.json').read_text())
    assert sha(DOC/'PROTOCOL.md')==manifest['protocol_sha256']
    assert sha(OUT/'us_major_news_2010_2026.csv')==manifest['calendar_sha256']
    for name,value in manifest['prepared_sha256'].items():assert sha(RUN/name)==value,name
    compile_expert(RUN,EXPERT)
    for job in manifest['jobs']:
        tag=job['tag'];marker=RUN/(tag+'.completed.json')
        if marker.exists():
            done=json.loads(marker.read_text())
            assert all(sha(RUN/n)==h for n,h in done['outputs'].items())
            continue
        assert all(not (COMMON/n).exists() for n in job['outputs'])
        config=runtime_tester_config(RUN,tag,EXPERT)
        print('Running '+tag,flush=True)
        proc=hidden_process([str(INSTALL_DIR/'terminal64.exe'),'/config:'+str(config)],timeout=900,cwd=INSTALL_DIR)
        assert proc['returncode']==0,proc
        for name in job['outputs']:shutil.copyfile(COMMON/name,RUN/name)
        shutil.copyfile(DATA/(tag+'.htm'),RUN/(tag+'.htm'))
        stamp=datetime.now().strftime('%Y%m%d')
        for source,suffix in ((DATA/'Tester/logs'/(stamp+'.log'),'tester'),(AGENT_LOGS/(stamp+'.log'),'agent')):
            if source.exists():trim_log(source,RUN/(tag+'.'+suffix+'.log'),EXPERT)
        if job['mask']==0:
            assert (RUN/job['outputs'][0]).read_bytes()==(BASE/f'rtlvwap_{TAG}_1.00.csv').read_bytes(),'Disabled control differs'
            print('Disabled control byte-identical',flush=True)
        done=dict(tag=tag,**proc,outputs={n:sha(RUN/n) for n in job['outputs']},report_sha256=sha(RUN/(tag+'.htm')),
                  expert_sha256=sha(RUN/(EXPERT+'.ex5')))
        marker.write_text(json.dumps(done,indent=2)+'\n',encoding='utf-8')
        print('Completed '+tag,flush=True)

if __name__=='__main__':main()
