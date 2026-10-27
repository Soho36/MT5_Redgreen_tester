"""Prepare frozen RTL replay for the existing terminal's historical Tester.

The fresh portable terminal cannot start Tester without an account context.
This environment-only fallback never launches/stops a terminal, touches account
settings, or attaches an EA to a chart. Installation copies a checked tester-only
EX5 into its own named folder and the frozen features into Common Files;
importing/running the config is a separate action.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

from run_rtl_vwap_replay import (
    COMMON, EXPERT_FOLDER, RUN, SOURCE_DATA, digest, load_manifest, save_json,
)


def checked_binary():
    manifest = load_manifest()
    binary = RUN / (manifest['expert'] + '.ex5')
    compiled = json.loads((RUN / 'compile.completed.json').read_text(encoding='utf-8'))
    if digest(binary) != compiled['binary_sha256']:
        raise RuntimeError('Compiled binary differs from checked build')
    return manifest, binary


def install():
    manifest, binary = checked_binary()
    parent = (SOURCE_DATA / 'MQL5/Experts').resolve()
    folder = parent / EXPERT_FOLDER
    if folder.resolve().parent != parent:
        raise RuntimeError('Expert destination escapes dedicated folder')
    target = folder / binary.name
    if folder.exists():
        if any(p.name != binary.name for p in folder.iterdir()):
            raise RuntimeError('Dedicated folder has unexpected content; preserve and inspect')
    if target.exists() and digest(target) != digest(binary):
        raise RuntimeError('Existing destination differs; preserve and inspect')
    folder.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copyfile(binary, target)
    if digest(target) != digest(binary):
        raise RuntimeError('Installed binary hash differs')
    name = manifest['feature_common_name']
    if Path(name).name != name or not name.startswith('rtl_vwap_replay_20261026_'):
        raise RuntimeError('Unexpected shared feature name')
    feature, shared = RUN / name, COMMON / name
    if shared.exists() and digest(shared) != digest(feature):
        raise RuntimeError('Existing shared feature differs; preserve and inspect')
    if not shared.exists():
        shutil.copyfile(feature, shared)
    assert digest(shared) == digest(feature)
    save_json(RUN / 'active_tester_install.json', dict(
        source=str(binary), destination=str(target), binary_sha256=digest(binary),
        feature_name=name, feature_sha256=digest(feature),
        tester_only_guard=True, chart_attachment=False, account_settings_changed=False,
        terminal_launched=False, terminal_stopped=False,
    ))
    print('Installed checked tester-only binary: ' + str(target), flush=True)


def prepare(tag):
    manifest, binary = checked_binary()
    matches = [job for job in manifest['jobs'] if job['tag'] == tag]
    if len(matches) != 1 or not re.fullmatch(r'[A-Za-z0-9_]+', tag):
        raise ValueError('Unknown or duplicate replay tag')
    if matches[0]['gate_enabled']:
        validation = json.loads((RUN / 'baseline_validation.json').read_text(encoding='utf-8'))
        if validation.get('all_passed') is not True:
            raise RuntimeError('Gate-on requires exact baseline validation')
    for name in matches[0]['outputs']:
        if (COMMON / name).exists() or (RUN / name).exists():
            raise RuntimeError('Uncompleted output exists; preserve before rerun: ' + name)
    source = RUN / (tag + '.ini')
    text = source.read_text(encoding='utf-16')
    replacements = {
        'Expert': EXPERT_FOLDER + '\\' + binary.name,
        'ShutdownTerminal': '0',
        # MT5 accepts paths relative to its installation, not absolute paths.
        'Report': tag + '.htm',
    }
    for key, value in replacements.items():
        pattern = r'^' + key + r'=.*$'
        if len(re.findall(pattern, text, re.MULTILINE)) != 1:
            raise RuntimeError('Nonunique tester key: ' + key)
        text = re.sub(pattern, lambda _: key + '=' + value, text, flags=re.MULTILINE)
    for setting in ('ShutdownTerminal=0', 'Optimization=0', 'Model=1', 'Period=M30',
                    'Visual=0', 'UseLocal=1', 'UseRemote=0', 'UseCloud=0',
                    'Enabled=0', 'AllowLiveTrading=0', 'AllowDllImport=0'):
        if setting not in text.splitlines():
            raise RuntimeError('Missing required setting: ' + setting)
    if re.search(r'^(Password|Server|Login)=', text, re.MULTILINE):
        raise RuntimeError('Launch copy must not carry account credentials')
    destination = RUN / (tag + '.active_tester.ini')
    encoded = text.encode('utf-16')
    if destination.exists() and destination.read_bytes() != encoded:
        raise RuntimeError('Existing launch copy differs; preserve and inspect')
    if not destination.exists():
        destination.write_bytes(encoded)
    save_json(RUN / (tag + '.active_tester_prepared.json'), dict(
        tag=tag, frozen_config=str(source), frozen_config_sha256=digest(source),
        launch_config=str(destination), launch_config_sha256=digest(destination),
        binary_sha256=digest(binary), changed_settings=replacements,
        environment_deviation='Existing logged-in terminal historical Tester instead of accountless portable terminal',
        strategy_parameters_changed=False, account_credentials_copied=False,
        terminal_launched=False, terminal_stopped=False, tester_launched=False,
    ))
    print('Prepared launch copy; no terminal or tester started: ' + str(destination), flush=True)


def collect(tag):
    """Preserve finalized native history; disclose an absent optional HTML report."""
    import pandas as pd
    from run_rtl_vwap_replay import INSTALL
    manifest, binary = checked_binary()
    job = next(j for j in manifest['jobs'] if j['tag'] == tag)
    marker = RUN / (tag + '.completed.json')
    if marker.exists():
        record = json.loads(marker.read_text(encoding='utf-8'))
        for name, expected in record['outputs'].items():
            assert digest(RUN / name) == expected, name
        print('Previously collected run verified: ' + tag)
        return
    # OnTester summaries are written after complete history export. Both
    # observers must have finalized with every position closed and no errors.
    for prefix in ('path', 'vwap'):
        summary = pd.read_csv(COMMON / f'{prefix}_{tag}_summary.csv', sep='\t', encoding='utf-16').iloc[0]
        assert summary.observer_errors == 0
        if prefix == 'path':
            assert summary.active_at_end == 0 and summary.counts_match == 1 and summary.profit_match == 1
    hashes = {}
    for name in job['outputs']:
        assert tag in name and name == Path(name).name
        source, destination = COMMON / name, RUN / name
        before = digest(source)
        if destination.exists():
            assert digest(destination) == before, 'Preserve differing existing output: ' + name
        else:
            shutil.copyfile(source, destination)
        assert digest(source) == before == digest(destination), 'Output changed during collection: ' + name
        hashes[name] = before
    report = RUN / (tag + '.htm')
    for parent in (INSTALL, SOURCE_DATA):
        candidate = parent / report.name
        if candidate.exists():
            if report.exists():
                assert digest(report) == digest(candidate)
            else:
                shutil.copyfile(candidate, report)
    config = RUN / (tag + '.active_tester.ini')
    save_json(marker, dict(tag=tag, runtime='existing terminal historical Strategy Tester',
        launch_config_sha256=digest(config), expert_sha256=digest(binary), outputs=hashes,
        report_sha256=digest(report) if report.exists() else None,
        report_status='collected' if report.exists() else 'not_generated',
        execution_evidence='complete native order/deal history and independent complete path logger',
        environment_deviation='User authorized usual terminal after accountless portable runtime could not start',
        account_credentials_copied=False, live_trading_enabled=False))
    print('Collected and hashed finalized native outputs: ' + tag, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest='command', required=True)
    subcommands.add_parser('install')
    preparation = subcommands.add_parser('prepare')
    preparation.add_argument('tag')
    collection = subcommands.add_parser('collect')
    collection.add_argument('tag')
    args = parser.parse_args()
    if args.command == 'install':
        install()
    elif args.command == 'prepare':
        prepare(args.tag)
    else:
        collect(args.tag)


if __name__ == '__main__':
    main()
