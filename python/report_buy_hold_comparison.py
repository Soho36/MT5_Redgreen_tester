"""Publish the matched hold/RTL/GG comparison, including VWAP and entry exclusion."""
import json
import shutil
from pathlib import Path
import pandas as pd
from project_paths import PROJECT_ROOT as ROOT
from run_rtl_vwap_replay import digest

RUN=ROOT/'Reports/buy_hold_20261108/comparison'
DOC=ROOT/'docs/baseline/buy-hold/COMPARISON.md'
audit=json.loads((RUN/'verification.json').read_text())
assert audit['all_passed'] and audit['original_comparison_unchanged']
assert digest(RUN/'comparison.csv')==audit['comparison_sha256']
s=pd.read_csv(RUN/'comparison.csv')
NAMES=['Hold raw series','Hold with rollovers','Hold, flatten/reopen each session','RTL','RTL + VWAP','RTL + VWAP + exclude 16-17',
       'GG','GG + VWAP','GG + VWAP + exclude 16-17']
PAIRS=['RTL + GG (2 contracts)','RTL + GG + VWAP (2 contracts)',
       'RTL + GG + VWAP + exclude 16-17 (2 contracts)']
def money(x):return ('−$' if x<0 else '$')+f'{abs(x):,.2f}'
def table(period,names=NAMES):
 out='| Strategy | Net profit | Maximum equity DD | Net / DD |\n|---|---:|---:|---:|\n'
 for name in names:
  r=s[(s.period==period)&(s.strategy==name)].iloc[0]
  out+=f'| {name} | {money(r.net)} | {money(r.equity_dd)} | {r.net_dd:.2f} |\n'
 return out
text='''# Buy and hold versus RTL and GG, with VWAP and entry-window filters

Updated 2026-11-09 (session-flat benchmark added). Matched dataset dates, one MNQ-sized contract per individual
strategy, $2 per point and $1.05 per completed position, no compounding. Every
DD below includes unrealized P&L and external commission. The added variants
come from existing, verified native MT5 replays; no new parameter search.

## Policies

- **Hold, flatten/reopen each session:** buy one contract at the first session
  quote, close at the first quote at/after 23:30 or the existing early-close cutoff,
  and reopen at the next session's first quote. No stop or target. If the cutoff
  is not reached, use the session's final available quote (only the final partial
  dataset session needed this fallback). There are 4,203 positions and $4,413.15
  in modeled fees over the full dataset. No overnight or roll-boundary gap is held.
  Session cutoffs match RTL/GG and are earlier than the exchange's final quote.
- **RTL / GG:** original uncapped RR=1, session-flattened baselines.
- **+ VWAP:** the existing orange-cutoff gate. Skip signals closing strictly below
  session VWAP minus A20; equality or an unknown value permits entry. This is not
  the blue-line slope filter.
- **+ VWAP + exclude 16-17:** the same gate, plus `W1600W1700=false`.
  No new entries are submitted in 16:00–17:00 in the dataset clock
  (Chicago + 8 hours, corresponding to 09:00–10:00 New York). Existing positions
  retain their normal exits. No extra 16:30 flatten was added. A pending order
  can still fill on a boundary quote before cancellation, as in the original EA.

![Equity comparison](comparison.png)

[Complete comparison CSV](comparison.csv) · [Session replay verification](session_flat_verification.json)

## Full dataset: 7 June 2010 to 1 October 2026

'''+table('Full 2010-26')+'''
Both unfiltered baselines earn less than holding with rollovers but have smaller
full-history drawdowns. VWAP and the entry exclusion improve RTL's full-history
profit and profit/DD. Full-history risk includes the early losing years; the
smaller 2016-onward DD figures must not be substituted into this table.
Profit/DD is total net dollars divided by maximum equity DD, not an annualized
return or a Sharpe ratio.

## Since 2016, same final dataset quote

'''+table('2016-26')+'''
## Since 2020, same final dataset quote

'''+table('2020-26')+'''
## Earlier periods

### 2010–15

'''+table('2010-15')+'''
### 2016–19

'''+table('2016-19')+'''
The early losses explain much of the difference between full-history and recent
results. Lower drawdown than passive holding is not universal across periods.
These are historical comparisons, not evidence that a chosen variant will keep
outperforming after this repeatedly studied dataset ends.

## RTL and GG together: allow two contracts

Each row below runs one contract in each strategy and can hold two simultaneous
contracts. Portfolio DD sums the legs' final observations each second, carrying
last values forward. It can omit intermediate fluctuations within a second;
it is neither the sum of individual DDs nor a new combined-account EA replay.

### Full history

'''+table('Full 2010-26',PAIRS)+'''
Two-contract holding with rollovers: $100,638.30 net, $25,616.40 equity DD.

### Since 2020

'''+table('2020-26',PAIRS)+'''
Two-contract holding with rollovers: $73,241.20 net, $25,616.40 equity DD.

## Matching and verification

- All comparisons include the final partial session on 1 October 2026, matching
  the original buy-and-hold test. Earlier reports stopping on 30 September differ
  by any trade in that final partial session.
- Each subperiod restarts the passive benchmark on its first available quote
  and closes on its last. Strategy equity and DD reset at the same period boundary.
- Fees are $1.05 charged at each completed position's exit. MT5 spread/fill effects
  are already in strategy P&L; passive buys use the verified 0.25-point entry spread.
- All six RTL/GG variants use the native reports and equity observations
  in `Reports/rtl_gg_exclude16_20261101/`. Completed-output hashes, total trades,
  gross profits, final balances and gross-equity DD reconcile. RR=1, uncapped runs,
  VWAP settings and entry-window settings are checked explicitly.
- Individual strategy DD uses every saved native intraday observation, including
  multiple observations within a second. Passive DD uses minute highs/lows;
  full passive profit and DD reconcile to the exact-start native hold/roll runs.
  The equity chart uses daily snapshots; table DD is intraday.
- The session-flat benchmark has a separate exact-start MT5 replay under
  `Reports/buy_hold_20261108/session_flat/`. All 4,203 entries/exits were checked
  against raw source prices and the calendar, and gross-equity DD matches MT5.
  Intraday extrema after a cutoff-minute exit are excluded from its equity path.
  Every original VWAP/baseline/passive row is unchanged after adding this benchmark.
- The original baseline/passive comparison is preserved as `baseline_only_*`
  artifacts. All previously reported numeric rows are unchanged within 0.0000001.
- Roll closes use the last old-contract quote and reopens the first new-contract
  quote. This excludes the intervening market gap as well as the contract-price
  difference, not a simultaneous calendar-spread execution. NQ prices use MNQ-sized
  economics throughout, including years before the micro contract existed.
- Existing strategy runs retain their original initial history/indicator warm-up.
  No settings were retuned or live defaults changed for this comparison.

## Artifacts and reproduction

`Reports/buy_hold_20261108/comparison/` contains `comparison.csv`, `daily_equity.csv`,
`comparison.png`, `verification.json`, and the preserved baseline-only outputs.

```powershell
./venv/Scripts/python.exe python/run_buy_hold_session.py prepare
./venv/Scripts/python.exe python/run_buy_hold_session.py native
./venv/Scripts/python.exe python/run_buy_hold_session.py verify
./venv/Scripts/python.exe python/compare_buy_hold_baselines.py
./venv/Scripts/python.exe python/report_buy_hold_comparison.py
```
'''
DOC.write_text(text,encoding='utf-8')
for name in ['comparison.csv','comparison.png']:
 shutil.copyfile(RUN/name,DOC.parent/name)
shutil.copyfile(ROOT/'Reports/buy_hold_20261108/session_flat/verification.json',
                DOC.parent/'session_flat_verification.json')
print(table('Full 2010-26'))
print(table('2020-26'))
