"""Publish verified first-minute news results and a complete tester EA package."""
import json
import shutil
import zipfile
import pandas as pd
from run_news_first_minute import ROOT,RUN,DOC,EXPERT,sha

def direction_results():
    rows=[]
    periods={'2010-15':('2010-01-01','2016-01-01'),'2016-19':('2016-01-01','2020-01-01'),
             '2020-26':('2020-01-01','2026-10-01'),'2016-26':('2016-01-01','2026-10-01'),
             'full':('2010-01-01','2026-10-01')}
    for policy in ['both','cpi','payrolls']:
        trades=pd.read_csv(RUN/f'{policy}_trades.csv',parse_dates=['session','exit_time'])
        for period,(start,end) in periods.items():
            part=trades.loc[trades.session.ge(start)&trades.session.lt(end)]
            subtotal=0.;count=0
            for direction,label in [(1,'Long'),(-1,'Short')]:
                p=part.loc[part.direction.eq(direction)].sort_values('exit_time');net=p.net_dollars
                loss=-net[net.lt(0)].sum();equity=pd.concat([pd.Series([0.]),net.cumsum()],ignore_index=True)
                rows.append(dict(policy=policy,period=period,direction=label,trades=len(p),gross=p.trade_profit.sum(),
                    net=net.sum(),win_rate=net.gt(0).mean(),profit_factor=net[net.gt(0)].sum()/loss if loss else float('nan'),
                    avg_net=net.mean(),mean_net_r=p.net_r.mean(),median_reward_risk=p.reward_risk.median(),
                    closed_trade_dd=(equity.cummax()-equity).max(),stress_net=net.sum()-len(p)))
                subtotal+=net.sum();count+=len(p)
            assert count==len(part) and abs(subtotal-part.net_dollars.sum())<1e-7
    result=pd.DataFrame(rows)
    result.to_csv(DOC/'direction_summary.csv',index=False)
    return result

def table(frame,columns):
    lines=['| '+' | '.join(columns.values())+' |','| '+' | '.join('---' for _ in columns)+' |']
    for _,r in frame.iterrows():
        row=[]
        for col in columns:
            v=r[col]
            if col in ['net','gross','equity_dd','stress_net','avg_net']:v=f'{v:,.2f}'
            elif col=='win_rate':v=f'{v*100:.1f}%'
            elif col in ['profit_factor','median_reward_risk','mean_net_r']:v=f'{v:.3f}'
            row.append(str(v))
        lines.append('| '+' | '.join(row)+' |')
    return '\n'.join(lines)

def main():
    audit=json.loads((RUN/'verification.json').read_text());assert audit['all_passed']
    for name,h in audit['files'].items():assert sha(RUN/name)==h
    s=pd.read_csv(RUN/'summary.csv');d=pd.read_csv(RUN/'decisions_summary.csv');t=pd.read_csv(RUN/'both_trades.csv')
    text='''# First one-minute candle of 15:30 news

Completed 2026-11-22. [Frozen protocol](PROTOCOL.md).

**The combined rule does not show a profitable edge after costs.** Three full
native MT5 runs completed: CPI + payrolls, CPI only and payrolls only. All
333 combined trades independently match raw-minute signals, entry quotes and
subsequent exits. The two separate ledgers reproduce the combined ledger exactly.

One MNQ-valued contract ($2/point), $1.05 per round trip. This uses the project's
continuous NQ research history, not a native MNQ feed. Original historical dates;
the packed Forex Tester dataset was not used. DD below is intraday marked-to-market
equity after costs. The complete [summary](summary.csv) also includes annual
results, daily-close DD, mean net R and +$1/trade stress.

'''
    text+=table(s.loc[s.policy.eq('both')&s.period.isin(['2010-15','2016-19','2020-26','2016-26'])],
        dict(period='Period',trades='Trades',gross='Gross $',net='Net $',win_rate='Win rate',profit_factor='PF',equity_dd='Equity DD $',stress_net='Net with +$1/trade'))
    text+=f'\n\nFull June 2010–September 2026: {len(t)} trades, gross ${t.trade_profit.sum():,.2f}, net ${t.net_dollars.sum():,.2f}.\n'
    text+='''
The recent win rate is about 71%, but the median planned reward/risk is only
0.256: the remaining wick offers a relatively small target while the opposite
candle extreme is often a distant stop. A high hit rate alone is insufficient.
The 2016–19 net gain is only $38.35 and becomes a loss with another $1 per trade.

## CPI and payroll decomposition

These are the same fixed rule on predeclared subsets, not optimized variants.

'''
    text+=table(s.loc[s.policy.ne('both')&s.period.isin(['2016-19','2020-26','2016-26'])],
        dict(policy='Release',period='Period',trades='Trades',net='Net $',win_rate='Win rate',profit_factor='PF',mean_net_r='Mean net R',equity_dd='Equity DD $'))
    text+='''

Payrolls earn positive dollars in the main eras, whereas CPI loses. Payrolls'
recent mean net R is negative despite positive dollar P&L: dollar risk varies
between trades. This small, repeatedly examined historical sample does not
establish a robust payroll-only trading rule. No production change is made.

## Implemented execution rules

- Calendar: scheduled CPI and Employment Situation releases at 15:30 research
  time, equivalent to 08:30 New York. FOMC is not a 15:30 release and is excluded.
- Read the exact completed 15:30–15:31 M1 candle. Green buys, TP at its high and
  SL at its low; red sells, TP at its low and SL at its high.
- Enter once on the first available quote in 15:31. Buy at ask, sell at bid.
  This is an executable next-quote entry, not a retroactive fill at the candle's
  closing price. The entry may differ from that close.
- Skip a doji or a candle closing at its target extreme (zero target distance).
  Also skip if the new entry quote is outside the strict SL–TP bracket or broker
  stop-distance rules reject the levels. Do not move TP/SL to make an order fit.
- If the exact signal/entry minute is absent, do not substitute a later candle.
  One attempt per event session, no retries or re-entry.
- Attached TP/SL operate intrabar. Any survivor closes at the existing daily
  23:30/early-close cutoff. There were 241 TP exits, 91 SL exits, and one
  early-close exit (2021-04-02 at 16:00, net -$44.55).

The combined run observed 387 eligible source sessions:

'''
    text+=table(d.loc[d.policy.eq('both')],dict(status='Decision',count='Sessions'))
    text+='''

There were no broker order rejections. Dates before source history and dates
without any source bars are itemized in [verification](verification.json).
The 400-event calendar includes 13 such unobserved dates; missing data are not
counted as trading opportunities. The one missing entry-minute decision is
separate from dates with no source session at all.

## Model limitations and verification

All runs use MT5's generated one-minute OHLC ticks, not real news ticks.
Observed entry spread is 0.25 points. This exchange-mode symbol triggers attached
stops/targets on the Last-price OHLC path, including short positions. Native
tester exits fill at their specified levels; this is a tester convention, not a
guarantee of live stop/limit execution. [MT5 explains exchange stop triggering](https://www.metatrader5.com/en/terminal/help/trading/general_concept).
News latency, variable spreads, slippage and queue priority are not reproduced.

Two trades over full history have an execution-minute range containing both
TP and SL. Generated-tick ordering resolves them in the tester, but M1 OHLC
alone cannot prove real intraminute ordering. Neither occurs in 2020–26.
Five focused tests cover direction, dojis, zero target wick, next-quote gaps and
broker minimum distances. All native decisions match raw source candles; all
entries match quote side, exits match an independent forward minute-path replay,
and native gross equity DD reconciles. Daily compression reproduces full costed
equity paths. Subset union exactly matches the combined run.

## EA and reproduction

EA: `mt5/experts/News_first_minute_research.mq5`.
Installed for the tester as `CodexResearch\\News_first_minute_research`.
Use the original custom symbol `MNQcontDTBNT20102026_2`, M1, 1-minute OHLC model.
Inputs: `NewsMask=3` both, `1` CPI, `2` payrolls; `RunTag` labels output files.
The EA intentionally refuses live use and other symbols/clocks.

The complete source/includes, compiled EX5 and three tester INIs are packaged
in `Reports/news_first_minute_20261122/News_first_minute_EA.zip`. That folder
also holds native HTML reports, decisions, deals, equity paths and completion hashes.
The generated calendar include comes from the frozen timestamp CSV. Preparation
is performed by the runner; existing completed runs are preserved.

```powershell
& .\\venv\\Scripts\\python.exe python/run_news_first_minute.py
& .\\venv\\Scripts\\python.exe python/analyze_news_first_minute.py
& .\\venv\\Scripts\\python.exe python/report_news_first_minute.py
& .\\venv\\Scripts\\python.exe -m unittest discover -s python -p test_news_first_minute.py -v
```

No automatic commit. Calendar scope and source end date match the preceding
news study; this experiment does not add October/November 2026 releases.
'''
    checks=audit['jobs'][0]
    assert checks['forced_closes']==1 and checks['ambiguous_trades']==2 and checks['events_observed']==387
    assert len(checks['missing_calendar_dates'])==13
    native=pd.read_csv(RUN/'decisions_news1m_20261122_both.csv');assert (native.ask-native.bid).round(8).eq(.25).all()
    directions=direction_results()
    section='''## Long versus short trades

Post-hoc descriptive split of the verified native trades; no new rule or
parameter selection. One trade maximum per session makes this an exact ledger
decomposition. Longs follow green news candles, shorts follow red ones.
Both directions include the same $1.05 round-trip cost.

'''
    section+=table(directions.loc[directions.policy.eq('both') & directions.period.isin(['2010-15','2016-19','2020-26','full'])],
        dict(period='Period',direction='Direction',trades='Trades',net='Net $',win_rate='Win rate',profit_factor='PF',avg_net='Average net $',mean_net_r='Mean net R'))
    section+='''

**Longs outperform shorts in both main eras.** Since 2020, longs earn $940.80
while shorts lose $1,184.85, explaining the combined loss. Early longs earn
$160.65 versus shorts losing $122.30. Across full history, longs earn $1,057.05
and shorts lose $1,302.20. However, full-history mean net R for longs is still
slightly negative (-0.0066), so positive dollars are not uniform risk-adjusted
expectancy across eras. This post-hoc split motivates a hypothesis; it does not
validate a newly selected long-only strategy.

Recent release-specific split (2020–September 2026):

'''
    section+=table(directions.loc[directions.policy.ne('both') & directions.period.eq('2020-26')],
        dict(policy='Release',direction='Direction',trades='Trades',net='Net $',win_rate='Win rate',profit_factor='PF',mean_net_r='Mean net R'))
    section+='''

The full [direction summary](direction_summary.csv) includes all eras, both
release subsets, reward/risk, +$1/trade stress and **closed-trade** drawdown for
each side. That drawdown is not the intraday equity DD in the main table.
Counts and profits of the two sides reconcile to each combined ledger in every
period. Differences are descriptive; no formal significance or forward-data
confirmation is claimed.

'''
    text=text.replace('## EA and reproduction',section+'## EA and reproduction')
    text=text.replace('No automatic commit. Calendar scope','Calendar scope')
    (DOC/'RESULTS.md').write_text(text,encoding='utf-8')
    shutil.copyfile(RUN/'news_first_minute_dates.mqh',ROOT/'mt5/experts/news_first_minute_dates.mqh')
    with zipfile.ZipFile(RUN/'News_first_minute_EA.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in [*RUN.glob('*.mqh'),*RUN.glob('*.mq5'),*RUN.glob('*.ex5'),*RUN.glob('*.ini')]:z.write(p,p.name)
        z.write(DOC/'RESULTS.md','RESULTS.md')
    print('Published',DOC/'RESULTS.md')

if __name__=='__main__':main()
