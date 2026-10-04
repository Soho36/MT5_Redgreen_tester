import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from analyze_broad_support import verify_manifest
from analyze_price_levels import sha256
from broad_support import classify_contact, exact_contact


def scenario():
    low = np.full(200, 120.)
    low[55:66] = [110, 108, 106, 104, 102, 100, 102, 104, 106, 108, 110]
    b = pd.DataFrame(dict(low=low, high=low + 2, open=low + 1.5, close=low + 1,
                          contract=1, session_number=np.arange(200) // 30, atr=2.))
    b.loc[180, ["low", "high", "open", "close"]] = [99, 105, 104, 100]
    return b


class BroadContactTest(unittest.TestCase):
    def test_broken_and_deep_slice_still_qualify(self):
        b = scenario()
        b.loc[150, ["low", "high", "open", "close"]] = [89, 94, 93, 90]
        b.loc[180, ["low", "high", "open", "close"]] = [90, 105, 104, 91]
        self.assertEqual(classify_contact(b, 180), "contact")

    def test_opening_below_and_no_departure_qualify(self):
        b = scenario()
        b.loc[61:179, ["low", "high", "open", "close"]] = [100.5, 101.5, 101.4, 101.2]
        b.loc[180, ["low", "high", "open", "close"]] = [97, 101, 99, 98]
        self.assertEqual(classify_contact(b, 180), "contact")

    def test_both_zone_boundaries_inclusive(self):
        b = scenario()
        for low, high, expected in [(101, 105, "contact"), (101.25, 105, "no_contact"),
                                     (95, 99, "contact"), (95, 98.75, "no_contact")]:
            b.loc[180, ["low", "high"]] = [low, high]
            self.assertEqual(classify_contact(b, 180), expected)

    def test_pivot_must_be_confirmed_before_signal(self):
        b = scenario()
        b.loc[65, ["low", "high"]] = [100.5, 105]
        self.assertEqual(classify_contact(b, 65, sessions=1), "no_contact")
        b.loc[66, ["low", "high"]] = [100.5, 105]
        self.assertEqual(classify_contact(b, 66, sessions=1), "contact")

    def test_future_changes_cannot_change_contact(self):
        b = scenario()
        expected = classify_contact(b, 180)
        b.loc[181:, ["low", "high", "open", "close"]] = [10, 500, 100, 50]
        self.assertEqual(classify_contact(b, 180), expected)

    def test_expiry_and_availability(self):
        b = scenario()
        self.assertEqual(classify_contact(b, 180, sessions=1), "no_contact")
        self.assertEqual(classify_contact(b, 30), "missing_history")
        b.loc[180, "atr"] = np.nan
        self.assertEqual(classify_contact(b, 180), "invalid_atr")
        b.loc[180, "atr"] = 2
        b.loc[160:, "contract"] = 2
        self.assertEqual(classify_contact(b, 180), "contract_roll")

    def test_exact_contact_excludes_wholly_below_candles(self):
        np.testing.assert_array_equal(exact_contact(np.array([99, 100, 98, 101]),
                                                    np.array([101, 101, 99, 102]), 100),
                                      [True, True, False, False])


class ManifestTest(unittest.TestCase):
    def test_changed_or_missing_inputs_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.txt"
            source.write_text("original")
            manifest = Path(folder) / "manifest.json"
            manifest.write_text(json.dumps(dict(files=[dict(path=str(source), sha256=sha256(source))])))
            self.assertEqual(verify_manifest(manifest), 1)
            source.write_text("changed")
            with self.assertRaisesRegex(ValueError, "source.txt"):
                verify_manifest(manifest)
            source.unlink()
            with self.assertRaisesRegex(FileNotFoundError, "source.txt"):
                verify_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
