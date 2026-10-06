"""Draw Q23 examples: swing-low support levels, green breakdown-test signals and the stage-0 short trades (SVG).

Usage: python plot_support_breakdown.py START END OUT.svg [PX_PER_BAR]
Levels and the drawing come from plot_level_visit_example (the frozen Q11 map that Q23 uses unchanged). Markers
are the Q23 groups of green census signals (signals.csv, one week N = 5). Trades are the verified stage-0 ledger of
the short mirror baseline: candidates in colour with their stop (signal high) and 1R target while open, every
other mirror-baseline short as a thin grey line. Docs/levels/SUPPORT_BREAKDOWN_RESULTS.md has the results.
"""

import sys
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_support_breakdown import load_run
from level_visit import bar_frame
from plot_level_visit_example import DOWN, INK, M30, MUTED, UP, draw
from prepare_support_breakdown import RUN
from trend_regimes import ROLLS

MARK = {"breakdown_test": ("#f57c00", "Breakdown test from above (Q23 candidate)"),
        "poke_through": ("#000000", "Low > 0.5 x ATR below intact level"),
        "broken_downward_contact": ("#7b1fa2", "Contact with a broken level"),
        "not_departed_contact": ("#9e9e9e", "Contact, price never left by 1 x ATR")}
SUBTITLE = ("Q23, short mirror of Q18. Swing low = lowest of 5 bars each side, one-week window;\n"
            "band = level +/- 0.5 x ATR(14). Markers sit under green signal candles: sell stop at the\n"
            "candle low, stop at its high, exit after a close below entry - 1R or at the session flatten.\n"
            "Trades are the verified stage-0 run of the short mirror baseline.")
LEGEND = [("down", INK, "Short entry (sell stop at the signal low)"), ("circle", MUTED, "Exit (green profit / red loss)"),
          ("dashed", DOWN, "Stop = signal high"), ("dashed", UP, "1R target (close below -> exit)"),
          ("solid", "#bdbdbd", "Other mirror-baseline short")]


def trades_overlay(b, lo, hi, trades):
    """Overlay callback for plot_level_visit_example.draw: one group of elements per trade in the window."""
    pos = pd.Series(np.arange(len(b)), index=b.index)
    start, end = b.index[lo], b.index[hi] + pd.Timedelta("30min")
    t = trades[(trades.entry_time >= start) & (trades.entry_time < end)]

    def overlay(x, y, width_per):
        out = []
        for r in t.itertuples():
            ke = int(pos[r.entry_time.floor("30min")])
            kx = min(int(pos.get(r.exit_time.floor("30min"), hi)), hi)
            win = r.trade_profit - 1.05 > 0
            color = UP if win else DOWN
            tip = (f"{r.group}: short {r.base_entry:,.2f} at {r.entry_time:%d %b %H:%M}, stop {r.initial_stop:,.2f}, "
                   f"exit {r.exit_price:,.2f} at {r.exit_time:%H:%M} ({r.exit_class}), net {r.trade_profit - 1.05:+.2f} $")
            if r.group != "breakdown_test":
                out.append(f'<line x1="{x(ke):.1f}" y1="{y(r.base_entry):.1f}" x2="{x(kx):.1f}" y2="{y(r.exit_price):.1f}" '
                           f'stroke="#bdbdbd" stroke-width="1.2"><title>{escape(tip)}</title></line>')
                continue
            x0, x1 = x(ke) - width_per / 2, x(kx) + width_per / 2
            target = r.base_entry - r.candle_range
            for price, c in ((r.initial_stop, DOWN), (target, UP)):
                out.append(f'<line x1="{x0:.1f}" x2="{x1:.1f}" y1="{y(price):.1f}" y2="{y(price):.1f}" stroke="{c}" '
                           f'stroke-width="1.6" stroke-dasharray="5 3"/>')
            out.append(f'<line x1="{x(ke):.1f}" y1="{y(r.base_entry):.1f}" x2="{x(kx):.1f}" y2="{y(r.exit_price):.1f}" '
                       f'stroke="{color}" stroke-width="2"/>')
            out.append(f'<path d="M{x(ke):.1f},{y(r.base_entry) + 6:.1f} l6,-11 h-12 z" fill="{INK}">'
                       f'<title>{escape(tip)}</title></path>')
            out.append(f'<circle cx="{x(kx):.1f}" cy="{y(r.exit_price):.1f}" r="4" fill="#ffffff" stroke="{color}" '
                       f'stroke-width="2"><title>{escape(tip)}</title></circle>')
        return out
    return overlay


def main(start, end, out, px=None):
    b = bar_frame(pd.read_csv(M30, index_col=0, parse_dates=[0]), pd.read_csv(ROLLS))
    s = pd.read_csv(RUN / "signals.csv", parse_dates=["signal_time"])
    s = s[s.config == "week_n5"]
    _, led = load_run()
    led["exit_price"] = pd.to_numeric(led.exit_price)
    led = led.merge(s[["signal_time", "group"]], on="signal_time", how="left", validate="many_to_one")
    led["exit_class"] = np.select([led.exit_reason == 4, led.qualified_time.notna()], ["stop", "1R target"],
                                  default="session flatten")
    lo, hi = np.searchsorted(b.index, pd.Timestamp(start)), np.searchsorted(b.index, pd.Timestamp(end)) - 1
    view = s[(s.signal_time >= b.index[lo]) & (s.signal_time <= b.index[hi])]
    signals = [(int(b.index.get_loc(r.signal_time)), r.group,
                {} if pd.isna(r.level) else dict(level=r.level, depth_a=r.depth_a)) for r in view.itertuples()]
    title = f"MNQ M30, {b.index[lo]:%d %b %Y %H:%M} to {b.index[hi]:%d %b %Y %H:%M}: Q23 short at swing-low support"
    draw(b, signals, lo, hi, Path(out), title, mark=MARK, subtitle=SUBTITLE, overlay=trades_overlay(b, lo, hi, led),
         legend_extra=LEGEND, width_per=float(px) if px else None)
    print(out, view.group.value_counts().to_dict())


if __name__ == "__main__":
    main(*sys.argv[1:])
