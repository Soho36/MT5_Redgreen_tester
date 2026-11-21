"""Export complete available news sessions as M1 text for manual Forex Tester replay.

Prices, source clock, bar gaps and volumes are unchanged. Packed dates are
synthetic labels; they do not turn the selected sessions into continuous history.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

from project_paths import PROJECT_ROOT as ROOT
from rtl_weekly_engine import MINUTES

CALENDAR=ROOT/'data/calendars/us_major_news_2010_2026.csv'
TIMES=ROOT/'data/calendars/us_major_news_times_2010_2026.csv'
DEFAULT_OUT=ROOT/'Reports/mnq_news_forex_tester_20261121'
FIELDS=['<DATE>','<TIME>','<OPEN>','<HIGH>','<LOW>','<CLOSE>','<VOL>']
IMPORT_FIELDS=['Date','Time','Open','High','Low','Close','Volume']
IMPORT_GUIDE='https://desktop.forextester.com/import'

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def date_mapping(dates,mode,start):
    dates=sorted(set(dates))
    if mode=='original':return dict(zip(dates,dates))
    if mode!='packed':raise ValueError(mode)
    first=pd.Timestamp(start)
    if first.dayofweek>=5:raise ValueError('Packed start must be Monday-Friday')
    return dict(zip(dates,pd.bdate_range(first,periods=len(dates)).strftime('%Y-%m-%d')))

def import_frame(selected,mapping):
    result=selected[FIELDS].copy()
    original=result['<DATE>'].str.replace('.','-',regex=False)
    result['<DATE>']=original.map(mapping).str.replace('-','',regex=False)
    if result['<DATE>'].isna().any():raise ValueError('Missing session date mapping')
    result.columns=IMPORT_FIELDS
    return result

def validate_bars(frame):
    stamp=pd.to_datetime(frame.Date+frame.Time,format='%Y%m%d%H:%M:%S')
    assert stamp.is_monotonic_increasing and stamp.is_unique
    assert stamp.dt.second.eq(0).all()
    prices=frame[['Open','High','Low','Close']].astype(float)
    assert np.isfinite(prices.to_numpy()).all() and prices.gt(0).all().all()
    assert prices.High.ge(prices[['Open','Low','Close']].max(axis=1)).all()
    assert prices.Low.le(prices[['Open','High','Close']].min(axis=1)).all()
    assert np.allclose(prices.to_numpy()*4,np.round(prices.to_numpy()*4),atol=1e-7,rtol=0)
    volumes=frame.Volume.astype('int64')
    assert volumes.ge(0).all()
    assert stamp.dt.dayofweek.lt(5).all()

def build(source,out,mode,start):
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    assert not list(out.iterdir()),'Use a new empty output directory; preserve prior exports'
    source=Path(source)
    cal=pd.read_csv(CALENDAR,dtype=str)
    assert not cal[['date','event']].duplicated().any()
    assert set(cal.event)=={'CPI','PAYROLLS','FOMC'}
    wanted=set(cal.date.str.replace('-','',regex=False))
    pieces=[];source_rows=0;first=last=None
    for chunk in pd.read_csv(source,sep='\t',usecols=FIELDS,dtype=str,chunksize=250000):
        if first is None:first=chunk.iloc[0]['<DATE>']
        last=chunk.iloc[-1]['<DATE>'];source_rows+=len(chunk)
        mask=chunk['<DATE>'].str.replace('.','',regex=False).isin(wanted)
        if mask.any():pieces.append(chunk.loc[mask,FIELDS].copy())
    assert pieces,'No matching news sessions'
    selected=pd.concat(pieces,ignore_index=True)
    real_dates=selected['<DATE>'].str.replace('.','-',regex=False)
    dates=sorted(real_dates.unique())
    mapping=date_mapping(dates,mode,start)
    result=import_frame(selected,mapping);validate_bars(result)
    file=out/'MNQ_NEWS_ONLY_M1.csv'
    result.to_csv(file,index=False,lineterminator='\n')
    reread=pd.read_csv(file,dtype=str,keep_default_na=False)
    pd.testing.assert_frame_equal(reread,result,check_exact=True)
    # Reverse the only allowed edit and compare every source value verbatim.
    reverse={v.replace('-',''):k.replace('-','.') for k,v in mapping.items()}
    restored=reread.copy();restored.Date=restored.Date.map(reverse);restored.columns=FIELDS
    pd.testing.assert_frame_equal(restored,selected[FIELDS],check_exact=True)
    assert reread.Date.nunique()==len(dates) and set(real_dates)<=set(cal.date)

    all_times=pd.read_csv(TIMES,dtype=str)
    timed=all_times.loc[all_times.date.isin(dates)].copy()
    base_keys=set(zip(cal.loc[cal.date.isin(dates),'date'],cal.loc[cal.date.isin(dates),'event']))
    assert base_keys==set(zip(timed.loc[timed.event.ne('FOMC_PRESS_CONFERENCE'),'date'],timed.loc[timed.event.ne('FOMC_PRESS_CONFERENCE'),'event']))
    sequence={date:i+1 for i,date in enumerate(dates)}
    event_rows=[]
    for r in timed.itertuples():
        chart=pd.Timestamp(r.research_time).strftime('%H:%M:%S')
        event_rows.append(dict(session_number=sequence[r.date],import_date=mapping[r.date],original_date=r.date,
            event=r.event,time_et=r.time_et,time_chart=chart,import_event_time=mapping[r.date]+' '+chart,
            original_event_utc=r.event_utc,time_source=r.time_source))
    pd.DataFrame(event_rows).to_csv(out/'events.csv',index=False,lineterminator='\n')
    sessions=[]
    for original,part in selected.groupby('<DATE>',sort=True):
        day=original.replace('.','-');events=timed.loc[timed.date.eq(day)]
        minute=pd.to_timedelta(part['<TIME>']).dt.total_seconds().to_numpy()/60
        gaps=np.diff(minute)
        sessions.append(dict(session_number=sequence[day],import_date=mapping[day],original_date=day,
            original_weekday=pd.Timestamp(day).day_name(),events='; '.join(events.event),
            event_times_et='; '.join(events.event+' '+events.time_et),
            event_times_chart='; '.join(events.event+' '+events.research_time.str[-8:]),
            bars=len(part),first_time=part.iloc[0]['<TIME>'],last_time=part.iloc[-1]['<TIME>'],
            missing_minutes_between_first_last=int((minute[-1]-minute[0]+1)-len(minute)),
            largest_bar_gap_minutes=int(gaps.max()) if len(gaps) else 0))
    pd.DataFrame(sessions).to_csv(out/'sessions.csv',index=False,lineterminator='\n')
    omitted=[]
    for day in sorted(set(cal.date)-set(dates)):
        reason='before_source_history' if day<first.replace('.','-') else ('after_source_history' if day>last.replace('.','-') else 'no_source_bars')
        omitted.append(dict(date=day,events='; '.join(cal.loc[cal.date.eq(day),'event']),reason=reason))
    pd.DataFrame(omitted,columns=['date','events','reason']).to_csv(out/'omitted_dates.csv',index=False,lineterminator='\n')
    assert len(dates)+len(omitted)==cal.date.nunique()
    first_import,last_import=mapping[dates[0]],mapping[dates[-1]]
    date_note=(f'News sessions have synthetic consecutive Monday-Friday dates, {first_import} to {last_import}.\n'
               'Use sessions.csv to translate each chart date back to the real event date.\n'
               'Weekdays and holidays on the packed chart are labels, not historical facts.') if mode=='packed' else (
               'Real session dates are retained. Non-news dates have no bars in this file.')
    instructions=f'''MNQ NEWS-ONLY MANUAL REPLAY — FOREX TESTER DESKTOP

Ready to import: MNQ_NEWS_ONLY_M1.csv
{len(dates):,} available news sessions; {len(result):,} one-minute bars.
Original sessions: {dates[0]} through {dates[-1]}.
{date_note}

IMPORT
1. In Data Center, create/select a separate custom research symbol such as
   MNQ_NEWS_ONLY and choose Import from a file. Avoid merging this selection
   into your ordinary continuous symbol's history.
2. Select MNQ_NEWS_ONLY_M1.csv. Time shift: 0 hours.
3. Separator: comma. Date format: YYYYMMDD. Map the seven columns:
   Date | Time | Open | High | Low | Close | Volume.
   The first row is a header. The first actual bar should be
   {reread.iloc[0].Date} {reread.iloc[0].Time}, open {reread.iloc[0].Open}.
   Confirm the preview has no conversion errors before importing.
4. Create a project using minute data and this symbol. Use M30, M5, M1 or
   another intraday chart; Forex Tester generates higher timeframes from M1.
   Start at the beginning of the imported range, {first_import}.
5. Review each session separately. Close positions and cancel pending orders
   before moving to the next selected day.

Official import instructions: {IMPORT_GUIDE}
The file has been parsed back and compared with the source; the Forex Tester
application import itself has not been performed.

CLOCK
The original research clock is retained: America/Chicago wall time +8 hours,
equivalently New York wall time +7 hours. Normal sessions run 01:00–23:59.
Thus 08:30 New York CPI/payroll news appears at 15:30 on this chart.
Use events.csv for each historical Fed release/conference time. Do not apply
European DST or another time shift to this already session-aligned clock.

WHAT IS INCLUDED
The same frozen core calendar as our study: CPI, Employment Situation/payrolls,
and scheduled FOMC decision days through September 2026. Conference starts are
listed in the event lookup; they do not add a second copy of the same session.
Multiple releases on a single date remain ONE session. Every available M1 bar
on a selected source session date is included: overnight, pre-news and post-news.
There are no non-news sessions or extra warm-up days. This is a core subset,
not all historical Investing.com three-star announcements.

SOURCE AND INTERPRETATION
Source: {source}
This is continuous NQ OHLCV used by the project for MNQ-sized research, not a
separate native-MNQ price or volume feed. Prices and volume are unchanged.
Only non-news dates are removed; in packed mode only the date labels change.
Price jumps between selected days span omitted history and are artificial
adjacency. Do not trade those joins or interpret multi-session indicators,
weekly candles, or previous-day levels as the original continuous market.
Source missing minutes, sparse bars, historical halts and shortened sessions
are preserved. No invented candles or flat prices fill missing minutes.

LOOKUP FILES
sessions.csv: one row per imported session, original date, event times, bar
counts and gaps. events.csv: one row per event, including conference starts.
omitted_dates.csv: calendar dates without bars (including before history began).
manifest.json: input/output hashes and exact validation counts.

The lookup files contain event identities/times but no daily profit, high/low
or outcome labels, so you can inspect candles without a result summary.
'''
    (out/'IMPORT_INSTRUCTIONS.txt').write_text(instructions,encoding='utf-8',newline='\n')
    manifest=dict(created='2026-11-21',date_mode=mode,synthetic_start=start if mode=='packed' else None,
        source=str(source),source_sha256=sha(source),source_bars=source_rows,
        calendar=str(CALENDAR),calendar_sha256=sha(CALENDAR),event_times_sha256=sha(TIMES),
        source_session_start=dates[0],source_session_end=dates[-1],import_start=first_import,import_end=last_import,
        sessions=len(dates),bars=len(result),core_events=len(base_keys),event_timestamps=len(event_rows),
        calendar_dates=len(set(cal.date)),omitted_dates=len(omitted),
        omitted_within_source=[r['date'] for r in omitted if r['reason']=='no_source_bars'],
        data_clock='Chicago+8 / New York+7 wall clock; synthetic dates are labels only',
        source_instrument='Continuous NQ, used as MNQ-sized research proxy',
        validation=dict(csv_round_trip_exact=True,all_ohlcv_and_intraday_times_source_exact=True,
            one_import_date_per_source_session=True,only_news_dates=True,timestamps_sorted_unique=True,
            no_synthetic_bars=True,forex_tester_ui_import_tested=False),
        files_sha256={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()},builder_sha256=sha(__file__))
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    archive=out/'MNQ_NEWS_ONLY_FOREX_TESTER.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.iterdir()):
            if p.is_file() and p!=archive:z.write(p,p.name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name,digest in manifest['files_sha256'].items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
    print(json.dumps({k:manifest[k] for k in ['date_mode','sessions','bars','core_events','event_timestamps','source_session_start','source_session_end','import_start','import_end','omitted_within_source','validation']},indent=2))
    print('Saved',archive,'bytes',archive.stat().st_size)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=MINUTES)
    parser.add_argument('--output',type=Path,default=DEFAULT_OUT)
    parser.add_argument('--dates',choices=['packed','original'],default='packed')
    parser.add_argument('--packed-start',default='2010-01-04')
    args=parser.parse_args()
    build(args.source,args.output,args.dates,args.packed_start)

if __name__=='__main__':main()
