"""Prepare the frozen exit-threshold study; does not launch MT5 or alter its profile."""

import hashlib
import json
import re
from pathlib import Path

from project_paths import PROJECT_ROOT


def replace_once(text, before, after):
    assert text.count(before) == 1, f"Source anchor not unique: {before!r}"
    return text.replace(before, after, 1)


def main():
    root = PROJECT_ROOT
    out = root / "Reports/exit_thresholds_20260930"
    out.mkdir(parents=True, exist_ok=True)
    source_path = root / "mt5/experts/RR_r_MFE_buy-stop-entry_runband.cs"
    original = source_path.read_text(encoding="utf-8-sig")
    source = replace_once(original, "input double RiskReward     = 1.0;",
                         "input double RiskReward     = 1.0;\ninput bool UseFixedTP = false; // Research comparison only")
    source = replace_once(source, "void ManageOpenPosition()\n{",
                         "void ManageOpenPosition()\n{\n   if(UseFixedTP) return; // Attached TP handles profit-taking")
    source = replace_once(source, "\t   req.sl           = stop;",
                         "\t   req.sl           = stop;\n"
                         "       if(UseFixedTP)\n       {\n"
                         "          double tick = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);\n"
                         "          if(tick <= 0.0) return;\n"
                         "          req.tp = NormalizeDouble(MathCeil((entry + risk * RiskReward) / tick - 1e-9) * tick, _Digits);\n"
                         "       }")
    expert = out / "RTL_exit_comparison.mq5"
    expert.write_text(source, encoding="utf-8")
    jobs = []
    for phase, old in (("train", "train1519_run3"), ("recent", "test2026_run3")):
        template = (root / f"Reports/maxredrun_train_20260929/{old}.ini").read_text(encoding="utf-16")
        for mode, rr in [("close", r) for r in (1.0, .75, 1.25, 1.5, 2.0)] + [("tp", 1.0)]:
            tag = f"exit_20260930_{phase}_{mode}_{rr:.2f}".replace(".", "p")
            config = template
            for key, value in {"Expert": r"CodexExitResearch\RTL_exit_comparison.ex5",
                               "Report": f"{tag}.htm", "RunTag": tag,
                               "RiskReward": str(rr)}.items():
                config, count = re.subn(rf"(?m)^{key}=.*$", lambda _: f"{key}={value}", config)
                assert count == 1, key
            config = config.replace("[Experts]", f"SnapshotBars=1\nUseFixedTP={'true' if mode == 'tp' else 'false'}\n\n[Experts]")
            config = config[config.index("[Tester]"):]
            ini = out / f"{tag}.ini"
            ini.write_text(config, encoding="utf-16")
            jobs.append(dict(tag=tag, phase=phase, mode=mode, rr=rr, ini=str(ini),
                             csv=f"runband_{tag}_{rr:.2f}.csv", report=f"{tag}.htm"))
    manifest = dict(source=str(source_path), source_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
                    experimental_source_sha256=hashlib.sha256(expert.read_bytes()).hexdigest(),
                    protocol_sha256=hashlib.sha256((root / "docs/EXIT_THRESHOLD_PROTOCOL.md").read_bytes()).hexdigest(),
                    jobs=jobs)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Prepared {len(jobs)} runs and {expert}")


if __name__ == "__main__":
    main()
