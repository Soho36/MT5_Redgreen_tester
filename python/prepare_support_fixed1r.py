"""Prepare an isolated, logged fixed-SL/TP reference for the Q10 amendment."""
import json
import re
import shutil

from analyze_price_levels import ROOT, sha256
from analyze_breach_reclaim import TREND, TAG

RUN = ROOT / 'Reports' / 'levels' / 'support_fixed1r_20261003'
RUN_TAG = 'support_fixed1r_20261003_all'


def main():
    RUN.mkdir(parents=True, exist_ok=True)
    if list(RUN.glob('*.completed.json')):
        raise RuntimeError('Preserve completed run; do not overwrite its source')
    source_path = TREND/'RTL_trend_rr.mq5'
    source = source_path.read_text(encoding='utf-8-sig')
    replacements = [
        ('input double RiskReward     = 1.0;', 'input double RiskReward     = 1.0;\ninput bool StudyFixedTP=true; // Q10 research only'),
        ('void ManageOpenPosition()\n{', 'void ManageOpenPosition()\n{\n   if(StudyFixedTP) return; // Attached fixed TP handles profit exits'),
        ('\t   req.sl           = stop;', '\t   req.sl           = stop;\n       if(StudyFixedTP) req.tp = NormalizeDouble(entry + risk, _Digits);')]
    for before, after in replacements:
        assert source.count(before) == 1
        source = source.replace(before, after, 1)
    expert = RUN/'RTL_support_fixed1r.mq5'
    expert.write_text(source, encoding='utf-8-sig')
    for name in ('early_closes.mqh', 'trend_rr_ledger.mqh', 'trend_rr_research.mqh'):
        shutil.copyfile(TREND/name, RUN/name)
    ini = (TREND/f'{TAG}.ini').read_text(encoding='utf-16')
    for key, value in dict(Expert=r'CodexSupportResearch\RTL_support_fixed1r.ex5', RunTag=RUN_TAG, Report=f'{RUN_TAG}.htm').items():
        ini, n = re.subn(rf'(?m)^{key}=.*$', lambda m: f'{key}={value}', ini)
        assert n == 1
    ini = ini.replace('[TesterInputs]', '[TesterInputs]\nStudyFixedTP=true')
    path = RUN/f'{RUN_TAG}.ini'
    path.write_text(ini, encoding='utf-16')
    manifest = dict(experiment='All RTL signals, fixed 1R SL and TP, full-history OHLC',
                    parent_source=str(source_path), parent_sha256=sha256(source_path), expert_sha256=sha256(expert),
                    protocol_sha256=sha256(ROOT/'docs/setups/horizontal/support-bounce-long/q10-support-interaction/PROTOCOL.md'),
                    jobs=[dict(tag=RUN_TAG, ini=str(path), csv=f'runband_{RUN_TAG}_1.00.csv',
                               report=f'{RUN_TAG}.htm', extra_csv=[f'{RUN_TAG}_signals.csv', f'{RUN_TAG}_checks.csv'])])
    (RUN/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(expert)


if __name__ == '__main__':
    main()
