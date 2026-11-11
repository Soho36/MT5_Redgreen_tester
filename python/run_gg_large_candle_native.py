"""Run the frozen GG study with the existing terminal, after it has been closed."""
import json
import shutil
import subprocess
from datetime import datetime
from prepare_gg_large_candle import RUN, EXPERT, DOC
from run_rtl_vwap_replay import hidden_process
from run_mt5_job import INSTALL_DIR, DATA, COMMON, AGENT_LOGS, compile_expert, trim_log
from audit_granularity_ledgers import digest
from project_paths import PROJECT_ROOT as ROOT


def main():
    check = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "(Get-Process terminal64 -ErrorAction SilentlyContinue | Measure-Object).Count"],
                           capture_output=True, text=True, check=True)
    assert check.stdout.strip() == "0", "Close MT5 before running; never terminate user processes"
    manifest = json.loads((RUN / "manifest.json").read_text())
    assert digest(DOC / "PROTOCOL.md") == manifest["protocol_sha256"]
    for name, expected in manifest["prepared_sha256"].items():
        assert digest(RUN / name) == expected, name
    compile_expert(RUN, EXPERT)
    for job in manifest["jobs"]:
        tag = job["tag"]
        marker = RUN / (tag + ".completed.json")
        if marker.exists():
            saved = json.loads(marker.read_text())
            assert all(digest(RUN / name) == h for name, h in saved["outputs"].items())
            continue
        assert all(not (COMMON / name).exists() for name in job["outputs"])
        print("Running " + tag, flush=True)
        proc = hidden_process([str(INSTALL_DIR / "terminal64.exe"), "/config:" + str(RUN / (tag + ".ini"))],
                              timeout=900, cwd=INSTALL_DIR)
        assert proc["returncode"] == 0, proc
        for name in job["outputs"]:
            shutil.copyfile(COMMON / name, RUN / name)
        shutil.copyfile(DATA / (tag + ".htm"), RUN / (tag + ".htm"))
        stamp = datetime.now().strftime("%Y%m%d")
        for src, suffix in ((DATA / "Tester/logs" / (stamp + ".log"), "tester"),
                            (AGENT_LOGS / (stamp + ".log"), "agent")):
            if src.exists():
                trim_log(src, RUN / (tag + "." + suffix + ".log"), EXPERT)
        done = dict(tag=tag, **proc, outputs={name:digest(RUN/name) for name in job["outputs"]},
                    report_sha256=digest(RUN/(tag+".htm")), expert_sha256=digest(RUN/(EXPERT+".ex5")))
        marker.write_text(json.dumps(done,indent=2),encoding="utf-8")
        if job["ratio"] == 0:
            reference = ROOT / "Reports/ym_baselines_20261023/runband_ymbase_20261023_gg_nq_1.00.csv"
            assert (RUN / job["outputs"][0]).read_bytes() == reference.read_bytes(), "Disabled control differs"
            print("Disabled control byte-identical to saved GG.",flush=True)
        print("Completed " + tag,flush=True)


if __name__ == "__main__":
    main()

