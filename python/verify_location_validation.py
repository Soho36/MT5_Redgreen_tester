"""Verify saved MT5 location-filter runs and summarize $1/trade net results.

Usage: python python/verify_location_validation.py Reports/location_validation_20260929
The directory contains the unique codex_location_20260929* CSV exports plus
features_reference.csv from the original feature run. No third-party packages.
"""

import csv
import json
import math
import sys
from pathlib import Path


PREFIX = "codex_location_20260929_"


def read_rows(path):
    encoding = "utf-16" if path.read_bytes()[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"
    with path.open(encoding=encoding, newline="") as source:
        reader = csv.reader(source, delimiter="\t")
        rows = list(reader)
    # Legacy EA exports can lack the header because FileSize includes the BOM.
    if rows[0][0].isdigit():
        header = ["ticket", "entry_time", "exit_time", "mae_money", "mfe_money",
                  "trade_profit", "candle_range"]
        if len(rows[0]) == 9:
            header += ["red_run", "location"]
        assert len(rows[0]) == len(header), "Unexpected headerless CSV schema"
    else:
        header, rows = rows[0], rows[1:]
    return [dict(zip(header, row, strict=True)) for row in rows if row]


def pf(values):
    gain = sum(v for v in values if v > 0)
    loss = -sum(v for v in values if v < 0)
    return gain / loss if loss else None


def balance_dd(values):
    balance = peak = drawdown = 0.0
    for value in values:
        balance += value
        peak = max(peak, balance)
        drawdown = max(drawdown, peak - balance)
    return drawdown


def main(directory):
    directory = Path(directory)
    cases = ["base", "off", "red2_loc0", "red2_loc10", "red2_loc15", "red2_loc20"]
    cases += [name for name in ("early_red2_loc0", "early_red2_loc15")
              if (directory / f"runband_{PREFIX}{name}_1.00.csv").exists()]
    trades = {}
    stats = {}
    for name in cases:
        stem = ("" if name == "base" else "runband_") + PREFIX + name + "_1.00"
        trades[name] = read_rows(directory / f"{stem}.csv")
        stats[name] = read_rows(directory / f"{stem}_stats.csv")[0]
        rows = trades[name]
        assert len(rows) == int(stats[name]["trades"]), (name, "missing trade rows")
        gross = sum(float(row["trade_profit"]) for row in rows)
        assert math.isclose(gross, float(stats[name]["net_profit"]), abs_tol=1e-6), (name, "MT5 PnL mismatch")
        if name != "base":
            threshold = float(stats[name]["min_location"])
            cap = int(stats[name]["max_red_run"])
            assert int(stats[name]["location_lookback"]) == 20
            for row in rows:
                loc = float(row["location"])
                assert 0 <= loc <= 1, (name, "invalid location")
                assert loc + 5e-11 >= threshold, (name, "location filter violated")
                assert cap == 0 or int(row["red_run"]) <= cap, (name, "red-run filter violated")

    original_columns = tuple(trades["base"][0])
    for baseline, disabled in zip(trades["base"], trades["off"], strict=True):
        assert all(baseline[key] == disabled[key] for key in original_columns), "Filters-off trade mismatch"
    print(f"PASS: filters off reproduce all {len(trades['base']):,} baseline trades and excursions exactly.")

    features = read_rows(directory / "features_reference.csv")
    by_entry = {row["entry_time"]: row for row in features}
    assert len(by_entry) == len(features), "Reference entry times are not unique"
    assert len(features) == len(trades["off"]), "Research baseline trade count differs"
    maximum_error = 0.0
    for row in trades["off"]:
        reference = by_entry[row["entry_time"]]
        assert row["exit_time"] == reference["exit_time"], "Research exit time mismatch"
        for key in ("trade_profit", "candle_range"):
            assert math.isclose(float(row[key]), float(reference[key]), abs_tol=1e-8), (key, "Research baseline mismatch")
        highs = [float(reference[f"h{i}"]) for i in range(1, 21)]
        lows = [float(reference[f"l{i}"]) for i in range(1, 21)]
        expected = (float(reference["c1"]) - min(lows)) / (max(highs) - min(lows))
        error = abs(float(row["location"]) - expected)
        maximum_error = max(maximum_error, error)
        assert error < 1e-9, (row["entry_time"], "Location formula mismatch", error)
    print(f"PASS: all location values match original 20-bar snapshots; max error {maximum_error:.3g}.")
    print("PASS: trade counts/PnL reconcile with MT5, and all filtered trades meet both inputs.")

    # A common chronological split for all recent cases matches analyze_features.py.
    recent_split = trades["base"][len(trades["base"]) // 2]["entry_time"]
    early = trades.get("early_red2_loc0", [])
    early_split = early[len(early) // 2]["entry_time"] if early else None
    summary = []
    for name in cases:
        rows = trades[name]
        split = early_split if name.startswith("early_") else recent_split
        net = [float(row["trade_profit"]) - 1.0 for row in rows]
        first = [v for row, v in zip(rows, net) if row["entry_time"] < split]
        second = [v for row, v in zip(rows, net) if row["entry_time"] >= split]
        dd = balance_dd(net)
        summary.append(dict(case=name, trades=len(rows), net=sum(net), pf=pf(net),
                            pf_first=pf(first), pf_second=pf(second), net_balance_dd=dd,
                            net_over_dd=sum(net) / dd if dd else None,
                            mt5_gross_equity_dd=float(stats[name]["equity_dd"]),
                            split=split, first_entry=rows[0]["entry_time"],
                            last_entry=rows[-1]["entry_time"]))
    (directory / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (directory / "summary.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    print("\nNet results subtract a modeled $1 round-turn from gross MT5 PnL.")
    print("DD below is closed-trade balance DD after that deduction, not equity DD.")
    print("case                   trades       net      PF   halves       DD   net/DD")
    for row in summary:
        print(f"{row['case']:22} {row['trades']:6,d} {row['net']:9,.1f} "
              f"{row['pf']:7.3f} {row['pf_first']:.3f}/{row['pf_second']:.3f} "
              f"{row['net_balance_dd']:8,.1f} {row['net_over_dd']:6.2f}")


if __name__ == "__main__":
    main(sys.argv[1])
