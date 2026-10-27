"""Evaluation checks of the RTL far-below-VWAP skip (2026-10-27).

Not part of the frozen VWAP study: ad-hoc controls run after it, on the saved
ledger (omission, not replay). Run analyze_rtl_vwap.py first.
1. Risk: far-below vs other trades by planned-risk decile; skip-largest-risk rule.
2. Placebos without VWAP: same count per risk decile; per month x risk tertile;
   the actual skip pattern rolled within each month (keeps runs of skips).
3. Neighbouring thresholds and year-by-year drawdown. -1 stays the frozen rule.
"""
import numpy as np
import pandas as pd

import analyze_rtl_vwap as av

DRAWS = 2000


def placebo(stats, skip, groups, rng):
    """Skip the same number of non-far-below trades in every group cell."""
    cells = []
    for _, idx in pd.Series(np.asarray(groups)).groupby(np.asarray(groups)).groups.items():
        idx = np.asarray(idx)
        pool = idx[~skip[idx]]
        need = min(int(skip[idx].sum()), len(pool))
        if need:
            cells.append((pool, need))
    out = np.empty((DRAWS, 3))
    for d in range(DRAWS):
        mask = np.zeros(len(skip), bool)
        for pool, need in cells:
            mask[rng.choice(pool, need, replace=False)] = True
        out[d] = stats(~mask)
    return out


def rolled(stats, skip, months, rng):
    blocks = [np.flatnonzero(months == m) for m in np.unique(months)]
    out = np.empty((DRAWS, 3))
    for d in range(DRAWS):
        mask = np.zeros(len(skip), bool)
        for idx in blocks:
            mask[idx] = np.roll(skip[idx], rng.integers(0, len(idx)))
        out[d] = stats(~mask)
    return out


def main():
    trades, calendar_all = av.load_inputs()
    trades = trades.loc[trades.variant.eq('full_hlc3')]
    for n, (era, (start, stop)) in enumerate(av.ERAS.items()):
        calendar = calendar_all[(calendar_all >= start) & (calendar_all < stop)]
        e = trades.loc[trades.era.eq(era)].sort_values(['submitted', 'ticket']).reset_index(drop=True)
        skip = e.distance.eq('far_below').to_numpy()
        pnl, risk, r = e.net_dollars.to_numpy(), e.initial_risk_dollars.to_numpy(), e.net_r.to_numpy()
        day = calendar.get_indexer(e.session)
        assert (day >= 0).all()

        def stats(keep):
            return (pnl[keep].sum(), av.max_dd(np.bincount(day[keep], weights=pnl[keep], minlength=len(calendar))),
                    risk[keep].sum()/risk.sum())

        base, actual = stats(np.ones(len(e), bool)), stats(~skip)
        print(f'\n=== {era}: {len(e)} trades, {skip.sum()} far below')
        print(f'baseline net {base[0]:,.0f} DD {base[1]:,.0f}; skip far below net {actual[0]:,.0f} '
              f'DD {actual[1]:,.0f}, planned risk kept {actual[2]:.1%}')

        decile = pd.qcut(risk, 10, labels=False)
        by = pd.DataFrame(dict(decile=decile, far=skip, r=r)).groupby(['decile', 'far']).r.mean().unstack()
        print(f'mean planned risk far below ${risk[skip].mean():.2f} vs others ${risk[~skip].mean():.2f}; '
              f'far-below mean R lower in {int((by[True] < by[False]).sum())}/10 risk deciles')
        print('  mean R others|far: ' + ' '.join(f'{a:+.3f}|{b:+.3f}' for a, b in zip(by[False], by[True])))

        largest = np.zeros(len(e), bool)
        largest[np.argsort(-risk, kind='stable')[:skip.sum()]] = True
        net, dd, kept = stats(~largest)
        print(f'skip the {skip.sum()} largest-risk trades: net {net:,.0f} DD {dd:,.0f}, planned risk kept {kept:.1%}')

        rng = np.random.default_rng(20261027+n)
        month = e.submitted.dt.to_period('M').astype(str).to_numpy()
        tertile = pd.qcut(risk, 3, labels=False).astype(str)
        for name, draws in (('risk-decile placebo', placebo(stats, skip, decile, rng)),
                            ('month x risk-tertile placebo', placebo(stats, skip, np.char.add(month, tertile), rng)),
                            ('skip pattern rolled within month', rolled(stats, skip, month, rng))):
            q = np.quantile(draws, [.05, .5, .95], axis=0)
            print(f'{name}: median net {q[1, 0]:,.0f} [{q[0, 0]:,.0f}..{q[2, 0]:,.0f}], median DD {q[1, 1]:,.0f} '
                  f'[{q[0, 1]:,.0f}..{q[2, 1]:,.0f}], risk kept {q[1, 2]:.1%}; actual beats net '
                  f'{np.mean(draws[:, 0] < actual[0]):.1%}, DD {np.mean(draws[:, 1] > actual[1]):.1%}')

        z = np.nan_to_num(e.z.to_numpy(), nan=0.)
        for threshold in (-0.5, -0.75, -1.0, -1.25, -1.5, -2.0):
            cut = z < threshold
            net, dd, _ = stats(~cut)
            print(f'z < {threshold:+.2f}: skip {cut.sum():5d}, skipped net {pnl[cut].sum():>8,.0f}, '
                  f'retained net {net:>8,.0f}, DD {dd:>6,.0f}')
        yearly = []
        for year in sorted(e.year.unique()):
            sessions = calendar[calendar.year == year]
            m = e.year.eq(year).to_numpy()
            ids = sessions.get_indexer(e.session[m])
            keep = ~skip[m]
            yearly.append(f'{year} DD {av.max_dd(np.bincount(ids, weights=pnl[m], minlength=len(sessions))):,.0f}->'
                          f'{av.max_dd(np.bincount(ids[keep], weights=pnl[m][keep], minlength=len(sessions))):,.0f} '
                          f'net {pnl[m].sum():,.0f}->{pnl[m][keep].sum():,.0f}')
        print(' | '.join(yearly))


if __name__ == '__main__':
    main()
