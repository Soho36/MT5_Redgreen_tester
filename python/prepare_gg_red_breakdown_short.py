"""Prepare the chart-matching red range-expansion breakdown short.

Red M30 signal; its low breaks the preceding n lows and its full high/low
range exceeds the widest preceding individual candle. The signal high need
not exceed prior highs. Entry/SL/exit are the corrected red short's rules.
"""
import json
import shutil

from prepare_gg_outside import ROOT, SETTINGS, BASE_INI, once
from prepare_gg_red_outside_short import build_red_short_source

EXPERT = "GG_red_breakdown_short"
STUDY = ROOT / "Reports" / "gg_red_breakdown_short_20261021"


def build_breakdown_source():
    src = build_red_short_source()
    for old, new in (
        ("UseOutsideFilter", "UseBreakdownFilter"),
        ("OutsideLookback", "BreakdownLookback"),
        ("MinOutsideRangeRatio", "MinBreakdownRangeRatio"),
        ("MinOutsideOverhangFraction", "MinLowBreakFraction"),
        ("IsOutsideSignal", "IsBreakdownSignal"),
    ):
        src = src.replace(old, new)
    src = once(src, "Red outside-bar short EA:", "Red range-breakdown short EA:")
    src = once(src, "// Research-only full-range outside-bar filter; off reproduces GG.",
               "// Red range-expansion breakdown filter; high-side overhang is not required.")
    src = once(src, "double priorHigh = -DBL_MAX, priorLow = DBL_MAX, widest = 0.0;",
               "double priorLow = DBL_MAX, widest = 0.0;")
    src = once(src, "      priorHigh = MathMax(priorHigh, high);\n", "")
    src = once(src, """   double upper = signalHigh - priorHigh;
   double lower = priorLow - signalLow;
   return upper > 0.0 && lower > 0.0
      && upper + 1e-9 >= MinLowBreakFraction * widest
      && lower + 1e-9 >= MinLowBreakFraction * widest
      && signalHigh - signalLow + 1e-9 >= MinBreakdownRangeRatio * widest;""",
               """   double lower = priorLow - signalLow;
   return lower > 0.0
      && lower + 1e-9 >= MinLowBreakFraction * widest
      && signalHigh - signalLow + 1e-9 >= MinBreakdownRangeRatio * widest;""")
    src = once(src, "// SELL-STOP ORDER AT PREVIOUS RED OUTSIDE CANDLE LOW",
               "// SELL-STOP ORDER AT PREVIOUS RED RANGE-BREAKDOWN CANDLE LOW")
    return src


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    (STUDY / f"{EXPERT}.mq5").write_text(build_breakdown_source(), encoding="utf-8")
    shutil.copyfile(ROOT / "mt5" / "experts" / "early_closes.mqh",
                    STUDY / "early_closes.mqh")
    template = BASE_INI.read_text(encoding="utf-16")
    template = template.replace("MinGreenRun=", "MinRedRun=")
    template = template.replace("MaxGreenRun=", "MaxRedRun=")
    jobs = []
    for n, ratio, low_break in [(None, None, None)] + SETTINGS:
        if n is None:
            tag = "ggredbreak_20261021_control"
            extra = "UseBreakdownFilter=false\n"
        else:
            tag = f"ggredbreak_20261021_n{n}_r{ratio:g}_b{low_break:g}".replace(".", "p")
            extra = (f"UseBreakdownFilter=true\nBreakdownLookback={n}\n"
                     f"MinBreakdownRangeRatio={ratio}\n"
                     f"MinLowBreakFraction={low_break}\n")
        ini = once(template, "Expert=CodexBaselineResearch\\GG_runband.ex5",
                   f"Expert=CodexBaselineResearch\\{EXPERT}.ex5")
        ini = once(ini, "Report=gggreen_20261020_cap0.htm", f"Report={tag}.htm")
        ini = once(ini, "RunTag=gggreen_20261020_cap0", f"RunTag={tag}")
        ini = once(ini, "SnapshotBars=0\n", "SnapshotBars=0\n" + extra)
        (STUDY / f"{tag}.ini").write_text(ini, encoding="utf-16")
        jobs.append({"tag": tag, "n": n, "range_ratio": ratio,
                     "low_break_fraction": low_break,
                     "outputs": [f"runband_{tag}_1.00.csv",
                                 f"runband_{tag}_1.00_stats.csv"]})
    (STUDY / "manifest.json").write_text(json.dumps({
        "expert": EXPERT,
        "definition": "Red closed signal; new n-bar low; range >= ratio x widest preceding candle; no new-high requirement; sell stop low, SL high",
        "strict_outside_study": "gg_red_outside_short_20261021",
        "jobs": jobs}, indent=2), encoding="utf-8")
    print(f"Prepared {len(jobs)} red breakdown short jobs in {STUDY}")


if __name__ == "__main__":
    main()

