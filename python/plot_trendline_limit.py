"""Draw Q20 resting buy limits on M30 candles as standalone SVGs (no outcomes used).

Usage: python plot_trendline_limit.py START END OUT.svg [--zoom]
Reads the verified classify-only bar log (EA = Python, 0 mismatches). For every bar where the primary
would rest an order, the chosen line is drawn from its first anchor, and the order is drawn as a step:
the limit (orange) and the stop (red) are fixed for that bar and re-priced at the next bar's open.
Triangles mark bars whose bid low reached limit - spread (the tester would fill a flat strategy there;
re-arming after fills is ignored, as in the classify-only run).
"""

import sys
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd

from level_visit import bar_frame, swing_lows
from trend_regimes import ROLLS

ROOT = Path(__file__).absolute().parent.parent
M30 = ROOT / "Reports" / "levels" / "breach_reclaim_20261003" / "m30_reference.csv"
BARS = ROOT / "Reports" / "trendlines" / "trendline_limit_20261005" / "trendline_limit_20261005_classify_bars.csv"
SPREAD = 0.25
UP, DOWN, PIVOT, LINE, LIMIT, STOP, MUTED, INK = ("#26a69a", "#ef5350", "#2962ff", "#7b1fa2", "#f57c00", "#c62828",
                                                  "#5f6368", "#202124")


def load(start, end):
    b = bar_frame(pd.read_csv(M30, index_col=0, parse_dates=[0]), pd.read_csv(ROLLS))
    o = pd.read_csv(BARS, parse_dates=["bar_time", "anchor1_time_ea", "anchor2_time_ea"])
    o = o[(o.bar_time >= start) & (o.bar_time < end) & (o.status_ea == "order")]
    pos = pd.Series(np.arange(len(b)), index=b.index)
    o = o.assign(t=pos.reindex(o.bar_time).to_numpy(), i=pos.reindex(o.anchor1_time_ea).to_numpy(),
                 j=pos.reindex(o.anchor2_time_ea).to_numpy())
    lo, hi = int(pos[b.index >= start].iloc[0]), int(pos[b.index < end].iloc[-1])
    return b, o, lo, hi


def draw(b, o, lo, hi, path, title, zoom=False):
    width_per = 26.0 if zoom else (2.4 if hi - lo > 400 else 7.0)
    left, right, top, bottom = 70, 300, 64, 46
    w, h = int(left + right + (hi - lo + 1) * width_per), 660 if zoom else 640
    view = b.iloc[lo:hi + 1]
    pmin, pmax = min(view.low.min(), o.stop_ea.min() if len(o) else np.inf), view.high.max()
    pad = (pmax - pmin) * 0.04
    pmin, pmax = pmin - pad, pmax + pad
    x = lambda k: left + (k - lo + 0.5) * width_per
    y = lambda p: top + (pmax - p) / (pmax - pmin) * (h - top - bottom)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
           'font-family="Segoe UI, Arial, sans-serif" font-size="12">',
           f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
           f'<text x="{left}" y="24" font-size="16" font-weight="600" fill="{INK}">{escape(title)}</text>',
           f'<text x="{left}" y="42" fill="{MUTED}">Rising lines through consecutive higher swing lows (5 bars each side, '
           '>= 10 bars apart, >= 0.02 x ATR per bar, one week), intact and departed by 1 x ATR. At each bar open the '
           'buy limit sits on the nearest such line below price;</text>',
           f'<text x="{left}" y="56" fill="{MUTED}">it is fixed for that bar and re-priced at the next open. '
           'Stop = limit - 0.5 x ATR(14). Classify-only run: no orders, no outcomes.</text>']
    step = 10 ** np.floor(np.log10((pmax - pmin) / 6))
    step *= [1, 2, 5, 10][int(np.searchsorted([1.5, 3.5, 7.5], (pmax - pmin) / 6 / step))]
    for p in np.arange(np.ceil(pmin / step) * step, pmax, step):
        svg.append(f'<line x1="{left}" x2="{w - right}" y1="{y(p):.1f}" y2="{y(p):.1f}" stroke="#eeeeee"/>')
        svg.append(f'<text x="{left - 6}" y="{y(p) + 4:.1f}" text-anchor="end" fill="{MUTED}">{p:,.0f}</text>')
    sn = b.session_number.to_numpy()
    last_label = -1e9
    for k in range(lo, hi + 1):
        new_day = k == lo or sn[k] != sn[k - 1]
        if new_day:
            svg.append(f'<line x1="{x(k) - width_per / 2:.1f}" x2="{x(k) - width_per / 2:.1f}" y1="{top}" '
                       f'y2="{h - bottom}" stroke="#ececec"/>')
        label = f"{b.index[k]:%H:%M}" if zoom else f"{b.index[k]:%d %b}"
        if (zoom and k % 2 == 0) or (not zoom and new_day and x(k) - last_label > 44):
            svg.append(f'<text x="{x(k):.1f}" y="{h - bottom + 16}" text-anchor="{"middle" if zoom else "start"}" '
                       f'fill="{MUTED}">{label}</text>')
            last_label = x(k)
    if zoom:
        svg.append(f'<text x="{left}" y="{h - 10}" fill="{MUTED}">{b.index[lo]:%a %d %b %Y}</text>')
    low = b.low.to_numpy()
    # Lines: one segment per (i, j) from its first anchor (clipped) to the last bar it carries the order.
    for (i, j), g in o.groupby(["i", "j"]):
        i, j, end = int(i), int(j), int(g.t.max())
        x0 = max(i, lo)
        p0 = low[i] + (low[j] - low[i]) * (x0 - i) / (j - i)
        p1 = low[i] + (low[j] - low[i]) * (end + 0.5 - i) / (j - i)
        svg.append(f'<line x1="{x(x0):.1f}" x2="{x(end) + width_per / 2:.1f}" y1="{y(p0):.1f}" y2="{y(p1):.1f}" '
                   f'stroke="{LINE}" stroke-width="1.1" opacity="0.6"><title>{escape(f"Line {b.index[i]:%d %b %H:%M} -> {b.index[j]:%d %b %H:%M}")}'
                   f'</title></line>')
        for a in (i, j):
            if lo <= a <= hi:
                svg.append(f'<circle cx="{x(a):.1f}" cy="{y(low[a]):.1f}" r="{5 if zoom else 3.5}" fill="none" '
                           f'stroke="{LINE}" stroke-width="1.5"/>')
    cw = max(1.0, width_per * (0.55 if zoom else 0.7))
    for k in range(lo, hi + 1):
        op, hh, ll, c = b.open.iloc[k], b.high.iloc[k], b.low.iloc[k], b.close.iloc[k]
        color = UP if c >= op else DOWN
        svg.append(f'<line x1="{x(k):.1f}" x2="{x(k):.1f}" y1="{y(hh):.1f}" y2="{y(ll):.1f}" stroke="{color}" '
                   f'stroke-width="{0.8 if width_per < 4 else 1}"/>')
        svg.append(f'<rect x="{x(k) - cw / 2:.1f}" y="{y(max(op, c)):.1f}" width="{cw:.1f}" '
                   f'height="{max(0.8, abs(y(op) - y(c))):.1f}" fill="{color}"/>')
    # Orders: one step per bar, the full bar width (fixed between two bar opens).
    sw = 2.6 if zoom else 1.6
    for r in o.itertuples():
        x0, x1 = x(r.t) - width_per / 2, x(r.t) + width_per / 2
        tip = (f"{r.bar_time:%d %b %H:%M}: line {r.line_ea:,.2f}, limit {r.limit_ea:,.2f}, stop {r.stop_ea:,.2f}, "
               f"ATR {r.atr_ea:.2f}, price {r.delta:.2f} ATR above the line")
        svg.append(f'<line x1="{x0:.1f}" x2="{x1:.1f}" y1="{y(r.limit_ea):.1f}" y2="{y(r.limit_ea):.1f}" stroke="{LIMIT}" '
                   f'stroke-width="{sw}"><title>{escape(tip)}</title></line>')
        svg.append(f'<line x1="{x0:.1f}" x2="{x1:.1f}" y1="{y(r.stop_ea):.1f}" y2="{y(r.stop_ea):.1f}" stroke="{STOP}" '
                   f'stroke-width="{sw * 0.6:.1f}" stroke-dasharray="{"4 3" if zoom else "2 2"}"/>')
        if low[r.t] <= r.limit_ea - SPREAD:
            yy = y(low[r.t]) + 8
            svg.append(f'<path d="M{x(r.t):.1f},{yy:.1f} l{6 if zoom else 5},{11 if zoom else 9} h-{12 if zoom else 10} z" '
                       f'fill="{LIMIT}" stroke="#ffffff" stroke-width="1"><title>{escape(tip + "; bid low reaches limit - spread")}'
                       f'</title></path>')
    pivots = swing_lows(low, b.contract.to_numpy(), 5)
    for i in pivots[(pivots >= lo) & (pivots <= hi)]:
        svg.append(f'<circle cx="{x(i):.1f}" cy="{y(low[i]) + (9 if zoom else 5):.1f}" r="2.4" fill="{PIVOT}"/>')
    if zoom and len(o):
        r = o.iloc[len(o) // 2]
        ax = x(r.t) + width_per / 2 + 6
        svg.append(f'<text x="{ax:.1f}" y="{y(r.limit_ea) - 6:.1f}" fill="{LIMIT}" font-weight="600">limit = line at this bar\'s open</text>')
        svg.append(f'<text x="{ax:.1f}" y="{y(r.stop_ea) + 15:.1f}" fill="{STOP}" font-weight="600">stop = limit - 0.5 x ATR</text>')
    lx, ly = w - right + 18, top + 8
    items = [("dot", PIVOT, "Confirmed swing low"), ("ring", LINE, "Line anchors"),
             ("line", LINE, "Rising line carrying the order"), ("step", LIMIT, "Buy limit (per bar)"),
             ("dash", STOP, "Stop (per bar)"), ("tri", LIMIT, "Bid low reaches limit - spread")]
    for n_item, (kind, color, text) in enumerate(items):
        yy = ly + 22 * n_item
        if kind == "dot":
            svg.append(f'<circle cx="{lx + 11}" cy="{yy}" r="3" fill="{color}"/>')
        elif kind == "ring":
            svg.append(f'<circle cx="{lx + 11}" cy="{yy}" r="4" fill="none" stroke="{color}" stroke-width="1.5"/>')
        elif kind == "line":
            svg.append(f'<line x1="{lx}" x2="{lx + 22}" y1="{yy + 4}" y2="{yy - 4}" stroke="{color}" stroke-width="1.2"/>')
        elif kind == "step":
            svg.append(f'<path d="M{lx},{yy + 3} h8 v-3 h7 v-3 h7" fill="none" stroke="{color}" stroke-width="2.4"/>')
        elif kind == "dash":
            svg.append(f'<line x1="{lx}" x2="{lx + 22}" y1="{yy}" y2="{yy}" stroke="{color}" stroke-width="1.6" '
                       'stroke-dasharray="4 3"/>')
        elif kind == "tri":
            svg.append(f'<path d="M{lx + 11},{yy - 6} l6,11 h-12 z" fill="{color}"/>')
        svg.append(f'<text x="{lx + 30}" y="{yy + 4}" fill="{INK}">{escape(text)}</text>')
    svg.append('</svg>')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(svg), encoding="utf-8")


def main(start, end, out, *flags):
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    b, o, lo, hi = load(start, end)
    zoom = "--zoom" in flags
    title = (f"Q20 resting buy limit, {start:%d %b %Y %H:%M} - {end:%H:%M}" if zoom else
             f"Q20 resting buy limits on rising trendlines, {start:%d %b} - {end - pd.Timedelta(days=1):%d %b %Y}")
    draw(b, o, lo, hi, Path(out), title, zoom)
    print(out, len(o), "order bars")


if __name__ == "__main__":
    main(*sys.argv[1:])
