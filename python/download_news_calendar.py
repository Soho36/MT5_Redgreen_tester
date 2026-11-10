"""Cache public official calendars; no credentials or economic values needed."""
from pathlib import Path
import hashlib
import json
import urllib.request
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / 'Reports/rtl_news_days_20261110/sources'

def fetch(item):
    name, url = item
    path = CACHE / name
    if not path.exists():
        request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html'})
        with urllib.request.urlopen(request, timeout=40) as response:
            body = response.read()
        path.write_bytes(body)
    body = path.read_bytes()
    return dict(file=name, url=url, sha256=hashlib.sha256(body).hexdigest(), bytes=len(body))

def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    urls = [(f'bls_{event}.html', f'https://www.bls.gov/bls/news-release/{event}.htm') for event in ('cpi', 'empsit')]
    urls += [(f'fed_{year}.html', f'https://www.federalreserve.gov/monetarypolicy/fomchistorical{year}.htm') for year in range(2010,2021)]
    urls += [('fed_recent.html', 'https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm')]
    if '--alternatives' in sys.argv:
        urls = [
            ('bls_cpi_query.html', 'https://www.bls.gov/bls/news-release/cpi.htm?archive=1'),
            ('bls_cpi_no_www.html', 'https://bls.gov/bls/news-release/cpi.htm'),
            ('bls_2016.html', 'https://www.bls.gov/schedule/2016/home.htm'),
            ('bls_cpi_http.html', 'http://www.bls.gov/bls/news-release/cpi.htm')]
    results = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [(item, pool.submit(fetch,item)) for item in urls]
        for item, future in futures:
            try:
                result = future.result()
                results.append(result)
                print(item[0], result['bytes'], flush=True)
            except Exception as exc:
                print(item[0], type(exc).__name__, str(exc), flush=True)
    manifest = CACHE / ('alternatives.json' if '--alternatives' in sys.argv else 'downloads.json')
    manifest.write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
    if len(results) != len(urls):
        raise SystemExit('Some sources unavailable; preserve successes and audit alternatives.')

if __name__ == '__main__':
    main()
