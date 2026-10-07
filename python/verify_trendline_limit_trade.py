"""Q20 trading-run checks (protocol: docs/setups/trendlines/uptrend-bounce-long/q20-trendline-limit/PROTOCOL.md, "Verification").

For one trading job of Reports/trendlines/trendline_limit_runs_20261005/:
1. Logged bars = eligible bars of the verified classify-only run, minus bars that open with a position.
2. Replay: every logged order is recomputed in Python from closed bars and the run's own fills:
   primary - the frozen lines minus consumed episodes (re-armed by a close >= line + A(t) at or after the fill bar);
   C1 / C2 - the classify-only status, control arming (close >= P + A(t) after the latest fill) and the delta table.
3. Execution audit: each fill comes from the order resting in its bar, at or below the limit, with the logged stop;
   the trade ledger matches the fills, one position at a time, nothing held past the session.

Usage: verify_trendline_limit_trade.py TAG [TAG ...]
"""
import json
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

from analyze_price_levels import sha256
from level_visit import swing_lows
from trendline_limit import TICK, armed_lines, choose_line, floor_tick
from trendline_support import line_value
from verify_location_validation import read_rows
from verify_trendline_limit import RUN as CLASSIFY, bars

RUN = CLASSIFY.parent / "trendline_limit_runs_20261005"
TBARS = 1500  # bars copied by the EA (CopyRates from shift 1)
TIME = "%Y.%m.%d %H:%M:%S"
_B = _PIV = _FILLS = None
_JOB = {}


def load_log(tag):
    g = pd.DataFrame(read_rows(RUN / f"{tag}_limit.csv"))
    for c in ("bar_time", "anchor1_time", "anchor2_time"):
        g[c] = pd.to_datetime(g[c].replace("", np.nan), format=TIME)
    for c in ("open", "ask", "bid", "line", "limit", "stop", "atr", "delta"):
        g[c] = g[c].astype(float)
    for c in ("known_pivots", "lines_armed", "lines_below"):
        g[c] = g[c].astype(int)
    assert g.bar_time.is_unique
    return g


def load_fills(tag):
    f = pd.DataFrame(read_rows(RUN / f"{tag}_fills.csv"))
    if not len(f):
        return f
    for c in ("fill_time", "order_bar", "anchor1_time", "anchor2_time"):
        f[c] = pd.to_datetime(f[c].replace("", np.nan), format=TIME)
    for c in ("fill_price", "sl", "order_limit", "order_stop", "line", "delta"):
        f[c] = f[c].astype(float)
    f["fill_bar"] = f.fill_time.dt.floor("30min")
    return f


def _init(job, fills):
    global _B, _PIV, _FILLS, _JOB
    _B = bars()
    _PIV = swing_lows(_B.low.to_numpy(), _B.contract.to_numpy(), 5)
    _JOB = job
    pos = pd.Series(np.arange(len(_B)), index=_B.index)
    _FILLS = fills.assign(fb=pos.reindex(fills.fill_bar).to_numpy()) if len(fills) else fills


def _rearmed(t, fb, threshold):
    """Any close in the EA's copied bars, at or after the fill bar, at or above threshold(k)."""
    close = _B.close.to_numpy()
    k = np.arange(max(int(fb), t - min(TBARS, t)), t)
    return bool(len(k) and (close[k] >= threshold(k)).any())


def _primary(t, ask, bar_time):
    reason, a, known, lines = armed_lines(_B, t, _PIV)
    if reason:
        return dict(status=reason)
    low, off, stop_a = _B.low.to_numpy(), _JOB["LimitTickOffset"], _JOB["LimitStopA"]
    times = _B.index
    earlier = _FILLS[_FILLS.fill_time < bar_time] if len(_FILLS) else _FILLS
    kept = []
    for x in lines:
        if len(earlier):
            hit = earlier[(earlier.anchor1_time == times[x["i"]]) & (earlier.anchor2_time == times[x["j"]])]
            if len(hit) and not _rearmed(t, hit.fb.max(),
                                         lambda k, i=x["i"], j=x["j"]: line_value(i, j, low, k) + a):
                continue
        kept.append(x)
    out = dict(lines_armed=len(kept), known_pivots=len(known), atr=a)
    if not kept:
        return dict(out, status="no_line")
    out["lines_below"] = sum(x["value"] < ask for x in kept)
    x = choose_line(kept, ask)
    if x is None:
        return dict(out, status="above_price")
    base = float(floor_tick(x["value"]))
    return dict(out, status="order", action="placed", limit=base - off * TICK,
                stop=float(floor_tick(base - stop_a * a)) - off * TICK,
                anchor1_time=times[x["i"]], anchor2_time=times[x["j"]])


def _control(t, ask, bar_time, status, a, delta):
    eligible = status == "order" or (_JOB["LimitMode"] == 4 and status in ("no_line", "above_price"))
    if not eligible:
        return dict(action="no_order")
    earlier = _FILLS[_FILLS.fill_time < bar_time] if len(_FILLS) else _FILLS
    if len(earlier):
        last = earlier.iloc[-1]
        if not _rearmed(t, last.fb, lambda k: last.fill_price + a):
            return dict(action="unarmed")
    off, stop_a = _JOB["LimitTickOffset"], _JOB["LimitStopA"]
    base = float(floor_tick(float(_B.open.iloc[t]) - delta * a))
    limit = base - off * TICK
    if not limit < ask:
        return dict(action="above_price")
    return dict(action="placed", limit=limit, stop=float(floor_tick(base - stop_a * a)) - off * TICK)


def _replay(chunk):
    out = []
    for row in chunk:
        if _JOB["LimitMode"] == 2:
            r = _primary(row["t"], row["ask"], row["bar_time"])
            r.setdefault("action", "no_order")
        else:
            r = _control(row["t"], row["ask"], row["bar_time"], row["status_classify"], row["atr_classify"],
                         row["delta_table"])
        out.append(dict(t=row["t"], **{f"{k}_py": v for k, v in r.items()}))
    return out


def verify(tag):
    manifest = json.loads((RUN / "manifest.json").read_text())
    job = next(j for j in manifest["jobs"] if j["tag"] == tag)
    inputs = job["inputs"]
    assert sha256(RUN / "RTL_trendline_limit.mq5") == manifest["expert_sha256"]
    stats = read_rows(RUN / f"{tag}_limit_stats.csv")[0]
    mt5 = read_rows(RUN / f"runband_{tag}_1.00_stats.csv")[0]
    g = load_log(tag)
    fills = load_fills(tag)
    b = bars()
    pos = pd.Series(np.arange(len(b)), index=b.index)
    g["t"] = pos.reindex(g.bar_time).to_numpy()
    cls = pd.read_csv(CLASSIFY / "trendline_limit_20261005_classify_bars.csv", parse_dates=["bar_time"])
    g = g.merge(cls[["bar_time", "status_ea", "atr_ea"]].rename(columns={"status_ea": "status_classify"}),
                on="bar_time", how="left", validate="one_to_one")
    assert g.status_classify.notna().all(), "logged a bar outside the eligible set"
    py_atr = b.atr.to_numpy()[g.t.to_numpy()]
    g["atr_classify"] = py_atr
    d = pd.read_csv(RUN / manifest["deltas"], dtype={"delta": str})
    d["bar_time"] = pd.Timestamp("1970-01-01") + pd.to_timedelta(d.unix_time, unit="s")
    g = g.merge(d.assign(delta_table=d.delta.astype(float))[["bar_time", "delta_table"]], on="bar_time", how="left")

    # 1. Which bars were logged.
    led = pd.DataFrame(read_rows(RUN / f"runband_{tag}_1.00.csv"))
    for c in ("entry_time", "exit_time"):
        led[c] = pd.to_datetime(led[c], format=TIME)
    eligible = pd.DatetimeIndex(cls.bar_time)
    held = np.zeros(len(eligible), bool)
    for e, x in zip(led.entry_time, led.exit_time):
        held |= (eligible > e) & (eligible <= x)
    expected = eligible[~held]
    extra, absent = g.bar_time[~g.bar_time.isin(expected)], expected[~expected.isin(g.bar_time)]

    # 2. Replay.
    rows = g[["t", "ask", "bar_time", "status_classify", "atr_classify", "delta_table"]].to_dict("records")
    chunks = [rows[k:k + 2000] for k in range(0, len(rows), 2000)]
    with Pool(8, initializer=_init, initargs=(inputs, fills)) as pool:
        py = pd.DataFrame([r for c in pool.map(_replay, chunks) for r in c])
    m = g.merge(py, on="t", validate="one_to_one")
    same_action = m.action == m.action_py
    placed = same_action & (m.action == "placed")
    checks = dict(action=same_action,
                  limit=m.loc[placed, "limit"] == m.loc[placed, "limit_py"],
                  stop=m.loc[placed, "stop"] == m.loc[placed, "stop_py"])
    if inputs["LimitMode"] == 2:
        checks["status"] = m.status == m.status_py
        checks["anchors"] = (m.loc[placed, "anchor1_time"] == m.loc[placed, "anchor1_time_py"]) & \
                            (m.loc[placed, "anchor2_time"] == m.loc[placed, "anchor2_time_py"])
        avail = m.lines_armed_py.notna() & (m.status == m.status_py)
        checks["lines_armed"] = m.loc[avail, "lines_armed"] == m.loc[avail, "lines_armed_py"]
    else:
        checks["status"] = m.status == m.status_classify
        checks["delta"] = (m.loc[placed, "delta"] - m.loc[placed, "delta_table"]).abs() <= 1e-10  # logged with 10 decimals
    bad = pd.Series(False, index=m.index)
    for ok in checks.values():
        bad.loc[ok.index[~ok.to_numpy()]] = True

    # 3. Execution audit.
    orders = m[m.action == "placed"].set_index("bar_time")
    audit = {}
    if len(fills):
        o = orders.reindex(fills.order_bar)
        audit["fill_from_placed_order"] = int(o.limit.notna().sum())
        audit["fill_in_order_bar"] = int((fills.fill_bar == fills.order_bar).sum())
        audit["limit_matches_log"] = int((o.limit.to_numpy() == fills.order_limit.to_numpy()).sum())
        audit["stop_matches_log"] = int((o.stop.to_numpy() == fills.order_stop.to_numpy()).sum())
        audit["sl_is_order_stop"] = int((fills.sl == fills.order_stop).sum())
        audit["fill_at_or_below_limit"] = int((fills.fill_price <= fills.order_limit + 1e-9).sum())
        for c in ("base_entry", "initial_stop", "candle_range", "trade_profit"):
            led[c] = led[c].astype(float)
        led_sorted = led.sort_values("entry_time").reset_index(drop=True)
        audit["ledger_rows"] = len(led)
        audit["ledger_entry_time_matches"] = int((led_sorted.entry_time == fills.fill_time).sum())
        audit["ledger_entry_price_matches"] = int((led_sorted.base_entry == fills.fill_price).sum())
        audit["ledger_stop_matches"] = int((led_sorted.initial_stop == fills.sl).sum())
        audit["ledger_range_is_planned_r"] = int(np.isclose(led_sorted.candle_range,
                                                            fills.order_limit - fills.order_stop).sum())
        audit["same_session_exit"] = int((led.entry_time.dt.normalize() == led.exit_time.dt.normalize()).sum())
        audit["overlapping_trades"] = int((led_sorted.entry_time.iloc[1:].to_numpy() <
                                           led_sorted.exit_time.iloc[:-1].to_numpy()).sum())
        audit["mt5_trades"] = int(mt5["trades"])
        audit["mt5_net_matches_ledger"] = bool(np.isclose(led.trade_profit.sum(), float(mt5["net_profit"]),
                                                          atol=1e-6))
    result = dict(tag=tag, inputs=inputs, stats=stats,
                  log_rows=len(g), expected_rows=len(expected), logged_not_expected=len(extra),
                  expected_not_logged=len(absent), extra_examples=[str(x) for x in extra.head(5)],
                  absent_examples=[str(x) for x in absent[:5]],
                  placed=int((m.action == "placed").sum()), fills=len(fills),
                  field_mismatches={k: int((~v).sum()) for k, v in checks.items()},
                  field_compared={k: int(len(v)) for k, v in checks.items()},
                  mismatched_rows=int(bad.sum()), audit=audit, log_sha256=sha256(RUN / f"{tag}_limit.csv"))
    (RUN / f"{tag}_verification.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    m[bad].to_csv(RUN / f"{tag}_mismatches.csv", index=False)
    return result


def main(*tags):
    for tag in tags:
        r = verify(tag)
        print(json.dumps({k: v for k, v in r.items() if k not in ("stats", "inputs")}, indent=1, default=str))


if __name__ == "__main__":
    main(*sys.argv[1:])
