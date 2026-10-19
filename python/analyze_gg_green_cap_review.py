"""Review the 2026-10-20 standalone GG cap sweep against the 2026-10-13 study."""
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / 'Reports' / 'gg_green_cap_review_20261020'
sys.path.insert(0, str(ROOT / 'python'))
from analyze_instrument_baseline import COST, load, max_dd, summary

runs = {}
for cap in range(8):
    tag = f'gggreen_20261020_cap{cap}'
    path = STUDY / f'runband_{tag}_1.00.csv'
    d = load(path)
    stats = pd.read_csv(STUDY / f'runband_{tag}_1.00_stats.csv', sep='\t', encoding='utf-16').iloc[0]
    assert int(stats.max_red_run) == cap
    assert len(d) == int(stats.trades)
    assert abs(d.trade_profit.sum() - stats.net_profit) < 1e-6
    runs[cap] = d
print('All 8 ledgers reconcile with MT5 totals.')
print('Entry range:', min(d.entry.min() for d in runs.values()), max(d.entry.max() for d in runs.values()))

periods = [(2016, 2019), (2020, 2026), (2021, 2024), (2025, 2026), (2026, 2026)]
for lo, hi in periods:
    print(f'\n{lo}-{hi}: cap trades net$ DD$ netPF grossPF net/DD')
    for cap, d in runs.items():
        subset = d[(d.entry.dt.year >= lo) & (d.entry.dt.year <= hi)]
        s = summary(subset, 2.0)
        print(f"{cap:>3} {s['trades']:>6} {s['net_$']:>9.0f} {s['maxDD_$']:>8.0f} "
              f"{s['PF_net']:>6.3f} {s['PF_gross']:>7.3f} {s['net_$']/s['maxDD_$']:>6.2f}")

old = ROOT / 'Reports' / 'gg_run_cap_20261013'
print('\nOld study overlap through 2026-07-14: cap old_trades new_trades same_entries_and_profit')
for cap, d in runs.items():
    old_d = load(old / f'runband_ggcap_20261013_cap{cap}_1.00.csv')
    old_d = old_d[(old_d.entry.dt.year >= 2016) & (old_d.entry < pd.Timestamp('2026-07-14'))]
    new_d = d[d.entry < pd.Timestamp('2026-07-14')]
    same = len(old_d) == len(new_d) and (old_d.entry_time.values == new_d.entry_time.values).all() and abs(old_d.trade_profit.values - new_d.trade_profit.values).max() < 1e-7
    assert same, (cap, "historical ledger mismatch")
    print(cap, len(old_d), len(new_d), same)
print('\nNew entries from 2026-07-14: cap trades net$ DD$ netPF')
for cap, d in runs.items():
    s = summary(d[d.entry >= pd.Timestamp('2026-07-14')], 2.0)
    print(cap, s['trades'], round(s['net_$']), round(s['maxDD_$']), round(s['PF_net'], 3))

rtl = load(ROOT / 'Reports/maxredrun_extended_20261013/runband_mrrext_20261013_cap0_1.00.csv')
print('\nCombined RTL no-cap + GG by exit day: period cap net$ daily-DD$ net/DD')
for lo, hi in [(2020, 2026), (2021, 2024), (2025, 2026)]:
    red = rtl[(rtl.entry.dt.year >= lo) & (rtl.entry.dt.year <= hi)]
    red_daily = (red.trade_profit - COST).groupby(red.exit.dt.normalize()).sum()
    for cap, d in runs.items():
        green = d[(d.entry.dt.year >= lo) & (d.entry.dt.year <= hi)]
        green_daily = (green.trade_profit - COST).groupby(green.exit.dt.normalize()).sum()
        daily = red_daily.add(green_daily, fill_value=0).sort_index()
        dd = max_dd(daily.to_numpy())
        print(f'{lo}-{hi}', cap, round(daily.sum()), round(dd), round(daily.sum() / dd, 2))