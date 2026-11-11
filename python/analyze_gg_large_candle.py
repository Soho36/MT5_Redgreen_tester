"""Independent decisions, minute replay, native economics and equity for GG midpoint stops."""
import json
import numpy as np
import pandas as pd
import rtl_weekly_engine as engine
from prepare_gg_large_candle import RUN, DOC
from project_paths import PROJECT_ROOT as ROOT
from audit_granularity_ledgers import digest, ensure_audited
from analyze_rtl_vwap_cross import parse_report, economics, INSTRUMENTS
from verify_exclude16_replay import DTYPE, equity_metrics, maxdd
from verify_rtl_failed_breakout_short import load_quote_index

PERIODS = {"2010-15": ("2010-01-01", "2016-01-01"),
           "2016-19": ("2016-01-01", "2020-01-01"),
           "2020-26": ("2020-01-01", "2026-10-01"),
           "2016-26": ("2016-01-01", "2026-10-01")}
TICK = .25


def features(frame):
    """Prior-only expanding session median; current candle never enters its reference."""
    f = frame.copy()
    f["session"] = f.bar_time.dt.normalize()
    f["range"] = f.high-f.low
    valid = f.bar_time.dt.hour.ge(1)
    earlier = f.loc[valid].groupby("session")["range"]
    f["prior_count"] = 0
    f["median"] = 0.0
    f.loc[valid, "prior_count"] = earlier.cumcount()
    f.loc[valid, "median"] = earlier.transform(lambda s: s.expanding().median().shift()).fillna(0)
    f["ratio"] = np.divide(f["range"], f["median"], out=np.zeros(len(f)), where=f["median"].gt(0))
    return f


def stops(f, ratio, min_prior=5, tick=TICK):
    if not np.isfinite(ratio) or ratio < 0 or (0 < ratio <= 1) or min_prior < 1 or tick <= 0:
        raise ValueError("Invalid large-candle parameters")
    flag = (ratio > 0) & f.prior_count.ge(min_prior) & f["median"].gt(0) & (f["range"]+1e-9 >= ratio*f["median"])
    midpoint = np.floor((f.high+f.low)/2/tick+.5)*tick
    midpoint = np.maximum(f.low, np.minimum(midpoint, f.high-tick))
    return flag, np.where(flag, midpoint, f.low)


def check_decisions(job, f):
    d = pd.read_csv(RUN/f"large_candle_{job['tag']}.tsv", sep="\t",
                    parse_dates=["time","signal_bar"])
    f = f.set_index("bar_time")
    indices = f.index.get_indexer(d.signal_bar)
    assert (indices >= 0).all()
    expected_signal = np.searchsorted(f.index.to_numpy(), d.time.dt.floor("30min").to_numpy())-1
    assert np.array_equal(indices, expected_signal), "Signal must be previous completed observed M30 bar"
    ref = f.iloc[indices].reset_index()
    same_day = d.time.dt.normalize().eq(ref.session)
    ref.loc[~same_day, ["prior_count","median","ratio"]] = 0
    for c in ("high","low","prior_count","median","ratio"):
        np.testing.assert_allclose(d[c],ref[c],rtol=0,atol=1e-9,err_msg=c)
    assert ref.close.gt(ref.open).all(), "GG signal must be green"
    flags, sl = stops(ref,job["ratio"])
    assert np.array_equal(d.tightened.astype(bool),flags)
    np.testing.assert_allclose(d.stop,sl,rtol=0,atol=1e-8)
    assert d.time.dt.floor("30min").is_unique
    d["order_bar"] = d.time.dt.floor("30min")
    return d


def validate_simulation(q, f, native, ratio):
    flags, sl = stops(f,ratio)
    # No tightening when a prior-session candle becomes the next session's signal.
    next_day = f.session.shift(-1).eq(f.session)
    use = flags & next_day
    keys = f.bar_time.to_numpy(dtype="datetime64[s]").astype(np.int64)//1800
    mapping = dict(zip(keys[use],sl[use])) if ratio else None
    sim,rejected = engine.simulate_m30_ea(q.b,cutoffs=engine.load_cutoffs(),signal="green",signal_stops=mapping)
    sim["entry_minute"] = pd.to_datetime(sim.entry_time).dt.floor("min")
    # The source's first few bars precede MT5's history warmup. All later trades must match.
    later = sim.loc[sim.entry_minute >= native.entry_time.min().floor("min")].reset_index(drop=True)
    assert len(later)==len(native),(ratio,len(later),len(native))
    assert np.array_equal(later.entry_minute,native.entry_time.dt.floor("min"))
    assert np.array_equal(pd.to_datetime(later.exit_time).dt.floor("min"),native.exit_time.dt.floor("min"))
    for a,b in (("requested","requested_price"),("sl","original_sl"),("fill","fill_price"),("exit_price","exit_price")):
        np.testing.assert_allclose(later[a],native[b],rtol=0,atol=1e-7,err_msg=a)
    assert np.array_equal(pd.to_datetime(later.submitted).dt.floor("30min"),native.submitted.dt.floor("30min"))
    return dict(trades=len(later),extra_before_tester_start=len(sim)-len(later),rejected_orders=rejected)


def metrics(p):
    net=p.net_dollars
    loss=-net[net<0].sum()
    changed=p.loc[p.tightened.eq(1)]
    return dict(trades=len(p),tightened_fills=len(changed),tightened_pct=100*len(changed)/len(p),
                net_dollars=float(net.sum()),mean_net_R=float(p.net_r.mean()),
                mean_gross_R=float(p.gross_r.mean()),win_pct=float(100*(net>0).mean()),
                profit_factor=float(net[net>0].sum()/loss) if loss else float("nan"),
                median_risk_dollars=float(p.initial_risk_dollars.median()),
                affected_median_old_risk=float(((changed.high-changed.low)*2).median()),
                affected_median_new_risk=float(changed.initial_risk_dollars.median()),
                affected_stops=int(changed.exit_comment.str.startswith("sl ").sum()),
                stress1_net=float((net-1).sum()),stress2_net=float((net-2).sum()),
                stress1_mean_R=float(((net-1)/p.initial_risk_dollars).mean()),
                stress2_mean_R=float(((net-2)/p.initial_risk_dollars).mean()))


def main():
    manifest=json.loads((RUN/"manifest.json").read_text())
    assert digest(DOC/"PROTOCOL.md")==manifest["protocol_sha256"]
    for n,h in manifest["prepared_sha256"].items(): assert digest(RUN/n)==h,n
    q=load_quote_index() # checks every cached OHLC against the original raw minute file
    f=features(pd.DataFrame(dict(bar_time=pd.to_datetime(q.slots*1800,unit="s"),
              open=q.ohlc[:,0],high=q.ohlc[:,1],low=q.ohlc[:,2],close=q.ohlc[:,3])))
    f.to_csv(RUN/"signal_features.csv",index=False)
    print(f"Raw minutes and {len(f):,} M30 features checked.",flush=True)
    rows=[];checks=[];ledgers={}
    scopes={**PERIODS,**{str(y):(f"{y}-01-01",min(f"{y+1}-01-01","2026-10-01")) for y in range(2010,2027)}}
    for job in manifest["jobs"]:
        tag=job["tag"]
        done=json.loads((RUN/(tag+".completed.json")).read_text())
        for n,h in done["outputs"].items(): assert digest(RUN/n)==h,n
        assert digest(RUN/(tag+".htm"))==done["report_sha256"]
        audit=ensure_audited(RUN,job,dict(symbol=manifest["symbol"],grid_points=TICK),2)
        d=check_decisions(job,f)
        n=economics(parse_report(RUN/(tag+".htm"),manifest["symbol"]),INSTRUMENTS["NQ"])
        simcheck=validate_simulation(q,f,n,job["ratio"])
        print(tag,"full minute replay matches",len(n),"native trades",flush=True)
        a=pd.read_csv(audit,sep="\t",encoding="utf-16").set_index("ticket").loc[n.ticket]
        np.testing.assert_allclose(a.trade_profit,n.trade_profit,rtol=0,atol=1e-7)
        np.testing.assert_allclose(n.trade_profit,(n.exit_price-n.fill_price)*2,rtol=0,atol=1e-7)
        accepted=d.set_index("order_bar").reindex(n.submitted.dt.floor("30min")).reset_index(drop=True)
        assert accepted.signal_bar.notna().all()
        np.testing.assert_allclose(n.requested_price,accepted.high,rtol=0,atol=1e-8)
        np.testing.assert_allclose(n.original_sl,accepted.stop,rtol=0,atol=1e-8)
        for c in ("signal_bar","high","low","prior_count","median","ratio","tightened"):
            n[c]=accepted[c].to_numpy()
        data=np.memmap(RUN/f"window_equity_{tag}.bin",dtype=DTYPE,mode="r")
        assert np.all(np.diff(data["time"])>=0)
        stat=pd.read_csv(RUN/job["outputs"][1],sep="\t",encoding="utf-16").iloc[0]
        gross_dd=maxdd(data["equity"])
        assert abs(gross_dd-stat.equity_dd)<1e-6,(tag,gross_dd,stat.equity_dd)
        assert abs(data["balance"][-1]-500000-n.trade_profit.sum())<1e-6
        assert abs(data["equity"][-1]-data["balance"][-1])<1e-6
        exits=np.sort(n.exit_time.to_numpy().astype("datetime64[s]").astype(np.int64))
        for period,(start,end) in scopes.items():
            p=n.loc[n.session.ge(start)&n.session.lt(end)]
            row=dict(threshold=job["ratio"],period=period,**metrics(p),**equity_metrics(data,start,end,exits))
            row["net_per_equity_dd"]=row["net_dollars"]/row["sampled_equity_dd"]
            rows.append(row)
        n.to_csv(RUN/(tag+"_trades.csv"),index=False)
        ledgers[job["ratio"]]=n
        checks.append(dict(tag=tag,decisions=len(d),tightened_decisions=int(d.tightened.sum()),
                           fills=len(n),native_gross_equity_dd=gross_dd,minute_replay=simcheck))
        del data
    summary=pd.DataFrame(rows)
    summary.to_csv(RUN/"summary.csv",index=False)
    # Match unchanged entry opportunities only; separately count newly available trades.
    paired=[]
    base=ledgers[0.0]
    for ratio,n in ledgers.items():
        if not ratio: continue
        j=n.merge(base,on=["submitted","entry_time"],suffixes=("_new","_base"))
        for period,(start,end) in PERIODS.items():
            p=j.loc[j.session_new.ge(start)&j.session_new.lt(end)&j.tightened_new.eq(1)]
            nb=n.loc[n.session.ge(start)&n.session.lt(end)]
            bb=base.loc[base.session.ge(start)&base.session.lt(end)]
            allmatch=j.loc[j.session_new.ge(start)&j.session_new.lt(end)]
            paired.append(dict(threshold=ratio,period=period,matched_affected=len(p),
                 affected_pnl_change=float((p.net_dollars_new-p.net_dollars_base).sum()),
                 stopped_old_winners=int((p.exit_comment_new.str.startswith("sl ")&p.net_dollars_base.gt(0)).sum()),
                 smaller_stopped_losses=int((p.exit_comment_new.str.startswith("sl ")&p.exit_comment_base.str.startswith("sl ")).sum()),
                 new_entries=len(nb)-len(allmatch),missing_old_entries=len(bb)-len(allmatch)))
    pd.DataFrame(paired).to_csv(RUN/"paired.csv",index=False)
    result=dict(all_passed=True,jobs=checks,source_sha256=digest(engine.MINUTES),
                code_sha256=digest(__file__),simulator_sha256=digest(engine.__file__),
                summary_sha256=digest(RUN/"summary.csv"),raw_minutes=len(q.b["o"]))
    (RUN/"verification.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(summary.loc[summary.period.isin(PERIODS),["threshold","period","trades","tightened_fills",
          "net_dollars","mean_net_R","sampled_equity_dd","net_per_equity_dd"]].to_string(index=False))


if __name__=="__main__":
    main()

