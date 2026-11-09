"""Independent cash-calendar, raw-minute, execution and net P&L audit of weak-close shorts."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from pandas.tseries.holiday import (
    AbstractHolidayCalendar, GoodFriday, Holiday, USLaborDay, USMartinLutherKingJr,
    USMemorialDay, USPresidentsDay, USThanksgivingDay, nearest_workday, sunday_to_monday,
)

from project_paths import PROJECT_ROOT
from rtl_weekly_engine import MINUTES, ROLLS


RUN = PROJECT_ROOT / "Reports/mnq_weak_close_20261106"
NY, CHICAGO = ZoneInfo("America/New_York"), ZoneInfo("America/Chicago")
START, END = "2016-01-01", "2026-09-30"
PERIODS = {
    "2016-19": (START, "2019-12-31"),
    "2020-26": ("2020-01-01", END),
    "2016-26": (START, END),
    "post-paper": ("2020-05-04", END),
}


class CashClosures(AbstractHolidayCalendar):
    # Cash equity schedule, independent of CME's open/flattening calendar.
    # See exchange_calendars' XNYS and us_holidays definitions.
    rules = [Holiday("New Year", month=1, day=1, observance=sunday_to_monday),
             USMartinLutherKingJr, USPresidentsDay, GoodFriday, USMemorialDay,
             Holiday("Juneteenth", month=6, day=19, start_date="2022-01-01", observance=nearest_workday),
             Holiday("Independence", month=7, day=4, observance=nearest_workday),
             USLaborDay, USThanksgivingDay,
             Holiday("Christmas", month=12, day=25, observance=nearest_workday)]


def cash_sessions():
    # Include the previous session needed for the first reported January trade.
    weekdays = pd.bdate_range("2015-12-01", END)
    closed = CashClosures().holidays(weekdays[0], weekdays[-1])
    memorials = pd.to_datetime(["2018-12-05", "2025-01-09"])
    dates = weekdays.difference(closed.union(memorials))
    black_fridays = USThanksgivingDay.dates(weekdays[0], weekdays[-1]) + pd.Timedelta(days=1)
    return {d: 13 if (d in black_fridays or (d.month, d.day) in {(7, 3), (12, 24)}) else 16
            for d in dates}


def raw_clock(day, hour, minute):
    # Invert the conversion independently for both winter and summer dates.
    eastern = datetime.combine(day.date(), time(hour, minute), tzinfo=NY)
    synth = eastern.astimezone(CHICAGO).replace(tzinfo=None) + timedelta(hours=8)
    assert synth.date() == day.date() and synth.hour == hour + 7
    return synth.strftime("%H:%M:%S")


def minute_records():
    """Select only the needed fields from the original continuous export, carrying OHLC direction."""
    wanted = {"19:59:00", "22:30:00", "22:31:00", "22:59:00", "23:00:00"}
    records = {}
    last_direction = 0.
    for block in pd.read_csv(MINUTES, sep="\t", chunksize=180_000,
                             usecols=["<DATE>", "<TIME>", "<OPEN>", "<HIGH>", "<LOW>", "<CLOSE>", "<TICKVOL>"]):
        directions = np.sign(block["<CLOSE>"] - block["<OPEN>"]).replace(0, np.nan)
        prev = directions.shift().ffill().fillna(last_direction)
        nonflat = directions.dropna()
        if len(nonflat):
            last_direction = float(nonflat.iloc[-1])
        chosen = block["<TIME>"].isin(wanted) & block["<DATE>"].between("2015.12.01", "2026.09.30")
        for ix, row in block.loc[chosen].iterrows():
            key = pd.Timestamp(row["<DATE>"]), row["<TIME>"]
            assert key not in records
            o, h, l, c = [float(row[k]) for k in ("<OPEN>", "<HIGH>", "<LOW>", "<CLOSE>")]
            n = int(row["<TICKVOL>"])
            assert min(o, c) >= l and max(o, c) <= h and n > 0, key
            records[key] = (o, h, l, c, n, prev.loc[ix])
    return records


def first_second(bar):
    o, h, l, c, n, _ = bar
    return (30 if n == 1 else 1) if h == l else 0


def next_quote(bar, next_minute):
    """Price and seconds after 15:30:00 of the quote *after* the signal quote."""
    o, h, l, c, n, prev = bar
    if h == l:
        return (20, o) if n >= 4 else (60 + first_second(next_minute), next_minute[0])
    first_low = c > o or (c == o and prev < 0)
    extrema = [l, h] if first_low else [h, l]
    if n >= 4:
        return 20, extrema[0]
    distinct_shadows = [p for p in extrema if p not in (o, c)]
    if len(distinct_shadows) == 2:
        return 20, extrema[0]
    if distinct_shadows:
        return 30, distinct_shadows[0]
    return (30 if n == 2 else 59), c


def period_metrics(gross_values):
    # All entries are one round trip per eligible date; use actual chronological order.
    gross = np.array(gross_values, dtype=float)
    net = gross - 1.05
    losses = -net[net < 0].sum()
    equity = np.r_[0., np.cumsum(net)]
    return dict(trades=len(net), gross_dollars=gross.sum(), net_dollars=net.sum(),
                avg_net_dollars=net.mean(), win_pct=100. * (net > 0).mean(),
                profit_factor=net[net > 0].sum() / losses if losses else np.nan,
                daily_close_dd=(np.maximum.accumulate(equity) - equity).max(),
                stress1_net_dollars=net.sum() - len(net), stress2_net_dollars=net.sum() - 2 * len(net))


def reconstruct():
    records = minute_records()
    schedule = cash_sessions()
    days = list(schedule)
    rolls = pd.read_csv(ROLLS, parse_dates=["date"]).set_index("date")["instrument_id"].sort_index()
    ids = rolls.reindex(pd.DatetimeIndex(days), method="ffill")
    out = []
    for prior, day in zip(days, days[1:]):
        if day < pd.Timestamp(START):
            continue
        prior_close = records.get((prior, raw_clock(prior, schedule[prior] - 1, 59)))
        mark = records.get((day, raw_clock(day, 15, 30)))
        next_bar = records.get((day, raw_clock(day, 15, 31)))
        exit_bar = records.get((day, raw_clock(day, 16, 0)))
        row = dict(date=day, prior_date=prior, contract_id=ids[day], prior_contract_id=ids[prior])
        if schedule[day] == 13:
            row["reason"] = "early_close"
        elif ids[day] != ids[prior]:
            row["reason"] = "contract_change"
        elif None in (prior_close, mark, next_bar, exit_bar):
            row["reason"] = "missing_minute"
        else:
            second, entry = next_quote(mark, next_bar)
            assert second > first_second(mark)
            row.update(reason="eligible", weak=mark[0] < prior_close[3], prior_close=prior_close[3],
                       signal_price=mark[0], entry_quote=entry, entry_quote_second=second,
                       entry_1531=next_bar[0], exit_price=exit_bar[0])
        out.append(row)
    return pd.DataFrame(out).set_index("date")


def main():
    expected = reconstruct()
    saved = pd.read_csv(RUN / "sessions.csv", parse_dates=["date", "prior_date"]).set_index("date")
    assert expected.index.equals(saved.index), ("cash calendar disagreement",
                                                 expected.index.symmetric_difference(saved.index))
    normalized = saved.reason.mask(saved.reason.str.startswith("missing_"), "missing_minute")
    assert np.array_equal(expected.reason, normalized), expected.loc[expected.reason.ne(normalized)]
    usable = expected.loc[expected.reason.eq("eligible")]
    observed = saved.loc[usable.index]
    for key in ("prior_date", "weak", "prior_close", "signal_price", "entry_quote", "entry_quote_second",
                "entry_1531", "exit_price", "contract_id", "prior_contract_id"):
        assert np.array_equal(usable[key], observed[key]), (key, observed.loc[usable[key].ne(observed[key])].head())
    row_counts = {}
    for name in ("summaries", "annual"):
        published = pd.read_csv(RUN / f"{name}.csv")
        id_col = "period" if name == "summaries" else "year"
        keys = published[[id_col, "fill", "variant"]]
        assert not keys.duplicated().any()
        groups = (list(PERIODS) if id_col == "period" else sorted(usable.index.year.unique()))
        assert len(published) == len(groups) * 2 * 3
        for row in published.itertuples(index=False):
            dates = usable.loc[slice(*PERIODS[row.period])] if name == "summaries" else usable.loc[usable.index.year == row.year]
            if row.variant == "weak":
                dates = dates.loc[dates.weak.eq(True)]
            elif row.variant == "nonweak":
                dates = dates.loc[dates.weak.eq(False)]
            else:
                assert row.variant == "all"
            field = {"next_quote": "entry_quote", "minute_open": "entry_1531"}[row.fill]
            measures = period_metrics((dates[field] - dates.exit_price) * 2.0)
            for k, v in measures.items():
                assert np.isclose(v, getattr(row, k), rtol=1e-8, atol=1e-5, equal_nan=True), (row, k, v)
        row_counts[name] = len(published)
    sources = [MINUTES, ROLLS, RUN / "sessions.csv", RUN / "summaries.csv", RUN / "annual.csv"]
    hashes = {}
    for f in sources:
        with f.open("rb") as stream:
            hashes[f.name] = hashlib.file_digest(stream, "sha256").hexdigest()
    schedule = cash_sessions()
    report = dict(all_passed=True, cash_sessions_checked=len(expected), eligible_dates=len(usable),
                  reason_counts=expected.reason.value_counts().to_dict(), reference_after_half_day=sum(
                      schedule[d] == 13 for d in set(usable.prior_date)),
                  weak_days=int(usable.weak.sum()), rows_verified=row_counts,
                  checks=["XNYS holidays and half days, ET/Chicago clock",
                          "immediately preceding cash date and same actual instrument ID",
                          "original NQ OHLC/volume, next simulated quote or 15:31 open, exit",
                          "session classification, chronological P&L, fees, drawdown and cost stress"],
                  sha256=hashes)
    (RUN / "independent_verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
