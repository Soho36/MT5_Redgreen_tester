"""Install and run native MT5 orange/blue short tests; never close an active terminal."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import pandas as pd
from prepare_rtl_short_vwap_lines import RUN,PRIOR,PROTOCOL,EXPERT,FEATURES,TAG
from prepare_rtl_short_vwap import TAG as PRIOR_TAG
from run_rtl_vwap_replay import INSTALL,SOURCE_DATA,COMMON,digest,hidden_process,save_json


def checked_inputs():
    manifest=json.loads((RUN/'manifest.json').read_text())
    for path,expected in manifest['input_hashes'].items(): assert digest(path)==expected,path
    for name,expected in manifest['prepared_sha256'].items(): assert digest(RUN/name)==expected,name
    compile=json.loads((RUN/'compile.completed.json').read_text())
    assert digest(RUN/(EXPERT+'.ex5'))==compile['binary_sha256']
    return manifest


def install():
    checked_inputs()
    folder=SOURCE_DATA/'MQL5/Experts/CodexShortVwap'
    folder.mkdir(parents=True,exist_ok=True)
    target=folder/(EXPERT+'.ex5')
    binary=RUN/(EXPERT+'.ex5')
    if target.exists() and digest(target)!=digest(binary):
        assert digest(target)==digest(PRIOR/(EXPERT+'.ex5')),'Installed EA changed externally; preserve it'
        backup=RUN/'installed_previous.ex5'
        if not backup.exists(): shutil.copyfile(target,backup)
        else: assert digest(backup)==digest(target)
    shutil.copyfile(binary,target)
    for name in (EXPERT+'.mq5','early_closes.mqh','rtl_session_vwap.mqh'):
        shutil.copyfile(RUN/name,folder/name)
    shared=COMMON/FEATURES
    if shared.exists(): assert digest(shared)==digest(RUN/FEATURES)
    else: shutil.copyfile(RUN/FEATURES,shared)
    save_json(RUN/'installation.json',dict(binary=str(target),binary_sha256=digest(target),
        previous_preserved=(RUN/'installed_previous.ex5').exists(),chart_attachment=False,
        tester_only_guard=True,features_sha256=digest(shared)))
    print('Installed updated tester-only short EA with VwapFilterLine switch',flush=True)


def check_orange():
    new=RUN/f'runband_{TAG}_orange_1.00.csv'
    old=PRIOR/f'runband_{PRIOR_TAG}_on_1.00.csv'
    a=pd.read_csv(RUN/f'runband_{TAG}_orange_1.00_stats.csv',sep='\t',encoding='utf-16').iloc[0]
    b=pd.read_csv(PRIOR/f'runband_{PRIOR_TAG}_on_1.00_stats.csv',sep='\t',encoding='utf-16').iloc[0]
    totals={k:dict(new=float(a[k]),original=float(b[k])) for k in ('trades','net_profit','gross_profit','gross_loss','equity_dd','balance_dd')}
    passed=new.read_bytes()==old.read_bytes() and all(x['new']==x['original'] for x in totals.values())
    save_json(RUN/'orange_validation.json',dict(all_passed=passed,ledger_byte_identical=new.read_bytes()==old.read_bytes(),native_totals=totals))
    assert passed,totals
    print('Orange switch option exactly reproduces original ON ledger and native totals',flush=True)


def run(variant):
    manifest=checked_inputs()
    if variant=='blue': assert json.loads((RUN/'orange_validation.json').read_text())['all_passed']
    job=next(j for j in manifest['jobs'] if j['variant']==variant)
    tag=job['tag']
    assert not (RUN/(tag+'.completed.json')).exists(),'Preserve completed outputs'
    active=subprocess.run(['tasklist','/FI','IMAGENAME eq terminal64.exe','/FO','CSV','/NH'],capture_output=True,text=True)
    if 'terminal64.exe' in active.stdout.lower(): raise RuntimeError('MT5 is still open; preserve its work')
    install()
    config=RUN/(tag+'.ini')
    text=config.read_text(encoding='utf-16')
    for setting in ('UseRemote=0','UseCloud=0','Visual=0','ShutdownTerminal=1','AllowLiveTrading=0','Optimization=0'):
        assert setting in text.splitlines()
    assert not re.search(r'^(Login|Server|Password)=',text,re.M)
    for name in job['outputs']:
        assert not (COMMON/name).exists() and not (RUN/name).exists(),'Preserve output: '+name
    record=dict(tag=tag,variant=variant,filter_line=job['filter_line'],native_mt5=True,
        config_sha256=digest(config),expert_sha256=digest(RUN/(EXPERT+'.ex5')),
        live_trading_enabled=False,protocol_sha256=digest(PROTOCOL))
    save_json(RUN/(tag+'.started.json'),record)
    print('Running native '+variant+' cutoff test',flush=True)
    process=hidden_process([str(INSTALL/'terminal64.exe'),'/config:'+str(config)],timeout=900,cwd=INSTALL)
    assert process['returncode']==0,process
    for name in job['outputs']:
        assert (COMMON/name).exists(),name
        shutil.copyfile(COMMON/name,RUN/name)
    report=None
    for folder in (SOURCE_DATA,INSTALL):
        path=folder/(tag+'.htm')
        if path.exists():
            report=RUN/path.name
            shutil.copyfile(path,report)
            break
    assert report is not None,'Missing native report'
    record.update(process,outputs={name:digest(RUN/name) for name in job['outputs']},report_sha256=digest(report))
    save_json(RUN/(tag+'.completed.json'),record)
    if variant=='orange':check_orange()
    print('Completed native '+variant+' test',flush=True)


if __name__=='__main__':
    action=sys.argv[1]
    if action=='install':install()
    elif action in ('orange','blue'):run(action)
    else:raise ValueError(action)
