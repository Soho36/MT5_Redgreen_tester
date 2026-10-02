"""Audit the frozen RTL trend experiment and evaluate annual walk-forward."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

from analyze_averaging_study import validate
from prepare_trend_rr_study import STUDY
from trend_regimes import VARIANTS, ROLLS, build_m30_reference
from trend_rr_metrics import metrics, regime_metrics, walk_forward
from verify_location_validation import read_rows
from project_paths import PROJECT_ROOT

TIMES=("entry_time","exit_time","qualified_time","signal_time")
PERIODS={"train":("2016-01-01","2020-01-01"),"recent":("2020-01-02","2026-07-14"),
         "walkforward":("2015-01-01","2026-01-01")}
REGIME_NAMES={1:"bull",0:"neutral",-1:"bear",-2:"warmup"}


def mt5_csv(path):
    return pd.read_csv(path,sep="\t",encoding="utf-16")


def timestamp(series):
    return pd.to_datetime(series,format="%Y.%m.%d %H:%M:%S")


def audit_job(study,job,daily,bars):
    rows=read_rows(study/job["csv"])
    stats=read_rows(study/job["csv"].replace(".csv","_stats.csv"))[0]
    validate(rows,stats,dict(job,distance=0))
    assert stats["run_tag"]==job["tag"]
    for key in ("trend_export_errors","trend_close_errors"):
        assert int(stats[key])==0,(job["tag"],key)
    assert int(stats["fast_days"])==job["fast"]
    assert float(stats["bull_rr"])==job["bull"] and float(stats["bear_rr"])==job["bear"]
    t=mt5_csv(study/job["csv"])
    for c in TIMES:
        t[c]=timestamp(t[c])
    t["previous_day"]=pd.to_datetime(t.previous_day,format="%Y.%m.%d")
    t["regime_name"]=t.regime.map(REGIME_NAMES)
    ref=daily.reindex(t.entry_time.dt.normalize()).reset_index(drop=True)
    assert np.array_equal(t.regime_name,ref[f"regime{job['fast']}"]),"regime mismatch"
    assert np.allclose(t.previous_close,ref.previous_close,atol=1e-7,rtol=0)
    assert np.array_equal(t.previous_day,ref.previous_date)
    assert (t.previous_day<t.entry_time.dt.normalize()).all(),"current/future daily data"
    known=t.regime!=-2
    assert np.allclose(t.loc[known,"sma_fast"],ref.loc[known,f"sma{job['fast']}"],atol=1e-7,rtol=0)
    assert np.allclose(t.loc[known,"sma200"],ref.loc[known,"sma200"],atol=1e-7,rtol=0)
    rr=np.where(t.regime==1,job["bull"],np.where(t.regime==-1,job["bear"],1.))
    assert np.array_equal(t.assigned_rr,rr),"RR mapping"
    signal=bars.reindex(t.signal_time).reset_index(drop=True)
    for field in ("open","high","low","close"):
        assert np.array_equal(t[f"signal_{field}"],signal[field]),("signal",field)
    assert (t.signal_close<t.signal_open).all()
    assert (t.signal_time<t.entry_time).all()
    assert (t.red_run.between(1,3)).all()
    assert np.array_equal(t.signal_low,t.initial_stop)
    assert np.allclose(t.initial_risk_money,2*(t.base_entry-t.initial_stop))
    assert t.ticket.is_unique
    checks=mt5_csv(study/f"{job['tag']}_checks.csv")
    checks["check_time"]=timestamp(checks.check_time)
    checks["bar_time"]=timestamp(checks.bar_time)
    assert checks.ticket.isin(t.ticket).all()
    lookup=t.set_index("ticket").reindex(checks.ticket).reset_index(drop=True)
    assert np.array_equal(checks.assigned_rr,lookup.assigned_rr),"RR changed while open"
    assert np.array_equal(checks.regime,lookup.regime)
    expected=lookup.base_entry+(lookup.base_entry-lookup.initial_stop)*lookup.assigned_rr
    assert np.allclose(checks.target,expected,atol=1e-7,rtol=0)
    assert np.array_equal(checks.bar_close,bars.reindex(checks.bar_time).close),"check read wrong M30 close"
    assert np.array_equal(checks.qualified,(checks.bar_close>=checks.target).astype(int))
    assert (checks.bar_time<checks.check_time).all()
    assert (checks.check_time>=lookup.entry_time).all() and (checks.check_time<=lookup.exit_time).all()
    first=checks[checks.qualified==1].groupby("ticket").check_time.min()
    actual=t.set_index("ticket").qualified_time.dropna().sort_index()
    pd.testing.assert_series_equal(first.sort_index(),actual,check_names=False)
    assert (t.loc[t.qualified_time.notna(),"qualified_time"]==t.loc[t.qualified_time.notna(),"exit_time"]).all()
    signals=mt5_csv(study/f"{job['tag']}_signals.csv")
    signals["signal_time"]=timestamp(signals.signal_time)
    signals["submission_time"]=timestamp(signals.submission_time)
    assert (signals.submission_time>signals.signal_time).all()
    assert (signals.strategy=="RR").all()
    assert t.signal_time.isin(signals.signal_time).all()
    refsig=bars.reindex(signals.signal_time).reset_index(drop=True)
    for field in ("open","high","low","close"):
        assert np.array_equal(signals[field],refsig[field])
    t["risk_points"]=t.base_entry-t.initial_stop
    t["mae_r"]=t.mae_money/t.initial_risk_money
    t["mfe_r"]=t.mfe_money/t.initial_risk_money
    t["net_profit"]=t.trade_profit-1.05
    t["commission"]=1.05
    t["weekday"]=t.entry_time.dt.day_name()
    t["duration_minutes"]=(t.exit_time-t.entry_time).dt.total_seconds()/60
    t["entry_window"]=t.entry_time.dt.strftime("%H:00")
    for hour in (1,23):
        mask=t.entry_time.dt.hour==hour
        t.loc[mask,"entry_window"]=t.loc[mask,"entry_time"].dt.floor("30min").dt.strftime("%H:%M")
    rolls=pd.read_csv(ROLLS,parse_dates=["date"])
    contracts=pd.merge_asof(t[["entry_time"]].sort_values("entry_time"),rolls,left_on="entry_time",right_on="date",direction="backward")
    t["contract"]=contracts.symbol.values
    t["instrument_id"]=contracts.instrument_id.values
    t["exit_label"]=np.where(t.exit_reason==4,"stop",np.where(t.qualified_time.notna(),"qualified_target","session_flatten"))
    t.to_csv(study/f"{job['tag']}_enriched.csv",index=False)
    return t,dict(trades=len(t),signals=len(signals),checks=len(checks),qualified_checks=int(checks.qualified.sum()),
                  gross_equity_dd=float(stats["equity_dd"]),source_contracts=int(t.instrument_id.nunique()))


def audit_baseline(t):
    for period,(start,end) in ((k,v) for k,v in PERIODS.items() if k!="walkforward"):
        old=pd.DataFrame(read_rows(PROJECT_ROOT/"Reports/rr_clean_20261001"/f"runband_rrclean_20261001_{period}_1p00_1.00.csv"))
        old["entry_time"]=timestamp(old.entry_time);old["exit_time"]=timestamp(old.exit_time)
        new=t[(t.entry_time>=start)&(t.entry_time<end)].reset_index(drop=True)
        assert len(old)==len(new),(period,len(old),len(new))
        for field in ("entry_time","exit_time"):
            assert np.array_equal(old[field],new[field])
        for field in ("trade_profit","mae_money","mfe_money","candle_range","red_run","location"):
            assert np.allclose(old[field].astype(float),new[field],rtol=0,atol=1e-9),(period,field)


def evaluate(tables,study=STUDY):
    output={}
    for fast,variants in tables.items():
        stitched,selections=walk_forward(variants)
        start,end=PERIODS["walkforward"]
        base=variants["baseline"]
        m=metrics(stitched,start,end); b=metrics(base,start,end)
        annual={str(y):dict(selected=metrics(stitched,f"{y}-01-01",f"{y+1}-01-01"),
                            baseline=metrics(base,f"{y}-01-01",f"{y+1}-01-01")) for y in range(2015,2026)}
        improved_ratio=sum(v["selected"]["net_dd"]>v["baseline"]["net_dd"] for v in annual.values())
        improved_net=sum(v["selected"]["net"]>v["baseline"]["net"] for v in annual.values())
        delta={int(y):v["selected"]["net"]-v["baseline"]["net"] for y,v in annual.items()}
        largest=max(delta,key=delta.get)
        removals={}
        for name,excluded in (("without_2020_2021",[2020,2021]),("without_largest_gain_year",[largest])):
            a=metrics(stitched[~stitched.entry_time.dt.year.isin(excluded)],start,end)
            c=metrics(base[~base.entry_time.dt.year.isin(excluded)],start,end)
            removals[name]=dict(excluded=excluded,selected=a,baseline=c,beneficial=a["net_dd"]>c["net_dd"])
        fixed={name:dict(metrics=metrics(t,start,end),regimes=regime_metrics(t,start,end),
                         train=metrics(t,*PERIODS["train"]),recent=metrics(t,*PERIODS["recent"])) for name,t in variants.items()}
        stresses={str(cost):dict(selected=metrics(stitched,start,end,cost),baseline=metrics(base,start,end,cost)) for cost in (1.,2.)}
        gates=dict(ratio_gain_10_percent=m["net_dd"]>=1.1*b["net_dd"],net_retained_90_percent=m["net"]>=.9*b["net"],
                   dd_not_increased=m["dd"]<=b["dd"],improved_60_percent_years=improved_ratio/11>=.6,
                   beats_reversed_10_percent=m["net_dd"]>=1.1*fixed["reversed"]["metrics"]["net_dd"],
                   survives_without_2020_2021=removals["without_2020_2021"]["beneficial"],
                   survives_without_best_year=removals["without_largest_gain_year"]["beneficial"],
                   survives_extra_2_cost=stresses["2.0"]["selected"]["net_dd"]>stresses["2.0"]["baseline"]["net_dd"])
        output[str(fast)]=dict(metrics=m,baseline=b,selections=selections,annual=annual,fixed_variants=fixed,
                               regime_results=regime_metrics(stitched,start,end),improved_ratio_years=improved_ratio,
                               improved_net_years=improved_net,removals=removals,cost_stresses=stresses,gates=gates)
        stitched.to_csv(study/f"stitched_f{fast}.csv",index=False)
    neighbor=all(output[str(n)]["metrics"]["net_dd"]>output[str(n)]["baseline"]["net_dd"] for n in (40,60))
    output["50"]["gates"]["both_neighbor_lengths_beneficial"]=neighbor
    return output


def main(study=STUDY):
    manifest=json.loads((study/"manifest.json").read_text(encoding="utf-8"))
    daily=pd.read_csv(study/"daily_reference.csv",index_col="date",parse_dates=["date","previous_date"])
    path=study/"m30_reference.csv"
    bars=pd.read_csv(path,index_col="bar_time",parse_dates=["bar_time"]) if path.exists() else build_m30_reference(path)
    tables={n:{} for n in (50,40,60)}; audits={}
    for job in manifest["jobs"]:
        assert (study/f"{job['tag']}.completed.json").exists(),f"Run unfinished: {job['tag']}"
        t,audit=audit_job(study,job,daily,bars)
        tables[job["fast"]][job["variant"]]=t
        audits[job["tag"]]=audit
        print(f"AUDIT PASS {job['tag']}: {len(t)} trades, {audit['checks']} target checks",flush=True)
    baseline=tables[50]["baseline"]
    audit_baseline(baseline)
    for n in (40,60):
        t=baseline.copy()
        ref=daily.reindex(t.entry_time.dt.normalize())
        t["regime_name"]=ref[f"regime{n}"].values
        t["regime"]=t.regime_name.map({v:k for k,v in REGIME_NAMES.items()})
        t["sma_fast"]=ref[f"sma{n}"].values
        t.loc[t.regime_name=="warmup","sma_fast"]=0.
        tables[n]["baseline"]=t
    results=evaluate(tables,study)
    payload=dict(audits=audits,results=results,passed=all(results["50"]["gates"].values()),
                 cost_note="Primary $1.05 commission; unmeasured slippage shown as +$1/+2 costs, not validated fills.")
    (study/"results.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
    for n,r in results.items():
        a,b=r["metrics"],r["baseline"]
        print(f"MA{n}: stitched net ${a['net']:.2f}, DD ${a['dd']:.2f}, net/DD {a['net_dd']:.3f}; baseline {b['net_dd']:.3f}; improved years {r['improved_ratio_years']}/11")
    print("Frozen decision gates:",results["50"]["gates"])


if __name__=="__main__":
    main(Path(sys.argv[1]) if len(sys.argv)>1 else STUDY)
