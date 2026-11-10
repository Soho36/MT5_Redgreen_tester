"""Run frozen tester-only window jobs. Preserve existing terminals and outputs."""
import json
import shutil
import subprocess
from collections import deque
from datetime import datetime
from prepare_rtl_news_windows import ROOT,RUN,DOC,BASE,TAG,EXPERT,TIME_CSV,WINDOW_CSV,sha
from run_rtl_vwap_replay import hidden_process
from run_mt5_job import INSTALL_DIR,DATA,COMMON,AGENT_LOGS,compile_expert
from mt5_expert_layout import runtime_tester_config

def main():
    check=subprocess.run(['powershell','-NoProfile','-Command',
        '(Get-Process terminal64 -ErrorAction SilentlyContinue | Measure-Object).Count'],capture_output=True,text=True,check=True)
    assert check.stdout.strip()=='0','Existing MT5 is running; do not terminate it'
    manifest=json.loads((RUN/'manifest.json').read_text())
    for path,key in ((DOC/'PROTOCOL.md','protocol_sha256'),(TIME_CSV,'calendar_sha256'),(WINDOW_CSV,'windows_sha256')):
        assert sha(path)==manifest[key]
    for name,value in manifest['prepared_sha256'].items():assert sha(RUN/name)==value,name
    compile_expert(RUN,EXPERT)
    for job in manifest['jobs']:
        tag=job['tag'];marker=RUN/(tag+'.completed.json')
        if marker.exists():
            done=json.loads(marker.read_text());assert all(sha(RUN/n)==h for n,h in done['outputs'].items())
            continue
        assert all(not (COMMON/n).exists() for n in job['outputs'])
        stamp=datetime.now().strftime('%Y%m%d')
        logs=[DATA/'Tester/logs'/(stamp+'.log'),AGENT_LOGS/(stamp+'.log')]
        offsets=[p.stat().st_size if p.exists() else 0 for p in logs]
        config=runtime_tester_config(RUN,tag,EXPERT)
        print('Running '+tag,flush=True)
        proc=hidden_process([str(INSTALL_DIR/'terminal64.exe'),'/config:'+str(config)],timeout=900,cwd=INSTALL_DIR)
        assert proc['returncode']==0,proc
        for name in job['outputs']:shutil.copyfile(COMMON/name,RUN/name)
        shutil.copyfile(DATA/(tag+'.htm'),RUN/(tag+'.htm'))
        for source,offset,suffix in zip(logs,offsets,['tester','agent']):
            if not source.exists():continue
            # Read only bytes appended by this pass; keep head/tail and all errors.
            head=[];tail=deque(maxlen=100);errors=[];n=0
            with source.open('rb') as f:
                f.seek(offset);text=f.read().decode('utf-16-le',errors='replace')
            for line in text.splitlines():
                n+=1
                if n<=100:head.append(line)
                else:tail.append(line)
                if 'NEWS_ACTION_ERROR' in line:errors.append(line)
            assert not errors,errors
            (RUN/(tag+'.'+suffix+'.log')).write_text('\n'.join(head+[f'... {max(0,n-200)} lines trimmed ...']+list(tail))+'\n',encoding='utf-8')
        if job['mode']==0:
            assert (RUN/job['outputs'][0]).read_bytes()==(BASE/f'rtlvwap_{TAG}_1.00.csv').read_bytes(),'Disabled control differs'
            print('Disabled control byte-identical',flush=True)
        done=dict(tag=tag,**proc,outputs={n:sha(RUN/n) for n in job['outputs']},report_sha256=sha(RUN/(tag+'.htm')),
                  expert_sha256=sha(RUN/(EXPERT+'.ex5')))
        marker.write_text(json.dumps(done,indent=2)+'\n',encoding='utf-8')
        print('Completed '+tag,flush=True)

if __name__=='__main__':main()
