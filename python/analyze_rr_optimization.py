"""Reconcile the user's 0.5-5.0 MT5 XML optimization with its native trade exports.

Read-only toward MT5; preserve matched evidence and analysis in Reports.
"""

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

from project_paths import PROJECT_ROOT
from verify_location_validation import read_rows, balance_dd, pf


def summarize(rows):
    gross = [float(r["trade_profit"]) for r in rows]
    risk = [2 * float(r["candle_range"]) for r in rows]
    assert all(r > 0 for r in risk)
    net = [g - 1 for g in gross]
    return dict(trades=len(rows), gross=sum(gross), net=sum(net), net_pf=pf(net),
                net_balance_dd=balance_dd(net), net_avg_r=sum(p / r for p, r in zip(net, risk)) / len(net),
                total_net_r=sum(p / r for p, r in zip(net, risk)),
                cross_date_trades=sum(r["entry_time"][:10] != r["exit_time"][:10] for r in rows),
                cross_date_net=sum(p for p, r in zip(net, rows) if r["entry_time"][:10] != r["exit_time"][:10]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corrected", action="store_true", help="Analyze the repeated cap-3 run")
    args = parser.parse_args()
    directory = PROJECT_ROOT / ("Reports/rr_cap3_corrected_20260930" if args.corrected else "Reports/rr_optimization_20260930")
    xml = directory / "rr_cap3_corrected_20260930.xml" if args.corrected else PROJECT_ROOT / "mt5/optimizations/rr-05-5-0.1.xml"
    ns = {"s": "urn:schemas-microsoft-com:office:spreadsheet"}
    root = ET.parse(xml).getroot()
    raw = [[d.text for d in row.findall("s:Cell/s:Data", ns)] for row in root.findall(".//s:Table/s:Row", ns)]
    grid = [dict(zip(raw[0], map(float, row), strict=True)) for row in raw[1:]]
    grid.sort(key=lambda r: r["RiskReward"])
    assert len(grid) == 46
    assert [round(r["RiskReward"] * 10) for r in grid] == list(range(5, 51))
    directory.mkdir(parents=True, exist_ok=True)
    evidence = directory / "native"
    evidence.mkdir(exist_ok=True)
    common = Path(os.environ["APPDATA"]) / "MetaQuotes/Terminal/Common/Files"
    profile = Path(os.environ["APPDATA"]) / "MetaQuotes/Terminal/F5855995045EF8A4C3CA7AE968872CF2/MQL5/Profiles/Tester"
    if not args.corrected:
        # Preserve the original mistaken-run settings, even after a corrected run changes the profile.
        for name in ("RTL_runband_location.set", "RTL_runband_location.MNQcontDATABENTOcurr6.M30.20200102_20260714.110.ini"):
            if not (evidence / name).exists():
                shutil.copyfile(profile / name, evidence / name)
    results, yearly, provenance = [], [], []
    for row in grid:
        rr = row["RiskReward"]
        candidates = list(directory.glob(f"runband_rr_cap3_corrected_20260930_{rr:.2f}_stats.csv")) if args.corrected else list(common.glob(f"runband_1-2+*_{rr:.2f}_stats.csv"))
        assert len(candidates) == 1, (rr, candidates)
        stat_path = candidates[0]
        stats_rows = read_rows(stat_path)
        assert len(stats_rows) == 1
        stats = stats_rows[0]
        assert int(stats["min_red_run"]) == (1 if args.corrected else 3)
        assert int(stats["max_red_run"]) == (3 if args.corrected else 0)
        assert float(stats["min_location"]) == 0 and int(stats["location_lookback"]) == 20
        assert math.isclose(float(stats["risk_reward"]), rr, rel_tol=0, abs_tol=1e-9)
        assert int(stats["trades"]) == int(row["Trades"])
        assert abs(float(stats["net_profit"]) - row["Profit"]) < 1e-6
        assert abs(row["Result"] - (500000 + row["Profit"])) < 1e-6
        for export, key in (("profit_factor", "Profit Factor"), ("recovery_factor", "Recovery Factor"), ("expected_payoff", "Expected Payoff")):
            assert abs(float(stats[export]) - row[key]) < 0.000001
        trades_path = stat_path.with_name(stat_path.name.replace("_stats.csv", ".csv"))
        trades = read_rows(trades_path)
        assert len(trades) == int(row["Trades"])
        assert all(1 <= int(t["red_run"]) <= 3 if args.corrected else int(t["red_run"]) >= 3 for t in trades)
        assert all("2020.01.02" <= t["entry_time"][:10] < "2026.07.14" for t in trades)
        assert len({t["ticket"] for t in trades}) == len(trades)
        assert [t["exit_time"] for t in trades] == sorted(t["exit_time"] for t in trades)
        assert abs(sum(float(t["trade_profit"]) for t in trades) - row["Profit"]) < 1e-6
        assert abs(balance_dd([float(t["trade_profit"]) for t in trades]) - float(stats["balance_dd"])) < 1e-6
        assert abs(pf([float(t["trade_profit"]) for t in trades]) - row["Profit Factor"]) < 0.000001
        if args.corrected and rr == 1:
            baseline = read_rows(PROJECT_ROOT / "Reports/maxredrun_train_20260929/runband_test2026_run3_1.00.csv")
            assert len(trades) == len(baseline)
            for actual, expected in zip(trades, baseline, strict=True):
                for key, value in expected.items():
                    assert actual[key] == value or (key not in ("entry_time", "exit_time") and abs(float(actual[key])-float(value)) < 1e-8), (key, actual[key], value)
        result = dict(rr=rr, **summarize(trades), gross_pf=row["Profit Factor"],
                      gross_equity_dd=float(stats["equity_dd"]), gross_recovery=row["Recovery Factor"],
                      equity_dd_pct=row["Equity DD %"])
        result["net_over_balance_dd"] = result["net"] / result["net_balance_dd"]
        results.append(result)
        for year in sorted({t["exit_time"][:4] for t in trades}):
            yearly.append(dict(rr=rr, year=int(year), **summarize([t for t in trades if t["exit_time"].startswith(year)])))
        for kind, source in (("stats", stat_path), ("trades", trades_path)):
            dest = evidence / f"rr_{rr:.2f}_{kind}.csv"
            shutil.copyfile(source, dest)
            provenance.append(dict(source=str(source), saved_as=str(dest.relative_to(directory)),
                                   sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
    # Pareto comparison: no alternative has >= net profit and <= net closed DD, with one strict.
    frontier = [r["rr"] for r in results if not any(
        other["net"] >= r["net"] and other["net_balance_dd"] <= r["net_balance_dd"]
        and (other["net"] > r["net"] or other["net_balance_dd"] < r["net_balance_dd"])
        for other in results)]
    payload = dict(xml_sha256=hashlib.sha256(xml.read_bytes()).hexdigest(),
                   settings=dict(min_red_run=1 if args.corrected else 3, max_red_run=3 if args.corrected else 0,
                                 min_location=0, modeled_round_trip_commission=1),
                   results=results, yearly=yearly, net_profit_closed_dd_frontier=frontier, provenance=provenance)
    (directory / "analysis.json").write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    for name, values in (("summary", results), ("yearly", yearly)):
        with (directory / f"{name}.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(values[0]))
            writer.writeheader()
            writer.writerows(values)
    print(f"Reconciled {len(results)} passes / {sum(r['trades'] for r in results):,} trade rows")
    for r in results:
        if r["rr"] in (1, 1.5, 2, 2.5, 2.6, 2.7, 3, 3.1, 3.2, 4.6, 5):
            print(json.dumps(r))
    print("Net-profit / closed-DD frontier:", frontier)
    for key in ("net", "net_avg_r", "net_over_balance_dd", "gross_recovery"):
        best = max(results, key=lambda r: r[key])
        print("Highest", key, "RR", best["rr"], best[key])


if __name__ == "__main__":
    main()
