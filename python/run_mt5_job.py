"""Compile a prepared research EA and run one tester job, then collect its files into the run folder.

Usage: run_mt5_job.py <run_dir> <expert_name> [tag ...]
The run folder must hold <expert_name>.mq5, its includes and <tag>.ini (written by a prepare_*.py script).
Install folder: MQL5/Experts/CodexTrendlineResearch. Writes <tag>.completed.json only if every output exists.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from analyze_price_levels import sha256
from prepare_resistance_standalone import INSTALL

INSTALL_DIR = Path(r"I:\Programs\1AMP Global (USA) MT5 Exchange-Traded Futures Only")
DATA = Path(os.environ["APPDATA"]) / "MetaQuotes" / "Terminal" / "F5855995045EF8A4C3CA7AE968872CF2"
COMMON = Path(os.environ["APPDATA"]) / "MetaQuotes" / "Terminal" / "Common" / "Files"
AGENT_LOGS = Path(os.environ["APPDATA"]) / "MetaQuotes" / "Tester" / DATA.name / "Agent-127.0.0.1-3000" / "logs"


def compile_expert(run, expert):
    target = DATA / "MQL5" / "Experts" / INSTALL
    target.mkdir(parents=True, exist_ok=True)
    for f in list(run.glob("*.mqh")) + [run / f"{expert}.mq5"]:
        shutil.copyfile(f, target / f.name)
    log = run / "compile.log"
    subprocess.run([str(INSTALL_DIR / "MetaEditor64.exe"), f"/compile:{target / (expert + '.mq5')}", f"/log:{log}"])
    text = log.read_text(encoding="utf-16", errors="replace")
    result = [x for x in text.splitlines() if "result" in x.lower()]
    print("\n".join(result))
    if not result or "0 errors, 0 warnings" not in result[-1]:
        raise RuntimeError(f"Compile failed or warned: {result}")
    shutil.copyfile(target / f"{expert}.ex5", run / f"{expert}.ex5")


def trim_log(path, expert, keep=150):
    """The day's MT5 log holds every run and a print per bar: keep this run's first and last lines."""
    lines = path.read_bytes().decode("utf-16", errors="replace").splitlines()
    starts = [i for i, x in enumerate(lines) if "testing of Experts" in x and expert in x]
    run = lines[max(starts[-1] - 25, 0):] if starts else lines
    if len(run) > 2 * keep:
        run = run[:keep] + [f"... {len(run) - 2 * keep} lines trimmed ..."] + run[-keep:]
    path.write_text("\n".join(run) + "\n", encoding="utf-8")


def run_job(run, tag, outputs, expert, inputs_files=()):
    for name in outputs:
        (COMMON / name).unlink(missing_ok=True)
    for name in inputs_files:
        shutil.copyfile(run / name, COMMON / name)
    started = time.time()
    stamp = datetime.now().strftime("%Y%m%d")
    subprocess.run([str(INSTALL_DIR / "terminal64.exe"), f"/config:{run / (tag + '.ini')}"], check=True)
    seconds = time.time() - started
    missing = [n for n in outputs if not (COMMON / n).exists()]
    for name in outputs:
        if (COMMON / name).exists():
            shutil.copyfile(COMMON / name, run / name)
    for src, dst in ((DATA / f"{tag}.htm", run / f"{tag}.htm"),
                     (DATA / "Tester" / "logs" / f"{stamp}.log", run / f"{tag}.tester.log"),
                     (AGENT_LOGS / f"{stamp}.log", run / f"{tag}.agent.log")):
        if src.exists():
            shutil.copyfile(src, dst)
            if dst.suffix == ".log":
                trim_log(dst, expert)
    if missing:
        raise RuntimeError(f"Missing outputs: {missing}")
    done = dict(tag=tag, seconds=round(seconds, 1), outputs={n: sha256(run / n) for n in outputs})
    (run / f"{tag}.completed.json").write_text(json.dumps(done, indent=2), encoding="utf-8")
    print(json.dumps(done, indent=2))


def main(run_dir, expert, *tags):
    """Compile once, then run each named job (all jobs not yet completed when none are named)."""
    run = Path(run_dir)
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    if tags:
        jobs = [j for j in manifest["jobs"] if j["tag"] in tags]
    else:
        jobs = [j for j in manifest["jobs"] if not (run / f"{j['tag']}.completed.json").exists()]
    if any((run / f"{j['tag']}.completed.json").exists() for j in jobs):
        raise RuntimeError("Job already completed; preserve it")
    compile_expert(run, expert)
    for job in jobs:
        run_job(run, job["tag"], job["outputs"], expert, job.get("inputs_files", []))


if __name__ == "__main__":
    main(*sys.argv[1:])
