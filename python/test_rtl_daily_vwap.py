"""Daily/monthly rescaling: causal features and original order mechanics."""
import unittest
import numpy as np
import pandas as pd
from rtl_daily_vwap import allowed,simulate

def fixture(rows):
    dates=pd.to_datetime([r[0] for r in rows])
    b=dict(day=dates.to_numpy(dtype='datetime64[D]').astype('int64'),
        date=np.array([int(x.strftime('%Y%m%d')) for x in dates]),minute=np.ones(len(rows),dtype=int)*60)
    for j,k in enumerate('ohlc',1):b[k]=np.array([r[j] for r in rows],float)
    f=pd.DataFrame([dict(open=r[1],high=r[2],low=r[3],close=r[4],vwap=r[5],a20=1.,known=True)
                    for r in rows],index=dates)
    return b,f

class DailyTests(unittest.TestCase):
    def test_strict_boundary(self):
        r=pd.Series(dict(close=99.,vwap=100.,a20=1.,known=True),name=pd.Timestamp('2020-01-02'))
        self.assertEqual(allowed(r,pd.Timestamp('2020-01-03')),(True,True))
        r['close']=98.75
        self.assertEqual(allowed(r,pd.Timestamp('2020-01-03')),(True,False))

    def test_new_month_and_warmup_unknown_allow(self):
        r=pd.Series(dict(close=90.,vwap=100.,a20=1.,known=True),name=pd.Timestamp('2020-01-31'))
        self.assertEqual(allowed(r,pd.Timestamp('2020-02-03')),(False,True))
        r.name=pd.Timestamp('2020-02-03');r['known']=False;r['a20']=np.nan
        self.assertEqual(allowed(r,pd.Timestamp('2020-02-04')),(False,True))

    def test_blocked_red_replaces_pending(self):
        rows=[('2020-01-02',100,110,90,99,99),('2020-01-03',100,105,95,98,100),
              ('2020-01-06',100,111,99,108,105)]
        b,f=fixture(rows)
        self.assertEqual(len(simulate(b,f,'2020-01-03',True)[0]),0)
        self.assertEqual(len(simulate(b,f,'2020-01-03',False)[0]),1)

    def test_green_keeps_pending_even_if_below_band(self):
        rows=[('2020-01-02',100,110,90,99,99),('2020-01-03',98,105,95,100,110),
              ('2020-01-06',100,111,99,108,105)]
        b,f=fixture(rows);t=simulate(b,f,'2020-01-03',True)[0].iloc[0]
        self.assertEqual(t.submitted,pd.Timestamp('2020-01-03 01:00'))
        self.assertEqual(t.fill,110)

    def test_holds_position_across_month_end(self):
        rows=[('2020-01-29',100,110,90,99,99),('2020-01-30',100,111,99,108,105),
              ('2020-01-31',108,120,105,118,115),('2020-02-03',118,132,115,131,128),
              ('2020-02-04',132,133,131,132,132)]
        b,f=fixture(rows);t=simulate(b,f,'2020-01-30',True)[0].iloc[0]
        self.assertEqual(t.reason,'target')
        self.assertEqual(t.exit_time,pd.Timestamp('2020-02-04 01:00'))
        self.assertEqual(t.exit_price,132)

    def test_month_reset_preserves_pending(self):
        rows=[('2020-01-30',100,110,90,99,99),('2020-01-31',98,105,95,100,100),
              ('2020-02-03',100,111,99,108,105)]
        b,f=fixture(rows);t=simulate(b,f,'2020-01-31',True)[0].iloc[0]
        self.assertEqual(t.submitted,pd.Timestamp('2020-01-31 01:00'))
        self.assertEqual(t.entry_time.date(),pd.Timestamp('2020-02-03').date())

    def test_future_label_cannot_change_current_candidate(self):
        rows=[('2020-01-02',100,110,90,99,99),('2020-01-03',100,111,99,108,105)]
        b,f=fixture(rows);a=simulate(b,f,'2020-01-03',True)
        f.loc[pd.Timestamp('2020-01-03'),['vwap','a20']]=[100000,100]
        z=simulate(b,f,'2020-01-03',True)
        pd.testing.assert_frame_equal(a[0],z[0]);pd.testing.assert_frame_equal(a[1],z[1])

if __name__=='__main__':unittest.main()
