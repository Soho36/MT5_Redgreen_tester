"""Apply the granularity study's ledger audit to the 2026-10-08 runs (exploratory follow-up, 2026-10-09).

The research EA can omit a position that opens and stops before its next OnTick (found in
docs/baseline/granularity/RESULTS.md). This reuses audit_granularity_ledgers.ensure_audited on the
signal-colour (MNQ, MES, coarse NQ) and instrument-baseline runs. SignalMode 3 = market-buy control;
every other mode and the baseline EA enter with a buy stop ("rtl" in the audit's checks). fix_risk is on: a row
logged with the wrong risk (fallback flatten + new market entry in one OnTick) takes its original order's risk.
Writes <raw>_audited.csv and <tag>.ledger_audit.json next to each run; raw files stay unchanged.

Usage: python audit_signal_colour_ledgers.py
"""

import json

from audit_granularity_ledgers import ensure_audited
from project_paths import PROJECT_ROOT as ROOT

RUNS = ("signal_colour_20261008", "signal_colour_20261008_mes", "signal_colour_20261008_nqcoarse",
        "instrument_baseline_20261008")
PV = {"MNQcontDTBNT20102026_2": 2.0, "MEScontDTBNT20102026": 5.0, "MNQcoarseDTBNT20102026": 2.0}
GRID = 0.25   # every price (also the coarse grids) lies on the native 0.25 tick


def main():
    rows = []
    for folder in RUNS:
        run = ROOT / "Reports" / folder
        manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        for job in manifest["jobs"]:
            symbol = job.get("symbol") or manifest["symbol"]
            mode = "control" if job.get("mode") == 3 else "rtl"
            ensure_audited(run, {**job, "mode": mode}, {"symbol": symbol, "grid_points": GRID}, PV[symbol],
                           fix_risk=True)
            audit = json.loads((run / f"{job['tag']}.ledger_audit.json").read_text(encoding="utf-8"))
            rows.append((job["tag"], mode, audit["raw_trades"], audit["recovered_trades"], audit["recovered_profit"]))
    print(f"\n{'tag':45s} {'mode':8s} {'raw':>7s} {'recovered':>9s} {'profit':>10s}")
    for tag, mode, raw, rec, profit in rows:
        print(f"{tag:45s} {mode:8s} {raw:>7,} {rec:>9,} {profit:>10,.2f}")


if __name__ == "__main__":
    main()
