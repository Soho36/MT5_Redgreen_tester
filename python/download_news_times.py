"""Fetch official FOMC release pages and historical press-conference timing notices."""
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from build_news_calendar import ROOT,OUT,sha

RUN=ROOT/'Reports/rtl_news_windows_20261110'
SOURCES=RUN/'sources'
OLD=ROOT/'Reports/rtl_news_days_20261110/sources'
NOTICES={
 'notice_20110324.html':'https://www.federalreserve.gov/newsevents/pressreleases/monetary20110324a.htm',
 'notice_20130313.html':'https://www.federalreserve.gov/newsevents/pressreleases/monetary20130313a.htm',
 'nyfed_2012_timing.html':'https://libertystreeteconomics.newyorkfed.org/2013/11/a-way-with-words-the-economics-of-the-feds-press-conference/',
 'historical_timing_table.html':'https://www.federalreserve.gov/pubs/ifdp/2014/1101/ifdp1101.htm',
 'minutes_20120125.html':'https://www.federalreserve.gov/monetarypolicy/fomcminutes20120125.htm',
 'minutes_20120425.html':'https://www.federalreserve.gov/monetarypolicy/fomcminutes20120425.htm',
 'minutes_20120620.html':'https://www.federalreserve.gov/monetarypolicy/fomcminutes20120620.htm',
 'minutes_20120913.html':'https://www.federalreserve.gov/monetarypolicy/fomcminutes20120913.htm'}

def conference_links():
    links={}
    for path in sorted(OLD.glob('fed_*.html')):
        text=path.read_text(encoding='utf-8')
        for url,day in re.findall(r'href="((?:https://www.federalreserve.gov)?/monetarypolicy/fomcpres(?:s)?conf(\d{8})\.htm)"',text):
            links[day]=url if url.startswith('https:') else 'https://www.federalreserve.gov'+url
    return links

def fetch(item):
    name,url=item
    path=SOURCES/name
    if not path.exists():
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req,timeout=40) as response:payload=response.read()
        path.write_bytes(payload)
    return dict(file=name,url=url,sha256=sha(path),bytes=path.stat().st_size)

def main():
    SOURCES.mkdir(parents=True,exist_ok=True)
    events=pd.read_csv(OUT/'us_major_news_2010_2026.csv')
    dates=set(events.loc[events.event.eq('FOMC'),'date'].str.replace('-',''))
    urls=[('statement_'+row.date.replace('-','')+'.html',row.source_url)
          for row in events.loc[events.event.eq('FOMC')].itertuples()]
    urls += [('conference_'+day+'.html',url) for day,url in conference_links().items() if day in dates]
    urls+=list(NOTICES.items())
    results=[];failures=[]
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures=[(item,pool.submit(fetch,item)) for item in urls]
        for item,future in futures:
            try:results.append(future.result())
            except Exception as exc:failures.append(dict(file=item[0],url=item[1],error=str(exc)))
    (SOURCES/'downloads.json').write_text(json.dumps(dict(sources=results,failures=failures),indent=2)+'\n',encoding='utf-8')
    print('Fetched',len(results),'sources; failures:',failures)

if __name__=='__main__':main()
