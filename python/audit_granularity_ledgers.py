"""Audit strategy ledgers against MT5's complete HTML order/deal history.

The unchanged research EA occasionally omits positions that close before its
next OnTick tracking callback. Recover those trades from original orders and
deals, never from assumed R outcomes. Keep raw files intact. Existing rows must
match report entry/exit times, profit and original order price-minus-stop risk.
Recovered excursion and signal-label fields are unknown and remain NaN.
"""

import argparse
import hashlib
import html
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_instrument_baseline import load
from project_paths import PROJECT_ROOT as ROOT

TOL = 1e-6
TD = re.compile(r"<td\b[^>]*>(.*?)</td>", re.IGNORECASE)
TAG = re.compile(r"<[^>]*>")
TIME = re.compile(r"^\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}$")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def number(value):
    return float(value.replace(" ", "").replace("\xa0", ""))


def read_report(path, symbol, mode):
    """Stream the report's single-line data rows; accept only one-lot long trades."""
    orders = {}
    trades = []
    active = None
    section = None
    with Path(path).open(encoding="utf-16") as stream:
        for line in stream:
            if ">Orders<" in line:
                section = "orders"
            elif ">Deals<" in line:
                section = "deals"
            if "<tr" not in line or "</tr>" not in line:
                continue
            cells = [html.unescape(TAG.sub("", x)).strip() for x in TD.findall(line)]
            if not cells or not TIME.match(cells[0]):
                continue
            if section == "orders" and len(cells) == 11:
                if cells[2] != symbol or cells[3] not in ("buy", "buy stop"):
                    continue
                ticket = int(cells[1])
                if ticket in orders:
                    raise ValueError(f"Duplicate original buy order {ticket}")
                orders[ticket] = {"requested_price": number(cells[5]),
                                 "sl": number(cells[6]) if cells[6] else np.nan,
                                 "submitted": cells[0], "type": cells[3],
                                 "state": cells[9], "volume": cells[4]}
            elif section == "deals" and len(cells) == 13:
                if cells[3] == "balance":
                    continue
                if cells[2] != symbol:
                    raise ValueError(f"Unexpected dealt symbol in {path}: {cells[2]}")
                if abs(number(cells[8])) > TOL or abs(number(cells[9])) > TOL:
                    raise ValueError(f"Nonzero deal commission/swap in {path}; audit requires explicit treatment")
                if not np.isclose(number(cells[5]), 1.0, rtol=0, atol=TOL):
                    raise ValueError(f"Unexpected deal size in {path}: {cells[5]}")
                if cells[3] == "buy" and cells[4] == "in":
                    if active is not None:
                        raise ValueError(f"Overlapping or partial positions in {path}")
                    ticket = int(cells[7])
                    if ticket not in orders:
                        raise ValueError(f"Entry has no original buy order: {ticket}")
                    order = orders[ticket]
                    if order["state"] != "filled":
                        raise ValueError(f"Entry references unfilled order {ticket}")
                    if mode == "control" and order["type"] != "buy":
                        raise ValueError(f"Control entry used a pending order: {ticket}")
                    if mode == "rtl" and order["type"] != "buy stop":
                        raise ValueError(f"RTL entry did not use a buy stop: {ticket}")
                    risk = order["requested_price"] - order["sl"]
                    if not np.isfinite(risk) or risk <= 0:
                        raise ValueError(f"Original order SL/risk absent or invalid: {ticket}")
                    if mode == "control" and pd.Timestamp(cells[0]).floor("30min") != pd.Timestamp(order["submitted"]).floor("30min"):
                        raise ValueError(f"Control entry filled in a later M30 bar: {ticket}")
                    active = {"ticket": ticket, "entry_time": cells[0], "candle_range": risk,
                              "entry_deal": int(cells[1]), "entry_profit": number(cells[10])}
                elif cells[3] == "sell" and cells[4] == "out":
                    if active is None:
                        raise ValueError(f"Unpaired closing deal in {path}")
                    trades.append({"ticket": active["ticket"], "entry_time": active["entry_time"],
                                   "exit_time": cells[0], "trade_profit": active["entry_profit"] + number(cells[10]),
                                   "candle_range": active["candle_range"]})
                    active = None
                else:
                    raise ValueError(f"Unsupported deal direction/type in {path}: {cells[3:5]}")
    if active is not None or not trades:
        raise ValueError(f"Unclosed position or absent complete deals in {path}")
    frame = pd.DataFrame(trades)
    if frame.ticket.duplicated().any():
        raise ValueError(f"Repeated position/order identifier in {path}")
    return frame


def reconcile_totals(frame, stats_path, tag):
    stats = pd.read_csv(stats_path, sep="\t", encoding="utf-16")
    required = {"run_tag", "risk_reward", "trades", "net_profit", "gross_profit", "gross_loss"}
    if len(stats) != 1 or required.difference(stats.columns):
        raise ValueError(f"{tag}: invalid tester summary")
    s = stats.iloc[0]
    if s.run_tag != tag or not np.isclose(float(s.risk_reward), 1, rtol=0, atol=1e-9):
        raise ValueError(f"{tag}: tester tag or RR1 differs")
    if float(s.trades) != len(frame):
        raise ValueError(f"{tag}: audited count {len(frame)} differs from tester {s.trades}")
    totals = {"net_profit": float(frame.trade_profit.sum()),
              "gross_profit": float(frame.loc[frame.trade_profit > 0, "trade_profit"].sum()),
              "gross_loss": float(frame.loc[frame.trade_profit < 0, "trade_profit"].sum())}
    for field, value in totals.items():
        actual = float(s[field])
        if not np.isfinite(actual) or not np.isclose(value, actual, rtol=0, atol=TOL):
            raise ValueError(f"{tag}: audited {field}={value}, tester={actual}")
    return totals


def ensure_audited(run, job, variant, pv, fix_risk=False):
    """Return an audited ledger path, validating raw/report provenance and totals.

    fix_risk (opt-in, default off): a logged row whose risk disagrees with its original order (times and profit
    still matching) takes the order's price-minus-SL risk, is labelled "original_risk_from_order" and listed in the
    metadata. Seen when a fallback flatten and a new market entry share one OnTick. Default runs stay strict."""
    run = Path(run)
    raw_path, stats_path = (run / name for name in job["outputs"][:2])
    report_path = run / f"{job['tag']}.htm"
    out_path = run / f"{raw_path.stem}_audited.csv"
    audit_path = run / f"{job['tag']}.ledger_audit.json"
    inputs = {"raw": digest(raw_path), "stats": digest(stats_path), "report": digest(report_path)}
    completion_path = run / f"{job['tag']}.completed.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    if completion.get("tag") != job["tag"]:
        raise ValueError(f"Completion tag differs: {completion_path}")
    for filename, key in zip(job["outputs"][:2], ("raw", "stats")):
        if completion.get("outputs", {}).get(filename) != inputs[key]:
            raise ValueError(f"Completed raw/stat output changed: {filename}")
    identity = {"tag": job["tag"], "mode": job["mode"], "symbol": variant["symbol"],
                "grid_points": variant["grid_points"], "point_value": pv, "version": 1}
    if fix_risk:
        identity["fix_risk"] = True
    if audit_path.exists():
        previous = json.loads(audit_path.read_text(encoding="utf-8"))
        if previous.get("input_sha256") == inputs and previous.get("identity") == identity:
            if not out_path.exists() or previous.get("audited_sha256") != digest(out_path):
                raise ValueError(f"Audited output changed: {out_path}")
            return out_path
    raw = pd.read_csv(raw_path, sep="\t", encoding="utf-16")
    if raw.ticket.duplicated().any():
        raise ValueError(f"Raw ledger has repeated tickets: {raw_path}")
    report = read_report(report_path, variant["symbol"], job["mode"])
    report_totals = reconcile_totals(report, stats_path, job["tag"])
    ref = report.set_index("ticket")
    existing = raw.set_index("ticket")
    if not existing.index.isin(ref.index).all():
        raise ValueError(f"Raw ledger contains positions absent from tester report: {raw_path}")
    paired = ref.reindex(existing.index)
    for field in ("entry_time", "exit_time"):
        if not np.array_equal(existing[field].to_numpy(), paired[field].to_numpy()):
            raise ValueError(f"Raw {field} differs from complete deal history: {raw_path}")
    corrected = pd.Index([], dtype="int64")
    for field in ("trade_profit", "candle_range"):
        if not np.allclose(existing[field], paired[field], rtol=0, atol=TOL):
            off = ~np.isclose(existing[field], paired[field], rtol=0, atol=TOL)
            if field == "candle_range" and fix_risk:
                corrected = existing.index[off]
                continue
            raise ValueError(f"{int(off.sum())} raw {field} values differ from original orders/deals: {raw_path}")
    levels = report.candle_range / variant["grid_points"]
    if not np.isclose(levels, np.rint(levels), rtol=0, atol=1e-7).all():
        raise ValueError(f"Report-derived original risks do not lie on grid: {job['tag']}")
    missing = report.loc[~report.ticket.isin(raw.ticket)].copy()
    recovered = pd.DataFrame(np.nan, index=missing.index, columns=raw.columns)
    for field in ("ticket", "entry_time", "exit_time", "trade_profit", "candle_range"):
        recovered[field] = missing[field]
    raw_out = raw.copy()
    raw_out["ledger_source"] = "original"
    fix = raw_out.ticket.isin(corrected)
    raw_out.loc[fix, "candle_range"] = ref.loc[raw_out.loc[fix, "ticket"], "candle_range"].to_numpy()
    raw_out.loc[fix, "ledger_source"] = "original_risk_from_order"
    recovered["ledger_source"] = "tester_orders_deals"
    augmented = pd.concat([raw_out, recovered], ignore_index=True)
    augmented["ticket"] = augmented.ticket.astype("int64")
    augmented = augmented.sort_values(["entry_time", "ticket"], kind="stable").reset_index(drop=True)
    reconcile_totals(augmented, stats_path, job["tag"])
    logged = augmented.ledger_source.isin(["original", "original_risk_from_order"])
    preserved = augmented.loc[logged, raw.columns].set_index("ticket").reindex(existing.index)
    expected = existing.copy()
    expected.loc[corrected, "candle_range"] = ref.loc[corrected, "candle_range"]
    pd.testing.assert_frame_equal(expected, preserved, check_dtype=False, check_exact=True)
    augmented.to_csv(out_path, sep="\t", encoding="utf-16", index=False)
    loaded = load(out_path)
    exact_open = loaded.entry.dt.minute.isin([0, 30]) & (loaded.entry.dt.second == 0)
    recovery_periods = []
    if len(missing):
        years = pd.to_datetime(missing.entry_time, format="%Y.%m.%d %H:%M:%S").dt.year
        for label, lo, hi in (("2010-15", 2010, 2015), ("2016-19", 2016, 2019), ("2020-26", 2020, 2026)):
            part = missing.loc[(years >= lo) & (years <= hi)]
            recovery_periods.append({"period": label, "trades": len(part),
                                     "profit": float(part.trade_profit.sum()),
                                     "gross_R_sum": float((part.trade_profit / (part.candle_range * pv)).sum())})
    metadata = {"identity": identity, "input_sha256": inputs, "audited_sha256": digest(out_path),
                "all_passed": True, "raw_trades": len(raw), "audited_trades": len(augmented),
                "recovered_trades": len(missing), "recovered_profit": float(missing.trade_profit.sum()),
                "report_totals": report_totals, "raw_fields_preserved": True,
                "original_order_risk_matches_all_logged_rows": True,
                "control_order_and_fill_same_m30_bar": True if job["mode"] == "control" else None,
                "control_exact_m30_timestamp_fraction": float(exact_open.mean()) if job["mode"] == "control" else None,
                "recovered_unknown_fields": [c for c in raw.columns if c not in missing.columns],
                "recovery_periods": recovery_periods,
                "risk_corrected_trades": [{"ticket": int(k), "entry_time": existing.loc[k, "entry_time"],
                                           "logged_risk": float(existing.loc[k, "candle_range"]),
                                           "order_risk": float(ref.loc[k, "candle_range"])} for k in corrected],
                "notes": "Raw trade fields remain unchanged. Missing risk comes from original order requested price minus SL; profit/times come from deals. Missing excursions/signal labels remain NaN. Delayed first ticks need not equal the exact M30 boundary."}
    audit_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"AUDIT {job['tag']}: {len(raw):,} original + {len(missing)} recovered = {len(augmented):,}"
          f"{f', {len(corrected)} risks from orders' if len(corrected) else ''}; tester totals match.", flush=True)
    return out_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, nargs="?", default=ROOT / "Reports" / "granularity_20261009")
    args = parser.parse_args()
    manifest = json.loads((args.run / "manifest.json").read_text(encoding="utf-8"))
    variants = {v["key"]: v for v in manifest["variants"]}
    for job in manifest["jobs"]:
        if (args.run / f"{job['tag']}.completed.json").exists():
            ensure_audited(args.run, job, variants[job["variant"]], float(manifest.get("pv", 2.0)))


if __name__ == "__main__":
    main()

