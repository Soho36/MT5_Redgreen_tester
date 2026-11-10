"""Prepare four isolated native RTL half-hour exclusion jobs."""
import json
import re
import shutil
from analyze_rtl_vwap_slope import ROOT, sha

RUN = ROOT / 'Reports/rtl_open_halves_20261111'
OLD = ROOT / 'Reports/rtl_gg_exclude16_20261101'
DOC = ROOT / 'docs/baseline/rtl-open-halves'
EXPERT = 'RTL_open_halves_20261111'
FEATURE = 'rtl_vwap_replay_20261026_features.csv'


def main():
    RUN.mkdir(parents=True, exist_ok=True)
    assert not (RUN / 'manifest.json').exists(), 'Preserve prepared study'
    source = OLD / 'RTL_GG_exclude16_replay.mq5'
    src = source.read_text(encoding='utf-8')
    old = 'input bool W1600W1700 = false;'
    assert src.count(old) == 1
    src = src.replace(old, 'input bool SkipPreOpenHalf = false;\ninput bool SkipPostOpenHalf = false;\n' + old)
    old = '   return windows[slot];'
    assert src.count(old) == 1
    src = src.replace(old, '''   if(totalMinutes >= 960 && totalMinutes < 990 && SkipPreOpenHalf) return false;
   if(totalMinutes >= 990 && totalMinutes < 1020 && SkipPostOpenHalf) return false;
   return windows[slot];''')
    (RUN / (EXPERT + '.mq5')).write_text(src, encoding='utf-8')
    for name in ('early_closes.mqh', 'stock_early_closes.mqh', 'rtl_session_vwap.mqh', 'window_equity_research.mqh', FEATURE):
        shutil.copyfile(OLD / name, RUN / name)
    base = (OLD / 'ex16_20261101_rtl_base_all.ini').read_text(encoding='utf-16')
    jobs = []
    for arm, pre, post in [('control', False, False), ('skip_pre', True, False), ('skip_post', False, True), ('skip_both', True, True)]:
        tag = 'openhalf_20261111_' + arm
        ini = base
        for k, v in dict(Expert='CodexResearch\\' + EXPERT + '.ex5', Report=tag + '.htm', RunTag=tag).items():
            assert len(re.findall('^' + k + '=.*$', ini, re.M)) == 1
            ini = re.sub('^' + k + '=.*$', lambda _: k + '=' + v, ini, flags=re.M)
        ini = ini.replace('[TesterInputs]', '[TesterInputs]\nSkipPreOpenHalf=' + str(pre).lower() + '\nSkipPostOpenHalf=' + str(post).lower())
        fields = re.findall(r'^input\s+\w+\s+(\w+)\s*=', src, re.M)
        given = re.findall(r'^(\w+)=', ini.split('[TesterInputs]')[1].split('[', 1)[0], re.M)
        assert sorted(fields) == sorted(given)
        (RUN / (tag + '.ini')).write_text(ini, encoding='utf-16')
        outputs = [f'rtlvwap_{tag}_1.00.csv', f'rtlvwap_{tag}_1.00_stats.csv', f'vwap_decisions_{tag}.csv', f'window_equity_{tag}.bin']
        jobs.append(dict(tag=tag, arm=arm, pre=pre, post=post, outputs=outputs, inputs_files=[FEATURE]))
    manifest = dict(expert=EXPERT, source=str(source), source_sha256=sha(source), protocol_sha256=sha(DOC / 'PROTOCOL.md'), jobs=jobs,
                    prepared_sha256={p.name: sha(p) for p in RUN.iterdir() if p.is_file()})
    (RUN / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(RUN)


if __name__ == '__main__':
    main()

