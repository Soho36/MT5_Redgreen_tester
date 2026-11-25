"""Session extension × achieved P&L. See docs/baseline/rtl-session-extension/PROTOCOL.md."""
from pathlib import Path
import numpy as np
import pandas as pd
import rtl_weekly_engine as e
from project_paths import PROJECT_ROOT

OUT = PROJECT_ROOT / 'Reports/rtl_session_extension_20261124'
CACHE = PROJECT_ROOT / 'Reports/rtl_weekly_flatten_20261027/minutes.npz'
Q24 = PROJECT_ROOT / 'Reports/trade_streaks_20261007/trades.csv'
STATES = ('green', 'one_r', 'two_wins')


def opportunities():
    """Price each eligible order independently. Later replay resolves position blocking."""
    bars = e.load_minutes(CACHE)
    day, minute = bars['day'], bars['minute']
    o, h, l, c = [bars[key] for key in 'ohlc']
    low_first = e.low_first(o, c)
    starts = np.flatnonzero(np.r_[True, np.diff(day * 48 + minute // 30) != 0])
    ends = np.r_[starts[1:], len(o)]
    high, low = np.maximum.reduceat(h, starts), np.minimum.reduceat(l, starts)
    close = c[ends - 1]
    red = close < o[starts]
    run = np.arange(len(red)) - np.maximum.accumulate(np.where(red, -1, np.arange(len(red))))
    sessions = np.flatnonzero(np.r_[True, np.diff(day[starts]) != 0])
    cuts = e.load_cutoffs()
    rows = []
    for a, b in zip(sessions, np.r_[sessions[1:], len(starts)]):
        date = bars['date'][starts[a]]
        if not 20160101 <= date <= 20260713:
            continue
        first, end = starts[a], ends[b-1]
        # Local quote indices preserve broker processing before the EA's bar-open decision.
        s = slice(first, end)
        price = np.stack([o[s], np.where(low_first[s], l[s], h[s]),
                          np.where(low_first[s], h[s], l[s]), c[s]], axis=1).ravel()
        bar_ticks = (starts[a:b] - first)*4
        cutoff_index = np.searchsorted(minute[starts[a:b]] // 30 * 30, cuts.get(date, e.CUTOFF))
        cutoff = bar_ticks[cutoff_index] if cutoff_index < len(bar_ticks) else len(price)-1
        def stamp(t):
            return e.stamp(day[first+t//4], minute[first+t//4], t%4)
        reds = np.flatnonzero(red[a-1:b-1]) if a else np.array([], dtype=int)
        for j, k in enumerate(reds):
            i = a+k-1
            submit = bar_ticks[k]
            if submit >= cutoff or run[i] > 3 or high[i] <= price[submit]:
                continue
            expiry = min(cutoff, bar_ticks[reds[j+1]] if j+1 < len(reds) else cutoff)
            hit = np.flatnonzero(price[submit+1:expiry+1] >= high[i])
            if not len(hit):
                continue
            fill = submit+1+hit[0]
            target_bars = np.flatnonzero((bar_ticks >= fill) & (bar_ticks <= cutoff) &
                                         (close[a-1:b-1] >= 2*high[i]-low[i]))
            market_exit = bar_ticks[target_bars[0]] if len(target_bars) else cutoff
            sl = np.flatnonzero(price[fill+1:market_exit+1] <= low[i])
            exit_tick = fill+1+sl[0] if len(sl) else market_exit
            exit_price = low[i] if len(sl) else price[market_exit]
            net = 2*(exit_price-high[i])-1.05
            rows.append((date, stamp(submit), stamp(fill), stamp(exit_tick), not len(sl),
                         (price[submit]-o[first])*100/o[first], net, net/(2*(high[i]-low[i]))))
    return pd.DataFrame(rows, columns=['date','submitted','entry','exit','market_exit','extension','net','r'])


def replay(candidates, threshold=None, state=None):
    records = []
    previous_day = None
    for t in candidates.itertuples(index=False):
        if t.date != previous_day:
            pnl = sum_r = wins = 0
            previous_day, busy = t.date, None
        if busy is not None and (t.submitted < busy or (consume_bar and t.submitted == busy)):
            continue
        green, one_r, two_wins = pnl > 0.000001, sum_r >= 1, wins >= 2
        if (threshold is not None or state is not None) and (threshold is None or t.extension >= threshold) and (
                state is None or dict(zip(STATES, (green, one_r, two_wins)))[state]):
            continue
        records.append((*t, green, one_r, two_wins, pnl, sum_r, wins))
        busy, consume_bar = t.exit, t.market_exit
        pnl += t.net
        sum_r += t.r
        wins = wins+1 if t.net > 0 else 0
    return pd.DataFrame(records, columns=[*candidates.columns,*STATES,'prior_net','prior_r','wins'])


def metrics(x):
    net = x.net.to_numpy()
    eq = np.r_[0, net.cumsum()]
    return dict(n=len(x), sessions=x.date.nunique(), net=net.sum(), mean_usd=x.net.mean(),
                mean_r=x.r.mean(), win_rate=(x.net>0).mean(), dd=(np.maximum.accumulate(eq)-eq).max())


def contrast(f, state):
    if not len(f) or f[state].nunique()<2:
        return {}
    week = f.submitted.dt.to_period('W')
    arrays = []
    for mask in [f[state], ~f[state]]:
        g = f[mask].groupby(week).r.agg(['sum','size']).reindex(week.unique(),fill_value=0)
        arrays.append(g.to_numpy())
    w = len(arrays[0])
    draws = np.random.default_rng(20261124).multinomial(w,np.full(w,1/w),size=3000)
    a,b = [draws@arr for arr in arrays]
    ok = (a[:,1]>0)&(b[:,1]>0)
    low,high = np.quantile(a[ok,0]/a[ok,1]-b[ok,0]/b[ok,1],[.025,.975])
    hourly = f.groupby([f.submitted.dt.hour,state]).r.agg(['mean','size']).unstack()
    overlap = hourly.dropna()
    weight = overlap['size'].sum(axis=1)
    return dict(delta_r=f.loc[f[state],'r'].mean()-f.loc[~f[state],'r'].mean(),
                low=low,high=high,matched_n=weight.sum(),
                common_hour_delta=np.average(overlap['mean'][True]-overlap['mean'][False],weights=weight) if len(overlap) else np.nan)


def main():
    OUT.mkdir(exist_ok=True)
    candidates = opportunities()
    baseline = replay(candidates)
    native = pd.read_csv(Q24,parse_dates=['submission_time','entry_time','exit_time'])
    # Native timestamps can differ within a minute under a different generated quote schedule.
    native['submitted'] = native.submission_time.dt.floor('min')
    pairs = baseline.merge(native,on='submitted',how='outer',indicator=True,suffixes=('','_mt5'),validate='one_to_one')
    issues = pairs[(pairs._merge!='both') | (abs(pairs.net-pairs.net_mt5)>1e-6) |
                   (pairs.entry.dt.floor('min')!=pairs.entry_time.dt.floor('min')) |
                   (pairs.exit.dt.floor('min')!=pairs.exit_time.dt.floor('min'))]
    issues.to_csv(OUT/'audit_differences.csv',index=False)
    print('Native / replay / differences:', len(native),len(baseline),len(issues),flush=True)
    assert issues.empty
    assert np.allclose(pairs.r,pairs.net_r) and np.array_equal(pairs.wins,pairs.session_before.clip(lower=0))
    baseline.to_csv(OUT/'baseline_states.csv',index=False)
    cells, comparisons, policies, annual = [],[],[],[]
    arms = [(None,None)] + [(t,None) for t in (1,2,3)] + [(t,s) for t in (None,1,2,3) for s in STATES]
    for threshold, state in arms:
        taken = replay(candidates,threshold,state) if threshold or state else baseline
        for period, first, last in [('early',20160101,20191231),('recent',20200101,20260713)]:
            x = taken[taken.date.between(first,last)]
            base = baseline[baseline.date.between(first,last)]
            skipped = base[~base.submitted.isin(x.submitted)]
            added = x[~x.submitted.isin(base.submitted)]
            delta = x.net.sum()-base.net.sum()
            assert np.isclose(delta,added.net.sum()-skipped.net.sum())
            key = dict(period=period,threshold=threshold or 0,state=state or 'any')
            policies.append(dict(**key,**metrics(x),delta=delta,omitted=len(skipped),added=len(added)))
            for year,b in base.groupby(base.submitted.dt.year):
                y=x[x.submitted.dt.year==year]
                annual.append(dict(**key,year=year,delta=y.net.sum()-b.net.sum()))
            if threshold and state:
                for extended in (False,True):
                    pool = base[(base.extension>=threshold)==extended]
                    comparisons.append(dict(**key,extended=extended,**contrast(pool,state)))
                    for on in (False,True):
                        cells.append(dict(**key,extended=extended,on=on,**metrics(pool[pool[state]==on])))
    for name, values in [('cells',cells),('contrasts',comparisons),('policies',policies),('annual',annual)]:
        pd.DataFrame(values).to_csv(OUT/(name+'.csv'),index=False)


if __name__ == '__main__':
    main()


