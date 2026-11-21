"""Contract checks for the news-session date edit and Forex Tester serialization."""
import unittest
import pandas as pd
from export_mnq_news_forex_tester import date_mapping,import_frame,validate_bars,FIELDS

class ExportTests(unittest.TestCase):
    def test_multiple_events_same_date_become_one_session(self):
        mapping=date_mapping(['2024-06-12','2024-06-07','2024-06-12'],'packed','2010-01-08')
        self.assertEqual(mapping,{'2024-06-07':'2010-01-08','2024-06-12':'2010-01-11'})

    def test_original_dates_are_preserved(self):
        dates=['2024-06-07','2024-06-12']
        self.assertEqual(date_mapping(dates,'original','ignored'),dict(zip(dates,dates)))

    def test_ohlcv_and_sparse_minutes_unchanged(self):
        source=pd.DataFrame([['2024.06.07','15:29:00','19000.25','19002.00','18999.50','19001.25','17'],
                             ['2024.06.07','15:31:00','19001.25','19004.00','19000.00','19003.75','38']],columns=FIELDS)
        result=import_frame(source,{'2024-06-07':'2010-01-04'})
        validate_bars(result)
        self.assertEqual(result.Date.tolist(),['20100104']*2)
        self.assertEqual(result.iloc[:,1:].values.tolist(),source.iloc[:,1:].values.tolist())
        self.assertEqual(len(result),2)

    def test_duplicate_timestamps_rejected(self):
        source=pd.DataFrame([['2024.06.07','15:30:00','1.00','1.25','0.75','1.00','2']]*2,columns=FIELDS)
        with self.assertRaises(AssertionError):validate_bars(import_frame(source,{'2024-06-07':'2010-01-04'}))

    def test_invalid_ohlc_rejected(self):
        source=pd.DataFrame([['2024.06.07','15:30:00','2.00','1.25','0.75','1.00','2']],columns=FIELDS)
        with self.assertRaises(AssertionError):validate_bars(import_frame(source,{'2024-06-07':'2010-01-04'}))

    def test_weekend_start_rejected(self):
        with self.assertRaises(ValueError):date_mapping(['2024-06-07'],'packed','2010-01-09')

if __name__=='__main__':unittest.main()
