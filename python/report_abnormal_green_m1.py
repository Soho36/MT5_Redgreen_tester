"""Rebuild the abnormal-M1 research report and static figure from saved ledgers."""
import json
import shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from abnormal_green_m1 import RUN,DOC


def table(df):
    headers=list(df.columns)
    rows=['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']
    for row in df.itertuples(index=False,name=None):
        rows.append('| '+' | '.join(str(x) for x in row)+' |')
    return '\n'.join(rows)


def main():
    assert json.loads((RUN/'independent_verification.json').read_text())['all_passed']
    summary=pd.read_csv(RUN/'summary.csv')
    base=summary.loc[summary['mode'].eq('directional') & summary.multiplier.eq(10)]
    tr=pd.read_csv(RUN/'10x_directional_trades.csv',parse_dates=['signal_time','entry_time','exit_time'])
    signals=pd.read_csv(RUN/'10x_directional_signals.csv')
    annual=base.loc[base.period.str.fullmatch(r'\d{4}')]
    img=DOC/'img';img.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(2,1,figsize=(11,7),layout='constrained',gridspec_kw={'height_ratios':[1.45,1]})
    for mode,label,col in [('directional','Directional OHLC','#165e9d'),('high_first','High-first sensitivity','#d77831')]:
        t=pd.read_csv(RUN/f'10x_{mode}_trades.csv',parse_dates=['exit_time'])
        ax[0].plot(t.exit_time,t.net.cumsum(),label=label,color=col,lw=1.8,alpha=.9)
    ax[0].axhline(0,color='#999999',lw=.7);ax[0].set_ylabel('Cumulative net USD, one MNQ')
    ax[0].set_title('10x abnormal green M1 breakout | immediate 1R target',loc='left',weight='bold')
    ax[0].legend(loc='upper left');ax[0].grid(alpha=.18)
    ax[1].bar(annual.period,annual.net,color=['#348b71' if v>=0 else '#bc5a55' for v in annual.net])
    ax[1].axhline(0,color='#999999',lw=.7);ax[1].set_ylabel('Annual net USD');ax[1].tick_params(axis='x',rotation=45)
    ax[1].set_title('Annual results; 2026 ends November 13',loc='left');ax[1].grid(axis='y',alpha=.18)
    fig.supxlabel('June 2010–November 2026 | $1.05/trade cost | Python OHLC screen; spread not separately modeled',fontsize=9)
    fig.savefig(img/'results.png',dpi=160);plt.close(fig)
    primary=base.loc[base.period.isin(['2010-15','2016-19','2020-Sep2026','Oct-Nov2026','2016-Nov2026','all'])].copy()
    display=pd.DataFrame({'Period':primary.period,'Trades':primary.trades,'Net $':primary.net.map(lambda x:f'{x:,.2f}'),
                          'Win %':primary.win_pct.map(lambda x:f'{x:.1f}'),'PF':primary.pf.map(lambda x:f'{x:.3f}'),
                          'Mean net R':primary.mean_net_r.map(lambda x:f'{x:.3f}'),
                          'OHLC path DD $':primary.path_equity_dd.map(lambda x:f'{x:,.2f}')})
    best=tr.nlargest(1,'net').iloc[0];total=float(tr.net.sum())
    year=pd.DataFrame({'Year':annual.period,'Signals eligible':annual.eligible,'Trades':annual.trades,'Net $':annual.net.map(lambda x:f'{x:,.2f}')})
    recent=tr.loc[tr.date.ge(20200101)&tr.date.lt(20261001)]
    text=f'''# Abnormally large green M1 breakout: initial 10x screen

Completed 2026-11-24. **Small positive historical result, fragile and uneven;
this initial screen does not establish a robust edge.** One MNQ, $2/point,
$1.05 per completed trade. Full extended continuous NQ source: 5,556,005 M1 bars,
2010-06-07 01:00 through 2026-11-13 23:59, research clock. Python OHLC replay,
not a native MT5 run. No strategy defaults or live settings changed.

## Rule

Green close > open; high-low range >= **10 times the mean high-low range of
exactly the previous 20 candles**, both colours. Signal excluded from its own
reference. Require consecutive minutes within the same session. After close,
buy at its high on a subsequent touch, SL **one tick (0.25 point) below its low**,
immediate TP at **1R from actual entry**, as confirmed by the user. One position.
Worse opening entry/stop gaps are paid. Pending waits until filled, replaced by
another qualifying signal, or session cutoff; ordinary candles and pre-entry
low touches do not cancel it. Flatten at 23:30 or the existing early close.
See [frozen protocol](PROTOCOL.md) for all order and fill assumptions.

## Counts

Of **2,395 raw 10x green signals**, **492** pass eligibility and **446** fill:

- 1,896 excluded because the previous 20 bars cross a minute gap/session boundary.
- 3 lack an immediately following minute; 4 are outside the entry session.
- Of the 492 eligible: 446 filled, 34 expired at the session cutoff, 10 occurred
  while holding a position, and 2 pending orders were replaced.
- Since 2016: 348 eligible signals and 313 trades. This exceeds the predeclared
  100-signal minimum, so **the threshold was not lowered**.

The scan covers every available minute. The continuity requirement materially
reduces early-history counts; raw and excluded signals are retained in the
signal ledger, not silently discarded. Price alone does not establish a news cause.

## Results

{table(display)}

Win percentage and PF use net dollars. Drawdown above is marked along assumed
OHLC paths, including open positions, rather than just closed balance. Full-history
closed-trade DD is $2,240.65. Era rows reset equity at each era's start. Signal
and entry are within the same session; 33 session-flattened trades do not end at
exactly +1R or -1R. No end-of-data marking was needed in the observed run.

![Cumulative and annual results](img/results.png)

## Fragility and execution assumptions

- Largest winner: signal **{best.signal_time}**, range **{best.signal_range:,.2f}
  points**, ratio **{best.ratio:.2f}x**, net **${best.net:,.2f}**. Removing this one
  trade changes full-history net from **${total:,.2f}** to **${total-best.net:,.2f}**;
  2020-Sep2026 changes to **${recent.net.sum()-best.net:,.2f}**. This is a concentration
  diagnostic, not a rule to exclude trades.
- 2026 through November 13: **-$1,644.25** on 25 trades. Positive earlier periods
  therefore do not establish stable annual performance.
- Extra $1/trade reduces all-history net to **$526.20**; extra $2 to **$80.20**.
  Since 2016 these become $910.35 and $597.35. Spread is not separately simulated;
  the stresses do not reproduce actual news-time slippage or bid/ask execution.
- Directional and uniformly low-first paths both net $972.20 with $2,424.90 path DD.
  Uniformly high-first nets $962.20 with **$2,885.40** path DD. These are assumed
  path sensitivities, not formal bounds on all possible within-minute paths.
- 7 trades have entry/stop or stop/target overlap within a minute; 8 entries pay
  a worse opening price; 34 held trades cross missing minutes. Stops use worse
  opens, but missing prices can still hide an earlier level touch.
- Median signal-to-fill delay: **2 minutes**. 156 fills wait >5 minutes; 89 wait
  >30 minutes and 61 >60 minutes; maximum 1,188 minutes. Pending lifetime is an
  explicit research choice, and some fills are far removed from the initial
  jump. No expiry or threshold was optimized after viewing outcomes.
- Fixed one-contract sizing gives larger-dollar weight to larger candles.
  Mean net R is descriptive, not a tested constant-risk sizing policy.

## Annual results

{table(year)}

## Reproduction and verification

Run from the project root:

```powershell
.\\venv\\Scripts\\python.exe -m unittest discover -s python -p test_abnormal_green_m1.py -v
.\\venv\\Scripts\\python.exe python\\abnormal_green_m1.py
.\\venv\\Scripts\\python.exe python\\verify_abnormal_green_m1.py
.\\venv\\Scripts\\python.exe python\\report_abnormal_green_m1.py
```

Focused tests cover lookahead, threshold equality, red/doji/zero references,
gaps, session boundaries, entry and stop gap fills, immediate target, ambiguous
entry/stop ordering, pending persistence, cutoff and final marking. Separate
verification reads raw data again, independently finds all signals with cumulative
sums, checks every first-touch entry and every exit in all three paths, and
rebuilds marked equity DD from the complete price-mark sequence.

Source, protocol, calendar, code and output hashes are saved in
`Reports/abnormal_green_m1_20261124/manifest.json`; independent checks are in
`independent_verification.json`. The same folder contains all detected/excluded
signals and trade ledgers for each path, summary and decision counts. Compact
summary and audit files are copied beside this report. Data and results remain
exploratory; there is no untouched out-of-sample confirmation or identified
scheduled/unscheduled news attribution.
'''
    (DOC/'RESULTS.md').write_text(text,encoding='utf-8')
    for name in ['summary.csv','decisions_summary.csv','independent_verification.json','manifest.json']:
        shutil.copyfile(RUN/name,DOC/name)
    print(DOC/'RESULTS.md');print(img/'results.png')


if __name__=='__main__':main()
