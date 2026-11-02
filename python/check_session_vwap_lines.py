"""Install Session_VWAP_Lines in MT5 and check it on the live contract MNQZ26.

A read-only script opens MNQZ26 charts (M30, M1, M5, H1), attaches the indicator from a template
as a user would, with the 1-minute cache removed so it must wait for its history, then saves a
screenshot and the two lines per timeframe, plus the minute and M30 bars. Separate code here
rebuilds both lines from those bars (Chicago clock from the time-zone database, not the
indicator's DST rule). Also compares M30 values with the research features for the weeks where
the research data trade the same contract (NQZ6, full-size volume, against MNQZ26's micro volume).
MT5 must be closed. Output: Reports/session_vwap_lines_20261103 (verification.json, screenshots).
"""
import json
import shutil
import subprocess

import numpy as np
import pandas as pd

from project_paths import PROJECT_ROOT as ROOT
from run_mt5_job import COMMON, DATA, INSTALL_DIR

RUN = ROOT / 'Reports' / 'session_vwap_lines_20261103'
NAME = 'Session_VWAP_Lines'
SYMBOL = 'MNQZ26'
FRAMES = {'M30': 1800, 'M1': 60, 'M5': 300, 'H1': 3600}
FEATURES = ROOT / 'Reports' / 'rtl_vwap_cross_20261027' / 'features_NQ.csv'
ROLL_TO_Z6 = pd.Timestamp('2026-09-15')   # F:\DATABENTO\MNQ_16_YEARS rolls file: NQZ6 from this date
LABELS_END = pd.Timestamp('2026-10-01')
TOLERANCE = 1e-6   # the dump prints 10 decimals

SCRIPT = r'''#property strict
// Read-only check of Session_VWAP_Lines on a live contract. No trading functions.
string SYMBOL = "MNQZ26";
string HELPER = "MNQcontDTBNT20102026_2";
ENUM_TIMEFRAMES FRAMES[4] = {PERIOD_M30, PERIOD_M1, PERIOD_M5, PERIOD_H1};
string NAMES[4] = {"M30", "M1", "M5", "H1"};

string Cell(double v) { return v >= DBL_MAX / 2 ? "" : DoubleToString(v, 10); }

void Check(int job, int meta)
{
   uint started = GetTickCount();
   long chart = ChartOpen(SYMBOL, FRAMES[job]);
   bool applied = chart != 0 && ChartApplyTemplate(chart, "session_vwap_lines_check");
   int h = INVALID_HANDLE;
   while(applied && h == INVALID_HANDLE && GetTickCount() - started < 20000)
   {
      Sleep(200);
      for(int j = 0; j < ChartIndicatorsTotal(chart, 0) && h == INVALID_HANDLE; j++)
         if(StringFind(ChartIndicatorName(chart, 0, j), "Session VWAP lines") == 0) h = ChartIndicatorGet(chart, 0, ChartIndicatorName(chart, 0, j));
   }
   datetime to = TimeCurrent() + 86400, from = to - 63 * 86400;
   int size = 0, filled = 0;
   while(h != INVALID_HANDLE && GetTickCount() - started < 120000)
   {
      Sleep(500);
      double v[];
      size = CopyBuffer(h, 0, from, to, v);
      filled = 0;
      for(int i = 0; i < size; i++) if(v[i] < DBL_MAX / 2) filled++;
      if(size > 0 && filled > size / 2) break;
   }
   double seconds = (GetTickCount() - started) / 1000.0;
   if(h != INVALID_HANDLE)
   {
      Sleep(1500);
      datetime t[];
      double v[], g[];
      int n = CopyTime(SYMBOL, FRAMES[job], from, to, t);
      if(CopyBuffer(h, 0, from, to, v) == n && CopyBuffer(h, 1, from, to, g) == n)
      {
         int f = FileOpen("lines_" + NAMES[job] + ".tsv", FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, '\t');
         FileWrite(f, "time", "vwap", "gate");
         for(int i = 0; i < n; i++) FileWrite(f, (long)t[i], Cell(v[i]), Cell(g[i]));
         FileClose(f);
      }
      ChartSetInteger(chart, CHART_AUTOSCROLL, true);
      ChartSetInteger(chart, CHART_SCALE, 2);
      ChartNavigate(chart, CHART_END, 0);
      ChartRedraw(chart);
      Sleep(1500);
      ChartScreenShot(chart, "lines_" + NAMES[job] + ".png", 1500, 800, ALIGN_RIGHT);
      Sleep(500);
   }
   FileWrite(meta, NAMES[job], (int)(h != INVALID_HANDLE), DoubleToString(seconds, 1), size, filled);
   if(chart != 0) ChartClose(chart);
}

void OnStart()
{
   SymbolSelect(SYMBOL, true);
   long helper = ChartOpen(HELPER, PERIOD_M30);
   int hh = iCustom(HELPER, PERIOD_M30, "CodexResearch\\Session_VWAP_Lines", -1.0, 0, 0, 60);
   bool saved = helper != 0 && hh != INVALID_HANDLE && ChartIndicatorAdd(helper, 0, hh)
                && ChartSaveTemplate(helper, "session_vwap_lines_check");
   if(helper != 0) ChartClose(helper);
   if(hh != INVALID_HANDLE) IndicatorRelease(hh);
   int meta = FileOpen("lines_charts.tsv", FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, '\t');
   FileWrite(meta, "frame", "added", "seconds", "bars", "filled");
   if(saved) for(int job = 0; job < 4; job++) Check(job, meta);
   FileClose(meta);

   datetime to = TimeCurrent() + 86400, from = to - 66 * 86400;
   MqlRates r[];
   int n = CopyRates(SYMBOL, PERIOD_M1, from, to, r);
   int f = FileOpen("lines_rates_m1.tsv", FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, '\t');
   FileWrite(f, "time", "high", "low", "close", "tick_volume", "real_volume");
   for(int i = 0; i < n; i++)
      FileWrite(f, (long)r[i].time, DoubleToString(r[i].high, 2), DoubleToString(r[i].low, 2), DoubleToString(r[i].close, 2),
                r[i].tick_volume, r[i].real_volume);
   FileClose(f);
   n = CopyRates(SYMBOL, PERIOD_M30, from - 7 * 86400, to, r);
   f = FileOpen("lines_rates_m30.tsv", FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, '\t');
   FileWrite(f, "time", "open", "high", "low", "close");
   for(int i = 0; i < n; i++)
      FileWrite(f, (long)r[i].time, DoubleToString(r[i].open, 2), DoubleToString(r[i].high, 2), DoubleToString(r[i].low, 2),
                DoubleToString(r[i].close, 2));
   FileClose(f);
   f = FileOpen("lines_server.tsv", FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, '\t');
   FileWrite(f, "time_current", "time_gmt", "time_trade_server", "connected", "custom");
   FileWrite(f, (long)TimeCurrent(), (long)TimeGMT(), (long)TimeTradeServer(), (int)TerminalInfoInteger(TERMINAL_CONNECTED),
             (int)SymbolInfoInteger(SYMBOL, SYMBOL_CUSTOM));
   FileClose(f);
   int done = FileOpen("lines.done", FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(done != INVALID_HANDLE) { FileWriteString(done, "done\n"); FileClose(done); }
}
'''


def compile_mq5(path):
    log = RUN / f'{path.stem}_compile.log'
    subprocess.run([str(INSTALL_DIR / 'MetaEditor64.exe'), f'/compile:{path}', f'/log:{log}'])
    result = [x for x in log.read_text(encoding='utf-16', errors='replace').splitlines() if 'result' in x.lower()]
    if not result or '0 errors, 0 warnings' not in result[-1]:
        raise RuntimeError(f'{path.name} compile failed or warned: {result}')


def run_in_mt5():
    running = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq terminal64.exe'], capture_output=True, text=True).stdout
    assert 'terminal64.exe' not in running, 'Close MT5 first'
    indicator = DATA / 'MQL5' / 'Indicators' / 'CodexResearch' / f'{NAME}.mq5'
    shutil.copyfile(ROOT / 'mt5' / 'indicators' / f'{NAME}.mq5', indicator)
    compile_mq5(indicator)
    shutil.copyfile(indicator.with_suffix('.ex5'), RUN / f'{NAME}.ex5')
    script = DATA / 'MQL5' / 'Scripts' / 'CodexResearch' / 'SessionVwapLinesCheck.mq5'
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(SCRIPT, encoding='utf-8')
    shutil.copyfile(script, RUN / script.name)
    compile_mq5(script)
    for old in COMMON.glob('lines*'):
        old.unlink()
    # A file MT5 rebuilds on demand; without it the minutes are not built when the charts open.
    cache = DATA / 'bases' / 'AMPGlobalUSA-Demo' / 'history' / SYMBOL / 'cache' / 'M1.hc'
    cache.unlink(missing_ok=True)
    ini = RUN / 'check.ini'
    ini.write_text('[Experts]\nEnabled=0\nAllowLiveTrading=0\nAllowDllImport=0\n[StartUp]\n'
                   f'Script=CodexResearch\\SessionVwapLinesCheck\nSymbol={SYMBOL}\nPeriod=M30\nShutdownTerminal=1\n', encoding='utf-16')
    subprocess.run([str(INSTALL_DIR / 'terminal64.exe'), f'/config:{ini}'], check=True, timeout=900)
    if not (COMMON / 'lines.done').exists():
        raise RuntimeError('The check script did not finish')
    for path in COMMON.glob('lines*'):
        shutil.copyfile(path, RUN / path.name)
    for frame in FRAMES:
        png = DATA / 'MQL5' / 'Files' / f'lines_{frame}.png'
        if png.exists():
            shutil.move(str(png), str(RUN / png.name))
    (DATA / 'MQL5' / 'Profiles' / 'Templates' / 'session_vwap_lines_check.tpl').unlink(missing_ok=True)


def read(name):
    return pd.read_csv(RUN / name, sep='\t', encoding='cp1252')


def session_clock(epochs):
    """UTC server seconds to the session clock, Chicago + 8 h, from the time-zone database."""
    chicago = pd.DatetimeIndex(pd.to_datetime(np.asarray(epochs), unit='s', utc=True)).tz_convert('America/Chicago').tz_localize(None)
    return chicago + pd.Timedelta(hours=8)


def expected_lines(m1, m30, bars, seconds, last_time):
    """Both lines at each chart bar's close, from the minute and M30 dumps."""
    m1 = m1.sort_values('time').reset_index(drop=True)
    day = session_clock(m1.time).normalize()
    typical = (m1.high + m1.low + m1.close) / 3.0
    assert (m1.real_volume > 0).any()
    pv, vol = typical * m1.real_volume, m1.real_volume.astype(float)
    # Auto volume: real while the session so far has any, else tick volume.
    cum_real = vol.groupby(day.to_numpy()).cumsum()
    real = pv.groupby(day.to_numpy()).cumsum() / cum_real
    tpv, tvol = typical * m1.tick_volume, m1.tick_volume.astype(float)
    tick = tpv.groupby(day.to_numpy()).cumsum() / tvol.groupby(day.to_numpy()).cumsum()
    vwap = real.where(cum_real > 0, tick).to_numpy()
    prev = m30.close.shift()
    tr = np.maximum.reduce([m30.high - m30.low, (m30.high - prev).abs(), (m30.low - prev).abs()])
    a20 = pd.Series(tr).rolling(20).mean().to_numpy()
    ends = bars.time.to_numpy() + seconds
    at = np.searchsorted(m1.time.to_numpy(), ends, side='left') - 1
    out = pd.DataFrame({'time': bars.time, 'vwap': np.where(at >= 0, vwap[np.clip(at, 0, None)], np.nan)})
    capped = np.minimum(ends, np.where(bars.time.to_numpy() == bars.time.max(), last_time, ends))
    last_m30 = np.searchsorted(m30.time.to_numpy() + 1800, capped, side='right') - 1
    out['gate'] = out.vwap - np.where(last_m30 >= 0, a20[np.clip(last_m30, 0, None)], np.nan)
    return out


def check_frame(frame, seconds, m1, m30, last_time):
    bars = read(f'lines_{frame}.tsv')
    want = expected_lines(m1, m30, bars, seconds, last_time)
    drawn = bars.vwap.notna()
    first = bars.time[drawn].min()
    # The market was live: the newest bar kept forming between the line dump and the bar dump.
    newest = bars.time == bars.time.max()
    scope = (bars.time >= first) & ~newest
    out = dict(bars=len(bars), drawn=int(drawn.sum()), gate_drawn=int(bars.gate.notna().sum()),
               first_drawn=str(pd.to_datetime(first, unit='s')), last_bar=str(pd.to_datetime(bars.time.max(), unit='s')),
               empty_after_first=int((~drawn & scope).sum()),
               max_vwap_difference=float(np.nanmax(np.abs(bars.vwap - want.vwap)[scope])),
               max_gate_difference=float(np.nanmax(np.abs(bars.gate - want.gate)[scope])),
               newest_bar_vwap_difference=float(np.abs(bars.vwap - want.vwap)[newest].iloc[0]))
    out['passed'] = bool(out['drawn'] > 0 and out['empty_after_first'] == 0
                         and max(out['max_vwap_difference'], out['max_gate_difference']) <= TOLERANCE)
    return out


def compare_research():
    lines = read('lines_M30.tsv')
    lines['bar_time'] = session_clock(lines.time)
    f = pd.read_csv(FEATURES, usecols=['bar_time', 'close', 'vwap', 'a20', 'z', 'distance'], parse_dates=['bar_time'])
    m30 = read('lines_rates_m30.tsv')
    m30['bar_time'] = session_clock(m30.time)
    m = lines.merge(f, on='bar_time', suffixes=('', '_study')).merge(m30[['bar_time', 'close']], on='bar_time', suffixes=('_study', ''))
    # Z6 from the roll date, plus 21 M30 bars so the research A20 holds no earlier contract.
    start = f.loc[f.bar_time >= ROLL_TO_Z6, 'bar_time'].iloc[21]
    m = m[(m.bar_time >= start) & (m.bar_time < LABELS_END) & m.vwap.notna() & m.gate.notna() & m.a20.gt(0) & m.z.notna()]
    m['a20_live'] = m.vwap - m.gate
    m['far_live'] = m.close < m.gate
    m['far_study'] = m.distance.eq('far_below')
    return dict(first=str(m.bar_time.min()), last=str(m.bar_time.max()), bars=len(m),
                median_abs_close_gap=float((m.close - m.close_study).abs().median()),
                median_abs_vwap_gap=float((m.vwap - m.vwap_study).abs().median()),
                max_abs_vwap_gap=float((m.vwap - m.vwap_study).abs().max()),
                median_abs_a20_gap=float((m.a20_live - m.a20).abs().median()),
                far_below_live=int(m.far_live.sum()), far_below_study=int(m.far_study.sum()),
                far_below_disagree=int((m.far_live != m.far_study).sum()))


def main():
    RUN.mkdir(parents=True, exist_ok=True)
    if not (RUN / 'lines.done').exists():
        run_in_mt5()
    m1, m30 = read('lines_rates_m1.tsv'), read('lines_rates_m30.tsv')
    server = read('lines_server.tsv').iloc[0]
    charts = read('lines_charts.tsv').set_index('frame').to_dict('index')
    out = dict(symbol=SYMBOL, server={k: int(v) for k, v in server.items()}, charts=charts,
               minutes=dict(rows=len(m1), with_real_volume=int((m1.real_volume > 0).sum()),
                            first=str(pd.to_datetime(m1.time.min(), unit='s')), last=str(pd.to_datetime(m1.time.max(), unit='s'))))
    out['server_minus_gmt_seconds'] = int(server.time_trade_server - server.time_gmt)
    out['frames'] = {frame: check_frame(frame, seconds, m1, m30, int(server.time_current)) for frame, seconds in FRAMES.items()}
    out['research_overlap'] = compare_research()
    out['indicator_log'] = []
    log = DATA / 'MQL5' / 'Logs' / f'{pd.Timestamp.now():%Y%m%d}.log'
    if log.exists():
        out['indicator_log'] = sorted({x.split('\t')[-1] for x in log.read_text(encoding='utf-16', errors='replace').splitlines()
                                       if 'Session_VWAP_Lines (MNQZ26' in x})[:10]
    out['passed'] = all(f['passed'] for f in out['frames'].values()) and all(c['added'] == 1 for c in charts.values())
    (RUN / 'verification.json').write_text(json.dumps(out, indent=2, default=str) + '\n', encoding='utf-8')
    print(json.dumps(out, indent=1, default=str))
    assert out['passed'], 'Check failed'


if __name__ == '__main__':
    main()
