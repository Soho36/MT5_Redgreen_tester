"""Generate Q24 readable evidence, observed-run ledger and static plot."""
import json
from pathlib import Path
import argparse
import sys

import numpy as np
import pandas as pd

from analyze_price_levels import sha256
from analyze_trade_streaks import ROOT, STUDY, states

DOC = ROOT / 'docs/TRADE_STREAKS_RESULTS.md'
PERIOD_NAMES = {'train': '2016–19', 'recent': '2020–Jul 2026'}


def table(frame):
    # Avoid requiring tabulate in the project's environment.
    rows = [[str(v) for v in row] for row in frame.itertuples(index=False, name=None)]
    return '\n'.join(['| ' + ' | '.join(frame.columns) + ' |',
                      '| ' + ' | '.join(['---']*len(frame.columns)) + ' |'] +
                     ['| ' + ' | '.join(row) + ' |' for row in rows])


def plot(c, baseline, plot_packages=None):
    if plot_packages:
        sys.path.append(str(plot_packages))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
    colors = {'train': '#3367b5', 'recent': '#de8034'}
    for column, sign in enumerate(('win', 'loss')):
        for period in PERIOD_NAMES:
            q = c[(c.scope == 'session') & (c.period == period) &
                  c.state.str.startswith(f'{sign}_exact_')].iloc[:6]
            k = np.arange(1, 7) + (-.06 if period == 'train' else .06)
            mask = q.n >= 20
            # Do not visually amplify tiny observations; they remain in the table.
            ax = axes[0, column]
            ax.plot(k[mask], q.win_rate[mask]*100, 'o-', color=colors[period], label=PERIOD_NAMES[period])
            ax.axhline(float(baseline[baseline.period == period].win_rate.iloc[0])*100,
                       linestyle=':', color=colors[period], alpha=.6)
            for xx, yy, count in zip(k[mask], q.win_rate[mask]*100, q.n[mask]):
                ax.annotate(f'n={count}', (xx, yy), xytext=(0, 8 if period == 'recent' else -15),
                            textcoords='offset points', ha='center', fontsize=7, color=colors[period])
            ax = axes[1, column]
            d = q.r_difference[mask]
            lo, hi = q.r_diff_lo[mask], q.r_diff_hi[mask]
            ax.errorbar(k[mask], d, yerr=np.array([d-lo, hi-d]), fmt='o-', capsize=4,
                        color=colors[period], label=PERIOD_NAMES[period])
        axes[0, column].set_title(f'Next trade after consecutive {"wins" if sign == "win" else "losses"}')
        axes[0, column].set_ylabel('Next-trade win rate (%)')
        axes[0, column].set_ylim(25, 65)
        axes[0, column].legend(fontsize=9)
        axes[1, column].axhline(0, color='#666666', linewidth=1)
        axes[1, column].set_ylabel('Mean net R difference vs other trades')
        axes[1, column].set_xlabel('Exact number of preceding same-session results')
        axes[1, column].set_xticks(range(1, 7))
        for row in range(2):
            axes[row, column].grid(alpha=.15)
            axes[row, column].spines[['right', 'top']].set_visible(False)
    fig.suptitle('RTL trade streaks: no stable next-trade advantage', fontsize=17)
    fig.text(.5, .015, 'Same-session streaks • $1.05/trade cost • points with n ≥ 20 • lower panels: 95% week-cluster intervals\n'
             'Dotted lines: unconditional win rates. Partial 2026. OHLC screening, previously examined history.',
             ha='center', fontsize=10)
    fig.tight_layout(rect=(0, .06, 1, .94))
    fig.savefig(STUDY / 'streaks.png', dpi=160)
    plt.close(fig)


def main(plot_packages=None):
    c = pd.read_csv(STUDY / 'conditional.csv')
    s = pd.read_csv(STUDY / 'stops.csv')
    y = pd.read_csv(STUDY / 'stop_yearly.csv')
    t = pd.read_csv(STUDY / 'session_tails.csv')
    perm = pd.read_csv(STUDY / 'permutation.csv')
    yearly = pd.read_csv(STUDY / 'yearly.csv')
    trades = pd.read_csv(STUDY / 'trades.csv', parse_dates=['submission_time', 'entry_time', 'exit_time', 'session'])
    run_rows = []
    for period, f in trades.groupby('period', sort=False):
        f = f.reset_index(drop=True)
        for scope in ('session', 'global'):
            _, after = states(f.net.to_numpy(), f.session.to_numpy(), scope == 'session')
            for last in range(len(f)):
                if not after[last]:
                    continue
                at_end = last == len(f)-1
                new_day = not at_end and f.session.iloc[last] != f.session.iloc[last+1]
                changed = not at_end and np.sign(after[last]) != np.sign(after[last+1])
                if not (at_end or changed or (scope == 'session' and new_day)):
                    continue
                first = last-abs(int(after[last]))+1
                q = f.iloc[first:last+1]
                ending = 'period_end' if at_end else 'session_end' if scope == 'session' and new_day else 'zero' if after[last+1] == 0 else 'opposite'
                run_rows.append(dict(period=period, scope=scope, sign='win' if after[last]>0 else 'loss',
                                     length=len(q), first_entry=q.entry_time.iloc[0], last_exit=q.exit_time.iloc[-1],
                                     sessions=q.session.nunique(), net=float(q.net.sum()), sum_r=float(q.net_r.sum()),
                                     ended_by=ending, next_trade_net=None if at_end else f.net.iloc[last+1]))
    run_frame = pd.DataFrame(run_rows)
    run_frame.to_csv(STUDY / 'streak_runs.csv', index=False)
    frequency = run_frame.groupby(['period', 'scope', 'sign', 'length']).size().reset_index(name='runs')
    frequency.to_csv(STUDY / 'streak_frequency.csv', index=False)
    plot(c, s[s.rule == 'baseline'], plot_packages)

    # Evaluate the frozen predictive gate for every exact bin, keeping failures.
    gates = []
    for scope in ('session', 'global'):
        for sign in ('win', 'loss'):
            for k in range(1, 8):
                state = f'{sign}_exact_{k if k < 7 else "7plus"}'
                q = c[(c.scope == scope) & (c.state == state)]
                direction = np.sign(q.r_difference.iloc[0]) if len(q) else 0
                pp = perm[(perm.scope == scope) & (perm.sign == sign) & (perm.length == k) &
                          (perm.shuffle == 'session') & (perm.metric == 'mean_r')]
                yy = yearly[(yearly.scope == scope) & (yearly.state == state)]
                years_agree = int((yy.r_difference*direction > 0).sum())
                neighbor_agree = True
                for neighbor in (k-1, k+1):
                    nn = c[(c.scope == scope) & (c.state == f'{sign}_exact_{neighbor}')]
                    neighbor_agree &= len(nn) == 2 and bool((nn.r_difference*direction > 0).all())
                enough = len(q) == 2 and bool((q.n >= 100).all())
                same_direction = len(q) == 2 and bool((q.r_difference*direction > 0).all())
                intervals = len(q) == 2 and bool((q.r_diff_lo*direction > 0).all() if direction > 0 else (q.r_diff_hi*direction > 0).all())
                significant = len(pp) == 2 and bool((pp.p_holm < .05).all())
                passes = enough and same_direction and intervals and significant and years_agree >= 8 and neighbor_agree
                gates.append(dict(scope=scope, sign=sign, length=k, enough=enough, same_direction=same_direction,
                                  cluster_intervals_exclude_zero=intervals, adjusted_p_pass=significant,
                                  years_agree=years_agree, neighbor_agree=neighbor_agree, passes=passes))
    pd.DataFrame(gates).to_csv(STUDY / 'predictive_gates.csv', index=False)
    stop_gates = []
    for rule, q in s[s.rule != 'baseline'].groupby('rule'):
        sign, number = rule.split('_')[1:]
        k = int(number)
        yy = y[y.rule == rule]
        neighbors = [s[s.rule == f'stop_{sign}_{n}'] for n in (k-1, k+1)]
        agrees = all(len(nn) == 2 and bool((nn.net_dd_ratio > 1).all()) for nn in neighbors)
        risk = bool((q.net_dd_ratio >= 1.10).all())
        profit = bool((q.net_retained >= .9).all())
        dd = bool((q.dd_ratio <= 1).all())
        years = int((yy.net_change > 0).sum())
        stop_gates.append(dict(rule=rule, net_dd_pass=risk, net_retention_pass=profit, dd_pass=dd,
                               positive_years=years, neighbor_agree=agrees,
                               passes=risk and profit and dd and years >= 8 and agrees))
    pd.DataFrame(stop_gates).to_csv(STUDY / 'stop_gates.csv', index=False)
    assert not any(g['passes'] for g in gates)
    assert not any(g['passes'] for g in stop_gates)
    lines = ['# Q24: trade-result streaks — 2026-10-07', '',
        '**No predictive or daily-stop rule passes the frozen screen.** Five same-session wins are too rare '
        'to assess; three losses do not make the next win more likely. Stops after losses can reduce '
        'historical drawdown, but yearly benefits are inconsistent. No EA or sizing change.', '',
        '[Protocol](TRADE_STREAKS_PROTOCOL.md). Current RTL baseline, 14,968 trades '
        '(5,697 earlier; 9,271 recent), one contract, net of $1.05 per trade. '
        '2026 ends July 13. One-minute OHLC; all history previously examined.', '',
        '## Next trade after a known result sequence', '',
        'These are **exact preceding streaks**, known at actual order submission. '
        'Daily state resets at the synthetic session boundary. The last trade that establishes '
        'the streak is excluded from the next-trade result. Zero net breaks a streak.', '']
    base_rows = []
    for row in s[s.rule == 'baseline'].itertuples():
        base_rows.append([PERIOD_NAMES[row.period], str(row.n), f'{row.win_rate:.1%}', f'{row.mean_r:+.3f}', f'${row.net:,.2f}'])
    lines += [table(pd.DataFrame(base_rows, columns=['Period', 'Trades', 'Win rate', 'Mean net R', 'Net dollars'])), '']
    for scope in ('session', 'global'):
        rows = []
        for row in c[(c.scope == scope) & c.state.isin(['win_exact_5', 'loss_exact_3'])].itertuples():
            rows.append([PERIOD_NAMES[row.period], '5 wins' if row.state.startswith('win') else '3 losses',
                         str(row.n), f'{row.win_rate:.1%}', f'{row.mean_r:+.3f}',
                         f'{row.r_difference:+.3f}', f'[{row.r_diff_lo:+.3f}, {row.r_diff_hi:+.3f}]'])
        lines += [f'**{"Within the session (primary)" if scope == "session" else "Across consecutive trades, including different sessions (secondary)"}**', '',
                  table(pd.DataFrame(rows, columns=['Period', 'Preceding streak', 'Next trades', 'Win rate', 'Mean R', 'R vs others', '95% week interval'])), '']
    lines += ['After three same-session losses, next-trade win rates are 41.9% / 41.1%, '
              'versus baseline 43.4% / 43.0%. Mean-R differences are negative in both periods, '
              'but both cluster intervals include zero. This supports neither a winner-is-due rule '
              'nor a reliable next-trade skip rule.', '',
              'Only 2 / 13 trades occur after exactly five same-session wins. '
              'There are 10 / 21 sessions reaching five wins, but most have no subsequent trade. '
              'A positive earlier R interval based on two trades is sparse-sample evidence and '
              'fails the minimum-count gate. Across sessions, five-win next trades have negative '
              'mean R, but only 41 / 77 observations and intervals spanning zero.', '',
              '![Exact streak outcomes](../Reports/trade_streaks_20261007/streaks.png)', '',
              'Plot points require n >=20; all counts, including smaller groups, are retained '
              'in `conditional.csv`. Wilson intervals are descriptive; the lower plot uses '
              'calendar-week cluster intervals for mean R versus other next trades.', '',
              '## Streaks versus shuffled sequences', '',
              '2,000 shuffles within month and separately within session, recomputing streaks '
              'after each shuffle. Daily shuffles retain exactly the outcomes and dollars/R '
              'available on each trading day. Holm adjustment covers all exact-bin tests in '
              'both scopes within each period/metric/null.', '',
              'Longest same-session win streaks: **6 / 7**; loss streaks: **11 / 8**. '
              'Across sessions: wins **8 / 10**, losses **14 / 17**. Longest cross-session '
              'streaks lie inside the monthly-shuffle 95% reference ranges. The earlier '
              'within-session 11-loss streak is unusual under monthly shuffling, but ordinary '
              'under daily shuffling: a bad day explains it without a sequence effect.', '',
              'There is some earlier-period excess alternation: 3,418 daily runs versus '
              '3,307–3,413 in the daily-shuffle 95% range; recent 5,472 versus 5,370–5,505 '
              'is ordinary. This does not establish predictable profitable entries.', '',
              'One isolated recent group survives the adjusted permutation screen: next trade '
              'after four same-session wins, 37 observations, mean +0.657R. '
              'The earlier counterpart has 26 trades and mean -0.180R. It fails replication '
              'and sample-size gates. No exact group passes all requirements.', '',
              '`streak_runs.csv` lists every observed maximal run, dollars/R and timestamps; '
              '`streak_frequency.csv` gives its length distribution. `ended_by` distinguishes '
              'an opposite result, zero, session end and period end; boundary-ended runs '
              'must not be called reversals.', '',
              '## Stop for the remainder of the session', '',
              'Keep the triggering trade, skip all later trades that session and resume next '
              'session. The independent sequential replay verifies these decisions. '
              'These are saved-ledger counterfactuals; adoption requires an EA/full MT5 check. '
              'Skipping only the next trade would change available entries and is not modelled.', '']
    for period in PERIOD_NAMES:
        rows = []
        for row in s[s.period == period].itertuples():
            change = '—' if row.rule == 'baseline' else f'{row.net_change:+,.2f}'
            rows.append([row.rule.replace('stop_', '').replace('_', ' '), str(row.n), f'{row.net:,.2f}',
                         f'{row.dd:,.2f}', f'{row.pf:.3f}', f'{row.mean_r:+.3f}', change])
        lines += [f'**{PERIOD_NAMES[period]}**', '', table(pd.DataFrame(rows,
                  columns=['Stop after', 'Trades', 'Net $', 'DD $', 'PF', 'Mean R', 'Net change $'])), '']
    lines += ['After five wins, stopping changes net by **-$16.90 / +$160.05**, with '
              'drawdown unchanged. Recently, 8 of 13 sessions with another trade have a losing '
              'remainder, but only 2 give back over half the positive trigger profit. '
              'Earlier, neither of the two continuing sessions loses money. Across all '
              'trigger sessions, including days with no remainder, the recent giveback rate '
              'is 2/21. One memorable giveback is insufficient to set this rule.', '',
              'Stopping after three losses reduces DD by 18.0% / 18.6%, improves net/DD '
              'by 39.7% / 11.9%, but changes profit by +$948 / -$3,405 and benefits only '
              '6/11 years. Four-loss stopping reduces DD by 12.4% / 18.4% and retains '
              '105.1% / 98.5% of profit; dollar benefit appears in only 5/11 years. '
              'The similar four/five-loss thresholds are a possible risk-management '
              'trade-off to discuss, not a confirmed prediction or an adopted rule. '
              'Every stop threshold fails at least one fixed requirement.', '',
              '## Verification and limits', '',
              'Seven synthetic sequence tests pass. MT5 trade counts and gross PnL match '
              'the stats export; all 14,968 net outcomes match the established Q10 ledger. '
              'Every prior result is closed by the next actual submission, with no '
              'overlapping/cross-session positions. Independent sequential replay: '
              '**14,968 states and 20 policies, zero mismatches**, including dollar '
              'totals, omissions, mean R and drawdown. Source/output hashes are saved.', '',
              'The statistical nulls assume exchangeability within their shuffle groups. '
              'Long-streak estimates are especially sparse. These historical comparisons '
              'do not demonstrate trend exhaustion, actual tick execution or future '
              'profitability. The previously documented OHLC sensitivity still applies.', '',
              'Reproduce from the project root:', '', '```powershell',
              '.\\venv\\Scripts\\python.exe -m unittest discover -s python -p test_trade_streaks.py -v',
              '.\\venv\\Scripts\\python.exe python\\analyze_trade_streaks.py',
              '.\\venv\\Scripts\\python.exe python\\verify_trade_streaks.py',
              '.\\venv\\Scripts\\python.exe python\\report_trade_streaks.py', '```', '',
              'Evidence: `Reports/trade_streaks_20261007/` (conditional/yearly results, '
              'daily stops and remainders, permutation tests, run frequencies, gate checks '
              'and provenance).', '']
    if plot_packages:
        lines += ['The reporting command additionally needs matplotlib. This run used the '
                  'existing Codex bundled plotting packages through the project venv:', '',
                  '```powershell', f'.\\venv\\Scripts\\python.exe python\\report_trade_streaks.py --plot-packages "{plot_packages}"',
                  '```', '']
    DOC.write_text('\n'.join(lines), encoding='utf-8')
    generated = [DOC, STUDY/'streaks.png', STUDY/'streak_runs.csv', STUDY/'streak_frequency.csv',
                 STUDY/'predictive_gates.csv', STUDY/'stop_gates.csv',
                 STUDY/'independent_verification.json', ROOT/'python/verify_trade_streaks.py', Path(__file__)]
    (STUDY/'report_provenance.json').write_text(json.dumps(dict(
        inputs=[dict(path=str(STUDY/n), sha256=sha256(STUDY/n)) for n in ('provenance.json', 'conditional.csv', 'stops.csv', 'permutation.csv')],
        files=[dict(path=str(p), sha256=sha256(p)) for p in generated]), indent=2), encoding='utf-8')
    print('No predictive gate passes; no stop gate passes. Wrote', DOC)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--plot-packages', type=Path, help='Optional existing compatible plotting site-packages directory')
    main(parser.parse_args().plot_packages)
