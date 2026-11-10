"""Publish the frozen RTL news-day study with its qualifications and evidence."""
import json
import shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from build_news_calendar import ROOT,RUN,OUT,DOC,sha

LABELS={'control':'Original RTL','skip_cpi':'Skip CPI','skip_payrolls':'Skip payrolls',
        'skip_fomc':'Skip FOMC','skip_all':'Skip all three'}

def table(frame,columns):
    lines=['| '+' | '.join(columns.values())+' |','| '+' | '.join('---' for _ in columns)+' |']
    dollars={'net_dollars','equity_dd','daily_close_dd','avg_net_trade','net_change','net_change_ci_low',
             'net_change_ci_high','random_net_median','random_dd_median','control_net','filtered_net','change',
             'control_dd','filtered_dd'}
    integer={'trades','removed_sessions','removed_trades','sessions'}
    for _,row in frame.iterrows():
        values=[]
        for key in columns:
            x=row[key]
            if key=='policy':x=LABELS[x]
            elif key in dollars:x=f'${x:,.0f}' if key!='avg_net_trade' else f'${x:,.2f}'
            elif key in integer:x=f'{x:,.0f}'
            elif isinstance(x,(float,np.floating)):x=f'{x:.2f}'
            values.append(str(x))
        lines.append('| '+' | '.join(values)+' |')
    return '\n'.join(lines)

def main():
    audit=json.loads((RUN/'verification.json').read_text())
    independent=json.loads((RUN/'independent_verification.json').read_text())
    assert audit['all_passed'] and independent['all_passed']
    for name,value in audit['output_sha256'].items():assert sha(RUN/name)==value
    s=pd.read_csv(RUN/'summary.csv');c=pd.read_csv(RUN/'comparisons.csv')
    sensitivity=pd.read_csv(RUN/'schedule_sensitivity.csv')
    for name in ('summary.csv','comparisons.csv','schedule_sensitivity.csv','calendar_counts.csv'):
        shutil.copyfile(RUN/name,DOC/name)
    fig,axes=plt.subplots(2,2,figsize=(12,7),constrained_layout=True)
    colors=['#64748b','#38bdf8','#0ea5e9','#6366f1','#0f766e']
    for j,period in enumerate(('2016-19','2020-26')):
        part=s.loc[s.period.eq(period)].set_index('policy').loc[list(LABELS)]
        for i,metric in enumerate(('net_dollars','equity_dd')):
            ax=axes[i,j]
            bars=ax.bar(range(5),part[metric],color=colors)
            ax.set_xticks(range(5),['Original','Skip\nCPI','Skip\npayrolls','Skip\nFOMC','Skip\nall three'])
            ax.set_title(('2016–2019' if j==0 else '2020–September 2026')+' · '+('Net profit' if i==0 else 'Intraday equity drawdown'))
            ax.bar_label(bars,labels=[f'${v:,.0f}' for v in part[metric]],padding=3,fontsize=8)
            ax.set_ylim(0,part[metric].max()*1.15);ax.grid(axis='y',alpha=.15)
            ax.set_axisbelow(True);ax.spines[['top','right']].set_visible(False)
    fig.suptitle('RTL: exclude whole sessions with scheduled CPI, payrolls or FOMC decisions\nOne contract · $1.05 per trade · five native MT5 runs',fontsize=12)
    fig.savefig(DOC/'comparison.png',dpi=160);plt.close(fig)
    text='''# RTL: skipping scheduled major US news days

Completed 2026-11-10 under the [frozen protocol](PROTOCOL.md).

**Promising recent risk reduction, but not a stable improvement across eras.**
Skipping CPI, payroll and scheduled FOMC announcement sessions raises recent net
profit and lowers intraday equity drawdown substantially. In 2016–19 it lowers
profit and increases drawdown. No baseline setting is changed.

![Native comparison](comparison.png)

## Main comparison

Original uncapped RTL M30, RR=1, one MNQ-sized contract ($2/point), all original
entry windows, VWAP off, daily/early-close flatten. Costs are $1.05 per round trip.
DD below is sampled **intraday marked-to-market equity** after external costs,
not just closed trades or end-of-day equity. Generated 1-minute OHLC ticks are
used, consistent with existing research; actual-news slippage is not modelled.

'''
    cols=dict(period='Era',policy='Policy',trades='Trades',net_dollars='Net',equity_dd='Equity DD',net_equity_dd='Net/DD')
    ordered=pd.concat([s.loc[s.period.eq(p)].set_index('policy').loc[list(LABELS)].reset_index()
                       for p in ('2016-19','2020-26','2016-26')],ignore_index=True)
    text+=table(ordered,cols)
    text+='''

For **2020–September 2026**, the combined rule raises net profit by $3,739
(9.7%) and reduces equity DD by $1,905 (32.1%). Net/DD rises from 6.46 to 10.44.
It skips 210 of 1,745 available sessions (12.0%) and removes 1,292 trades (12.3%).
For **2016–19**, it reduces profit by $703 (15.9%) and increases DD by $127 (5.4%).
Pooled 2016–September 2026 net rises $3,035 (7.1%), but pooling hides that disagreement.

The individual exclusions are less impressive recently: CPI adds $370 while
reducing DD $771; payrolls add $2,351 while reducing DD $476; FOMC adds $684 while
reducing DD $74. The union is a prespecified fourth filter, not a combination
selected after seeing these outcomes. Overlapping announcements count once per
session, so the three individual profit differences need not sum to the union.

## Does it beat simply trading fewer days?

10,000 random exclusions per filter/era, preserving the number excluded within
each calendar year and weekday, including sessions without a baseline trade.
Seed 20261110. Every retained session keeps its full native equity path; the
path is reassembled chronologically, so the control measures intraday DD.

The combined filter's recent net/DD exceeds 99.67% of matched random exclusions;
its DD is no worse than 99.64% of them. Recent net profit exceeds 95.79%.
In 2016–19 its net/DD is only at the 32.37th percentile. These descriptive ranks
are not multiple-test-adjusted significance or evidence of live profitability.

'''
    text+=table(c.loc[c.policy.eq('skip_all')],dict(period='Era',net_change='Net change',
        net_change_ci_low='95% interval low',net_change_ci_high='95% interval high',
        random_net_median='Random median net',random_dd_median='Random median DD',net_dd_percentile='Net/DD percentile'))
    text+='''

Intervals resample paired calendar-week P&L differences (10,000 draws). The recent
profit-change interval is approximately **−$5,413 to +$13,501** and includes zero.
The filter's drawdown result is stronger than its estimated profit advantage.

## Annual concentration and schedule sensitivity

'''
    annual=s.loc[s.period.str.fullmatch(r'\d{4}') & s.policy.isin(['control','skip_all'])]
    pivot=annual.pivot(index='period',columns='policy',values=['net_dollars','equity_dd'])
    ann=pd.DataFrame(dict(year=pivot.index,control_net=pivot['net_dollars']['control'].to_numpy(),
        filtered_net=pivot['net_dollars']['skip_all'].to_numpy(),
        change=(pivot['net_dollars']['skip_all']-pivot['net_dollars']['control']).to_numpy(),
        control_dd=pivot['equity_dd']['control'].to_numpy(),filtered_dd=pivot['equity_dd']['skip_all'].to_numpy()))
    ann.to_csv(DOC/'annual_combined.csv',index=False)
    text+=table(ann,dict(year='Year',control_net='Original net',filtered_net='Skip-all net',change='Difference',control_dd='Original DD',filtered_dd='Skip-all DD'))
    text+='''

2026 ends September 30; 2010 begins with available June data. The recent profit
gain comes mainly from 2022, 2025 and 2026, offset by substantial profit sacrificed
in 2023–24. The combined rule improves profit in 4 of the 7 recent annual slices.

The schedule-quality sensitivity removes 2013, 2025 and 2026 entirely because
publication disruptions require extra point-in-time schedule evidence. For the
recent sample this leaves **2020–24**: original net $21,719 / DD $4,463 versus
filtered net $20,515 / DD $4,037. Profit falls 5.5%, DD falls 9.5%, and net/DD
only moves from 4.87 to 5.08. Thus the headline gain is **not robust to removing
the latest two years**. Excluding 2020 as well leaves the same modest risk/profit
tradeoff. This changes the sample; it does not prove those release dates are wrong.

2010–15 remains loss-making: original −$7,496 versus filtered −$6,269. The combined
rule's risk-adjusted rank is ordinary among matched random exclusions there.

## Calendar and exact rule

- [BLS CPI archive](https://www.bls.gov/bls/news-release/cpi.htm): headline and core
  inflation belong to one release date.
- [BLS Employment Situation archive](https://www.bls.gov/bls/news-release/empsit.htm):
  payrolls, unemployment and wages belong to one release date.
- [Fed historical meeting archive](https://www.federalreserve.gov/monetarypolicy/fomc_historical_year.htm)
  and [recent calendars](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm):
  scheduled policy announcement day, not the first day of a two-day meeting.

533 events on 523 distinct dates from January 2010 through September 2026.
This is a **core subset** of the user's Investing.com three-star definition,
not a reconstruction of all historical Investing.com ratings. It excludes PCE,
PPI, ADP, JOLTS, claims, speeches and FOMC minutes in this first study.

The Fed parser excludes 14 unscheduled/cancelled/notation-vote items, including
the March 2020 emergencies and cancelled March 17–18 meeting. The BLS archives
contain 11 releases per category in 2025, versus 12 in ordinary full years;
missing releases are not invented. Actual archived publication dates are used,
including the 2013 shutdown delays. No release value or sentiment enters the rule.

The CSV date is the US announcement date. For these daytime releases it is also
the date in the research clock (Chicago+8 / New York+7). Skip the whole research
session, including its overnight portion. Bars/bookkeeping still advance.
All native reported trades and filled orders stay within their submission dates;
the excluded runs contain no trades on excluded dates. No pre-news positions
remain to flatten in this dataset.

**Calendar limitation:** archived publication dates do not establish exactly
when every rescheduled date became known. This is a release-day exclusion study,
not a fully reconstructed vintage calendar. A deployable scheduled filter needs
advance-known calendars and cancellation updates. The year-removal sensitivity
above makes the important limitation visible.

## Verification and reproduction

Five native MT5 runs completed; the disabled control is byte-identical to the
saved RTL ledger. Every candidate's native report, fills, exits and profit match
the baseline's surviving sessions exactly. Independently checking the raw ledgers
gives the same result. Full native equity paths match the reassembled session
paths, and all five gross-equity DD figures match MT5's own report statistic.
Six focused tests cover dates, unscheduled meetings, duplicate-day unions,
drawdown reconstruction, matched sampling and the zero-profit closure edge case.

Two zero-profit closes in 2011/2013 have no observer sample because gross equity
did not change. Their $1.05 fees are inserted at the actual close timestamps;
all daily net changes then reconcile exactly. Equity DD resets its running high
only at each reported era/year boundary. Costs at equal one-second timestamps
follow the existing at-close convention.

The tester includes one incomplete October 1, 2026 trade for exact old-control
reconciliation. All published tables exclude it. This explains the $133.95
difference from older RTL totals that included that trade.

Artifacts: `Reports/rtl_news_days_20261110/`; [summary](summary.csv),
[matched comparisons](comparisons.csv), [sensitivity](schedule_sensitivity.csv),
[annual table](annual_combined.csv). Calendar and hashed source snapshots are
in `data/calendars/us_major_news_2010_2026*`. The source ZIP permits offline rebuild;
the BLS web-reader snapshots preserve resolved dated official URLs because direct
HTTP requests returned 403. Federal Reserve snapshots are original HTML.

```powershell
.\\venv\\Scripts\\python.exe python\\build_news_calendar.py
.\\venv\\Scripts\\python.exe -m unittest discover -s python -p test_rtl_news_days.py -v
# Prepare/run only for a fresh study directory; existing artifacts are protected.
.\\venv\\Scripts\\python.exe python\\prepare_rtl_news_days.py
.\\venv\\Scripts\\python.exe python\\run_rtl_news_days.py
.\\venv\\Scripts\\python.exe python\\analyze_rtl_news_days.py
.\\venv\\Scripts\\python.exe python\\verify_rtl_news_days.py
.\\venv\\Scripts\\python.exe python\\report_rtl_news_days.py
```

The historical eras have already been used extensively for research. No untouched
holdout or live adoption claim is made. This supports further validation of the
combined filter, not changing the baseline on the strength of the pooled result.
'''
    (DOC/'RESULTS.md').write_text(text,encoding='utf-8')
    print('Published',DOC/'RESULTS.md')

if __name__=='__main__':main()
