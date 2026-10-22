"""Prepare the four baselines on YM (Dow, priced as MYM) next to NQ and ES, same settings (2026-10-23).

Baselines, all M30, RR 1, bar-close exit, no run cap, flatten 23:30 with fallback, early-close calendar:
  rtl        RTL_runband            red candle, buy stop at its high, stop at its low
  gg         GG_runband             green candle, buy stop at its high, stop at its low
  rtl_short  GG_outside_short       green candle, sell stop at its low, stop at its high (RTL mirror;
                                    UseOutsideFilter=false = the green-candle short control of 2026-10-20)
  gg_short   GG_red_outside_short   red candle, sell stop at its low, stop at its high (GG mirror;
                                    UseOutsideFilter=false = the red-candle short control of 2026-10-21)
Long EAs: current repo sources (identical to the installed ones). Short EAs: the saved study sources
(identical to the installed ones). INIs: the 2026-10-21 server-clock research INIs (long) and the short
studies' control INIs, with symbol, dates, report and run tag changed. Every input is written.

Symbols: NQ MNQcontDTBNT20102026_2 ($2/pt), ES MEScontDTBNT20102026_2 ($5/pt; re-imported 2026-10-23, the old symbol has lost its history), YM MYMcontDTBNT20102026
($0.50/pt, imported 2026-10-23 by import_custom_symbol.py). Tester 2010-06-07 -> 2026-10-23 (data ends
NQ 2026-10-01, ES 2026-10-07, YM 2026-10-22). Writes Reports/ym_baselines_20261023/. Run per EA:
    python run_mt5_job.py Reports/ym_baselines_20261023 <EA> <tags...>
"""
import json
import shutil

from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / "Reports" / "ym_baselines_20261023"
SYMBOLS = {"nq": "MNQcontDTBNT20102026_2", "es": "MEScontDTBNT20102026_2", "ym": "MYMcontDTBNT20102026"}
FROM, TO = "2010.06.07", "2026.10.23"
STRATEGIES = {
    "rtl": ("RTL_runband", ROOT / "mt5" / "experts" / "RR_r_MFE_buy-stop-entry_runband.cs",
            ROOT / "Reports" / "server_clock_20261021" / "clock_20261021_rtl_research.ini"),
    "gg": ("GG_runband", ROOT / "mt5" / "experts" / "GG_r_MFE_buy-stop-entry_runband.cs",
           ROOT / "Reports" / "server_clock_20261021" / "clock_20261021_gg_research.ini"),
    "rtl_short": ("GG_outside_short", ROOT / "Reports" / "gg_outside_short_20261020" / "GG_outside_short.mq5",
                  ROOT / "Reports" / "gg_outside_short_20261020" / "ggshort_20261020_control.ini"),
    "gg_short": ("GG_red_outside_short",
                 ROOT / "Reports" / "gg_red_outside_short_20261021" / "GG_red_outside_short.mq5",
                 ROOT / "Reports" / "gg_red_outside_short_20261021" / "ggredshort_20261021_control.ini"),
}


def make_ini(template, tag, symbol):
    out, seen = [], set()
    for line in template.read_text(encoding="utf-16").splitlines():
        key = line.split("=", 1)[0]
        if key == "Symbol":
            line = f"Symbol={symbol}"
        elif key == "FromDate":
            line = f"FromDate={FROM}"
        elif key == "ToDate":
            line = f"ToDate={TO}"
        elif key == "Report":
            line = f"Report={tag}.htm"
        elif key == "RunTag":
            line = f"RunTag={tag}"
        seen.add(key)
        out.append(line)
    assert {"Symbol", "FromDate", "ToDate", "Report", "RunTag"} <= seen
    return "\n".join(out) + "\n"


def main():
    if (STUDY / "manifest.json").exists():
        raise RuntimeError("Prepared manifest already exists; preserve it")
    STUDY.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "mt5" / "experts" / "early_closes.mqh", STUDY / "early_closes.mqh")
    jobs = []
    for key, (expert, source, template) in STRATEGIES.items():
        shutil.copyfile(source, STUDY / f"{expert}.mq5")
        for inst, symbol in SYMBOLS.items():
            tag = f"ymbase_20261023_{key}_{inst}"
            (STUDY / f"{tag}.ini").write_text(make_ini(template, tag, symbol), encoding="utf-16")
            jobs.append({"tag": tag, "strategy": key, "instrument": inst, "symbol": symbol, "expert": expert,
                         "outputs": [f"runband_{tag}_1.00.csv", f"runband_{tag}_1.00_stats.csv"]})
    (STUDY / "manifest.json").write_text(json.dumps({"jobs": jobs}, indent=1), encoding="utf-8")
    print(f"Wrote {len(jobs)} jobs to {STUDY}")


if __name__ == "__main__":
    main()
