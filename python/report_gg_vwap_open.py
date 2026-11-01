"""Publish the verified descriptive GG open/close comparison."""
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analyze_gg_vwap_open import OUT, DOC, sha


def table(frame, columns):
    lines = ['| ' + ' | '.join(columns.values()) + ' |', '| ' + ' | '.join('---' for _ in columns) + ' |']
    for _, row in frame.iterrows():
        cells = []
        for key in columns:
            x = row[key]
            if key in ('net_dollars', 'daily_close_dd'):
                cells.append(f'${x:,.0f}')
            elif key == 'net_mean_r':
                cells.append(f'{x:+.4f}')
            elif key == 'trades':
                cells.append(f'{x:,.0f}')
            elif key in ('risk_fraction', 'win_rate'):
                cells.append(f'{x:.1%}')
            elif key in ('net_over_dd', 'profit_factor'):
                cells.append(f'{x:.3f}')
            else:
                cells.append(str(x))
        lines.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(lines)


def main():
    check = json.loads((OUT / 'verification.json').read_text())
    assert check['all_passed']
    for name, digest in json.loads((OUT / 'output_hashes.json').read_text()).items():
        assert sha(OUT / name) == digest
    s = pd.read_csv(OUT / 'summaries.csv')
    g = pd.read_csv(OUT / 'groups.csv')
    a = pd.read_csv(OUT / 'annual.csv')
    daily = pd.read_csv(OUT / 'daily.csv', parse_dates=['session'])
    colors = {'baseline': '#64748b', 'close': '#d97706', 'open': '#087f8c'}
    labels = {'baseline': 'Baseline GG', 'close': 'Skip close below cutoff', 'open': 'Skip open below cutoff'}
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True, constrained_layout=True)
    for policy, color in colors.items():
        d = daily.loc[daily.period.eq('2016-26') & daily.policy.eq(policy)]
        equity = d.net_dollars.cumsum().to_numpy()
        drawdown = equity - np.maximum.accumulate(np.r_[0., equity])[1:]
        axes[0].plot(d.session, equity, color=color, label=labels[policy], linewidth=1.3)
        axes[1].plot(d.session, drawdown, color=color, linewidth=1.1)
    axes[0].legend(loc='upper left', frameon=False)
    axes[0].set_ylabel('Cumulative net ($)')
    axes[1].set_ylabel('Daily-close drawdown ($)')
    for ax in axes:
        ax.grid(alpha=.18)
        ax.spines[['top', 'right']].set_visible(False)
    fig.suptitle('GG signal open vs close at VWAP - A20\nNQ, 2016-Sep 2026; baseline-trade omission, $1.05 cost/trade')
    fig.savefig(DOC / 'gg_open_summary.png', dpi=160)
    plt.close(fig)
    retained = s.loc[s.policy.isin(colors)]
    extra = g.loc[~g.annual & g.group.eq('open_only_skip')]
    annual_extra = g.loc[g.annual & g.group.eq('open_only_skip') & g.period.astype(str).ge('2016')]
    exposure = s.loc[s.period.eq('2016-26')]
    cols = dict(period='Era', policy='Policy', trades='Trades', net_dollars='Net', net_mean_r='Mean net R',
                daily_close_dd='Daily-close DD', net_over_dd='Net/DD')
    text = '''# GG open versus close below the orange VWAP cutoff

Run 2026-11-01 under the [saved plan](GG_OPEN_PROTOCOL.md). **Using the open is stricter,
but does not improve the profit/drawdown trade-off in the pooled sample.** It removes
1,870 additional trades that earned $11,916.50 net. These green candles opened below
the cutoff and closed at or above it: this group contributed profit rather than loss.

This is descriptive baseline-trade omission, not a new MT5 strategy replay. All
results include $1.05 per trade and use the original one-contract sizing.

![GG open and close filters](gg_open_summary.png)

## Definition and timing

The cutoff is the same signal-bar-close session VWAP minus A20 in both comparisons.
Only the signal price changes: `close < cutoff` versus `open < cutoff`. The signal
is evaluated after its M30 candle closes. This does not compare the open with the
VWAP line as it stood at the opening instant. Equality is allowed; unknown labels
are kept under both rules. Both use original baseline fills and exits.

## Results

'''
    text += table(retained, cols)
    text += '''

Over 2016-Sep 2026, the close rule skips 2,713 trades (15.4%); the open rule skips
4,583 (26.1%). Relative to close, open loses $11,916.50 net for a $947.80 smaller
maximum daily drawdown. Relative to baseline, it loses $5,595.35 net for only a
$425.30 smaller drawdown. Net/DD falls from 8.80 baseline and 9.12 close to 8.38 open.
The 2010-15 secondary history remains unprofitable under all three policies.

## What the stricter rule removes

'''
    text += table(extra, dict(period='Era', trades='Additional skips', net_dollars='Net of removed trades',
                             net_mean_r='Mean net R', profit_factor='Profit factor', win_rate='Win rate'))
    text += '''

The additional group earns positive net dollars and positive mean net R in both
primary eras; it is not just a handful of large dollar winners with negative average
R over the whole era. Its pooled mean is +0.0485 R, versus +0.0286 R for the open
rule's retained trades. This is a description, without a significance claim.

The additional removed group is profitable in 9 of the 11 years from 2016 onward.
However, its mean net R is negative in 2020, 2022 and 2025 despite positive dollar
profit, reflecting differences in trade risk. Annual contributions:

'''
    text += table(annual_extra, dict(period='Year', trades='Additional skips', net_dollars='Net of removed trades',
                                    net_mean_r='Mean net R'))
    text += '''

**2026 is not repaired:** close-filter DD is $5,404; open-filter DD is $4,456;
ungated GG DD that year is $3,881. Open removes another 128 trades worth +$2,334,
reducing 2026 net from $3,507 to $1,173. Across 2016-26, open has a larger annual
DD than close in 7 of 11 years, despite its smaller pooled maximum DD.

## Compare with simply reducing exposure

The open rule retains about 65.0% of total planned initial risk. Scaling every
baseline trade to that fraction gives $27,901 net and $3,171 DD. The actual open
filter earns more ($37,356) but also has more DD ($4,456); its net/DD is lower.
Thus some DD reduction is available from reduced exposure alone. This aggregate
risk control is descriptive fractional sizing; it is not executable one-contract
trading and does not establish that the two paths have equal market risk.

'''
    text += table(exposure, dict(policy='Policy', net_dollars='Net', daily_close_dd='Daily-close DD',
                                risk_fraction='Planned risk retained', net_over_dd='Net/DD'))
    text += '''

## Interpretation and limits

The user's observation is correct: green closes put fewer GG signals below the
cutoff. Using the open captures more of them, including candles that recover across
the cutoff before closing. In this history, those extra candidates supplied useful
profit. The stricter filter therefore trades away profit for a modest pooled DD
reduction; it does not support replacing the close rule on this evidence.

No threshold sweep, fresh confirmation claim, or strategy-default change. The
earlier [GG native replay](GG_RESULTS.md#mt5-replay) materially underperformed its
ledger omission because newly available trades changed the result. The open rule
has not been replayed; these filtered ledgers cannot predict that full strategy path.

## Verification and artifacts

26,504 eligible baseline trades; 26,505 whole-run trades less the one October 2026
trade. Source ledger, original independently verified feature/calendar hashes and
protocol were recorded before analysis. Existing close labels and baseline/close
counts, net, mean R and DD were reproduced. All signal candles are green; close
skips are a subset of open skips; group profits reconcile exactly.

The separate verifier rejoins frozen features by availability time, checks OHLC,
session eligibility and both masks, and independently recomputes 189 metric rows
(eras, annual policies, groups, and exposure controls). All checks pass.
It reuses the previously verified frozen features; it does not repeat their raw
minute rebuild. Evidence: `Reports/gg_vwap_open_20261101/` (gitignored), including
`input_manifest.json`, `source_checks.json`, `verification.json`, all tables,
labelled trades and output hashes.

Code: [analysis](../../../python/analyze_gg_vwap_open.py),
[verification](../../../python/verify_gg_vwap_open.py),
[report and chart](../../../python/report_gg_vwap_open.py).
'''
    (DOC / 'GG_OPEN_RESULTS.md').write_text(text, encoding='utf-8')
    print('Wrote GG_OPEN_RESULTS.md and gg_open_summary.png')


if __name__ == '__main__':
    main()
