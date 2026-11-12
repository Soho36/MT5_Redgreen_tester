"""Prepare eight fixed native tests; whole-session gates isolate trading overlays."""
import json
import re
import shutil
import pandas as pd
import whipsaw_days as wd
from whipsaw_followup_features import verify_original
from prepare_whipsaw_days import ROOT, digest

RUN = ROOT / 'Reports/whipsaw_native_20261112'
DOC = ROOT / 'docs/baseline/whipsaw-native'
BASE = ROOT / 'Reports/rtl_gg_exclude16_20261101'
EXPERT = 'Whipsaw_session_research'


def event_calendar(panel, table):
    pairs = []
    for day, row in panel.loc[panel.whipsaw].iterrows():
        for h in (1, 2, 3):
            i = int(row.position) + h
            if i < len(table) and table.index[i] < pd.Timestamp(wd.END):
                pairs.append(dict(event=day, session=table.index[i], horizon=h))
    return pd.DataFrame(pairs)


def prepare():
    assert not (RUN / 'manifest.json').exists(), 'Preserve prepared study'
    verify_original()
    RUN.mkdir(parents=True, exist_ok=True)
    bars = wd.read_m30()
    panel, table = wd.event_panel(bars), wd.session_table(bars)
    assert wd.counts(panel) == wd.EXPECTED_COUNTS
    pairs = event_calendar(panel, table)
    pairs.to_csv(RUN / 'event_sessions.csv', index=False)
    masks = {}
    for r in pairs.itertuples():
        key = int(r.session.strftime('%Y%m%d'))
        masks[key] = masks.get(key, 0) | (1 << (r.horizon - 1))
    keys = sorted(masks)
    header = '''// Research calendar: every event predates the permitted session.
input int WhipsawMask=0;
int WS_DATE[]={DATES};
int WS_MASK[]={MASKS};
bool WhipsawAllowed(datetime t) {
 if(WhipsawMask==0) return true;
 MqlDateTime d;TimeToStruct(t,d);int date=d.year*10000+d.mon*100+d.day;
 int lo=0,hi=ArraySize(WS_DATE)-1;
 while(lo<=hi) {int mid=(lo+hi)/2;
 if(WS_DATE[mid]==date) return (WS_MASK[mid]&WhipsawMask)!=0;
 if(WS_DATE[mid]<date) lo=mid+1;else hi=mid-1;}
 return false;
}
'''.replace('DATES', ','.join(map(str, keys))).replace('MASKS', ','.join(str(masks[k]) for k in keys))
    (RUN / 'whipsaw_session.mqh').write_text(header)
    source = (BASE / 'RTL_GG_exclude16_replay.mq5').read_text(encoding='utf-8')
    anchor = '#include "window_equity_research.mqh"'
    assert source.count(anchor) == 1
    source = source.replace(anchor, anchor + '\n#include "whipsaw_session.mqh"')
    anchor = '   // 🔹 time window check (ENTRY ONLY)'
    assert source.count(anchor) == 1
    source = source.replace(anchor, '   if(!WhipsawAllowed(sessionBar)) {CancelAllOrders();return;}\n\n' + anchor)
    (RUN / (EXPERT + '.mq5')).write_text(source, encoding='utf-8')
    for n in ('early_closes.mqh', 'stock_early_closes.mqh', 'rtl_session_vwap.mqh', 'window_equity_research.mqh'):
        shutil.copyfile(BASE / n, RUN / n)
    jobs = []
    for strategy in ('rtl', 'gg'):
        ini = (BASE / f'ex16_20261101_{strategy}_base_all.ini').read_text(encoding='utf-16')
        for policy, mask, rr in [('control', 0, 1), ('day1', 1, 1), ('days123', 7, 1), ('day1_rr2', 1, 2)]:
            tag = f'whipnative_20261112_{strategy}_{policy}'
            text = ini
            for k, v in dict(Expert='CodexResearch\\' + EXPERT + '.ex5', Report=tag + '.htm',
                             RunTag=tag, LogVwapDecisions='false', RiskReward=str(rr)).items():
                assert len(re.findall('^' + k + '=.*$', text, re.M)) == 1
                text = re.sub('^' + k + '=.*$', lambda _: k + '=' + v, text, flags=re.M)
            text = text.replace('[TesterInputs]', f'[TesterInputs]\nWhipsawMask={mask}')
            fields = re.findall(r'^input\s+\w+\s+(\w+)\s*=', source + '\n' + header, re.M)
            given = re.findall(r'^(\w+)=', text.split('[TesterInputs]')[1].split('[', 1)[0], re.M)
            assert sorted(fields) == sorted(given)
            (RUN / (tag + '.ini')).write_text(text, encoding='utf-16')
            jobs.append(dict(tag=tag, strategy=strategy, policy=policy, mask=mask, rr=rr,
                outputs=[f'rtlvwap_{tag}_{rr:.2f}.csv', f'rtlvwap_{tag}_{rr:.2f}_stats.csv', f'window_equity_{tag}.bin']))
    manifest = dict(expert=EXPERT, jobs=jobs, counts=wd.counts(panel),
                    protocol_sha256=digest(DOC / 'PROTOCOL.md'),
                    prepared_sha256={p.name: digest(p) for p in RUN.iterdir() if p.is_file()})
    (RUN / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print('Prepared eight native jobs', flush=True)


if __name__ == '__main__':
    prepare()
