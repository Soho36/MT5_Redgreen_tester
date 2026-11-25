"""Prepare the native seven-close replay from the frozen cost-floor control."""
import json
import shutil

from prepare_rtl_cost_floor import ROOT, sha

RUN = ROOT / "Reports/rtl_regression_slope_20261125"
BASE = ROOT / "Reports/rtl_cost_floor_20261119"
CONTROL = "costfloor_20261119_control"
EXPERT = "RTL_regression7_research"
PREFIX = "rtlreg7_20261125_"

GATE = """
input bool RequireRisingRegression = false;
int regressionLog = INVALID_HANDLE;

bool RegressionAllows(datetime barOpen)
{
   double closes[7];
   int count = CopyClose(_Symbol, PERIOD_M30, 1, 7, closes);
   // CopyClose places the oldest value first. The slope equals numerator / 28.
   double numerator = 0;
   if(count == 7)
      for(int i = 0; i < 7; i++)
         numerator += (i - 3) * closes[i];
   bool allowed = !RequireRisingRegression || (count == 7 && numerator > 0);
   FileWrite(regressionLog, (long)barOpen, (long)iTime(_Symbol, PERIOD_M30, 1),
             count, numerator, (int)allowed);
   return allowed;
}

void OnDeinit(const int reason)
{
   if(regressionLog != INVALID_HANDLE) FileClose(regressionLog);
}
"""


def replace(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new)


def main():
    RUN.mkdir(parents=True, exist_ok=True)
    assert not list(RUN.glob("*.completed.json")), "Preserve completed runs"
    src = BASE / "RTL_midpoint.mq5"
    assert sha(src) == "b4b1879c5cd807ecb447510a2f6db7cf3417c41861b43e5ee6c792185062fa32"
    code = src.read_text(encoding="utf-8")
    code = replace(code, "int OnInit()", GATE + "\nint OnInit()")
    code = replace(code, "   DisplaySettings();", """   regressionLog = FileOpen("decisions_" + g_runTag + ".tsv",
      FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_COMMON, '\\t');
   if(regressionLog == INVALID_HANDLE) return INIT_FAILED;
   FileWrite(regressionLog, "bar", "signal", "bars", "numerator", "allowed");
   DisplaySettings();""")
    code = replace(code, "double entry = h1;", "if(!RegressionAllows(barOpen)) return;\n       double entry = h1;")
    code = replace(code, '"early_closes.mqh"', '"regression7_early_closes.mqh"')
    (RUN / (EXPERT + ".mq5")).write_text(code, encoding="utf-8")
    shutil.copyfile(BASE / "early_closes.mqh", RUN / "regression7_early_closes.mqh")
    ini = (BASE / (CONTROL + ".ini")).read_text(encoding="utf-16")
    jobs = []
    for arm in ("off", "on"):
        tag = PREFIX + arm
        config = ini.replace(CONTROL, tag).replace("RTL_midpoint.ex5", EXPERT + ".ex5")
        config = replace(config, "[TesterInputs]", "[TesterInputs]\nRequireRisingRegression=" + str(arm == "on").lower())
        (RUN / (tag + ".ini")).write_text(config, encoding="utf-16")
        jobs.append(dict(tag=tag, outputs=[f"runband_{tag}_1.00.csv", f"runband_{tag}_1.00_stats.csv", f"decisions_{tag}.tsv"]))
    (RUN / "manifest.json").write_text(json.dumps(dict(expert=EXPERT, jobs=jobs), indent=2))


if __name__ == "__main__":
    main()
