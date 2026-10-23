"""Prepare the YM experiments on Russell 2000 futures (RTY, priced as M2K) (2026-10-23).

Same EAs, sources and INI templates as the YM study, only symbol, dates, report and run tag change:
  four baselines (prepare_ym_baselines.STRATEGIES): RTL, GG, RTL-short, GG-short, M30
  plain-long control: RTL_signal SignalMode 3, plus SignalMode 0 as a check (must reproduce RTL_runband)
  RTL on H1: RTL_timeframe (tick-level 23:30 cutoff)
Symbol M2KcontDTBNT20172026 ($5/pt, $0.50 per 0.1 tick; imported by import_custom_symbol.py). CME RTY starts
2017-07-10, so the tester runs 2017-07-10 -> 2026-10-23. NQ, ES and YM ledgers are reused from the YM study.

Writes Reports/rty_baselines_20261023/. Run per EA (tags in manifest.json):
    python run_mt5_job.py Reports/rty_baselines_20261023 <EA> <tags...>
"""
import json
import shutil

import prepare_ym_baselines as base
import prepare_ym_control as ctrl
import prepare_ym_h1 as h1
from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / "Reports" / "rty_baselines_20261023"
SYMBOL = "M2KcontDTBNT20172026"
FROM = "2017.07.10"


def main():
    if (STUDY / "manifest.json").exists():
        raise RuntimeError("Prepared manifest already exists; preserve it")
    STUDY.mkdir(parents=True, exist_ok=True)
    base.FROM = ctrl.FROM = h1.FROM = FROM   # make_ini reads the module-level dates
    shutil.copyfile(ROOT / "mt5" / "experts" / "early_closes.mqh", STUDY / "early_closes.mqh")
    jobs = []

    def add(tag, expert, kind, ini, source):
        assert f"Symbol={SYMBOL}\n" in ini and f"FromDate={FROM}\n" in ini
        assert "MaxRedRun=0\n" in ini or "MaxGreenRun=0\n" in ini
        shutil.copyfile(source, STUDY / f"{expert}.mq5")
        (STUDY / f"{tag}.ini").write_text(ini, encoding="utf-16")
        jobs.append({"tag": tag, "kind": kind, "expert": expert, "symbol": SYMBOL,
                     "outputs": [f"runband_{tag}_1.00.csv", f"runband_{tag}_1.00_stats.csv"]})

    for key, (expert, source, template) in base.STRATEGIES.items():
        tag = f"rtybase_20261023_{key}"
        add(tag, expert, key, base.make_ini(template, tag, SYMBOL), source)
    ctrl_src = ctrl.SOURCE / f"{ctrl.EXPERT}.mq5"
    for kind, mode in (("control", 3), ("red_nocap", 0)):
        tag = f"rtybase_20261023_{kind}"
        add(tag, ctrl.EXPERT, kind, ctrl.make_ini(tag, SYMBOL, mode), ctrl_src)
    tag = "rtybase_20261023_rtl_h1"
    add(tag, h1.EXPERT, "rtl_h1", base.make_ini(h1.TEMPLATE, tag, SYMBOL), h1.SOURCE / f"{h1.EXPERT}.mq5")
    (STUDY / "manifest.json").write_text(json.dumps({"symbol": SYMBOL, "jobs": jobs}, indent=1), encoding="utf-8")
    print(f"Wrote {len(jobs)} jobs to {STUDY}")


if __name__ == "__main__":
    main()
