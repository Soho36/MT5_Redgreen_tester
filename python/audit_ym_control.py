"""Audit the 2026-10-23 control and RTL ledgers against their MT5 reports (audit_granularity_ledgers.ensure_audited).

Covers the market-buy controls and the red check run of Reports/ym_control_20261023 and the RTL buy-stop runs of
Reports/ym_baselines_20261023 (NQ, ES, YM). fix_risk on, as in audit_signal_colour_ledgers.py. Writes
<raw>_audited.csv and <tag>.ledger_audit.json next to each run; raw files stay unchanged.
Usage: python audit_ym_control.py
"""
import json

from audit_granularity_ledgers import ensure_audited
from project_paths import PROJECT_ROOT as ROOT

PV = {"MNQcontDTBNT20102026_2": 2.0, "MEScontDTBNT20102026_2": 5.0, "MYMcontDTBNT20102026": 0.5}
GRID = {"MNQcontDTBNT20102026_2": 0.25, "MEScontDTBNT20102026_2": 0.25, "MYMcontDTBNT20102026": 1.0}


def jobs():
    run = ROOT / "Reports" / "ym_control_20261023"
    for job in json.loads((run / "manifest.json").read_text(encoding="utf-8"))["jobs"]:
        yield run, job, "control" if job["mode"] == 3 else "rtl"
    run = ROOT / "Reports" / "ym_baselines_20261023"
    for job in json.loads((run / "manifest.json").read_text(encoding="utf-8"))["jobs"]:
        if job["strategy"] == "rtl":
            yield run, job, "rtl"


def main():
    print(f"{'tag':40s} {'mode':8s} {'raw':>7s} {'recovered':>9s} {'profit':>10s}")
    for run, job, mode in jobs():
        symbol = job["symbol"]
        ensure_audited(run, {**job, "mode": mode}, {"symbol": symbol, "grid_points": GRID[symbol]}, PV[symbol],
                       fix_risk=True)
        a = json.loads((run / f"{job['tag']}.ledger_audit.json").read_text(encoding="utf-8"))
        print(f"{job['tag']:40s} {mode:8s} {a['raw_trades']:>7,} {a['recovered_trades']:>9,} {a['recovered_profit']:>10,.2f}")


if __name__ == "__main__":
    main()
