"""Publish the verified native RTL blue-VWAP slope replay."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from analyze_rtl_vwap_slope import ROOT,CROSS,DOC
from prepare_rtl_vwap_slope_replay import RUN


def main():
    assert json.loads((RUN/'verification.json').read_text())['all_passed']
    s=pd.read_csv(RUN/'summaries.csv')
    t=pd.read_csv(RUN/'replay_trades.csv',parse_dates=['session'])
    original=pd.read_csv(ROOT/'Reports/rtl_vwap_slope_20261101/trades.csv',parse_dates=['session'])
    cal=pd.read_csv(CROSS/'calendars.csv',parse_dates=['session'])
    cal=pd.DatetimeIndex(cal.loc[cal.instrument.eq('NQ'),'session'])
    cal=cal[(cal>='2016-01-01')&(cal<'2026-10-01')]
    fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True,constrained_layout=True)
    for label,frame,color in [('Baseline',original,'#64748b'),('Slope omission',original.loc[original.slope_state.eq('up')],'#93c5fd'),('Full slope replay',t,'#2563eb')]:
        d=frame.groupby('session').net_dollars.sum().reindex(cal,fill_value=0.)
        e=d.cumsum().to_numpy();dd=e-np.maximum.accumulate(np.r_[0.,e])[1:]
        axes[0].plot(cal,e,label=label,color=color,linewidth=1.3)
        axes[1].plot(cal,dd,color=color,linewidth=1.1)
    axes[0].legend(frameon=False);axes[0].set_ylabel('Cumulative net ($)');axes[1].set_ylabel('Daily-close DD ($)')
    for ax in axes: ax.grid(alpha=.18);ax.spines[['top','right']].set_visible(False)
    fig.suptitle('RTL: full MT5 blue-VWAP slope replay\nNQ 2016-Sep 2026; one contract, $1.05/trade')
    fig.savefig(DOC/'slope_replay_summary.png',dpi=160);plt.close(fig)
    text='''# RTL blue VWAP slope: full MT5 replay

Completed 2026-11-01 under the [replay plan](SLOPE_REPLAY_PROTOCOL.md).
**The replay increases profit compared with omission, but the improvement over
unfiltered RTL in pooled profit/drawdown ratio remains modest.** Blue VWAP slope
is the only new condition: no price-versus-blue or orange-cutoff requirement.

![Full slope replay](slope_replay_summary.png)

## Native results

Slope OFF reproduces all 25,833 baseline trades byte for byte. The ON run permits
new orders only for a positive change between consecutive same-session M30 VWAP
endpoints. Flat, falling and unavailable slopes block. Pending-order cancellation
runs before the gate; existing exit rules and fills apply; no slope check at fill.
Withheld orders can free later signals to trade.

One contract, $2/point and $1.05 external cost/trade. Submission-session attribution,
daily-close drawdown and frozen observed calendar match the descriptive study.
2026 ends in September; 2010-15 is secondary.

| Era | Curve | Trades | Net | Mean net R | Daily-close DD | Net/DD |
|---|---|---|---|---|---|---|
'''
    for _,r in s.loc[s.period.isin(['2016-19','2020-26','2016-26','2010-15'])].iterrows():
        text+=f'| {r.period} | {r.curve} | {r.trades:,} | ${r.net_dollars:,.0f} | {r.net_mean_r:+.4f} | ${r.daily_close_dd:,.0f} | {r.net_over_dd:.2f} |\n'
    text+='''
## What changes in a replay

Over 2016-Sep 2026, the replay takes 8,406 trades versus omission's 6,346:
2,060 more trades overall. Net rises $4,641.50, while maximum daily DD rises
$527.25. Mean net R falls from +0.0475 to +0.0403. The net trade-count difference
does not mean the surviving trade sets are nested; later entries can change which
subsequent baseline trades are available.

Compared with unfiltered RTL, pooled replay net is 31.7% lower and DD 33.9% lower.
Net/DD rises from 7.41 to 7.65 (about 3.3%). In 2016-19, net/DD improves from
2.06 to 4.65 and DD falls strongly, but mean net R is still negative. In 2020-26,
net/DD improves only from 6.64 to 6.89, with substantially less total profit.
2010-15 remains unprofitable. Dollar profit and average R differ because trade
risks vary and external commission weighs more heavily on narrow signals.

This is exploratory known-history reuse, without optimization, a fresh sample,
or a significance claim. The result describes a smaller-profit, smaller-drawdown
strategy path; it does not establish a reliable improvement for future trading.
The research EA is tester-only and was not attached to a live chart.

## Checks and evidence

- Both builds: zero compiler errors/warnings. All 25,833 OFF trade ledger rows
  reproduce the baseline byte for byte; native report, ledger and totals reconcile.
- OFF: 60,194 candidate decisions checked. ON: 77,182 checked, 48,996 blocked.
  Each known/blocked flag matches a separate frozen-feature slope calculation.
- Every filled ON trade maps to an accepted rising-slope source signal, with
  requested high and initial stop low matching the source candle.
- Native profit is reconstructed from entry/exit prices at $2/point; every ledger
  profit and entry/exit timestamp agrees with the report. Net deducts $1.05/trade.
- Baseline/omission summaries reproduce the descriptive study. Replay daily DD is
  independently accumulated from zero through the full observed calendar.

The first OFF attempt stopped after the frozen feature window at the October edge.
It is preserved in `Reports/rtl_vwap_slope_replay_20261101/`. The corrected version
treats beyond-window data as unavailable: OFF allows, strict ON blocks. Successful
evidence is in `Reports/rtl_vwap_slope_replay_20261101_v2/` (gitignored), including
hashes, configs, frozen sources/labels, native reports, ledgers, logs, candidate
decisions, summaries and `verification.json`. Published periods exclude October.

Code: [preparation](../../../python/prepare_rtl_vwap_slope_replay.py),
[tester-only gate](../../../mt5/experts/slope_replay_research.mqh),
[verification](../../../python/verify_rtl_vwap_slope_replay.py),
[report](../../../python/report_rtl_vwap_slope_replay.py).
'''
    (DOC/'SLOPE_REPLAY_RESULTS.md').write_text(text,encoding='utf-8')
    print('Published native slope replay report and chart')


if __name__=='__main__': main()
