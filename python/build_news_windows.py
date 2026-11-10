"""Build auditable historical event times and merged half-hour exclusion intervals."""
import html
import json
import re
import zipfile
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from build_news_calendar import ROOT,OUT,sha
from download_news_times import RUN,SOURCES,NOTICES,conference_links

DOC=ROOT/'docs/baseline/rtl-news-windows'
TIME_CSV=OUT/'us_major_news_times_2010_2026.csv'
WINDOW_CSV=OUT/'us_major_news_windows_30m_2010_2026.csv'

def clean(text):return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>',' ',text))).strip()

def clock_time(text):
    m=re.search(r'(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m\.?',text,re.I)
    assert m,text
    hour=int(m[1])%12+(12 if m[3].lower()=='p' else 0)
    return f'{hour:02}:{int(m[2] or 0):02}'

def merge_windows(events,minutes=30):
    intervals=[]
    for row in events.sort_values('research_time').itertuples():
        center=pd.Timestamp(row.research_time)
        lo=center-pd.Timedelta(minutes=minutes);hi=center+pd.Timedelta(minutes=minutes)
        if intervals and lo<=intervals[-1]['end']:
            intervals[-1]['end']=max(hi,intervals[-1]['end'])
            intervals[-1]['events']+='|'+row.event
        else:intervals.append(dict(start=lo,end=hi,events=row.event))
    return pd.DataFrame(intervals)

def window_ids(times,windows):
    values=np.asarray(pd.to_datetime(times),dtype='datetime64[s]').astype(np.int64)
    if windows.empty:return np.full(values.shape,-1,dtype=int)
    starts=windows.start.to_numpy(dtype='datetime64[s]').astype(np.int64)
    ends=windows.end.to_numpy(dtype='datetime64[s]').astype(np.int64)
    ix=np.searchsorted(starts,values,side='right')-1
    return np.where((ix>=0)&(values<ends[np.maximum(ix,0)]),ix,-1)

def timed_record(date,event,time,source,method,evidence):
    eastern=datetime.fromisoformat(date+'T'+time).replace(tzinfo=ZoneInfo('America/New_York'))
    research=eastern.replace(tzinfo=None)+timedelta(hours=7)
    return dict(date=date,event=event,time_et=time,event_utc=eastern.astimezone(ZoneInfo('UTC')).isoformat(),
                research_time=research.isoformat(sep=' '),time_source=source,time_method=method,evidence=evidence)

def main():
    base=pd.read_csv(OUT/'us_major_news_2010_2026.csv')
    bls=json.loads((SOURCES/'bls_time_checks.json').read_text(encoding='utf-8'))
    lookup={r['url']:r for r in bls}
    assert len(lookup)==400 and all(r['verified'] for r in bls)
    sources=json.loads((SOURCES/'downloads.json').read_text())
    assert not sources['failures']
    for record in sources['sources']:assert sha(SOURCES/record['file'])==record['sha256']
    conf=conference_links();rows=[];counts={};discrepancies=[]
    for r in base.itertuples():
        if r.event!='FOMC':
            proof=lookup[r.source_url];assert '8:30' in proof['evidence']
            rows.append(timed_record(r.date,r.event,'08:30',proof['time_source'],proof['method'],proof['evidence']))
            continue
        day=r.date.replace('-','');page=SOURCES/f'statement_{day}.html'
        text=clean(page.read_text(encoding='utf-8'))
        found=re.search(r'For release at ([^<]{1,50}?[ap]\.m\.)',text,re.I)
        if found:
            time=clock_time(found[1]);source=r.source_url;method='statement_release_header';evidence=found[0]
        elif day in conf:
            ctext=clean((SOURCES/f'conference_{day}.html').read_text(encoding='utf-8'))
            found=re.search(r'FOMC Meeting Statement.{0,100}?Released.{0,60}?at (\d{1,2}:\d{2} [ap]\.m\.)',ctext,re.I)
            assert found,(day,'no statement release time')
            time=clock_time(found[1]);source=conf[day];method='conference_statement_release_label';evidence=found[0]
        elif r.date>='2013-03-13':
            notice=clean((SOURCES/'notice_20130313.html').read_text(encoding='utf-8'))
            assert 'released at 2 p.m. Eastern Time' in notice and 'regularly scheduled' in notice
            time='14:00';source=NOTICES['notice_20130313.html'];method='official_uniform_scheduled_time'
            evidence='March 13, 2013 notice: all regularly scheduled FOMC statements released at 2:00 p.m. Eastern.'
        else:
            assert r.date<='2013-01-30',(day,'missing recent release time')
            time='14:15';source=NOTICES['historical_timing_table.html'];method='dated_Fed_research_table_1'
            table=clean((SOURCES/'historical_timing_table.html').read_text(encoding='utf-8'))
            table=table.split('Table 1: Dates and Times of US Monetary Policy Announcements',1)[-1].split('Table 2:',1)[0]
            md=str(int(day[4:6]))+'/'+str(int(day[6:]))
            assert re.search(r'(?<!\d)'+re.escape(md)+r'(?!\d)',table),day
            evidence=f'Table 1, {r.date}: 14:15 New York unless an explicit alternative is printed.'
        expected='14:00' if r.date>='2013-03-13' else ('12:30' if day in conf else '14:15')
        if day in ('20120125','20120425','20120620','20120913') and time!=expected:
            minutes=clean((SOURCES/f'minutes_{day}.html').read_text(encoding='utf-8'))
            proof=re.search(r'statement below to be released at 12:30 p\.m\.',minutes)
            assert proof,'Need contemporaneous scheduled-time evidence'
            discrepancies.append(dict(date=r.date,archive_time=time,scheduled_time='12:30',resolution='Use scheduled time approved in contemporaneous minutes'))
            time='12:30';source=NOTICES[f'minutes_{day}.html'];method='minutes_scheduled_time_over_conflicting_page';evidence=proof[0]
        assert time==expected,(r.date,time,expected)
        rows.append(timed_record(r.date,'FOMC',time,source,method,evidence))
        if day in conf:
            counts[day[:4]]=counts.get(day[:4],0)+1
            time='14:15' if day<'20130313' else '14:30'
            source=NOTICES['notice_20110324.html'] if day<'20120101' else (NOTICES['nyfed_2012_timing.html'] if day<'20130101' else NOTICES['notice_20130313.html'])
            rows.append(timed_record(r.date,'FOMC_PRESS_CONFERENCE',time,source,'listed_conference_and_official_timing_notice',conf[day]))
    expected_counts={str(y):(3 if y==2011 else 5 if y==2012 else 4 if y<=2018 else 7 if y==2020 else 6 if y==2026 else 8) for y in range(2011,2027)}
    assert counts==expected_counts,(counts,expected_counts)
    frame=pd.DataFrame(rows).sort_values(['research_time','event'])
    assert len(frame)==626 and frame[['date','event']].duplicated().sum()==0
    windows=merge_windows(frame)
    frame.to_csv(TIME_CSV,index=False)
    windows.to_csv(WINDOW_CSV,index=False)
    sources_paths=sorted(p for p in SOURCES.iterdir() if p.is_file())
    archive_path=OUT/'us_major_news_times_2010_2026_sources.zip'
    with zipfile.ZipFile(archive_path,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sources_paths:
            info=zipfile.ZipInfo(path.name,date_time=(2026,11,10,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,path.read_bytes())
    manifest=dict(base_calendar_sha256=sha(OUT/'us_major_news_2010_2026.csv'),events=len(frame),windows=len(windows),
        conference_counts=counts,clock='America/New_York; research=New York+7 hours; half-open +/-30 minutes',
        event_csv_sha256=sha(TIME_CSV),window_csv_sha256=sha(WINDOW_CSV),source_zip_sha256=sha(archive_path),
        source_sha256={p.name:sha(p) for p in sources_paths},timing_methods=frame.time_method.value_counts().to_dict(),discrepancies=discrepancies)
    (OUT/'us_major_news_times_2010_2026_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in manifest.items() if k!='source_sha256'},indent=2))

if __name__=='__main__':main()
