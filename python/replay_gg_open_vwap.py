"""Prepare, run, or verify the paired native GG candle-open VWAP experiment."""
import argparse
import json
import shutil

import mt5_expert_layout as layout
import prepare_gg_vwap_ea as source
import run_mt5_job as tester
from analyze_price_levels import sha256


RUN = source.ROOT / "Reports" / "gg_open_replay_20261124"
EXPERT = "GG_open_vwap_research"
FEATURE = "gg_open_replay_20261124_features.csv"
PREFIX = "ggopen_20261124_"


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Expected exactly one occurrence of {old!r}")
    return text.replace(old, new)


def prepare():
    archive = source.STUDY
    frozen = json.loads((archive / "manifest.json").read_text())
    for name, digest in frozen["prepared_sha256"].items():
        assert sha256(archive / name) == digest, name
    original = next(j for j in frozen["jobs"] if j["gate"])
    old_tag = original["tag"]
    ea = (archive / f"{original['expert']}.mq5").read_text(encoding="utf-8")
    ea = once(ea, "bool VwapGateAllows(datetime barOpen, double close1)",
              "input bool GateUsesOpen = true;\n\nbool VwapGateAllows(datetime barOpen, double open1, double close1)")
    ea = once(ea, "double z = known ? (close1", "double price = GateUsesOpen ? open1 : close1;\n   double z = known ? (price")
    ea = once(ea, "&& close1 < vwap", "&& price < vwap")
    ea = once(ea, "VwapGateAllows(barOpen, c1)", "VwapGateAllows(barOpen, o1, c1)")
    ea = once(ea, '"signal_close", "vwap"', '"signal_open", "signal_close", "vwap"')
    ea = once(ea, "DoubleToString(close1, _Digits), known ?", "DoubleToString(open1, _Digits), DoubleToString(close1, _Digits), known ?")
    ea = once(ea, 'VWAP gate: close ", DoubleToString(close1', 'VWAP gate: signal price ", DoubleToString(price')
    RUN.mkdir(parents=True, exist_ok=True)
    if (RUN / "manifest.json").exists():
        raise FileExistsError("Study already prepared")
    (RUN / f"{EXPERT}.mq5").write_text(ea, encoding="utf-8")
    for name in source.INCLUDES:
        shutil.copyfile(archive / name, RUN / name)
    shutil.copyfile(archive / source.FEATURES, RUN / FEATURE)
    jobs = []
    for variant in ("open", "close"):
        tag = PREFIX + variant
        ini = (archive / f"{old_tag}.ini").read_text(encoding="utf-16")
        ini = ini.replace(old_tag, tag).replace(original["expert"] + ".ex5", EXPERT + ".ex5")
        ini = once(ini, source.FEATURES, FEATURE)
        ini = once(ini, "[TesterInputs]", "[TesterInputs]\nGateUsesOpen=" + str(variant == "open").lower())
        (RUN / f"{tag}.ini").write_text(ini, encoding="utf-16")
        jobs.append(dict(tag=tag, inputs_files=[FEATURE], outputs=[n.replace(old_tag, tag) for n in original["outputs"]]))
    (RUN / "manifest.json").write_text(json.dumps(dict(jobs=jobs), indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    action = parser.parse_args().action
    if action == "prepare":
        prepare()
    else:
        layout.EXPERT_FOLDERS[EXPERT] = "CodexGGOpenReplay"
        tester.main(RUN, EXPERT)
