"""Static example of the manual overlay, using verified replay fills and signals."""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as dates
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
RUN=ROOT/'Reports/rtl_vwap_replay_20261026'
DAY=pd.Timestamp('2026-09-14')


def main():
    f=pd.read_csv(ROOT/'Reports/rtl_vwap_20261025/features_full_hlc3.csv',
        parse_dates=['bar_time','available_at','feature_session'],float_precision='round_trip')
    bars=f.loc[f.bar_time.dt.normalize().eq(DAY)].copy()
    j=np.searchsorted(f.available_at.to_numpy(),bars.bar_time.to_numpy(),side='right')-1
    prior=f.iloc[j].reset_index(drop=True)
    valid=prior.feature_session.eq(DAY)&prior.vwap_available&prior.a20.gt(0)
    x=dates.date2num(bars.bar_time)
    fig,axes=plt.subplots(2,1,figsize=(15,9),sharex=True,sharey=True)
    for ax,variant in zip(axes,('off','on')):
        for at,b in zip(x,bars.itertuples()):
            color='#168b7b' if b.close>=b.open else '#bc5260'
            ax.vlines(at,b.low,b.high,color=color,lw=.9)
            ax.add_patch(Rectangle((at-.006,min(b.open,b.close)),.012,max(abs(b.close-b.open),.25),
                                   facecolor=color,edgecolor=color,alpha=.65))
        ax.plot(x,prior.vwap.where(valid),color='#2574b8',lw=1.8,label='VWAP known at bar open')
        ax.plot(x,(prior.vwap-prior.a20).where(valid),color='#d58b16',ls='--',lw=1.5,label='VWAP − A20')
        t=pd.read_csv(RUN/f'trades_{variant}.csv',parse_dates=['submitted','entry_time','exit_time'])
        t=t.loc[t.submitted.dt.normalize().eq(DAY)]
        for row in t.itertuples():
            ax.plot(dates.date2num([row.entry_time,row.exit_time]),[row.fill_price,row.exit_price],
                    color='#455364',ls=':',lw=1)
        ax.scatter(dates.date2num(t.entry_time),t.fill_price,marker='^',s=65,color='#006640',zorder=4,label='Actual buy fill')
        ax.scatter(dates.date2num(t.exit_time),t.exit_price,marker='v',s=55,color='#263342',zorder=4,label='Actual exit')
        c=pd.read_csv(RUN/f'candidates_{variant}.csv',parse_dates=['submitted'])
        c=c.loc[c.submitted.dt.normalize().eq(DAY)&c.blocked.eq(1)]
        ax.scatter(dates.date2num(c.submitted),c.signal_close,marker='x',s=65,color='#dd3333',zorder=5,label='Blocked signal')
        ax.set_title(f'VWAP gate {variant.upper()} · {len(t)} filled trades · {len(c)} blocked requests',loc='left',fontweight='bold')
        ax.grid(alpha=.15);ax.set_ylabel('NQ price');ax.spines[['top','right']].set_visible(False)
    axes[0].legend(loc='upper left',ncol=3,fontsize=9,framealpha=.95)
    axes[1].xaxis.set_major_locator(dates.HourLocator(interval=2))
    axes[1].xaxis.set_major_formatter(dates.DateFormatter('%H:%M'))
    axes[1].set_xlabel('Source clock: Chicago + 8 hours')
    fig.suptitle('RTL trade and VWAP inspection · 14 September 2026',x=.08,ha='left',fontweight='bold',fontsize=17)
    fig.text(.08,.935,'Verified full-replay ledger preview · M30 candles · 1-minute OHLC simulation',color='#526072',fontsize=11)
    fig.text(.08,.025,'Lines use completed information at each bar open. Red X: decision time / previous signal close.\n'
             'Fills and exits come from the full replay; a separately started short manual run can differ initially.',fontsize=10,color='#526072')
    fig.tight_layout(rect=(.02,.065,1,.91))
    target=ROOT/'docs/baseline/rtl-vwap/manual_visual_example.png'
    fig.savefig(target,dpi=160);plt.close(fig)
    print(target)


if __name__=='__main__':
    main()
