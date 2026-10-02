import unittest
import pandas as pd
from trend_regimes import label_daily
from trend_rr_metrics import select_for_year, metrics


def trades(values,dates,regimes=None):
    n=len(values)
    return pd.DataFrame(dict(entry_time=pd.to_datetime(dates),exit_time=pd.to_datetime(dates)+pd.Timedelta(hours=1),
                             trade_profit=values,initial_risk_money=[10]*n,
                             regime_name=regimes or ["bull"]*n,qualified_time=[pd.NaT]*n,
                             exit_reason=[4]*n,mfe_money=[10]*n,mae_money=[-10]*n))


class TrendTests(unittest.TestCase):
    def test_today_and_future_do_not_enter_labels(self):
        dates=pd.date_range("2020-01-01",periods=250,freq="B")
        d=pd.DataFrame({"close":range(1,251)},index=dates,dtype=float)
        a=label_daily(d)
        d.loc[dates[210]:,"close"]=-10000
        b=label_daily(d)
        cols=["previous_close","sma40","sma50","sma60","sma200","regime50"]
        pd.testing.assert_frame_equal(a.loc[:dates[210],cols],b.loc[:dates[210],cols])
        self.assertAlmostEqual(a.loc[dates[200],"sma200"],100.5)
        self.assertEqual(a.loc[dates[199],"regime50"],"warmup")
        self.assertEqual(a.loc[dates[200],"regime50"],"bull")

    def test_selector_cannot_see_test_year(self):
        dates=list(pd.date_range("2013-01-01",periods=225,freq="D"))
        regimes=["bull"]*75+["neutral"]*75+["bear"]*75
        baseline=trades([3,-1,2]*75,dates,regimes)
        mild=trades([4,-1,2]*75,dates,regimes)
        strong=trades([2,-2,1]*75,dates,regimes)
        v=dict(baseline=baseline,mild=mild,strong=strong)
        self.assertEqual(select_for_year(v,2015)[0],"mild")
        v["strong"]=pd.concat([strong,trades([1e9],["2015-01-01"])],ignore_index=True)
        self.assertEqual(select_for_year(v,2015)[0],"mild")
        v["mild"]=mild.iloc[:-1] # only 74 bears: ineligible
        self.assertEqual(select_for_year(v,2015)[0],"baseline")

    def test_bear_and_equality_neutral(self):
        dates=pd.date_range("2020-01-01",periods=220,freq="B")
        falling=pd.DataFrame({"close":range(220,0,-1)},index=dates,dtype=float)
        self.assertEqual(label_daily(falling).iloc[-1].regime50,"bear")
        flat=pd.DataFrame({"close":[100.]*220},index=dates)
        self.assertEqual(label_daily(flat).iloc[-1].regime50,"neutral")

    def test_simultaneous_exits_and_zero_months(self):
        t=trades([11.05,-8.95],["2020-01-01","2020-01-01"])
        m=metrics(t,"2020-01-01","2021-01-01")
        self.assertAlmostEqual(m["net"],0.)
        self.assertAlmostEqual(m["dd"],0.)
        self.assertEqual(len(m["months"]),12)


if __name__=="__main__":
    unittest.main()
