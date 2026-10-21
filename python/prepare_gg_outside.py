"""Prepare isolated GG outside-bar MT5 runs from the unchanged GG baseline.

Run:
  venv/Scripts/python.exe python/prepare_gg_outside.py
  venv/Scripts/python.exe python/run_mt5_job.py Reports/gg_outside_20261020 GG_outside
"""
import json
import shutil
from project_paths import PROJECT_ROOT as ROOT

EXPERT = "GG_outside"
STUDY = ROOT / "Reports" / "gg_outside_20261020"
BASE = ROOT / "mt5" / "experts" / "GG_r_MFE_buy-stop-entry_runband.cs"
BASE_INI = ROOT / "Reports" / "gg_green_cap_review_20261020" / "gggreen_20261020_cap0.ini"
SETTINGS = [(n, ratio, overhang) for n in (1, 3, 5, 10)
            for ratio, overhang in ((1.0, 0.0), (1.25, 0.0), (1.25, 0.10))]

INPUTS = """// Research-only full-range outside-bar filter; off reproduces GG.
input bool   UseOutsideFilter = false;
input int    OutsideLookback = 3;
input double MinOutsideRangeRatio = 1.25;
input double MinOutsideOverhangFraction = 0.0;

"""
PREDICATE = """// Signal is index 1; compare only with prior CLOSED bars 2..n+1.
bool IsOutsideSignal(double signalHigh, double signalLow)
{
   if(!UseOutsideFilter) return true;
   if(Bars(_Symbol, _Period) < OutsideLookback + 2) return false;
   double priorHigh = -DBL_MAX, priorLow = DBL_MAX, widest = 0.0;
   for(int i = 2; i <= OutsideLookback + 1; ++i)
   {
      double high = iHigh(_Symbol, _Period, i);
      double low = iLow(_Symbol, _Period, i);
      if(high <= low) return false;
      priorHigh = MathMax(priorHigh, high);
      priorLow = MathMin(priorLow, low);
      widest = MathMax(widest, high - low);
   }
   double upper = signalHigh - priorHigh;
   double lower = priorLow - signalLow;
   return upper > 0.0 && lower > 0.0
      && upper + 1e-9 >= MinOutsideOverhangFraction * widest
      && lower + 1e-9 >= MinOutsideOverhangFraction * widest
      && signalHigh - signalLow + 1e-9 >= MinOutsideRangeRatio * widest;
}

"""

def once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f"Anchor occurs {source.count(old)} times: {old[:70]!r}")
    return source.replace(old, new)

def build_source():
    src = BASE.read_text(encoding="utf-8").replace("\r\n", "\n")
    src = once(src, "input int    SnapshotBars = 0;       // Raw OHLC bars to log (0 = disabled)\n",
               "input int    SnapshotBars = 0;       // Raw OHLC bars to log (0 = disabled)\n\n" + INPUTS)
    src = once(src, "bool IsCandleInRange(double high, double low)\n",
               PREDICATE + "bool IsCandleInRange(double high, double low)\n")
    src = once(src, "   if(SnapshotBars < 0)\n",
               """   if(OutsideLookback < 1 || MinOutsideRangeRatio < 1.0
      || MinOutsideOverhangFraction < 0.0
      || !MathIsValidNumber(MinOutsideRangeRatio)
      || !MathIsValidNumber(MinOutsideOverhangFraction))
   {
      Print("Invalid outside-bar inputs");
      return INIT_PARAMETERS_INCORRECT;
   }

   if(SnapshotBars < 0)
""")
    anchor = '\t   Print("Green candle (run=", run, ", location=", DoubleToString(loc, 2), ") -> place Buy Stop");\n'
    src = once(src, anchor, """\t   if(!IsOutsideSignal(h1, l1))
\t   {
\t      CancelOldBuyStops();
\t      return;
\t   }

""" + anchor)
    return src

def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    (STUDY / f"{EXPERT}.mq5").write_text(build_source(), encoding="utf-8")
    shutil.copyfile(ROOT / "mt5" / "experts" / "early_closes.mqh", STUDY / "early_closes.mqh")
    template = BASE_INI.read_text(encoding="utf-16")
    jobs = []
    tag = "ggout_20261020_control"
    control = once(template, "Expert=CodexBaselineResearch\\GG_runband.ex5",
                   f"Expert=CodexBaselineResearch\\{EXPERT}.ex5")
    control = once(control, "Report=gggreen_20261020_cap0.htm", f"Report={tag}.htm")
    control = once(control, "RunTag=gggreen_20261020_cap0", f"RunTag={tag}")
    control = once(control, "SnapshotBars=0\n", "SnapshotBars=0\nUseOutsideFilter=false\n")
    (STUDY / f"{tag}.ini").write_text(control, encoding="utf-16")
    jobs.append({"tag": tag, "control": True,
                 "outputs": [f"runband_{tag}_1.00.csv", f"runband_{tag}_1.00_stats.csv"]})
    for n, ratio, overhang in SETTINGS:
        tag = f"ggout_20261020_n{n}_r{ratio:g}_o{overhang:g}".replace(".", "p")
        ini = once(template, "Expert=CodexBaselineResearch\\GG_runband.ex5",
                   f"Expert=CodexBaselineResearch\\{EXPERT}.ex5")
        ini = once(ini, "Report=gggreen_20261020_cap0.htm", f"Report={tag}.htm")
        ini = once(ini, "RunTag=gggreen_20261020_cap0", f"RunTag={tag}")
        ini = once(ini, "SnapshotBars=0\n",
                   f"SnapshotBars=0\nUseOutsideFilter=true\nOutsideLookback={n}\n"
                   f"MinOutsideRangeRatio={ratio}\nMinOutsideOverhangFraction={overhang}\n")
        (STUDY / f"{tag}.ini").write_text(ini, encoding="utf-16")
        jobs.append({"tag": tag, "n": n, "range_ratio": ratio,
                     "overhang_fraction": overhang,
                     "outputs": [f"runband_{tag}_1.00.csv", f"runband_{tag}_1.00_stats.csv"]})
    (STUDY / "manifest.json").write_text(json.dumps({
        "expert": EXPERT, "baseline": str(BASE_INI),
        "definition": "green GG signal; high and low beyond prior n bars; each overhang >= fraction times widest prior candle; signal range >= ratio times widest prior candle",
        "jobs": jobs}, indent=2), encoding="utf-8")
    print(f"Prepared {len(jobs)} jobs in {STUDY}")

if __name__ == "__main__":
    main()



