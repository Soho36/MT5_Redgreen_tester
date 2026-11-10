"""Build a dated, auditable CPI/jobs/scheduled-FOMC calendar from official archives."""
from __future__ import annotations
import hashlib
import html
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / 'Reports/rtl_news_days_20261110'
SOURCES = RUN / 'sources'
OUT = ROOT / 'data/calendars'
DOC = ROOT / 'docs/baseline/rtl-news-days'

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def clean(text):
    return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', ' ', text))).strip()

def bls_records(text, source):
    urls = sorted(set(re.findall(r'https://www\.bls\.gov/news\.release/archives/(?:cpi|empsit)_\d{8}\.htm', text)))
    records = []
    for url in urls:
        code, date = re.search(r'(cpi|empsit)_(\d{8})', url).groups()
        date = datetime.strptime(date, '%m%d%Y').strftime('%Y-%m-%d')
        records.append(dict(date=date, event='CPI' if code == 'cpi' else 'PAYROLLS',
                            source_url=url, source_file=source, release_time_et='08:30',
                            basis='official archived release URL', schedule_caveat='archive_not_vintage_schedule'))
    return records

def fed_records(text, source, recent=False):
    records, excluded = [], []
    if not recent:
        chunks = re.split(r'<h5\b[^>]*>', text, flags=re.I)[1:]
        for chunk in chunks:
            heading, body = chunk.split('</h5>', 1)
            label = clean(heading)
            links = re.findall(r'href="([^"]+)"[^>]*>\s*Statement\s*</a>', body, re.I)
            if any(word in label.lower() for word in ('unscheduled', 'cancelled', 'notation', 'conference call')):
                excluded.append(dict(source_file=source, label=label, reason='not scheduled announcement', links=links))
                continue
            assert 'Meeting' in label and len(links) == 1, (source,label,links)
            match = re.search(r'monetary/?(\d{8})',links[0])
            assert match, links
            date = datetime.strptime(match[1],'%Y%m%d').strftime('%Y-%m-%d')
            records.append(dict(date=date,event='FOMC',source_url='https://www.federalreserve.gov'+links[0],
                                source_file=source,release_time_et='',basis=label,schedule_caveat='scheduled_meeting_archive'))
    else:
        # A row has one month/date and its statement. Avoid minutes, policy-framework
        # statements and implementation notes, which are distinct links.
        sections = re.split(r'<h4>\s*<a[^>]*>(\d{4}) FOMC Meetings</a>\s*</h4>', text)
        assert len(sections)>2
        for year, body in zip(sections[1::2],sections[2::2]):
            rows = re.split(r'<div class="[^"]*\brow fomc-meeting"[^>]*>',body)[1:]
            for row in rows:
                label = clean(row[:row.find('Statement:')])
                link = re.search(r'Statement:</strong>.*?href="(/newsevents/pressreleases/monetary(\d{8})[a-z]\.htm)"',row,re.S)
                if not link:  # future scheduled meetings without a statement
                    continue
                if 'unscheduled' in label.lower():
                    excluded.append(dict(source_file=source,label=label,reason='unscheduled',links=[link[1]]))
                    continue
                date = datetime.strptime(link[2],'%Y%m%d').strftime('%Y-%m-%d')
                assert date.startswith(year), (date,year)
                records.append(dict(date=date,event='FOMC',source_url='https://www.federalreserve.gov'+link[1],
                                    source_file=source,release_time_et='',basis='scheduled '+label,
                                    schedule_caveat='scheduled_meeting_archive'))
    return records, excluded

def main():
    records, excluded = [], []
    sources = sorted(SOURCES.glob('bls_*_web_*.txt'))+sorted(SOURCES.glob('fed_*.html'))
    if not sources:
        # Restore only our flat, checked source inventory, never arbitrary zip paths.
        archive_path=OUT/'us_major_news_2010_2026_sources.zip'
        saved=json.loads((OUT/'us_major_news_2010_2026_manifest.json').read_text(encoding='utf-8'))
        with zipfile.ZipFile(archive_path) as archive:
            assert set(archive.namelist())==set(saved['sources'])
            SOURCES.mkdir(parents=True,exist_ok=True)
            for name in archive.namelist():
                assert Path(name).name==name and re.fullmatch(r'(?:bls_\w+\.txt|fed_\w+\.html)',name)
                payload=archive.read(name)
                assert hashlib.sha256(payload).hexdigest()==saved['sources'][name]
                (SOURCES/name).write_bytes(payload)
        sources=sorted(SOURCES.glob('bls_*_web_*.txt'))+sorted(SOURCES.glob('fed_*.html'))
    for path in sources:
        text = path.read_text(encoding='utf-8',errors='replace')
        if path.name.startswith('bls'):
            records += bls_records(text,path.name)
        else:
            rows, omissions = fed_records(text,path.name,path.name=='fed_recent.html')
            records += rows
            excluded += omissions
    frame = pd.DataFrame(records).drop_duplicates(['event','date','source_url'])
    frame = frame.loc[frame.date.ge('2010-01-01') & frame.date.lt('2026-10-01')].sort_values(['date','event'])
    assert not frame.duplicated(['event','date']).any()
    frame['research_session'] = frame.date
    # Times of old FOMC releases changed. No guessed intraday timestamps are used.
    counts = frame.assign(year=frame.date.str[:4]).groupby(['year','event']).size().unstack(fill_value=0)
    for year in range(2010,2025):
        assert counts.loc[str(year),'CPI']==12, (year,'CPI',counts.loc[str(year)])
        assert counts.loc[str(year),'PAYROLLS']==12, (year,'PAYROLLS',counts.loc[str(year)])
        assert counts.loc[str(year),'FOMC']==(7 if year==2020 else 8), (year,'FOMC',counts.loc[str(year)])
    assert (counts.loc['2026']==pd.Series({'CPI':9,'FOMC':6,'PAYROLLS':9})).all()
    assert (counts.loc['2025']==pd.Series({'CPI':11,'FOMC':8,'PAYROLLS':11})).all()
    assert not frame.date.isin(['2020-03-03','2020-03-15','2020-03-18']).where(frame.event.eq('FOMC'),False).any()
    assert '2013-10-22' in set(frame.loc[frame.event.eq('PAYROLLS'),'date'])
    assert '2013-10-30' in set(frame.loc[frame.event.eq('CPI'),'date'])
    path=OUT/'us_major_news_2010_2026.csv'
    frame.to_csv(path,index=False)
    counts.to_csv(RUN/'calendar_counts.csv')
    manifest=dict(built='2026-11-10',coverage=['2010-01-01','2026-09-30'],events=len(frame),
                  unique_dates=frame.date.nunique(),calendar_sha256=sha(path),
                  sources={p.name:sha(p) for p in sources},excluded_fed_items=excluded,
                  bls_archive_pages=['https://www.bls.gov/bls/news-release/cpi.htm',
                                     'https://www.bls.gov/bls/news-release/empsit.htm'],
                  access='BLS resolved official archive links via web reader (HTTP download 403); Fed direct HTML',
                  counts=counts.to_dict(),schedule_caveat='Release archives are not full point-in-time schedules; sensitivity omits 2013/2025/2026.')
    (OUT/'us_major_news_2010_2026_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    with zipfile.ZipFile(OUT/'us_major_news_2010_2026_sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for source in sources:
            info=zipfile.ZipInfo(source.name,date_time=(2026,11,10,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,source.read_bytes())
    print(counts.to_string())
    print(f'{len(frame)} events on {frame.date.nunique()} dates; {len(excluded)} non-scheduled Fed items excluded')

if __name__=='__main__':main()
