"""Prepare isolated native RTL blue-slope replay jobs, no terminal launch."""
import json
import re
import shutil

import pandas as pd
from analyze_rtl_vwap_slope import ROOT, CROSS, DOC, FROZEN, sha, slope_features

RUN=ROOT/'Reports/rtl_vwap_slope_replay_20261101_v2'
EXPERT='RTL_blue_slope_replay'
FEATURE='rtl_slope_replay_20261101_features.tsv'


def main():
    RUN.mkdir(parents=True,exist_ok=True)
    assert not (RUN/'manifest.json').exists(), 'Prepared already; preserve evidence'
    for n,h in FROZEN.items(): assert sha(CROSS/n)==h
    assert json.loads((ROOT/'Reports/rtl_vwap_slope_20261101/verification.json').read_text())['all_passed']
    f=pd.read_csv(CROSS/'features_NQ.csv',float_precision='round_trip')
    for c in ('bar_time','feature_session'): f[c]=pd.to_datetime(f[c])
    s=slope_features(f)
    epoch=lambda x: (pd.to_datetime(x)-pd.Timestamp('1970-01-01')).dt.total_seconds().astype('int64')
    labels=pd.DataFrame(dict(available=epoch(f.available_at),session=epoch(f.feature_session),bar=epoch(f.bar_time),
                             close=f.close,delta=s.slope_delta.fillna(0),known=s.slope_state.ne('unknown').astype(int)))
    labels.to_csv(RUN/FEATURE,sep='\t',index=False,float_format='%.17g')
    src=(ROOT/'mt5/experts/RR_GG_r_MFE_buy-stop-entry_vwap.cs').read_text(encoding='utf-8')
    replacements={'// ======== HELPER FUNCTIONS ========':'#include "slope_replay_research.mqh"\n\n// ======== HELPER FUNCTIONS ========',
                  '   DisplaySettings();':'   if(!SlopeReplayInit()) return INIT_FAILED;\n   DisplaySettings();',
                  '   if(!VwapGateAllows(barOpen, c1)) return;':'   if(!SlopeReplayAllows(barOpen, c1)) return;',
                  'void OnDeinit(const int reason)\n{':'void OnDeinit(const int reason)\n{\n   SlopeReplayClose();',
                  'int OnInit()\n{':'int OnInit()\n{\n   if(!MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;'}
    for a,b in replacements.items():
        assert src.count(a)==1,a
        src=src.replace(a,b)
    (RUN/(EXPERT+'.mq5')).write_text(src,encoding='utf-8')
    for n in ('early_closes.mqh','stock_early_closes.mqh','rtl_session_vwap.mqh','slope_replay_research.mqh'):
        shutil.copyfile(ROOT/'mt5/experts'/n,RUN/n)
    template=(ROOT/'Reports/rtl_vwap_ea_20261028/vwapea_20261028_file.ini').read_text(encoding='utf-16')
    jobs=[]
    for mode in ('off','on'):
        tag='slope_replay_20261101_v2_'+mode
        text=template
        for k,v in dict(Expert='CodexResearch\\'+EXPERT+'.ex5',Report=tag+'.htm',RunTag=tag,
                        UseVwapGate='false',LogVwapDecisions='false',VwapLabelFile='').items():
            assert len(re.findall('^'+k+'=.*$',text,re.M))==1,k
            text=re.sub('^'+k+'=.*$',lambda _:k+'='+v,text,flags=re.M)
        text=text.replace('[TesterInputs]','[TesterInputs]\nSignalCandle=0\nVwapFilterLine=0\nUseSlopeGate='+str(mode=='on').lower())
        fields=re.findall(r'^input\s+\w+\s+(\w+)\s*=',src+'\n'+(RUN/'slope_replay_research.mqh').read_text(),re.M)
        section=text.split('[TesterInputs]')[1].split('[',1)[0]
        given=re.findall(r'^(\w+)=',section,re.M)
        assert sorted(fields)==sorted(given),(set(fields)^set(given))
        (RUN/(tag+'.ini')).write_text(text,encoding='utf-16')
        jobs.append(dict(tag=tag,outputs=[f'rtlvwap_{tag}_1.00.csv',f'rtlvwap_{tag}_1.00_stats.csv',f'slope_decisions_{tag}.tsv'],inputs_files=[FEATURE]))
    manifest=dict(expert=EXPERT,protocol_sha256=sha(DOC/'SLOPE_REPLAY_PROTOCOL.md'),jobs=jobs,
                  prepared_sha256={p.name:sha(p) for p in RUN.iterdir() if p.is_file()})
    (RUN/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Prepared two slope-only replay jobs:',RUN)


if __name__=='__main__': main()
