"""Publish the fixed +/-30 minute RTL comparison and execution qualifications."""
import json
import shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from build_news_windows import ROOT,RUN,DOC,sha

LABELS={'control':'Original RTL','entry':'Block entries','flat':'Flatten + block','day':'Skip whole day'}

def table(frame,columns):
    lines=['| '+' | '.join(columns.values())+' |','| '+' | '.join('---' for _ in columns)+' |']
    dollars={'net_dollars','equity_dd','daily_close_dd','avg_net_trade','net_change','ci_low','ci_high',
             'stress_net','stress_equity_dd','control_net','entry_net','flat_net','day_net'}
    for _,row in frame.iterrows():
        values=[]
        for key in columns:
            x=row[key]
            if key=='policy':x=LABELS[x]
            elif key in dollars:
                sign='−' if x<0 else ''
                x=sign+(f'${abs(x):,.0f}' if key!='avg_net_trade' else f'${abs(x):,.2f}')
            elif key=='trades':x=f'{x:,.0f}'
            elif key=='net_mean_r':x=f'{x:+.4f}'
            elif isinstance(x,(float,np.floating)):x=f'{x:.2f}'
            values.append(str(x))
        lines.append('| '+' | '.join(values)+' |')
    return '\n'.join(lines)

def main():
    audit=json.loads((RUN/'verification.json').read_text());independent=json.loads((RUN/'independent_verification.json').read_text())
    assert audit['all_passed'] and independent['all_passed']
    for name,h in audit['output_sha256'].items():assert sha(RUN/name)==h
    s=pd.read_csv(RUN/'summary.csv');c=pd.read_csv(RUN/'comparisons.csv');sensitivity=pd.read_csv(RUN/'schedule_sensitivity.csv')
    for name in ('summary.csv','comparisons.csv','schedule_sensitivity.csv','verification.json','independent_verification.json'):
        shutil.copyfile(RUN/name,DOC/name)
    fig,axes=plt.subplots(2,2,figsize=(12,7),constrained_layout=True)
    colors=['#64748b','#0284c7','#c26722','#0f766e']
    for j,period in enumerate(('2016-19','2020-26')):
        part=s.loc[s.period.eq(period)].set_index('policy').loc[list(LABELS)]
        for i,metric in enumerate(('net_dollars','equity_dd')):
            ax=axes[i,j];bars=ax.bar(range(4),part[metric],color=colors)
            ax.set_xticks(range(4),['Original','Block\nentries','Flatten\n+ block','Skip\nwhole day'])
            ax.set_title(('2016–2019' if j==0 else '2020–September 2026')+' · '+('Net profit' if i==0 else 'Intraday equity drawdown'))
            ax.bar_label(bars,labels=[f'${v:,.0f}' for v in part[metric]],padding=3,fontsize=9)
            ax.set_ylim(0,part[metric].max()*1.18);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
            ax.spines[['top','right']].set_visible(False)
    fig.suptitle('RTL: 30 minutes before and after scheduled major news\nOne contract · $1.05 per trade · native MT5 replays',fontsize=13)
    fig.savefig(DOC/'comparison.png',dpi=160);plt.close(fig)
    ordered=pd.concat([s.loc[s.period.eq(p)].set_index('policy').loc[list(LABELS)].reset_index() for p in ('2016-19','2020-26','2016-26')])
    text='''# RTL: thirty-minute news exclusion windows

Completed 2026-11-11 under the [November 10 frozen protocol](PROTOCOL.md), following the
[whole-day study](../rtl-news-days/RESULTS.md).

**The narrower rule does not produce a consistent improvement.** Blocking new
entries gives a small recent drawdown reduction with almost unchanged profit.
Flattening positions sacrifices more profit and offers little recent drawdown
benefit. Both rules are worse in 2016–19. Keep this as research evidence; the
results do not support adopting the flat-window rule or changing the baseline.

![Native comparison](comparison.png)

## Main comparison

Original uncapped RTL M30/RR1, VWAP off, one MNQ-sized contract ($2/point), all
original entry windows and daily/early-close flatten. Costs: $1.05 per round trip.
DD is sampled **intraday marked-to-market equity drawdown after costs**, not
closed-trade or daily-close drawdown. Native tester uses generated minute-OHLC
quotes; actual-news spreads, slippage, queueing and execution failures are not
modelled. This matters especially when comparing exposure near announcements.

'''
    text+=table(ordered,dict(period='Era',policy='Policy',trades='Trades',net_dollars='Net',equity_dd='Equity DD',net_equity_dd='Net/DD'))
    text+='''

Recent entry blocking loses $204 (0.5%) while lowering DD $364 (6.1%): net/DD
6.46 → 6.85. Only 94 fewer trades (0.9%) remain after the full strategy replay.
Flattening loses $1,692 (4.4%) and lowers DD just $56 (0.9%); net/DD falls to 6.24.
In 2016–19, entry blocking loses $381 with essentially unchanged DD; flattening
loses $1,034 and increases DD $149. Pooled results hide this era disagreement.

The whole-day rule is much stronger in the recent sample, but its earlier-era
failure and dependence on 2025–26 remain. These outcomes suggest that removing
only the immediate announcement window does not reproduce the whole-day result.
They do not establish why: the policies also change later opportunities and exits.

## Exact rules and calendar

- **Block entries:** cancel pending orders at the first available quote on or
  after window start and block new submissions throughout. Existing positions
  retain normal stop/close-based exits. This rule permits news exposure.
- **Flatten + block:** also close existing positions on that quote and remain
  flat after each EA callback during the window.
- Window is **[event −30 minutes, event +30 minutes)**. Start is inclusive, end
  exclusive; overlapping or touching windows merge. Entry logic resumes only
  at the next ordinary M30 new-bar callback. Signal candles may contain news prices.

Scope remains CPI, Employment Situation/payrolls, and scheduled FOMC decisions,
with each associated FOMC press-conference **start** added separately. These are
a core subset of Investing.com's three-star category, not all historical ratings.
No PCE, PPI, ADP, JOLTS, claims, speeches, minutes or emergency Fed meetings.

The calendar has 626 timestamps (533 releases + 93 conference starts), forming
541 merged windows from January 2010 through September 2026. Of these, 525 have
eligible quotes within the native test. BLS releases are 08:30 New York, so their
window is 08:00–09:00. Modern FOMC statement and conference-start windows merge
to 13:30–15:00 New York. That does **not** guarantee avoidance of the whole press
conference. Older Fed times preserve a tradable gap: for example, a 12:30
statement and 14:15 conference give 12:00–13:00 and 13:45–14:45 windows.

Research clock = New York +7 hours (Chicago +8); UTC conversions use US DST,
independently of European DST. All 400 BLS times were checked: 395 release headers
and five prior releases announcing the next date/time. Four 2012 Fed archive
labels differ from the scheduled 12:30 time; contemporaneous minutes explicitly
approve 12:30, which is used here and recorded in the provenance manifest.

Sources include the [Fed's March 2011 timing notice](https://www.federalreserve.gov/newsevents/pressreleases/monetary20110324a.htm),
[2013 timing change](https://www.federalreserve.gov/newsevents/pressreleases/monetary20130313a.htm),
[New York Fed's account of the 2012 schedule](https://libertystreeteconomics.newyorkfed.org/2013/11/a-way-with-words-the-economics-of-the-feds-press-conference/),
individual statements/conference pages and BLS archive releases. Portable
[event times](../../../data/calendars/us_major_news_times_2010_2026.csv),
[merged windows](../../../data/calendars/us_major_news_windows_30m_2010_2026.csv),
[provenance](../../../data/calendars/us_major_news_times_2010_2026_manifest.json),
and [source bundle](../../../data/calendars/us_major_news_times_2010_2026_sources.zip).

Archived publication dates do not establish when every rescheduling was known.
This is not a complete point-in-time schedule. The year-removal check below
retains the earlier study's explicit schedule-quality sensitivity.

## Exposure and execution audit

Across the full native dataset, both window rules cancel 131 pending orders.
No submitted order lies inside a window, and no boundary-quote fills occurred.
Broker processing still precedes the EA callback, so boundary fills are possible
in principle and are covered by focused tests.

Entry blocking leaves **250 positions** exposed within windows, totalling
10,434 minutes. Flat mode makes **277 forced closes**. Four windows have delayed
first quotes (maximum 61 seconds); three positions remain open briefly between
the scheduled boundary and that first quote, totalling 63 seconds. None survives
the first available callback. Every logged first action matches the raw quotes.
Thus even flat mode means first executable quote, not a guaranteed fill exactly
at the clock boundary. Counts include all tested years, not just the recent era.

## Uncertainty, costs and stability

Paired calendar-week P&L bootstrap, 10,000 draws, seed 20261110. These are
descriptive 95% intervals for profit differences, not out-of-sample evidence or
multiple-test-adjusted significance. No random intraday omission claim is made:
that would require additional full strategy replays.

'''
    text+=table(c.loc[c.period.isin(['2016-19','2020-26'])],dict(period='Era',policy='Policy',net_change='Net change',ci_low='95% low',ci_high='95% high'))
    text+='''

The recent profit-change intervals include zero for both window variants. The
early flattening loss has an interval below zero. Additional $1 per round trip
(total $2.05), applied at each native closure, gives:

'''
    text+=table(ordered.loc[ordered.period.isin(['2016-19','2020-26'])],dict(period='Era',policy='Policy',stress_net='Stressed net',stress_equity_dd='Stressed DD',stress_net_equity_dd='Stressed net/DD'))
    text+='''

All variants lose money in 2016–19 at the higher cost. The entry-only rule's
recent risk tradeoff remains small; extra flattening does not rescue it.
The complete [summary CSV](summary.csv) also reports PF, average trade, average
gross/net R and daily-close DD. Main per-trade results:

'''
    text+=table(ordered.loc[ordered.period.isin(['2016-19','2020-26'])],dict(period='Era',policy='Policy',profit_factor='PF',avg_net_trade='Avg net trade',net_mean_r='Avg net R',daily_close_dd='Daily-close DD'))
    text+='''

Removing 2013, 2025 and 2026 leaves the recent sample at **2020–24**:

'''
    text+=table(sensitivity.loc[sensitivity.period.eq('2020-26')],dict(policy='Policy',net_dollars='Net',equity_dd='Equity DD',net_equity_dd='Net/DD'))
    text+='''

Both window variants then lose about $300 relative to the original and reduce
DD about $185: a small risk/profit tradeoff. The strong full-day profit advantage
disappears too. This changes the sample; it does not prove those dates were wrong.

Annual net profits follow. 2010 starts with available June data; 2026 ends
September 30. All 2010–15 aggregate variants remain loss-making. Annual DD and
other metrics are included in the summary CSV.

'''
    annual=s.loc[s.period.str.fullmatch(r'\d{4}')].pivot(index='period',columns='policy',values='net_dollars')
    annual=annual.rename(columns={k:k+'_net' for k in LABELS}).reset_index().rename(columns={'period':'year'})
    annual.to_csv(DOC/'annual_net.csv',index=False)
    text+=table(annual,dict(year='Year',control_net='Original',entry_net='Block entries',flat_net='Flatten + block',day_net='Skip whole day'))
    text+='''

## Verification and reproduction

Three new native MT5 runs compiled without errors or warnings. Disabled control
is byte-identical to the original 25,833-trade ledger. Independent full replay
of 5,511,965 source minutes matches every submission bar, fill/exit minute, entry,
stop and exit price for all three runs (25,833 / 25,601 / 25,618 trades). Native
reports, ledgers, statistics and gross-equity drawdown reconcile. Daily envelopes
match direct full equity paths, including external fees at zero-profit closes.
The old whole-day benchmark reconciles to its already published results.
The incomplete October 1, 2026 trade is included in accounting audits and excluded
from all published performance tables.

Separate checks validate all source ZIP hashes, all clock conversions, an
independently reconstructed interval union, 84 metric rows and 12 comparisons.
Twelve focused tests cover release dates, whole-day controls, half-open/merged
intervals, US DST, quarter-hour boundaries, pending cancellation, boundary fills,
forced exits and zero-profit fees at both cost levels.

Evidence: `Reports/rtl_news_windows_20261110/`. Portable checks:
[native/replay audit](verification.json), [separate verification](independent_verification.json).
Research source and INIs are generated by `python/prepare_rtl_news_windows.py`;
no production EA setting changes. Run preparation only in a fresh output folder;
completed native outputs are preserved. Existing raw minutes, original baseline
and whole-day study are required for the full replay.

```powershell
& .\\venv\\Scripts\\python.exe python/download_news_times.py
& .\\venv\\Scripts\\python.exe python/build_news_windows.py
& .\\venv\\Scripts\\python.exe python/prepare_rtl_news_windows.py
& .\\venv\\Scripts\\python.exe python/run_rtl_news_windows.py
& .\\venv\\Scripts\\python.exe python/analyze_rtl_news_windows.py
& .\\venv\\Scripts\\python.exe python/verify_rtl_news_windows.py
& .\\venv\\Scripts\\python.exe python/report_rtl_news_windows.py
& .\\venv\\Scripts\\python.exe -m unittest discover -s python -p 'test_rtl_news*.py' -v
```

Calendar rebuilding also requires the saved BLS time-check excerpts, available
in the portable source bundle. Neither width optimization nor production adoption
is part of this study.
'''
    (DOC/'RESULTS.md').write_text(text,encoding='utf-8')
    print('Published',DOC/'RESULTS.md')

if __name__=='__main__':main()
