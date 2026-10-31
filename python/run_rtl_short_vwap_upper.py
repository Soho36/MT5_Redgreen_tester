"""Native lower-control and upper-band RTL-short jobs in a separate tester EA."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import pandas as pd
from prepare_rtl_short_vwap_upper import RUN,PRIOR,PROTOCOL,EXPERT,FEATURES,TAG
from run_rtl_vwap_replay import INSTALL,SOURCE_DATA,COMMON,digest,hidden_process,save_json


def checked_inputs():
    manifest=json.loads((RUN/'manifest.json').read_text())
    for path,expected in manifest['input_hashes'].items():assert digest(path)==expected,path
    for name,expected in manifest['prepared_sha256'].items():assert digest(RUN/name)==expected,name
    compiled=json.loads((RUN/'compile.completed.json').read_text())
    assert digest(RUN/(EXPERT+'.ex5'))==compiled['binary_sha256']
    return manifest


def install():
    checked_inputs()
    folder=SOURCE_DATA/'MQL5/Experts/CodexShortVwapUpper'
    folder.mkdir(parents=True,exist_ok=True)
    for name in (EXPERT+'.ex5',EXPERT+'.mq5','early_closes.mqh','rtl_session_vwap.mqh'):
        target=folder/name
        if target.exists():assert digest(target)==digest(RUN/name),'Preserve changed installed file: '+name
        else:shutil.copyfile(RUN/name,target)
    shared=COMMON/FEATURES
    if shared.exists():assert digest(shared)==digest(RUN/FEATURES)
    else:shutil.copyfile(RUN/FEATURES,shared)
    save_json(RUN/'installation.json',dict(binary=str(folder/(EXPERT+'.ex5')),binary_sha256=digest(folder/(EXPERT+'.ex5')),
        original_ea_unchanged=True,chart_attachment=False,tester_only_guard=True,feature_sha256=digest(shared)))


def check_lower():
    tag=TAG+'_lower'
    mine=RUN/f'runband_{tag}_1.00.csv'
    original=PRIOR/'runband_rtlshortlines_20261031_orange_1.00.csv'
    a=pd.read_csv(RUN/f'runband_{tag}_1.00_stats.csv',sep='\t',encoding='utf-16').iloc[0]
    b=pd.read_csv(PRIOR/'runband_rtlshortlines_20261031_orange_1.00_stats.csv',sep='\t',encoding='utf-16').iloc[0]
    totals={k:dict(new=float(a[k]),original=float(b[k])) for k in ('trades','net_profit','gross_profit','gross_loss','equity_dd','balance_dd')}
    passed=mine.read_bytes()==original.read_bytes() and all(v['new']==v['original'] for v in totals.values())
    save_json(RUN/'lower_validation.json',dict(all_passed=passed,ledger_byte_identical=mine.read_bytes()==original.read_bytes(),native_totals=totals))
    assert passed,totals
    print('Lower control reproduces prior orange ledger byte for byte',flush=True)


def run(variant):
    manifest=checked_inputs()
    if variant=='upper':assert json.loads((RUN/'lower_validation.json').read_text())['all_passed']
    job=next(j for j in manifest['jobs'] if j['variant']==variant)
    tag=job['tag']
    if (RUN/(tag+'.completed.json')).exists():raise RuntimeError('Preserve completed run')
    active=subprocess.run(['tasklist','/FI','IMAGENAME eq terminal64.exe','/FO','CSV','/NH'],capture_output=True,text=True)
    if 'terminal64.exe' in active.stdout.lower():raise RuntimeError('MT5 is open; preserve its work')
    install()
    config=RUN/(tag+'.ini')
    text=config.read_text(encoding='utf-16')
    for setting in ('UseRemote=0','UseCloud=0','Visual=0','ShutdownTerminal=1','AllowLiveTrading=0','Optimization=0'):
        assert setting in text.splitlines()
    assert not re.search(r'^(Login|Server|Password)=',text,re.M)
    for name in job['outputs']:assert not (COMMON/name).exists() and not (RUN/name).exists(),'Preserve output: '+name
    record=dict(tag=tag,variant=variant,z=job['z'],side=job['side'],native_mt5=True,
        config_sha256=digest(config),expert_sha256=digest(RUN/(EXPERT+'.ex5')),live_trading_enabled=False,
        protocol_sha256=digest(PROTOCOL),runner_sha256=digest(Path(__file__)))
    save_json(RUN/(tag+'.started.json'),record)
    print('Running native '+variant+' short test',flush=True)
    process=hidden_process([str(INSTALL/'terminal64.exe'),'/config:'+str(config)],timeout=900,cwd=INSTALL)
    assert process['returncode']==0,process
    for name in job['outputs']:
        assert (COMMON/name).exists(),name
        shutil.copyfile(COMMON/name,RUN/name)
    report=None
    for parent in (SOURCE_DATA,INSTALL):
        candidate=parent/(tag+'.htm')
        if candidate.exists():
            report=RUN/candidate.name
            shutil.copyfile(candidate,report)
            break
    assert report is not None,'Native report missing'
    record.update(process,outputs={name:digest(RUN/name) for name in job['outputs']},report_sha256=digest(report))
    save_json(RUN/(tag+'.completed.json'),record)
    if variant=='lower':check_lower()
    print('Completed native '+variant+' short test',flush=True)


if __name__=='__main__':
    if sys.argv[1]=='install':install()
    else:run(sys.argv[1])
