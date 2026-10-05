"""Prepare the Q20 trendline buy-limit EA and tester jobs (protocol: docs/trendlines/TRENDLINE_LIMIT_PROTOCOL.md).

Copies the Q10 baseline research EA (Reports/trend_rr_20261002/RTL_trend_rr.mq5, tag f50_baseline) and replaces
its red-candle buy-stop entry with mt5/experts/trendline_limit.mqh, called at the open of every eligible bar
(flat, inside a trade window, before the flatten). Flatten, windows, early closes and the bar-close exit are
unchanged; leaving a trade window cancels every pending order (the limit too), and a new position is reported
to the include (episode / control arming).

Writes the run folder Reports/trendlines/trendline_limit_runs_20261005/ with:
- `classify`: LimitMode=1 again, a regression check against the verified classify-only log
  (Reports/trendlines/trendline_limit_20261005/, EA = Python on every bar);
- primary (mode 2), control C1 (mode 3) at the primary setting and the three sensitivities, control C2 (mode 4);
- the C1/C2 delta table: one delta per eligible bar, drawn with replacement from the primary's classify-only
  placement distances (open - V) / A in the same session segment, seed 20261005.
"""
import json
import re
import shutil

import numpy as np
import pandas as pd

from analyze_breach_reclaim import TAG, TREND
from analyze_price_levels import ROOT, sha256
from prepare_resistance_standalone import INSTALL, rolls_include

CLASSIFY = ROOT / "Reports" / "trendlines" / "trendline_limit_20261005"
CLASSIFY_BARS = CLASSIFY / "trendline_limit_20261005_classify_bars.csv"
RUN = ROOT / "Reports" / "trendlines" / "trendline_limit_runs_20261005"
STEM = "trendline_limit_runs_20261005"
EXPERT = "RTL_trendline_limit"
INCLUDE = ROOT / "mt5" / "experts" / "trendline_limit.mqh"
PROTOCOL = ROOT / "docs" / "trendlines" / "TRENDLINE_LIMIT_PROTOCOL.md"
DELTAS = f"{STEM}_deltas.csv"
SEED = 20261005
SETTINGS = {"": (0.5, 0), "_tt": (0.5, 1), "_s025": (0.25, 0), "_s100": (1.0, 0)}
ENTRY = "   // Red candle setup (only if all filters pass)\n"


def jobs():
    out = {"classify": dict(LimitMode=1)}
    for mode, name in ((2, "primary"), (3, "c1")):
        for suffix, (stop_a, offset) in SETTINGS.items():
            out[name + suffix] = dict(LimitMode=mode, LimitStopA=stop_a, LimitTickOffset=offset)
    out["c2"] = dict(LimitMode=4, LimitStopA=0.5, LimitTickOffset=0)
    common = dict(LimitN=5, LimitSessions=5, LimitMinSep=10, LimitMinSlope=0.02)
    for name, inputs in out.items():
        inputs.update(common)
        inputs.setdefault("LimitStopA", 0.5)
        inputs.setdefault("LimitTickOffset", 0)
        inputs["LimitDeltaFile"] = DELTAS if inputs["LimitMode"] >= 3 else ""
    return out


def build_source(source):
    patches = [
        ('#include "trend_rr_research.mqh"',
         '#include "contract_rolls.mqh"\n#include "trendline_limit.mqh"   // Q20 research entry\n'
         '#include "trend_rr_research.mqh"'),
        ("   if(!OpenTrendExports()) return INIT_FAILED;",
         "   if(!TLInit()) return INIT_FAILED;\n   if(!OpenTrendExports()) return INIT_FAILED;"),
        ("   FileClose(f);\n   return(0.0);\n}", "   FileClose(f);\n   TLDeinit();\n   return(0.0);\n}"),
        ("       FreezeTrendAtEntry();\n", "       FreezeTrendAtEntry();\n"
         "       tr_rr=RiskReward;   // Q20: one bar-close target in every regime\n"
         "       TLOnFill();   // Q20 episode / control arming\n"),
        ("int OnInit()\n{", "int OnInit()\n{\n"
         "   if(!MathIsValidNumber(RiskReward) || RiskReward<=0) return INIT_PARAMETERS_INCORRECT;"),
        ("      Print(\"⏱ Outside trading window → no new entries\");\n      CancelOldBuyStops();",
         "      Print(\"⏱ Outside trading window → no new entries\");\n      CancelAllOrders();   // Q20: the limit too"),
    ]
    for before, after in patches:
        assert source.count(before) == 1, before
        source = source.replace(before, after, 1)
    # The red-candle entry is the tail of OnTick, the last function in the file: replace it whole.
    assert source.count(ENTRY) == 1 and source.rstrip().endswith("}")
    head = source[:source.index(ENTRY)]
    return head + "   // Q20: a buy limit resting on a rising trendline replaces the red-candle buy stop.\n" \
                  "   TLOnBar(barOpen);\n}\n"


def segment(times):
    minutes = times.dt.hour * 60 + times.dt.minute
    return np.select([minutes < 600, minutes < 1380], ["morning", "main"], "evening")


def delta_table():
    """One delta per eligible bar of the verified classify-only log, drawn in time order within each segment."""
    bars = pd.read_csv(CLASSIFY_BARS, parse_dates=["bar_time"]).sort_values("bar_time")
    bars["segment"] = segment(bars.bar_time)
    pools = {s: g.delta.to_numpy() for s, g in bars[bars.status_ea == "order"].groupby("segment")}
    rng = np.random.default_rng(SEED)
    bars["delta"] = np.nan
    for s in ("morning", "main", "evening"):
        rows = bars.index[bars.segment == s]
        bars.loc[rows, "delta"] = rng.choice(pools[s], size=len(rows), replace=True)
    # delta can be <= 0: the primary's line only has to lie below the ask, which is one tick above the open
    assert bars.delta.notna().all()
    unix = (bars.bar_time - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)
    out = pd.DataFrame(dict(unix_time=unix, delta=bars.delta.map(lambda v: repr(float(v)))))
    out.to_csv(RUN / DELTAS, index=False)
    return {s: len(p) for s, p in pools.items()}


def main():
    RUN.mkdir(parents=True, exist_ok=True)
    parent = TREND / "RTL_trend_rr.mq5"
    expert = RUN / f"{EXPERT}.mq5"
    source = build_source(parent.read_text(encoding="utf-8-sig"))
    changed = not expert.exists() or expert.read_text(encoding="utf-8-sig") != source or \
        (RUN / INCLUDE.name).read_bytes() != INCLUDE.read_bytes()
    if changed and list(RUN.glob("*.completed.json")):
        raise RuntimeError("Preserve completed runs; do not overwrite their source")
    expert.write_text(source, encoding="utf-8-sig")
    for name in ("early_closes.mqh", "trend_rr_ledger.mqh", "trend_rr_research.mqh"):
        shutil.copyfile(TREND / name, RUN / name)
    shutil.copyfile(INCLUDE, RUN / INCLUDE.name)
    (RUN / "contract_rolls.mqh").write_text(rolls_include(), encoding="utf-8")
    pools = None if (RUN / DELTAS).exists() else delta_table()
    base_ini = (TREND / f"{TAG}.ini").read_text(encoding="utf-16")
    out = []
    for job, inputs in jobs().items():
        tag = f"{STEM}_{job}"
        path = RUN / f"{tag}.ini"
        if not (RUN / f"{tag}.completed.json").exists():
            ini = base_ini
            for key, value in dict(Expert=fr"{INSTALL}\{EXPERT}.ex5", RunTag=tag, Report=f"{tag}.htm").items():
                ini, n = re.subn(rf"(?m)^{key}=.*$", lambda m: f"{key}={value}", ini)
                assert n == 1, key
            ini = ini.replace("[TesterInputs]",
                              "[TesterInputs]\n" + "\n".join(f"{k}={v}" for k, v in inputs.items()), 1)
            path.write_text(ini, encoding="utf-16")
        outputs = [f"{tag}_limit.csv", f"{tag}_limit_stats.csv", f"runband_{tag}_1.00_stats.csv"]
        if inputs["LimitMode"] >= 2:
            outputs += [f"{tag}_fills.csv", f"runband_{tag}_1.00.csv", f"{tag}_checks.csv"]
        out.append(dict(tag=tag, ini=str(path), inputs=inputs, report=f"{tag}.htm", outputs=outputs,
                        inputs_files=[DELTAS] if inputs["LimitMode"] >= 3 else []))
    manifest = dict(experiment="Q20 buy limit resting on a rising trendline, full-history one-minute OHLC",
                    parent_source=str(parent), parent_sha256=sha256(parent), parent_ini=str(TREND / f"{TAG}.ini"),
                    include_source=str(INCLUDE), include_sha256=sha256(INCLUDE), expert_sha256=sha256(expert),
                    protocol_sha256=sha256(PROTOCOL), classify_bars=str(CLASSIFY_BARS),
                    classify_bars_sha256=sha256(CLASSIFY_BARS), deltas=DELTAS, deltas_sha256=sha256(RUN / DELTAS),
                    delta_seed=SEED, jobs=out)
    if pools:
        manifest["delta_pool_sizes"] = pools
    elif (RUN / "manifest.json").exists():
        manifest["delta_pool_sizes"] = json.loads((RUN / "manifest.json").read_text()).get("delta_pool_sizes")
    (RUN / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(expert, len(out), "jobs")


if __name__ == "__main__":
    main()
