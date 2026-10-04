"""Draw Q14 rising trendlines on M30 candles as a standalone SVG (no outcomes used).

Usage: python plot_trendline_example.py START END [OUT.svg]
Dots are confirmed swing lows (N=5). For every census red signal in the range, the
line that classifies it (trendline_support.classify) is drawn from its first anchor to
the signal bar, coloured by group, with a +/-D band at the signal. Lines are not drawn
for signals with no contact or with only broken lines (marker only).
"""

import sys
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd

from level_visit import bar_frame, swing_lows
from trend_regimes import ROLLS
from trendline_support import classify

ROOT = Path(__file__).absolute().parent.parent
M30 = ROOT / "Reports" / "levels" / "breach_reclaim_20261003" / "m30_reference.csv"
CENSUS = ROOT / "Reports" / "levels" / "support_interaction_20261003" / "potential_signals.csv"
OUT = ROOT / "Reports" / "trendlines" / "charts"
N, SESSIONS, MIN_SEP, MIN_SLOPE = 5, 5, 10, 0.02
UP, DOWN, PIVOT, MUTED, INK = "#26a69a", "#ef5350", "#2962ff", "#5f6368", "#202124"
MARK = {"trendline_support": ("#f57c00", "Trendline support (candidate)"),
        "slice_through": ("#000000", "Sliced > 0.5 x ATR through intact line"),
        "broken_contact": ("#7b1fa2", "Contact with a broken line"),
        "not_departed_contact": ("#9e9e9e", "Contact, price never left the line by 1 x ATR")}


def draw(b, signals, pivots, lo, hi, path, title):
    width_per = 2.4 if hi - lo > 400 else 7.0
    left, right, top, bottom = 70, 280, 56, 46
    w, h = int(left + right + (hi - lo + 1) * width_per), 640
    view = b.iloc[lo:hi + 1]
    pmin, pmax = view.low.min(), view.high.max()
    pad = (pmax - pmin) * 0.04
    pmin, pmax = pmin - pad, pmax + pad
    x = lambda k: left + (k - lo + 0.5) * width_per
    y = lambda p: top + (pmax - p) / (pmax - pmin) * (h - top - bottom)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
           'font-family="Segoe UI, Arial, sans-serif" font-size="12">',
           f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
           f'<text x="{left}" y="24" font-size="16" font-weight="600" fill="{INK}">{escape(title)}</text>',
           f'<text x="{left}" y="42" fill="{MUTED}">Dots = confirmed swing lows (lowest of 5 bars each side). Each red signal '
           'that touches a rising line (consecutive higher swing lows, >= 10 bars apart, rising >= 0.02 x ATR per bar, one week) shows it '
           'from its first anchor to the signal; band = line +/- 0.5 x ATR(14) at the signal.</text>']
    step = 10 ** np.floor(np.log10((pmax - pmin) / 6))
    step *= [1, 2, 5, 10][int(np.searchsorted([1.5, 3.5, 7.5], (pmax - pmin) / 6 / step))]
    for p in np.arange(np.ceil(pmin / step) * step, pmax, step):
        svg.append(f'<line x1="{left}" x2="{w - right}" y1="{y(p):.1f}" y2="{y(p):.1f}" stroke="#eeeeee"/>')
        svg.append(f'<text x="{left - 6}" y="{y(p) + 4:.1f}" text-anchor="end" fill="{MUTED}">{p:,.0f}</text>')
    sn = b.session_number.to_numpy()
    last_label = -1e9
    for k in range(lo, hi + 1):
        if k == lo or sn[k] != sn[k - 1]:
            svg.append(f'<line x1="{x(k) - width_per / 2:.1f}" x2="{x(k) - width_per / 2:.1f}" y1="{top}" '
                       f'y2="{h - bottom}" stroke="#f3f3f3"/>')
            if x(k) - last_label > 44:
                svg.append(f'<text x="{x(k):.1f}" y="{h - bottom + 16}" fill="{MUTED}">{b.index[k]:%d %b}</text>')
                last_label = x(k)
    low = b.low.to_numpy()
    # lines first, so candles stay readable on top
    for k, group, info in signals:
        if group not in MARK or group == "broken_contact":  # broken lines: marker only, keeps the chart legible
            continue
        i, j, v, d = info["anchor1"], info["anchor2"], info["line"], info["d"]
        x0, p0 = max(i, lo), low[i] + (low[j] - low[i]) * (max(i, lo) - i) / (j - i)
        color = MARK[group][0]
        svg.append(f'<line x1="{x(x0):.1f}" x2="{x(k):.1f}" y1="{y(p0):.1f}" y2="{y(v):.1f}" stroke="{color}" '
                   f'stroke-width="1.2" opacity="0.55"><title>{escape(f"Line {b.index[i]:%d %b %H:%M} -> {b.index[j]:%d %b %H:%M}")}'
                   f'</title></line>')
        svg.append(f'<rect x="{x(k) - width_per / 2:.1f}" y="{y(v + d):.1f}" width="{width_per:.1f}" '
                   f'height="{y(v - d) - y(v + d):.1f}" fill="{color}" opacity="0.18"/>')
    cw = max(1.0, width_per * 0.7)
    for k in range(lo, hi + 1):
        o, hh, ll, c = b.open.iloc[k], b.high.iloc[k], b.low.iloc[k], b.close.iloc[k]
        color = UP if c >= o else DOWN
        svg.append(f'<line x1="{x(k):.1f}" x2="{x(k):.1f}" y1="{y(hh):.1f}" y2="{y(ll):.1f}" stroke="{color}" '
                   f'stroke-width="{0.8 if width_per < 4 else 1}"/>')
        svg.append(f'<rect x="{x(k) - cw / 2:.1f}" y="{y(max(o, c)):.1f}" width="{cw:.1f}" '
                   f'height="{max(0.8, abs(y(o) - y(c))):.1f}" fill="{color}"/>')
    for i in pivots[(pivots >= lo) & (pivots <= hi)]:
        svg.append(f'<circle cx="{x(i):.1f}" cy="{y(low[i]) + 4:.1f}" r="2.6" fill="{PIVOT}"/>')
    for k, group, info in signals:
        if group not in MARK:
            continue
        tip = (f'{b.index[k]:%d %b %H:%M} {MARK[group][1]}; line {info["line"]:,.2f}, undercut {info["depth_a"]:+.2f} ATR, '
               f'earlier retests {info["retests"]}, lines touched {info["contacted"]}')
        yy = y(low[k]) + 9
        svg.append(f'<path d="M{x(k):.1f},{yy:.1f} l5,9 h-10 z" fill="{MARK[group][0]}" stroke="#ffffff" '
                   f'stroke-width="1"><title>{escape(tip)}</title></path>')
        if group == "trendline_support" and info["retests"] == 0:
            svg.append(f'<text x="{x(k):.1f}" y="{yy + 21:.1f}" text-anchor="middle" fill="{INK}" font-size="10">1st</text>')
    lx, ly = w - right + 18, top + 8
    items = [("dot", PIVOT, "Confirmed swing low")] + [("tri", c, t) for c, t in MARK.values()] + \
            [("txt", INK, "1st = first retest of that line")]
    for n_item, (kind, color, text) in enumerate(items):
        yy = ly + 22 * n_item
        if kind == "dot":
            svg.append(f'<circle cx="{lx + 11}" cy="{yy}" r="3" fill="{color}"/>')
        elif kind == "tri":
            svg.append(f'<path d="M{lx + 11},{yy - 6} l6,11 h-12 z" fill="{color}"/>')
        svg.append(f'<text x="{lx + 30}" y="{yy + 4}" fill="{INK}">{escape(text)}</text>')
    svg.append('</svg>')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(svg), encoding="utf-8")


def main(start, end, out=None):
    b = bar_frame(pd.read_csv(M30, index_col=0, parse_dates=[0]), pd.read_csv(ROLLS))
    census = pd.read_csv(CENSUS, usecols=["signal_time"], parse_dates=["signal_time"]).drop_duplicates()
    lo, hi = np.searchsorted(b.index, pd.Timestamp(start)), np.searchsorted(b.index, pd.Timestamp(end)) - 1
    pivots = swing_lows(b.low.to_numpy(), b.contract.to_numpy(), N)
    times = census.signal_time[(census.signal_time >= b.index[lo]) & (census.signal_time <= b.index[hi])]
    signals = [(int(k), *classify(b, k, N, SESSIONS, MIN_SEP, MIN_SLOPE, pivots)) for k in sorted(b.index.get_indexer(times)) if k >= 0]
    counts = pd.Series([g for _, g, _ in signals]).value_counts().to_dict()
    title = f"MNQ M30, {b.index[lo]:%d %b %Y} to {b.index[hi]:%d %b %Y}: rising trendline support (Q14 example)"
    out = Path(out) if out else OUT / f"trendlines_{b.index[lo]:%Y%m%d}_{b.index[hi]:%Y%m%d}.svg"
    draw(b, signals, pivots, lo, hi, out, title)
    print(out, counts)


if __name__ == "__main__":
    main(*sys.argv[1:])
