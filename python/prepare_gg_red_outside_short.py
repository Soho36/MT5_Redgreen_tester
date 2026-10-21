"""Prepare red-outside-candle sell stops using the GG short order/exit mechanics.

This is the user's corrected short hypothesis: the CLOSED signal candle is red,
its high and low exceed the preceding n-bar extremes, and a sell stop rests at
its low with a stop loss at its high. The previous green-signal short remains
a separate, unchanged research result.
"""
import json
import shutil

from prepare_gg_outside import ROOT, SETTINGS, BASE_INI, once
from prepare_gg_outside_short import build_short_source

EXPERT = "GG_red_outside_short"
STUDY = ROOT / "Reports" / "gg_red_outside_short_20261021"


def build_red_short_source():
    src = build_short_source()
    src = src.replace("MinGreenRun", "MinRedRun").replace("MaxGreenRun", "MaxRedRun")
    src = src.replace("ConsecutiveGreenRun", "ConsecutiveRedRun")
    src = src.replace("g_greenRun", "g_redRun")
    src = once(src, "if(iClose(_Symbol, _Period, i) > iOpen(_Symbol, _Period, i))",
               "if(iClose(_Symbol, _Period, i) < iOpen(_Symbol, _Period, i))")
    src = once(src, "if(c1 > o1)   // GREEN signal candle",
               "if(c1 < o1)   // RED signal candle")
    src = src.replace("green", "red").replace("Green", "Red").replace("GREEN", "RED")
    src = once(src, "a red bar (no signal) leaves",
               "a green bar (no signal) leaves")
    src = once(src, "Red-Red Breakout EA:", "Red outside-bar short EA:")
    src = once(src, "Signal candle is red (close > open)",
               "Signal candle is red (close < open)")
    src = once(src, "same buy-stop entry, plus",
               "sell-stop entry below the red signal low, plus")
    src = once(src, "With all filters off it trades exactly like the base EA.",
               "With the outside filter off it is a red-candle short control.")
    # The full high/low outside predicate, pending-order life, stop, target and
    # flattening remain exactly those of the green-signal short variant.
    return src


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    (STUDY / f"{EXPERT}.mq5").write_text(build_red_short_source(), encoding="utf-8")
    shutil.copyfile(ROOT / "mt5" / "experts" / "early_closes.mqh",
                    STUDY / "early_closes.mqh")
    template = BASE_INI.read_text(encoding="utf-16")
    template = template.replace("MinGreenRun=", "MinRedRun=")
    template = template.replace("MaxGreenRun=", "MaxRedRun=")
    jobs = []
    for n, ratio, overhang in [(None, None, None)] + SETTINGS:
        if n is None:
            tag = "ggredshort_20261021_control"
            extra = "UseOutsideFilter=false\n"
        else:
            tag = f"ggredshort_20261021_n{n}_r{ratio:g}_o{overhang:g}".replace(".", "p")
            extra = (f"UseOutsideFilter=true\nOutsideLookback={n}\n"
                     f"MinOutsideRangeRatio={ratio}\n"
                     f"MinOutsideOverhangFraction={overhang}\n")
        ini = once(template, "Expert=CodexBaselineResearch\\GG_runband.ex5",
                   f"Expert=CodexBaselineResearch\\{EXPERT}.ex5")
        ini = once(ini, "Report=gggreen_20261020_cap0.htm", f"Report={tag}.htm")
        ini = once(ini, "RunTag=gggreen_20261020_cap0", f"RunTag={tag}")
        ini = once(ini, "SnapshotBars=0\n", "SnapshotBars=0\n" + extra)
        (STUDY / f"{tag}.ini").write_text(ini, encoding="utf-16")
        jobs.append({"tag": tag, "n": n, "range_ratio": ratio,
                     "overhang_fraction": overhang,
                     "outputs": [f"runband_{tag}_1.00.csv",
                                 f"runband_{tag}_1.00_stats.csv"]})
    (STUDY / "manifest.json").write_text(json.dumps({
        "expert": EXPERT,
        "description": "Red outside signal, sell stop at low, SL at high, 1R bar-close exit",
        "prior_green_short_study": "gg_outside_short_20261020",
        "jobs": jobs}, indent=2), encoding="utf-8")
    print(f"Prepared {len(jobs)} corrected red-outside short jobs in {STUDY}")


if __name__ == "__main__":
    main()



