"""Add four separate flatten-at-16:30 jobs to the running eight-job window study."""
import json
import re
import shutil
from analyze_rtl_vwap_slope import ROOT,DOC,sha
from prepare_exclude16_replay import RUN as ORIGINAL, FEATURE

RUN=ROOT/'Reports/rtl_gg_exclude16_flatten1630_20261101'
EXPERT='RTL_GG_exclude16_flatten1630_replay'
FLATTEN=r'''
// User-requested flatten at cash open (16:30 source clock); entries blocked16-17.
datetime flat_last_date=0;
int flat_log=INVALID_HANDLE;
bool FlattenOpenInit()
{
   flat_log=FileOpen("flatten_events_"+g_runTag+".tsv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,'\t');
   if(flat_log==INVALID_HANDLE) return false;
   FileWrite(flat_log,"time","positions_before","orders_before","positions_after","orders_after");
   return true;
}
void FlattenBeforeOpen()
{
   datetime now=SessionClock(TimeCurrent()),date=now-now%86400;
   if(now-date<16*3600+30*60 || flat_last_date==date) return;
   flat_last_date=date;
   int positions=PositionsTotal(),orders=OrdersTotal();
   CloseAllPositions();CancelAllOrders();
   FileWrite(flat_log,TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),positions,orders,PositionsTotal(),OrdersTotal());
}
'''


def main():
    RUN.mkdir(parents=True,exist_ok=True)
    assert not (RUN/'manifest.json').exists()
    original=json.loads((ORIGINAL/'manifest.json').read_text())
    src=(ORIGINAL/(original['expert']+'.mq5')).read_text(encoding='utf-8')
    old='void OnTick() {WindowEquitySample();StrategyOnTick();WindowEquitySample();}'
    assert src.count(old)==1
    src=src.replace(old,FLATTEN+'\nvoid OnTick() {WindowEquitySample();FlattenBeforeOpen();WindowEquitySample();StrategyOnTick();WindowEquitySample();}')
    src=src.replace('   if(!WindowEquityInit()) return INIT_FAILED;',
                    '   if(!WindowEquityInit() || !FlattenOpenInit()) return INIT_FAILED;')
    src=src.replace('   WindowEquityClose();','   WindowEquityClose();\n   if(flat_log!=INVALID_HANDLE) FileClose(flat_log);')
    # Globals/functions must precede the handlers that reference flat_log.
    src=src.replace(FLATTEN,'').replace('// ======== HELPER FUNCTIONS ========',FLATTEN+'\n// ======== HELPER FUNCTIONS ========')
    (RUN/(EXPERT+'.mq5')).write_text(src,encoding='utf-8')
    for p in ORIGINAL.glob('*.mqh'):shutil.copyfile(p,RUN/p.name)
    shutil.copyfile(ORIGINAL/FEATURE,RUN/FEATURE)
    jobs=[]
    for job in original['jobs']:
        if not job['exclude']:continue
        oldtag=job['tag'];tag=oldtag.replace('_skip','_flat1630')
        text=(ORIGINAL/(oldtag+'.ini')).read_text(encoding='utf-16')
        text=text.replace(oldtag,tag).replace(original['expert']+'.ex5',EXPERT+'.ex5')
        (RUN/(tag+'.ini')).write_text(text,encoding='utf-16')
        outputs=[n.replace(oldtag,tag) for n in job['outputs']]+[f'flatten_events_{tag}.tsv']
        jobs.append(dict(job,tag=tag,flatten=True,outputs=outputs))
    manifest=dict(expert=EXPERT,protocol_sha256=sha(DOC/'EXCLUDE_1630_FLATTEN_AMENDMENT.md'),jobs=jobs,
                  prepared_sha256={p.name:sha(p) for p in RUN.iterdir() if p.is_file()})
    (RUN/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Prepared four additional flatten jobs')


if __name__=='__main__':main()
