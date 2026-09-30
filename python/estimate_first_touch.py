"""Same-entry +1R first-touch diagnostic; not a full strategy backtest.

Run from the project root: python python/estimate_first_touch.py
Risk is signal range * $2/point for the saved one-lot MNQ runs.
"""

import argparse
import html
import json
import math
import re
from pathlib import Path

from project_paths import PROJECT_ROOT
from verify_location_validation import pf, read_rows


def report_entries(path):
    entries = {}
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", path.read_text(encoding="utf-16"), re.S | re.I):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", cell)).strip()
                 for cell in re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.S | re.I)]
        if len(cells) == 13 and cells[3:5] == ["buy", "in"]:
            assert cells[7] not in entries, "Multiple entry deals require different accounting"
            assert float(cells[5]) == 1, "Expected one-lot entries"
            entries[cells[7]] = float(cells[6].replace(" ", ""))
    return entries


def metrics(profits, risks, commission):
    n = len(profits)
    return dict(trades=n, gross_pf=pf(profits),
                gross_avg_r=sum(p / r for p, r in zip(profits, risks)) / n,
                net_avg_r=sum((p - commission) / r for p, r in zip(profits, risks)) / n,
                net_dollars=sum(profits) - commission * n)


def analyze(reference, snapshots, name, phase, commission):
    rows = read_rows(reference / f"runband_{name}_1.00.csv")
    snapshot_phase = {"2015-2019": "train", "2020-2026": "recent"}[phase]
    snaps = read_rows(snapshots / f"runband_bars_20260930_{snapshot_phase}_1.00.csv")
    entries = report_entries(reference / f"{name}.htm")
    assert len(rows) == len(snaps) == len(entries)
    profits, risks, touched = [], [], []
    for row, snap in zip(rows, snaps, strict=True):
        assert row["ticket"] == snap["ticket"]
        assert row["entry_time"] == snap["entry_time"]
        assert row["trade_profit"] == snap["trade_profit"] or math.isclose(
            float(row["trade_profit"]), float(snap["trade_profit"]), abs_tol=1e-8)
        high, low = float(snap["h1"]), float(snap["l1"])
        assert math.isclose(entries[row["ticket"]], high, abs_tol=1e-8), "Fill differs from signal high"
        risk = float(row["candle_range"]) * 2
        assert risk > 0 and math.isclose(risk, (high - low) * 2, abs_tol=1e-8)
        profit, mfe = float(row["trade_profit"]), float(row["mfe_money"])
        assert math.isfinite(profit) and math.isfinite(mfe)
        assert mfe + 1e-8 >= profit, "MFE must include final realized profit"
        profits.append(profit)
        risks.append(risk)
        touched.append(mfe >= risk - 1e-8)
    alternate = [r if t else p for p, r, t in zip(profits, risks, touched)]
    above = [p / r - 1 for p, r, t in zip(profits, risks, touched) if t and p > r + 1e-8]
    count = sum(touched)
    delta = [a - p for a, p in zip(alternate, profits)]
    return dict(phase=phase, fills_match_signal_high=len(entries),
                current=metrics(profits, risks, commission),
                first_touch=metrics(alternate, risks, commission),
                touched=count, touched_share=count / len(rows),
                losing_share_of_touched=sum(t and p < 0 for p, t in zip(profits, touched)) / count,
                above_one_r_share_of_touched=len(above) / count,
                mean_overshoot_r_of_above_one_r=sum(above) / len(above),
                improved_outcomes_dollars=sum(d for d in delta if d > 0),
                sacrificed_outcomes_dollars=-sum(d for d in delta if d < 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=PROJECT_ROOT / "Reports/maxredrun_train_20260929")
    parser.add_argument("--snapshots", type=Path, default=PROJECT_ROOT / "Reports/preceding_candles_20260930")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "Reports/exit_estimate_20260930")
    parser.add_argument("--commission", type=float, default=1.0)
    args = parser.parse_args()
    if not math.isfinite(args.commission) or args.commission < 0:
        parser.error("Commission must be finite and nonnegative")
    results = [analyze(args.reference, args.snapshots, name, phase, args.commission)
               for name, phase in (("train1519_run3", "2015-2019"), ("test2026_run3", "2020-2026"))]
    payload = dict(method="Same entries, replace PnL with +1R when recorded MFE reaches +1R; unchanged otherwise",
                   commission_per_trade=args.commission, dollars_per_point=2,
                   limitations=["Recorded MT5 simulated path, not tick-market verification",
                                "No new entries after earlier exits", "No alternative fill/slippage model",
                                "MFE ends at original exit; cannot estimate longer holds"], results=results)
    args.output.mkdir(parents=True, exist_ok=True)
    output = args.output / "first_touch.json"
    output.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(f"Saved {output}")


if __name__ == "__main__":
    main()
