"""Publish verified RTL cash-open diagnostics and native comparisons."""
import json
import shutil
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from prepare_rtl_open_halves import RUN, DOC
from analyze_rtl_open_halves import SCOPES

ARMS = ['control','skip_pre','skip_post','skip_both']
NAMES = dict(control='Baseline',skip_pre='Skip 16:00-16:30',skip_post='Skip 16:30-17:00',skip_both='Skip 16:00-17:00')
ORIGINS = ['before 16:00','16:00-16:30','16:30-17:00','17:00+']


def money(x):
    return f'{x:,.2f}'


def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+
                     ['| '+' | '.join(map(str,r))+' |' for r in rows])


def main():
    assert json.loads((RUN/'verification.json').read_text())['all_passed']
    metrics = pd.read_csv(RUN/'replay_metrics.csv')
    origins = pd.read_csv(RUN/'exit_origins.csv')
    halves = pd.read_csv(RUN/'half_hour_outcomes.csv')
    base = pd.read_csv(RUN/'control_trades.csv',parse_dates=['session','submitted','entry_time','exit_time'])
    key = ['submitted','entry_time','requested_price','original_sl','exit_time','exit_price']
    decomposed = []
    for arm in ARMS[1:]:
        other = pd.read_csv(RUN/(arm+'_trades.csv'),parse_dates=['session','submitted','entry_time','exit_time'])
        for period,(start,end) in SCOPES.items():
            b = base[base.session.ge(start)&base.session.lt(end)]
            o = other[other.session.ge(start)&other.session.lt(end)]
            bm,om = pd.MultiIndex.from_frame(b[key]),pd.MultiIndex.from_frame(o[key])
            assert bm.is_unique and om.is_unique
            removed,added = b.loc[~bm.isin(om)],o.loc[~om.isin(bm)]
            delta = o.net_dollars.sum()-b.net_dollars.sum()
            assert abs(delta-(added.net_dollars.sum()-removed.net_dollars.sum())) < 1e-7
            minute = b.submitted.dt.hour*60+b.submitted.dt.minute
            omit = (minute.ge(960)&minute.lt(990)) if arm=='skip_pre' else (minute.ge(990)&minute.lt(1020))
            if arm=='skip_both':
                omit = minute.ge(960)&minute.lt(1020)
            decomposed.append(dict(arm=arm,period=period,removed_or_replaced=len(removed),added_or_changed=len(added),
                                   removed_net=removed.net_dollars.sum(),added_net=added.net_dollars.sum(),
                                   net_delta=delta,naive_omission_delta=-b.loc[omit,'net_dollars'].sum()))
    decomp = pd.DataFrame(decomposed)
    decomp.to_csv(RUN/'replay_decomposition.csv',index=False)
    years = metrics[metrics.period.isin([str(y) for y in range(2016,2027)])]
    annual = years.pivot(index='period',columns='arm',values='net_dollars')
    annual_dd = years.pivot(index='period',columns='arm',values='sampled_equity_dd')
    summary = {a:dict(years_profit_improved=int((annual[a]>annual.control).sum()),
                      years_equity_dd_improved=int((annual_dd[a]<annual_dd.control).sum())) for a in ARMS[1:]}
    (RUN/'annual_consistency.json').write_text(json.dumps(summary,indent=2))
    print('Annual consistency:',summary,flush=True)
    print(decomp[decomp.period.eq('2016-26')].to_string(index=False),flush=True)
    x = origins[(origins.period=='2016-26')&(origins.exit_window=='17:00-18:00')&(origins.basis=='entry_origin')].set_index('origin').reindex(ORIGINS)
    m = metrics[metrics.period.eq('2016-26')].set_index('arm').loc[ARMS]
    fig,axs=plt.subplots(1,2,figsize=(13,5),layout='constrained')
    fig.suptitle('RTL cash open: entry origins and full-strategy replay',fontsize=16,fontweight='bold')
    axs[0].barh(range(4),x.net/1000,color=['#216b86','#399caf','#e49e3a','#b44d58'])
    axs[0].set_yticks(range(4),['Before 16:00','16:00-16:30','16:30-17:00','17:00 or later'])
    axs[0].invert_yaxis()
    axs[0].axvline(0,color='#555',lw=.8)
    axs[0].set_xlim(-9,34)
    for i,v in enumerate(x.net/1000):
        axs[0].text(v+(.5 if v>=0 else -.5),i,f'{v:+.1f}',va='center',ha='left' if v>=0 else 'right')
    axs[0].set_title('17:00-18:00 exits: where did they enter?')
    axs[0].set_xlabel('Net result of those exits ($ thousands)')
    for i,(a,r) in enumerate(m.iterrows()):
        axs[1].barh(i-.18,r.net_dollars/1000,height=.34,color='#216b86',label='Net profit' if i==0 else None)
        axs[1].barh(i+.18,r.sampled_equity_dd/1000,height=.34,color='#b44d58',label='Equity drawdown' if i==0 else None)
        axs[1].text(r.net_dollars/1000+.4,i-.18,f'{r.net_dollars/1000:.2f}',va='center',fontsize=9)
        axs[1].text(r.sampled_equity_dd/1000+.4,i+.18,f'{r.sampled_equity_dd/1000:.2f}',va='center',fontsize=9)
    axs[1].set_yticks(range(4),[NAMES[a] for a in ARMS])
    axs[1].invert_yaxis()
    axs[1].set_xlim(0,51)
    axs[1].set_title('Full native replays, normal exit rules')
    axs[1].set_xlabel('$ thousands; one contract, after costs')
    axs[1].legend(loc='lower right',frameon=False)
    for ax in axs:
        ax.spines[['top','right']].set_visible(False)
        ax.grid(axis='x',alpha=.15)
        ax.set_axisbelow(True)
    fig.supxlabel('2016-September 2026 | Unfiltered RTL | Chicago+8 clock | 16:30 cash open',fontsize=10)
    fig.savefig(DOC/'comparison.png',dpi=170)
    plt.close(fig)

    text = ['# RTL: split the cash-open hour',
      '2026-11-11. Four complete native MT5 runs, with all checks passing. The full-hour exclusion remains the strongest of these four historical alternatives: highest pooled net profit and lowest sampled equity drawdown. Neither half alone improves on it. Exploratory evidence, not untouched out-of-sample confirmation.',
      '## Why the 16-hour loss bar and 17-hour profit bar differ',
      'Both earlier positions and new fills stop out after 16:30. RTL holds a broker stop that can execute inside the M30 bar, but checks its profit target against the completed candle only on the next bar. A trade filled during 16:30-17:00 normally cannot take its bar-close profit exit before 17:00. The hourly exit bars partly reflect that mechanism; they are not entry-window expectancies.',
      'Of 1,186 baseline positions filled before and still open immediately before the 16:30 quote, 254 (21.4%) stop in the first five minutes, another 190 in minutes 5-15, and another 111 in minutes 15-30: **555 / 1,186 = 46.8% stop within the first half-hour.** There are also 396 stops during that half-hour from trades filled at/after 16:30. Native deal comments identify stops. This establishes timing association, not proof that volatility caused the losses.',
      'The entire pre-open position cohort nevertheless earns **$15,591 net** over its full trade lifetimes. That includes P/L earned before 16:30 and is not the incremental value of holding through the open. A flatten decision requires a marked-to-market counterfactual; it cannot be inferred from whole-trade cohort P/L or stop counts.',
      '## Where the 17:00-18:00 profits came from',
      'Actual fill times below, pooled 2016-Sep2026. Conditional exit groups, not all outcomes for each entry window.',
      table(['Actual entry','Trades exiting 17-18','Gross profit $','Gross loss $','Net $'],
            [[k,int(r.trades),money(r.gross_profit),money(r.gross_loss),money(r.net)] for k,r in x.iterrows()]),
      'About 61% of gross profits in the 17-hour exit bar came from entries before the cash open; about 38% came from fills in 16:30-17:00. By order-submission time the pre-open share is larger: some earlier orders fill after the open. See exit_origins.csv for both definitions.',
      '## Full outcomes by entry time',
      'All exits included, actual fill times. Dollars use one contract; R uses each trade’s planned candle risk.']
    hh=halves[(halves.period.eq('2016-26'))&(halves.basis.eq('entry_half'))&halves.window.isin(['15:30','16:00','16:30','17:00','17:30'])]
    text += [table(['Fill half-hour starts','Trades','Net $','Mean net R','Net PF'],
                   [[r.window,int(r.trades),money(r.net),f'{r.mean_net_r:.4f}',f'{r.pf:.3f}'] for r in hh.itertuples()]),
             'The 16:30-17:00 fills are approximately break-even in pooled dollars despite the dramatic exit bars: -$391 in 2016-19 and +$542 since 2020. The 16:00-16:30 fill group is -$273 early and +$545 recently. Neither is consistently losing in dollars. Submission groups differ because buy stops can remain pending.',
             '## Full native strategy comparisons',
             'Normal exits; no forced close at 16:30. Exclusion changes submissions and original pending cancellation. These runs have zero fills in their excluded halves, but that is not guaranteed on all data. Costs are $1.05 per trade. Equity DD is sampled open-equity peak-to-trough after costs.']
    for period in ['2016-26','2016-19','2020-26','2010-15']:
        mm=metrics[metrics.period.eq(period)].set_index('arm').loc[ARMS]
        text += [f'### {period}',table(['Run','Trades','Net $','Equity DD $','Net / equity DD','Net PF'],
                   [[NAMES[a],int(r.trades),money(r.net_dollars),money(r.sampled_equity_dd),
                     f'{r.net_dollars/r.sampled_equity_dd:.2f}',f'{r.profit_factor:.3f}'] for a,r in mm.iterrows()])]
    text += ['## Why a full replay differs from removing baseline trades',
             'Simple omission by submission time removes profitable baseline trades. Native reruns also change pending-order lifetimes and later opportunities.',
             table(['Exclusion','Native net change $','Naive omission change $','Removed/replaced trades','Added/changed trades'],
                  [[NAMES[r.arm],money(r.net_delta),money(r.naive_omission_delta),r.removed_or_replaced,r.added_or_changed]
                    for r in decomp[decomp.period.eq('2016-26')].itertuples()]),
             'Changed trades use exact submission, fill, original stop and exit identity; this includes changed outcomes and different opportunities.',
             '## Annual consistency',
             table(['Exclusion','Years net improves / 11','Years equity DD improves / 11'],
                   [[NAMES[a],v['years_profit_improved'],v['years_equity_dd_improved']] for a,v in summary.items()]),
             'Full-hour exclusion improves net in both primary eras. Post-open-only slightly raises recent equity DD ($5,942 to $5,990); excluding both halves lowers it to $5,734. Historical selection and 1-minute OHLC modelling limit causal and forward-performance claims.',
             '![Attribution and replay comparison](comparison.png)',
             '## Verification and reproduction',
             'Four jobs compile with zero errors/warnings. Control and full-hour ledgers match earlier runs byte for byte. Every native deal reconciles to ledger timestamps, candle risk, P/L and stats. Every filled signal/accepted decision checked; forbidden submissions absent. Sampled full-history gross equity DD matches MT5 in all arms. Three boundary/aggregation tests pass.',
             'Primary sample: January 2016-September 2026; 2010-15 secondary. Incomplete October endpoint excluded. Chicago+8 custom-symbol clock, not changing Estonia wall-clock differences.',
             'Evidence folder: Reports/rtl_open_halves_20261111. Contains frozen manifest, native HTML/INI/ledgers, equity paths, verification.json, replay_metrics.csv, half_hour_outcomes.csv, exit_origins.csv, entry_exit_matrix.csv, opening_cohorts.csv, baseline_attributed_trades.csv and replay_decomposition.csv. Compact CSV tables copied beside this report.',
             'Reproduce: python/analyze_rtl_open_halves.py describe; python/analyze_rtl_open_halves.py; python/report_rtl_open_halves.py; python/test_rtl_open_halves.py. Preparation preserves existing artifacts. Shared run_mt5_job.py runs the isolated tester-only RTL_open_halves_20261111 expert. No live chart or production settings changed.']
    # Follow-up requested in the discussion: evening exit bars versus entry outcomes.
    pooled = base[base.session.ge('2016-01-01') & base.session.lt('2026-10-01')]
    evening = []
    for hour in range(18, 23):
        en = pooled[pooled.entry_time.dt.hour.eq(hour)]
        ex = pooled[pooled.exit_time.dt.hour.eq(hour)]
        evening.append(dict(hour=hour,entry_trades=len(en),entry_net=en.net_dollars.sum(),
                            exit_trades=len(ex),exit_net=ex.net_dollars.sum()))
    evening = pd.DataFrame(evening)
    evening.to_csv(RUN/'evening_attribution.csv',index=False)
    at23 = pooled[pooled.exit_time.dt.hour.eq(23)]
    atflat = at23[at23.exit_time.dt.strftime('%H:%M:%S').eq('23:30:00')]
    flat = atflat[~atflat.exit_comment.fillna('').str.startswith('sl ')]
    profit23 = at23[at23.exit_time.dt.strftime('%H:%M:%S').eq('23:00:00')]
    late = pooled[pooled.entry_time.dt.hour.between(18,22)]
    late23 = late[late.exit_time.dt.hour.eq(23)]
    d = decomp[(decomp.period=='2016-26') & (decomp.arm=='skip_both')].iloc[0]
    text += ['## Interpretation agreed after reviewing the results',
             f'The exclusion changes the subsequent trading sequence for this historical run. Removed/replaced trades collectively earned ${money(d.removed_net)}; added/changed trades earned ${money(d.added_net)}, producing the ${money(d.net_delta)} improvement. It is not simply avoidance of a uniformly losing entry group or later losses. Changed pending orders and occupancy can enable some later trades and prevent others.',
             'The narrow conclusion is that excluding 16:00-17:00 improved this historical backtest. A reliable forward advantage has not been established. Annual drawdown improvement (10/11 years) is more consistent than profit improvement (6/11); both remain descriptive results from historical selection, not independent confirmation.',
             '## Follow-up: evening 18:00-23:00',
             'Same baseline and period; these are different trade groups in each column. No native evening-exclusion experiment was run.',
             table(['Hour starts','Trades entering','Eventual entry-group net $','Trades exiting','Exit-group net $'],
                   [[int(r.hour),int(r.entry_trades),money(r.entry_net),int(r.exit_trades),money(r.exit_net)] for r in evening.itertuples()]),
             f'Entries filled during 18:00-23:00 earned ${money(late.net_dollars.sum())} overall. Their exits during the 23-hour bucket earned ${money(late23.net_dollars.sum())}; earlier losses offset much of that. The exit chart therefore does not establish that evening entries lose.',
             f'The full 23-hour exit bucket earns ${money(at23.net_dollars.sum())} net: {len(profit23)} normal bar-close profit exits at 23:00 contribute ${money(profit23.net_dollars.sum())}, and {len(flat)} non-stop exits at the configured 23:30 flatten contribute ${money(flat.net_dollars.sum())}. Stop exits offset the rest; one stop occurring exactly at 23:30 is excluded from the flatten count.',
             'Those observations do not settle whether excluding the evening would improve the complete strategy. That would require a separate native replay. No evening exclusion was adopted.']
    shutil.copyfile(RUN/'evening_attribution.csv',DOC/'evening_attribution.csv')
    (DOC/'RESULTS.md').write_text('\n\n'.join(text)+'\n',encoding='utf-8')
    for n in ['replay_metrics.csv','exit_origins.csv','opening_cohorts.csv','half_hour_outcomes.csv','replay_decomposition.csv']:
        shutil.copyfile(RUN/n,DOC/n)
    print('Published',DOC/'RESULTS.md')


if __name__ == '__main__':
    main()

