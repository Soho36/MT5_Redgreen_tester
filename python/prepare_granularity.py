"""Prepare the pre-recorded fixed-grid NQ intervention (2026-10-09).

Creates 15 histories / 30 MT5 jobs. Native uses the existing source; a startup
MQL script imports 14 synthetic symbols without trading or changing source data.
"""
import hashlib
import json
import shutil
from pathlib import Path

from prepare_instrument_baseline import make_ini
from prepare_signal_colour import build_source
from project_paths import PROJECT_ROOT as ROOT

RUN = ROOT / 'Reports' / 'granularity_20261009'
SOURCE = 'MNQcontDTBNT20102026_2'
SOURCE_FILE = Path(r'F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_ohlcv-1m.csv')
EXPERT = 'RTL_granularity'
IMPORTER = 'BuildNQGranularity20261009'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def importer_source(variants):
    coarse = [v for v in variants if v['k'] > 1]
    names = ','.join('"' + v['symbol'] + '"' for v in coarse)
    ks = ','.join(str(v['k']) for v in coarse)
    origins = ','.join(str(v['origin_ticks']) for v in coarse)
    return r'''#property strict
// Research data importer only. No order/trading functions.
string SOURCE="MNQcontDTBNT20102026_2";
string NAMES[]={__NAMES__};
int K[]={__KS__};
int ORIGIN[]={__ORIGINS__};
string OWNER="Codex granularity 20261009 half-up";
string PREFIX="granularity_20261009";

double Quantize(double price,int k,int origin)
{
   long u=(long)MathRound(price/0.25);
   return 0.25*(origin+k*(long)MathFloor((double)(u-origin)/k+0.5));
}


bool SameSettings(string name,int f)
{
   ENUM_SYMBOL_INFO_INTEGER ip[]={SYMBOL_DIGITS,SYMBOL_SPREAD_FLOAT,SYMBOL_TRADE_CALC_MODE,SYMBOL_CHART_MODE,SYMBOL_TRADE_STOPS_LEVEL,SYMBOL_TRADE_FREEZE_LEVEL};
   ENUM_SYMBOL_INFO_DOUBLE dp[]={SYMBOL_POINT,SYMBOL_TRADE_TICK_SIZE,SYMBOL_TRADE_CONTRACT_SIZE,SYMBOL_VOLUME_MIN,SYMBOL_VOLUME_MAX,SYMBOL_VOLUME_STEP};
   for(int i=0;i<ArraySize(ip);i++)
   {
      long a=SymbolInfoInteger(SOURCE,ip[i]),b=SymbolInfoInteger(name,ip[i]);
      FileWrite(f,name,EnumToString(ip[i]),a,b);
      if(a!=b) { Print("Copied integer setting differs ",name," ",EnumToString(ip[i])); return false; }
   }
   for(int i=0;i<ArraySize(dp);i++)
   {
      double a=SymbolInfoDouble(SOURCE,dp[i]),b=SymbolInfoDouble(name,dp[i]);
      FileWrite(f,name,EnumToString(dp[i]),a,b);
      if(MathAbs(a-b)>MathMax(0.0000000001,MathAbs(a)*0.00000001))
      { Print("Copied double setting differs ",name," ",EnumToString(dp[i])); return false; }
   }
   string a=SymbolInfoString(SOURCE,SYMBOL_CURRENCY_PROFIT),b=SymbolInfoString(name,SYMBOL_CURRENCY_PROFIT);
   FileWrite(f,name,"SYMBOL_CURRENCY_PROFIT",a,b);
   if(a!=b) { Print("Copied profit currency differs ",name); return false; }
   FileWrite(f,name,"SYMBOL_SPREAD",SymbolInfoInteger(SOURCE,SYMBOL_SPREAD),SymbolInfoInteger(name,SYMBOL_SPREAD));
   FileWrite(f,name,"SYMBOL_TRADE_TICK_VALUE_PROFIT",SymbolInfoDouble(SOURCE,SYMBOL_TRADE_TICK_VALUE_PROFIT),SymbolInfoDouble(name,SYMBOL_TRADE_TICK_VALUE_PROFIT));
   FileWrite(f,name,"SYMBOL_TRADE_TICK_VALUE_LOSS",SymbolInfoDouble(SOURCE,SYMBOL_TRADE_TICK_VALUE_LOSS),SymbolInfoDouble(name,SYMBOL_TRADE_TICK_VALUE_LOSS));
   return true;
}
void OnStart()
{
   if(!SymbolSelect(SOURCE,true)) { Print("SOURCE unavailable ",GetLastError()); return; }
   double tick=SymbolInfoDouble(SOURCE,SYMBOL_TRADE_TICK_SIZE);
   if(MathAbs(tick-0.25)>0.000001) { Print("Unexpected native tick ",tick); return; }
   int meta=FileOpen(PREFIX+"_settings.tsv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,'\t');
   if(meta==INVALID_HANDLE) { Print("Settings log open failed"); return; }
   FileWrite(meta,"symbol","property","source_value","copied_value");
   for(int v=0;v<ArraySize(NAMES);v++)
   {
      bool custom=false;
      if(SymbolExist(NAMES[v],custom))
      {
         if(!custom || SymbolInfoString(NAMES[v],SYMBOL_DESCRIPTION)!=OWNER)
         { Print("Refusing existing non-owned symbol ",NAMES[v]); return; }
      }
      else if(!CustomSymbolCreate(NAMES[v],"CodexGranularity20261009",SOURCE))
      { Print("Create failed ",NAMES[v]," ",GetLastError()); return; }
      if(!CustomSymbolSetString(NAMES[v],SYMBOL_DESCRIPTION,OWNER))
      { Print("Description failed ",GetLastError()); return; }
      if(!SameSettings(NAMES[v],meta)) { FileClose(meta); return; }
      if(MathAbs(SymbolInfoDouble(NAMES[v],SYMBOL_TRADE_TICK_SIZE)-tick)>0.000001)
      { Print("Copied tick mismatch ",NAMES[v]); return; }
   }
   FileClose(meta);
   int f=FileOpen(PREFIX+"_import.tsv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,'\t');
   if(f==INVALID_HANDLE) { Print("Diagnostic open failed ",GetLastError()); return; }
   FileWrite(f,"symbol","k","origin_ticks","year","bars","first","last","zero_m1","tick_size","contract_size","sum_open","sum_high","sum_low","sum_close");
   long total=0;
   for(int year=2010;year<=2026;year++)
   {
      datetime start=StringToTime(IntegerToString(year)+".01.01 00:00:00");
      datetime stop=StringToTime(IntegerToString(year+1)+".01.01 00:00:00")-1;
      if(year==2010) start=D'2010.06.07 00:00:00';
      if(year==2026) stop=D'2026.07.13 23:59:59';
      MqlRates raw[];
      int n=-1;
      for(int attempt=0;attempt<60;attempt++)
      {
         n=CopyRates(SOURCE,PERIOD_M1,start,stop,raw);
         if(n>0) break;
         Sleep(250);
      }
      if(n<=0) { Print("CopyRates failed ",year," ",GetLastError()); FileClose(f); return; }
      total+=n;
      long so=0,sh=0,sl=0,sc=0;
      for(int i=0;i<n;i++) { so+=(long)MathRound(raw[i].open*4); sh+=(long)MathRound(raw[i].high*4); sl+=(long)MathRound(raw[i].low*4); sc+=(long)MathRound(raw[i].close*4); }
      FileWrite(f,SOURCE,1,0,year,n,TimeToString(raw[0].time,TIME_DATE|TIME_SECONDS),TimeToString(raw[n-1].time,TIME_DATE|TIME_SECONDS),0,tick,SymbolInfoDouble(SOURCE,SYMBOL_TRADE_CONTRACT_SIZE),so,sh,sl,sc);
      for(int v=0;v<ArraySize(NAMES);v++)
      {
         MqlRates rates[];
         if(ArrayCopy(rates,raw)!=n) { Print("ArrayCopy failed"); FileClose(f); return; }
         int zeros=0;
         for(int i=0;i<n;i++)
         {
            rates[i].open=Quantize(raw[i].open,K[v],ORIGIN[v]);
            rates[i].high=Quantize(raw[i].high,K[v],ORIGIN[v]);
            rates[i].low=Quantize(raw[i].low,K[v],ORIGIN[v]);
            rates[i].close=Quantize(raw[i].close,K[v],ORIGIN[v]);
            if(rates[i].high<MathMax(rates[i].open,rates[i].close) || rates[i].low>MathMin(rates[i].open,rates[i].close))
            { Print("OHLC invalid ",NAMES[v]," ",i); FileClose(f); return; }
            if(rates[i].high==rates[i].low) zeros++;
         }
         int wrote=CustomRatesReplace(NAMES[v],start,stop,rates);
         if(wrote!=n) { Print("Import mismatch ",NAMES[v]," ",year," ",wrote,"/",n," err ",GetLastError()); FileClose(f); return; }
         FileWrite(f,NAMES[v],K[v],ORIGIN[v],year,n,TimeToString(rates[0].time,TIME_DATE|TIME_SECONDS),TimeToString(rates[n-1].time,TIME_DATE|TIME_SECONDS),zeros,SymbolInfoDouble(NAMES[v],SYMBOL_TRADE_TICK_SIZE),SymbolInfoDouble(NAMES[v],SYMBOL_TRADE_CONTRACT_SIZE),so,sh,sl,sc);
      }
      FileFlush(f);
      Print("Granularity imported year ",year," rows ",n);
   }
   FileClose(f);
   for(int v=0;v<ArraySize(NAMES);v++) SymbolSelect(NAMES[v],true);
   int done=FileOpen(PREFIX+"_import.done",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(done!=INVALID_HANDLE) { FileWriteString(done,"complete "+IntegerToString(total)+" 14\n"); FileClose(done); }
   Print("Granularity import complete ",total," source rows");
}
'''.replace('__NAMES__', names).replace('__KS__', ks).replace('__ORIGINS__', origins)


def main():
    if (RUN / 'manifest.json').exists():
        raise RuntimeError('Prepared manifest already exists; preserve frozen inputs')
    RUN.mkdir(parents=True, exist_ok=True)
    variants = []
    jobs = []
    for k in (1, 2, 4, 8):
        for origin in range(k):
            key = f'k{k}_o{origin}'
            symbol = SOURCE if k == 1 else f'G26NQk{k}o{origin}'
            variants.append(dict(key=key, symbol=symbol, k=k, origin_ticks=origin,
                                 grid_points=k * .25, origin_points=origin * .25))
            for mode, signal_mode, cap in (('rtl', 0, 3), ('control', 3, 0)):
                tag = f'gran_20261009_{key}_{mode}'
                ini = make_ini(tag, symbol).replace('RTL_runband.ex5', EXPERT + '.ex5')
                ini = ini.replace('MaxRedRun=3\n', f'MaxRedRun={cap}\nSignalMode={signal_mode}\n')
                (RUN / f'{tag}.ini').write_text(ini, encoding='utf-16')
                jobs.append(dict(tag=tag, variant=key, mode=mode, symbol=symbol,
                                 outputs=[f'runband_{tag}_1.00.csv', f'runband_{tag}_1.00_stats.csv']))
    (RUN / f'{EXPERT}.mq5').write_text(build_source(), encoding='utf-8')
    shutil.copyfile(ROOT / 'mt5' / 'experts' / 'early_closes.mqh', RUN / 'early_closes.mqh')
    (RUN / f'{IMPORTER}.mq5').write_text(importer_source(variants), encoding='utf-8')
    startup = '[Charts]\nMaxBars=10000000\n[Experts]\nEnabled=0\nAllowLiveTrading=0\nAllowDllImport=0\n[StartUp]\n' + f'Script=CodexTrendlineResearch\\{IMPORTER}\nSymbol={SOURCE}\nPeriod=M1\nShutdownTerminal=1\n'
    (RUN / 'import.ini').write_text(startup, encoding='utf-16')
    manifest = dict(experiment='granularity_20261009', expert=EXPERT, importer=IMPORTER,
                    source_symbol=SOURCE, source_file=str(SOURCE_FILE), native_tick=.25, pv=2.,
                    start='2010-06-07', end_exclusive='2026-07-14',
                    tie_rule='nearest_half_up_integer_native_ticks', variants=variants, jobs=jobs,
                    input_hashes={str(p):sha(p) for p in (SOURCE_FILE, RUN / f'{EXPERT}.mq5', RUN / f'{IMPORTER}.mq5', RUN / 'early_closes.mqh', ROOT / 'docs' / 'baseline' / 'granularity' / 'PROTOCOL.md')})
    manifest['input_hashes'].update({str(f):sha(f) for f in RUN.glob('*.ini')})
    (RUN / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Prepared {len(variants)} variants, {len(jobs)} jobs in {RUN}')


if __name__ == '__main__':
    main()




