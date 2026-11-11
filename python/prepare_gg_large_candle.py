"""Freeze four native GG session-relative midpoint-stop runs."""
import json
import re
import shutil
from audit_granularity_ledgers import digest
from prepare_gg_outside import once
from prepare_ym_baselines import STRATEGIES, SYMBOLS, make_ini
from project_paths import PROJECT_ROOT as ROOT

RUN = ROOT / "Reports/gg_large_candle_20261109"
DOC = ROOT / "docs/baseline/gg-large-candle-stop"
EXPERT = "GG_large_candle"
BASE = ROOT / "mt5/experts/GG_r_MFE_buy-stop-entry_runband.cs"


def build_source():
    src = BASE.read_text(encoding="utf-8")
    src = once(src, "// ======== HELPER FUNCTIONS ========",
               '#include "gg_large_candle_research.mqh"\n#include "window_equity_research.mqh"\n\n// ======== HELPER FUNCTIONS ========')
    src = once(src, "int OnInit()\n{", "int OnInit()\n{\n   if(!MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;")
    src = once(src, "   DisplaySettings();",
               "   if(!LargeCandleInit() || !WindowEquityInit()) return INIT_FAILED;\n   DisplaySettings();")
    src = once(src, "\t   double stop  = l1;", "\t   double stop  = LargeCandleStop(h1,l1);")
    src = once(src, "\t   g_candleRange = h1 - l1;", "\t   g_candleRange = risk; // actual initial stop distance")
    src = once(src, "void OnTick()", "void StrategyOnTick()")
    assert "void OnDeinit(" not in src
    src += """
void OnTick() { WindowEquitySample(); StrategyOnTick(); WindowEquitySample(); }
void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &req,const MqlTradeResult &res)
{ WindowEquityTransaction(trans); }
void OnDeinit(const int reason)
{
   WindowEquityClose();
   if(gl_file != INVALID_HANDLE) {FileClose(gl_file);gl_file=INVALID_HANDLE;}
}
"""
    return src


def main():
    if (RUN / "manifest.json").exists():
        raise RuntimeError("Preserve prepared study")
    RUN.mkdir(parents=True, exist_ok=True)
    src = build_source()
    (RUN / (EXPERT + ".mq5")).write_text(src, encoding="utf-8")
    for name in ("early_closes.mqh", "gg_large_candle_research.mqh", "window_equity_research.mqh"):
        shutil.copyfile(ROOT / "mt5/experts" / name, RUN / name)
    jobs = []
    for ratio in (0.0, 3.0, 2.5, 3.5):
        label = "control" if not ratio else f"r{ratio:g}".replace(".", "p")
        tag = "gglarge_20261109_" + label
        ini = make_ini(STRATEGIES["gg"][2], tag, SYMBOLS["nq"])
        ini = once(ini, "Expert=CodexBaselineResearch\\GG_runband.ex5",
                   f"Expert=CodexResearch\\{EXPERT}.ex5")
        ini = once(ini, "[TesterInputs]", "[TesterInputs]\n"
                   f"UseLargeCandleStop={str(bool(ratio)).lower()}\n"
                   f"LargeCandleRatio={ratio or 3.0}\nLargeCandleMinPrior=5")
        fields = re.findall(r"^input\s+\w+\s+(\w+)\s*=", src + (RUN / "gg_large_candle_research.mqh").read_text(), re.M)
        given = re.findall(r"^(\w+)=", ini.split("[TesterInputs]")[1].split("[", 1)[0], re.M)
        assert sorted(fields) == sorted(given), (set(fields)-set(given),set(given)-set(fields))
        (RUN / (tag + ".ini")).write_text(ini, encoding="utf-16")
        jobs.append(dict(tag=tag, ratio=ratio, mode="rtl",
                         outputs=[f"runband_{tag}_1.00.csv", f"runband_{tag}_1.00_stats.csv",
                                  f"large_candle_{tag}.tsv", f"window_equity_{tag}.bin"]))
    manifest = dict(expert=EXPERT, symbol=SYMBOLS["nq"], jobs=jobs,
                    protocol_sha256=digest(DOC / "PROTOCOL.md"),
                    prepared_sha256={p.name: digest(p) for p in RUN.iterdir() if p.is_file()})
    (RUN / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Prepared {len(jobs)} jobs in {RUN}", flush=True)


if __name__ == "__main__":
    main()

