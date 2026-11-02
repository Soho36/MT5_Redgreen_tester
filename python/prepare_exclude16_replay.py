"""Eight native RTL/GG x VWAP x entry-window jobs, with passive equity sampling."""
import json
import re
import shutil

from analyze_rtl_vwap_slope import ROOT,DOC,sha

RUN=ROOT/'Reports/rtl_gg_exclude16_20261101'
EXPERT='RTL_GG_exclude16_replay'
FEATURE='rtl_vwap_replay_20261026_features.csv'


def main():
    RUN.mkdir(parents=True,exist_ok=True)
    assert not (RUN/'manifest.json').exists(),'Preserve prepared study'
    src=(ROOT/'mt5/experts/RR_GG_r_MFE_buy-stop-entry_vwap.cs').read_text(encoding='utf-8')
    edits={'// ======== HELPER FUNCTIONS ========':'#include "window_equity_research.mqh"\n\n// ======== HELPER FUNCTIONS ========',
           'int OnInit()\n{':'int OnInit()\n{\n   if(!MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;',
           '   DisplaySettings();':'   if(!WindowEquityInit()) return INIT_FAILED;\n   DisplaySettings();',
           'void OnTick()':'void StrategyOnTick()',
           'void OnDeinit(const int reason)\n{':'void OnDeinit(const int reason)\n{\n   WindowEquityClose();'}
    for old,new in edits.items():
        assert src.count(old)==1,old
        src=src.replace(old,new)
    src+='''\nvoid OnTick() {WindowEquitySample();StrategyOnTick();WindowEquitySample();}
void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &req,const MqlTradeResult &res)
{WindowEquityTransaction(trans);}\n'''
    (RUN/(EXPERT+'.mq5')).write_text(src,encoding='utf-8')
    for n in ('early_closes.mqh','stock_early_closes.mqh','rtl_session_vwap.mqh','window_equity_research.mqh'):
        shutil.copyfile(ROOT/'mt5/experts'/n,RUN/n)
    source=ROOT/'Reports/rtl_vwap_ea_20261028'/FEATURE
    assert source.exists()
    assert sha(source)==sha(ROOT/'Reports/rtl_vwap_replay_20261026'/FEATURE)
    shutil.copyfile(source,RUN/FEATURE)
    base=(ROOT/'Reports/rtl_vwap_ea_20261028/vwapea_20261028_file.ini').read_text(encoding='utf-16')
    jobs=[]
    for strategy in ('rtl','gg'):
        for vwap in (False,True):
            for exclude in (False,True):
                tag=f'ex16_20261101_{strategy}_'+('vwap' if vwap else 'base')+('_skip' if exclude else '_all')
                text=base
                replacements=dict(Expert='CodexResearch\\'+EXPERT+'.ex5',Report=tag+'.htm',RunTag=tag,
                                  UseVwapGate=str(vwap).lower(),LogVwapDecisions='true',
                                  W1600W1700=str(not exclude).lower(),VwapLabelFile=FEATURE,
                                  ToDate='2026.10.23' if strategy=='gg' else '2026.10.15')
                for k,v in replacements.items():
                    assert len(re.findall('^'+k+'=.*$',text,re.M))==1,k
                    text=re.sub('^'+k+'=.*$',lambda _:k+'='+v,text,flags=re.M)
                text=text.replace('[TesterInputs]',f'[TesterInputs]\nSignalCandle={int(strategy=="gg")}\nVwapFilterLine=0')
                fields=re.findall(r'^input\s+\w+\s+(\w+)\s*=',src,re.M)
                given=re.findall(r'^(\w+)=',text.split('[TesterInputs]')[1].split('[',1)[0],re.M)
                assert sorted(fields)==sorted(given)
                (RUN/(tag+'.ini')).write_text(text,encoding='utf-16')
                outputs=[f'rtlvwap_{tag}_1.00.csv',f'rtlvwap_{tag}_1.00_stats.csv',f'vwap_decisions_{tag}.csv',f'window_equity_{tag}.bin']
                jobs.append(dict(tag=tag,strategy=strategy,vwap=vwap,exclude=exclude,outputs=outputs,inputs_files=[FEATURE]))
    manifest=dict(expert=EXPERT,protocol_sha256=sha(DOC/'EXCLUDE_16_PROTOCOL.md'),jobs=jobs,
                  prepared_sha256={p.name:sha(p) for p in RUN.iterdir() if p.is_file()})
    (RUN/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Prepared eight native jobs:',RUN)


if __name__=='__main__':main()
