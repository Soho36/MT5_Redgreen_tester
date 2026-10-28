"""Compile/run the two frozen hybrid-exit jobs in the installed historical MT5 tester.
Refuses to launch while any MT5 terminal is already running. Uses no live trading.
"""
import argparse
import json
import shutil
import subprocess
from pathlib import Path
from prepare_rtl_intrabar_tp import RUN, EXPERT
from run_mt5_job import INSTALL_DIR, DATA, COMMON, trim_log, AGENT_LOGS
from run_rtl_vwap_replay import hidden_process, digest
from datetime import datetime

FOLDER='CodexExitResearch'


def load_manifest():
    m=json.loads((RUN/'manifest.json').read_text(encoding='utf-8'))
    for name, expected in m['input_hashes'].items():
        assert digest(Path(name))==expected, name
    return m


def no_terminal():
    result=subprocess.run(['tasklist','/FI','IMAGENAME eq terminal64.exe','/FO','CSV','/NH'],
                          capture_output=True,text=True,check=True)
    if 'terminal64.exe' in result.stdout.lower():
        raise RuntimeError('Existing MT5 terminal is running; preserve the active session')


def compile_expert():
    load_manifest()
    source=RUN/(EXPERT+'.mq5')
    log=RUN/'compile.log'
    result=hidden_process([str(INSTALL_DIR/'MetaEditor64.exe'),'/compile:'+str(source),'/log:'+str(log)],timeout=180)
    lines=log.read_text(encoding='utf-16',errors='replace').splitlines()
    outcome=[x for x in lines if 'result' in x.lower()]
    assert outcome and '0 errors, 0 warnings' in outcome[-1], outcome
    binary=RUN/(EXPERT+'.ex5')
    record=dict(**result,result=outcome[-1],binary_sha256=digest(binary))
    (RUN/'compile.completed.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(outcome[-1],flush=True)


def run(tag):
    m=load_manifest()
    job=next(j for j in m['jobs'] if j['tag']==tag)
    marker=RUN/(tag+'.completed.json')
    if marker.exists():
        record=json.loads(marker.read_text(encoding='utf-8'))
        assert all(digest(RUN/n)==h for n,h in record['outputs'].items())
        print('Verified existing completed run',tag,flush=True)
        return
    no_terminal()
    compiled=json.loads((RUN/'compile.completed.json').read_text(encoding='utf-8'))
    binary=RUN/(EXPERT+'.ex5')
    assert digest(binary)==compiled['binary_sha256']
    target=DATA/'MQL5/Experts'/FOLDER/binary.name
    if target.exists():
        assert digest(target)==digest(binary), 'Preserve differing existing EA'
    else:
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(binary,target)
    lines=(RUN/(tag+'.ini')).read_text(encoding='utf-16').splitlines()
    for setting in ('Model=1','Optimization=0','UseRemote=0','UseCloud=0','AllowLiveTrading=0','Enabled=0','ShutdownTerminal=1'):
        assert setting in lines, setting
    lines=[f'Expert={FOLDER}\\{EXPERT}.ex5' if x.startswith('Expert=') else x for x in lines]
    runtime=RUN/'.mt5_runtime'; runtime.mkdir(exist_ok=True)
    config=runtime/(tag+'.ini'); config.write_text('\n'.join(lines)+'\n',encoding='utf-16')
    for name in job['outputs']:
        assert not (COMMON/name).exists() and not (RUN/name).exists(), 'Preserve previous output: '+name
    print('Starting historical tester',tag,flush=True)
    result=hidden_process([str(INSTALL_DIR/'terminal64.exe'),'/config:'+str(config)],timeout=600)
    assert result['returncode']==0, result
    for name in job['outputs']:
        assert (COMMON/name).exists(), 'Missing output: '+name
        shutil.copyfile(COMMON/name,RUN/name)
    reports=[DATA/(tag+'.htm'),INSTALL_DIR/(tag+'.htm')]
    report=next((p for p in reports if p.exists()),None)
    if report:
        shutil.copyfile(report,RUN/report.name)
    day=datetime.now().strftime('%Y%m%d')
    for source,suffix in [(DATA/'Tester/logs'/(day+'.log'),'tester'),(AGENT_LOGS/(day+'.log'),'agent')]:
        if source.exists():
            trim_log(source,RUN/(tag+'.'+suffix+'.log'),EXPERT)
    record=dict(tag=tag,**result,outputs={n:digest(RUN/n) for n in job['outputs']},
                binary_sha256=digest(binary),config_sha256=digest(config),
                mode='installed historical tester; no preexisting terminal',live_trading=False,report_present=bool(report))
    marker.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print('Completed',tag,flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['compile','run'])
    p.add_argument('tag',nargs='?')
    a=p.parse_args()
    if a.action=='compile': compile_expert()
    else:
        assert a.tag, 'Specify a frozen job tag'
        run(a.tag)


if __name__=='__main__':
    main()
