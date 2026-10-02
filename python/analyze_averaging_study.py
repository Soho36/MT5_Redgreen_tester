"""Reconcile the frozen near-stop averaging study and evaluate its protocol."""
import json
import math
import sys
from pathlib import Path

from prepare_averaging_study import STUDY
from project_paths import PROJECT_ROOT
from verify_location_validation import read_rows, pf, balance_dd


def close(a, b):
    return math.isclose(float(a), float(b), abs_tol=1e-6)


def summary(rows, commission=1.05):
    net, normalized, r_values, planned_r = [], [], [], []
    add_net = []
    fills = 0
    for row in rows:
        volume = float(row["base_volume"]) + float(row["add_volume"])
        pnl = float(row["trade_profit"]) - commission * volume
        risk = float(row["initial_risk_money"])
        budget = risk + float(row["planned_add_risk"])
        net.append(pnl)
        normalized.append(pnl * risk / budget)
        r_values.append(pnl / risk)
        planned_r.append(pnl / budget)
        if float(row["add_volume"]) > 0:
            fills += 1
            add_net.append(float(row["add_profit"]) - commission * float(row["add_volume"]))
    drawdown = balance_dd(net)
    return dict(baskets=len(rows), fills=fills, net=sum(net), pf=pf(net), dd=drawdown,
                net_dd=sum(net)/drawdown if drawdown else None,
                avg_initial_r=sum(r_values)/len(rows), avg_planned_r=sum(planned_r)/len(rows),
                equal_risk_net=sum(normalized), equal_risk_dd=balance_dd(normalized),
                add_net=sum(add_net), add_winners=sum(x>0 for x in add_net),
                add_pf=pf(add_net), add_avg=sum(add_net)/fills if fills else None)


def validate(rows, stats, job):
    assert sum(int(r["exit_deals"]) for r in rows) == int(stats["trades"]), (job["tag"], "MT5 trade count")
    assert close(sum(float(r["trade_profit"]) for r in rows), stats["net_profit"]), "MT5 PnL"
    assert close(stats["average_near_stop_r"], job["distance"])
    assert int(stats["average_target"]) == 0
    for key in ("adds_rejected", "cancel_errors", "orphan_close_errors"):
        assert int(stats[key]) == 0, (job["tag"], key)
    assert int(stats["adds_placed"]) == sum(int(r["add_status"]) == 1 for r in rows)
    assert int(stats["adds_skipped"]) == sum(int(r["add_status"]) == 2 for r in rows)
    for r in rows:
        assert r["entry_time"][:10] == r["exit_time"][:10], "cross-date basket"
        assert close(float(r["base_volume"]) + float(r["add_volume"]), r["exit_volume"]), "unbalanced volume"
        assert close(r["base_volume"], 1) and float(r["add_volume"]) in (0.0, 1.0), "more than one equal-sized add"
        assert float(r["initial_risk_money"]) > 0
        assert close(r["broker_costs"], 0), "update costs model to avoid double charging"
        assert close(float(r["base_profit"]) + float(r["add_profit"]), r["trade_profit"]), "leg attribution"
        if float(r["add_volume"]) > 0:
            assert r["entry_time"] <= r["add_time"] <= r["exit_time"], "fill ordering"
            assert float(r["add_entry"]) <= float(r["add_limit"]) + 1e-8, "limit execution"
            assert float(r["initial_stop"]) < float(r["add_limit"]) < float(r["base_entry"]), "limit placement"
            assert int(r["add_status"]) == 1
        elif job["distance"] == 0:
            assert int(r["add_status"]) == 0


def main(study):
    manifest = json.loads((study / "manifest.json").read_text(encoding="utf-8"))
    assert not manifest["average_target"], "analysis protocol assumes fixed original target"
    results, controls = {}, {}
    for job in manifest["jobs"]:
        assert (study / f"{job['tag']}.completed.json").exists()
        rows = read_rows(study / job["csv"])
        stats = read_rows(study / job["csv"].replace(".csv", "_stats.csv"))[0]
        validate(rows, stats, job)
        if job["distance"] == 0:
            if manifest.get("model", 1) == 1:
                old = read_rows(PROJECT_ROOT / "Reports/rr_clean_20261001" /
                                f"runband_rrclean_20261001_{job['period']}_1p00_1.00.csv")
                assert len(old) == len(rows), "control differs from baseline"
                for a, b in zip(old, rows):
                    for key in ("entry_time", "exit_time", "trade_profit", "mae_money", "mfe_money", "candle_range", "red_run", "location"):
                        assert a[key] == b[key] or close(a[key], b[key]), (key, a, b)
            controls[job["period"]] = rows
        else:
            control = controls[job["period"]]
            assert len(control) == len(rows), "averaging changed basket count"
            for a, b in zip(control, rows):
                assert a["entry_time"] == b["entry_time"] and a["base_exit_time"] == b["base_exit_time"], "schedule changed"
                assert close(a["trade_profit"], b["base_profit"]), "original leg changed"
        result = dict(job, primary=summary(rows), cost_1=summary(rows, 1.0),
                      extra_dollar_slippage=summary(rows, 2.05),
                      mt5_gross_equity_dd=float(stats["equity_dd"]),
                      skips=int(stats["adds_skipped"]))
        result["stop_before_add_fills"] = sum(float(r["orphan_volume"])>0 for r in rows)
        result["years"] = {year: summary([r for r in rows if r["entry_time"][:4] == year])
                           for year in sorted({r["entry_time"][:4] for r in rows})}
        result["same_minute_add_exit"] = sum(r["add_time"] and r["add_time"][:16] == r["exit_time"][:16] for r in rows if r["add_time"])
        results[f"{job['period']}_{job['distance']:.2f}"] = result
    distances = sorted({j["distance"] for j in manifest["jobs"] if j["distance"] > 0})
    passed = all(results[f"{p}_{d:.2f}"]["primary"][metric] > results[f"{p}_0.00"]["primary"][metric]
                 for p in ("train", "recent") for d in distances for metric in ("pf", "net_dd"))
    passed &= all(results[f"{p}_0.10"]["primary"]["equal_risk_net"] > results[f"{p}_0.00"]["primary"]["net"]
                  for p in ("train", "recent"))
    payload = dict(screen_passed=passed, commission=1.05, model=manifest.get("model", 1), results=results)
    (study / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("PASS: all runs reconcile, original legs and schedules match their controls, no cross-date baskets.")
    if manifest.get("model", 1) == 1:
        print("OHLC controls also reproduce the historical clean-data baseline field by field.")
    print(f"{'period':<8}{'add R':>7}{'baskets':>9}{'fills':>7}{'net $':>11}{'PF':>8}{'DD $':>10}{'net/DD':>9}{'avg R':>9}{'eqRisk $':>11}{'add net $':>11}")
    for result in results.values():
        s = result["primary"]
        print(f"{result['period']:<8}{result['distance']:>7.2f}{s['baskets']:>9}{s['fills']:>7}{s['net']:>11.2f}{s['pf']:>8.3f}{s['dd']:>10.2f}{s['net_dd']:>9.2f}{s['avg_initial_r']:>9.4f}{s['equal_risk_net']:>11.2f}{s['add_net']:>11.2f}")
    print("Predefined screen" if len(distances)==3 else "Focused sensitivity screen", ":",
          "PASS; candidate for further research" if passed else "FAIL; retain baseline")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv)>1 else STUDY)
