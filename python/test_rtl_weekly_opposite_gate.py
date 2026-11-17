"""State, timing, and execution tests for the exact weekly gate."""
import unittest
import numpy as np
import pandas as pd
from rtl_weekly_opposite_gate import weekly_bars,decisions,halt_windows
from rtl_news_window_engine import simulate
from test_rtl_sell_limit_fade import bars,RED,FILL,at
from build_news_windows import window_ids

def weeks(rows):
    dates=pd.date_range('2020-01-06',periods=len(rows),freq='W-MON')
    return pd.DataFrame([dict(week=d,first=d+pd.Timedelta(hours=1),open=o,high=h,low=l,close=c)
        for d,(o,h,l,c) in zip(dates,rows)])

# Green, red that holds, second red breaks older green, two green recovery weeks.
SEQUENCE=[(100,110,95,105),(108,109,98,100),(100,102,90,94),
          (94,103,93,101),(101,104,100,103),(103,106,102,104)]

class WeeklyGateTests(unittest.TestCase):
    def test_distant_opposite_colour_and_persistent_state(self):
        d=decisions(weeks(SEQUENCE))
        self.assertEqual(d.enabled.tolist(),[1,1,0,0,1])
        self.assertEqual(d.trigger.tolist(),['none','none','halt','none','resume'])
        self.assertEqual(d.green_week.iloc[2],pd.Timestamp('2020-01-06'))
        self.assertEqual(d.red_week.iloc[4],pd.Timestamp('2020-01-20'))

    def test_references_update_while_halted(self):
        seq=SEQUENCE[:4]+[(101,105,92,93),(93,104,92,104),(104,106,103,106),(106,108,104,107)]
        d=decisions(weeks(seq))
        # New red high 105 replaces old red high 102; close 104 cannot resume.
        self.assertEqual(d.enabled.tolist(),[1,1,0,0,0,0,1])
        self.assertEqual(d.red_high.iloc[5],105)

    def test_doji_does_not_replace_reference_or_toggle(self):
        seq=SEQUENCE[:3]+[(94,200,1,94),(94,103,92,103),(103,104,102,103)]
        d=decisions(weeks(seq))
        self.assertEqual(d.enabled.tolist(),[1,1,0,0,1])
        self.assertEqual(d.red_high.iloc[4],102)

    def test_strict_low_and_high_boundaries(self):
        seq=[(100,110,95,105),(105,109,94,95),(95,102,90,94),
             (94,103,93,102),(102,104,101,103),(103,104,102,103)]
        self.assertEqual(decisions(weeks(seq)).enabled.tolist(),[1,1,0,0,1])

    def test_colour_required_despite_price_gap(self):
        seq=[(100,110,95,105),(90,96,89,94),(94,96,90,93),(110,112,105,106),(106,107,104,105)]
        self.assertEqual(decisions(weeks(seq)).enabled.tolist(),[1,1,1,1])

    def test_missing_reference_starts_enabled(self):
        seq=[(100,101,90,91),(91,92,80,81),(81,82,70,71)]
        self.assertEqual(decisions(weeks(seq)).enabled.tolist(),[1,1])

    def test_last_unfinished_week_cannot_change_past(self):
        a=weeks(SEQUENCE)
        b=a.copy()
        b.loc[b.index[-1],['open','high','low','close']]=[1000,2000,0,1]
        pd.testing.assert_frame_equal(decisions(a),decisions(b))
        pd.testing.assert_frame_equal(decisions(a.iloc[:4]),decisions(a).iloc[:3].reset_index(drop=True))

    def test_changes_only_next_week_first_quote(self):
        w=weeks(SEQUENCE)
        d=decisions(w)
        t=w.iloc[3]['first']
        self.assertEqual(d.effective.iloc[2],t)
        windows=halt_windows(d,'2020-03-01')
        ids=window_ids([t-pd.Timedelta(seconds=1),t,w.iloc[5]['first']],windows)
        self.assertEqual(ids.tolist(),[-1,0,-1])

    def test_raw_weekly_aggregation(self):
        b=bars([('10:00',100,110,95,104),('10:01',104,108,90,101)])
        b['day']=np.array([18267,18274]) # Thursdays a week apart
        w=weekly_bars(b)
        self.assertEqual(len(w),2)
        self.assertEqual(w.week.dt.dayofweek.tolist(),[0,0])
        self.assertEqual(w.close.tolist(),[104,101])

    def test_halt_cancels_pending_without_resurrection(self):
        b=bars(RED+[('10:30',99.5,99.75,99.5,99.75),('10:31',100,100.5,100,100.25),
                    ('10:32',100,102,100,101),('11:00',101,102,101,102)])
        windows=pd.DataFrame([dict(start=at('10:31'),end=at('10:33'))])
        self.assertEqual(len(simulate(b,windows,1)[0]),0)
        self.assertGreater(len(simulate(b,windows,0)[0]),0)

    def test_halt_preserves_open_position_normal_target(self):
        b=bars(RED+FILL+[('10:32',101,103.5,101,103),('11:00',103.25,104,103,103.5)])
        windows=pd.DataFrame([dict(start=at('10:32'),end=at('11:30'))])
        t=simulate(b,windows,1)[0].iloc[0]
        self.assertEqual(t.reason,'target')
        self.assertEqual(t.exit_time,at('11:00'))
        self.assertEqual(t.exit_price,103.25)

    def test_boundary_fill_is_position_before_callback(self):
        b=bars(RED+[('10:30',99.5,99.75,99.5,99.75),('10:31',101,102,101,101.5)])
        windows=pd.DataFrame([dict(start=at('10:31'),end=at('11:30'))])
        t=simulate(b,windows,1)[0].iloc[0]
        self.assertEqual(t.entry_time,at('10:31'))
        self.assertEqual(t.reason,'end_of_data')

if __name__=='__main__':
    unittest.main()

