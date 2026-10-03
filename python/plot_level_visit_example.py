"""Draw Q11 swing-low levels on M30 candles as a standalone SVG (no outcomes used).

Usage: python plot_level_visit_example.py START END [OUT.svg]
Each line is one confirmed swing low (N=5): dotted until confirmed, solid while
it could be support, ending when a close goes more than 0.5 x ATR below it
(broken, red x) or when it leaves the one-week window. The shaded band is +/-D.
Markers are census red signals classified by level_visit.classify.
"""

import sys
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd

from level_visit import bar_frame, classify, swing_lows
from trend_regimes import ROLLS

ROOT = Path(__file__).absolute().parent.parent
M30 = ROOT / "Reports" / "levels" / "breach_reclaim_20261003" / "m30_reference.csv"
CENSUS = ROOT / "Reports" / "levels" / "support_interaction_20261003" / "potential_signals.csv"
OUT = ROOT / "Reports" / "levels" / "level_visit_20261004" / "charts"
N, SESSIONS = 5, 5
UP, DOWN, LEVEL, BROKEN, MUTED, INK = "#26a69a", "#ef5350", "#2962ff", "#9e9e9e", "#5f6368", "#202124"
MARK = {"support_revisit": ("#f57c00", "Support revisit (Q11 candidate)"),
        "slice_through": ("#000000", "Sliced > 0.5 x ATR through intact level"),
        "broken_contact": ("#7b1fa2", "Contact with a broken level"),
        "not_departed_contact": ("#9e9e9e", "Contact, price never left by 1 x ATR")}


def segments(b, pivots, lo, hi):
    """Life of each swing low: (pivot, confirm, end, broken) in bar indices."""
    low, close, atr, sn = b.low.to_numpy(), b.close.to_numpy(), b.atr.to_numpy(), b.session_number.to_numpy()
    out = []
    for i in pivots:
        if i + N > hi or i < lo - 400:
            continue
        L, end, broken, expiry = low[i], hi, False, hi
        for k in range(i + 1, hi + 1):
            if sn[k] - sn[i] > SESSIONS:
                expiry = k - 1
                break
        for k in range(i + 1, expiry + 1):
            if np.isfinite(atr[k]) and close[k] < L - 0.5 * atr[k]:
                end, broken = k, True
                break
        else:
            end = expiry
        if expiry >= lo:
            out.append((i, i + N, end, broken, expiry))
    return out


def draw(b, signals, lo, hi, path, title):
    width_per = 2.4 if hi - lo > 400 else 7.0
    left, right, top, bottom = 70, 250, 56, 46
    w = int(left + right + (hi - lo + 1) * width_per)
    h = 640
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
           f'<text x="{left}" y="42" fill="{MUTED}">Swing low = lowest of 5 bars each side. Dotted until confirmed; '
           'solid while usable; band = level +/- 0.5 x ATR(14). Broken (x) when a close is more than 0.5 x ATR below; dashed grey afterwards; dropped after one week. Markers sit under the signal candle.</text>']
    # price grid
    step = 10 ** np.floor(np.log10((pmax - pmin) / 6))
    step *= [1, 2, 5, 10][int(np.searchsorted([1.5, 3.5, 7.5], (pmax - pmin) / 6 / step))]
    for p in np.arange(np.ceil(pmin / step) * step, pmax, step):
        svg.append(f'<line x1="{left}" x2="{w - right}" y1="{y(p):.1f}" y2="{y(p):.1f}" stroke="#eeeeee"/>')
        svg.append(f'<text x="{left - 6}" y="{y(p) + 4:.1f}" text-anchor="end" fill="{MUTED}">{p:,.0f}</text>')
    # session separators and date labels
    sn = b.session_number.to_numpy()
    last_label = -1e9
    for k in range(lo, hi + 1):
        if k == lo or sn[k] != sn[k - 1]:
            svg.append(f'<line x1="{x(k) - width_per / 2:.1f}" x2="{x(k) - width_per / 2:.1f}" y1="{top}" '
                       f'y2="{h - bottom}" stroke="#f3f3f3"/>')
            if x(k) - last_label > 44:
                svg.append(f'<text x="{x(k):.1f}" y="{h - bottom + 16}" fill="{MUTED}">{b.index[k]:%d %b}</text>')
                last_label = x(k)
    # levels
    atr = b.atr.to_numpy()
    for i, confirm, end, broken, expiry in segments(b, swing_lows(b.low.to_numpy(), b.contract.to_numpy(), N), lo, hi):
        L = b.low.iloc[i]
        a = atr[min(confirm, len(atr) - 1)]
        s0, s1 = max(i, lo), min(end, hi)
        if np.isfinite(a) and max(confirm, lo) <= s1:
            c0 = max(confirm, lo)
            svg.append(f'<rect x="{x(c0):.1f}" y="{y(L + 0.5 * a):.1f}" width="{x(s1) - x(c0) + 0.1:.1f}" '
                       f'height="{y(L - 0.5 * a) - y(L + 0.5 * a):.1f}" fill="{LEVEL}" opacity="0.07"/>')
        if s0 <= min(confirm, hi):
            svg.append(f'<line x1="{x(s0):.1f}" x2="{x(min(confirm, hi)):.1f}" y1="{y(L):.1f}" y2="{y(L):.1f}" '
                       f'stroke="{LEVEL}" stroke-width="1" stroke-dasharray="1 3" opacity="0.7"/>')
        if max(confirm, lo) <= s1:
            svg.append(f'<line x1="{x(max(confirm, lo)):.1f}" x2="{x(s1):.1f}" y1="{y(L):.1f}" y2="{y(L):.1f}" '
                       f'stroke="{LEVEL}" stroke-width="1.6" opacity="0.85"><title>Swing low {L:,.2f} '
                       f'set {b.index[i]:%d %b %H:%M}</title></line>')
        if broken and max(end, lo) < min(expiry, hi):
            svg.append(f'<line x1="{x(max(end, lo)):.1f}" x2="{x(min(expiry, hi)):.1f}" y1="{y(L):.1f}" y2="{y(L):.1f}" '
                       f'stroke="{BROKEN}" stroke-width="1" stroke-dasharray="4 3" opacity="0.8"/>')
        if broken and lo <= end <= hi:
            svg.append(f'<text x="{x(end):.1f}" y="{y(L) + 4:.1f}" text-anchor="middle" fill="{DOWN}" '
                       f'font-weight="700">x</text>')
    # candles
    cw = max(1.0, width_per * 0.7)
    for k in range(lo, hi + 1):
        o, hh, ll, c = b.open.iloc[k], b.high.iloc[k], b.low.iloc[k], b.close.iloc[k]
        color = UP if c >= o else DOWN
        svg.append(f'<line x1="{x(k):.1f}" x2="{x(k):.1f}" y1="{y(hh):.1f}" y2="{y(ll):.1f}" stroke="{color}" '
                   f'stroke-width="{0.8 if width_per < 4 else 1}"/>')
        top_body, body = y(max(o, c)), max(0.8, abs(y(o) - y(c)))
        svg.append(f'<rect x="{x(k) - cw / 2:.1f}" y="{top_body:.1f}" width="{cw:.1f}" height="{body:.1f}" fill="{color}"/>')
    # signal markers
    for k, group, info in signals:
        if group not in MARK or not lo <= k <= hi:
            continue
        color = MARK[group][0]
        yy = y(b.low.iloc[k]) + 7
        tip = f'{b.index[k]:%d %b %H:%M} {MARK[group][1]}'
        if "level" in info:
            tip += f'; level {info["level"]:,.2f}, undercut {info["depth_a"]:+.2f} ATR'
        svg.append(f'<path d="M{x(k):.1f},{yy:.1f} l5,9 h-10 z" fill="{color}" stroke="#ffffff" stroke-width="1">'
                   f'<title>{escape(tip)}</title></path>')
    # legend
    lx, ly = w - right + 18, top + 8
    items = [("line", LEVEL, "Swing-low level (usable)"), ("dot", LEVEL, "Not yet confirmed"),
             ("x", DOWN, "Level broken"), ("dash", BROKEN, "Broken level (now resistance)")] + [("tri", c, t) for c, t in MARK.values()]
    for n_item, (kind, color, text) in enumerate(items):
        yy = ly + 22 * n_item
        if kind == "line":
            svg.append(f'<line x1="{lx}" x2="{lx + 22}" y1="{yy}" y2="{yy}" stroke="{color}" stroke-width="2"/>')
        elif kind == "dot":
            svg.append(f'<line x1="{lx}" x2="{lx + 22}" y1="{yy}" y2="{yy}" stroke="{color}" stroke-dasharray="1 3"/>')
        elif kind == "dash":
            svg.append(f'<line x1="{lx}" x2="{lx + 22}" y1="{yy}" y2="{yy}" stroke="{color}" stroke-dasharray="4 3"/>')
        elif kind == "x":
            svg.append(f'<text x="{lx + 11}" y="{yy + 4}" text-anchor="middle" fill="{color}" font-weight="700">x</text>')
        else:
            svg.append(f'<path d="M{lx + 11},{yy - 6} l6,11 h-12 z" fill="{color}"/>')
        svg.append(f'<text x="{lx + 30}" y="{yy + 4}" fill="{INK}">{escape(text)}</text>')
    svg.append('</svg>')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(svg), encoding="utf-8")


def main(start, end, out=None):
    bars = pd.read_csv(M30, index_col=0, parse_dates=[0])
    b = bar_frame(bars, pd.read_csv(ROLLS))
    census = pd.read_csv(CENSUS, usecols=["signal_time"], parse_dates=["signal_time"]).drop_duplicates()
    lo, hi = np.searchsorted(b.index, pd.Timestamp(start)), np.searchsorted(b.index, pd.Timestamp(end)) - 1
    pivots = swing_lows(b.low.to_numpy(), b.contract.to_numpy(), N)
    idx = b.index.get_indexer(census.signal_time[(census.signal_time >= b.index[lo]) & (census.signal_time <= b.index[hi])])
    signals = [(int(k), *classify(b, k, n=N, sessions=SESSIONS, pivots=pivots)) for k in sorted(idx) if k >= 0]
    counts = pd.Series([g for _, g, _ in signals]).value_counts().to_dict()
    title = (f"MNQ M30, {b.index[lo]:%d %b %Y} to {b.index[hi]:%d %b %Y}: one-week swing-low support (Q11 example)")
    out = Path(out) if out else OUT / f"levels_{b.index[lo]:%Y%m%d}_{b.index[hi]:%Y%m%d}.svg"
    draw(b, signals, lo, hi, out, title)
    print(out, counts)


if __name__ == "__main__":
    main(*sys.argv[1:])
