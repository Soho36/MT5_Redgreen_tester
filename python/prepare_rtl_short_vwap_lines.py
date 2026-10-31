"""Prepare/compile the native orange-versus-blue RTL-short experiment."""
import json
from pathlib import Path
import re
import shutil
import sys
import prepare_rtl_short_vwap as original
from project_paths import PROJECT_ROOT as ROOT
from run_rtl_vwap_replay import INSTALL, digest, hidden_process, save_json

RUN=ROOT/'Reports/rtl_short_vwap_lines_20261031'
PRIOR=ROOT/'Reports/rtl_short_vwap_20261031'
PROTOCOL=ROOT/'docs/baseline/rtl-vwap/SHORT_LINE_PROTOCOL.md'
EXPERT=original.EXPERT
FEATURES=original.FEATURES
TAG='rtlshortlines_20261031'


def prepare():
    RUN.mkdir(exist_ok=True)
    if (RUN/'manifest.json').exists(): raise RuntimeError('Preserve prepared study')
    source=original.build_source()
    assert source==(ROOT/'mt5/experts/shorts/RTL_short_vwap.cs').read_text(encoding='utf-8')
    (RUN/(EXPERT+'.mq5')).write_text(source,encoding='utf-8')
    for name in ('early_closes.mqh','rtl_session_vwap.mqh'):
        shutil.copyfile(ROOT/'mt5/experts'/name,RUN/name)
    shutil.copyfile(PRIOR/FEATURES,RUN/FEATURES)
    template=(PRIOR/(original.TAG+'_on.ini')).read_text(encoding='utf-16').splitlines()
    jobs=[]
    for variant,line in [('orange',0),('blue',1)]:
        tag=TAG+'_'+variant
        changes={'Report':tag+'.htm','RunTag':tag}
        lines=[k+'='+changes[k] if (k:=x.split('=',1)[0]) in changes else x for x in template]
        at=lines.index('[TesterInputs]')+1
        lines.insert(at,'VwapFilterLine='+str(line))
        end=next(i for i in range(at,len(lines)) if lines[i].startswith('['))
        supplied=[x.split('=',1)[0] for x in lines[at:end] if '=' in x]
        inputs=re.findall(r'^input\s+\w+\s+(\w+)\s*=',source,re.M)
        assert sorted(supplied)==sorted(inputs) and len(supplied)==len(set(supplied))
        (RUN/(tag+'.ini')).write_text('\n'.join(lines)+'\n',encoding='utf-16')
        preset='\n'.join(x.split('||')[0] for x in lines[at:end] if '=' in x)+'\n'
        (RUN/f'{EXPERT}_{variant}.set').write_text(preset,encoding='utf-16')
        jobs.append(dict(tag=tag,variant=variant,filter_line=line,outputs=[f'runband_{tag}_1.00.csv',
            f'runband_{tag}_1.00_stats.csv',f'short_vwap_{tag}.csv']))
    inputs=[PROTOCOL,Path(__file__),ROOT/'python/prepare_rtl_short_vwap.py',
            ROOT/'mt5/experts/shorts/RTL_short_vwap.cs',PRIOR/(original.TAG+'_on.htm'),
            PRIOR/f'runband_{original.TAG}_on_1.00.csv',PRIOR/f'runband_{original.TAG}_on_1.00_stats.csv']
    save_json(RUN/'manifest.json',dict(expert=EXPERT,jobs=jobs,cutoffs={'orange':-1,'blue':0},
        input_hashes={str(p):digest(p) for p in inputs},
        prepared_sha256={p.name:digest(p) for p in RUN.iterdir() if p.suffix in ('.mq5','.mqh','.csv','.ini','.set')}))
    print('Prepared native orange/blue jobs and presets',flush=True)


def compile():
    log=RUN/'compile.log'
    process=hidden_process([str(INSTALL/'MetaEditor64.exe'),'/compile:'+str(RUN/(EXPERT+'.mq5')),
                            '/log:'+str(log)],timeout=180)
    result=log.read_text(encoding='utf-16',errors='replace')
    assert 'Result: 0 errors, 0 warnings' in result,result[-2000:]
    save_json(RUN/'compile.completed.json',dict(**process,binary_sha256=digest(RUN/(EXPERT+'.ex5')),
        inputs_sha256={p.name:digest(p) for p in RUN.iterdir() if p.suffix in ('.mq5','.mqh')}))
    print('Compiled switch EA: 0 errors, 0 warnings',flush=True)


if __name__=='__main__':
    {'prepare':prepare,'compile':compile}[sys.argv[1]]()
