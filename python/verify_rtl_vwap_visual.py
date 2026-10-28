"""Replay both manual EA arms and verify identical trades and indicator buffers.

Requires the usual terminal to be closed. Only the process launched here is used;
its tester config requests shutdown after completion. No visual UI is opened.
"""
import json
import re
import subprocess

import pandas as pd

from prepare_rtl_vwap_visual import OUT
from run_rtl_vwap_replay import RUN,INSTALL,COMMON,digest,hidden_process,save_json,load_manifest


def verify():
    load_manifest()
    results=[]
    for arm in ('off','on'):
        count=subprocess.check_output(['powershell','-NoProfile','-Command',
            '@(Get-Process terminal64 -ErrorAction SilentlyContinue).Count'],text=True).strip()
        assert count=='0','Close MT5 before this explicit verification; no existing terminal is interrupted.'
        source=(RUN/f'vwap_replay_20261026_{arm}.ini').read_text(encoding='utf-16')
        for key,value in {'Expert':r'CodexVwapVisual\RTL_vwap_visual.ex5',
                          'Report':f'manual_vwap_verify_{arm}.htm','ShutdownTerminal':'1','Visual':'0'}.items():
            source,n=re.subn(r'^'+key+r'=.*$',lambda _:key+'='+value,source,flags=re.MULTILINE)
            assert n==1,key
        source=source.replace('[TesterInputs]\n','[TesterInputs]\nShowStudyOverlay=true\n')
        config=OUT/f'verify_{arm}.ini'
        config.write_text(source,encoding='utf-16')
        existing=set(COMMON.glob('visual_manual_vwap_*_checks.csv'))
        print('Verifying manual visual EA, gate '+arm,flush=True)
        process=hidden_process([str(INSTALL/'terminal64.exe'),'/config:'+str(config)],timeout=180,cwd=INSTALL)
        added=set(COMMON.glob('visual_manual_vwap_*_checks.csv'))-existing
        assert len(added)==1,added
        check=added.pop()
        tag=check.name[len('visual_'):-len('_checks.csv')]
        checks=pd.read_csv(check,sep='\t',encoding='utf-16').iloc[0]
        raw=COMMON/f'runband_{tag}_1.00.csv'
        expected=RUN/f'runband_vwap_replay_20261026_{arm}_1.00.csv'
        assert raw.read_bytes()==expected.read_bytes(),'Manual chart copy changed trades: '+arm
        summary=pd.read_csv(COMMON/f'vwap_{tag}_summary.csv',sep='\t',encoding='utf-16').iloc[0]
        assert summary.observer_errors==0 and checks.indicator_errors==0
        assert checks.indicator_checks==summary.candidates and checks.indicator_checks>0
        results.append(dict(arm=arm,run_tag=tag,raw_byte_equal=True,raw_sha256=digest(raw),
            indicator_checks=int(checks.indicator_checks),indicator_errors=int(checks.indicator_errors),
            process=process,config_sha256=digest(config)))
        save_json(OUT/'verification_progress.json',dict(completed=results))
        print(results[-1],flush=True)
    build=json.loads((OUT/'build.json').read_text())
    save_json(OUT/'verification.json',dict(all_passed=True,checks=results,
        compiled_sha256=build['compiled_sha256'],visual_ui_inspected=False,
        note='Full nonvisual strategy replay checks every plotted decision value; visual UI remains manual.'))


if __name__=='__main__':
    verify()
