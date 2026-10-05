"""Q21 trading-run checks (protocol: docs/trendlines/BREAKDOWN_SHORT_PROTOCOL.md, "Verification").

For one trading job of Reports/trendlines/trendline_breakdown_runs_20261006/:
1. Logged bars = eligible bars of the verified classify-only run (same threshold), minus bars that open with a
   position.
2. Replay: the classification does not depend on fills, so every logged row must carry the verified classify-only
   row of its bar (status, bar s, line, anchors, line counts, colour, contract), and the action follows from it:
   primary / S1 - status order (gap_below = no order); C1 - red s, available, >= 1 armed line; C2 - red s, same
   contract; no order when the bid is at or below low(s). Order = sell stop at low(s), stop high(s) (from the bars).
3. Execution audit: each fill is a short from a placed order, at or below its entry, with the logged stop, in the
   order's bar (bar-boundary fills counted); the ledger matches the fills; one position at a time; nothing held past
   the session; MT5 trades and net match the ledger.

Usage: verify_trendline_breakdown_trade.py JOB [JOB ...]   (primary, s1, c1, c2; *_rr2 for the 2R follow-up)
"""
import json
import sys

import numpy as np
import pandas as pd

from analyze_price_levels import sha256
from trend_regimes import SOURCE
from prepare_trendline_breakdown import EXPERT, RUN, STEM, rr_label
from verify_location_validation import read_rows
from verify_trendline_breakdown import RUN as CLASSIFY, STEM as CLASSIFY_STEM, bars

TIME = "%Y.%m.%d %H:%M:%S"
KEYS = ["status", "s_time", "line", "anchor1_time", "anchor2_time", "atr", "known_pivots", "lines_armed",
        "lines_live", "lines_broken", "s_red", "same_contract", "entry", "stop"]


def load_log(path):
    g = pd.DataFrame(read_rows(path))
    for c in ("bar_time", "s_time", "anchor1_time", "anchor2_time"):
        g[c] = pd.to_datetime(g[c].replace("", np.nan), format=TIME)
    for c in ("open", "ask", "bid", "line", "entry", "stop", "atr", "order_entry", "order_stop"):
        if c in g:
            g[c] = g[c].astype(float)
    for c in ("known_pivots", "lines_armed", "lines_live", "lines_broken", "s_red", "same_contract"):
        g[c] = g[c].astype(int)
    assert g.bar_time.is_unique
    return g


def load_fills(tag):
    f = pd.DataFrame(read_rows(RUN / f"{tag}_fills.csv"))
    for c in ("fill_time", "order_bar", "s_time", "anchor1_time", "anchor2_time"):
        f[c] = pd.to_datetime(f[c].replace("", np.nan), format=TIME)
    for c in ("fill_price", "sl", "order_entry", "order_stop", "line"):
        f[c] = f[c].astype(float)
    f["fill_bar"] = f.fill_time.dt.floor("30min")
    return f


def load_ledger(tag, rr="1.00"):
    led = pd.DataFrame(read_rows(RUN / f"runband_{tag}_{rr}.csv"))
    for c in ("entry_time", "exit_time", "signal_time"):
        led[c] = pd.to_datetime(led[c], format=TIME)
    led["qualified_time"] = pd.to_datetime(led.qualified_time.replace("", np.nan), format=TIME)
    for c in ("trade_profit", "candle_range", "exit_reason", "base_entry", "initial_stop", "exit_price", "direction",
              "assigned_rr"):
        led[c] = pd.to_numeric(led[c])
    return led.sort_values("entry_time").reset_index(drop=True)


def first_minutes(bar_times):
    """First one-minute bar of each given M30 bar in the tester's source data (its first tick)."""
    want = set(pd.DatetimeIndex(bar_times).normalize())
    out = {}
    if not want:
        return out
    for chunk in pd.read_csv(SOURCE, sep="\t", usecols=["<DATE>", "<TIME>"], chunksize=500000):
        day = pd.to_datetime(chunk["<DATE>"], format="%Y.%m.%d")
        keep = day.isin(want)
        if keep.any():
            t = pd.to_datetime(chunk.loc[keep, "<DATE>"] + " " + chunk.loc[keep, "<TIME>"], format="%Y.%m.%d %H:%M:%S")
            for bar, first in t.groupby(t.dt.floor("30min")).min().items():
                out[bar] = min(out.get(bar, first), first)
    return out


def same(a, b):
    """Equal, treating NaN/NaT == NaN/NaT."""
    return (a == b) | (pd.isna(a) & pd.isna(b))


def verify(job):
    tag = f"{STEM}_{job}"
    manifest = json.loads((RUN / "manifest.json").read_text())
    inputs = next(j for j in manifest["jobs"] if j["tag"] == tag)["inputs"]
    mode = inputs["BreakMode"]
    assert sha256(RUN / f"{EXPERT}.mq5") == manifest["expert_sha256"]
    stats = read_rows(RUN / f"{tag}_breakdown_stats.csv")[0]
    rr = rr_label(inputs)
    mt5 = read_rows(RUN / f"runband_{tag}_{rr}_stats.csv")[0]
    g = load_log(RUN / f"{tag}_breakdown.csv")
    cjob = "classify_s1" if inputs["BreakDepthA"] == 0.5 else "classify"
    cls = load_log(CLASSIFY / f"{CLASSIFY_STEM}_{cjob}_breakdown.csv")
    fills, led = load_fills(tag), load_ledger(tag, rr)
    b = bars()
    pos = pd.Series(np.arange(len(b)), index=b.index)

    # 1. Which bars were logged.
    held = np.zeros(len(cls), bool)
    eligible = pd.DatetimeIndex(cls.bar_time)
    for e, x in zip(led.entry_time, led.exit_time):
        held |= (eligible > e) & (eligible <= x)
    expected = eligible[~held]
    extra, absent = g.bar_time[~g.bar_time.isin(expected)], expected[~expected.isin(g.bar_time)]
    # Bar-boundary effects (as in Q20): the tester matches stops and pending orders on a bar's first tick, before
    # OnTick. A stop hit then leaves the EA flat in time to log the bar; an order filled then (still live from the
    # previous bar) means the bar opens in a position. Anything else is unexplained.
    stops = led[led.exit_reason == 4]
    first_minute = first_minutes(stops.exit_time.dt.floor("30min")[stops.exit_time.dt.floor("30min").isin(extra)])
    stop_at_open = stops[stops.exit_time.dt.floor("min") ==
                         stops.exit_time.dt.floor("30min").map(first_minute)]
    boundary = fills[fills.fill_bar > fills.order_bar]
    extra_unexplained = extra[~extra.isin(stop_at_open.exit_time.dt.floor("30min"))]
    absent_unexplained = absent[~absent.isin(boundary.fill_bar)]

    # 2. Replay against the verified classification.
    m = g.merge(cls[["bar_time"] + KEYS + ["bid"]], on="bar_time", how="left", suffixes=("", "_cls"),
                validate="one_to_one")
    checks = {f"{k}_matches_classify": same(m[k], m[f"{k}_cls"]) for k in KEYS + ["bid"]}
    t = pos.reindex(m.bar_time).to_numpy()
    s_low, s_high = b.low.to_numpy()[t - 1], b.high.to_numpy()[t - 1]
    avail = ~m.status_cls.isin(["missing_history", "contract_roll", "invalid_atr"])
    if mode == 2:
        cand = m.status_cls.isin(["order", "gap_below"])
    elif mode == 3:
        cand = (m.s_red_cls == 1) & avail & (m.lines_armed_cls > 0)
    else:
        cand = (m.s_red_cls == 1) & (m.same_contract_cls == 1)
    gap = cand & (m.bid <= s_low)
    m["action_py"] = np.where(gap, "gap_below", np.where(cand, "placed", "no_order"))
    checks["action"] = m.action == m.action_py
    if mode == 2:
        checks["gap_is_status"] = gap == (m.status_cls == "gap_below")
    placed = m.action == "placed"
    checks["order_entry_is_low_s"] = m.loc[placed, "order_entry"] == s_low[placed.to_numpy()]
    checks["order_stop_is_high_s"] = m.loc[placed, "order_stop"] == s_high[placed.to_numpy()]
    bad = pd.Series(False, index=m.index)
    for ok in checks.values():
        bad.loc[ok.index[~ok.to_numpy()]] = True

    # 3. Execution audit.
    orders = m[placed].set_index("bar_time")
    o = orders.reindex(fills.order_bar)
    n = len(fills)
    audit = dict(
        fills=n, placed=int(placed.sum()),
        fill_is_short=int((fills.position_type == "sell").sum()),
        fill_from_placed_order=int(o.order_entry.notna().sum()),
        fill_in_order_bar=int((fills.fill_bar == fills.order_bar).sum()),
        fill_next_bar_open=int((fills.fill_time == fills.order_bar + pd.Timedelta("30min")).sum()),
        entry_matches_log=int((o.order_entry.to_numpy() == fills.order_entry.to_numpy()).sum()),
        stop_matches_log=int((o.order_stop.to_numpy() == fills.order_stop.to_numpy()).sum()),
        sl_is_order_stop=int((fills.sl == fills.order_stop).sum()),
        fill_at_or_below_entry=int((fills.fill_price <= fills.order_entry + 1e-9).sum()),
        ledger_rows=len(led),
        ledger_direction_short=int((led.direction == -1).sum()),
        ledger_rr_matches_input=int((led.assigned_rr == float(rr)).sum()),
        ledger_entry_time_matches=int((led.entry_time == fills.fill_time).sum()),
        ledger_entry_price_matches=int((led.base_entry == fills.fill_price).sum()),
        ledger_stop_matches=int((led.initial_stop == fills.sl).sum()),
        ledger_range_is_planned_r=int(np.isclose(led.candle_range, fills.order_stop - fills.order_entry).sum()),
        ledger_signal_is_s=int((led.signal_time == fills.s_time).sum()),
        same_session_exit=int((led.entry_time.dt.normalize() == led.exit_time.dt.normalize()).sum()),
        overlapping_trades=int((led.entry_time.iloc[1:].to_numpy() < led.exit_time.iloc[:-1].to_numpy()).sum()),
        mt5_trades=int(mt5["trades"]),
        mt5_net_matches_ledger=bool(np.isclose(led.trade_profit.sum(), float(mt5["net_profit"]), atol=1e-6)))
    if mode == 2:
        sig = orders[["anchor1_time", "anchor2_time"]]
        audit["orders_per_line_max"] = int(sig.groupby(["anchor1_time", "anchor2_time"]).size().max())
        audit["fill_line_matches_log"] = int((same(o.anchor1_time.to_numpy(), fills.anchor1_time.to_numpy()) &
                                              same(o.anchor2_time.to_numpy(), fills.anchor2_time.to_numpy())).sum())
    result = dict(tag=tag, inputs=inputs, stats=stats, log_rows=len(g), expected_rows=len(expected),
                  logged_not_expected=len(extra), expected_not_logged=len(absent),
                  logged_not_expected_unexplained=len(extra_unexplained),
                  expected_not_logged_unexplained=len(absent_unexplained), boundary_fills=len(boundary),
                  extra_examples=[str(x) for x in extra.head(5)], absent_examples=[str(x) for x in absent[:5]],
                  actions=m.action.value_counts().to_dict(),
                  field_mismatches={k: int((~v).sum()) for k, v in checks.items()},
                  field_compared={k: int(len(v)) for k, v in checks.items()},
                  mismatched_rows=int(bad.sum()), audit=audit, log_sha256=sha256(RUN / f"{tag}_breakdown.csv"))
    (RUN / f"{tag}_verification.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    m[bad].to_csv(RUN / f"{tag}_mismatches.csv", index=False)
    return result


def main(*jobs):
    for job in jobs or ("primary", "s1", "c1", "c2"):
        r = verify(job)
        print(json.dumps({k: v for k, v in r.items() if k not in ("stats", "inputs")}, indent=1, default=str))


if __name__ == "__main__":
    main(*sys.argv[1:])
