"""Q24 trading-run checks (protocol: docs/setups/horizontal/support-reclaim-long/q25-support-reclaim/PROTOCOL.md, "Verification").

For one trading job of Reports/levels/support_reclaim_runs_20261007/:
1. Logged bars = eligible bars of the verified classify-only run (same threshold), minus bars that open with a
   position; differences must be bar-boundary effects (a fill or a stop on a bar's first tick, before OnTick).
2. Replay: the classification does not depend on fills, so every logged row must carry its bar's verified
   classify-only row, and an order is placed exactly when the status is "order": buy stop at L (C1: high(s)), stop
   low(s); "replaced" exactly when an order was pending at the bar's open.
3. Order life on one-minute data: from its bar's open until the first of the next order, the open of bar t + 3, or
   the open of the first non-eligible bar (window exit / flatten), the order fills in the first minute whose high
   reaches the entry unless an earlier minute's low touched low(s), which cancels it. Inside a minute the tester's
   ticks carry the source file's spread (1 point = 0.01, below the 0.25 tick), so a buy stop on the tick grid fills
   only when the bid trades at the entry. Checked empirically: with a one-tick spread 329 of 4,350 primary orders
   disagree, with this rule 1.
   Same-minute fill and touch are OHLC-ambiguous; a fill on the first tick of the end bar is a bar-boundary fill.
4. Execution audit: fills at or above the entry with the logged stop; the ledger matches the fills; one position at
   a time; every trade exits its session; MT5 trades and net match the ledger.

Usage: verify_support_reclaim_trade.py [VARIANT [JOB ...]]   (variant '' or nocancel; jobs primary, c1, primary_s1, c1_s1)
With CancelOnLow = false (the nocancel variant) no touch cancellation is predicted.
"""
import json
import sys

import numpy as np
import pandas as pd

from analyze_price_levels import sha256
from prepare_support_reclaim import EXPERT, RUN, STEM, VARIANTS
from trend_regimes import SOURCE
from verify_location_validation import read_rows
from verify_support_reclaim import RUN as CLASSIFY, STEM as CLASSIFY_STEM, bars

TIME = "%Y.%m.%d %H:%M:%S"
FILL_OFFSET = 0.0  # the bid must reach a buy stop (intrabar spread 0.01 < tick); see the docstring
KEYS = ["status", "s_time", "level", "key_time", "t0_time", "members", "atr", "entry", "stop", "risk", "known_pivots",
        "levels", "levels_live", "levels_broken", "s_red", "same_contract", "bid", "ask"]


def load_log(path):
    g = pd.DataFrame(read_rows(path))
    for c in ("bar_time", "s_time", "key_time", "t0_time"):
        g[c] = pd.to_datetime(g[c].replace("", np.nan), format=TIME)
    for c in ("open", "ask", "bid", "level", "atr", "entry", "stop", "risk", "order_entry", "order_stop"):
        if c in g:
            g[c] = g[c].astype(float)
    for c in ("members", "known_pivots", "levels", "levels_live", "levels_broken", "s_red", "same_contract",
              "pending_at_open"):
        if c in g:
            g[c] = g[c].astype(int)
    assert g.bar_time.is_unique
    return g


def load_table(path, times, floats):
    f = pd.DataFrame(read_rows(path))
    for c in times:
        f[c] = pd.to_datetime(f[c].replace("", np.nan), format=TIME)
    for c in floats:
        f[c] = pd.to_numeric(f[c])
    return f


def load_ledger(tag, run=RUN):
    led = load_table(run / f"runband_{tag}_1.00.csv", ("entry_time", "exit_time", "signal_time"),
                     ("trade_profit", "candle_range", "exit_reason", "base_entry", "initial_stop", "exit_price",
                      "assigned_rr"))
    led["qualified_time"] = pd.to_datetime(led.qualified_time.replace("", np.nan), format=TIME)
    return led.sort_values("entry_time").reset_index(drop=True)


def minutes():
    """The tester's one-minute source: (times, highs, lows, opens) as numpy arrays."""
    m = pd.read_csv(SOURCE, sep="\t", usecols=["<DATE>", "<TIME>", "<OPEN>", "<HIGH>", "<LOW>"])
    t = pd.to_datetime(m["<DATE>"] + " " + m["<TIME>"], format="%Y.%m.%d %H:%M:%S").to_numpy()
    return t, m["<HIGH>"].to_numpy(), m["<LOW>"].to_numpy(), m["<OPEN>"].to_numpy()


def same(a, b):
    return (a == b) | (pd.isna(a) & pd.isna(b))


def expected_life(orders, eligible, b, m1, cancel_on_low=True):
    """Predicted outcome of every placed order from one-minute data (see the module docstring, point 3)."""
    mt, mh, ml, mo = m1
    idx = b.index
    pos = pd.Series(np.arange(len(b)), index=idx)
    elig = set(eligible)
    nxt = orders.bar_time.shift(-1)
    out = []
    for r, next_order in zip(orders.itertuples(), nxt):
        t = int(pos[r.bar_time])
        ends = [(idx[t + 3], "expired")] if t + 3 < len(idx) else []
        ends += [(idx[k], "external") for k in (t + 1, t + 2) if k < len(idx) and idx[k] not in elig][:1]
        if pd.notna(next_order):
            ends.append((next_order, "replaced"))
        end, end_reason = min(ends) if ends else (idx[-1] + pd.Timedelta("30min"), "end")
        lo, hi = np.searchsorted(mt, r.bar_time.to_datetime64()), np.searchsorted(mt, end.to_datetime64())
        fill = np.flatnonzero(mh[lo:hi] >= r.order_entry - FILL_OFFSET)
        touch = np.flatnonzero(ml[lo:hi] <= r.order_stop) if cancel_on_low else np.empty(0, int)
        f = fill[0] if len(fill) else None
        c = touch[0] if len(touch) else None
        first_end = mt[hi] if hi < len(mt) else None  # the first minute of the end bar (its first tick)
        if c == 0 and mo[lo] <= r.order_stop:
            # The order is placed on the bar's first tick: a low at that open tick precedes the order and cannot
            # cancel it; later ticks of the minute may or may not touch again (one-minute OHLC cannot tell).
            out.append(dict(bar_time=r.bar_time, expected="placement_tick_touch", expected_minute=pd.Timestamp(mt[lo]),
                            end_time=end, end_reason=end_reason,
                            end_first_minute=pd.Timestamp(first_end) if first_end is not None else pd.NaT))
            continue
        if f is not None and (c is None or f < c):
            kind, when = "fill", mt[lo + f]
        elif c is not None and (f is None or c < f):
            kind, when = "touch_low", mt[lo + c]
        elif f is not None:
            kind, when = "ambiguous", mt[lo + f]
        else:
            kind, when = end_reason, end.to_datetime64()
        out.append(dict(bar_time=r.bar_time, expected=kind, expected_minute=pd.Timestamp(when), end_time=end,
                        end_reason=end_reason, end_first_minute=pd.Timestamp(first_end) if first_end is not None else pd.NaT))
    return pd.DataFrame(out)


def verify(job, m1, b, variant=""):
    run, stem, _ = VARIANTS[variant]
    tag = f"{stem}_{job}"
    manifest = json.loads((run / "manifest.json").read_text())
    inputs = next(j for j in manifest["jobs"] if j["tag"] == tag)["inputs"]
    mode = inputs["ReclaimMode"]
    assert sha256(run / f"{EXPERT}.mq5") == manifest["expert_sha256"]
    stats = read_rows(run / f"{tag}_reclaim_stats.csv")[0]
    mt5 = read_rows(run / f"runband_{tag}_1.00_stats.csv")[0]
    g = load_log(run / f"{tag}_reclaim.csv")
    cjob = "classify_s1" if inputs["BreakDepthA"] == 0.5 else "classify"
    cls = load_log(CLASSIFY / f"{CLASSIFY_STEM}_{cjob}_reclaim.csv")
    fills = load_table(run / f"{tag}_fills.csv", ("fill_time", "order_bar", "s_time", "key_time"),
                       ("fill_price", "sl", "order_entry", "order_stop", "level", "age"))
    cancels = load_table(run / f"{tag}_cancels.csv", ("cancel_time", "order_bar"), ("order_entry", "order_stop", "age", "bid"))
    led = load_ledger(tag, run)
    pos = pd.Series(np.arange(len(b)), index=b.index)
    mt = m1[0]

    def first_minute(bar):
        return pd.Timestamp(mt[np.searchsorted(mt, bar.to_datetime64())])

    # 1. Which bars were logged.
    eligible = pd.DatetimeIndex(cls.bar_time)
    held = np.zeros(len(eligible), bool)
    for e, x in zip(led.entry_time, led.exit_time):
        held |= (eligible > e) & (eligible <= x)
    expected_bars = eligible[~held]
    extra, absent = g.bar_time[~g.bar_time.isin(expected_bars)], expected_bars[~expected_bars.isin(g.bar_time)]
    stop_open = led[led.exit_reason == 4]
    stop_open = stop_open[stop_open.exit_time.dt.floor("min") ==
                          stop_open.exit_time.dt.floor("30min").map(first_minute)].exit_time.dt.floor("30min")
    fill_open = fills[fills.fill_time.dt.floor("min") == fills.fill_time.dt.floor("30min").map(first_minute)]
    extra_unexplained = extra[~extra.isin(stop_open)]
    absent_unexplained = absent[~absent.isin(fill_open.fill_time.dt.floor("30min"))]

    # 2. Replay against the verified classification.
    m = g.merge(cls[["bar_time"] + KEYS], on="bar_time", how="left", suffixes=("", "_cls"), validate="one_to_one")
    checks = {f"{k}_matches_classify": same(m[k], m[f"{k}_cls"]) for k in KEYS}
    t = pos.reindex(m.bar_time).to_numpy()
    s_low, s_high = b.low.to_numpy()[t - 1], b.high.to_numpy()[t - 1]
    want = m.status_cls == "order"
    m["action_py"] = np.where(want, np.where(m.pending_at_open == 1, "replaced", "placed"), "no_order")
    checks["action"] = m.action == m.action_py
    placed = m.action.isin(["placed", "replaced"])
    entry_py = m.level_cls if mode == 2 else pd.Series(s_high, index=m.index)
    checks["order_entry"] = m.loc[placed, "order_entry"] == entry_py[placed]
    checks["order_stop_is_low_s"] = m.loc[placed, "order_stop"] == s_low[placed.to_numpy()]
    bad = pd.Series(False, index=m.index)
    for ok in checks.values():
        bad.loc[ok.index[~ok.to_numpy()]] = True

    # 3. Order life on one-minute data.
    orders = m[placed].sort_values("bar_time").reset_index(drop=True)
    life = expected_life(orders, eligible, b, m1, str(inputs.get("CancelOnLow", "true")).lower() == "true")
    actual = pd.concat([fills.assign(outcome="fill", when=fills.fill_time)[["order_bar", "outcome", "when"]],
                        cancels.assign(outcome=cancels.reason, when=cancels.cancel_time)[["order_bar", "outcome", "when"]]])
    assert actual.order_bar.is_unique and len(actual) == len(orders), "every order needs exactly one outcome"
    life = life.merge(actual.rename(columns={"order_bar": "bar_time"}), on="bar_time", how="left", validate="one_to_one")
    life["minute"] = life.when.dt.floor("min")
    exact = (life.outcome == life.expected) & ((life.minute == life.expected_minute) |
                                               life.expected.isin(["expired", "replaced", "external", "end"]))
    ambiguous = (life.expected == "ambiguous") & life.outcome.isin(["fill", "touch_low"]) & (life.minute == life.expected_minute)
    placement = life.expected == "placement_tick_touch"
    boundary = (life.outcome == "fill") & life.expected.isin(["expired", "replaced", "external"]) & \
               (life.minute == life.end_first_minute)
    life["agrees"] = exact | ambiguous | boundary | placement
    life_summary = dict(orders=len(life), exact=int(exact.sum()), ohlc_ambiguous=int(ambiguous.sum()),
                        boundary_fills=int(boundary.sum()), placement_tick_touch=int(placement.sum()),
                        placement_tick_outcomes=life[placement].outcome.value_counts().to_dict(), disagree=int((~life.agrees).sum()),
                        expected=life.expected.value_counts().to_dict(), actual=life.outcome.value_counts().to_dict())

    # 4. Execution audit.
    o = orders.set_index("bar_time").reindex(fills.order_bar)
    n = len(fills)
    audit = dict(
        fills=n, fill_from_placed_order=int(o.order_entry.notna().sum()),
        entry_matches_log=int((o.order_entry.to_numpy() == fills.order_entry.to_numpy()).sum()),
        stop_matches_log=int((o.order_stop.to_numpy() == fills.order_stop.to_numpy()).sum()),
        sl_is_order_stop=int((fills.sl == fills.order_stop).sum()),
        fill_at_or_above_entry=int((fills.fill_price >= fills.order_entry - 1e-9).sum()),
        fill_within_life=int((fills.age < inputs["OrderLife"]).sum()),
        ledger_rows=len(led), ledger_rr_is_1=int((led.assigned_rr == 1.0).sum()),
        ledger_entry_time_matches=int((led.entry_time == fills.fill_time).sum()),
        ledger_entry_price_matches=int((led.base_entry == fills.fill_price).sum()),
        ledger_stop_matches=int((led.initial_stop == fills.sl).sum()),
        ledger_range_is_planned_r=int(np.isclose(led.candle_range, fills.order_entry - fills.order_stop).sum()),
        ledger_signal_is_s=int((led.signal_time == fills.s_time).sum()),
        same_session_exit=int((led.entry_time.dt.normalize() == led.exit_time.dt.normalize()).sum()),
        overlapping_trades=int((led.entry_time.iloc[1:].to_numpy() < led.exit_time.iloc[:-1].to_numpy()).sum()),
        mt5_trades=int(mt5["trades"]),
        mt5_net_matches_ledger=bool(np.isclose(led.trade_profit.sum(), float(mt5["net_profit"]), atol=1e-6)))
    result = dict(tag=tag, inputs=inputs, stats=stats, log_rows=len(g), expected_rows=len(expected_bars),
                  logged_not_expected=len(extra), expected_not_logged=len(absent),
                  logged_not_expected_unexplained=len(extra_unexplained),
                  expected_not_logged_unexplained=len(absent_unexplained),
                  actions=m.action.value_counts().to_dict(), field_mismatches={k: int((~v).sum()) for k, v in checks.items()},
                  mismatched_rows=int(bad.sum()), order_life=life_summary, audit=audit,
                  log_sha256=sha256(run / f"{tag}_reclaim.csv"))
    (run / f"{tag}_verification.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    m[bad].to_csv(run / f"{tag}_mismatches.csv", index=False)
    life.to_csv(run / f"{tag}_order_life.csv", index=False)
    return result


def main(variant="", *jobs):
    m1, b = minutes(), bars()
    for job in jobs or ("primary", "c1", "primary_s1", "c1_s1"):
        r = verify(job, m1, b, variant)
        print(json.dumps({k: v for k, v in r.items() if k not in ("stats", "inputs")}, indent=1, default=str))


if __name__ == "__main__":
    main(*sys.argv[1:])
