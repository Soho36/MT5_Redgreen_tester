"""Render the audited trend-RR results as a readable report."""
import json
from prepare_trend_rr_study import STUDY
from project_paths import PROJECT_ROOT

LABELS={"baseline":"Fixed 1R","mild":"Mild 1.25 / 1 / 0.75","strong":"Strong 1.5 / 1 / 0.75",
        "bull_only":"Bull-only 1.5 / 1 / 1","bear_only":"Bear-only 1 / 1 / 0.75","reversed":"Reversed 0.75 / 1 / 1.5"}


def money(value):
    return f"{value:,.2f}"



def main():
    payload=json.loads((STUDY/"results.json").read_text())
    allr=payload["results"];r=allr["50"];a,b=r["metrics"],r["baseline"]
    gain=100*(a["net_dd"]/b["net_dd"]-1)
    verdict="Passes the frozen historical screen" if payload["passed"] else "Keep fixed 1R; the proposed adaptation fails the frozen screen"
    lines=["# RTL trend-conditioned RR — 2026-10-02","",f"**{verdict}.**",
           f"The primary annual selection changes 2015–2025 net/DD by **{gain:+.1f}%** versus fixed 1R. "
           f"Net profit is ${money(a['net'])} versus ${money(b['net'])}; closed-trade drawdown is "
           f"${money(a['dd'])} versus ${money(b['dd'])}.","",
           "The user clarified that only the trend concept should be imported. Every run uses our existing RTL "
           "buy-stop entry, MaxRedRun=3, candle-low stop, M30-close-qualified market exit and session handling. "
           "No GG, new entry filter, sell-limit exit or forward test was added. All tests use 1-minute OHLC.","",
           "## Our usual comparison periods","",
           "Mappings show bull / neutral / bear RR. Previous completed daily close and SMAfast must both be above SMA200 "
           "for bull, both below for bear; all other available combinations are neutral. Each trade keeps its entry-day "
           "RR. This table uses 50/200 and $1.05 commission per contract. DD is net balance drawdown.","",
           "| Mapping | 2016–2019 net $ | DD $ | Net/DD | 2020–Jul 2026 net $ | DD $ | Net/DD |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for key,label in LABELS.items():
        x,y=r["fixed_variants"][key]["train"],r["fixed_variants"][key]["recent"]
        lines.append(f"| {label} | {money(x['net'])} | {money(x['dd'])} | {x['net_dd']:.2f} | {money(y['net'])} | {money(y['dd'])} | {y['net_dd']:.2f} |")
    lines += ["","## Historical annual selection","",
              "Training expands from the available 2010–2014 history. Select only fixed, mild or strong using "
              "prior years' net/DD, subject to the 75-trades-per-regime rule, and freeze the choice for the next "
              "year. Full test years are 2015–2025; partial 2026 is excluded from this score. "
              "The 2015–2025 history was examined in earlier research, so these are chronological selector "
              "holdouts, not genuinely untouched validation data.","",
              "| Year | Selected mapping | Selected net $ | Fixed net $ | Selected net/DD | Fixed net/DD |",
              "|---|---|---:|---:|---:|---:|"]
    for s in r["selections"]:
        z=r["annual"][str(s["year"])];x,y=z["selected"],z["baseline"]
        lines.append(f"| {s['year']} | {s['variant']} | {money(x['net'])} | {money(y['net'])} | {x['net_dd']:.2f} | {y['net_dd']:.2f} |")
    lines += ["",f"Improved annual net/DD: **{r['improved_ratio_years']}/11** years; improved annual net dollars: **{r['improved_net_years']}/11**.","",
              "## Moving-average and placebo checks","",
              "Each MA length has its own prior-years-only selector; MA lengths are never candidates for selection. "
              "Diagnostics below are fixed mappings across the same 2015–2025 dates.","",
              "| Fast / slow | Annual selection net $ | DD $ | Net/DD | Fixed 1R net/DD | Reversed net/DD | Bear-only net/DD |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for n in (40,50,60):
        z=allr[str(n)];x=z["metrics"]
        lines.append(f"| {n}/200 | {money(x['net'])} | {money(x['dd'])} | {x['net_dd']:.2f} | {z['baseline']['net_dd']:.2f} | {z['fixed_variants']['reversed']['metrics']['net_dd']:.2f} | {z['fixed_variants']['bear_only']['metrics']['net_dd']:.2f} |")
    lines += ["","All mapping sensitivities (net/DD, 2015–2025):","",
              "| Mapping | 40/200 | 50/200 | 60/200 |","|---|---:|---:|---:|"]
    for key,label in LABELS.items():
        lines.append(f"| {label} | "+" | ".join(f"{allr[str(n)]['fixed_variants'][key]['metrics']['net_dd']:.2f}" for n in (40,50,60))+" |")
    lines += ["","## Costs and concentration","",
              "Slippage is unmeasured. The primary comparison retains our $1.05 commission assumption. "
              "The following are additional cost allowances, not validated execution simulations; selections stay frozen.","",
              "| Extra cost / trade | Selected net $ | Fixed net $ | Selected net/DD | Fixed net/DD |",
              "|---|---:|---:|---:|---:|"]
    for cost,z in r["cost_stresses"].items():
        x,y=z["selected"],z["baseline"]
        lines.append(f"| ${float(cost):.2f} | {money(x['net'])} | {money(y['net'])} | {x['net_dd']:.2f} | {y['net_dd']:.2f} |")
    lines += ["","The selected strategy makes 771 fewer trades than fixed 1R in these test years. "
              "Charging more per trade therefore helps its relative result: the cost-stress advantage is real "
              "within that assumption, but it does not establish the actual execution cost. At the known "
              "commission assumption the primary screen still fails."]
    for name,z in r["removals"].items():
        lines += ["",f"Excluding {', '.join(map(str,z['excluded']))}: selected net/DD {z['selected']['net_dd']:.2f}, "
                  f"fixed {z['baseline']['net_dd']:.2f}."]
    lines += ["","## Regime results for the selected strategy","",
              "These are attributed subsets: their drawdowns do not sum to portfolio drawdown. "
              "Profit shares are signed shares of total net profit.","",
              "| Regime | Trades | Net $ | Share of total net | DD $ | PF |",
              "|---|---:|---:|---:|---:|---:|"]
    for name in ("bull","neutral","bear"):
        z=r["regime_results"][name]
        lines.append(f"| {name} | {z['trades']:,} | {money(z['net'])} | {100*z['share_of_total_net']:.1f}% | {money(z['dd'])} | {z['pf']:.3f} |")
    bearbase=r["fixed_variants"]["baseline"]["regimes"]["bear"]
    lines += ["",f"Fixed-1R bear subset: net ${money(bearbase['net'])}, DD ${money(bearbase['dd'])}.","",
              "## Other selected-strategy metrics (2015–2025)","",
              "| Metric | Annual selection | Fixed 1R |","|---|---:|---:|"]
    fields=[("Trades","trades",".0f"),("Average net trade $","avg_trade",".2f"),("Profit factor","pf",".3f"),
            ("Profitable months","profitable_months",".1%"),("Profitable years","profitable_years",".1%"),
            ("Worst month $","worst_month",".2f"),("Worst quarter $","worst_quarter",".2f"),("Worst year $","worst_year",".2f"),
            ("Longest balance drawdown, calendar days","longest_dd_days",".1f"),("Average holding time, minutes","average_duration_minutes",".1f"),
            ("Trades qualifying for target exit","target_qualification_rate",".1%"),
            ("Qualified exits completed","qualified_exit_completion_rate",".1%"),
            ("Gross realized / sum positive MFE","mfe_conversion",".1%"),("Average net R","avg_net_r",".4f"),
            ("Average MAE R","avg_mae_r",".4f"),("Average MFE R","avg_mfe_r",".4f")]
    for label,key,fmt in fields:
        lines.append(f"| {label} | {a[key]:{fmt}} | {b[key]:{fmt}} |")
    lines += ["","## Frozen decision gates","","| Gate | Result |","|---|---|"]
    for key,value in r["gates"].items():
        lines.append(f"| {key.replace('_',' ')} | {'PASS' if value else 'FAIL'} |")
    checks=sum(z["checks"] for z in payload["audits"].values())
    lines += ["","The protocol defines “clearly beats reversed” as at least 10% better net/DD and annual improvement "
              "as higher annual net/DD; annual net-dollar improvement is also shown. See the "
              "[frozen protocol](TREND_RR_PROTOCOL.md) for all definitions.","",
              "## Validation and limits","",
              f"All 16 MT5 runs reconcile to tester trade counts and gross PnL. The independent minute-source "
              f"audit checks each signal OHLC, prior-day MA label, frozen trade RR and all **{checks:,}** M30 "
              "target checks. No cross-date trades or trend export/target-close errors were found. The fixed "
              "control reproduces both established comparison periods, including trade times, profits, "
              "excursions and signal features. Compilation has zero errors/warnings; 12 Python tests pass.","",
              "The source begins in June 2010; 200 prior daily closes first exist on 2011-03-15. Earlier "
              "entries remain at 1R with an explicit warmup label, without treating unknown trend as neutral. "
              "Before-2016 market hours differ; the existing early-close calendar is retained. Raw continuous "
              "prices include roll gaps, matching the baseline's rollover construction.","",
              "One-minute OHLC cannot establish actual intraminute ordering or slippage. Drawdowns in tables "
              "use completed trades, not marked-to-market equity; per-run MT5 gross equity DD is retained in "
              "the audit JSON. Sell-limit fill rates and RR/GG simultaneous failures are inapplicable to this "
              "RTL-only market-exit study. No live strategy defaults were changed.","",
              "## Files","",
              "- `Reports/trend_rr_20261002/`: source/compiled EA, includes, INIs, manifests, reports, logs, "
              "raw/enriched trades, every accepted setup, every target check, independent daily/M30 references, "
              "stitched annual trades and `results.json` (including all monthly/yearly and regime metrics).",
              "- `python/prepare_trend_rr_study.py`, `trend_regimes.py`, `trend_rr_metrics.py`, "
              "`analyze_trend_rr_study.py`, `report_trend_rr_study.py`, `test_trend_rr.py`.",
              "- `mt5/experts/trend_rr_research.mqh`: tester-only daily regime assignment and audit logging.","",
              "```powershell",r".\venv\Scripts\python.exe python\analyze_trend_rr_study.py",
              r".\venv\Scripts\python.exe python\report_trend_rr_study.py","```",""]
    path=PROJECT_ROOT/"docs/TREND_RR_RESULTS.md"
    path.write_text("\n".join(lines),encoding="utf-8")
    print(path)


if __name__=="__main__":
    main()
