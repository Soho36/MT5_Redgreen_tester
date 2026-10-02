"""Audit standalone-limit fills against MT5 reports and summarize OHLC screening."""
import json
import math
import sys
from pathlib import Path

from analyze_averaging_study import close, summary, validate
from prepare_limit_only_study import STUDY
from project_paths import PROJECT_ROOT
from recover_averaging_control import ReportRows, number
from verify_location_validation import read_rows


def audit_report(path, rows, limit_only):
    raw = path.read_bytes()
    parser = ReportRows()
    parser.feed(raw.decode("utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"))
    orders_i, deals_i = parser.rows.index(["Orders"]), parser.rows.index(["Deals"])
    header = parser.rows[orders_i+1]
    orders = {r[1]: dict(zip(header, r)) for r in parser.rows[orders_i+2:deals_i] if len(r) == len(header)}
    expected = "buy limit" if limit_only else "buy stop"
    buys = [o for o in orders.values() if o["Type"].startswith("buy")]
    assert buys and all(o["Type"] == expected for o in buys), "unexpected entry order type"
    header = parser.rows[deals_i+1]
    deals = [dict(zip(header, r)) for r in parser.rows[deals_i+2:] if len(r) == len(header) and r[3] in ("buy", "sell")]
    assert len(deals) == 2*len(rows), "CSV/report deal count mismatch"
    for row, entry, exit in zip(rows, deals[::2], deals[1::2]):
        assert (entry["Type"], entry["Direction"], exit["Type"], exit["Direction"]) == ("buy", "in", "sell", "out")
        assert number(entry["Volume"]) == number(exit["Volume"]) == 1
        assert row["ticket"] == entry["Order"]
        assert row["entry_time"] == entry["Time"] and row["exit_time"] == exit["Time"]
        assert close(row["trade_profit"], number(exit["Profit"]))
        assert close(row["base_entry"], number(entry["Price"]))
        order = orders[entry["Order"]]
        assert close(row["initial_stop"], number(order["S / L"]))
        if limit_only:
            assert close(row["limit_order_price"], number(order["Price"]))
    return len(buys)


def main(study):
    manifest = json.loads((study/"manifest.json").read_text(encoding="utf-8"))
    assert manifest["model"] == 1
    results = {}
    for job in manifest["jobs"]:
        assert (study/f"{job['tag']}.completed.json").exists(), job["tag"]
        rows = read_rows(study/job["csv"])
        stats = read_rows(study/job["csv"].replace(".csv", "_stats.csv"))[0]
        validate(rows, stats, dict(job, distance=0))
        assert stats["run_tag"] == job["tag"]
        limit_only = job["offset"] is not None
        assert int(stats["limit_only"]) == int(limit_only)
        assert int(stats["wait_for_high"]) == int(manifest["wait_for_high"])
        for key in ("limits_rejected", "limit_cancel_errors"):
            assert int(stats[key]) == 0, (job["tag"], key)
        if limit_only:
            assert close(stats["limit_offset_percent"], job["offset"])
            assert len(rows) <= int(stats["limits_placed"]) <= int(stats["limit_setups"])
            for row in rows:
                high, low = float(row["signal_high"]), float(row["signal_low"])
                price = float(row["limit_order_price"])
                expected = max(low+.25, math.ceil((high-(high-low)*job["offset"]/100)/.25-1e-8)*.25)
                assert close(price, expected) and low < price < high
                assert float(row["base_entry"]) <= price, "limit filled above order price"
                assert close(row["initial_stop"], low)
                assert close(row["target_price"], 2*high-low), "target moved to limit entry"
                assert row["signal_time"] < row["entry_time"]
                if manifest["wait_for_high"]:
                    assert row["signal_time"] < row["breakout_time"] <= row["entry_time"]
        else:
            old = read_rows(PROJECT_ROOT/"Reports/rr_clean_20261001"/f"runband_rrclean_20261001_{job['period']}_1p00_1.00.csv")
            assert len(old) == len(rows)
            for a, b in zip(old, rows):
                for key in ("entry_time", "exit_time", "trade_profit", "mae_money", "mfe_money", "candle_range", "red_run", "location"):
                    assert a[key] == b[key] or close(a[key], b[key]), (job["tag"], key)
        order_count = audit_report(study/job["report"], rows, limit_only)
        if limit_only:
            assert order_count == int(stats["limits_placed"])
        primary = summary(rows)
        primary["win_rate"] = sum(float(r["trade_profit"]) > 1.05 for r in rows)/len(rows)
        primary["avg_candle_r"] = sum((float(r["trade_profit"])-1.05)/(2*float(r["candle_range"])) for r in rows)/len(rows)
        result = dict(job, primary=primary, extra_dollar_slippage=summary(rows, 2.05),
                      mt5_gross_equity_dd=float(stats["equity_dd"]),
                      orders=order_count, skips=int(stats["limits_skipped"]),
                      same_minute_exit=sum(r["entry_time"][:16] == r["exit_time"][:16] for r in rows),
                      years={year: summary([r for r in rows if r["entry_time"][:4] == year])
                             for year in sorted({r["entry_time"][:4] for r in rows})})
        results[f"{job['period']}_{job['offset']}"] = result
        print(f"{job['period']:6} {str(job['offset']):>7} {len(rows):6} trades  net {primary['net']:11.2f}  PF {primary['pf']:.3f}  DD {primary['dd']:.2f}  net/DD {primary['net_dd']:.2f}  win {primary['win_rate']:.1%}")
    payload = dict(model=1, commission=1.05, wait_for_high=manifest["wait_for_high"], results=results)
    (study/"results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("PASS: all CSVs reconcile to MT5 statistics AND complete order/deal reports; controls reproduce baseline; limit variants contain only buy-limit entries.")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv)>1 else STUDY)
