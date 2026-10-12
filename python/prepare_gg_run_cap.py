"""Prepare the GG run-cap train/test on MNQ (2026-10-13). The cap (MaxRedRun 3) was chosen and tested for RTL
only; the signal-colour study then applied it to GG without a test.

Protocol, fixed before running (the RTL rule from docs/baseline/maxredrun/RESULTS.md, applied to green):
  EA: RTL_signal with SignalMode 1 (GG; the run filter counts consecutive green bars), nothing else changed.
  Runs: MaxRedRun in {0 (off), 1, ..., 7}, full period 2010-06-07 -> 2026-07-14, periods sliced by entry year.
  1. Train, 2016-19: winner = highest gross PF. A tie within 0.005 goes to the larger cap (off = largest).
  2. Test, 2020-26: the winner, frozen, against off. It passes if net PF is higher and net DD lower than off.
  Caveat: GG 2020-26 was already seen for cap 3 and off on 2026-10-08, so only another winner is a new test.
  Check: the cap 3 and off runs must reproduce the 2026-10-08 green ledgers exactly.

Writes Reports/gg_run_cap_20261013/. Run with
    .\\venv\\Scripts\\python.exe python\\run_mt5_job.py Reports\\gg_run_cap_20261013 RTL_signal
"""

import json
import shutil

from prepare_instrument_baseline import make_ini
from prepare_signal_colour import EXPERT, SYMBOLS, build_source
from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / "Reports" / "gg_run_cap_20261013"
CAPS = (0, 1, 2, 3, 4, 5, 6, 7)


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    (STUDY / f"{EXPERT}.mq5").write_text(build_source(), encoding="utf-8")
    shutil.copyfile(ROOT / "mt5" / "experts" / "early_closes.mqh", STUDY / "early_closes.mqh")
    jobs = []
    for cap in CAPS:
        tag = f"ggcap_20261013_cap{cap}"
        ini = make_ini(tag, SYMBOLS["mnq"]).replace("Expert=CodexTrendlineResearch\\RTL_runband.ex5",
                                                    f"Expert=CodexTrendlineResearch\\{EXPERT}.ex5")
        assert "MaxRedRun=3\n" in ini and f"\\{EXPERT}.ex5" in ini
        ini = ini.replace("MaxRedRun=3\n", f"MaxRedRun={cap}\nSignalMode=1\n")
        (STUDY / f"{tag}.ini").write_text(ini, encoding="utf-16")
        jobs.append({"tag": tag, "mode": 1, "max_run": cap,
                     "outputs": [f"runband_{tag}_1.00.csv", f"runband_{tag}_1.00_stats.csv"]})
    (STUDY / "manifest.json").write_text(json.dumps({"expert": EXPERT, "symbol": SYMBOLS["mnq"], "jobs": jobs}, indent=1),
                                         encoding="utf-8")
    print(f"Wrote {len(jobs)} jobs to {STUDY}")


if __name__ == "__main__":
    main()
