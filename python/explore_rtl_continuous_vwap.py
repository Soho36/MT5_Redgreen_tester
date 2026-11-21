"""Exploratory baseline-trade omission: VWAP anchored at first 2010 bar."""
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
features = pd.read_csv(ROOT/'Reports/rtl_vwap_20261025/features_full_hlc3.csv',
                       parse_dates=['bar_time','available_at'], float_precision='round_trip')
trades = pd.read_csv(ROOT/'Reports/rtl_market_regimes_20261023/trades.csv',
                     parse_dates=['submitted','session'], float_precision='round_trip')
assert features.bar_time.is_monotonic_increasing and (features.volume > 0).all()
features['continuous_vwap'] = features.pv_hlc3.cumsum()/features.volume.cumsum()
assert np.allclose(features.continuous_vwap * features.volume.cumsum(), features.pv_hlc3.cumsum())
labels = pd.merge_asof(trades.sort_values('submitted'),
    features[['available_at','close','a20','continuous_vwap']].sort_values('available_at'),
    left_on='submitted', right_on='available_at', direction='backward')
assert (labels.available_at <= labels.submitted).all()
labels['skip'] = labels.close.lt(labels.continuous_vwap-labels.a20)
dates = pd.DatetimeIndex(features.bar_time.dt.normalize().unique()).sort_values()
for name, start, end in [('2010-15','2010-01-01','2016-01-01'),
                          ('2016-19','2016-01-01','2020-01-01'),
                          ('2020-Sep26','2020-01-01','2026-10-01')]:
    f = labels[labels.session.ge(start)&labels.session.lt(end)]
    calendar = dates[(dates >= start)&(dates < end)]
    print(name, 'eligible',len(f),'skipped',int(f.skip.sum()),
          'skip_share',round(100*f.skip.mean(),2),
          'median_price_minus_continuous_vwap',round((f.close-f.continuous_vwap).median(),2))
    for label, mask in [('baseline',np.ones(len(f),dtype=bool)),('retained',~f.skip),('skipped',f.skip)]:
        x=f.loc[mask]
        daily=x.groupby('session').net_dollars.sum().reindex(calendar,fill_value=0.)
        equity=np.r_[0.,daily.cumsum().to_numpy()]
        dd=(np.maximum.accumulate(equity)-equity).max()
        print(' ',label,'trades',len(x),'net',round(x.net_dollars.sum(),2),
              'mean_R',round(x.net_r.mean(),4),'daily_dd',round(dd,2))
