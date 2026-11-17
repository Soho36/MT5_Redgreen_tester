"""Regression coverage for appending CSV data to a DBN history."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import build_continuous as build


class MixedSourceVolumeTest(unittest.TestCase):
    def test_mixed_unsigned_dbn_and_signed_csv_keep_integral_volumes(self):
        def frame(stamp, volume, dtype):
            return pd.DataFrame({
                'instrument_id': [261401], 'symbol': ['NQZ6'],
                'open': [30000.0], 'high': [30000.25],
                'low': [29999.75], 'close': [30000.0],
                'volume': pd.Series([volume], dtype=dtype),
                'ts_utc': pd.to_datetime([stamp], utc=True),
            })
        parts = [frame('2026-10-01T00:00:00Z', 117, 'uint64'),
                 frame('2026-10-01T00:01:00Z', 99, 'int64')]
        with tempfile.TemporaryDirectory() as tmp, patch.object(build, 'read_one', side_effect=parts):
            build.main('NQ', tmp, ['history.dbn', 'topup.csv'])
            output = Path(tmp, 'MT5_NQ_continuous_2026-2026_ohlcv-1m.csv')
            rows = [line.split('\t') for line in output.read_text().splitlines()[1:]]
            self.assertEqual([(r[6], r[7]) for r in rows], [('117', '117'), ('99', '99')])


if __name__ == '__main__':
    unittest.main()
