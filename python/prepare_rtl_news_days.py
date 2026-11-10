"""Prepare five frozen whole-session news-exclusion native RTL jobs."""
import json
import re
import shutil
import pandas as pd
from build_news_calendar import ROOT,RUN,DOC,OUT,sha

BASE=ROOT/'Reports/rtl_gg_exclude16_20261101'
EXPERT='RTL_news_days_research'
TAG='ex16_20261101_rtl_base_all'
POLICIES={'control':0,'skip_cpi':1,'skip_payrolls':2,'skip_fomc':4,'skip_all':7}

def main():
    assert not (RUN/'manifest.json').exists(),'Preserve prepared study'
    events=pd.read_csv(OUT/'us_major_news_2010_2026.csv')
    bits=events.event.map({'CPI':1,'PAYROLLS':2,'FOMC':4})
    masks=bits.groupby(events.date).sum().sort_index()
    dates=','.join(masks.index.str.replace('-',''))
    flags=','.join(map(str,masks.to_list()))
    header=f'''// Generated from the frozen official release calendar; research only.
input int NewsMask=0; // 1=CPI, 2=payrolls, 4=scheduled FOMC, 7=union
int NEWS_DATE[]={{{dates}}};
int NEWS_FLAGS[]={{{flags}}};
bool IsNewsSession(datetime sessionTime)
{{
   if(NewsMask==0) return false;
   MqlDateTime dt;TimeToStruct(sessionTime,dt);
   int date=dt.year*10000+dt.mon*100+dt.day;
   int lo=0,hi=ArraySize(NEWS_DATE)-1;
   while(lo<=hi) {{int mid=(lo+hi)/2;
      if(NEWS_DATE[mid]==date) return (NEWS_FLAGS[mid]&NewsMask)!=0;
      if(NEWS_DATE[mid]<date) lo=mid+1;else hi=mid-1;
   }}
   return false;
}}
'''
    (RUN/'news_days_research.mqh').write_text(header,encoding='utf-8')
    src=(BASE/'RTL_GG_exclude16_replay.mq5').read_text(encoding='utf-8')
    anchor='#include "window_equity_research.mqh"'
    assert src.count(anchor)==1
    src=src.replace(anchor,anchor+'\n#include "news_days_research.mqh"')
    anchor='   // 🔹 manage existing position'
    assert src.count(anchor)==1
    gate='''   // Whole-session exclusion: historical bars/bookkeeping still advance.
   if(IsNewsSession(sessionBar))
   {
      CancelAllOrders();
      if(PositionsTotal()>0) {Print("NEWS_EXPOSURE_ERROR");ExpertRemove();}
      return;
   }

'''
    src=src.replace(anchor,gate+anchor)
    (RUN/(EXPERT+'.mq5')).write_text(src,encoding='utf-8')
    for name in ('early_closes.mqh','stock_early_closes.mqh','rtl_session_vwap.mqh','window_equity_research.mqh'):
        shutil.copyfile(BASE/name,RUN/name)
    ini=(BASE/(TAG+'.ini')).read_text(encoding='utf-16')
    jobs=[]
    for policy,mask in POLICIES.items():
        tag='news_20261110_'+policy
        text=ini
        for key,value in dict(Expert='CodexResearch\\'+EXPERT+'.ex5',Report=tag+'.htm',RunTag=tag,LogVwapDecisions='false').items():
            assert len(re.findall('^'+key+'=.*$',text,re.M))==1
            text=re.sub('^'+key+'=.*$',lambda _:key+'='+value,text,flags=re.M)
        text=text.replace('[TesterInputs]',f'[TesterInputs]\nNewsMask={mask}')
        fields=re.findall(r'^input\s+\w+\s+(\w+)\s*=',src+'\n'+header,re.M)
        given=re.findall(r'^(\w+)=',text.split('[TesterInputs]')[1].split('[',1)[0],re.M)
        assert sorted(fields)==sorted(given),(set(fields)-set(given),set(given)-set(fields))
        (RUN/(tag+'.ini')).write_text(text,encoding='utf-16')
        outputs=[f'rtlvwap_{tag}_1.00.csv',f'rtlvwap_{tag}_1.00_stats.csv',f'window_equity_{tag}.bin']
        jobs.append(dict(tag=tag,policy=policy,mask=mask,outputs=outputs))
    paths=[*RUN.glob('*.mq5'),*RUN.glob('*.mqh'),*RUN.glob('*.ini')]
    manifest=dict(expert=EXPERT,jobs=jobs,protocol_sha256=sha(DOC/'PROTOCOL.md'),
                  calendar_sha256=sha(OUT/'us_major_news_2010_2026.csv'),
                  prepared_sha256={p.name:sha(p) for p in paths})
    (RUN/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('Prepared five native RTL jobs',flush=True)

if __name__=='__main__':main()
