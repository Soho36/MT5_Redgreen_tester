"""Rank the current session return against earlier sessions at the same minute."""
from pathlib import Path
import numpy as np
import pandas as pd

from rtl_session_extension import CACHE, Q24, opportunities, replay, metrics
import rtl_weekly_engine as e
from project_paths import PROJECT_ROOT

OUT = PROJECT_ROOT / 'Reports/rtl_clock_extension_20261124'
PERIODS = {'early': (20160101, 20191231), 'recent': (20200101, 20260713)}
ARMS = [('clock', 80), ('clock', 90), ('clock', 95), ('vol_clock', 90)]


def clock_table(bars):
    """All decision slots, with references drawn from all sessions (including no-trade days)."""
    date, minute, price = (bars[k] for k in ('date','minute','o'))
    dates, first, session = np.unique(date, return_index=True, return_inverse=True)
    move = (100 * (price - price[first][session]) / price[first][session]).round(10)
    step = np.diff(np.log(price), prepend=np.log(price[0])) ** 2
    step[first] = 0
    cumulative = step.cumsum()
    vol = np.sqrt(np.maximum(0, cumulative-cumulative[first][session]))
    slot = bars['day']*48 + minute//30
    decision = np.flatnonzero(np.r_[True, slot[1:]!=slot[:-1]])
    decision = decision[(date[decision]>=20160101)&(date[decision]<=20260713)]
    loc = np.full((len(dates),1440),-1,dtype=np.int32)
    loc[session,minute] = np.arange(len(price))
    assert len(np.unique(bars['day']*1440+minute))==len(price)
    parts = []
    offsets = np.arange(1,121)
    for ii in np.array_split(decision, max(1,len(decision)//1024)):
        ix = loc[session[ii,None]-offsets,minute[ii,None]]
        assert (session[ii]>=120).all()
        ok = ix>=0
        prev = move[ix]
        def rank(mask,minimum):
            count = mask.sum(axis=1)
            points = ((prev<move[ii,None]) + 0.5*(prev==move[ii,None]))
            pct = 100*(points*mask).sum(axis=1)/np.maximum(count,1)
            return np.where(count>=minimum,pct,np.nan),count
        clock,n = rank(ok & (offsets<=60),40)
        distance = np.where(ok, np.abs(vol[ix]-vol[ii,None]), np.inf)
        nearest = np.argsort(distance,axis=1,kind='stable')[:,:60]
        select = np.zeros_like(ok)
        np.put_along_axis(select,nearest,True,axis=1)
        vol_clock,nv = rank(select & ok,60)
        parts.append(pd.DataFrame(dict(slot=slot[ii],submitted=e.stamp_array(bars['day'][ii],minute[ii]),
            move_pct=move[ii],volatility=vol[ii],clock=clock,vol_clock=vol_clock,n_ref=n,n_vol_ref=nv)))
    table = pd.concat(parts,ignore_index=True)
    # Re-derive scores at a deterministic spread of decisions using isolated day slices.
    for j in np.linspace(0,len(decision)-1,120,dtype=int):
        i=decision[j]
        samples=[]
        d=session[i]
        for old in range(d,d-121,-1):
            stop=first[old+1]
            offset=np.searchsorted(minute[first[old]:stop],minute[i])
            k=first[old]+offset
            if k==stop or minute[k]!=minute[i]:
                continue
            prices=price[first[old]:k+1]
            ret=round(100*(prices[-1]-prices[0])/prices[0],10)
            rv=np.sqrt(np.square(np.diff(np.log(prices))).sum())
            if old==d:
                target,vol_target=ret,rv
                assert abs(vol_target-table.volatility.iloc[j])<1e-8
            else:
                samples.append((d-old,ret,abs(rv-vol_target)))
        for col,subset,minimum in [('clock',[x for x in samples if x[0]<=60],40),
                                   ('vol_clock',sorted(samples,key=lambda x:x[2])[:60],60)]:
            ranks=[float(x[1]<target)+.5*(x[1]==target) for x in subset]
            expected=100*np.mean(ranks) if len(ranks)>=minimum else np.nan
            assert np.isclose(table[col].iloc[j],expected,equal_nan=True), (j,col,expected,table[col].iloc[j])
    return table


def skip_path(c, measure, cutoff, state):
    # The validated replay reads its trigger from the column named extension.
    # Keep raw percentages in move_pct and require a strictly positive rally.
    scored=c.assign(extension=c[measure].where(c.move_pct>0,-1))
    return replay(scored,cutoff,state)


def weekly_contrast(x,matched):
    x=x.copy()
    if matched:
        x=x[x.prior_count>0].copy()
        x['cell']=(x.clock.ge(95).astype(int)*100+x.submitted.dt.hour.floordiv(3)*10+
                   x.prior_count.clip(upper=3))
    else:
        x['cell']=0
    weeks=x.submitted.dt.to_period('W')
    axis=pd.period_range(weeks.min(),weeks.max(),freq='W')
    cells=sorted(x.cell.unique())
    index=pd.MultiIndex.from_product([axis,cells,[False,True]])
    agg=x.groupby([weeks,x.cell,x.green]).r.agg(['sum','size']).reindex(index,fill_value=0)
    data=agg.to_numpy().reshape(len(axis),len(cells),2,2)
    def calc(blocks):
        sums,counts=blocks[...,0],blocks[...,1]
        common=counts.min(axis=-1)>0
        weight=counts.sum(axis=-1)*common
        means=sums/np.maximum(counts,1)
        total=weight.sum(axis=-1)
        return ((means[...,1]-means[...,0])*weight).sum(axis=-1)/np.maximum(total,1),total
    delta,common_n=calc(data.sum(axis=0))
    rng=np.random.default_rng(20261124)
    samples=[]
    for chunk in range(30):
        draws=rng.multinomial(len(axis),np.ones(len(axis))/len(axis),size=100)
        diff,n=calc((draws@data.reshape(len(axis),-1)).reshape(100,len(cells),2,2))
        samples.extend(diff[n>0])
    lo,hi=np.quantile(samples,[.025,.975])
    return dict(matched=matched,eligible=len(x),common_n=common_n,delta_r=delta,low=lo,high=hi)


def main():
    OUT.mkdir(exist_ok=True)
    table=clock_table(e.load_minutes(CACHE))
    c=opportunities().merge(table,on='submitted',validate='one_to_one',how='left')
    assert c.slot.notna().all() and np.allclose(c.extension,c.move_pct)
    base=replay(c)
    base['prior_count']=base.groupby('date').cumcount()
    native=pd.read_csv(Q24,parse_dates=['submission_time','entry_time','exit_time'])
    assert len(native)==len(base)==14968
    for a,b in [('submitted','submission_time'),('entry','entry_time'),('exit','exit_time')]:
        assert np.array_equal(base[a].to_numpy(dtype='datetime64[m]'),native[b].to_numpy(dtype='datetime64[m]')), a
    assert np.allclose(base.net,native.net) and np.allclose(base.r,native.net_r)
    base.to_csv(OUT/'baseline_clock.csv',index=False)
    table.to_pickle(OUT/'decisions.pkl')
    policies=[]; cells=[]; annual=[]; contrasts=[]
    for measure,cutoff in [('clock',0),*ARMS]:
        for state in [None,'green','one_r']:
            taken=skip_path(c,measure,cutoff or None,state)
            if measure=='clock' and cutoff==90:
                taken.to_csv(OUT/f'primary_{state or "all"}.csv',index=False)
            for period,(start,end) in PERIODS.items():
                b=base[base.date.between(start,end)]
                t=taken[taken.date.between(start,end)]
                key=dict(period=period,measure=measure,cutoff=cutoff,state=state or 'all')
                policies.append(dict(**key,**metrics(t),delta=t.net.sum()-b.net.sum(),
                    omitted=(~b.submitted.isin(t.submitted)).sum(),added=(~t.submitted.isin(b.submitted)).sum()))
                for year,by in b.groupby(b.submitted.dt.year):
                    ty=t[t.submitted.dt.year==year]
                    annual.append(dict(**key,year=year,delta=ty.net.sum()-by.net.sum()))
                if state is None and cutoff:
                    valid=b[b[measure].notna()]
                    rally=valid.move_pct.gt(0)&valid[measure].ge(cutoff)
                    for unusual in (False,True):
                        for green in (False,True):
                            sub=valid[(rally==unusual)&(valid.green==green)]
                            cells.append(dict(**key,unusual=unusual,green=green,**metrics(sub)))
                    if measure=='clock' and cutoff==90:
                        for matched in (False,True):
                            contrasts.append(dict(**key,**weekly_contrast(valid[rally],matched)))
    for name,records in [('policies',policies),('cells',cells),('annual',annual),('contrasts',contrasts)]:
        pd.DataFrame(records).to_csv(OUT/(name+'.csv'),index=False)
    print('Native baseline and 120 independent feature checks passed.')
    print(base[['clock','vol_clock']].isna().sum())


if __name__=='__main__':
    main()


