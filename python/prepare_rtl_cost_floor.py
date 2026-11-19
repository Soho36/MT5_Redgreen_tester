"""Prepare the RTL cost-floor runs: RTL baseline with a minimum signal-candle range (see PROTOCOL.md)."""
import hashlib
import json
import shutil

from project_paths import PROJECT_ROOT as ROOT

SRC_RUN = ROOT / "Reports/rtl_midpoint_20261116"
RUN = ROOT / "Reports/rtl_cost_floor_20261119"
DOC = ROOT / "docs/baseline/rtl-cost-floor"
EXPERT = "RTL_midpoint"
CONTROL_INI = SRC_RUN / "midpoint_20261116_baseline.ini"
ARMS = {"control": None, "floor20": "262.5", "floor10": "524.5", "floor05": "1049.5"}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tag(arm):
    return "costfloor_20261119_" + arm


def main():
    assert (DOC / "PROTOCOL.md").exists()
    assert not (RUN / "manifest.json").exists(), "Preserve prepared study"
    assert sha(SRC_RUN / f"{EXPERT}.mq5") == "b4b1879c5cd807ecb447510a2f6db7cf3417c41861b43e5ee6c792185062fa32"
    RUN.mkdir(parents=True, exist_ok=True)
    for name in (f"{EXPERT}.mq5", "early_closes.mqh"):
        shutil.copyfile(SRC_RUN / name, RUN / name)
    base = CONTROL_INI.read_text(encoding="utf-16").splitlines()
    jobs = []
    for arm, min_range in ARMS.items():
        changes = {"RunTag": tag(arm), "Report": tag(arm) + ".htm"}
        if min_range:
            changes.update({"UseCandleRangeFilter": "true||false||0||true||N",
                            "MinCandleRange": f"{min_range}||5.0||0.500000||50.000000||N",
                            "MaxCandleRange": "10000000||1000||500||30000||N"})
        lines = list(base)
        for key, value in changes.items():
            assert sum(x.startswith(key + "=") for x in lines) == 1, key
            lines = [key + "=" + value if x.startswith(key + "=") else x for x in lines]
        (RUN / (tag(arm) + ".ini")).write_text("\n".join(lines) + "\n", encoding="utf-16")
        jobs.append(dict(tag=tag(arm), arm=arm, min_range_points=min_range,
                         outputs=[f"runband_{tag(arm)}_1.00.csv", f"runband_{tag(arm)}_1.00_stats.csv"]))
    files = [DOC / "PROTOCOL.md", CONTROL_INI, ROOT / "python/prepare_rtl_cost_floor.py",
             *RUN.glob("*.mq5"), *RUN.glob("*.mqh"), *RUN.glob("*.ini")]
    manifest = dict(expert=EXPERT, jobs=jobs, input_hashes={str(p): sha(p) for p in files})
    (RUN / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Prepared", RUN)


if __name__ == "__main__":
    main()
