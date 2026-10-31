"""Prepare/compile the separate upper-band mean-reversion short EA."""
import json
from pathlib import Path
import re
import shutil
import sys
from project_paths import PROJECT_ROOT as ROOT
from prepare_rtl_short_vwap import FEATURES
from run_rtl_vwap_replay import INSTALL,digest,hidden_process,save_json

RUN=ROOT/'Reports/rtl_short_vwap_upper_20261101'
PRIOR=ROOT/'Reports/rtl_short_vwap_lines_20261031'
PROTOCOL=ROOT/'docs/baseline/rtl-vwap/SHORT_UPPER_PROTOCOL.md'
EXPERT='RTL_short_vwap_upper'
TAG='rtlshortupper_20261101'


def build_source():
    source=(ROOT/'mt5/experts/shorts/RTL_short_vwap.cs').read_text(encoding='utf-8')
    source=source.replace('// RTL-short VWAP experiment, 2026-10-31. Green signal / sell stop.',
        '// RTL-short upper-band experiment, 2026-11-01. Green signal / sell stop; above VWAP + A20.')
    needle='input double VwapFarBelowZ = -1.0;'
    assert source.count(needle)==1
    source=source.replace(needle,'''// Offset name retained for compatibility; +1 places orange above VWAP.
input double VwapFarBelowZ = 1.0;
enum SHORT_VWAP_SIDE
{
   SHORT_BELOW_LINE = 0,  // Allow close below selected line
   SHORT_ABOVE_LINE = 1   // Allow close above selected line
};
input SHORT_VWAP_SIDE ShortVwapSide = SHORT_ABOVE_LINE;''')
    needle='bool eligible = known && close1 < cutoff;'
    assert source.count(needle)==1
    source=source.replace(needle,'bool eligible = known && (ShortVwapSide == SHORT_ABOVE_LINE ? close1 > cutoff : close1 < cutoff);')
    source=source.replace('(int)allowed, (int)VwapFilterLine);','(int)allowed, (int)VwapFilterLine, (int)ShortVwapSide);')
    source=source.replace('"eligible", "allowed", "filter_line");','"eligible", "allowed", "filter_line", "filter_side");')
    needle='|| (VwapFilterLine != VWAP_FILTER_ORANGE && VwapFilterLine != VWAP_FILTER_BLUE)) return INIT_PARAMETERS_INCORRECT;'
    assert source.count(needle)==1
    source=source.replace(needle,'''|| (VwapFilterLine != VWAP_FILTER_ORANGE && VwapFilterLine != VWAP_FILTER_BLUE)
      || (ShortVwapSide != SHORT_BELOW_LINE && ShortVwapSide != SHORT_ABOVE_LINE)) return INIT_PARAMETERS_INCORRECT;''')
    source=source.replace('// Same blue VWAP and orange VWAP + Z*A20 lines; only eligibility reverses.',
        '// Blue is VWAP; orange is VWAP + Z*A20. Choose the eligibility side explicitly.')
    source=source.replace('// Unknown cannot qualify: the long gate allows unknown, so its complement does not.',
        '// Unknown and equality cannot qualify on either side.')
    return source


def prepare():
    RUN.mkdir(exist_ok=True)
    if (RUN/'manifest.json').exists():raise RuntimeError('Preserve prepared study')
    source=build_source()
    (ROOT/f'mt5/experts/shorts/{EXPERT}.cs').write_text(source,encoding='utf-8')
    (RUN/(EXPERT+'.mq5')).write_text(source,encoding='utf-8')
    for name in ('early_closes.mqh','rtl_session_vwap.mqh'):shutil.copyfile(ROOT/'mt5/experts'/name,RUN/name)
    shutil.copyfile(PRIOR/FEATURES,RUN/FEATURES)
    template=(PRIOR/'rtlshortlines_20261031_orange.ini').read_text(encoding='utf-16').splitlines()
    jobs=[]
    for variant,z,side in [('lower',-1,0),('upper',1,1)]:
        tag=TAG+'_'+variant
        changes={'Expert':f'CodexShortVwapUpper\\{EXPERT}.ex5','Report':tag+'.htm','RunTag':tag,'VwapFarBelowZ':str(z)}
        lines=[k+'='+changes[k] if (k:=x.split('=',1)[0]) in changes else x for x in template]
        at=lines.index('[TesterInputs]')+1
        lines.insert(at,'ShortVwapSide='+str(side))
        end=next(i for i in range(at,len(lines)) if lines[i].startswith('['))
        supplied=[x.split('=',1)[0] for x in lines[at:end] if '=' in x]
        inputs=re.findall(r'^input\s+\w+\s+(\w+)\s*=',source,re.M)
        assert sorted(supplied)==sorted(inputs) and len(supplied)==len(set(supplied))
        (RUN/(tag+'.ini')).write_text('\n'.join(lines)+'\n',encoding='utf-16')
        (RUN/f'{EXPERT}_{variant}.set').write_text('\n'.join(x.split('||')[0] for x in lines[at:end] if '=' in x)+'\n',encoding='utf-16')
        jobs.append(dict(variant=variant,tag=tag,z=z,side=side,outputs=[f'runband_{tag}_1.00.csv',f'runband_{tag}_1.00_stats.csv',f'short_vwap_{tag}.csv']))
    frozen=[PROTOCOL,Path(__file__),ROOT/'mt5/experts/shorts/RTL_short_vwap.cs',ROOT/f'mt5/experts/shorts/{EXPERT}.cs',
        PRIOR/'rtlshortlines_20261031_orange.htm',PRIOR/'runband_rtlshortlines_20261031_orange_1.00.csv',
        PRIOR/'runband_rtlshortlines_20261031_orange_1.00_stats.csv']
    save_json(RUN/'manifest.json',dict(expert=EXPERT,jobs=jobs,input_hashes={str(p):digest(p) for p in frozen},
        prepared_sha256={p.name:digest(p) for p in RUN.iterdir() if p.suffix in ('.mq5','.mqh','.csv','.ini','.set')}))
    print('Prepared lower reproduction and upper-band experiment; label bytes unchanged',flush=True)


def compile():
    log=RUN/'compile.log'
    process=hidden_process([str(INSTALL/'MetaEditor64.exe'),'/compile:'+str(RUN/(EXPERT+'.mq5')),'/log:'+str(log)],timeout=180)
    result=log.read_text(encoding='utf-16',errors='replace')
    assert 'Result: 0 errors, 0 warnings' in result,result[-2000:]
    save_json(RUN/'compile.completed.json',dict(**process,binary_sha256=digest(RUN/(EXPERT+'.ex5')),
        inputs_sha256={p.name:digest(p) for p in RUN.iterdir() if p.suffix in ('.mq5','.mqh')}))
    print('Compiled upper-band EA: 0 errors, 0 warnings',flush=True)


if __name__=='__main__':{'prepare':prepare,'compile':compile}[sys.argv[1]]()
