"""Check the VWAP gate EA runs prepared by prepare_rtl_vwap_ea_check.py.

1. file job: labels read from the replay's feature file. Pass = the replay ON run's candidates,
   labels, VWAP/A20 and byte-identical trades and totals.
2. bars job: VWAP computed in the tester, whose 1-minute bars carry synthetic volume. Pass = the
   same session/A20/known logic as the study, and VWAP equal to the equal-weight average of minute
   typical prices (what the tester's volume allows).
3. stored bars: StoredVwapCheck.mq5 run in the normal terminal (MT5 must be closed first) computes
   the include's VWAP and A20 for September 2026 from stored bars. Pass = the study's values.
4. indicator: IndicatorVwapCheck.mq5 reads RTL_Session_VWAP's buffers for September 2026, computed
   from stored bars and from the label file. Pass = the study's VWAP, gate line and red-x marks.
5. indicator on a fresh chart: attached from a template to a custom-symbol chart (no ticks) whose
   1-minute history is not built yet. Pass = it waits for the minutes and fills itself.
Writes verification.json in the run folder.
"""
import json
import shutil
import subprocess
from datetime import datetime

import numpy as np
import pandas as pd

import analyze_rtl_market_regimes as base
from project_paths import PROJECT_ROOT as ROOT
from run_mt5_job import COMMON, DATA, INSTALL_DIR

RUN = ROOT / 'Reports' / 'rtl_vwap_ea_20261028'
REPLAY = ROOT / 'Reports' / 'rtl_vwap_replay_20261026'
TOLERANCE = 1e-6   # the decision log prints 10 decimals


def stats(path):
    return pd.read_csv(path, sep='\t', encoding='utf-16').iloc[0]


def decisions(tag):
    return pd.read_csv(RUN / f'vwap_decisions_{tag}.csv', sep='\t', encoding='cp1252')


def features():
    f = pd.read_csv(RUN / 'rtl_vwap_replay_20261026_features.csv', sep='\t', float_precision='round_trip')
    f['bar'] = pd.to_datetime(f.bar_epoch, unit='s').dt.strftime('%Y.%m.%d %H:%M:%S')
    return f.set_index('bar')


def equal_weight_vwap():
    """Per M30 bar: plain mean of minute typical prices from the session start to the bar's close."""
    parts = []
    for raw in pd.read_csv(base.MINUTES, sep='\t', usecols=['<DATE>', '<TIME>', '<HIGH>', '<LOW>', '<CLOSE>'],
                           dtype={'<DATE>': str, '<TIME>': str}, chunksize=1_000_000):
        t = pd.to_datetime(raw['<DATE>'] + ' ' + raw['<TIME>'], format='%Y.%m.%d %H:%M:%S')
        typical = (raw['<HIGH>'] + raw['<LOW>'] + raw['<CLOSE>']) / 3.0
        parts.append(pd.DataFrame({'bar': t.dt.floor('30min'), 'tp': typical, 'n': 1})
                     .groupby('bar').agg(tp=('tp', 'sum'), n=('n', 'sum')))
    bars = pd.concat(parts).groupby(level=0).sum().sort_index()
    day = bars.index.normalize()
    out = bars.tp.groupby(day).cumsum() / bars.n.groupby(day).cumsum()
    out.index = out.index.strftime('%Y.%m.%d %H:%M:%S')
    return out


def check_file_job(f):
    new, old = decisions('vwapea_20261028_file'), pd.read_csv(REPLAY / 'candidates_on.csv')
    out = dict(candidates=dict(ea=len(new), replay=len(old)))
    assert len(new) == len(old), out
    assert (new.signal_bar.to_numpy() == old.signal_bar.to_numpy()).all(), 'signal bars differ'
    out['max_signal_close_difference'] = float(np.abs(new.signal_close - old.signal_close).max())
    for flag in ('known', 'blocked'):
        out[flag] = dict(ea=int(new[flag].sum()), replay=int(old[flag].sum()),
                         mismatches=int((new[flag].to_numpy() != old[flag].to_numpy()).sum()))
    known = old.known.eq(1).to_numpy()
    for col in ('vwap', 'a20'):
        out[f'max_{col}_difference'] = float(np.abs(new[col].to_numpy()[known] - old[col].to_numpy()[known]).max())
    tag = 'vwapea_20261028_file'
    out['trade_ledger_identical'] = ((RUN / f'rtlvwap_{tag}_1.00.csv').read_bytes()
                                     == (REPLAY / 'runband_vwap_replay_20261026_on_1.00.csv').read_bytes())
    a, b = stats(RUN / f'rtlvwap_{tag}_1.00_stats.csv'), stats(REPLAY / 'runband_vwap_replay_20261026_on_1.00_stats.csv')
    keys = ('trades', 'net_profit', 'gross_profit', 'gross_loss', 'equity_dd', 'balance_dd')
    out['tester'] = {k: dict(ea=float(a[k]), replay=float(b[k])) for k in keys}
    out['ea_counts'] = {k: int(a[k]) for k in ('vwap_candidates', 'vwap_known', 'vwap_blocked')}
    out['passed'] = bool(all(out[x]['mismatches'] == 0 for x in ('known', 'blocked'))
                         and max(out['max_signal_close_difference'], out['max_vwap_difference'],
                                 out['max_a20_difference']) <= 1e-9
                         and out['trade_ledger_identical'] and all(v['ea'] == v['replay'] for v in out['tester'].values())
                         and out['ea_counts'] == dict(vwap_candidates=len(old), vwap_known=out['known']['replay'],
                                                      vwap_blocked=out['blocked']['replay']))
    return out


def check_bars_job(f, ew):
    d = decisions('vwapea_20261028_bars')
    row = f.reindex(d.signal_bar)
    present = row.close.notna().to_numpy()   # the features end with the 23:00 bar of 2026-09-30
    same_day = d.signal_bar.str[:10].to_numpy() == d.time.str[:10].to_numpy()
    known_study = present & same_day & row.a20.gt(0).to_numpy() & row.known.eq(1).to_numpy()
    k = d.known.eq(1).to_numpy()
    assert not (k & ~present).any(), 'known label for a bar outside the features'
    ew_vwap = ew.reindex(d.signal_bar).to_numpy()
    # On the test's first session the minutes before the tester's first tick are stored bars
    # with real volume, so its VWAP mixes real and synthetic weights; every later session is
    # pure tester bars.
    first_day = d.signal_bar[k].iloc[0][:10]
    first = d.signal_bar.str[:10].le(first_day).to_numpy()
    later = k & ~first
    blocked_ew = later & (d.signal_close.to_numpy() < ew_vwap - d.a20.to_numpy())
    out = dict(candidates=len(d), known=int(k.sum()), outside_features=int((~present).sum()),
               known_mismatches_vs_study_logic=int((k != known_study).sum()),
               max_signal_close_difference=float(np.abs(d.signal_close.to_numpy()[present] - row.close.to_numpy()[present]).max()),
               max_a20_difference_vs_study=float(np.abs(d.a20.to_numpy()[k] - row.a20.to_numpy()[k]).max()),
               first_session=dict(date=first_day, known=int((k & first).sum()),
                                  max_vwap_difference_vs_equal_weight=float(np.abs(d.vwap.to_numpy()[k & first]
                                                                                   - ew_vwap[k & first]).max())),
               later_known=int(later.sum()),
               max_vwap_difference_vs_equal_weight_later=float(np.abs(d.vwap.to_numpy()[later] - ew_vwap[later]).max()),
               median_abs_gap_equal_weight_vs_real_vwap=float(np.median(np.abs(ew_vwap[k] - row.vwap.to_numpy()[k]))),
               blocked=int(d.blocked.sum()), blocked_study=int((known_study & (row.close < row.vwap - row.a20).to_numpy()).sum()),
               blocked_mismatches_vs_equal_weight_later=int((d.blocked.to_numpy()[~first] != blocked_ew[~first]).sum()))
    out['passed'] = bool(out['known_mismatches_vs_study_logic'] == 0 and out['blocked_mismatches_vs_equal_weight_later'] == 0
                         and max(out['max_signal_close_difference'], out['max_a20_difference_vs_study'],
                                 out['max_vwap_difference_vs_equal_weight_later']) <= TOLERANCE)
    return out


INDICATOR_SCRIPT = r'''#property strict
// Read-only check: RTL_Session_VWAP's buffers for September 2026, computed from stored bars and
// read from the replay's label file. No trading functions.
string SYMBOL = "MNQcontDTBNT20102026_2";
string LABELS = "rtl_vwap_replay_20261026_features.csv";

int Wait(int h)
{
   for(int k = 0; k < 480; k++) { int n = BarsCalculated(h); if(n > 0) return n; Sleep(250); }
   return -1;
}

string Cell(double v) { return v >= DBL_MAX / 2 ? "" : DoubleToString(v, 10); }

void OnStart()
{
   datetime from = StringToTime("2026.09.01 00:00"), to = StringToTime("2026.09.30 23:30");
   MqlRates r[];
   // Load the 1-minute history the indicator's default 3000 bars need: a script can wait, an
   // indicator cannot (it retries on a timer instead).
   datetime t[];
   if(CopyTime(SYMBOL, PERIOD_M30, 0, 3000, t) != 3000) { Print("short M30 history"); return; }
   datetime need = t[0] - t[0] % 86400;
   for(int a = 0; a < 240; a++)
   {
      MqlRates m1[];
      CopyRates(SYMBOL, PERIOD_M1, need, need + 3600, m1);
      if((datetime)SeriesInfoInteger(SYMBOL, PERIOD_M1, SERIES_FIRSTDATE) <= need) break;
      Sleep(250);
   }
   int hc = iCustom(SYMBOL, PERIOD_M30, "CodexResearch\\RTL_Session_VWAP", -1.0, 0, 0, 0, 3000, "");
   int hf = iCustom(SYMBOL, PERIOD_M30, "CodexResearch\\RTL_Session_VWAP", -1.0, 0, 0, 0, 3000, LABELS);
   if(hc == INVALID_HANDLE || hf == INVALID_HANDLE || Wait(hc) <= 0 || Wait(hf) <= 0) { Print("indicator unavailable ", GetLastError()); return; }
   int n = CopyRates(SYMBOL, PERIOD_M30, from, to, r);
   double vc[], gc[], mc[], vf[], gf[], mf[];
   string got = StringFormat("%d %d %d %d %d %d %d", n, CopyBuffer(hc, 0, from, to, vc), CopyBuffer(hc, 1, from, to, gc),
                             CopyBuffer(hc, 2, from, to, mc), CopyBuffer(hf, 0, from, to, vf), CopyBuffer(hf, 1, from, to, gf),
                             CopyBuffer(hf, 2, from, to, mf));
   if(ArraySize(vc) != n || ArraySize(gc) != n || ArraySize(mc) != n || ArraySize(vf) != n || ArraySize(gf) != n
      || ArraySize(mf) != n) { Print("buffer sizes differ: ", got); return; }
   int f = FileOpen("vwap_indicator_check.tsv", FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, '\t');
   if(f == INVALID_HANDLE) { Print("open failed"); return; }
   FileWrite(f, "bar", "open", "close", "vwap_c", "gate_c", "mark_c", "vwap_f", "gate_f", "mark_f");
   for(int i = 0; i < n; i++)
      FileWrite(f, TimeToString(r[i].time, TIME_DATE|TIME_SECONDS), DoubleToString(r[i].open, 2), DoubleToString(r[i].close, 2),
                Cell(vc[i]), Cell(gc[i]), Cell(mc[i]), Cell(vf[i]), Cell(gf[i]), Cell(mf[i]));
   FileClose(f);
   int done = FileOpen("vwap_indicator_check.done", FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(done != INVALID_HANDLE) { FileWriteString(done, got + "\n"); FileClose(done); }
}
'''


CHART_SCRIPT = r'''#property strict
// Read-only check: RTL_Session_VWAP attached to a freshly opened chart of a custom symbol the way a
// user attaches it (from a template), while the symbol's 1-minute history is not built yet. Charts
// of custom symbols get no ticks, so the indicator must fill itself through its timer.
// MNQcoarseDTBNT20102026 has no 1-minute cache; the template comes from a helper chart.
string SYMBOL = "MNQcoarseDTBNT20102026";
string HELPER = "MNQcontDTBNT20102026_2";

void OnStart()
{
   datetime from = StringToTime("2026.09.01 00:00"), to = StringToTime("2026.09.30 23:30");
   long helper = ChartOpen(HELPER, PERIOD_M30);
   int hh = iCustom(HELPER, PERIOD_M30, "CodexResearch\\RTL_Session_VWAP", -1.0, 0, 0, 0, 3000, "");
   bool saved = helper != 0 && hh != INVALID_HANDLE && ChartIndicatorAdd(helper, 0, hh)
                && ChartSaveTemplate(helper, "rtl_vwap_check");
   if(helper != 0) ChartClose(helper);
   if(hh != INVALID_HANDLE) IndicatorRelease(hh);
   long chart = ChartOpen(SYMBOL, PERIOD_M30);   // nothing touches its 1-minute series before the indicator
   bool applied = saved && chart != 0 && ChartApplyTemplate(chart, "rtl_vwap_check");
   int ch = INVALID_HANDLE;
   uint started = GetTickCount();
   while(applied && ch == INVALID_HANDLE && GetTickCount() - started < 15000)
   {
      Sleep(200);
      int k = ChartIndicatorsTotal(chart, 0);
      for(int j = 0; j < k && ch == INVALID_HANDLE; j++)
         if(StringFind(ChartIndicatorName(chart, 0, j), "RTL session VWAP") == 0) ch = ChartIndicatorGet(chart, 0, ChartIndicatorName(chart, 0, j));
   }
   int filled = 0, size = 0;
   while(ch != INVALID_HANDLE && GetTickCount() - started < 90000)
   {
      Sleep(500);
      double v[];
      size = CopyBuffer(ch, 0, from, to, v);
      filled = 0;
      for(int i = 0; i < size; i++) if(v[i] < DBL_MAX / 2) filled++;
      if(size > 0 && filled == size) break;
   }
   int f = FileOpen("vwap_chart_check.tsv", FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, '\t');
   if(f != INVALID_HANDLE)
   {
      FileWrite(f, "added", "seconds", "bars", "filled");
      FileWrite(f, (int)(ch != INVALID_HANDLE), DoubleToString((GetTickCount() - started) / 1000.0, 1), size, filled);
      FileClose(f);
   }
   if(chart != 0) ChartClose(chart);
   int done = FileOpen("vwap_chart_check.done", FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(done != INVALID_HANDLE) { FileWriteString(done, "done\n"); FileClose(done); }
}
'''


def check_indicator_chart():
    """Pass = the September 2026 bars fill on their own after the indicator had to wait for minutes.

    The symbol's 1-minute cache (a file MT5 rebuilds on demand) is removed before and after, so the
    minutes are not built when the chart opens; the test template is removed afterwards."""
    cache = DATA / 'bases' / 'Custom' / 'history' / 'MNQcoarseDTBNT20102026' / 'cache' / 'M1.hc'
    if not (RUN / 'vwap_chart_check.tsv').exists():
        (RUN / 'IndicatorChartCheck.mq5').write_text(CHART_SCRIPT, encoding='utf-8')
        log = DATA / 'MQL5' / 'Logs' / f'{datetime.now():%Y%m%d}.log'
        seen = len(log.read_text(encoding='utf-16', errors='replace').splitlines()) if log.exists() else 0
        cache.unlink(missing_ok=True)
        run_script('IndicatorChartCheck', 'vwap_chart_check')
        cache.unlink(missing_ok=True)
        (DATA / 'MQL5' / 'Profiles' / 'Templates' / 'rtl_vwap_check.tpl').unlink(missing_ok=True)
        lines = log.read_text(encoding='utf-16', errors='replace').splitlines()[seen:]
        (RUN / 'vwap_chart_check.log').write_text(
            '\n'.join(x for x in lines if 'RTL_Session_VWAP (MNQcoarseDTBNT20102026,M30)' in x) + '\n', encoding='utf-8')
    s = pd.read_csv(RUN / 'vwap_chart_check.tsv', sep='\t', encoding='cp1252').iloc[0]
    out = {k: (float(v) if k == 'seconds' else int(v)) for k, v in s.items()}
    out['indicator_log'] = [x.split('\t')[-1] for x in (RUN / 'vwap_chart_check.log').read_text(encoding='utf-8').splitlines() if x]
    out['had_to_wait_for_minutes'] = any('1-minute history' in x for x in out['indicator_log'])
    out['passed'] = bool(out['added'] == 1 and out['bars'] > 500 and out['filled'] == out['bars']
                         and out['had_to_wait_for_minutes'])
    return out


def run_script(name, output, includes=()):
    """Compile a read-only script into Scripts\\CodexResearch and run it once in the normal terminal."""
    target = DATA / 'MQL5' / 'Scripts' / 'CodexResearch'
    target.mkdir(parents=True, exist_ok=True)
    for f in (f'{name}.mq5', *includes):
        shutil.copyfile(RUN / f, target / f)
    log = RUN / f'{name}_compile.log'
    subprocess.run([str(INSTALL_DIR / 'MetaEditor64.exe'), f"/compile:{target / (name + '.mq5')}", f'/log:{log}'])
    result = [x for x in log.read_text(encoding='utf-16', errors='replace').splitlines() if 'result' in x.lower()]
    if not result or '0 errors, 0 warnings' not in result[-1]:
        raise RuntimeError(f'{name} compile failed or warned: {result}')
    for suffix in ('.tsv', '.done'):
        (COMMON / f'{output}{suffix}').unlink(missing_ok=True)
    ini = RUN / f'{name}.ini'
    ini.write_text('[Experts]\nEnabled=0\nAllowLiveTrading=0\nAllowDllImport=0\n[StartUp]\n'
                   f'Script=CodexResearch\\{name}\nSymbol=MNQcontDTBNT20102026_2\nPeriod=M30\n'
                   'ShutdownTerminal=1\n', encoding='utf-16')
    subprocess.run([str(INSTALL_DIR / 'terminal64.exe'), f'/config:{ini}'], check=True, timeout=900)
    if not (COMMON / f'{output}.done').exists():
        raise RuntimeError(f'{name} did not finish')
    shutil.copyfile(COMMON / f'{output}.tsv', RUN / f'{output}.tsv')
    shutil.copyfile(COMMON / f'{output}.done', RUN / f'{output}.done')


def check_indicator(f):
    if not (RUN / 'vwap_indicator_check.tsv').exists():
        (RUN / 'IndicatorVwapCheck.mq5').write_text(INDICATOR_SCRIPT, encoding='utf-8')
        run_script('IndicatorVwapCheck', 'vwap_indicator_check')
    s = pd.read_csv(RUN / 'vwap_indicator_check.tsv', sep='\t', encoding='cp1252')
    day = s.bar.str[:10].to_numpy()
    s['next_same_day'] = np.r_[day[1:] == day[:-1], False]
    s = s[s.bar.isin(f.index)].reset_index(drop=True)   # the features end with the 23:00 bar of 2026-09-30
    row = f.reindex(s.bar)
    gate = (row.vwap - row.a20).to_numpy()
    expect_mark = (s.close < s.open).to_numpy() & (s.close.to_numpy() < gate) & s.next_same_day.to_numpy()
    out = dict(bars=len(s), copied=(RUN / 'vwap_indicator_check.done').read_text().split())
    for mode in ('c', 'f'):
        out[mode] = dict(missing=int(s[f'vwap_{mode}'].isna().sum()),
                         max_vwap_difference=float(np.nanmax(np.abs(s[f'vwap_{mode}'].to_numpy() - row.vwap.to_numpy()))),
                         max_gate_difference=float(np.nanmax(np.abs(s[f'gate_{mode}'].to_numpy() - gate))),
                         marks=int(s[f'mark_{mode}'].notna().sum()), expected_marks=int(expect_mark.sum()),
                         mark_mismatches=int((s[f'mark_{mode}'].notna().to_numpy() != expect_mark).sum()))
    out['c']['label'], out['f']['label'] = 'computed from stored bars', 'read from the label file'
    out['passed'] = bool(len(s) > 500 and all(out[m]['missing'] == 0 and out[m]['mark_mismatches'] == 0
                                              and max(out[m]['max_vwap_difference'], out[m]['max_gate_difference']) <= TOLERANCE
                                              for m in ('c', 'f')))
    return out


def check_stored(f):
    if not (RUN / 'vwap_stored_check.tsv').exists():
        run_script('StoredVwapCheck', 'vwap_stored_check', includes=('rtl_session_vwap.mqh',))
    s = pd.read_csv(RUN / 'vwap_stored_check.tsv', sep='\t', encoding='cp1252')
    s['bar'] = s.bar + ':00'
    s = s[s.bar.isin(f.index)].reset_index(drop=True)   # the features end with the 23:00 bar of 2026-09-30
    row = f.reindex(s.bar)
    k = row.known.eq(1).to_numpy()
    out = dict(bars=len(s), first=s.bar.iloc[0], last=s.bar.iloc[-1], study_known=int(k.sum()),
               ea_vwap_ok=int(s.vwap_ok.sum()), ea_a20_ok=int(s.a20_ok.sum()),
               max_close_difference=float(np.abs(s.close.to_numpy() - row.close.to_numpy()).max()),
               max_vwap_difference=float(np.abs(s.vwap.to_numpy()[k] - row.vwap.to_numpy()[k]).max()),
               max_a20_difference=float(np.abs(s.a20.to_numpy()[k] - row.a20.to_numpy()[k]).max()),
               far_below_bars=int((row.close < row.vwap - row.a20).to_numpy()[k].sum()),
               far_below_mismatches=int(((s.close < s.vwap - s.a20).to_numpy()[k]
                                         != (row.close < row.vwap - row.a20).to_numpy()[k]).sum()))
    out['passed'] = bool(len(s) > 500 and out['study_known'] == len(s) and out['ea_vwap_ok'] == len(s)
                         and out['ea_a20_ok'] == len(s) and out['far_below_mismatches'] == 0
                         and max(out['max_close_difference'], out['max_vwap_difference'],
                                 out['max_a20_difference']) <= TOLERANCE)
    return out


def main():
    f = features()
    out = {'file_labels_vs_replay': check_file_job(f),
           'computed_in_tester': check_bars_job(f, equal_weight_vwap()),
           'computed_on_stored_bars': check_stored(f),
           'indicator': check_indicator(f),
           'indicator_on_fresh_chart': check_indicator_chart()}
    out['passed'] = all(v['passed'] for v in out.values())
    (RUN / 'verification.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
