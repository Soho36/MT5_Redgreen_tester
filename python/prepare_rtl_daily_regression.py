"""Prepare a five-completed-D1 gate on the archived native M30 RTL regression replay."""
import json
import shutil

from prepare_rtl_regression_slope import EXPERT as M30_EXPERT, GATE, PREFIX as M30_PREFIX
from prepare_rtl_regression_slope import ROOT, RUN as M30_RUN, replace

RUN = ROOT / "Reports/rtl_daily_regression_slope_20261125"
EXPERT = "RTL_regression5_daily_research"
PREFIX = "rtld1reg5_20261125_"

DAILY_GATE = """
input bool RequireRisingRegression = false;
int regressionLog = INVALID_HANDLE;

bool RegressionAllows(datetime barOpen)
{
   double closes[5];
   int count = CopyClose(_Symbol, PERIOD_D1, 1, 5, closes);
   double numerator = 0;
   if(count == 5)
      for(int i = 0; i < 5; i++)
         numerator += (i - 2) * closes[i];  // Oldest first. Slope = numerator / 10.
   bool allowed = !RequireRisingRegression || (count == 5 && numerator > 0);
   FileWrite(regressionLog, (long)barOpen, (long)iTime(_Symbol, PERIOD_M30, 1),
             (long)iTime(_Symbol, PERIOD_D1, 1), count, numerator, (int)allowed);
   return allowed;
}

void OnDeinit(const int reason)
{
   if(regressionLog != INVALID_HANDLE) FileClose(regressionLog);
}
"""


def main():
    RUN.mkdir(parents=True, exist_ok=True)
    assert not list(RUN.glob("*.completed.json")), "Preserve completed study"
    src = (M30_RUN / (M30_EXPERT + ".mq5")).read_text(encoding="utf-8")
    src = replace(src, GATE, DAILY_GATE)
    src = replace(src, '"signal", "bars",', '"signal", "last_daily", "bars",')
    include = "regression5d_early_closes.mqh"
    src = replace(src, "regression7_early_closes.mqh", include)
    shutil.copyfile(M30_RUN / "regression7_early_closes.mqh", RUN / include)
    (RUN / (EXPERT + ".mq5")).write_text(src, encoding="utf-8")
    jobs = []
    for arm in ("off", "on"):
        old, tag = M30_PREFIX + arm, PREFIX + arm
        ini = (M30_RUN / (old + ".ini")).read_text(encoding="utf-16")
        ini = replace(ini, M30_EXPERT + ".ex5", EXPERT + ".ex5").replace(old, tag)
        assert "Period=M30" in ini.splitlines()
        (RUN / (tag + ".ini")).write_text(ini, encoding="utf-16")
        jobs.append(dict(tag=tag, outputs=[f"runband_{tag}_1.00.csv", f"runband_{tag}_1.00_stats.csv", f"decisions_{tag}.tsv"]))
    (RUN / "manifest.json").write_text(json.dumps(dict(expert=EXPERT, jobs=jobs), indent=2))


if __name__ == "__main__":
    main()
