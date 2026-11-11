"""Write verified research results and plot."""
import json
import shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from prepare_gg_large_candle import RUN,DOC
from audit_granularity_ledgers import digest
USD=chr(36)
def money(x):return f"{USD}{x:,.2f}"
def label(x):return "Normal GG" if x==0 else f"Midpoint >= {x:g}x"
MONEY={"net_dollars","sampled_equity_dd","worst_session_equity_dd","stress1_net","stress2_net",
       "affected_median_old_risk","affected_median_new_risk","affected_pnl_change"}
def table(f,cols):
    out=["| "+" | ".join(cols.values())+" |","|"+"|".join("---" for _ in cols)+"|"]
    for _,r in f.iterrows():
        cells=[]
        for c in cols:
            x=r[c]
            if c=="threshold":x=label(x)
            elif c in MONEY:x=money(x)
            elif c in ("mean_net_R","stress1_mean_R","stress2_mean_R"):x=f"{x:+.4f}"
            elif c in ("win_pct","tightened_pct"):x=f"{x:.1f}%"
            elif isinstance(x,(float,np.floating)):x=f"{x:.2f}"
            cells.append(str(x))
        out.append("| "+" | ".join(cells)+" |")
    return "\n".join(out)+"\n"


def main():
    v=json.loads((RUN/"verification.json").read_text())
    assert v["all_passed"] and digest(RUN/"summary.csv")==v["summary_sha256"]
    s=pd.read_csv(RUN/"summary.csv");s["period"]=s.period.astype(str)
    pairs=pd.read_csv(RUN/"paired.csv")
    fig,axs=plt.subplots(2,2,figsize=(11,7),layout="constrained")
    for col,era in enumerate(("2016-19","2020-26")):
        p=s.loc[s.period.eq(era)].sort_values("threshold")
        for row,(field,title) in enumerate((("net_dollars","Net profit"),("sampled_equity_dd","Maximum equity drawdown"))):
            ax=axs[row,col];ax.bar(np.arange(4),p[field],color=["#6b7280","#0891b2","#16a34a","#7c3aed"])
            ax.set_xticks(np.arange(4),["Normal","2.5x","3x","3.5x"]);ax.set_title(f"{era}: {title}")
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x,pos:f"{USD}{x:,.0f}"))
            ax.grid(axis="y",alpha=.2);ax.set_axisbelow(True)
            for i,value in enumerate(p[field]):
                ax.annotate(f"{USD}{value:,.0f}",(i,value),xytext=(0,5),textcoords="offset points",ha="center",fontsize=9)
            ax.margins(y=.18)
    fig.suptitle("GG: midpoint stop only on unusually large signals\nOne MNQ contract; 1R candle-close exit scales with stop; $1.05 costs",fontsize=13)
    (DOC/"img").mkdir(exist_ok=True);fig.savefig(DOC/"img/comparison.png",dpi=160);plt.close(fig)
    base=s.loc[s.threshold.eq(0)].set_index("period");primary=s.loc[s.threshold.eq(3)].set_index("period")
    passed=all(s.loc[s.threshold.eq(r)&s.period.eq(e),"net_per_equity_dd"].iloc[0]>base.loc[e,"net_per_equity_dd"]
               and s.loc[s.threshold.eq(r)&s.period.eq(e),"net_dollars"].iloc[0]>=base.loc[e,"net_dollars"]
               for r in (2.5,3,3.5) for e in ("2016-19","2020-26"))
    verdict="Meets the predeclared historical screen" if passed else "Does not meet the predeclared consistency screen"
    text=f"# GG midpoint stops on unusually large session candles\n\nCompleted 2026-11-10; protocol frozen 2026-11-09. Exploratory.\n\n**{verdict}.**\n\n"
    for e in ("2016-19","2020-26"):
        b,p=base.loc[e],primary.loc[e]
        text+=f"- **{e}, primary 3x:** net {money(b.net_dollars)} -> {money(p.net_dollars)}; equity DD {money(b.sampled_equity_dd)} -> {money(p.sampled_equity_dd)}; net/DD {b.net_per_equity_dd:.2f} -> {p.net_per_equity_dd:.2f}.\n"
    text+="""
## Exact test

Compare signal high-low range (including wicks) with the median range of **all
earlier M30 candles in the same full session**, both colours, at least five
earlier bars. Exclude the signal itself, later bars, and previous sessions.
Primary >=3x; neighbours >=2.5x and >=3.5x. Stop at high-low midpoint, nearest
tick; entry stays at green signal high. Larger-than-threshold candles qualify.
Research session starts 01:00; not US cash session only.

Per your answer, profit-exit threshold shrinks with the stop, keeping RR=1.
It requires an M30 close at/above the threshold, then exits at the next quote.
Full MT5 replay, one-minute OHLC, one MNQ contract, uncapped GG, no VWAP or hour
exclusions, normal 23:30/early-close flatten. $1.05 per completed position.
Primary sample ends before October 1, 2026. Midpoint halves price risk on
flagged trades, subject to rounding, but changes exits and subsequent entries.
It does not automatically halve portfolio drawdown. No position-size increase.

![Profit and equity drawdown](img/comparison.png)

## Era comparisons

"""
    for e in ("2016-19","2020-26","2016-26","2010-15"):
        text+=f"### {e}"+(" (secondary)" if e=="2010-15" else "")+"\n\n"
        text+=table(s.loc[s.period.eq(e)].sort_values("threshold"),
                    dict(threshold="Rule",trades="Trades",tightened_fills="Tightened",net_dollars="Net",
                         mean_net_R="Mean net R",sampled_equity_dd="Equity DD",net_per_equity_dd="Net/DD",
                         worst_session_equity_dd="Worst-session DD",profit_factor="Net PF",win_pct="Net win rate"))+"\n"
    text+="## Flagged trades and opportunity changes\n\n"
    text+=table(s.loc[s.threshold.eq(3)&s.period.isin(["2016-19","2020-26","2016-26"])],
                dict(period="Period",tightened_fills="Tightened",tightened_pct="Share",
                     affected_median_old_risk="Median full-candle risk",affected_median_new_risk="Median actual risk",
                     affected_stops="Stopped tightened trades"))+"\n"
    text+="Pairs match submission and entry timestamps. Their P&L difference excludes new opportunities after changed exits; it is not the whole-strategy change.\n\n"
    text+=table(pairs.loc[pairs.threshold.eq(3)&pairs.period.isin(["2016-19","2020-26","2016-26"])],
                dict(period="Period",matched_affected="Matched affected",affected_pnl_change="Their P&L change",
                     stopped_old_winners="Old winners now stopped",smaller_stopped_losses="Both paths stopped",
                     new_entries="New entries",missing_old_entries="Old entries absent"))+"\n"
    text+="## Cost sensitivity at 3x\n\n"
    text+=table(s.loc[s.threshold.isin([0,3])&s.period.isin(["2016-19","2020-26"])].sort_values(["period","threshold"]),
                dict(period="Period",threshold="Rule",net_dollars="Net at $1.05",stress1_net="Net at $2.05",
                     stress2_net="Net at $3.05",mean_net_R="Mean net R",stress1_mean_R="R at $2.05",
                     stress2_mean_R="R at $3.05"))+"\n"
    text+="## Annual results\n\n"
    text+=table(s.loc[s.threshold.isin([0,3])&s.period.str.fullmatch(r"\d{4}")].sort_values(["period","threshold"]),
                dict(period="Year",threshold="Rule",net_dollars="Net",mean_net_R="Mean net R",
                     sampled_equity_dd="Equity DD",net_per_equity_dd="Net/DD"))+"\n"
    text+="## Verification and limits\n\n"
    text+=f"- Disabled native run is byte-identical to saved GG: 26,505 trades. Compilation: zero errors and warnings.\n- Checked all {v['raw_minutes']:,} cached minute OHLC rows against raw CSV, aggregated 191,786 M30 bars, rebuilt every candidate reference and stop.\n"
    for j in v["jobs"]:
        text+=f"- {j['tag']}: {j['decisions']:,} candidate decisions; all {j['fills']:,} native trades match independent minute replay in entry/exit minute, requested/fill/stop/exit price and submission bar. Full-run gross equity DD {money(j['native_gross_equity_dd'])} matches MT5.\n"
    text+="""
- Report/ledger totals and economics agree. R uses actual initial risk.
  Simulator warmup trades before the native first entry are excluded.
- 36 focused tests passed: session isolation, future-bar exclusion, minimum
  history, median, thresholds, rounding, stop chronology, scaled exit, and
  existing weekly/intrabar behavior.
- Equity DD uses marked-to-market equity on generated OHLC quotes. Fees use
  native exit times; same-second fee-order sensitivity is recorded in CSV.
  No real-tick/slippage validation. R is not a fixed-dollar-risk sizing model.
- Reused history is exploratory, not untouched out of sample. No live strategy
  or default changed. Screenshot contract/date not identified or reproduced.
- Account-free portable startup failed because this build requires an account.
  After the user closed MT5 and authorized reopening, runs used the established
  tester. Failed-start logs remain; no trades came from those attempts.

## Evidence and reproduction

[Protocol](PROTOCOL.md), [prepare](../../../python/prepare_gg_large_candle.py),
[native runner](../../../python/run_gg_large_candle_native.py),
[analysis/checks](../../../python/analyze_gg_large_candle.py),
[stop helper](../../../mt5/experts/gg_large_candle_research.mqh),
[tests](../../../python/test_gg_large_candle.py).

Reports/gg_large_candle_20261109/ holds frozen inputs, native reports, ledgers,
candidate logs, equity observations, hashes and verification.
[Summary CSV](summary.csv), [paired entries](paired.csv).

Run with the project venv: python/prepare_gg_large_candle.py (new study only),
python/run_gg_large_candle_native.py (MT5 closed), then
python/analyze_gg_large_candle.py and python/report_gg_large_candle.py.
"""
    (DOC/"RESULTS.md").write_text(text,encoding="utf-8")
    for name in ("summary.csv","paired.csv"):shutil.copyfile(RUN/name,DOC/name)
    print(verdict);print("Saved",DOC/"RESULTS.md")


if __name__=="__main__":main()

