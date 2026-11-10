"""Separate portable-calendar, source-archive, and reported-economics checks."""
import hashlib
import json
import zipfile
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from build_news_windows import ROOT,OUT,RUN,DOC,TIME_CSV,WINDOW_CSV,sha

def main():
    calendar_manifest=json.loads((OUT/'us_major_news_times_2010_2026_manifest.json').read_text())
    for path,key in [(TIME_CSV,'event_csv_sha256'),(WINDOW_CSV,'window_csv_sha256'),
                     (OUT/'us_major_news_times_2010_2026_sources.zip','source_zip_sha256')]:
        assert sha(path)==calendar_manifest[key]
    with zipfile.ZipFile(OUT/'us_major_news_times_2010_2026_sources.zip') as z:
        assert set(z.namelist())==set(calendar_manifest['source_sha256'])
        for name,h in calendar_manifest['source_sha256'].items():assert hashlib.sha256(z.read(name)).hexdigest()==h
        bls=json.loads(z.read('bls_time_checks.json'));assert len(bls)==400 and all(r['verified'] for r in bls)
    t=pd.read_csv(TIME_CSV);w=pd.read_csv(WINDOW_CSV,parse_dates=['start','end'])
    original=pd.read_csv(OUT/'us_major_news_2010_2026.csv')
    assert set(zip(original.date,original.event))==set(zip(t.loc[t.event.ne('FOMC_PRESS_CONFERENCE'),'date'],t.loc[t.event.ne('FOMC_PRESS_CONFERENCE'),'event']))
    assert t.event.eq('FOMC_PRESS_CONFERENCE').sum()==93
    assert (w.start<w.end).all() and (w.start.iloc[1:].to_numpy()>w.end.iloc[:-1].to_numpy()).all()
    pieces=[]
    for row in t.itertuples():
        et=datetime.fromisoformat(row.date+'T'+row.time_et).replace(tzinfo=ZoneInfo('America/New_York'))
        assert et.astimezone(ZoneInfo('UTC'))==datetime.fromisoformat(row.event_utc)
        research=et.replace(tzinfo=None)+timedelta(hours=7)
        assert research==datetime.fromisoformat(row.research_time)
        pieces.append((research-timedelta(minutes=30),research+timedelta(minutes=30)))
    # Independent union using all endpoints and midpoint coverage.
    points=sorted({v for pair in pieces for v in pair});union=[]
    for a,b in zip(points[:-1],points[1:]):
        mid=a+(b-a)/2
        if not any(lo<=mid<hi for lo,hi in pieces):continue
        if union and union[-1][1]==a:union[-1]=(union[-1][0],b)
        else:union.append((a,b))
    assert union==list(zip(w.start,w.end))
    audit=json.loads((RUN/'verification.json').read_text());assert audit['all_passed']
    for name,h in audit['output_sha256'].items():assert sha(RUN/name)==h
    for name,h in audit['code_sha256'].items():assert sha(ROOT/'python'/name)==h
    s=pd.read_csv(RUN/'summary.csv');c=pd.read_csv(RUN/'comparisons.csv')
    for policy in ('control','entry','flat','day'):
        path=(ROOT/'Reports/rtl_news_days_20261110/news_20261110_skip_all_trades.csv') if policy=='day' else RUN/f'newswin_20261110_{policy}_trades.csv'
        trades=pd.read_csv(path,parse_dates=['session'],float_precision='round_trip')
        for row in s.loc[s.policy.eq(policy)].itertuples():
            from analyze_rtl_vwap_slope import PERIODS
            start,end=PERIODS[row.period] if row.period in PERIODS else (row.period+'-01-01',min(str(int(row.period)+1)+'-01-01','2026-10-01'))
            part=trades.loc[trades.session.ge(start)&trades.session.lt(end)]
            pnl=part.trade_profit-1.05;stress=pnl-1
            assert len(part)==row.trades
            assert abs(pnl.sum()-row.net_dollars)<1e-6 and abs(stress.sum()-row.stress_net)<1e-6
            assert abs((pnl[pnl>0].sum()/-pnl[pnl<0].sum())-row.profit_factor)<1e-9
            assert abs(row.net_dollars/row.equity_dd-row.net_equity_dd)<1e-9
            daily=pnl.groupby(part.session).sum().cumsum().to_numpy();eq=np.r_[0.,daily]
            assert abs((np.maximum.accumulate(eq)-eq).max()-row.daily_close_dd)<1e-6
    for row in c.itertuples():
        part=s.loc[s.period.eq(row.period)].set_index('policy')
        assert abs(part.loc[row.policy,'net_dollars']-part.loc['control','net_dollars']-row.net_change)<1e-6
    result=dict(all_passed=True,source_zip_hashes=True,independent_interval_union=True,
        all_event_clock_conversions=True,summary_rows_checked=len(s),comparison_rows_checked=len(c),
        code_sha256=sha(__file__))
    (RUN/'independent_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
