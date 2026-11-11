"""Freeze eight native GG size-cap runs: cap off, 4x, 5x, 6x on two window settings."""
import json
import re
import shutil
from audit_granularity_ledgers import digest
from prepare_gg_outside import once
from prepare_ym_baselines import STRATEGIES, SYMBOLS, make_ini
from project_paths import PROJECT_ROOT as ROOT

RUN = ROOT / "Reports/gg_size_cap_20261111"
DOC = ROOT / "docs/baseline/gg-size-cap"
EXPERT = "GG_size_cap"
BASE = ROOT / "mt5/experts/GG_r_MFE_buy-stop-entry_runband.cs"
RATIOS = (0.0, 4.0, 5.0, 6.0)
PRIMARY = 5.0
# arm -> W1600W1700 (false disables submissions at 16:00 and 16:30) and the saved ledger its control must reproduce
ARMS = {"base": (True, ROOT / "Reports/ym_baselines_20261023/runband_ymbase_20261023_gg_nq_1.00.csv"),
        "ex16": (False, ROOT / "Reports/rtl_gg_exclude16_20261101/rtlvwap_ex16_20261101_gg_base_skip_1.00.csv")}
INCLUDES = ("early_closes.mqh", "gg_size_cap_research.mqh", "window_equity_research.mqh")
GREEN = '\t   Print("Green candle (run=", run, ", location=", DoubleToString(loc, 2), ") -> place Buy Stop");'
REJECT = ('\t   if(SizeCapReject(h1,l1))\n\t   {\n'
          '\t      Print("Size cap: signal candle too large for its session - skipping signal");\n'
          '\t      CancelOldBuyStops();\n\t      return;\n\t   }\n\n')


def build_source():
    src = BASE.read_text(encoding="utf-8")
    src = once(src, "// ======== HELPER FUNCTIONS ========",
               '#include "gg_size_cap_research.mqh"\n#include "window_equity_research.mqh"\n\n// ======== HELPER FUNCTIONS ========')
    src = once(src, "int OnInit()\n{", "int OnInit()\n{\n   if(!MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;")
    src = once(src, "   DisplaySettings();",
               "   if(!SizeCapInit() || !WindowEquityInit()) return INIT_FAILED;\n   DisplaySettings();")
    # After the EA's own filters and before the order: a capped signal is a rejected signal.
    src = once(src, GREEN, REJECT + GREEN)
    src = once(src, "void OnTick()", "void StrategyOnTick()")
    assert "void OnDeinit(" not in src
    src += """
void OnTick() { WindowEquitySample(); StrategyOnTick(); WindowEquitySample(); }
void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &req,const MqlTradeResult &res)
{ WindowEquityTransaction(trans); }
void OnDeinit(const int reason)
{
   WindowEquityClose();
   if(sc_file != INVALID_HANDLE) {FileClose(sc_file);sc_file=INVALID_HANDLE;}
}
"""
    return src


def job_tag(arm, ratio):
    return f"ggcap_20261111_{arm}_" + ("control" if not ratio else f"c{ratio:g}")


def main():
    if (RUN / "manifest.json").exists():
        raise RuntimeError("Preserve prepared study")
    RUN.mkdir(parents=True, exist_ok=True)
    src = build_source()
    (RUN / (EXPERT + ".mq5")).write_text(src, encoding="utf-8")
    for name in INCLUDES:
        shutil.copyfile(ROOT / "mt5/experts" / name, RUN / name)
    helper = (RUN / "gg_size_cap_research.mqh").read_text()
    fields = re.findall(r"^input\s+\w+\s+(\w+)\s*=", src + helper, re.M)
    jobs = []
    for arm, (open_hour, reference) in ARMS.items():
        assert reference.exists(), reference
        for ratio in RATIOS:
            tag = job_tag(arm, ratio)
            ini = make_ini(STRATEGIES["gg"][2], tag, SYMBOLS["nq"])
            ini = once(ini, "Expert=CodexBaselineResearch\\GG_runband.ex5",
                       f"Expert=CodexResearch\\{EXPERT}.ex5")
            ini = once(ini, "[TesterInputs]", "[TesterInputs]\n"
                       f"UseSizeCap={str(bool(ratio)).lower()}\n"
                       f"SizeCapRatio={ratio or PRIMARY}\nSizeCapMinPrior=5")
            if not open_hour:
                ini = once(ini, "W1600W1700=true||", "W1600W1700=false||")
            given = re.findall(r"^(\w+)=", ini.split("[TesterInputs]")[1].split("[", 1)[0], re.M)
            assert sorted(fields) == sorted(given), (set(fields) - set(given), set(given) - set(fields))
            (RUN / (tag + ".ini")).write_text(ini, encoding="utf-16")
            jobs.append(dict(tag=tag, arm=arm, ratio=ratio, mode="rtl", open_hour=open_hour,
                             outputs=[f"runband_{tag}_1.00.csv", f"runband_{tag}_1.00_stats.csv",
                                      f"size_cap_{tag}.tsv", f"window_equity_{tag}.bin"]))
    manifest = dict(expert=EXPERT, symbol=SYMBOLS["nq"], jobs=jobs,
                    protocol_sha256=digest(DOC / "PROTOCOL.md"),
                    base_source_sha256=digest(BASE),
                    prepared_sha256={p.name: digest(p) for p in RUN.iterdir() if p.is_file()})
    (RUN / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Prepared {len(jobs)} jobs in {RUN}", flush=True)


if __name__ == "__main__":
    main()
