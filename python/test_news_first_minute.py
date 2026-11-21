import unittest
from analyze_news_first_minute import decision

class NewsFirstMinute(unittest.TestCase):
    def test_green_uses_high_target_low_stop(self):
        self.assertEqual(decision(100,105,98,103,103,103.01),('entered',1,98,105))
    def test_red_uses_low_target_high_stop(self):
        self.assertEqual(decision(103,105,98,100,100,100.01),('entered',-1,105,98))
    def test_doji_and_no_target_wick(self):
        self.assertEqual(decision(100,105,98,100,100,100.01)[0],'doji')
        self.assertEqual(decision(100,105,98,105,104,104.01)[0],'zero_target_wick')
        self.assertEqual(decision(103,105,98,98,99,99.01)[0],'zero_target_wick')
    def test_next_quote_gap_past_target_or_stop(self):
        self.assertEqual(decision(100,105,98,103,105,105.01)[0],'invalid_entry_levels')
        self.assertEqual(decision(103,105,98,100,106,106.01)[0],'invalid_entry_levels')
    def test_broker_distance_not_silently_widened(self):
        self.assertEqual(decision(100,105,98,103,104.75,104.76,.5)[0],'broker_stop_distance')

if __name__=='__main__':unittest.main()
