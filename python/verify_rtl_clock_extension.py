"""Check primary skip paths against the independent minute-by-minute RTL engine."""
import numpy as np
import pandas as pd
import rtl_weekly_engine as e
from rtl_session_extension import CACHE
from rtl_clock_extension import OUT


def main():
    allbars=e.load_minutes(CACHE)
    frame=pd.DataFrame(allbars)
    frame['slot']=frame.day*48+frame.minute//30
    m=frame.groupby('slot',sort=False).agg(o=('o','first'),c=('c','last'),day=('day','first'),minute=('minute','first'))
    red=m.c<m.o
    cap=red.cumsum()-red.cumsum().where(~red).ffill().fillna(0)>3
    scores=pd.read_pickle(OUT/'decisions.pkl').set_index('slot').reindex(m.index)
    rally=(scores.move_pct.gt(0)&scores.clock.ge(90)).to_numpy()
    times=e.stamp_array(m.day,m.minute).astype('datetime64[s]')
    lo,hi=np.searchsorted(allbars['date'],[20151230,20260714])
    bars={k:v[lo:hi] for k,v in allbars.items()}
    for state in ['all','green','one_r']:
        ref=pd.read_csv(OUT/f'primary_{state}.csv',parse_dates=['submitted','entry','exit'])
        previous=np.searchsorted(ref.exit.to_numpy(dtype='datetime64[s]'),times,side='right')-1
        ix=previous.clip(min=0)
        same=(previous>=0)&(times.astype('datetime64[D]')==ref.exit.to_numpy(dtype='datetime64[D]')[ix])
        active=np.ones(len(times),dtype=bool)
        if state!='all':
            value=ref.groupby('date')['net' if state=='green' else 'r'].cumsum().to_numpy()[ix]
            active=same & ((value>1e-6) if state=='green' else (value>=1))
        skips=set(m.index[cap]) | set(m.index[:-1][(rally & active)[1:]])
        trades,_=e.simulate_m30_ea(bars,cutoffs=e.load_cutoffs(),signal_skips=skips)
        actual=trades[trades.submitted>='2016-01-01'].reset_index(drop=True)
        for col,native in [('submitted','submitted'),('entry','entry_time'),('exit','exit_time')]:
            assert np.array_equal(ref[col].to_numpy(dtype='datetime64[s]'),actual[native].to_numpy(dtype='datetime64[s]'))
        assert np.allclose(ref.net,2*(actual.exit_price-actual.fill)-1.05)
        print(state,len(actual),'matched',flush=True)


if __name__=='__main__':
    main()

