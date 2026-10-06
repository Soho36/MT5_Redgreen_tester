"""Independent sequential replay of Q24 states and daily stopping policies."""
import json

import numpy as np
import pandas as pd

from analyze_price_levels import sha256
from analyze_trade_streaks import STUDY


def main():
    provenance = json.loads((STUDY / 'provenance.json').read_text())
    for item in provenance['files'] + provenance['outputs']:
        assert sha256(item['path']) == item['sha256'], item['path']
    f = pd.read_csv(STUDY / 'trades.csv', parse_dates=['submission_time', 'exit_time', 'session'])
    summary = pd.read_csv(STUDY / 'stops.csv')
    checked_states = checked_policies = 0
    for period, x in f.groupby('period', sort=False):
        x = x.reset_index(drop=True)
        global_state = day_state = 0
        last_session = last_exit = None
        for row in x.itertuples():
            if row.session != last_session:
                day_state = 0
            assert last_exit is None or last_exit <= row.submission_time
            assert row.global_before == global_state and row.session_before == day_state
            sign = 1 if row.net > 0 else -1 if row.net < 0 else 0
            global_state = global_state + sign if sign and global_state*sign > 0 else sign
            day_state = day_state + sign if sign and day_state*sign > 0 else sign
            assert row.global_after == global_state and row.session_after == day_state
            last_session, last_exit = row.session, row.exit_time
            checked_states += 1
        for wanted_sign, name in ((1, 'win'), (-1, 'loss')):
            for threshold in range(2, 7):
                stopped = False
                state = 0
                previous_day = None
                kept, omitted = [], []
                for row in x.itertuples():
                    if row.session != previous_day:
                        stopped, state = False, 0
                    previous_day = row.session
                    if stopped:
                        omitted.append(row.Index)
                        continue
                    kept.append(row.Index)
                    sign = 1 if row.net > 0 else -1 if row.net < 0 else 0
                    state = state + sign if sign and state*sign > 0 else sign
                    if state*wanted_sign >= threshold:
                        stopped = True
                value = summary[(summary.period == period) & (summary.rule == f'stop_{name}_{threshold}')].iloc[0]
                assert value.n == len(kept) and value.removed == len(omitted)
                assert abs(x.net.iloc[kept].sum() - value.net) < 1e-6
                assert abs(x.net.iloc[omitted].sum() - value.removed_net) < 1e-6
                assert abs(x.net_r.iloc[kept].mean() - value.mean_r) < 1e-10
                balance = peak = dd = 0.
                for amount in x.net.iloc[kept]:
                    balance += amount
                    peak = max(peak, balance)
                    dd = max(dd, peak-balance)
                assert abs(dd - value.dd) < 1e-6
                checked_policies += 1
    result = dict(states_replayed=checked_states, policies_replayed=checked_policies,
                  hashes_verified=len(provenance['files'])+len(provenance['outputs']), mismatches=0)
    (STUDY / 'independent_verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('PASS:', result)


if __name__ == '__main__':
    main()
