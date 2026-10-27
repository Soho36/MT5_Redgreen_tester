"""Prepare two isolated, frozen-source MT5 VWAP replay jobs; do not launch MT5."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / 'Reports/rtl_vwap_replay_20261026'
BASE = ROOT / 'Reports/timeframe_baseline_20261015'
SOURCE = BASE / 'RTL_timeframe.mq5'
SOURCE_SHA = '8995d0ed6f97f21b15f4ce31f862fb8f642a1eae5a4e28c6bc371cb928165810'
INI = BASE / 'tf_20261015_rtl_m30_rr1p0.ini'
FEATURES = ROOT / 'Reports/rtl_vwap_20261025/features_full_hlc3.csv'
PROTOCOL = ROOT / 'docs/baseline/rtl-vwap/REPLAY_PROTOCOL.md'
EXPERT = 'RTL_vwap_replay'
FEATURE_NAME = 'rtl_vwap_replay_20261026_features.csv'
TAG = 'tf_20261015_rtl_m30_rr1p0'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(4*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def build_source():
    assert digest(SOURCE) == SOURCE_SHA, 'Frozen baseline changed'
    src = SOURCE.read_text(encoding='utf-8')
    edits = (
        ('// ======== HELPER FUNCTIONS ========\n', '#include "vwap_replay_path.mqh"\n#include "vwap_replay_research.mqh"\n\n// ======== HELPER FUNCTIONS ========\n'),
        ('   DisplaySettings();\n   return(INIT_SUCCEEDED);\n',
         '   DisplaySettings();\n   if(!VwapReplayInit()) return INIT_FAILED;\n   PathResearchInit();\n   if(!g_prReady) return INIT_FAILED;\n   return(INIT_SUCCEEDED);\n'),
        ('double OnTester()\n{\n', 'double OnTester()\n{\n   PathResearchFinishTester();\n   VwapReplayFinish();\n'),
        ('void OnTick()\n', 'void StrategyOnTick()\n'),
        ('   double target = g_initialEntry + g_initialRisk * RiskReward;\n',
         '   double target = g_initialEntry + g_initialRisk * RiskReward;\n   PathResearchTargetCheck(barClose, target);\n'),
        ('\t   CancelOldBuyStops();\n\n\t   double entry = h1;\n',
         '\t   CancelOldBuyStops();\n\n\t   // Original red-candidate maintenance precedes only the NEW order gate.\n\t   if(!VwapReplayCandidate(o1,h1,l1,c1)) return;\n\n\t   double entry = h1;\n'),
        ('\t   if(risk <= 0.0) return;\n', '\t   if(risk <= 0.0) { VwapReplayLogCandidate(0,0,false); return; }\n'),
        ('\t   if(!OrderSend(req, res))\n', '\t   bool vwapSent=OrderSend(req, res);\n\t   VwapReplayLogCandidate(res.order,res.retcode,vwapSent);\n\t   if(!vwapSent)\n'),
        ('\t   else\n\t      Print("Buy Stop placed @", entry);\n',
         '\t   else\n\t   {\n\t      PathResearchEntryOrder(req,res);\n\t      Print("Buy Stop placed @", entry);\n\t   }\n'),
    )
    for old, new in edits:
        assert src.count(old) == 1, repr(old)
        src = src.replace(old, new)
    return src + '''\n// Passive quote/equity observers around unchanged strategy returns.
void OnTick()
{
   VwapReplaySampleEquity();
   PathResearchBeforeTick();
   StrategyOnTick();
   PathResearchAfterTick();
   VwapReplaySampleEquity();
}

void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result)
{
   VwapReplaySampleEquity();
}
'''


def feature_export():
    meta = json.loads((FEATURES.parent/'feature_provenance.json').read_text())
    assert digest(FEATURES) == meta['outputs_sha256'][FEATURES.name]
    f = pd.read_csv(FEATURES, float_precision='round_trip',
                    usecols=['available_at','feature_session','bar_time','close','vwap','a20','vwap_available'])
    for c in ('available_at','feature_session','bar_time'):
        f[c] = pd.to_datetime(f[c], format='ISO8601')
    assert f.available_at.is_unique and f.available_at.is_monotonic_increasing
    known = f.vwap_available & f.vwap.notna() & f.a20.gt(0)
    assert np.array_equal((f.close-f.vwap).div(f.a20).lt(-1).loc[known], (f.close<f.vwap-f.a20).loc[known])
    out = pd.DataFrame({name: f[source].astype('int64')//10**6
                        for name, source in [('available_epoch','available_at'),('session_epoch','feature_session'),('bar_epoch','bar_time')]})
    # Pandas datetime resolution varies; convert explicitly through NumPy seconds.
    for name, source in [('available_epoch','available_at'),('session_epoch','feature_session'),('bar_epoch','bar_time')]:
        out[name] = f[source].to_numpy(dtype='datetime64[s]').astype('int64')
    out['close'] = f.close
    out['vwap'] = f.vwap.where(known, 0)
    out['a20'] = f.a20.where(known, 0)
    out['known'] = known.astype(int)
    return out


def main():
    assert PROTOCOL.exists(), 'Freeze replay protocol first'
    RUN.mkdir(parents=True, exist_ok=True)
    assert not (RUN/'manifest.json').exists(), 'Prepared study exists; resume instead'
    source = build_source()
    path_source = ROOT/'mt5/experts/path_research.mqh'
    observer = path_source.read_text(encoding='utf-8')
    assert observer.count('SignalMode') == 1
    observer = observer.replace('SignalMode', '0 /* frozen RTL mode */')
    (RUN/'vwap_replay_path.mqh').write_text(observer, encoding='utf-8')
    (RUN/f'{EXPERT}.mq5').write_text(source, encoding='utf-8')
    shutil.copyfile(BASE/'early_closes.mqh', RUN/'early_closes.mqh')
    research = ROOT/'mt5/experts/vwap_replay_research.mqh'
    shutil.copyfile(research, RUN/research.name)
    features = feature_export()
    features.to_csv(RUN/FEATURE_NAME, sep='\t', index=False, float_format='%.17g', lineterminator='\n')
    frozen = [PROTOCOL, Path(__file__), SOURCE, INI, FEATURES, FEATURES.parent/'feature_provenance.json',
              path_source, research, BASE/'early_closes.mqh', RUN/f'{EXPERT}.mq5',
              RUN/'vwap_replay_path.mqh', RUN/'early_closes.mqh', RUN/research.name, RUN/FEATURE_NAME]
    jobs = []
    for gate in (False, True):
        variant = 'on' if gate else 'off'
        tag = f'vwap_replay_20261026_{variant}'
        lines = INI.read_text(encoding='utf-16').splitlines()
        changes = {'Expert': f'CodexResearch\\{EXPERT}.ex5', 'RunTag': tag, 'Report': f'{tag}.htm'}
        for key, value in changes.items():
            assert sum(s.startswith(key+'=') for s in lines) == 1
            lines = [key+'='+value if s.startswith(key+'=') else s for s in lines]
        pos = lines.index('[TesterInputs]')+1
        lines[pos:pos] = [f'UseVwapReplayGate={str(gate).lower()}', f'VwapReplayFeatures={FEATURE_NAME}']
        for value in ('Model=1','Period=M30','MaxRedRun=0','FromDate=2010.06.07','ToDate=2026.10.15','AllowLiveTrading=0'):
            assert value in lines, value
        ini = RUN/f'{tag}.ini'
        ini.write_text('\n'.join(lines)+'\n', encoding='utf-16')
        frozen.append(ini)
        outputs = [f'runband_{tag}_1.00.csv',f'runband_{tag}_1.00_stats.csv']
        outputs += [f'path_{tag}_{name}.csv' for name in ('trades','bars','checks','orders','summary')]
        outputs += [f'vwap_{tag}_{name}.csv' for name in ('candidates','orders','deals','summary')]
        outputs += [f'vwap_{tag}_equity.bin']
        jobs.append(dict(tag=tag,variant=variant,gate_enabled=gate,mode='rtl',symbol='MNQcontDTBNT20102026_2',
            pv=2.,outputs=outputs,inputs_files=[FEATURE_NAME],reference_raw=str(BASE/f'runband_{TAG}_1.00.csv'),
            reference_stats=str(BASE/f'runband_{TAG}_1.00_stats.csv'),reference_report=str(BASE/f'{TAG}.htm')))
    manifest = dict(expert=EXPERT,symbol='MNQcontDTBNT20102026_2',pv=2.,feature_common_name=FEATURE_NAME,
        feature_rows=len(features),protocol=str(PROTOCOL),jobs=jobs,model='1-minute OHLC',
        start='2010-06-07',tester_end='2026-10-15',eligible_start='2016-01-01',eligible_end_exclusive='2026-10-01',
        cost_per_trade=1.05,gate='completed_close < full_session_HLC3_VWAP - arithmetic_A20',
        maintenance='original red-candidate cancellation runs before gate of NEW replacement order',
        equity_binary_dtype=[['time_msc','<i8'],['balance','<f8'],['equity','<f8']],
        input_hashes={str(p):digest(p) for p in frozen})
    (RUN/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(f'Prepared off/on jobs, {len(features):,} causal feature rows: {RUN}')


if __name__ == '__main__':
    main()
