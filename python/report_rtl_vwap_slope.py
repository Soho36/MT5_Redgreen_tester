"""Publish the user's narrowed RTL blue-VWAP-slope-only comparison.

Reads the already independently verified initial study; selects rows without
recomputing outcomes or applying any price-location/orange condition.
"""
from pathlib import Path
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analyze_rtl_vwap_slope import DOC, OUT as SOURCE, ROOT, sha

OUT = ROOT / 'Reports/rtl_vwap_slope_blue_20261101'
POLICIES = ('baseline', 'rising', 'known_baseline', 'rising_risk_scaled_baseline')


def table(frame, columns):
    rows = ['| ' + ' | '.join(columns.values()) + ' |', '| ' + ' | '.join('---' for _ in columns) + ' |']
    for _, r in frame.iterrows():
        cells = []
        for c in columns:
            x = r[c]
            if pd.isna(x):
                cells.append('—')
            elif c in ('net_dollars', 'daily_close_dd', 'baseline_net', 'rising_net', 'baseline_dd', 'rising_dd'):
                cells.append(f'${x:,.0f}')
            elif c == 'trades':
                cells.append(f'{x:,.0f}')
            elif c in ('net_mean_r', 'gross_mean_r'):
                cells.append(f'{x:+.4f}')
            elif c == 'risk_fraction':
                cells.append(f'{x:.1%}')
            elif c in ('net_over_dd', 'profit_factor'):
                cells.append(f'{x:.2f}')
            else:
                cells.append(str(x))
        rows.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(rows)


def main():
    check = json.loads((SOURCE / 'verification.json').read_text())
    assert check['all_passed']
    for name, digest in json.loads((SOURCE / 'input_manifest.json').read_text()).items():
        assert sha(ROOT / name) == digest, name
    for name, digest in json.loads((SOURCE / 'output_hashes.json').read_text()).items():
        assert sha(SOURCE / name) == digest, name
    OUT.mkdir(parents=True, exist_ok=True)
    selected = {}
    for name in ('summaries', 'annual', 'daily', 'groups', 'unknown_reasons', 'slope_distribution'):
        f = pd.read_csv(SOURCE / f'{name}.csv', float_precision='round_trip')
        if name in ('summaries', 'annual'):
            f = f.loc[f.policy.isin(POLICIES)]
        elif name == 'daily':
            f = f.loc[f.policy.isin(('baseline', 'rising'))]
        elif name == 'groups':
            f = f.loc[f.scope.eq('all')]
        f = f.reset_index(drop=True)
        path = OUT / f'{name}.csv'
        f.to_csv(path, index=False, float_format='%.17g')
        pd.testing.assert_frame_equal(f, pd.read_csv(path, float_precision='round_trip'))
        selected[name] = f
    trades = pd.read_csv(SOURCE / 'trades.csv', float_precision='round_trip')
    primary = trades.loc[(trades.session >= '2016-01-01') & (trades.session < '2026-10-01')]
    rising = primary.loc[primary.slope_state.eq('up')]
    s, g, a, u, d = [selected[x] for x in ('summaries', 'groups', 'annual', 'unknown_reasons', 'daily')]
    published = s.loc[s.period.eq('2016-26') & s.policy.eq('rising')].iloc[0]
    assert len(rising) == published.trades
    assert np.isclose(rising.net_dollars.sum(), published.net_dollars, rtol=0, atol=1e-7)
    manifest = dict(all_passed=True, scope='RTL blue VWAP slope only; no price-location condition',
                    amendment_sha256=sha(DOC / 'SLOPE_BLUE_PROTOCOL.md'),
                    report_code_sha256=sha(Path(__file__)),
                    source_verification_sha256=sha(SOURCE / 'verification.json'),
                    source_output_hashes_sha256=sha(SOURCE / 'output_hashes.json'),
                    exact_selected_rows={n: len(f) for n, f in selected.items()},
                    output_hashes={n + '.csv': sha(OUT / (n + '.csv')) for n in selected},
                    rising_policy_checked_without_price_condition=True)
    (OUT / 'publication_verification.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    colors = {'baseline': '#64748b', 'rising': '#2563eb'}
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True, constrained_layout=True)
    for policy in colors:
        p = d.loc[d.period.eq('2016-26') & d.policy.eq(policy)]
        equity = p.net_dollars.cumsum().to_numpy()
        drawdown = equity - np.maximum.accumulate(np.r_[0., equity])[1:]
        time = pd.to_datetime(p.session)
        axes[0].plot(time, equity, label='Baseline RTL' if policy == 'baseline' else 'RTL: blue VWAP slope > 0',
                     color=colors[policy], linewidth=1.4)
        axes[1].plot(time, drawdown, color=colors[policy], linewidth=1.1)
    axes[0].legend(frameon=False, loc='upper left')
    axes[0].set_ylabel('Cumulative net ($)')
    axes[1].set_ylabel('Daily-close drawdown ($)')
    for ax in axes:
        ax.grid(alpha=.18)
        ax.spines[['top', 'right']].set_visible(False)
    fig.suptitle('RTL: blue session VWAP slope only\nNQ 2016-Sep 2026; baseline-trade omission; $1.05/trade')
    fig.savefig(DOC / 'slope_summary.png', dpi=160)
    plt.close(fig)
    text = '''# RTL: trading only when blue VWAP slopes upward

Completed 2026-11-01. **Blue session VWAP slope only, RTL only.** There is no
requirement for the signal price to be above VWAP or any offset line. The user's
[scope amendment](SLOPE_BLUE_PROTOCOL.md) narrowed publication after initial
descriptive calculations; the initial [plan](SLOPE_PROTOCOL.md) and evidence remain
preserved. The preceding GG open/close study is committed as `c52a51d`.

**Rising-only reduces both profit and drawdown, with little improvement in their
pooled ratio.** It retains fewer, smaller-risk trades with a higher mean net R, but
many trades taken while VWAP is falling are also profitable in aggregate. These
results support a description of the trade-off, not a claim that down-slope periods
are uniformly unfavorable.

![RTL blue slope only](slope_summary.png)

## Exact rule

At a completed red signal candle, measure `delta = VWAP[t] - VWAP[t-1]`, where the
two VWAP values are at consecutive M30 closes within the same session. Positive
delta permits the normal RTL entry order; negative or zero delta blocks it.
Unknown slope also blocks under this strict rule. Session resets and missing bars
never create a synthetic slope. No A20 warmup is required.

The signal candle is included; the slope is known at order submission. No slope
check is made at a subsequent fill. Units are price points per 30 minutes, not a
screen angle. One fixed interval, no smoothing or magnitude-threshold optimization.

## Results after costs

One contract, $2/point, $1.05 per trade. Same baseline fills and exits; periods are
attributed by submission session. **This is baseline-trade omission, not a native
MT5 replay.** The 2010-15 period is secondary; 2026 ends in September.

'''
    text += table(s.loc[s.policy.isin(('baseline', 'rising'))],
                  dict(period='Era', policy='Policy', trades='Trades', net_dollars='Net', net_mean_r='Mean net R',
                       daily_close_dd='Daily-close DD', net_over_dd='Net/DD'))
    text += '''

In 2016-Sep 2026, rising-only keeps 6,346 of 16,668 trades (38.1%). Net profit
falls 42.5%, from $42,816.60 to $24,620.20; maximum daily drawdown falls 43.0%,
from $5,781.15 to $3,295.75. Net/DD moves only from 7.41 to 7.47.

Mean net R rises from +0.0247 to +0.0475. That improvement is not the same as a
large improvement in the dollar equity curve: the retained trades carry about
32.5% of total planned initial risk. In 2016-19, mean net R remains negative and
net/DD is slightly lower. In 2020-26, both improve modestly. The secondary
2010-15 history remains unprofitable, and mean net R deteriorates from -0.181 to
-0.230. Net/DD ratios on losing policies are not useful evidence of improvement.

## Rising, falling and unavailable slope

'''
    text += table(g.loc[g.period.eq('2016-26')], dict(state='Slope', trades='Trades', net_dollars='Net',
                                                  net_mean_r='Mean net R', profit_factor='Profit factor'))
    text += '''

The filter removes 9,369 falling-slope trades earning **$17,688.55** and averaging
**+0.0122 net R**. Their average is weaker than the rising group, but their aggregate
profit is positive. No exactly flat slopes occur in this sample.

The 953 unknown slopes contribute +$507.85 net. Of these, 400 lack a preceding
same-session VWAP and 553 are submissions in a new session referencing an older
signal candle. Session-start unavailable trades lose $1,648; the older-signal
group earns $2,155.85. They are not classified as falling slopes.

## Exposure and availability diagnostics

'''
    text += table(s.loc[s.period.eq('2016-26')], dict(policy='Policy', trades='Trades', net_dollars='Net',
                      daily_close_dd='Daily-close DD', risk_fraction='Baseline planned risk retained', net_over_dd='Net/DD'))
    text += '''

`known_baseline` keeps every trade with measurable slope, regardless of direction.
It earns $42,309 with $5,175 DD (net/DD 8.18), versus rising-only's $24,620 and
$3,296 (7.47). So the modest ratio improvement against the full baseline does not
persist when both groups use only known slopes.

`rising_risk_scaled_baseline` scales all baseline trades to 32.5% of their size,
matching rising-only's total planned initial risk. It earns $13,910 with $1,878 DD.
Rising-only earns more but also has more drawdown, leaving their profit/DD ratios
close. This is fractional-size arithmetic, not an executable one-contract policy
or a claim that the two paths have identical market risk.

## Annual comparison

'''
    annual = a.loc[a.period.ge(2016) & a.policy.isin(('baseline', 'rising'))]
    p = annual.pivot(index='period', columns='policy', values=['net_dollars', 'daily_close_dd'])
    annual_table = pd.DataFrame(dict(year=p.index, baseline_net=p.net_dollars.baseline.values,
                                    rising_net=p.net_dollars.rising.values, baseline_dd=p.daily_close_dd.baseline.values,
                                    rising_dd=p.daily_close_dd.rising.values))
    text += table(annual_table, dict(year='Year', baseline_net='Baseline net', rising_net='Rising-only net',
                                     baseline_dd='Baseline DD', rising_dd='Rising-only DD'))
    text += '''

## Interpretation and limits

For cumulative VWAP, a rising value means the newest candle's volume-weighted
average minute price exceeds the preceding session VWAP. This is related to price
location, but not identical to the signal close being above VWAP. Its magnitude
also depends on how much volume has already accumulated in the session. Here only
the sign matters.

For this definition and history, the filter concentrates average trade quality
while sacrificing many profitable trades. The main effect is a smaller equity
curve with a smaller drawdown; it does not clearly improve profit per dollar of
maximum drawdown. No statistical significance or fresh confirmation claim.

All results reuse known NQ history and original baseline fills/exits. A real replay
can enter later trades freed by skipped orders, so executable results may differ.
No EA setting, strategy default or live configuration was changed.

## Verification and saved evidence

The initial verifier independently rejoined 25,832 eligible RTL trades to frozen
features, matched signal OHLC/economics, recomputed slope using endpoint subtraction
and the cumulative-VWAP update identity, and checked all daily paths and metrics.
Maximum identity residual was 7.05e-12 points; no sign disagreements or near-zero
ambiguities. Three synthetic tests cover up/down/flat, session reset/gap, missing
VWAP, volume and immunity of past labels to future rows.

Publication rechecks all original input/output hashes and extracts only unconditional
slope policies. Selected rows round-trip exactly; the published rising-only count
and profit are checked directly against `slope_state == up`, with no price-location
condition. The original frozen feature rebuild was not repeated.

Publication tables and manifest: `Reports/rtl_vwap_slope_blue_20261101/`.
Initial independently verified evidence: `Reports/rtl_vwap_slope_20261101/`.
Both directories are gitignored. Code:
[analysis](../../../python/analyze_rtl_vwap_slope.py),
[verification](../../../python/verify_rtl_vwap_slope.py),
[boundary tests](../../../python/test_rtl_vwap_slope.py),
[slope-only publication](../../../python/report_rtl_vwap_slope.py).
'''
    (DOC / 'SLOPE_RESULTS.md').write_text(text, encoding='utf-8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
