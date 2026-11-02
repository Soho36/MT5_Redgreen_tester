"""Publish RTL/GG native window exclusion and 16:30 flatten comparisons."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from analyze_rtl_vwap_slope import ROOT,DOC,sha
from prepare_exclude16_replay import RUN as BASE
from prepare_exclude16_flatten import RUN as FLAT


def table(f,columns):
    lines=['| '+' | '.join(columns.values())+' |','| '+' | '.join('---' for _ in columns)+' |']
    for _,r in f.iterrows():
        cells=[]
        for c in columns:
            x=r[c]
            if c in ('net_dollars','daily_close_dd','sampled_equity_dd','worst_session_equity_dd'):
                cells.append(f'${x:,.0f}')
            elif c=='trades':cells.append(f'{x:,.0f}')
            elif c in ('net_mean_r',):cells.append(f'{x:+.4f}')
            elif c=='net_equity_dd':cells.append(f'{x:.2f}')
            else:cells.append(str(x))
        lines.append('| '+' | '.join(cells)+' |')
    return '\n'.join(lines)


def main():
    frames=[];verification=[]
    for run in (BASE,FLAT):
        check=json.loads((run/'verification.json').read_text());assert check['all_passed']
        assert json.loads((run/'equity_native_crosscheck.json').read_text())['all_passed']
        assert sha(run/'summaries.csv')==check['summaries_sha256']
        frames.append(pd.read_csv(run/'summaries.csv'));verification+=check['jobs']
    s=pd.concat(frames,ignore_index=True)
    s['policy']=np.where(s.flatten,'Exclude + flat16:30',np.where(s.exclude,'Exclude16-17','Original'))
    s['filter']=np.where(s.vwap,'VWAP','Baseline');s['strategy']=s.strategy.str.upper()
    s['net_equity_dd']=s.net_dollars/s.sampled_equity_dd
    s=s.sort_values(['period','strategy','vwap','exclude','flatten'])
    combined=BASE/'combined_summaries.csv';s.to_csv(combined,index=False,float_format='%.17g')
    pooled=s.loc[s.period.eq('2016-26')]
    fig,axes=plt.subplots(2,2,figsize=(12,7),constrained_layout=True)
    policies=['Original','Exclude16-17','Exclude + flat16:30'];colors=['#64748b','#2563eb','#0f766e']
    for col,strategy in enumerate(('RTL','GG')):
        for row,metric in enumerate(('net_dollars','sampled_equity_dd')):
            ax=axes[row,col]
            for k,policy in enumerate(policies):
                p=pooled.loc[pooled.strategy.eq(strategy)&pooled.policy.eq(policy)].sort_values('vwap')
                ax.bar(np.arange(2)+(k-1)*.24,p[metric],width=.23,color=colors[k],label=policy)
            ax.set_xticks([0,1],['VWAP OFF','VWAP ON']);ax.grid(axis='y',alpha=.15)
            ax.set_title(strategy+(': net profit' if row==0 else ': sampled equity DD'))
            ax.set_ylabel('$');ax.spines[['top','right']].set_visible(False)
    axes[0,0].legend(frameon=False,fontsize=8)
    fig.suptitle('Exclude 16:00-17:00 entries; optional flatten at16:30\nNQ 2016-Sep2026, full MT5 replay, one contract, $1.05/trade')
    fig.savefig(DOC/'exclude16_summary.png',dpi=160);plt.close(fig)
    text='''# RTL/GG: exclude 16:00-17:00, optionally flatten at16:30

Full native MT5 replays completed 2026-11-01 under the [initial plan](EXCLUDE_16_PROTOCOL.md)
and the user's [16:30 correction](EXCLUDE_1630_FLATTEN_AMENDMENT.md). Generic intraday
drawdown only, without a firm-specific threshold or breach simulation.

![Window and flatten comparison](exclude16_summary.png)

## Exact policies

- Original: all baseline entry windows enabled.
- Exclude16-17: change only `W1600W1700=false`, disabling new entry submissions at
  16:00 and16:30; resume at17:00. Existing positions follow normal exits.
- Exclude + flat16:30: the same entry exclusion, plus close open positions and
  cancel pending orders at the first available quote at/after16:30 each date.

Source clock is Chicago+8:16:00-17:00 is09:00-10:00 New York, with cash open16:30.
VWAP ON means the original signal-close filter: skip below session VWAP minus A20;
equality or unknown permits entry. No slope, blue-location, signal-open or other
condition. RTL uses red signal candles; GG uses green. Twelve separately replayed
jobs model changed subsequent orders; these are not deleted-trade ledgers.

A pending order can trigger on a boundary quote before the EA cancels it. Flatten
acts on the resulting position at the first eligible quote. The exclusion alone
does not guarantee zero fills or zero exposure during16:00-17:00.

## Pooled2016-Sep2026

All net dollars include $1.05 per round trip with one contract at $2/point.
Daily DD uses submission-session attribution as in the earlier studies. Equity DD
uses continuously sampled marked-to-market account equity, deducting external
cost at each closure, and a running high reset only at the analysis-period start.
This continuous equity DD is the relevant generic diagnostic for intraday trailing
risk. It has no fixed firm-specific cap/floor.

'''
    cols=dict(strategy='Strategy',filter='Filter',policy='Window policy',trades='Trades',net_dollars='Net',
              daily_close_dd='Daily DD',sampled_equity_dd='Equity DD',worst_session_equity_dd='Worst session DD',net_equity_dd='Net/equity DD')
    text+=table(pooled,cols)+'\n\n## Matched changes\n\n'
    text+='''For the VWAP-filtered strategies, entry exclusion alone improves pooled net
profit and equity DD. Adding the16:30 flatten then reduces profit without improving
pooled equity DD: RTL $52,739/$2,848 becomes $51,843/$2,959; GG $41,959/$4,616
becomes $39,180/$4,617. For unfiltered RTL/GG, flattening does further reduce DD
relative to entry exclusion alone. These conclusions describe this fixed history,
and the early/recent tables below should be checked before generalizing.

'''
    for strategy in ('RTL','GG'):
        for vwap in (False,True):
            p=pooled.loc[pooled.strategy.eq(strategy)&pooled.vwap.eq(vwap)].set_index('policy')
            b=p.loc['Original']
            for policy in policies[1:]:
                r=p.loc[policy]
                text+=f'- **{strategy}, VWAP {"ON" if vwap else "OFF"}, {policy}:** net change ${r.net_dollars-b.net_dollars:+,.2f}; equity-DD change ${r.sampled_equity_dd-b.sampled_equity_dd:+,.2f} ({(r.sampled_equity_dd/b.sampled_equity_dd-1)*100:+.1f}%); net/equity-DD {b.net_equity_dd:.2f} to {r.net_equity_dd:.2f}.\n'
    text+='\n## Early and recent eras\n\n'+table(s.loc[s.period.isin(['2016-19','2020-26'])],dict(period='Era',**cols))
    text+='\n\n## Remaining opening-hour exposure\n\n'
    text+=table(pooled,dict(strategy='Strategy',filter='Filter',policy='Window policy',fills_16='Fills during16-17',trades_overlapping_16='Trades overlapping16-17'))
    text+='''

The flat16:30 variant deliberately permits positions held from16:00 until16:30.
Its exposure count therefore need not be zero. Forced events and position exits
were checked at actual quote times; missing or delayed boundary quotes are reported
in verification, not assumed to occur exactly on the wall clock.

## Intraday measurement limits

Equity is sampled before/after strategy ticks and on trade-transaction events;
unchanged values are deduplicated. The last saved observation is carried forward
between changes. Worst-session DD seeds each date with the preceding equity, so
an overnight gap is charged to the new date. Period-boundary equity similarly uses
the last prior observation as an opening reference. This can differ from a reset
exactly at the first quote, and from daily-close DD, which attributes a whole trade
to its submission session. Costs are charged at closure for equity metrics.

These tests use generated ticks from1-minute OHLC, not actual tick order. Sampled
equity DD therefore describes this tester path. It is more informative about
intraday exposure than daily-close DD, but it cannot prove a live trailing-account
limit would survive. Firm thresholds, payout resets and trailing caps are outside
this generic comparison. No live settings were changed.

Worst-session DD is not necessarily reduced by suppressing the opening hour: the
worst episode can occur elsewhere. For example, GG's pooled worst-session DD stays
about $2,424 in all policies despite changes in continuous equity DD.

## Verification and artifacts

All four original-window controls reproduce their saved baseline/VWAP ledgers
byte for byte. Native reports, ledgers, timestamps and $2/point economics reconcile.
Every VWAP candidate known/blocked flag and filled source signal was checked against
the frozen real-volume feature panel. Exclusion jobs have no new submissions in
the blocked hour. Flatten events leave no open positions/orders and no trade
survives its forced event. Exit counts are reconstructed from native report times
and ending balances match native totals. Drawdown is independently recomputed
from saved binary observations.

For all12 jobs, maximum gross-equity DD over the whole run also exactly matches
MT5's native equity-DD statistic. This cross-check validates the sampled equity
path against a separate native statistic before external-cost adjustment.

The passive callback counter missed some completed-deal metadata, so costs were
reconstructed from authoritative native exit timestamps instead; raw account
balance/equity and strategy execution are independent of that counter. See the
[accounting note](EXCLUDE_16_EQUITY_NOTE.md). Charging costs strictly before versus
at the same one-second timestamp is checked as a sensitivity in the saved tables.

'''
    for check in verification:
        if 'flatten_events' in check:
            text+=f'- {check["tag"]}: {check["flatten_events"]:,} daily flatten events, {check["positions_closed"]:,} positions closed; {check["delayed_events"]:,} event minutes after16:30.\n'
    text+='''

The earlier16:00-flatten setup was compiled but not run; it is preserved separately.
Original/exclusion evidence: `Reports/rtl_gg_exclude16_20261101/`.
Corrected flatten evidence: `Reports/rtl_gg_exclude16_flatten1630_20261101/`.
Native source, settings, hashes, ledgers/reports, candidate decisions, equity binary
paths, summaries and verification JSONs are saved (gitignored). Combined tables
include annual and secondary2010-15 rows; all use the same fixed rules.

Code: [prepare](../../../python/prepare_exclude16_replay.py),
[flatten preparation](../../../python/prepare_exclude16_flatten.py),
[equity observer](../../../mt5/experts/window_equity_research.mqh),
[verify](../../../python/verify_exclude16_replay.py),
[report](../../../python/report_exclude16_replay.py).
'''
    text+=f'\nAcross all era/annual rows, the maximum fee-timestamp DD sensitivity is ${s.fee_timestamp_dd_sensitivity.max():.2f}; it is ${pooled.fee_timestamp_dd_sensitivity.max():.2f} in the pooled primary comparison.\n'
    for old,new in {'at16':'at 16','during16':'during 16','during16':'during 16','from16':'from 16',
                    'from1-minute':'from 1-minute','all12':'all 12','All12':'All 12',
                    'Pooled2016':'Pooled 2016','secondary2010':'secondary 2010','is09':'is 09',
                    'open16':'open 16','and16':'and 16','at17':'at 17','the16':'the 16',
                    'until16':'until 16','hour:16':'hour: 16'}.items():text=text.replace(old,new)
    (DOC/'EXCLUDE_16_RESULTS.md').write_text(text,encoding='utf-8')
    print(pooled.to_string(index=False))


if __name__=='__main__':main()
