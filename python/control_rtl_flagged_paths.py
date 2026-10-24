"""Post-hoc control for the flagged-episode path split; no new rule.

Added after EPISODE_RESULTS.md was written. Repeats the frozen range and path
grouping on trades that were NOT flagged at submission, to show whether
"contained loses, upper excursion wins" is specific to the flags.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import analyze_rtl_flagged_episodes as episodes

OUT = episodes.ROOT / 'Reports/rtl_flagged_paths_control_20261024'


def label_trades(trades, features, flag, n):
    """Same as-of join, rolling range and path groups, kept for every valid trade."""
    rows = features.copy()
    rows['flagged'] = episodes.flag_mask(features, flag)
    rows['range_high'] = rows.high.rolling(n, min_periods=n).max()
    rows['range_low'] = rows.low.rolling(n, min_periods=n).min()
    columns = ['available_at', 'valid', 'flagged', 'range_high', 'range_low']
    result = pd.merge_asof(trades.sort_values(['submitted', 'ticket'], kind='stable'), rows[columns],
                           left_on='submitted', right_on='available_at', direction='backward',
                           allow_exact_matches=True)
    result = result.loc[result.valid.eq(True)].copy()
    assert result.range_high.notna().all()
    result['path_group'] = episodes.path_groups(result.fill_price + result.mfe_money/2,
                                                result.fill_price + result.mae_money/2,
                                                result.range_high, result.range_low)
    result['headroom_r'] = (result.range_high-result.requested_price)/(result.requested_price-result.original_sl)
    result['state'] = np.where(result.flagged, 'flagged', 'unflagged')
    return result


def summarize(labelled, flag, timeframe, n):
    rows = []
    for (era, state), whole in labelled.groupby(['era', 'state'], sort=True):
        positive = float(whole.net_dollars.clip(lower=0).sum())
        common = dict(flag=flag, timeframe=timeframe, window=n, era=era, state=state,
                      state_trades=len(whole), state_headroom_below_1r=float(whole.headroom_r.lt(1).mean()))
        for path, part in whole.groupby('path_group', sort=True):
            rows.append(dict(**common, path_group=path, trades=len(part), trade_share=len(part)/len(whole),
                             net_dollars=float(part.net_dollars.sum()), net_mean_r=float(part.net_r.mean()),
                             win_rate=float(part.net_dollars.gt(0).mean()),
                             winning_dollars_share=float(part.net_dollars.clip(lower=0).sum())/positive))
    return rows


def main():
    trades = episodes.load_trades()
    prior = pd.read_csv(episodes.SOURCE.parent/'rtl_flagged_episodes_20261024/summaries.csv')
    prior = prior.loc[prior.dimension.eq('path_group')]
    OUT.mkdir(parents=True, exist_ok=True)
    out = []
    for n in episodes.WINDOWS:
        for flag, (timeframe, _) in episodes.FLAGS.items():
            features = pd.read_csv(episodes.SOURCE/f'features_{timeframe}_{n}.csv',
                                   parse_dates=['bar_time', 'available_at', 'history_start', 'last_bar_time'])
            features = features.loc[features.available_at.lt(episodes.END)].reset_index(drop=True)
            rows = summarize(label_trades(trades, features, flag, n), flag, timeframe, n)
            # Flagged rows must reproduce the original attribution exactly.
            for row in rows:
                if row['state'] != 'flagged':
                    continue
                old = prior.loc[prior.flag.eq(flag) & prior.window.eq(n) & prior.era.eq(row['era'])
                                & prior.category.eq(row['path_group'])].iloc[0]
                assert old.trades == row['trades'], (flag, n, row['era'], row['path_group'])
                assert np.isclose(old.net_dollars, row['net_dollars'], atol=1e-8, rtol=0)
            out.extend(rows)
    table = pd.DataFrame(out)
    table.to_csv(OUT/'path_control.csv', index=False)
    view = table.loc[table.path_group.isin(['contained', 'upper_only'])].pivot_table(
        index=['flag', 'window', 'era', 'state'], columns='path_group',
        values=['trades', 'trade_share', 'net_mean_r'])
    with pd.option_context('display.width', 200, 'display.max_rows', 200):
        print(view.round(3))


if __name__ == '__main__':
    main()
