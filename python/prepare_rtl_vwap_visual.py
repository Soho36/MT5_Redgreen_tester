"""Build/install a display-only manual tester copy without changing frozen research.

Does not start/stop MT5 or attach anything to a live chart. Manual output tags are
always made unique, and the EA rejects other symbols and live execution.
"""
from pathlib import Path
import shutil

from run_rtl_vwap_replay import ROOT,RUN,INSTALL,SOURCE_DATA,COMMON,digest,load_manifest,hidden_process,save_json

OUT=ROOT/'Reports/rtl_vwap_visual_20261027'


def replace_once(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new)


def build():
    load_manifest()
    OUT.mkdir(parents=True,exist_ok=True)
    source=(RUN/'RTL_vwap_replay.mq5').read_text(encoding='utf-8')
    source=replace_once(source,'#include "vwap_replay_research.mqh"',
        'void StudyVisualCandidate(ulong order,uint retcode,bool sent);\n#include "vwap_manual_research.mqh"\n#include "vwap_visual_overlay.mqh"')
    source=replace_once(source,'int OnInit()\n{','''int OnInit()
{
   if(!MQLInfoInteger(MQL_TESTER) || _Symbol!="MNQcontDTBNT20102026_2" || _Period!=PERIOD_M30)
   { Print("Manual study copy requires Strategy Tester, MNQcontDTBNT20102026_2, M30"); return INIT_FAILED; }
''')
    source=replace_once(source,'g_runTag  = (RunTag == "" ? ActiveWindowLabel() : RunTag);',
        '''string manualBase="manual_vwap_"+(UseVwapReplayGate ? "on_" : "off_")+(string)(long)TimeLocal()+"_"+(string)GetTickCount64();
   g_runTag=manualBase;
   int manualSuffix=0;
   while(FileIsExist("runband_"+g_runTag+"_"+DoubleToString(RiskReward,2)+".csv",FILE_COMMON) ||
         FileIsExist("vwap_"+g_runTag+"_candidates.csv",FILE_COMMON))
      g_runTag=manualBase+"_"+IntegerToString(++manualSuffix);''')
    source=replace_once(source,'   if(!g_prReady) return INIT_FAILED;',
        '   if(!g_prReady) return INIT_FAILED;\n   if(!StudyVisualInit()) return INIT_FAILED;')
    source=replace_once(source,'   VwapReplayFinish();','   StudyVisualFinish();\n   VwapReplayFinish();')
    observer=(RUN/'vwap_replay_research.mqh').read_text(encoding='utf-8')
    observer=replace_once(observer,'   int j=g_vrFeatureIndex;',
        '   StudyVisualCandidate(order,retcode,sent);\n   int j=g_vrFeatureIndex;')
    (OUT/'RTL_vwap_visual.mq5').write_text(source,encoding='utf-8')
    (OUT/'vwap_manual_research.mqh').write_text(observer,encoding='utf-8')
    for name in ('early_closes.mqh','vwap_replay_path.mqh'):
        shutil.copyfile(RUN/name,OUT/name)
    shutil.copyfile(ROOT/'mt5/experts/vwap_visual_overlay.mqh',OUT/'vwap_visual_overlay.mqh')
    shutil.copyfile(ROOT/'mt5/indicators/RTL_Study_VWAP.mq5',OUT/'RTL_Study_VWAP.mq5')
    compiled={}
    for name in ('RTL_Study_VWAP','RTL_vwap_visual'):
        log=OUT/(name+'.compile.log')
        hidden_process([str(INSTALL/'MetaEditor64.exe'),'/compile:'+str(OUT/(name+'.mq5')),
                        '/log:'+str(log)],timeout=180,cwd=OUT)
        result=[s for s in log.read_text(encoding='utf-16').splitlines() if 'result' in s.lower()]
        assert result and '0 errors, 0 warnings' in result[-1],result
        print(name+': '+result[-1])
        compiled[name]=digest(OUT/(name+'.ex5'))
    destinations={
        'RTL_Study_VWAP':SOURCE_DATA/'MQL5/Indicators/CodexVwapVisual',
        'RTL_vwap_visual':SOURCE_DATA/'MQL5/Experts/CodexVwapVisual'}
    for name,parent in destinations.items():
        parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(OUT/(name+'.ex5'),parent/(name+'.ex5'))
    feature='rtl_vwap_replay_20261026_features.csv'
    if (COMMON/feature).exists(): assert digest(COMMON/feature)==digest(RUN/feature)
    else: shutil.copyfile(RUN/feature,COMMON/feature)
    profiles=SOURCE_DATA/'MQL5/Profiles/Tester'
    profiles.mkdir(parents=True,exist_ok=True)
    for gate in ('off','on'):
        original=(RUN/f'vwap_replay_20261026_{gate}.ini').read_text(encoding='utf-16')
        inputs=original.split('[TesterInputs]\n')[1].split('\n[Experts]')[0]
        lines=[s.split('||')[0] for s in inputs.splitlines() if '=' in s]
        lines=[s for s in lines if not s.startswith('RunTag=')]
        preset='\n'.join(['; Frozen RTL study inputs; output name is always unique.','ShowStudyOverlay=true',*lines])+'\n'
        filename=f'RTL_VWAP_visual_{gate.upper()}.set'
        (OUT/filename).write_text(preset,encoding='utf-16')
        shutil.copyfile(OUT/filename,profiles/filename)
    save_json(OUT/'build.json',dict(compiled_sha256=compiled,
        source_sha256={p.name:digest(p) for p in OUT.glob('*.mq*')},
        frozen_source_sha256=digest(RUN/'RTL_vwap_replay.mq5'),feature_sha256=digest(RUN/feature),
        installed={k:str(v/(k+'.ex5')) for k,v in destinations.items()},
        trade_logic='unchanged; chart hooks and unique output names only',terminal_launched=False))
    print('Installed manual EA, indicator and OFF/ON presets. No terminal launched.')


if __name__=='__main__':
    build()
