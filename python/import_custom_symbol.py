"""Import a continuous 1-minute CSV (build_continuous.py output) as a new MT5 custom symbol.

The new symbol copies every setting of an existing research symbol (sessions, calculation mode,
currency, margin) and then sets only its own tick size and tick value. Bars are passed to a
startup MQL5 script as per-year binary files; the script writes them with CustomRatesReplace,
reads them back with CopyRates and logs per-year counts, first/last bar and price sums, which
are checked here against the CSV. No trading functions; Experts are disabled in the config.

Refuses to touch an existing symbol it did not create (description check). Close MT5 first:
an open terminal ignores /config.

Usage: import_custom_symbol.py <csv> <new_symbol> <source_symbol> <tick_size> <tick_value> <run_dir>
Example (YM priced as MYM, $0.50 per 1-point tick):
    import_custom_symbol.py F:\\DATABENTO\\YM_16_YEARS\\MT5_YM_continuous_2010-2026_ohlcv-1m.csv
        MYMcontDTBNT20102026 MNQcontDTBNT20102026_2 1.0 0.5 Reports\\ym_symbol_20261023
"""
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_price_levels import sha256
from run_mt5_job import COMMON, DATA, INSTALL_DIR

SCRIPT_FOLDER = "CodexResearch"
IMPORTER = "ImportCustomSymbol"

MQL = r'''#property strict
// Research data importer only. No order/trading functions.
string NEWSYM="__NEW__";
string SOURCE="__SOURCE__";
string OWNER="__OWNER__";
string PREFIX="__PREFIX__";
double TICK_SIZE=__TICK_SIZE__;
double TICK_VALUE=__TICK_VALUE__;
int YEARS[]={__YEARS__};

void Prop(int f,string name)
{
   FileWrite(f,name,"SYMBOL_DIGITS",SymbolInfoInteger(name,SYMBOL_DIGITS));
   FileWrite(f,name,"SYMBOL_TRADE_CALC_MODE",SymbolInfoInteger(name,SYMBOL_TRADE_CALC_MODE));
   FileWrite(f,name,"SYMBOL_POINT",SymbolInfoDouble(name,SYMBOL_POINT));
   FileWrite(f,name,"SYMBOL_TRADE_TICK_SIZE",SymbolInfoDouble(name,SYMBOL_TRADE_TICK_SIZE));
   FileWrite(f,name,"SYMBOL_TRADE_TICK_VALUE",SymbolInfoDouble(name,SYMBOL_TRADE_TICK_VALUE));
   FileWrite(f,name,"SYMBOL_TRADE_CONTRACT_SIZE",SymbolInfoDouble(name,SYMBOL_TRADE_CONTRACT_SIZE));
   FileWrite(f,name,"SYMBOL_VOLUME_MIN",SymbolInfoDouble(name,SYMBOL_VOLUME_MIN));
   FileWrite(f,name,"SYMBOL_CURRENCY_PROFIT",SymbolInfoString(name,SYMBOL_CURRENCY_PROFIT));
   FileWrite(f,name,"SYMBOL_DESCRIPTION",SymbolInfoString(name,SYMBOL_DESCRIPTION));
}

void OnStart()
{
   if(!SymbolSelect(SOURCE,true)) { Print("SOURCE unavailable ",GetLastError()); return; }
   bool custom=false;
   if(SymbolExist(NEWSYM,custom))
   {
      if(!custom || SymbolInfoString(NEWSYM,SYMBOL_DESCRIPTION)!=OWNER)
      { Print("Refusing existing non-owned symbol ",NEWSYM); return; }
   }
   else if(!CustomSymbolCreate(NEWSYM,"CodexInstruments",SOURCE))
   { Print("Create failed ",NEWSYM," ",GetLastError()); return; }
   if(!CustomSymbolSetString(NEWSYM,SYMBOL_DESCRIPTION,OWNER)
      || !CustomSymbolSetDouble(NEWSYM,SYMBOL_TRADE_TICK_SIZE,TICK_SIZE)
      || !CustomSymbolSetDouble(NEWSYM,SYMBOL_TRADE_TICK_VALUE,TICK_VALUE))
   { Print("Setting failed ",GetLastError()); return; }
   int meta=FileOpen(PREFIX+"_settings.tsv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,'\t');
   if(meta==INVALID_HANDLE) { Print("Settings log open failed"); return; }
   FileWrite(meta,"symbol","property","value");
   Prop(meta,SOURCE);
   Prop(meta,NEWSYM);
   FileClose(meta);

   int f=FileOpen(PREFIX+"_import.tsv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,'\t');
   if(f==INVALID_HANDLE) { Print("Diagnostic open failed ",GetLastError()); return; }
   FileWrite(f,"year","wrote","read","first","last","sum_open","sum_high","sum_low","sum_close");
   long total=0;
   for(int k=0;k<ArraySize(YEARS);k++)
   {
      int year=YEARS[k];
      int h=FileOpen(PREFIX+"_"+IntegerToString(year)+".bin",FILE_READ|FILE_BIN|FILE_COMMON);
      if(h==INVALID_HANDLE) { Print("Bin open failed ",year," ",GetLastError()); FileClose(f); return; }
      double v[];
      int m=(int)FileReadArray(h,v);
      FileClose(h);
      if(m<=0 || m%6!=0) { Print("Bad bin size ",year," ",m); FileClose(f); return; }
      int n=m/6;
      MqlRates rates[];
      ArrayResize(rates,n);
      for(int i=0;i<n;i++)
      {
         rates[i].time=(datetime)(long)v[6*i];
         rates[i].open=v[6*i+1]; rates[i].high=v[6*i+2]; rates[i].low=v[6*i+3]; rates[i].close=v[6*i+4];
         rates[i].tick_volume=(long)v[6*i+5]; rates[i].real_volume=(long)v[6*i+5]; rates[i].spread=1;
      }
      datetime start=StringToTime(IntegerToString(year)+".01.01 00:00:00");
      datetime stop=StringToTime(IntegerToString(year+1)+".01.01 00:00:00")-1;
      int wrote=CustomRatesReplace(NEWSYM,start,stop,rates);
      if(wrote!=n) { Print("Import mismatch ",year," ",wrote,"/",n," err ",GetLastError()); FileClose(f); return; }
      MqlRates back[];
      int got=-1;
      for(int attempt=0;attempt<120;attempt++)
      {
         got=CopyRates(NEWSYM,PERIOD_M1,start,stop,back);
         if(got==n) break;
         Sleep(250);
      }
      if(got<=0) { Print("CopyRates failed ",year," ",GetLastError()); FileClose(f); return; }
      long so=0,sh=0,sl=0,sc=0;
      for(int i=0;i<got;i++)
      { so+=(long)MathRound(back[i].open*100); sh+=(long)MathRound(back[i].high*100);
        sl+=(long)MathRound(back[i].low*100); sc+=(long)MathRound(back[i].close*100); }
      FileWrite(f,year,wrote,got,TimeToString(back[0].time,TIME_DATE|TIME_SECONDS),
                TimeToString(back[got-1].time,TIME_DATE|TIME_SECONDS),so,sh,sl,sc);
      FileFlush(f);
      total+=got;
      Print("Imported ",NEWSYM," year ",year," rows ",got);
   }
   FileClose(f);
   SymbolSelect(NEWSYM,true);
   int done=FileOpen(PREFIX+"_import.done",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(done!=INVALID_HANDLE) { FileWriteString(done,"complete "+IntegerToString(total)+"\n"); FileClose(done); }
   Print("Import complete ",total," rows");
}
'''


def load_csv(path):
    d = pd.read_csv(path, sep="\t")
    ts = pd.to_datetime(d["<DATE>"] + " " + d["<TIME>"], format="%Y.%m.%d %H:%M:%S")
    return pd.DataFrame({"t": (ts - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1), "year": ts.dt.year,
                         "stamp": ts.dt.strftime("%Y.%m.%d %H:%M:%S"),
                         "open": d["<OPEN>"], "high": d["<HIGH>"], "low": d["<LOW>"], "close": d["<CLOSE>"],
                         "vol": d["<VOL>"]})


def main(csv, new_symbol, source_symbol, tick_size, tick_value, run_dir, price_scale=100):
    run = Path(run_dir)
    run.mkdir(parents=True, exist_ok=True)
    prefix = f"import_{new_symbol}"
    owner = f"Codex import of {Path(csv).name}"
    bars = load_csv(csv)
    expected = {}
    for year, g in bars.groupby("year"):
        arr = g[["t", "open", "high", "low", "close", "vol"]].to_numpy(dtype=np.float64)
        arr.tofile(COMMON / f"{prefix}_{year}.bin")
        expected[int(year)] = dict(rows=len(g), first=g.stamp.iloc[0], last=g.stamp.iloc[-1],
                                   **{f"sum_{c}": int((g[c] * price_scale).round().astype("int64").sum())
                                      for c in ("open", "high", "low", "close")})
    src = (MQL.replace("__NEW__", new_symbol).replace("__SOURCE__", source_symbol).replace("__OWNER__", owner)
           .replace("__PREFIX__", prefix).replace("__TICK_SIZE__", repr(float(tick_size)))
           .replace("__TICK_VALUE__", repr(float(tick_value))).replace("__YEARS__", ",".join(map(str, expected))))
    (run / f"{IMPORTER}.mq5").write_text(src, encoding="utf-8")
    target = DATA / "MQL5" / "Scripts" / SCRIPT_FOLDER
    target.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(run / f"{IMPORTER}.mq5", target / f"{IMPORTER}.mq5")
    log = run / "import_compile.log"
    subprocess.run([str(INSTALL_DIR / "MetaEditor64.exe"), f"/compile:{target / (IMPORTER + '.mq5')}", f"/log:{log}"])
    result = [x for x in log.read_text(encoding="utf-16", errors="replace").splitlines() if "result" in x.lower()]
    if not result or "0 errors, 0 warnings" not in result[-1]:
        raise RuntimeError(f"Importer compile failed or warned: {result}")
    ini = run / "import.ini"
    ini.write_text("[Charts]\nMaxBars=10000000\n[Experts]\nEnabled=0\nAllowLiveTrading=0\nAllowDllImport=0\n"
                   f"[StartUp]\nScript={SCRIPT_FOLDER}\\{IMPORTER}\nSymbol={source_symbol}\nPeriod=M1\n"
                   "ShutdownTerminal=1\n", encoding="utf-16")
    for name in ("_import.done", "_import.tsv", "_settings.tsv"):
        (COMMON / f"{prefix}{name}").unlink(missing_ok=True)
    started = time.time()
    stamp = datetime.now().strftime("%Y%m%d")
    subprocess.run([str(INSTALL_DIR / "terminal64.exe"), f"/config:{ini}"], check=True, timeout=1800)
    terminal_log = DATA / "logs" / f"{stamp}.log"
    if terminal_log.exists():
        lines = terminal_log.read_text(encoding="utf-16", errors="replace").splitlines()
        (run / "import_terminal.log").write_text("\n".join(lines[-200:]), encoding="utf-8")
    done = COMMON / f"{prefix}_import.done"
    if not done.exists():
        raise RuntimeError("Import did not complete; inspect import_terminal.log")
    for name in ("_import.tsv", "_settings.tsv"):
        shutil.copyfile(COMMON / f"{prefix}{name}", run / f"{prefix}{name}")
    got = pd.read_csv(run / f"{prefix}_import.tsv", sep="\t")
    for _, row in got.iterrows():
        e = expected[int(row.year)]
        checks = [row.wrote == e["rows"], row.read == e["rows"], row["first"] == e["first"], row["last"] == e["last"]]
        checks += [int(row[f"sum_{c}"]) == e[f"sum_{c}"] for c in ("open", "high", "low", "close")]
        if not all(checks):
            raise RuntimeError(f"Read-back differs from CSV in {int(row.year)}: {row.to_dict()} vs {e}")
    if sorted(got.year) != sorted(expected):
        raise RuntimeError("Not every year was imported")
    for year in expected:
        (COMMON / f"{prefix}_{year}.bin").unlink(missing_ok=True)
    status = dict(symbol=new_symbol, source_symbol=source_symbol, tick_size=float(tick_size),
                  tick_value=float(tick_value), csv=str(csv), csv_sha256=sha256(Path(csv)), rows=len(bars),
                  seconds=round(time.time() - started, 1), years=expected)
    (run / "import.completed.json").write_text(json.dumps(status, indent=1), encoding="utf-8")
    print(f"PASS: {new_symbol} holds all {len(bars):,} CSV bars; per-year counts, spans and price sums match")
    print((run / f"{prefix}_settings.tsv").read_text())


if __name__ == "__main__":
    main(*sys.argv[1:])
