r"""Weekly check: backtest last week's RTL and GG on AMP's live MNQ contract, then compare with the prop fills.

Usage: weekly_mt5_nt8.py [--week YYYY-MM-DD] [--source PATH] [--accounts REGEX] [--symbol MNQZ26]
                         [--rtl-set FILE.set] [--gg-set FILE.set]

1. Copies NinjaTrader.sqlite from the trading PC's shared folder (--source, default \\DESKTOP-L6S1KEN\db)
   into the week's run folder as a plain file copy, then checks it with PRAGMA quick_check.
   Best at the weekend with NinjaTrader closed there; a copy taken mid-write fails the check.
2. Runs the RTL and GG runband EAs in the MT5 tester on the front MNQ contract for that week (real ticks,
   ServerClock = Auto, so the session windows and flatten follow the UTC server clock).
   Every EA input is written into the INI: the tester reuses the last value for any input an INI omits.
   Defaults are the research baseline (M30, RR 1, no run cap, all windows but 00:00-01:00 and 23:30-00:00).
   Pass an MT5 .set file saved from the tester's Inputs tab to use the live settings instead.
3. Runs compare_mt5_nt8 on both reports, writes the per-trade CSV, and updates Reports/weekly_fills/summary.csv
   with one line per strategy and week.

--week is any date in the week to check (Monday-Friday sessions); default: the last full week.
Re-running a week reuses its finished backtests and only repeats the copy and the comparison.
Close the AMP terminal first: an open terminal makes tester runs silently do nothing.
"""
import argparse
import csv
import json
import re
import shutil
import sqlite3
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path

import run_mt5_job
from compare_mt5_nt8 import mean, run as compare
from mt5_expert_layout import tester_expert_path
from project_paths import PROJECT_ROOT

# The trading PC's NT8 database as seen from this PC (shared folder); override with --source.
SHARED_DB = Path(r"\\DESKTOP-L6S1KEN\db\NinjaTrader.sqlite")
WEEKLY = PROJECT_ROOT / "Reports" / "weekly_fills"
EXPERTS = {"rtl": ("RTL_runband", "RR_r_MFE_buy-stop-entry_runband.cs"),
           "gg": ("GG_runband", "GG_r_MFE_buy-stop-entry_runband.cs")}
INPUT = re.compile(r"^input\s+\w+\s+(\w+)\s*=\s*([^;]+);", re.MULTILINE)
TESTER = {"Period": "M30", "Optimization": "0", "Model": "4", "ForwardMode": "0", "Deposit": "500000",
          "Currency": "USD", "ProfitInPips": "0", "Leverage": "100", "ExecutionMode": "0",
          "OptimizationCriterion": "0", "Visual": "0", "UseLocal": "1", "UseRemote": "0", "UseCloud": "0",
          "ShutdownTerminal": "1", "ReplaceReport": "1"}
BASELINE = {"Slippage": "0", "MaxCandleRange": "8000", "MinCandleRange": "1", "ServerClock": "0",
            "W0000W0100": "false", "W2330W0000": "false"}   # all other windows on; see window_inputs()
MONTHS = ((3, "H"), (6, "M"), (9, "U"), (12, "Z"))


def last_full_week(today):
    monday = today - timedelta(days=today.weekday())
    return monday - timedelta(days=7) if today.weekday() < 5 else monday


def front_month(day):
    """MNQ contract traded on `day`: CME equity index futures roll 8 days before the third-Friday expiry."""
    for year in (day.year, day.year + 1):
        for month, code in MONTHS:
            first = date(year, month, 1)
            expiry = first + timedelta(days=(4 - first.weekday()) % 7 + 14)
            if day < expiry - timedelta(days=8):
                return f"MNQ{code}{year % 100}", expiry - timedelta(days=8)
    raise ValueError(day)


def ea_inputs(source):
    """Every input of the EA with its source default, in declaration order."""
    values = {}
    for name, value in INPUT.findall(source):
        value = value.strip()
        values[name] = value[1:-1] if value.startswith('"') else value
    return values


def read_set(path):
    """MT5 .set file -> {input: value} (value before the first '||')."""
    raw = Path(path).read_bytes()
    text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig")
    return {k.strip(): v.split("||")[0].strip() for k, _, v in
            (line.partition("=") for line in text.splitlines() if "=" in line and not line.startswith(";"))}


def make_ini(tag, expert, inputs, symbol, start, end):
    tester = {"Expert": tester_expert_path(expert), "Symbol": symbol, **TESTER, "FromDate": start.strftime("%Y.%m.%d"),
              "ToDate": end.strftime("%Y.%m.%d"), "Report": f"{tag}.htm"}
    lines = ["[Tester]", *(f"{k}={v}" for k, v in tester.items()), "[TesterInputs]",
             *(f"{k}={v}" for k, v in inputs.items())]
    return "\n".join(lines) + "\n"


def prepare(run, monday, symbol, sets):
    """Write the EAs, INIs and manifest for the week; return the jobs."""
    # Sunday 22:00 UTC is the first session of the week; the tester stops at the start of ToDate (Saturday).
    start, end = monday - timedelta(days=1), monday + timedelta(days=5)
    shutil.copyfile(PROJECT_ROOT / "mt5/experts/early_closes.mqh", run / "early_closes.mqh")
    jobs = []
    for strategy, (expert, source) in EXPERTS.items():
        text = (PROJECT_ROOT / "mt5/experts" / source).read_text(encoding="utf-8")
        (run / f"{expert}.mq5").write_text(text, encoding="utf-8")
        inputs = ea_inputs(text)
        inputs.update({k: "true" for k in inputs if re.fullmatch(r"W\d{4}W\d{4}", k)})
        tag = f"weekly_{monday:%Y%m%d}_{strategy}"
        inputs.update(BASELINE, RunTag=tag)
        live = read_set(sets[strategy]) if sets.get(strategy) else {}
        unknown = set(live) - set(inputs)
        if unknown:
            raise ValueError(f"{sets[strategy]} has inputs the {expert} EA does not know: {sorted(unknown)}")
        inputs.update({k: v for k, v in live.items() if k != "RunTag"})
        enums = [k for k, v in inputs.items() if re.fullmatch(r"[A-Z_]+", v)]
        if enums:
            raise ValueError(f"Inputs without a numeric value: {enums}")
        (run / f"{tag}.ini").write_text(make_ini(tag, expert, inputs, symbol, start, end), encoding="utf-16")
        rr = f"{float(inputs['RiskReward']):.2f}"
        jobs.append({"tag": tag, "strategy": strategy, "expert": expert,
                     "outputs": [f"runband_{tag}_{rr}.csv", f"runband_{tag}_{rr}_stats.csv"]})
    (run / "manifest.json").write_text(json.dumps({"symbol": symbol, "jobs": jobs}, indent=1), encoding="utf-8")
    return jobs


def copy_db(source, target, week_end):
    """Plain file copy of the NT8 database (no SQLite locks on the trading PC), checked here; warn when it
    holds no fills from the week's last days."""
    if not Path(source).exists():
        raise FileNotFoundError(f"NT8 database not found at {source}; check the shared folder or pass --source")
    shutil.copyfile(source, target)
    dst = sqlite3.connect(target)
    if dst.execute("pragma quick_check").fetchone()[0] != "ok":
        raise RuntimeError(f"Copied database fails quick_check (NT8 was writing?); copy again with NT8 closed")
    last = dst.execute("select max(Time) from Executions").fetchone()[0]
    dst.close()
    newest = datetime(1, 1, 1) + timedelta(microseconds=last // 10) if last else None
    print(f"NT8 database copied; newest fill (UTC): {newest}")
    if newest is None or newest.date() < week_end - timedelta(days=1):
        print("WARNING: the copy has no fills from the end of the week; was NT8 connected, and is the copy fresh?")


def early_close_note(monday):
    text = (PROJECT_ROOT / "mt5/experts/early_closes.mqh").read_text(encoding="utf-8")
    last = max(int(x) for x in re.findall(r"\b(20\d{6})\b", text))
    if int(f"{monday:%Y%m%d}") > last:
        print(f"Note: the early-close calendar ends {last}. If this week had a holiday or early close, the "
              f"backtest still flattens at 23:30 session time there; treat those trades with care.")


def update_summary(week, symbol, rows):
    path = WEEKLY / "summary.csv"
    fields = ["week", "symbol", "strategy", "paired", "same_exit", "entry_slip_pt", "exit_slip_pt",
              "worse_usd_per_trade", "worse_r_per_trade", "exit_differs_usd", "prop_only", "mt5_only"]
    old = []
    if path.exists():
        with path.open(encoding="utf-8") as f:
            old = [r for r in csv.DictReader(f) if r["week"] != week]
    new = []
    for strategy in EXPERTS:
        mine = [r for r in rows if r["source"].endswith(f"_{strategy}")]
        same = [r for r in mine if r["status"] == "same exit"]
        differs = [r for r in mine if r["status"] == "exit differs"]
        new.append({"week": week, "symbol": symbol, "strategy": strategy,
                    "paired": len(same) + len(differs), "same_exit": len(same),
                    "entry_slip_pt": f"{mean(r['entry_slip'] for r in same):.2f}",
                    "exit_slip_pt": f"{mean(r['exit_slip'] for r in same):.2f}",
                    "worse_usd_per_trade": f"{mean(r['worse_usd'] for r in same):.2f}",
                    "worse_r_per_trade": f"{mean(r['worse_r'] for r in same):.3f}",
                    "exit_differs_usd": f"{sum(r['worse_usd'] for r in differs):.2f}",
                    "mt5_only": sum(r["status"] == "mt5_only" for r in mine)})
    prop_only = sum(r["status"] == "nt8_only" for r in rows)
    for r in new:
        r["prop_only"] = prop_only   # unpaired prop trades cannot be told apart by strategy
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fields)
        writer.writeheader()
        writer.writerows(sorted(old + new, key=lambda r: (r["week"], r["strategy"])))
    print(f"Updated {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--week", type=date.fromisoformat, help="any date in the week (default: last full week)")
    parser.add_argument("--source", default=SHARED_DB, help="NT8 database on the trading PC (shared folder)")
    parser.add_argument("--accounts", help="regex on NT8 account names (default: every non-Sim account)")
    parser.add_argument("--symbol", help="MT5 symbol (default: the front MNQ contract for the week)")
    parser.add_argument("--rtl-set", help="MT5 .set file with the live RTL inputs")
    parser.add_argument("--gg-set", help="MT5 .set file with the live GG inputs")
    args = parser.parse_args()

    day = args.week or last_full_week(date.today())
    monday = day - timedelta(days=day.weekday())
    if monday + timedelta(days=5) > date.today():
        raise SystemExit(f"The week of {monday} has not finished yet")
    symbol, roll = front_month(monday)
    symbol = args.symbol or symbol
    if monday <= roll < monday + timedelta(days=5) and not args.symbol:
        print(f"Note: contracts roll on {roll}; this week uses {symbol}, the prop fills may be on the next contract")
    if "terminal64.exe" in subprocess.run(["tasklist"], capture_output=True, text=True).stdout:
        raise SystemExit("Close the MT5 terminal first: an open terminal makes tester runs silently do nothing")

    run = WEEKLY / f"{monday:%Y-%m-%d}"
    run.mkdir(parents=True, exist_ok=True)
    print(f"Week {monday} - {monday + timedelta(days=4)}, symbol {symbol}, folder {run}")
    early_close_note(monday)
    copy_db(args.source, run / "NinjaTrader.sqlite", monday + timedelta(days=5))

    jobs = prepare(run, monday, symbol, {"rtl": args.rtl_set, "gg": args.gg_set})
    for job in jobs:
        if (run / f"{job['tag']}.completed.json").exists():
            print(f"{job['tag']}: backtest already done, reused")
        else:
            run_mt5_job.main(run, job["expert"], job["tag"])

    rows = compare([run / f"{j['tag']}.htm" for j in jobs], db=run / "NinjaTrader.sqlite", accounts=args.accounts,
                   out=run / f"weekly_{monday:%Y%m%d}_vs_nt8.csv")
    update_summary(f"{monday:%Y-%m-%d}", symbol, rows)


if __name__ == "__main__":
    main()
