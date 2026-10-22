"""Compare MT5 tester trades with the prop fills NinjaTrader 8 recorded for the same days.

Usage: compare_mt5_nt8.py <report.htm> [<report.htm> ...] [--accounts REGEX] [--tolerance 60]
                          [--server-offset 0] [--db PATH] [--out CSV]

MT5 side: the tester HTML report (Orders + Deals). AMP's MNQZ26 server clock is UTC (checked 2026-10-21:
tester fills land on the same second as the prop fills), so --server-offset defaults to 0.
NT8 side: executions read from a read-only snapshot of NinjaTrader.sqlite, which stores times in UTC.
Only executions inside the report's tested period are used.
Backtest the RTL/GG runband EAs on MNQZ26 with ServerClock = Auto (the default): on a broker symbol they move
their session windows and flatten to the UTC server clock themselves.

Each NT8 round trip is paired with the MT5 trade of the same direction whose entry is nearest in time,
within --tolerance seconds; several prop copies of one signal all pair with the same MT5 trade.
Signs: positive slippage = the prop fill was worse than the backtest. "same exit" = the exits are also
within the tolerance, i.e. both left the trade the same way; the others differ in path, not just in fill.
Writes <first report>_vs_nt8.csv (per pairing plus unmatched trades) and prints a summary.
"""
import argparse
import csv
import html
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

NT8_DB = Path.home() / "Documents" / "NinjaTrader 8" / "db" / "NinjaTrader.sqlite"
LOCAL = ZoneInfo("Europe/Tallinn")
UTC = ZoneInfo("UTC")
NET_EPOCH = datetime(1, 1, 1)
SKIP_ACCOUNTS = re.compile(r"^(Sim\d*|Playback\d*|Backtest)$")
TD = re.compile(r"<td[^>]*>(.*?)</td>")
TAG = re.compile(r"<[^>]+>")
TIME = re.compile(r"\d{4}\.\d\d\.\d\d \d\d:\d\d:\d\d$")
PERIOD = re.compile(r"\((\d{4}\.\d\d\.\d\d) - (\d{4}\.\d\d\.\d\d)\)")


def number(text):
    text = text.replace(" ", "").replace("\xa0", "")
    return float(text) if text else None


def server_time(text):
    return datetime.strptime(text, "%Y.%m.%d %H:%M:%S")


def to_utc(trades, offset):
    """Shift server-clock trades to UTC for a server offset in hours."""
    shift = timedelta(hours=offset)
    return [{**t, "entry_time": t["entry_time"] - shift, "exit_time": t["exit_time"] - shift} for t in trades]


def round_trips(fills):
    """FIFO unit lots: fills are (time, side, qty, price, extra) in time order -> closed trades."""
    trades, open_lots = [], []
    for time, side, qty, price, extra in fills:
        for _ in range(qty):
            if open_lots and open_lots[0]["side"] != side:
                lot = open_lots.pop(0)
                trades.append({**lot, "exit_time": time, "exit_price": price, "exit_info": extra})
            else:
                open_lots.append({"side": side, "entry_time": time, "entry_price": price, "entry_info": extra})
    return trades, open_lots


def read_report(path):
    """MT5 tester report -> (period start, period end, trades), all in the server clock."""
    text = Path(path).read_text(encoding="utf-16")
    period = PERIOD.search(text)
    if not period:
        raise ValueError(f"No tested period in {path}")
    start, end = (server_time(f"{x} 00:00:00") for x in period.groups())
    orders, fills, section = {}, [], None
    for line in text.splitlines():
        if ">Orders<" in line:
            section = "orders"
        elif ">Deals<" in line:
            section = "deals"
        cells = [html.unescape(TAG.sub("", x)).strip() for x in TD.findall(line)]
        if not cells or not TIME.match(cells[0]):
            continue
        if section == "orders" and len(cells) == 11:
            orders[cells[1]] = {"type": cells[3], "price": number(cells[5]), "sl": number(cells[6])}
        elif section == "deals" and len(cells) == 13 and cells[3] in ("buy", "sell"):
            time, _, symbol, side, _, volume, price, order = cells[:8]
            info = {"order": orders.get(order, {}), "comment": cells[12], "symbol": symbol}
            fills.append((server_time(time), side, int(number(volume)), number(price), info))
    trades, still_open = round_trips(fills)
    if still_open:
        print(f"Note: {len(still_open)} MT5 position(s) still open at the end of {Path(path).name}; ignored")
    for t in trades:
        order = t["entry_info"]["order"]
        t.update(source=Path(path).stem, symbol=t["entry_info"]["symbol"], planned=order.get("price"),
                 sl=order.get("sl"), exit_reason=t["exit_info"]["comment"] or "ea")
    return start, end, trades


def read_nt8(db, start, end, accounts, instrument):
    """Prop round trips per account from a snapshot of the NT8 database; times in UTC."""
    source = sqlite3.connect(Path(db).as_uri() + "?mode=ro", uri=True)
    con = sqlite3.connect(":memory:")
    source.backup(con)
    source.close()
    ticks = [int((x - NET_EPOCH).total_seconds()) * 10_000_000 for x in (start, end)]
    rows = con.execute("""
        select a.Name, e.Time, e.MarketPosition, e.Quantity, e.Price, m.PointValue, o.StopPrice, o.LimitPrice
        from Executions e
        join Accounts a on a.Id = e.Account
        join Instruments i on i.Id = e.Instrument
        join MasterInstruments m on m.Id = i.MasterInstrument
        left join Orders o on o.Id = (select max(Id) from Orders where OrderId = e.OrderId and Account = e.Account)
        where m.Name = ? and e.Time >= ? and e.Time < ?
        order by a.Name, e.Time, e.Id""", (instrument, *ticks)).fetchall()
    by_account = {}
    for name, time, position, qty, price, point_value, stop, limit in rows:
        if SKIP_ACCOUNTS.match(name) or (accounts and not re.search(accounts, name)):
            continue
        side = "buy" if position == 0 else "sell"
        planned = stop or limit or None
        by_account.setdefault(name, []).append(
            (NET_EPOCH + timedelta(microseconds=time // 10), side, qty, price, {"planned": planned, "pv": point_value}))
    trades = []
    for name, fills in by_account.items():
        closed, still_open = round_trips(fills)
        if still_open:
            print(f"Note: {len(still_open)} lot(s) still open in {name}; ignored")
        for t in closed:
            t.update(account=name, planned=t["entry_info"]["planned"], point_value=t["entry_info"]["pv"])
        trades += closed
    return trades


def nearest(trade, candidates, tolerance):
    best = None
    for c in candidates:
        gap = abs((c["entry_time"] - trade["entry_time"]).total_seconds())
        if c["side"] == trade["side"] and gap <= tolerance and (best is None or gap < best[0]):
            best = (gap, c)
    return best[1] if best else None


def local(t):
    return t.replace(tzinfo=UTC).astimezone(LOCAL).strftime("%Y-%m-%d %H:%M:%S") if t else ""


def compare(mt5, prop, tolerance):
    """One row per prop trade (paired or not) plus one per MT5 trade nobody traded."""
    rows, used = [], set()
    for p in prop:
        m = nearest(p, mt5, tolerance)
        sign = 1 if p["side"] == "buy" else -1
        row = {"time_local": local(p["entry_time"]), "status": "nt8_only", "source": "", "account": p["account"],
               "side": "long" if p["side"] == "buy" else "short",
               "nt8_entry": p["entry_price"], "nt8_planned": p["planned"], "nt8_exit": p["exit_price"],
               "nt8_exit_time": local(p["exit_time"]),
               "nt8_points": sign * (p["exit_price"] - p["entry_price"])}
        if m:
            used.add(id(m))
            risk = sign * (m["entry_price"] - m["sl"]) if m["sl"] else None
            mt5_points = sign * (m["exit_price"] - m["entry_price"])
            same_exit = abs((m["exit_time"] - p["exit_time"]).total_seconds()) <= tolerance
            row.update(status="same exit" if same_exit else "exit differs", source=m["source"],
                       mt5_entry=m["entry_price"], mt5_planned=m["planned"], mt5_sl=m["sl"],
                       mt5_exit=m["exit_price"], mt5_exit_time=local(m["exit_time"]), mt5_exit_reason=m["exit_reason"],
                       mt5_points=mt5_points,
                       entry_slip=sign * (p["entry_price"] - m["entry_price"]),
                       exit_slip=sign * (m["exit_price"] - p["exit_price"]),
                       worse_points=mt5_points - row["nt8_points"])
            row["worse_usd"] = row["worse_points"] * p["point_value"]
            row["worse_r"] = row["worse_points"] / risk if risk else None
        rows.append(row)
    for m in mt5:
        if id(m) not in used:
            sign = 1 if m["side"] == "buy" else -1
            rows.append({"time_local": local(m["entry_time"]), "status": "mt5_only", "source": m["source"],
                         "side": "long" if m["side"] == "buy" else "short", "mt5_entry": m["entry_price"],
                         "mt5_planned": m["planned"], "mt5_sl": m["sl"], "mt5_exit": m["exit_price"],
                         "mt5_exit_time": local(m["exit_time"]), "mt5_exit_reason": m["exit_reason"],
                         "mt5_points": sign * (m["exit_price"] - m["entry_price"])})
    return sorted(rows, key=lambda r: (r["time_local"], r["status"], r.get("account", "")))


def check_offset(mt5_by_offset, prop, tolerance, chosen):
    """Count prop trades that find a partner under each whole-hour server offset; warn if another fits better."""
    counts = {h: sum(nearest(p, trades, tolerance) is not None for p in prop) for h, trades in mt5_by_offset.items()}
    best = max(counts, key=counts.get)
    if counts[best] > counts[chosen]:
        print(f"WARNING: server offset {best:+d} h pairs {counts[best]} prop trades, the chosen {chosen:+d} h "
              f"only {counts[chosen]}. Check --server-offset.")


def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else float("nan")


def fmt(v, digits=2):
    return "" if v is None or v == "" else (f"{v:.{digits}f}" if isinstance(v, float) else str(v))


def run(reports, db=NT8_DB, accounts=None, instrument="MNQ", tolerance=60, server_offset=0, out=None):
    """Compare the reports with the NT8 fills, write the CSV, print the table and summary; return the rows."""
    loaded = [read_report(r) for r in reports]
    shift = timedelta(hours=server_offset)
    start, end = min(x[0] for x in loaded) - shift, max(x[1] for x in loaded) - shift
    server = sorted((t for x in loaded for t in x[2]), key=lambda t: t["entry_time"])
    mt5 = to_utc(server, server_offset)
    prop = read_nt8(db, start - timedelta(hours=12), end + timedelta(hours=12), accounts, instrument)
    prop = [p for p in prop if start <= p["entry_time"] < end]
    check_offset({h: to_utc(server, h) for h in range(-12, 13)}, prop, tolerance, server_offset)
    rows = compare(mt5, prop, tolerance)

    out = Path(out) if out else Path(reports[0]).with_name(Path(reports[0]).stem + "_vs_nt8.csv")
    fields = ["time_local", "status", "source", "account", "side", "mt5_planned", "mt5_entry", "nt8_planned",
              "nt8_entry", "entry_slip", "mt5_sl", "mt5_exit_time", "mt5_exit_reason", "mt5_exit", "nt8_exit_time",
              "nt8_exit", "exit_slip", "mt5_points", "nt8_points", "worse_points", "worse_usd", "worse_r"]
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows({k: fmt(v) for k, v in r.items()} for r in rows)

    print(f"Period (local): {local(start)} -> {local(end)}   MT5 trades {len(mt5)}   prop trades {len(prop)}")
    print(f"{'local time':19} {'status':12} {'account':18} {'mt5 in':>9} {'nt8 in':>9} {'slip':>5} "
          f"{'mt5 out':>9} {'nt8 out':>9} {'slip':>5} {'worse $':>8} {'worse R':>7}")
    for r in rows:
        print(f"{r['time_local']:19} {r['status']:12} {r.get('account', r['source'])[:18]:18} "
              f"{fmt(r.get('mt5_entry')):>9} {fmt(r.get('nt8_entry')):>9} {fmt(r.get('entry_slip')):>5} "
              f"{fmt(r.get('mt5_exit')):>9} {fmt(r.get('nt8_exit')):>9} {fmt(r.get('exit_slip')):>5} "
              f"{fmt(r.get('worse_usd')):>8} {fmt(r.get('worse_r'), 3):>7}")
    paired = [r for r in rows if r["status"] in ("same exit", "exit differs")]
    same = [r for r in paired if r["status"] == "same exit"]
    print(f"\nPaired prop trades: {len(paired)} ({len(same)} same exit); "
          f"prop only: {sum(r['status'] == 'nt8_only' for r in rows)}; "
          f"MT5 only: {sum(r['status'] == 'mt5_only' for r in rows)}")
    for label, group in (("same exit", same), ("all paired", paired)):
        if group:
            print(f"  {label:10}: entry slip {mean(r['entry_slip'] for r in group):+.2f} pt, "
                  f"exit slip {mean(r['exit_slip'] for r in group):+.2f} pt, "
                  f"worse {mean(r['worse_points'] for r in group):+.2f} pt = "
                  f"{mean(r['worse_usd'] for r in group):+.2f} $ = {mean(r['worse_r'] for r in group):+.3f} R per trade, "
                  f"total {sum(r['worse_usd'] for r in group):+.2f} $")
    print(f"Wrote {out}")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("reports", nargs="+", help="MT5 tester HTML report(s), e.g. one for RTL and one for GG")
    parser.add_argument("--accounts", help="regex on NT8 account names (default: every non-Sim account)")
    parser.add_argument("--instrument", default="MNQ")
    parser.add_argument("--tolerance", type=float, default=60, help="seconds between entries (and exits) to pair")
    parser.add_argument("--server-offset", type=int, default=0, help="MT5 server clock minus UTC, in hours")
    parser.add_argument("--db", default=NT8_DB)
    parser.add_argument("--out")
    args = parser.parse_args()
    run(args.reports, args.db, args.accounts, args.instrument, args.tolerance, args.server_offset, args.out)


if __name__ == "__main__":
    main()
