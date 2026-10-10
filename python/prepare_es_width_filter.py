"""Prepare one frozen, full-EA ES minimum-width experiment (50 native ticks)."""
import json
import shutil
from pathlib import Path

from path_collector_source import build_source as path_source
from project_paths import PROJECT_ROOT as ROOT
from run_path_experiment import digest

RUN = ROOT / 'Reports/es_width_filter_20261011'
REFERENCE = ROOT / 'Reports/path_experiment_20261009'
EXPERT = 'RTL_width'
SYMBOL = 'MEScontDTBNT20102026'
PROTOCOL = ROOT / 'docs/baseline/es-minimum-width/PROTOCOL.md'

METADATA = r'''
// Read-only tester metadata and unit guard; no strategy state is changed.
bool WidthResearchMetadata()
{
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double tick = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   int handle = FileOpen("width_" + g_runTag + "_symbol.csv",
                         FILE_WRITE|FILE_CSV|FILE_COMMON, '\t');
   if(handle == INVALID_HANDLE) return false;
   FileWrite(handle,"symbol","point","trade_tick_size","tick_value","digits",
             "range_filter","minimum_terminal_points","maximum_terminal_points",
             "minimum_price_points","minimum_native_ticks","maximum_price_points");
   FileWrite(handle,_Symbol,DoubleToString(point,8),DoubleToString(tick,8),
             DoubleToString(tickValue,8),(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS),
             (int)UseCandleRangeFilter,MinCandleRange,MaxCandleRange,
             MinCandleRange*point,MinCandleRange*point/tick,MaxCandleRange*point);
   FileClose(handle);
   if(!MQLInfoInteger(MQL_TESTER) || MathAbs(point-0.01)>1e-9 || MathAbs(tick-0.25)>1e-9)
   {
      Print("WIDTH UNIT GUARD FAILED: expected point .01 and native tick .25");
      return false;
   }
   if(UseCandleRangeFilter && MathAbs(MinCandleRange*point-12.5)>1e-7)
   {
      Print("WIDTH MINIMUM GUARD FAILED: expected 50 native ticks");
      return false;
   }
   return true;
}
'''


def build_source():
    source = path_source()
    anchor = '   PathResearchInit();\n'
    if source.count(anchor) != 1:
        raise ValueError('Metadata init hook is not unique')
    source = source.replace(anchor, '   if(!WidthResearchMetadata()) return INIT_PARAMETERS_INCORRECT;\n'+anchor)
    return source + METADATA


def main():
    if not PROTOCOL.is_file():
        raise RuntimeError('Record the protocol before preparation')
    RUN.mkdir(parents=True, exist_ok=True)
    if (RUN/'manifest.json').exists():
        raise RuntimeError('Frozen manifest exists; resume the runner')
    old = json.loads((REFERENCE/'manifest.json').read_text(encoding='utf-8'))
    if path_source().replace('\r\n','\n') != (REFERENCE/'RTL_path.mq5').read_text(encoding='utf-8').replace('\r\n','\n'):
        raise RuntimeError('Current original strategy/observer differs from the reference')
    source = Path(old['source_files']['ES'])
    metadata_path = REFERENCE/'source_ES_metadata.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    if metadata['source_sha256'] != digest(source) or metadata['m30_sha256'] != digest(REFERENCE/'source_ES_m30.csv'):
        raise RuntimeError('ES source/cache provenance differs')
    for filename in ('source_ES_m30.csv','source_ES_metadata.json'):
        shutil.copyfile(REFERENCE/filename,RUN/filename)
    calendar = dict(trading_days=metadata['trading_days'],all_source_checks_passed=True,
                    source_sha256=metadata['source_sha256'],source_metadata={'ES':metadata})
    (RUN/'source_calendar.json').write_text(json.dumps(calendar,indent=2)+'\n',encoding='utf-8')
    (RUN/f'{EXPERT}.mq5').write_text(build_source(),encoding='utf-8')
    frozen=[PROTOCOL,Path(__file__).resolve(),ROOT/'python/run_es_width_filter.py',
            ROOT/'python/path_collector_source.py',ROOT/'python/prepare_signal_colour.py',
            ROOT/'python/run_path_experiment.py',ROOT/'python/run_mt5_job.py',
            ROOT/'python/audit_granularity_ledgers.py',ROOT/'python/analyze_instrument_baseline.py',
            ROOT/'mt5/experts/RR_r_MFE_buy-stop-entry_runband.cs',RUN/f'{EXPERT}.mq5',
            REFERENCE/'RTL_path.mq5',REFERENCE/'manifest.json',source,metadata_path,
            REFERENCE/'source_ES_m30.csv',RUN/'source_ES_m30.csv',RUN/'source_ES_metadata.json',RUN/'source_calendar.json']
    for name in ('early_closes.mqh','path_research.mqh'):
        src=ROOT/'mt5/experts'/name; dst=RUN/name
        shutil.copyfile(src,dst); frozen.extend((src,dst))
    jobs=[]
    for mode in ('rtl','control'):
        reference=next(j for j in old['jobs'] if j['instrument']=='ES' and j['mode']==mode)
        original_ini=REFERENCE/(reference['tag']+'.ini')
        base=original_ini.read_text(encoding='utf-16').splitlines()
        frozen.extend((original_ini,Path(reference['reference_raw']),Path(reference['reference_audited']),
                       Path(reference['reference_stats']),Path(reference['reference_report']),
                       REFERENCE/f"path_{reference['tag']}_trades.csv"))
        for variant in ('baseline','min50'):
            tag=f'width_20261011_{mode}_{variant}'
            replace={'Expert=':f'Expert=CodexTrendlineResearch\\{EXPERT}.ex5',
                     'Report=':f'Report={tag}.htm','RunTag=':f'RunTag={tag}'}
            if variant=='min50':
                replace.update({'UseCandleRangeFilter=':'UseCandleRangeFilter=true',
                                'MinCandleRange=':'MinCandleRange=1250',
                                'MaxCandleRange=':'MaxCandleRange=100000000'})
            lines=base.copy()
            for prefix,value in replace.items():
                if sum(x.startswith(prefix) for x in lines)!=1: raise ValueError(f'Nonunique INI key {prefix}')
                lines=[value if x.startswith(prefix) else x for x in lines]
            for key in ('Model=1','Period=M30','FromDate=2010.06.07','ToDate=2026.07.14','Optimization=0'):
                if key not in lines: raise ValueError(f'Unexpected original setting {key}')
            ini=RUN/(tag+'.ini'); ini.write_text('\n'.join(lines)+'\n',encoding='utf-16'); frozen.append(ini)
            outputs=[f'runband_{tag}_1.00.csv',f'runband_{tag}_1.00_stats.csv']
            outputs += [f'path_{tag}_{kind}.csv' for kind in ('trades','bars','checks','orders','summary')]
            outputs += [f'width_{tag}_symbol.csv']
            jobs.append(dict(tag=tag,instrument='ES',mode=mode,variant=variant,symbol=SYMBOL,pv=5.0,
                             min_ticks=50 if variant=='min50' else 0,outputs=outputs,
                             reference_raw=reference['reference_raw'],reference_audited=reference['reference_audited'],
                             reference_path=str(REFERENCE/f"path_{reference['tag']}_trades.csv")))
    unique=list(dict.fromkeys(frozen))
    manifest=dict(expert=EXPERT,symbol=SYMBOL,pv=5.,point=.01,native_tick=.25,
                  start='2010-06-07',end_exclusive='2026-07-14',protocol=str(PROTOCOL),jobs=jobs,
                  minimum_native_ticks=50,minimum_price_points=12.5,minimum_terminal_points=1250,
                  maximum_terminal_points=100000000,expected_maximum_source_width=363.,
                  periods=[['2010-15',2010,2015],['2016-19',2016,2019],['2020-26',2020,2026],['all',2010,2026]],
                  cost_per_trade=1.05,cost_sensitivities=[1.05,2.30,3.55],
                  bootstrap=dict(draws=1000,seed=20261011,unit='common ES source entry day'),
                  exclusion_dates=['2020-02-28','2020-06-30'],source_file=str(source),
                  input_hashes={str(p):digest(p) for p in unique})
    (RUN/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(f'Prepared 4 complete EA jobs; {len(unique)} frozen inputs; ES calendar {len(calendar["trading_days"])} days.',flush=True)


if __name__=='__main__':
    main()
