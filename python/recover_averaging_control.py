"""Recover missing averaging-OFF CSV rows from a complete MT5 HTML report.

Strictly limited to one-contract controls with alternating buy-in/sell-out deals.
Retains the original CSV as *_unreconciled.csv, checks every surviving row against
the report, and leaves unobserved MAE/MFE and signal features blank. No fabricated
excursions or features. Requires the full report to reconcile to MT5 statistics.
"""
import argparse
import csv
import json
import shutil
from html.parser import HTMLParser
from pathlib import Path

from analyze_averaging_study import close, validate
from verify_location_validation import read_rows


class ReportRows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell = [], [], None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        if tag in ("td", "th"):
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append("".join(self.cell).strip())
            self.cell = None
        if tag == "tr" and self.row:
            self.rows.append(self.row)


def number(value):
    return float(value.replace(" ", "").replace("\xa0", ""))


def recover(study, tag):
    manifest = json.loads((study / "manifest.json").read_text(encoding="utf-8"))
    job = next(j for j in manifest["jobs"] if j["tag"] == tag)
    assert job["distance"] == 0, "Only controls can use this recovery"
    path = study / job["csv"]
    original = path.with_name(path.stem + "_unreconciled.csv")
    existing = read_rows(original if original.exists() else path)
    by_ticket = {r["ticket"]: r for r in existing}
    assert len(by_ticket) == len(existing), "Duplicate CSV tickets"
    stats = read_rows(path.with_name(path.stem + "_stats.csv"))[0]
    assert stats["run_tag"] == tag and close(stats["average_near_stop_r"], 0)
    raw = (study / job["report"]).read_bytes()
    parser = ReportRows()
    parser.feed(raw.decode("utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"))
    orders_i = parser.rows.index(["Orders"])
    deals_i = parser.rows.index(["Deals"])
    order_header = parser.rows[orders_i + 1]
    orders = {r[1]: dict(zip(order_header, r)) for r in parser.rows[orders_i + 2:deals_i] if len(r) == len(order_header)}
    header = parser.rows[deals_i + 1]
    deals = [dict(zip(header, r)) for r in parser.rows[deals_i + 2:] if len(r) == len(header) and r[3] in ("buy", "sell")]
    assert len(deals) == 2 * int(stats["trades"]), "Incomplete report or unexpected trade structure"
    result, recovered = [], []
    for entry, exit in zip(deals[::2], deals[1::2]):
        assert (entry["Type"], entry["Direction"], exit["Type"], exit["Direction"]) == ("buy", "in", "sell", "out")
        assert number(entry["Volume"]) == number(exit["Volume"]) == 1
        assert number(entry["Commission"]) == number(exit["Commission"]) == number(entry["Swap"]) == number(exit["Swap"]) == 0
        assert number(entry["Profit"]) == 0
        ticket = entry["Order"]
        order = orders[ticket]
        assert order["Type"] == "buy stop" and order["State"] == "filled"
        price, stop, out = number(entry["Price"]), number(order["S / L"]), number(exit["Price"])
        profit = number(exit["Profit"])
        assert price > stop and close(2 * (out - price), profit), "Unexpected MNQ point value"
        facts = dict(ticket=ticket, entry_time=entry["Time"], exit_time=exit["Time"],
                     base_exit_time=exit["Time"], base_entry=price, initial_stop=stop,
                     initial_risk_money=2 * (price - stop), exit_price=out, add_exit_price=out,
                     trade_profit=profit, base_profit=profit,
                     candle_range=number(order["Price"]) - stop)
        if ticket in by_ticket:
            row = dict(by_ticket[ticket])
            for key, value in facts.items():
                assert row[key] == str(value) or close(row[key], value), (ticket, key, row[key], value)
            row["export_recovered"] = "0"
        else:
            row = {key: "" for key in existing[0]}
            row.update({key: str(value) for key, value in facts.items()})
            row.update(base_volume="1", add_volume="0", exit_volume="1", add_entry="0",
                       planned_add_risk="0", add_profit="0", broker_costs="0", add_time="",
                       add_limit="0", add_status="0", entry_deals="1", exit_deals="1",
                       orphan_volume="0", export_recovered="1")
            # MAE/MFE, red_run, location and exit_reason remain unknown/blank.
            recovered.append(ticket)
        result.append(row)
    assert set(by_ticket).issubset({r["ticket"] for r in result})
    validate(result, stats, job)
    if not original.exists():
        shutil.copyfile(path, original)
    with path.open("w", encoding="utf-16", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=list(result[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(result)
    evidence = dict(tag=tag, original_rows=len(existing), final_rows=len(result),
                    recovered_tickets=recovered, report=job["report"], original_csv=original.name,
                    gross=sum(float(r["trade_profit"]) for r in result),
                    checks="All existing rows match report facts; full report and recovered CSV reconcile to MT5 trades and PnL; no cross-date baskets.")
    (study / (tag + ".export-recovery.json")).write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("study", type=Path)
    ap.add_argument("tag")
    args = ap.parse_args()
    recover(args.study, args.tag)
