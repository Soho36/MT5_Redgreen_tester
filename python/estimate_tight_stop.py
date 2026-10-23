"""Estimate a tighter RTL stop from the ledger's worst excursion (MAE), exit rule unchanged (2026-10-23, exploratory).

Stop at entry - k x candle range (k < 1). A trade whose MAE reached -k R would have been stopped there first (MAE is
measured up to the actual exit); every other trade keeps its result. The bar-close exit stays at +1 original R, so a
tighter stop also means a larger reward-to-risk. Fills at the stop price, as in the 1-minute OHLC tester. Audited
uncapped M30 RTL ledgers (NQ, YM) from Reports/ym_baselines_20261023, 2016-01 -> 2026-10-01, $1.05 per trade.
"net/risk" = mean net result per dollar of the new (tighter) risk: the measure if size is set by dollar risk.
Usage: python estimate_tight_stop.py
"""
import numpy as np

from analyze_instrument_baseline import COST, load
from project_paths import PROJECT_ROOT as ROOT

RUN = ROOT / "Reports" / "ym_baselines_20261023"
LEDGERS = (("NQ", 2.0, "nq"), ("YM", 0.5, "ym"))
FRACTIONS = (1.0, 0.9, 0.75, 0.6, 0.5, 0.35, 0.25)


def main():
    for name, pv, key in LEDGERS:
        d = load(RUN / f"runband_ymbase_20261023_rtl_{key}_1.00_audited.csv")
        d = d[(d.entry.dt.year >= 2016) & (d.entry < "2026-10-01")]
        risk = d.candle_range * pv
        r = (d.trade_profit / risk).to_numpy()
        mae = (d.mae_money / risk).to_numpy()
        print(f"\n{name}: {len(d):,} trades; stopped at the full stop {(r <= -0.99).mean():.3f}, MAE <= -1 {(mae <= -1 + 1e-9).mean():.3f}")
        print(f"{'k':>5} {'period':>8} {'stopped%':>8} {'gross R (orig)':>14} {'net $':>9} {'net/risk':>9} {'PF net':>7} {'winners lost%':>13}")
        for k in FRACTIONS:
            hit = mae <= -k + 1e-9
            new_r = np.where(hit, -k, r)
            for per, m in (("2016-19", (d.entry.dt.year <= 2019).to_numpy()), ("2020-26", (d.entry.dt.year >= 2020).to_numpy())):
                rk = risk.to_numpy()[m]
                net = new_r[m] * rk - COST
                lost = ((r[m] > 0) & hit[m]).sum() / (r[m] > 0).sum()
                print(f"{k:>5} {per:>8} {100 * hit[m].mean():8.1f} {new_r[m].mean():14.4f} {net.sum():9.0f} "
                      f"{(net / (k * rk)).mean():9.4f} {net[net > 0].sum() / -net[net < 0].sum():7.3f} {100 * lost:13.1f}")


if __name__ == "__main__":
    main()
