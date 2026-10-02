"""Post-hoc Q8 check: is the reclaim +0.5R excess directional or dispersion?

Reads the saved Q8 outputs only (no recomputation). Current-session low,
reclaim vs unrecovered, 3-bar horizon, eligible windows. Not part of the
frozen protocol; added 2026-10-03 after the results were read.
"""
from pathlib import Path

import pandas as pd

REPORT = Path(__file__).resolve().parent.parent / "Reports" / "breach_reclaim_20261003"

attempts = pd.read_csv(REPORT / "attempt_features.csv")
forward = pd.read_csv(REPORT / "forward_responses.csv")

attempts = attempts[(attempts.source == "current_session")
                    & attempts.group.isin(["breach_reclaim", "breach_unrecovered"])]
forward = forward[(forward.horizon == 3) & (forward.response_status == "eligible")]
m = attempts.merge(forward, on="event_id")
m["close_location"] = (m.signal_close - m.signal_low) / m.candle_range

table = m.groupby(["period", "group"]).apply(lambda x: pd.Series({
    "n": len(x),
    "p_up_half_r": (x.forward_r >= 0.5).mean(),
    "p_down_half_r": (x.forward_r <= -0.5).mean(),
    "std_forward_r": x.forward_r.std(),
    "close_location": x.close_location.mean(),
    "range_points": x.candle_range.mean(),
}))
print(table.round(3).to_string())
