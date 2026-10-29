"""Import the prepared stock CSVs into the research MT5, with exact bar read-back.

Uses the existing custom-symbol importer and its ownership guard. No trading code.
Run with MT5 closed. Source CSVs and their manifest are never modified.
"""
import json
import shutil
from pathlib import Path

import pandas as pd

import import_custom_symbol as imp
from analyze_price_levels import sha256

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path(r"F:\DATABENTO\STOCKS\MT5")
RUN = ROOT / "Reports/stock_import_20261029"
TEMPLATE = "MNQcontDTBNT20102026_2"


def stock_mql():
    source = imp.MQL
    anchor = '   int meta=FileOpen('
    settings = '''   // Stock units are shares; prices are split-adjusted to six decimals.
   if(!CustomSymbolSetInteger(NEWSYM,SYMBOL_DIGITS,6)
      || !CustomSymbolSetInteger(NEWSYM,SYMBOL_TRADE_CALC_MODE,SYMBOL_CALC_MODE_EXCH_STOCKS)
      || !CustomSymbolSetDouble(NEWSYM,SYMBOL_POINT,0.000001)
      || !CustomSymbolSetDouble(NEWSYM,SYMBOL_TRADE_TICK_SIZE,0.000001)
      || !CustomSymbolSetDouble(NEWSYM,SYMBOL_TRADE_TICK_VALUE,0.000001)
      || !CustomSymbolSetDouble(NEWSYM,SYMBOL_TRADE_CONTRACT_SIZE,1.0)
      || !CustomSymbolSetDouble(NEWSYM,SYMBOL_VOLUME_MIN,0.01)
      || !CustomSymbolSetDouble(NEWSYM,SYMBOL_VOLUME_STEP,0.01)
      || !CustomSymbolSetDouble(NEWSYM,SYMBOL_VOLUME_MAX,1000000.0)
      || !CustomSymbolSetDouble(NEWSYM,SYMBOL_VOLUME_LIMIT,0.0)
      || !CustomSymbolSetDouble(NEWSYM,SYMBOL_MARGIN_INITIAL,0.0)
      || !CustomSymbolSetDouble(NEWSYM,SYMBOL_MARGIN_MAINTENANCE,0.0)
      || !CustomSymbolSetString(NEWSYM,SYMBOL_CURRENCY_BASE,"USD")
      || !CustomSymbolSetString(NEWSYM,SYMBOL_CURRENCY_PROFIT,"USD")
      || !CustomSymbolSetString(NEWSYM,SYMBOL_CURRENCY_MARGIN,"USD"))
   { Print("Stock setting failed ",GetLastError()); return; }
'''
    assert source.count(anchor) == 1
    source = source.replace(anchor, settings + anchor)
    source = source.replace('   long so=0,sh=0,sl=0,sc=0;', '''   if(got!=n) { Print("Read count differs ",year); FileClose(f); return; }
      for(int i=0;i<n;i++)
      {
         if(back[i].time!=rates[i].time
            || MathAbs(back[i].open-rates[i].open)>0.0000001
            || MathAbs(back[i].high-rates[i].high)>0.0000001
            || MathAbs(back[i].low-rates[i].low)>0.0000001
            || MathAbs(back[i].close-rates[i].close)>0.0000001
            || back[i].tick_volume!=rates[i].tick_volume
            || back[i].real_volume!=rates[i].real_volume
            || back[i].spread!=rates[i].spread)
         { Print("Exact bar mismatch ",year," row ",i); FileClose(f); return; }
      }
      long so=0,sh=0,sl=0,sc=0;''')
    source = source.replace('   FileWrite(f,name,"SYMBOL_VOLUME_MIN",SymbolInfoDouble(name,SYMBOL_VOLUME_MIN));', '''   FileWrite(f,name,"SYMBOL_VOLUME_MIN",SymbolInfoDouble(name,SYMBOL_VOLUME_MIN));
   FileWrite(f,name,"SYMBOL_VOLUME_STEP",SymbolInfoDouble(name,SYMBOL_VOLUME_STEP));
   FileWrite(f,name,"SYMBOL_MARGIN_INITIAL",SymbolInfoDouble(name,SYMBOL_MARGIN_INITIAL));
   FileWrite(f,name,"SYMBOL_MARGIN_MAINTENANCE",SymbolInfoDouble(name,SYMBOL_MARGIN_MAINTENANCE));
   FileWrite(f,name,"SYMBOL_CURRENCY_MARGIN",SymbolInfoString(name,SYMBOL_CURRENCY_MARGIN));''')
    # At six decimal places, a binary float can straddle a half-cent. Exact bar
    # comparison above is authoritative; use full precision for aggregate checks.
    source = source.replace('*100)', '*1000000)')
    return source


def main():
    manifest = json.loads((SOURCE / 'manifest.json').read_text())
    RUN.mkdir(parents=True, exist_ok=True)
    imp.IMPORTER = "ImportStockSymbol"
    imp.MQL = stock_mql()
    expected_settings = {
        'SYMBOL_DIGITS': 6, 'SYMBOL_TRADE_CALC_MODE': 32,
        'SYMBOL_POINT': 0.000001, 'SYMBOL_TRADE_TICK_SIZE': 0.000001,
        'SYMBOL_TRADE_TICK_VALUE': 0.000001, 'SYMBOL_TRADE_CONTRACT_SIZE': 1,
        'SYMBOL_VOLUME_MIN': 0.01, 'SYMBOL_VOLUME_STEP': 0.01,
        'SYMBOL_MARGIN_INITIAL': 0, 'SYMBOL_MARGIN_MAINTENANCE': 0,
    }
    completed = []
    for stock, entry in manifest['stocks'].items():
        csv = SOURCE / entry['file']
        assert sha256(csv) == entry['sha256'], f"CSV hash mismatch: {stock}"
        symbol = stock + '_XNAS'
        folder = RUN / symbol
        print(f'IMPORTING {symbol}', flush=True)
        imp.main(str(csv), symbol, TEMPLATE, '0.000001', '0.000001', str(folder), price_scale=1_000_000)
        status = json.loads((folder / 'import.completed.json').read_text())
        assert status['rows'] == entry['rows'], stock
        props = pd.read_csv(folder / f'import_{symbol}_settings.tsv', sep='\t')
        props = props.loc[props.symbol.eq(symbol)].set_index('property').value.to_dict()
        for prop, value in expected_settings.items():
            assert abs(float(props[prop]) - value) < 1e-12, (stock, prop, props[prop])
        assert props['SYMBOL_CURRENCY_PROFIT'] == props['SYMBOL_CURRENCY_MARGIN'] == 'USD'
        labels = SOURCE / entry['vwap_labels']['file']
        assert sha256(labels) == entry['vwap_labels']['sha256']
        target = imp.COMMON / labels.name
        if not target.exists() or sha256(target) != sha256(labels):
            shutil.copyfile(labels, target)
        completed.append(dict(symbol=symbol, rows=status['rows'], csv_sha256=status['csv_sha256'],
                              exact_bar_readback=True, labels=labels.name))
        (RUN / 'completed.json').write_text(json.dumps(completed, indent=2))
        print(f'VERIFIED {symbol}: {status["rows"]:,} bars and stock settings', flush=True)
    print(f'ALL VERIFIED: {len(completed)} symbols, {sum(x["rows"] for x in completed):,} bars', flush=True)


if __name__ == '__main__':
    main()
