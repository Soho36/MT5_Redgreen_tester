"""Publish native overlay results without selecting or tuning a policy."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import whipsaw_days as wd
from prepare_whipsaw_native import DOC, RUN, ROOT


def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str,r))+' |' for r in rows])


def main():
    manifest=json.loads((RUN/'manifest.json').read_text())
    evidence=dict(preparation=manifest, completed_runs=[
        json.loads((RUN/(job['tag']+'.completed.json')).read_text()) for job in manifest['jobs']])
    (DOC/'run_manifest.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    native=pd.read_csv(DOC/'native_summary.csv')
    overlays=pd.read_csv(DOC/'overlays.csv')
    horizons=pd.read_csv(DOC/'horizons.csv')
    names={'control':'Normal 1 contract / 1R','day1':'+1 contract on day 1',
           'days123':'+1 contract on days 1-3','day1_rr2':'2R on day 1; 1R otherwise'}
    rows=[]
    for strategy in ('rtl','gg'):
        base=native.loc[native.strategy.eq(strategy)&native.policy.eq('control')&native.era.eq('2016-26')].iloc[0]
        rows.append([strategy.upper(),names['control'],f'{base.net:,.2f}',f'{base.equity_dd:,.2f}','—',f'{base.net/base.equity_dd:.2f}'])
        for r in overlays.loc[overlays.strategy.eq(strategy)&overlays.era.eq('2016-26')].itertuples():
            rows.append([strategy.upper(),names[r.policy],f'{r.net:,.2f}',f'{r.equity_dd:,.2f}',f'{r.extra_net:+,.2f}',f'{r.net/r.equity_dd:.2f}'])
    pooled=table(['Strategy','Normal trading plus adjustment','Net $','Equity DD $','Extra net $','Net/DD'],rows)
    rows=[]
    for r in overlays.itertuples():
        rows.append([r.strategy.upper(),names[r.policy],r.era,f'{r.extra_net:+,.2f}',
                     f'{r.extra_mean_ci_low:+.2f} to {r.extra_mean_ci_high:+.2f}'])
    eras=table(['Strategy','Adjustment','Period','Extra net $','95% interval: extra $ / calendar session'],rows)
    rows=[]
    for r in horizons.loc[horizons.cohort.eq('all')].itertuples():
        rows.append([r.strategy.upper(),r.horizon,r.events,f'{r.mean_abs_market_move:.2f}',f'{r.trend_share:.0%}',
                     f'{r.mean_net:.2f}',f'{r.net_ci_low:.2f} to {r.net_ci_high:.2f}',r.also_new_day1])
    horizon_table=table(['Strategy','Day','Events','Mean absolute move / event ATR','Trend share','Net $ / selected day',
                         '95% interval','Also fresh day 1'],rows)
    # Supplemental descriptive persistence check, not a new selection criterion.
    pairs=pd.read_csv(RUN/'event_sessions.csv',parse_dates=['event','session'])
    pairs=pairs.loc[pairs.event.ge('2016-01-01')&pairs.event.lt(wd.END)]
    sessions=wd.session_table(wd.read_m30())
    dates=pairs.pivot(index='event',columns='horizon',values='session').dropna()
    movement=np.column_stack([(sessions.close-sessions.open).reindex(dates[h]).to_numpy() for h in (1,2,3)])
    ranges=np.column_stack([(sessions.high-sessions.low).reindex(dates[h]).to_numpy() for h in (1,2,3)])
    signs=np.sign(movement)
    trends=np.abs(movement)>=.6*ranges
    persistence=dict(events=len(dates),day2_same_sign_as_day1=float(np.mean(signs[:,0]*signs[:,1]>0)),
                     all_three_same_sign=float(np.mean((signs[:,0]*signs[:,1]>0)&(signs[:,1]*signs[:,2]>0))),
                     all_three_trending=float(np.mean(trends.all(1))))
    (DOC/'persistence_descriptive.json').write_text(json.dumps(persistence,indent=2))
    image=DOC/'img';image.mkdir(exist_ok=True)
    fig,axes=plt.subplots(1,2,figsize=(11,4.7),sharey=True,layout='constrained')
    for ax,strategy in zip(axes,('rtl','gg')):
        base=native.loc[native.strategy.eq(strategy)&native.policy.eq('control')&native.era.eq('2016-26')].iloc[0]
        part=overlays.loc[overlays.strategy.eq(strategy)&overlays.era.eq('2016-26')]
        labels=['Baseline','Extra day 1','Extra days 1–3','Day 1 at 2R']
        net=np.r_[base.net,part.net]/1000;dd=np.r_[base.equity_dd,part.equity_dd]/1000
        x=np.arange(4)
        ax.bar(x-.18,net,.36,label='Net profit',color='#247aa5')
        ax.bar(x+.18,dd,.36,label='Equity drawdown',color='#c56c42')
        ax.set_xticks(x,labels,rotation=18);ax.set_ylabel('USD thousands');ax.set_title(strategy.upper())
        ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.15)
    axes[0].legend();fig.suptitle('Normal trading retained · NQ/MNQ economics · 2016–Sep 2026')
    fig.savefig(image/'overlays.png',dpi=160);plt.close(fig)
    text=f'''# Whipsaw native replays: extra size, 2R and persistence

Completed 2026-11-12. Eight native MT5 Model=1 runs, zero compilation warnings.
Exploratory reused history, under the [fixed specification](PROTOCOL.md).
Previous work was committed as 5d2062f before these runs. No live settings changed.

**An extra contract adds profit and risk. Extending it to three sessions is
especially unattractive for GG. RTL's next-session 2R experiment is worth
further checking, but its incremental-profit interval includes zero.**

## Keep normal trading and adjust selected sessions

All figures include $1.05 per round trip per contract. Day 1 uses 174 sessions;
the non-stacking union of days 1-3 uses 403. The selected-only runs isolate the
extra activity; the table below keeps normal baseline trades on all other days.

{pooled}

![Net profit and intraday equity drawdown](img/overlays.png)

The extra-contract scenarios use two contracts total on eligible sessions and
one elsewhere. Their exact native session equity envelopes are scaled under
identical-fill and linear-cost assumptions. They are not native two-contract
runs and do not model market impact. Mean net R in overlays.csv is per contract
round trip, not an account-level risk-adjusted return. Net/DD is descriptive.

The 2R scenario uses one contract throughout, replacing selected-day trades
with the actual native 2R trades. It retains the EA's bar-close exit logic.
It does not mean a resting 2R take-profit. It changes subsequent entries too:
selected trades fall from 1,037 to 859 for RTL and from 1,043 to 838 for GG.

RTL extra day 1 increases net by about 19%, but drawdown by about 30%.
GG extra day 1 increases net by about 20%, with drawdown about 15% higher.
Extending GG to three days adds only $67.20 beyond the day-1 overlay while
raising full-history equity DD from $6,483.35 to $9,093.65. RTL's three-day
overlay earns more but also worsens net/DD versus its baseline.

RTL 2R adds $2,322.40 overall with the same maximum full-history equity DD;
it adds $733.95 early and $1,588.45 recently. GG 2R subtracts $572.25 overall
and is negative in both eras. None of this establishes a rule for adoption.

## Stability and uncertainty

{eras}

Intervals redraw complete calendar months (5,000, seed 20261112) and measure
incremental PnL on the FULL calendar, including inactive sessions. They are
not intervals for total historical dollars or for drawdown. Most include zero;
the positive RTL days1-3 pooled interval still does not show superiority over
volatility-matched allocation or offset its added drawdown. Additional R
intervals and an extra $2-per-contract cost stress are in overlays.csv.

The larger-day hypothesis is not itself a long signal: both EAs are long-only.
The previous study also did not establish incremental volatility-forecast value
beyond detailed volatility controls. A matched-volatility allocation comparison
and genuinely prospective evidence remain necessary before changing live risk.

## Do several running sessions follow?

{horizon_table}

These are separate sessions, each open to close, scaled by the ORIGINAL event's
ATR. Trend means absolute body >=60% of that session's range. The average move
and trend frequency decline across the three horizons. These descriptive
averages have no matched-market baseline and do not establish excess persistence.

50 day-2 observations and 38 day-3 observations are also day 1 following a
newer whipsaw. Removing these leaves mean absolute moves of 0.75 and 0.70 ATR;
RTL selected-day profit intervals then include zero at both horizons. GG's
intervals include zero throughout. See horizons.csv for all and no-fresh-signal
cohorts. Do not sum horizon profits: their session sets overlap.

A supplemental descriptive check across {persistence['events']} complete sequences:
day 2 has the same open-to-close sign as day 1 in {persistence['day2_same_sign_as_day1']:.0%};
all three share a sign in {persistence['all_three_same_sign']:.0%}; all three meet
the trend-day definition in {persistence['all_three_trending']:.0%}. These rates
are not compared with controls and are not evidence for or against a causal
stop-liquidity mechanism. The old three-day aggregate did not answer this question.

## Verification

- Controls reproduce the published primary ledgers: 16,668 RTL / 17,569 GG trades.
- Both day-1 and days1-3 native 1R arms exactly match their control subsets in
  submission, entry/exit times, requested stops, fills, exits, net dollars and R.
- All positions and orders stay within their sessions; eligible dates are checked.
- Full native equity drawdowns reconcile with compressed session envelopes.
- An independent minute replay matches both native 2R arms (859 RTL / 838 GG
  primary trades), including entry/exit minutes and prices.
- Five focused tests cover chronological calendars, endpoint exclusions,
  non-stacking windows and overlay equity arithmetic.

Artifacts: native_summary.csv, overlays.csv, horizons.csv, verification.json,
rr2_verification.json, persistence_descriptive.json, run_manifest.json (input/output hashes).
Full native files, inputs,
manifests and per-session overlay envelopes: Reports/whipsaw_native_20261112/.
Preparation: python/prepare_whipsaw_native.py; runner: python/run_mt5_job.py;
analysis: python/analyze_whipsaw_native.py; independent 2R check:
python/verify_whipsaw_native_rr2.py; report: python/report_whipsaw_native.py.

No thresholds or targets were tuned after these outcomes. The original frozen
whipsaw study and the committed follow-up remain intact.
'''
    (DOC/'RESULTS.md').write_text(text,encoding='utf-8')
    print(json.dumps(persistence,indent=2));print(DOC/'RESULTS.md')


if __name__=='__main__':main()
