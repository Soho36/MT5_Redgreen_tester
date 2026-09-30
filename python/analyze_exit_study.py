"""Audit and summarize the frozen full-MT5 exit comparison."""

import argparse
import csv
from collections import Counter
from datetime import datetime, timedelta
import hashlib
import html
import json
import re

import numpy as np

from project_paths import PROJECT_ROOT
from verify_location_validation import balance_dd, pf, read_rows


def dt(value):
    return datetime.strptime(value, "%Y.%m.%d %H:%M:%S")


def number(value):
    return float(value.replace(" ", ""))


def deals(path):
    result = []
    order_comments = {}
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", path.read_text(encoding="utf-16"), re.S | re.I):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", cell)).strip()
                 for cell in re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.S | re.I)]
        if len(cells) == 13 and cells[4] in ("in", "out"):
            result.append(cells)
        elif len(cells) == 11 and cells[9] == "filled":
            order_comments[cells[1]] = cells[10].lower()
    return result, order_comments


def metrics(rows, commission=1):
    gross = [float(r["trade_profit"]) for r in rows]
    risk = [float(r["candle_range"]) * 2 for r in rows]
    net = [p - commission for p in gross]
    duration = [(dt(r["exit_time"]) - dt(r["entry_time"])).total_seconds() / 60 for r in rows]
    dd = balance_dd(net)
    return dict(trades=len(rows), gross=sum(gross), net=sum(net), gross_pf=pf(gross), net_pf=pf(net),
                net_balance_dd=dd, net_over_dd=sum(net) / dd,
                gross_avg_r=float(np.mean(np.array(gross) / risk)),
                net_avg_r=float(np.mean(np.array(net) / risk)), total_net_r=float(sum(np.array(net) / risk)),
                mean_hold_minutes=float(np.mean(duration)), median_hold_minutes=float(np.median(duration)),
                max_hold_minutes=max(duration),
                cross_date_trades=sum(r["entry_time"][:10] != r["exit_time"][:10] for r in rows))


def identity(row):
    return row["entry_time"], row["h1"], row["l1"]


def audit(directory, job, rows):
    stats = read_rows(directory / job["csv"].replace(".csv", "_stats.csv"))[0]
    assert len(rows) == int(stats["trades"]), (job["tag"], "Missing trade exports")
    assert abs(sum(float(r["trade_profit"]) for r in rows) - float(stats["net_profit"])) < 1e-6
    assert float(stats["risk_reward"]) == job["rr"]
    assert int(stats["max_red_run"]) == 3 and float(stats["min_location"]) == 0
    assert int(stats["snapshot_bars"]) == 1
    actual, order_comments = deals(directory / job["report"])
    assert len(actual) == 2 * len(rows)
    reasons = Counter()
    for i, row in enumerate(rows):
        entry, close = actual[2 * i:2 * i + 2]
        assert entry[3:5] == ["buy", "in"] and close[3:5] == ["sell", "out"]
        assert entry[7] == row["ticket"] and entry[0] == row["entry_time"] and close[0] == row["exit_time"]
        assert number(entry[5]) == number(close[5]) == 1
        high, low, risk = float(row["h1"]), float(row["l1"]), float(row["candle_range"])
        assert risk > 0 and abs(high - low - risk) < 1e-8
        assert abs(number(entry[6]) - high) < 1e-8, "Fill risk differs from signal range"
        assert abs(number(close[10]) - float(row["trade_profit"])) < 1e-8
        assert abs((number(close[6]) - high) * 2 - float(row["trade_profit"])) < 1e-8
        assert dt(row["entry_time"]) >= dt(row["signal_time"]) + timedelta(minutes=30)
        assert dt(row["exit_time"]) >= dt(row["entry_time"])
        if i:
            assert dt(row["entry_time"]) >= dt(rows[i-1]["exit_time"]), "Overlapping positions"
        comment = order_comments.get(close[7], "")
        reason = "tp" if comment.startswith("tp ") else "sl" if comment.startswith("sl ") else "market_or_end"
        reasons[reason] += 1
        if reason == "tp":
            assert job["mode"] == "tp"
            assert abs(float(row["trade_profit"]) / (risk * 2) - job["rr"]) < 1e-8
    tester = (directory / (job["tag"] + ".tester.log")).read_text(encoding="utf-8-sig")
    log = (directory / (job["tag"] + ".agent.log")).read_text(encoding="utf-8-sig")
    assert "automatic testing finished" in tester and "Test passed" in tester
    assert reasons["tp"] == len(re.findall(r"take profit triggered #", log))
    assert reasons["sl"] == len(re.findall(r"stop loss triggered #", log))
    assert abs(balance_dd([float(r["trade_profit"]) for r in rows]) - float(stats["balance_dd"])) < 1e-6
    error_lines = [line for line in log.splitlines() if re.search(r"failed|invalid|not enough|error", line, re.I)]
    # Existing gap/session-open invalid pending prices are retained and counted.
    unexplained = [line for line in error_lines if not ("[Invalid price]" in line or "retcode=10015" in line)]
    assert not unexplained, unexplained[:5]
    baseline_match = None
    if job["mode"] == "close" and job["rr"] == 1:
        name = "train1519_run3" if job["phase"] == "train" else "test2026_run3"
        old = read_rows(PROJECT_ROOT / f"Reports/maxredrun_train_20260929/runband_{name}_1.00.csv")
        assert len(old) == len(rows)
        for new, previous in zip(rows, old, strict=True):
            for key, value in previous.items():
                assert new[key] == value or (key not in ("entry_time", "exit_time") and abs(float(new[key]) - float(value)) < 1e-8)
        baseline_match = len(old)
    return dict(gross_mt5_equity_dd=float(stats["equity_dd"]), gross_mt5_balance_dd=float(stats["balance_dd"]),
                exit_reasons=dict(reasons), baseline_matched_trades=baseline_match,
                invalid_pending_prices=sum("[Invalid price]" in line for line in error_lines),
                unexplained_error_lines=len(unexplained))


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot(directory, results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(12, 7), constrained_layout=True)
    for i, (phase, title) in enumerate((("train", "2015-2019"), ("recent", "2020-2026"))):
        close = sorted([r for r in results if r["phase"] == phase and r["mode"] == "close"], key=lambda r: r["rr"])
        tp = next(r for r in results if r["phase"] == phase and r["mode"] == "tp")
        for j, (metric, label) in enumerate((("net", "Net dollars"), ("net_balance_dd", "Net closed-balance DD ($)"), ("net_avg_r", "Average net R"))):
            ax = axes[i, j]
            ax.plot([r["rr"] for r in close], [r[metric] for r in close], marker="o", color="#176b87", label="Bar-close threshold")
            ax.scatter([1], [tp[metric]], marker="x", s=80, color="#b84a37", label="Fixed TP 1R", zorder=3)
            ax.set_title(f"{title}: {label}")
            ax.set_xlabel("RR threshold")
            ax.set_xticks([.75, 1, 1.25, 1.5, 2])
            ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Full MT5 exit comparison: cap 3, one contract, $1 per completed trade")
    fig.savefig(directory / "threshold_curve.png", dpi=170)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plot", action="store_true", help="Also draw the curve; requires optional matplotlib")
    args = parser.parse_args()
    directory = PROJECT_ROOT / "Reports/exit_thresholds_20260930"
    manifest = json.loads((directory / "manifest.json").read_text())
    assert hashlib.sha256((PROJECT_ROOT / "docs/EXIT_THRESHOLD_PROTOCOL.md").read_bytes()).hexdigest() == manifest["protocol_sha256"]
    populations, results, audits, yearly = {}, [], {}, []
    for job in manifest["jobs"]:
        assert (directory / (job["tag"] + ".completed.json")).exists(), job["tag"]
        rows = read_rows(directory / job["csv"])
        audits[job["tag"]] = audit(directory, job, rows)
        populations[job["tag"]] = rows
        meta = {key: job[key] for key in ("tag", "phase", "mode", "rr")}
        results.append(dict(**meta, **metrics(rows)))
        for year in sorted({r["exit_time"][:4] for r in rows}):
            yearly.append(dict(**meta, year=int(year), **metrics([r for r in rows if r["exit_time"].startswith(year)])))
        print(f"Verified {job['tag']}: {len(rows):,} trades", flush=True)
    for result in results:
        baseline = next(r for r in results if r["phase"] == result["phase"] and r["mode"] == "close" and r["rr"] == 1)
        keys = {identity(r) for r in populations[result["tag"]]}
        original = {identity(r) for r in populations[baseline["tag"]]}
        result.update(common_entries=len(keys & original), added_entries=len(keys - original), omitted_entries=len(original - keys))
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir()
              if p.suffix in (".mq5", ".ex5", ".ini", ".csv", ".htm", ".log") and p.name not in ("summary.csv", "yearly.csv")}
    payload = dict(results=results, yearly=yearly, audits=audits, evidence_sha256=hashes)
    (directory / "analysis.json").write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    write_csv(directory / "summary.csv", results)
    write_csv(directory / "yearly.csv", yearly)
    lines = ["# Full MT5 exit comparison", "", "All figures use one contract and modeled $1 round-trip commission.", ""]
    for phase in ("train", "recent"):
        lines += [f"## {phase}", "", "| Mode | RR | Trades | Net $ | Net PF | Net balance DD | Net/DD | Net avg R | Mean hold min | Cross-date |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for r in sorted([r for r in results if r["phase"] == phase], key=lambda r: (r["mode"], r["rr"])):
            lines.append(f"| {r['mode']} | {r['rr']:.2f} | {r['trades']:,} | {r['net']:,.0f} | {r['net_pf']:.3f} | {r['net_balance_dd']:,.0f} | {r['net_over_dd']:.2f} | {r['net_avg_r']:+.4f} | {r['mean_hold_minutes']:.1f} | {r['cross_date_trades']} |")
        lines += [""]
    (directory / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    if args.plot:
        plot(directory, results)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
