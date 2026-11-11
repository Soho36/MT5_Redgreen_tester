"""Run GG large-candle study in its own portable MT5, leaving the open terminal running."""
import json
import run_rtl_vwap_replay as portable
from prepare_gg_large_candle import RUN, EXPERT
from project_paths import PROJECT_ROOT as ROOT


def main():
    portable.RUN = RUN
    portable.RUNTIME = RUN / "runtime"
    portable.OWNER = "GG large-candle stop 2026-11-09; isolated portable runtime"
    portable.EXPERT_FOLDER = "CodexResearch"
    portable.compile_expert()
    manifest = json.loads((RUN / "manifest.json").read_text())
    for job in manifest["jobs"]:
        portable.run_job(job["tag"])
        if job["ratio"] == 0:
            reference = ROOT / "Reports/ym_baselines_20261023/runband_ymbase_20261023_gg_nq_1.00.csv"
            assert (RUN / job["outputs"][0]).read_bytes() == reference.read_bytes(), "Disabled control differs"
            print("Disabled control byte-identical to saved GG.", flush=True)


if __name__ == "__main__":
    main()

