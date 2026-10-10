"""Analyse four complete ES baseline/minimum-50-tick EA reruns.

One declared threshold, unchanged fixed-one-MES sizing. Complete paths and
audited order/deal ledgers are required. Whole source-entry days are sampled
jointly across four arms; no threshold search, adoption or holdout claim.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_instrument_baseline import PERIODS
from project_paths import PROJECT_ROOT as ROOT

RUN = ROOT / "Reports" / "es_width_filter_20261011"
ARMS = [(m,v) for m in ("rtl","control") for v in ("baseline","min50")]
COSTS = (0., 1.05, 2.30, 3.55)
PRIMARY_COST = 1.05
PV, TICK, POINT, THRESHOLD = 5., .25, .01, 12.5
DRAWS, SEED, BATCH, TOL = 1000, 20261011, 32, 1e-6
HOLES = {"2020-02-28","2020-06-30"}
BOOT_METRICS = ("mean_gross_R","mean_net_R","net_cash","net_cash_per_source_day","net_R_sum","net_R_per_source_day")
SAMPLES = ("full_sample","source_sensitivity")


def require(condition, message):
    if not bool(condition):
        raise ValueError(message)


def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    with Path(path).open("rb") as f:
        bom=f.read(2)
    return pd.read_csv(path,sep="\t",encoding="utf-16" if bom in (b"\xff\xfe",b"\xfe\xff") else "utf-8-sig")


def clock(values):
    return pd.to_datetime(values,format="%Y.%m.%d %H:%M:%S")


def same_numbers(a,b,message,atol=TOL):
    require(np.allclose(np.asarray(a,dtype=float),np.asarray(b,dtype=float),atol=atol,rtol=0,equal_nan=True),message)


def equity_drawdown(profits):
    """Closed-trade equity drawdown, including the initial zero balance."""
    curve=np.r_[0.,np.cumsum(np.asarray(profits,dtype=float))]
    return float(np.max(np.maximum.accumulate(curve)-curve))


def session_labels(entries):
    minute=entries.dt.hour*60+entries.dt.minute
    return pd.Series(np.select([(minute>=60)&(minute<990),(minute>=990)&(minute<1200),
                                (minute>=1200)&(minute<1410)],
                               ["pre_cash","early_cash","late_cash"],default="outside_session"),
                     index=entries.index)


def symbol_value(frame,*names):
    for name in names:
        if name in frame:
            return frame[name].iloc[0]
    raise ValueError("Symbol metadata missing "+"/".join(names)+"; available: "+", ".join(frame.columns))


def load_and_validate(run):
    manifest_path=run/"manifest.json"
    require(manifest_path.is_file(),"Run manifest is missing; prepare the ES width study first")
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    require({(j["mode"],j["variant"]) for j in manifest["jobs"]}==set(ARMS) and len(manifest["jobs"])==4,
            "Manifest must contain exactly RTL/control x baseline/min50")
    require(manifest.get("pv")==PV and manifest.get("point")==POINT and manifest.get("native_tick")==TICK,
            "Frozen symbol/risk units differ")
    require(manifest.get("minimum_native_ticks")==50 and manifest.get("minimum_price_points")==THRESHOLD and
            manifest.get("minimum_terminal_points")==1250 and manifest.get("maximum_terminal_points")==1e8,
            "Frozen one-threshold configuration differs")
    require(manifest.get("periods")==[list(p) for p in PERIODS],"Frozen periods differ")
    require(set(manifest.get("exclusion_dates",[]))==HOLES,"Frozen source sensitivity dates differ")
    require(manifest.get("cost_per_trade")==PRIMARY_COST and manifest.get("cost_sensitivities")==list(COSTS[1:]),
            "Frozen cost scenarios differ")
    require(manifest.get("bootstrap",{}).get("draws")==DRAWS and manifest.get("bootstrap",{}).get("seed")==SEED,
            "Frozen bootstrap draw count/seed differ")
    require(bool(manifest.get("input_hashes")),"Frozen input hashes are absent")
    for filename,expected in manifest["input_hashes"].items():
        p=Path(filename)
        if not p.is_absolute():p=ROOT/p
        require(p.is_file() and digest(p)==expected,f"Frozen input changed: {p}")
    validation_path=run/"validation.json"
    require(validation_path.is_file(),"All four root runner/audit/source checks are required; validation.json is missing")
    validation=json.loads(validation_path.read_text(encoding="utf-8"))
    require(validation.get("all_passed") is True,"Root run validation did not pass")
    require(validation.get("manifest_sha256")==digest(manifest_path),"Root validation binds a different manifest")
    require(validation.get("frozen_input_count")==len(manifest["input_hashes"]),"Root frozen input count differs")
    records=validation.get("jobs",[])
    if isinstance(records,dict): records=[{"tag":key,**value} for key,value in records.items()]
    require(len(records)==4 and {j["tag"] for j in records}=={j["tag"] for j in manifest["jobs"]},
            "Root validation does not cover all four jobs")
    record_book={record["tag"]:record for record in records}
    for record in records:
        require(record.get("all_passed",True) is True,f"Root validation failed: {record['tag']}")
    metadata=json.loads((run/"source_ES_metadata.json").read_text(encoding="utf-8"))
    source_path=run/"source_ES_m30.csv"
    require(metadata["m30_sha256"]==digest(source_path),"Frozen ES source cache hash differs")
    require(metadata["source_sha256"] in manifest["input_hashes"].values(),"Real ES source hash is not frozen")
    source=pd.read_csv(source_path,index_col=0,parse_dates=True)
    require(len(source)==metadata["m30_bars"] and not source.index.duplicated().any(),"ES source M30 identity/count differs")
    require(list(source.columns)==["open","high","low","close"] and np.isfinite(source.to_numpy()).all(),
            "ES source OHLC cache schema differs")
    require(np.array_equal(source.to_numpy(),np.rint(source.to_numpy())),"ES cached OHLC is not integer native ticks")
    source_width=(source.high-source.low)/4
    require(source_width.min()>=0 and (source_width/POINT<=1e8).all(),"Declared maximum filter bound would bind source candles")
    calendar=json.loads((run/"source_calendar.json").read_text(encoding="utf-8"))
    es_days=sorted(metadata["trading_days"])
    require(calendar.get("all_source_checks_passed") is True and es_days==calendar["trading_days"] and
            calendar["source_metadata"]["ES"]==metadata,"Copied calendar differs from true ES source days/metadata")
    same_numbers(source_width.max(),manifest["expected_maximum_source_width"],"Frozen maximum source width differs")
    same_numbers(source_width.max(),validation["maximum_source_width"],"Root source width validation differs")
    days=pd.DatetimeIndex(pd.to_datetime(es_days))
    start,end=manifest.get("start","2010-06-07"),manifest.get("end_exclusive","2026-07-14")
    require((days>=pd.Timestamp(start)).all() and (days<pd.Timestamp(end)).all(),"Source calendar extends beyond frozen run")
    paths,audits=[],[]
    for job in manifest["jobs"]:
        tag=job["tag"]
        require(float(job.get("pv",PV))==PV and int(job["min_ticks"])==(50 if job["variant"]=="min50" else 0),
                f"{tag}: point value or threshold differs")
        marker=run/f"{tag}.completed.json"
        require(marker.is_file(),f"Incomplete job {tag}; finish all four EA reruns")
        completed=json.loads(marker.read_text(encoding="utf-8"))
        require(completed.get("tag")==tag,f"{tag}: completion tag differs")
        for filename in job["outputs"]:
            p=run/filename
            require(p.is_file() and digest(p)==completed.get("outputs",{}).get(filename),f"{tag}: completed output changed: {filename}")
        record=record_book[tag]
        require(record["mode"]==job["mode"] and record["variant"]==job["variant"],f"{tag}: root validation arm differs")
        require(record["input_sha256"]=={name:digest(run/name) for name in job["outputs"]},
                f"{tag}: root validation binds different completed outputs")
        require(record.get("signal_ohlc_source_exact") is True and record.get("observed_closes_source_exact") is True,
                f"{tag}: root source binding flags failed")
        require(record["report_sha256"]==digest(run/(tag+".htm")),f"{tag}: complete report changed")
        require(json.loads((run/(tag+".validation.json")).read_text(encoding="utf-8"))==record,
                f"{tag}: per-job root validation differs")
        raw_path=run/job["outputs"][0]
        audited_path=Path(job.get("audited",raw_path.with_name(raw_path.stem+"_audited.csv")))
        if not audited_path.is_absolute():audited_path=run/audited_path
        require(audited_path.is_file(),f"{tag}: complete audited ledger missing")
        audit_path=run/f"{tag}.ledger_audit.json"
        require(audit_path.is_file(),f"{tag}: audited provenance missing")
        audit_meta=json.loads(audit_path.read_text(encoding="utf-8"))
        require(audit_meta.get("all_passed") is True and audit_meta["audited_sha256"]==digest(audited_path)==record["audited_sha256"],
                f"{tag}: audited ledger hash binding differs")
        require(audit_meta["input_sha256"]=={"raw":digest(raw_path),"stats":digest(run/job["outputs"][1]),
                                             "report":digest(run/(tag+".htm"))},f"{tag}: audit input provenance differs")
        identity=audit_meta["identity"]
        require(identity["tag"]==tag and identity["mode"]==job["mode"] and identity["symbol"]==job["symbol"] and
                identity["point_value"]==PV and identity["grid_points"]==TICK and identity.get("fix_risk") is True,
                f"{tag}: audited economic/order-risk convention differs")
        # The audit itself binds raw, report and stats; the root validator also
        # reconciles its complete ledger with the independent path collector.
        audited=read(audited_path)
        stats=read(run/job["outputs"][1])
        t=read(run/f"path_{tag}_trades.csv")
        observer=read(run/f"path_{tag}_summary.csv")
        sym=read(run/f"width_{tag}_symbol.csv")
        require(len(sym)==len(stats)==len(observer)==1,f"{tag}: metadata row counts")
        same_numbers(symbol_value(sym,"point","symbol_point"),POINT,f"{tag}: source _Point guard")
        same_numbers(symbol_value(sym,"tick_size","trade_tick_size","symbol_trade_tick_size"),TICK,f"{tag}: native tick guard")
        require(sym.iloc[0].symbol==job["symbol"] and sym.iloc[0].digits==2,f"{tag}: symbol/digits guard")
        same_numbers(sym.iloc[0].tick_value/TICK,PV,f"{tag}: one-MES economic tick value")
        require(bool(sym.iloc[0].range_filter)==(job["variant"]=="min50"),f"{tag}: actual range filter switch")
        if job["variant"]=="min50":
            require(sym.iloc[0].minimum_native_ticks==50 and sym.iloc[0].minimum_price_points==THRESHOLD and
                    sym.iloc[0].minimum_terminal_points==1250 and sym.iloc[0].maximum_price_points>source_width.max(),
                    f"{tag}: actual minimum/maximum range bounds differ")
        st,s=stats.iloc[0],observer.iloc[0]
        require(st.run_tag==s.run_tag==tag and st.risk_reward==1,f"{tag}: tag/RR differs")
        require(s.observer_errors==s.active_at_end==s.max_entry_lag_msc==0 and s.counts_match==s.profit_match==1,
                f"{tag}: incomplete observer paths")
        require((t.first_quote_time_msc==t.entry_time_msc).all(),f"{tag}: initial quote timing differs")
        require(len(t)==record["trades"]==len(audited)==st.trades==s.exported_positions==s.history_entries==s.history_exits==s.tester_trades,
                f"{tag}: complete trade counts differ")
        require(not t.position_id.duplicated().any(),f"{tag}: duplicate independent position")
        old=audited.set_index("ticket")
        current=t.set_index("position_id").reindex(old.index)
        require(set(t.position_id)==set(old.index),f"{tag}: audited/path position identities differ")
        for field in ("entry_time","exit_time"):
            require(np.array_equal(current[field],old[field]),f"{tag}: audited/path {field} differs")
        same_numbers(current.trade_profit,old.trade_profit,f"{tag}: audited/path profit differs")
        same_numbers(current.requested_risk,old.candle_range,f"{tag}: original order risk differs")
        same_numbers([t.trade_profit.sum()]*4,[st.net_profit,s.exported_profit,s.history_profit,s.tester_profit],f"{tag}: profit totals differ")
        same_numbers(t.loc[t.trade_profit>0,"trade_profit"].sum(),st.gross_profit,f"{tag}: gross gains differ")
        same_numbers(t.loc[t.trade_profit<0,"trade_profit"].sum(),st.gross_loss,f"{tag}: gross losses differ")
        for field,value in (("max_red_run",3 if job["mode"]=="rtl" else 0),("early_close_calendar",1),
                            ("flatten_fallback",1),("trail_distance_r",0)):
            require(field in st.index and st[field]==value,f"{tag}: setting differs: {field}")
        t["entry"],t["exit"]=clock(t.entry_time),clock(t.exit_time)
        same_numbers(t.entry_time_msc//1000,t.entry.astype("datetime64[ns]").astype("int64")/1e9,f"{tag}: entry clock")
        same_numbers(t.exit_time_msc//1000,t.exit.astype("datetime64[ns]").astype("int64")/1e9,f"{tag}: exit clock")
        require((t.exit_time_msc>=t.entry_time_msc).all() and (t.quote_samples>0).all(),f"{tag}: quote coverage/order")
        same_numbers(t.requested_entry-t.initial_sl,t.requested_risk,f"{tag}: requested risk definition")
        same_numbers(t.actual_fill-t.initial_sl,t.actual_risk,f"{tag}: actual risk definition")
        same_numbers((t.exit_price-t.actual_fill)*PV,t.trade_profit,f"{tag}: fixed-one-MES PnL value")
        require((t.requested_risk>0).all() and (t.actual_risk>0).all(),f"{tag}: nonpositive risk")
        same_numbers(t.requested_risk/TICK,np.rint(t.requested_risk/TICK),f"{tag}: nonnative requested width")
        if job["variant"]=="min50":
            require((t.requested_risk>=THRESHOLD-TOL).all(),f"{tag}: a completed filtered trade violates the 50-tick minimum")
        orders=read(run/f"path_{tag}_orders.csv")
        source_index=source.index.get_indexer(clock(orders.signal_bar_open))
        require((source_index>=0).all() and np.array_equal(orders[["signal_open","signal_high","signal_low","signal_close"]].to_numpy(),
                                                       source.iloc[source_index].to_numpy()/4),f"{tag}: original signal/source OHLC binding")
        bars=read(run/f"path_{tag}_bars.csv")
        bar_index=source.index.get_indexer(clock(bars.closed_bar_open))
        require((bar_index>=0).all() and np.array_equal(bars.closed_close.to_numpy(),source.iloc[bar_index].close.to_numpy()/4),
                f"{tag}: observed M30 close/source binding")
        successful=orders.loc[orders.order>0]
        require(not successful.order.duplicated().any(),f"{tag}: repeated entry arming order")
        mapped=successful.set_index("order").reindex(t.entry_order)
        require(mapped.signal_high.notna().all(),f"{tag}: original arming signal absent")
        same_numbers(mapped.signal_high-mapped.signal_low,t.requested_risk,f"{tag}: signal width/order risk association")
        t["signal_bar_open"]=mapped.signal_bar_open.to_numpy()
        t["signal_arm_time_msc"]=mapped.arm_time_msc.to_numpy()
        if job["variant"]=="min50":
            require(((orders.signal_high-orders.signal_low)>=THRESHOLD-TOL).all(),f"{tag}: a filtered arming signal violates the minimum")
        hit=t.first_hit_1_msc>0
        require(np.array_equal(hit,t.mfe_R>=1-1e-9),f"{tag}: +1R reach disagrees with complete MFE")
        require(((t.first_hit_1_msc[hit]>=t.entry_time_msc[hit])&(t.first_hit_1_msc[hit]<=t.exit_time_msc[hit])).all(),
                f"{tag}: first +1R touch outside held path")
        same_numbers(np.maximum(0,(t.actual_fill-t.min_bid)/t.actual_risk),t.mae_R,f"{tag}: MAE extrema")
        same_numbers(np.maximum(0,(t.max_bid-t.actual_fill)/t.actual_risk),t.mfe_R,f"{tag}: MFE extrema")
        require(np.isfinite(t[["mae_R","mfe_R","trade_profit","requested_risk"]].to_numpy()).all(),f"{tag}: nonfinite path fields")
        if job["variant"]=="baseline" and job.get("reference_raw"):
            require(digest(raw_path)==digest(job["reference_raw"]),f"{tag}: baseline raw bytes do not replicate")
        if job["variant"]=="baseline" and job.get("reference_path"):
            require(digest(run/f"path_{tag}_trades.csv")==digest(job["reference_path"]),f"{tag}: baseline full observer bytes differ")
        if job["variant"]=="baseline" and job.get("reference_audited"):
            reference=read(job["reference_audited"]).set_index("ticket")
            require(set(reference.index)==set(old.index),f"{tag}: baseline audited identities differ")
            for field in ("entry_time","exit_time"):
                require(np.array_equal(old.reindex(reference.index)[field],reference[field]),f"{tag}: baseline complete {field} differs")
            for field in ("trade_profit","candle_range"):
                same_numbers(old.reindex(reference.index)[field],reference[field],f"{tag}: baseline complete {field} differs")
        t["mode"],t["variant"],t["arm"]=job["mode"],job["variant"],job["mode"]+"__"+job["variant"]
        t["day"],t["year"]=t.entry.dt.normalize(),t.entry.dt.year
        require(t.day.isin(days).all(),f"{tag}: trade day missing from true ES source calendar")
        t["session"]=session_labels(t.entry)
        t["source_hole"]=t.day.dt.strftime("%Y-%m-%d").isin(HOLES)
        t["cross_date"]=t.entry.dt.normalize()!=t.exit.dt.normalize()
        t["source_sensitivity"]=~t.source_hole&~t.cross_date
        t["risk_cash"]=t.requested_risk*PV
        t["gross_R"]=t.trade_profit/t.risk_cash
        t["inv_risk_cash"]=1/t.risk_cash
        t["hit1"]=hit.astype(float)
        t["stop_before1"]=((t.exit_reason==4)&~hit).astype(float)
        paths.append(t)
        audits.append({"tag":tag,"trades":len(t),"raw_rows":len(read(raw_path)),
                       "audited_sha256":digest(audited_path),"audit_metadata_sha256":digest(audit_path),
                       "path_sha256":digest(run/f"path_{tag}_trades.csv"),"symbol_sha256":digest(run/f"width_{tag}_symbol.csv"),
                       "source_hole_entries":int(t.source_hole.sum()),"cross_date":int(t.cross_date.sum()),
                       "requested_actual_risk_differences":int((~np.isclose(t.requested_risk,t.actual_risk,atol=TOL,rtol=0)).sum()),
                       "all_passed":True})
        print(f"PASS {tag}: {len(t):,} complete audited fixed-one-MES paths.",flush=True)
    d=pd.concat(paths,ignore_index=True)
    require(len(d)==validation["complete_paths"],"Root complete-path aggregate count differs")
    provenance={"manifest_sha256":digest(manifest_path),"validation_sha256":digest(validation_path),
                "source_metadata_sha256":digest(run/"source_ES_metadata.json"),
                "source_calendar_sha256":digest(run/"source_calendar.json"),"source_m30_sha256":digest(source_path)}
    return d,days,audits,provenance


def summary(frame,cost,source_days):
    n=len(frame)
    ordered=frame.sort_values(["exit_time_msc","entry_time_msc","position_id"])
    net=ordered.trade_profit.to_numpy()-cost
    net_r=ordered.gross_R.to_numpy()-cost*ordered.inv_risk_cash.to_numpy()
    gains=net[net>0].sum()
    losses=-net[net<0].sum()
    gross_gains=frame.loc[frame.trade_profit>0,"trade_profit"].sum()
    gross_losses=-frame.loc[frame.trade_profit<0,"trade_profit"].sum()
    cash_dd=equity_drawdown(net)
    return {"trades":n,"entry_days":frame.day.nunique(),"source_days":source_days,
            "trades_per_source_day":n/source_days if source_days else np.nan,
            "win_fraction_gross":float((frame.trade_profit>0).mean()) if n else np.nan,
            "median_requested_risk_points":frame.requested_risk.median(),
            "mean_requested_risk_points":frame.requested_risk.mean(),
            "mean_fixed_contract_risk_cash":frame.risk_cash.mean(),
            "gross_cash":frame.trade_profit.sum(),"net_cash":float(net.sum()),
            "net_cash_per_source_day":float(net.sum())/source_days if source_days else np.nan,
            "mean_gross_R":frame.gross_R.mean(),"mean_net_R":float(net_r.mean()) if n else np.nan,
            "mean_cost_R":float((cost*frame.inv_risk_cash).mean()) if n else np.nan,
            "net_R_sum":float(net_r.sum()),"net_R_per_source_day":float(net_r.sum())/source_days if source_days else np.nan,
            "PF_gross":gross_gains/gross_losses if gross_losses else np.nan,
            "PF_net":gains/losses if losses else np.nan,
            "closed_trade_maxDD_cash":cash_dd,"closed_trade_maxDD_R":equity_drawdown(net_r),
            "net_cash_over_closed_trade_maxDD":float(net.sum())/cash_dd if cash_dd>0 else np.nan,
            "zero_closed_trade_drawdown":cash_dd==0,
            "mean_mae_R":frame.mae_R.mean(),"mean_mfe_R":frame.mfe_R.mean(),
            "p_reach1":frame.hit1.mean(),"p_stop_before1":frame.stop_before1.mean()}


def day_totals(frame,calendar,arms):
    """Daily sums [gross R, inverse requested $ risk, cash, count]."""
    data=np.zeros((len(calendar),len(arms),4),dtype=float)
    d=frame.assign(_count=1.)
    g=d.groupby(["day","arm"])[["gross_R","inv_risk_cash","trade_profit","_count"]].sum()
    for j,arm in enumerate(arms):
        if arm in g.index.get_level_values("arm"):
            data[:,j]=g.xs(arm,level="arm").reindex(calendar).fillna(0).to_numpy()
    return data


def estimates(totals,cost,source_days):
    n=totals[...,3]
    net_cash=totals[...,2]-cost*n
    net_r=totals[...,0]-cost*totals[...,1]
    def ratio(x):
        return np.divide(x,n,out=np.full_like(x,np.nan,dtype=float),where=n>0)
    return np.stack([ratio(totals[...,0]),ratio(net_r),net_cash,net_cash/source_days,net_r,net_r/source_days],axis=-1)


def joint_bootstrap(daily,seed):
    """One shared draw schedule for all arms and both declared populations."""
    rng=np.random.default_rng(seed)
    n_days=len(daily)
    values=[]
    for start in range(0,DRAWS,BATCH):
        n=min(BATCH,DRAWS-start)
        indices=rng.integers(0,n_days,(n,n_days))
        freq=np.stack([np.bincount(row,minlength=n_days) for row in indices]).astype(float)
        values.append(np.einsum("bd,daf->baf",freq,daily,optimize=True))
    return np.concatenate(values)


def interval(values):
    finite=np.asarray(values)[np.isfinite(values)]
    return (*np.percentile(finite,[2.5,97.5]),len(finite)) if len(finite) else (np.nan,np.nan,0)


def opening_keys(frame):
    same_numbers(frame.actual_fill/TICK,np.rint(frame.actual_fill/TICK),"Actual entry fills do not lie on native grid")
    same_numbers(frame.requested_risk/TICK,np.rint(frame.requested_risk/TICK),"Requested risks do not lie on native grid")
    return pd.Series(list(zip(frame.entry_time_msc.astype(int),np.rint(frame.actual_fill/TICK).astype(int),
                              np.rint(frame.requested_risk/TICK).astype(int),frame.signal_bar_open)),index=frame.index,dtype=object)


def turnover_pair(baseline,filtered):
    """Opening identities exclude run-local tickets; ambiguous pairs are flagged."""
    b,f=baseline.copy(),filtered.copy()
    b["opening_key"],f["opening_key"]=opening_keys(b),opening_keys(f)
    duplicate_b=int(b.opening_key.duplicated(keep=False).sum())
    duplicate_f=int(f.opening_key.duplicated(keep=False).sum())
    qualified=b.loc[b.requested_risk>=THRESHOLD-TOL]
    if duplicate_b or duplicate_f:
        return {"opening_keys_unique":False,"duplicate_baseline_rows":duplicate_b,"duplicate_filtered_rows":duplicate_f},pd.DataFrame()
    kb,kf,kq=set(b.opening_key),set(f.opening_key),set(qualified.opening_key)
    common=kq&kf
    physical_b={key[:3] for key in kb}
    physical_f={key[:3] for key in kf}
    shared_physical=physical_b&physical_f
    changed_signal=len(shared_physical-{key[:3] for key in kb&kf})
    result={"opening_keys_unique":True,"duplicate_baseline_rows":0,"duplicate_filtered_rows":0,
            "baseline_trades":len(b),"qualified_baseline_trades":len(qualified),"filtered_trades":len(f),
            "common_qualifying_openings":len(common),"new_filtered_vs_baseline":len(kf-kb),
            "same_execution_different_original_signal":changed_signal,
            "new_filtered_vs_posthoc_subset":len(kf-kq),"removed_qualifying_baseline_openings":len(kq-kf),
            "retained_qualified_baseline_share":len(common)/len(qualified) if len(qualified) else np.nan,
            "shared_opening_share_of_full_baseline":len(common)/len(b) if len(b) else np.nan,
            "filtered_new_opening_fraction":len(kf-kb)/len(f) if len(f) else np.nan}
    # Use a regular Python tuple-key lookup, avoiding Pandas treating the
    # tuple's components as index levels when selecting one opening.
    book_b={row.opening_key:row for row in b.itertuples(index=False,name="Trade")}
    book_f={row.opening_key:row for row in f.itertuples(index=False,name="Trade")}
    records=[]
    changed_time,changed_profit=0,0
    for key in sorted(kq|kf):
        br,fr=book_b.get(key),book_f.get(key)
        kind="common" if key in common else ("new_filtered" if key in kf else "removed_qualifying_baseline")
        if kind=="common":
            changed_time+=br.exit_time_msc!=fr.exit_time_msc
            changed_profit+=not np.isclose(br.trade_profit,fr.trade_profit,atol=TOL,rtol=0)
        records.append({"kind":kind,"entry_time_msc":key[0],"actual_fill":key[1]*TICK,"requested_risk":key[2]*TICK,"original_signal_bar_open":key[3],
                        "baseline_entry_time":br.entry_time if br is not None else None,
                        "filtered_entry_time":fr.entry_time if fr is not None else None,
                        "baseline_exit_time":br.exit_time if br is not None else None,
                        "filtered_exit_time":fr.exit_time if fr is not None else None,
                        "baseline_profit":br.trade_profit if br is not None else np.nan,
                        "filtered_profit":fr.trade_profit if fr is not None else np.nan})
    result["common_openings_changed_exit_time"]=int(changed_time)
    result["common_openings_changed_profit"]=int(changed_profit)
    return result,pd.DataFrame(records)


def analyse(run=RUN):
    run=Path(run)
    d,calendar,audits,provenance=load_and_validate(run)
    arm_keys=[m+"__"+v for m,v in ARMS]
    summaries,contrasts,annual,sessions,daily_rows,bootstrap_checks=[],[],[],[],[],[]
    for pi,(period,lo,hi) in enumerate(PERIODS):
        p=d.loc[d.year.between(lo,hi)]
        days=calendar[(calendar.year>=lo)&(calendar.year<=hi)]
        require(len(days)>0,f"{period}: no ES source sessions")
        populations=[p,p.loc[p.source_sensitivity]]
        names=[sample+":"+arm for sample in SAMPLES for arm in arm_keys]
        daily=np.concatenate([day_totals(pop,days,arm_keys) for pop in populations],axis=1)
        sampled=joint_bootstrap(daily,SEED+pi)
        totals=daily.sum(axis=0)
        bootstrap_checks.append({"period":period,"source_days":len(days),"seed":SEED+pi,"draws":DRAWS,
                                 "zero_trade_denominator_draws":{name:int((sampled[:,i,3]==0).sum()) for i,name in enumerate(names)}})
        for cost in COSTS:
            point,boots=estimates(totals,cost,len(days)),estimates(sampled,cost,len(days))
            for sample_idx,(sample,pop) in enumerate(zip(SAMPLES,populations)):
                for arm_idx,arm in enumerate(arm_keys):
                    pos=sample_idx*4+arm_idx
                    mode,variant=arm.split("__")
                    frame=pop.loc[pop.arm==arm]
                    baseline_count=len(pop.loc[pop.arm==mode+"__baseline"])
                    row={"baseline_trade_count_reference":baseline_count,
                         "trade_count_ratio_vs_baseline":len(frame)/baseline_count if baseline_count else np.nan,
                         "period":period,"sample":sample,"mode":mode,"variant":variant,"arm":arm,"cost_roundtrip":cost,
                         "primary_cost":cost==PRIMARY_COST,**summary(frame,cost,len(days))}
                    for k,metric in enumerate(BOOT_METRICS):
                        same_numbers(row[metric],point[pos,k],f"{period}/{sample}/{arm}: day-sum reconstruction {metric}")
                        lower,upper,finite=interval(boots[:,pos,k])
                        row[metric+"_lo95"],row[metric+"_hi95"],row[metric+"_finite_draws"]=lower,upper,finite
                    summaries.append(row)
                definitions=[]
                for mode in ("rtl","control"):
                    definitions.append(("filter_minus_baseline",[(mode+"__min50",1),(mode+"__baseline",-1)],mode))
                for variant in ("baseline","min50"):
                    definitions.append(("rtl_minus_control",[("rtl__"+variant,1),("control__"+variant,-1)],variant))
                definitions.append(("filter_interaction",[("rtl__min50",1),("rtl__baseline",-1),
                                                           ("control__min50",-1),("control__baseline",1)],"four_arm"))
                for kind,components,label in definitions:
                    slots=[(sample_idx*4+arm_keys.index(arm),sign) for arm,sign in components]
                    vector=sum(sign*point[pos] for pos,sign in slots)
                    simulated=sum(sign*boots[:,pos] for pos,sign in slots)
                    for k,metric in enumerate(BOOT_METRICS):
                        lower,upper,finite=interval(simulated[:,k])
                        contrasts.append({"period":period,"sample":sample,"cost_roundtrip":cost,"kind":kind,"comparison":label,
                                          "metric":metric,"difference":vector[k],"lo95":lower,"hi95":upper,"finite_draws":finite})
        # A compact fundamental daily table suffices for every cost convention.
        for i,name in enumerate(names):
            sample,arm=name.split(":")
            mode,variant=arm.split("__")
            for day,value in zip(days,daily[:,i]):
                daily_rows.append({"period":period,"sample":sample,"mode":mode,"variant":variant,"day":day,
                                   "gross_R_sum":value[0],"inverse_risk_cash_sum":value[1],"gross_cash":value[2],"trades":int(value[3])})
        for sample,pop in zip(SAMPLES,populations):
            for session in ("pre_cash","early_cash","late_cash","outside_session"):
                for arm in arm_keys:
                    frame=pop.loc[(pop.arm==arm)&(pop.session==session)]
                    mode,variant=arm.split("__")
                    for cost in COSTS:
                        baseline_count=len(pop.loc[(pop.arm==mode+"__baseline")&(pop.session==session)])
                        sessions.append({"baseline_trade_count_reference":baseline_count,
                                         "trade_count_ratio_vs_baseline":len(frame)/baseline_count if baseline_count else np.nan,
                                         "period":period,"sample":sample,"session":session,"mode":mode,"variant":variant,
                                         "cost_roundtrip":cost,**summary(frame,cost,len(days))})
    for year in sorted(calendar.year.unique()):
        days=calendar[calendar.year==year]
        for sample in SAMPLES:
            p=d.loc[d.year==year]
            if sample=="source_sensitivity":p=p.loc[p.source_sensitivity]
            for arm in arm_keys:
                mode,variant=arm.split("__")
                for cost in COSTS:
                    baseline_count=len(p.loc[p.arm==mode+"__baseline"])
                    annual.append({"baseline_trade_count_reference":baseline_count,
                                   "trade_count_ratio_vs_baseline":len(p.loc[p.arm==arm])/baseline_count if baseline_count else np.nan,
                                   "year":int(year),"partial_year":year in (2010,2026),"sample":sample,"mode":mode,
                                   "variant":variant,"cost_roundtrip":cost,**summary(p.loc[p.arm==arm],cost,len(days))})
    turnover,opening_rows,posthoc=[],[],[]
    for period,lo,hi in PERIODS:
        p=d.loc[d.year.between(lo,hi)]
        days=calendar[(calendar.year>=lo)&(calendar.year<=hi)]
        for mode in ("rtl","control"):
            b=p.loc[(p["mode"]==mode)&(p.variant=="baseline")]
            f=p.loc[(p["mode"]==mode)&(p.variant=="min50")]
            changes,entries=turnover_pair(b,f)
            turnover.append({"period":period,"mode":mode,**changes})
            if len(entries):opening_rows.append(entries.assign(period=period,mode=mode))
            qualified=b.loc[b.requested_risk>=THRESHOLD-TOL]
            omitted=b.loc[b.requested_risk<THRESHOLD-TOL]
            require(len(qualified)+len(omitted)==len(b),"Posthoc width groups do not partition the baseline")
            for label,q in (("posthoc_baseline_min50_diagnostic",qualified),("omitted_baseline_below50_diagnostic",omitted)):
                for cost in COSTS:
                    posthoc.append({"baseline_trade_count_reference":len(b),
                                    "trade_count_ratio_vs_baseline":len(q)/len(b) if len(b) else np.nan,
                                    "period":period,"mode":mode,"sample":label,
                                    "cost_roundtrip":cost,**summary(q,cost,len(days))})
    exclusions=[]
    for period,lo,hi in PERIODS:
        period_data=d.loc[d.year.between(lo,hi)]
        for arm,g in period_data.groupby("arm"):
            mode,variant=arm.split("__")
            for reason,excluded in (("source_hole_entry",g.loc[g.source_hole]),("cross_date",g.loc[g.cross_date]),
                                    ("excluded_union",g.loc[~g.source_sensitivity])):
                exclusions.append({"period":period,"mode":mode,"variant":variant,"reason":reason,
                                   "trades":len(excluded),"gross_cash":excluded.trade_profit.sum(),
                                   "gross_R_sum":excluded.gross_R.sum(),
                                   "net_cash_at_primary_cost":(excluded.trade_profit-PRIMARY_COST).sum()})
    frames={"exclusion_contributions":pd.DataFrame(exclusions),"summary":pd.DataFrame(summaries),"contrasts":pd.DataFrame(contrasts),"yearly":pd.DataFrame(annual),
            "sessions":pd.DataFrame(sessions),"daily":pd.DataFrame(daily_rows),"turnover":pd.DataFrame(turnover),
            "turnover_entries":pd.concat(opening_rows,ignore_index=True) if opening_rows else pd.DataFrame(),
            "posthoc_diagnostic":pd.DataFrame(posthoc)}
    primary=frames["summary"].loc[(frames["summary"]["sample"]=="full_sample")&
                                  (frames["summary"].cost_roundtrip==PRIMARY_COST)&(frames["summary"]["mode"]=="rtl")]
    evidence=[]
    for period in ("2016-19","2020-26"):
        g=primary.loc[primary.period==period].set_index("variant")
        baseline,filtered=g.loc["baseline"],g.loc["min50"]
        evidence.append({"period":period,"filtered_mean_net_R":filtered.mean_net_R,
                         "filtered_mean_net_R_lo95":filtered.mean_net_R_lo95,"filtered_mean_net_R_hi95":filtered.mean_net_R_hi95,
                         "filter_mean_net_R_change":filtered.mean_net_R-baseline.mean_net_R,
                         "filter_fixed_contract_net_cash_change":filtered.net_cash-baseline.net_cash,
                         "point_criteria_met":bool(filtered.mean_net_R>0 and filtered.mean_net_R>baseline.mean_net_R and filtered.net_cash>baseline.net_cash)})
    year_primary=frames["yearly"].loc[(frames["yearly"]["sample"]=="full_sample")&
                                      (frames["yearly"].cost_roundtrip==PRIMARY_COST)&(frames["yearly"]["mode"]=="rtl")]
    consistency={}
    for variant,g in year_primary.groupby("variant"):
        traded=g.loc[g.trades>0]
        consistency[variant]={"traded_years":len(traded),"positive_mean_net_R_years":int((traded.mean_net_R>0).sum()),
                              "positive_net_cash_years":int((traded.net_cash>0).sum()),"zero_trade_years":int((g.trades==0).sum()),
                              "modern_traded_years":int(((g.year>=2016)&(g.trades>0)).sum()),
                              "modern_positive_mean_net_R_years":int(((g.year>=2016)&(g.trades>0)&(g.mean_net_R>0)).sum()),
                              "modern_positive_net_cash_years":int(((g.year>=2016)&(g.trades>0)&(g.net_cash>0)).sum())}
    for name,frame in frames.items():
        frame.to_csv(run/(name+".csv"),index=False,float_format="%.12g")
    checks={"all_passed":True,"jobs":audits,"provenance":provenance,"analyzer_sha256":digest(__file__),
            "bootstrap":bootstrap_checks,"costs_roundtrip":list(COSTS),"primary_cost_roundtrip":PRIMARY_COST,
            "cash_convention":"fixed one MES contract, $5 per ES price point; no sizing changes",
            "R_convention":"profit / original requested entry-minus-SL dollar risk; hypothetical unit-risk normalization",
            "turnover_identity":"entry deal timestamp + actual fill + requested risk + original signal bar; run-local position IDs excluded",
            "drawdown":"observed closed-trade sequence sorted by exit timestamp; no intratrade equity/DD bootstrap",
            "calendar":"true ES source entry-day calendar, zero-trade days included; entry-year attribution",
            "threshold":"one fixed minimum, 50 native ticks = 12.5 ES price points",
            "samples":{"primary":"full_sample","secondary":"known source-hole entry dates and cross-date positions excluded"},
            "historical_candidate_point_criteria":{"both_modern_periods_required":True,
                                                   "met":all(e["point_criteria_met"] for e in evidence),"evidence":evidence},
            "year_consistency":consistency,"all_history_seen":True,"holdout_or_automatic_adoption":False,
            "outputs":{name+".csv":digest(run/(name+".csv")) for name in frames}}
    (run/"analysis_checks.json").write_text(json.dumps(checks,indent=2)+"\n",encoding="utf-8")
    report=["# ES minimum-50-tick full EA rerun\n\n",
            "Four complete unchanged-sizing EA paths pass tester/HTML/audited-ledger and symbol/source checks. "
            "The single declared minimum is 50 native ES ticks (12.5 price points). Full reruns determine results; "
            "the baseline trades exceeding the threshold are retained only as a post-hoc diagnostic.\n\n",
            "Dollar results use one MES contract ($5 per ES price point). Larger candles therefore increase fixed-contract dollar risk. "
            "R divides each profit by its original requested order risk; sums/drawdowns in R describe unit-risk normalization, not the fixed-lot cash account. "
            "Drawdowns use chronological closed trades and exclude unobserved intratrade equity excursions.\n\n",
            "Primary arithmetic roundtrip cost is $1.05. $0 gross and $2.30/$3.55 sensitivities add one/two $1.25 tick costs. "
            "These cost scenarios do not replay executions or claim live slippage.\n\n",
            "One thousand common whole ES source-entry-day draws (including zero-trade sessions) supply paired percentile intervals for each era and all years. "
            "Means use resampled total profit/R divided by resampled trade count. Finite-draw counts disclose empty trade denominators; cash/day remains defined on zero-trade draws. "
            "Serial dependence spanning days is not covered. Drawdown and yearly/session descriptive tables have no bootstrap intervals.\n\n",
            "Full samples are primary; excluding the two known ES source-hole entry dates and cross-date trades is a secondary sensitivity. "
            "Periods use entry year; 2010 and 2026 are partial years. No threshold search, untouched holdout or adoption claim follows.\n\n",
            "Historical point criteria require positive filtered mean net R, improved mean net R and improved fixed-contract net dollars in BOTH 2016РІР‚вЂњ19 and 2020РІР‚вЂњ26. "
            f"Criteria met: {checks['historical_candidate_point_criteria']['met']}. Intervals and yearly consistency remain necessary context.\n\n",
            primary[["period","variant","trades","mean_gross_R","mean_net_R","mean_net_R_lo95","mean_net_R_hi95",
                     "net_cash","closed_trade_maxDD_cash"]].to_string(index=False,float_format=lambda x:f"{x:.4f}"),
            "\n\nTables beside this report contain paired filter contrasts, RTL/control comparisons, the four-arm interaction, costs, yearly/session results, "
            "aligned daily totals, entry turnover with original arming-bar identities, excluded-source contributions and both qualifying/omitted baseline diagnostics.\n"]
    (run/"ANALYSIS.md").write_text("".join(report),encoding="utf-8")
    print(f"Wrote ES width-filter analysis to {run}",flush=True)
    return frames,checks


def self_test():
    # Ratio-of-totals, common draw covariance and genuine zero source days.
    arms=["rtl__baseline","rtl__min50"]
    days=pd.date_range("2020-01-01",periods=4)
    fixture=pd.DataFrame({"day":[days[0],days[0],days[1],days[0],days[0],days[1]],
                          "arm":[arms[0]]*3+[arms[1]]*3,"gross_R":[0.,2.,3.,1.,3.,4.],
                          "inv_risk_cash":[.1]*6,"trade_profit":[0.,20.,30.,10.,30.,40.]})
    daily=day_totals(fixture,days,arms)
    require(np.array_equal(daily[2:],np.zeros_like(daily[2:])),"self-test zero source days")
    point=estimates(daily.sum(axis=0),1.,len(days))
    same_numbers(point[:,0],[5/3,8/3],"self-test ratio of totals")
    draws=joint_bootstrap(daily,SEED)
    est=estimates(draws,1.,len(days))
    finite=np.isfinite(est[:,0,0])&np.isfinite(est[:,1,0])
    same_numbers(est[finite,1,0]-est[finite,0,0],np.ones(finite.sum()),"self-test shared draw covariance")
    require(np.array_equal(draws,joint_bootstrap(daily,SEED)),"self-test deterministic draws")
    same_numbers(equity_drawdown([-2.,3.,-4.,2.]),4.,"self-test starting equity and chronological drawdown")
    tiny=pd.DataFrame({"signal_bar_open":["2020.01.01 00:30:00","2020.01.01 01:30:00"],"entry_time_msc":[1000,2000],"actual_fill":[100.,101.],"requested_risk":[12.5,15.],
                        "entry_time":["2020.01.01 01:00:00","2020.01.01 02:00:00"],
                        "exit_time":["2020.01.01 01:30:00","2020.01.01 02:30:00"],
                        "exit_time_msc":[1500,2500],"trade_profit":[10.,-20.]})
    filtered=tiny.iloc[[1]].copy()
    filtered.loc[:,"exit_time_msc"]=2600
    result,_=turnover_pair(tiny,filtered)
    require(result["common_qualifying_openings"]==1 and result["removed_qualifying_baseline_openings"]==1 and
            result["common_openings_changed_exit_time"]==1,"self-test rerun turnover keys")
    require((draws[:,0,3]==0).sum()>0,"self-test zero trade denominator disclosure")
    duplicate=pd.concat([tiny,tiny.iloc[[0]]],ignore_index=True)
    flagged,_=turnover_pair(duplicate,filtered)
    require(flagged["opening_keys_unique"] is False,"self-test duplicate opening flag")
    dd=pd.DataFrame({"exit_time_msc":[4,1,3,2],"entry_time_msc":[0]*4,"position_id":[4,1,3,2],
                     "trade_profit":[2.,-2.,-4.,3.],"gross_R":np.array([2.,-2.,-4.,3.])/62.5,
                     "inv_risk_cash":[1/62.5]*4,"requested_risk":[12.5]*4,"risk_cash":[62.5]*4,
                     "day":pd.date_range("2020-01-01",periods=4),"mae_R":[1.]*4,"mfe_R":[1.]*4,
                     "hit1":[1.]*4,"stop_before1":[0.]*4})
    same_numbers(summary(dd,0.,4)["closed_trade_maxDD_cash"],4.,"self-test exit-order DD chronology")
    same_numbers(summary(dd,0.,4)["net_cash_over_closed_trade_maxDD"],-.25,"self-test dollar/DD ratio")
    print("PASS synthetic day ratios/shared draws/zero days/DD chronology/turnover.",flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir",type=Path,default=RUN)
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    try:
        if args.self_test:self_test()
        else:analyse(args.run_dir)
    except (OSError,ValueError,AssertionError,KeyError,AttributeError) as exc:
        parser.exit(1,f"ES width analysis failed: {exc}\n")


if __name__=="__main__":
    main()
