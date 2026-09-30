# Exit estimate and data construction review

> **Summary** (added 2026-10-01; [project status](STATUS.md))
> - **Exit:** exiting at the first touch of +1R would lose money compared with
>   waiting for a bar close. The overshoot beyond +1R (about +0.6R on ~70% of
>   touching trades) is worth more than the reversals it avoids. A full MT5 run
>   later confirmed this.
> - **Data:** pre-2019 history is NQ-based (MNQ didn't exist). The clock is
>   Chicago time + 8 h. Roll contracts were chosen by that same day's volume (mild
>   hindsight, likely small). The NQ/MNQ join date and any price adjustment are
>   unverified, so treat early-vs-late period comparisons with care.

2026-09-30. Research discussion; no EA rules changed and no new MT5 run.
Candidate remains MaxRedRun=3, MinLocation=0, bar-close threshold RR=1.

## Independently reproduced first-touch estimate

Using the saved cap-3 runs, define risk as signal candle range times $2/point
for one contract. When logged MFE reaches that risk, replace the original
gross PnL with exactly +1R. Otherwise preserve the original PnL. Deduct the
same modeled $1 round-trip commission from each trade.

| Period | Exit calculation | Gross PF | Gross avg R | Net avg R | Net dollars |
|---|---|---:|---:|---:|---:|
| 2015-2019 | Original bar-close rule | 1.220 | 0.094 | -0.006 | 8,008 |
| 2015-2019 | Same-entry first touch +1R | 1.187 | 0.059 | -0.042 | 3,867 |
| 2020-2026 | Original bar-close rule | 1.132 | 0.084 | 0.060 | 37,291 |
| 2020-2026 | Same-entry first touch +1R | 1.119 | 0.061 | 0.037 | 26,345 |

This reproduces the figures supplied by Opus. The MT5 HTML entry deals were
also matched against the signal snapshots: all 7,052 earlier and 9,147 recent
fills equal the signal high, and all signal ranges reconcile. Thus the range
normalization agrees with entry minus initial signal-low stop for these runs.

49.7% / 50.1% of trades touch +1R. Of those, 20.0% / 20.2% end as gross
losers, while 71.5% / 75.2% finish above +1R. The latter trades average
0.669R / 0.605R above the threshold. Capping these winners sacrifices
$26,123 / $121,124.50, exceeding the $21,982 / $110,178.50 gained by improving
other outcomes. First touch therefore reduces net dollars by $4,141 / $10,946.

For this specific comparison, MFE during an open position is sufficient to
establish a target touch on the recorded simulation path, with unchanged SL.
There is no need to reconstruct the order of MAE and MFE. The result is still
a same-entry estimate: it does not model new signals made available by early
exits, alternative execution/slippage, or the true tick path behind M1 OHLC.
The EA also includes final realized PnL in MFE. This remains an idealized
exact-target fill calculation, including when a generated price jumps over it.

The M30 signal scale may make ambiguous M1 events infrequent; their frequency
has not been measured here. In a future replay, count ambiguous stop/target
minutes and compare both possible orderings before deciding they matter.
MFE ends at the original exit and cannot answer how a longer hold performs.

## Data construction evidence

The user reports combining Databento NQ history (back to approximately 2010)
and MNQ history, with synthetic timestamps designed for a regular session to
open at 01:00 and end with the 23:59 minute. Short sessions can differ.

Inspected external source:
`I:\PycharmProjects\1500_count\DATABENTO\Convert_databento_csv_to_mt5.py`.

- Parses UTC timestamps, converts to America/Chicago (US DST included), removes
  timezone information, then adds a fixed eight hours. This is an exchange-aligned
  synthetic clock. It is not Europe/Tallinn civil time during US/European DST
  mismatch weeks. Session-relative time studies should use it as designed;
  mapping to live timestamps requires an explicit timezone conversion.
- Selects the largest-volume contract using the total volume of that same
  synthetic date. The winning contract is known only after the date completes.
  This creates hindsight in contract selection if this script made the tested
  series. It does not prove the trading edge is artificial; inspect switch dates
  and compare a rule based on completed prior-session volume if necessary.
- Does not apply an additive or multiplicative price adjustment. OHLC values
  pass through apart from numeric parsing and output formatting. Contract IDs
  are omitted from the MT5 export, so provenance must be retained separately.
- `Dominant_contracts_builder.py` also uses same-day total volume and the same
  Chicago-plus-eight clock. The separate broker-time normalization script does
  not establish how the Databento series was joined or price-adjusted.

The inspected converter currently names a recent input file. It is evidence of
the available conversion method, not proof that every part of curr6 was produced
with this exact version. The NQ/MNQ join date, any additional price adjustment,
and the exact build chain remain unverified. The user subsequently recalled
that a price change might have been needed for part of the history around 2017,
but could not confirm it; the scripts were mostly used for time adjustment.
Do not infer an adjustment method or a confirmed transition date from that
recollection. This uncertainty does not alter the reproduced exit comparison
on the current dataset, but limits conclusions about early-versus-late regimes
and historical commission measured in R.

Databento's own continuous-contract service supplies original unadjusted prices
([documentation](https://databento.com/docs/examples/symbology/continuous)).
That vendor default alone does not establish what a custom local series contains.
Older NQ-based results should be described as MNQ-sized proxy results, not MNQ
execution history. Test source-transition and roll-date sensitivity before
attributing differences entirely to market regime.

## Interpretation and proposed direction

Preserve the core rule: take a qualifying bar-close exit at the specified R
or better, retaining the existing protective SL and session-close rules.
The estimate supports preserving overshoot; it does not prove that longer
holds are better. Higher bar-close thresholds and fixed resting targets are
different experiments, so identify which the user's earlier RR tests covered
before repeating them.

Suggested next exit comparison, if not already covered: the existing bar-close
rule with RR=1, 1.5 and 2, unchanged entry/SL/session inputs, through complete
MT5 runs. These are proposed values, not an adopted or completed protocol.
Full runs must include changed position availability. Trailing stops introduce
another rule and can conflict with the intended qualifying-close condition;
leave them for a separately defined hypothesis.

Choose a primary objective before ranking candidates. Net average R describes
ideal equal-risk weighting; net dollars with actual contract sizing describes
fixed-contract performance. The earlier baseline earns $8,008 while averaging
-0.006 net R, so the distinction already changes its verdict. Per-contract
commission divided by initial dollar risk is size-invariant under linear costs,
but that does not make the two portfolio weighting policies equivalent.
Retain both metrics and assess drawdown under the intended feasible sizing.

Deprioritize further preceding-bar filters. Broad session-relative time blocks
are a reasonable separate diagnostic, with signal time and fill time separated
and shortened sessions identified. Do not optimize clock windows at the same
time as RR. Previously viewed periods remain exploratory.

## Reproduce

```powershell
.\venv\Scripts\python.exe python\estimate_first_touch.py
```

Reads the original cap-3 CSVs/HTML reports and verified signal snapshots.
Writes `Reports/exit_estimate_20260930/first_touch.json`; no source data are
modified. The script checks trade matching, one-lot entries, entry prices,
signal ranges and consistency of MFE with realized PnL before calculating.
