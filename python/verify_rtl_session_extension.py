"""Cross-check the primary dynamic skip policies with the separate minute-by-minute EA engine."""
import numpy as np
import pandas as pd
import rtl_weekly_engine as e
from rtl_session_extension import CACHE, OUT, opportunities, replay, STATES


def main():
    all_bars = e.load_minutes(CACHE)
    frame = pd.DataFrame(all_bars)
    frame['slot'] = frame.day*48+frame.minute//30
    m = frame.groupby('slot',sort=False).agg(o=('o','first'),c=('c','last'),day=('day','first'),minute=('minute','first'))
    is_red = m.c < m.o
    m['cap'] = is_red.cumsum() - is_red.cumsum().where(~is_red).ffill().fillna(0) > 3
    m['ext'] = (m.o/m.groupby('day').o.transform('first')-1)*100
    cand = opportunities()
    lo = np.searchsorted(all_bars['date'],20151230)
    hi = np.searchsorted(all_bars['date'],20260713,side='right')
    bars = {k:v[lo:hi] for k,v in all_bars.items()}
    cutoff = e.load_cutoffs()
    times = (m.day.to_numpy().astype('datetime64[D]') + m.minute.to_numpy().astype('timedelta64[m]')).astype('datetime64[s]')
    for state in [None,*STATES]:
        x = replay(cand,2,state)
        q = x.copy()
        q['pnl'] = q.groupby('date').net.cumsum()
        q['rr'] = q.groupby('date').r.cumsum()
        q['run_after'] = np.where(q.net>0,q.wins+1,0)
        # Independent state reconstruction at every prospective submission, including unfilled setups.
        prev = np.searchsorted(q.exit.to_numpy(dtype='datetime64[s]'),times,side='right')-1
        ix = prev.clip(min=0)
        same = (prev>=0) & (times.astype('datetime64[D]')==q.exit.to_numpy(dtype='datetime64[D]')[ix])
        active = np.ones(len(m),dtype=bool) if state is None else same & (
            (q.pnl.to_numpy()[ix]>1e-6) if state=='green' else
            (q.rr.to_numpy()[ix]>=1) if state=='one_r' else (q.run_after.to_numpy()[ix]>=2))
        skip = set(m.index[m.cap]) | set(m.index[:-1][(active & (m.ext.to_numpy()>=2-1e-12))[1:]])
        native_like,_ = e.simulate_m30_ea(bars,cutoffs=cutoff,signal_skips=skip)
        y = native_like[native_like.submitted>='2016-01-01'].reset_index(drop=True)
        for a,b in [('submitted','submitted'),('entry','entry_time'),('exit','exit_time')]:
            assert np.array_equal(x[a].to_numpy(dtype='datetime64[s]'),y[b].to_numpy(dtype='datetime64[s]')), (state,a,len(x),len(y))
        assert np.allclose(x.net,2*(y.exit_price-y.fill)-1.05)
        print('Verified all trades:',state or 'extension alone',len(x),flush=True)


if __name__=='__main__':
    main()

