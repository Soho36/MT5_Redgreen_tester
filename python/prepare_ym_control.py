"""Prepare the plain-long control on YM, NQ and ES (2026-10-23): how much of RTL is the buy stop, how much
the market's background? Follow-up to prepare_ym_baselines.py.

EA: the saved signal-colour EA (Reports/signal_colour_20261008/RTL_signal.mq5, identical to the installed one).
SignalMode 3 = market buy at every M30 bar open while flat, stop one previous-candle range below, same RR 1
bar-close exit, flatten and calendar as RTL. One check job: SignalMode 0 (red candle, no cap) on YM must
reproduce the RTL_runband YM ledger of Reports/ym_baselines_20261023. INI: the saved market-control INI with
symbol, dates, report and run tag changed (every input written).

Writes Reports/ym_control_20261023/. Run with
    python run_mt5_job.py Reports/ym_control_20261023 RTL_signal
Market-entry ledgers must be audited before use: python audit_ym_control.py
"""
import json
import shutil

from prepare_ym_baselines import FROM, SYMBOLS, TO
from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / "Reports" / "ym_control_20261023"
EXPERT = "RTL_signal"
SOURCE = ROOT / "Reports" / "signal_colour_20261008"
TEMPLATE = SOURCE / "signal_20261008_market_control.ini"
JOBS = [("control", inst, 3) for inst in SYMBOLS] + [("red_nocap", "ym", 0)]


def make_ini(tag, symbol, mode):
    out = []
    for line in TEMPLATE.read_text(encoding="utf-16").splitlines():
        key = line.split("=", 1)[0]
        line = {"Symbol": f"Symbol={symbol}", "FromDate": f"FromDate={FROM}", "ToDate": f"ToDate={TO}",
                "Report": f"Report={tag}.htm", "RunTag": f"RunTag={tag}", "SignalMode": f"SignalMode={mode}"
                }.get(key, line)
        out.append(line)
    text = "\n".join(out) + "\n"
    assert f"SignalMode={mode}\n" in text and "MaxRedRun=0\n" in text and f"Symbol={symbol}\n" in text
    return text


def main():
    if (STUDY / "manifest.json").exists():
        raise RuntimeError("Prepared manifest already exists; preserve it")
    STUDY.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE / f"{EXPERT}.mq5", STUDY / f"{EXPERT}.mq5")
    shutil.copyfile(SOURCE / "early_closes.mqh", STUDY / "early_closes.mqh")
    jobs = []
    for name, inst, mode in JOBS:
        tag = f"ymctrl_20261023_{name}_{inst}"
        (STUDY / f"{tag}.ini").write_text(make_ini(tag, SYMBOLS[inst], mode), encoding="utf-16")
        jobs.append({"tag": tag, "instrument": inst, "symbol": SYMBOLS[inst], "mode": mode, "max_run": 0,
                     "outputs": [f"runband_{tag}_1.00.csv", f"runband_{tag}_1.00_stats.csv"]})
    (STUDY / "manifest.json").write_text(json.dumps({"expert": EXPERT, "jobs": jobs}, indent=1), encoding="utf-8")
    print(f"Wrote {len(jobs)} jobs to {STUDY}")


if __name__ == "__main__":
    main()
