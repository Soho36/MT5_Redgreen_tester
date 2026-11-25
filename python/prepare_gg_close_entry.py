"""Prepare native GG high-breakout and on-close entry tester jobs."""
import json
import shutil

from prepare_gg_outside import once
from prepare_ym_baselines import STUDY as BASE
from project_paths import PROJECT_ROOT
from mt5_expert_layout import EXPERT_FOLDERS

RUN = PROJECT_ROOT / "Reports" / "gg_close_entry_20261125"
EXPERT = "GG_close_entry_research"
OLD_TAG = "ymbase_20261023_gg_nq"
EXPERT_FOLDERS[EXPERT] = "CodexGGCloseEntry"


def prepare():
    ea = (BASE / "GG_runband.mq5").read_text(encoding="utf-8")
    for old, new in (
        ("int OnInit()\n{", "input bool EnterOnClose = false;\n\nint OnInit()\n{\n   if(!MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;"),
        ("double entry = h1;", "double entry = EnterOnClose ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : h1;"),
        ("req.action       = TRADE_ACTION_PENDING;", "req.action       = EnterOnClose ? TRADE_ACTION_DEAL : TRADE_ACTION_PENDING;"),
        ("req.type         = ORDER_TYPE_BUY_STOP;", "req.type         = EnterOnClose ? ORDER_TYPE_BUY : ORDER_TYPE_BUY_STOP;"),
        ("req.type_filling = ORDER_FILLING_RETURN;", "req.type_filling = EnterOnClose ? ORDER_FILLING_FOK : ORDER_FILLING_RETURN;"),
        ('") -> place Buy Stop"', '") -> submit GG entry"'),
        ('"Place Buy Stop failed err="', '"GG entry failed err="'),
        ('"Buy Stop placed @"', '"GG entry submitted @"'),
    ):
        ea = once(ea, old, new)
    RUN.mkdir(exist_ok=False)
    (RUN / f"{EXPERT}.mq5").write_text(ea, encoding="utf-8")
    shutil.copyfile(BASE / "early_closes.mqh", RUN / "early_closes.mqh")
    template = (BASE / f"{OLD_TAG}.ini").read_text(encoding="utf-16")
    jobs = []
    for mode in ("high", "close"):
        tag = f"gg_entry_20261125_{mode}"
        ini = template.replace(OLD_TAG, tag)
        ini = once(ini, r"CodexBaselineResearch\GG_runband.ex5", rf"CodexGGCloseEntry\{EXPERT}.ex5")
        ini = once(ini, "[TesterInputs]", "[TesterInputs]\nEnterOnClose=" + str(mode == "close").lower())
        (RUN / f"{tag}.ini").write_text(ini, encoding="utf-16")
        jobs.append(dict(tag=tag, outputs=[f"runband_{tag}_1.00.csv", f"runband_{tag}_1.00_stats.csv"]))
    (RUN / "manifest.json").write_text(json.dumps(dict(jobs=jobs), indent=2))


if __name__ == "__main__":
    import argparse
    import run_mt5_job

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    if parser.parse_args().action == "prepare":
        prepare()
    else:
        run_mt5_job.main(RUN, EXPERT)
