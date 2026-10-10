"""Plot validated ES baseline versus the single minimum-50-tick EA rule."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from project_paths import PROJECT_ROOT as ROOT

RUN=ROOT/'Reports/es_width_filter_20261011'
OUT=ROOT/'docs/baseline/es-minimum-width'
COLORS={'baseline':'#476da2','min50':'#16867d'}
LABELS={'baseline':'Baseline','min50':'Minimum 50 ticks'}
PERIODS=('2010-15','2016-19','2020-26')


def save(fig,name):
    OUT.mkdir(parents=True,exist_ok=True)
    for suffix in ('png','svg'):
        fig.savefig(OUT/(name+'.'+suffix),dpi=180,facecolor='white',bbox_inches='tight')
    plt.close(fig)
    print('Wrote',OUT/name,flush=True)


def main():
    checks=json.loads((RUN/'analysis_checks.json').read_text(encoding='utf-8'))
    if not checks['all_passed'] or len(checks['jobs'])!=4: raise ValueError('Four validated runs required')
    data=pd.read_csv(RUN/'summary.csv')
    data=data[(data['sample']=='full_sample')&(data['mode']=='rtl')&(data.cost_roundtrip==1.05)&data.period.isin(PERIODS)]
    if len(data)!=6: raise ValueError('Missing declared period/variant estimates')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,
                         'text.color':'#17212d','axes.labelcolor':'#334155','xtick.color':'#475569','ytick.color':'#475569'})
    fig,axes=plt.subplots(2,2,figsize=(13,8.8))
    fig.subplots_adjust(left=.08,right=.98,top=.80,bottom=.12,hspace=.35,wspace=.23)
    fig.text(.08,.956,'ES: does a 50-tick minimum help RTL?',fontsize=22,fontweight='bold')
    fig.text(.08,.913,'Full EA reruns; one MES contract; 12.5 price-point minimum; original bar-close exit.',fontsize=12,color='#536176')
    fig.text(.08,.873,'$1.05 arithmetic cost per round trip. Error bars: paired source-day 95% intervals. All history was previously examined.',fontsize=11,color='#536176')
    x=np.arange(3)
    specs=[('mean_net_R','Average net R per trade','R'),('net_cash','Net dollars at fixed contracts','USD'),
           ('trades','Trade frequency','Trades'),('mean_fixed_contract_risk_cash','Mean initial dollar risk per trade','USD')]
    for ax,(metric,title,ylabel) in zip(axes.flat,specs):
        for variant,offset in [('baseline',-.17),('min50',.17)]:
            values=data[data.variant==variant].set_index('period').reindex(PERIODS)
            xx=x+offset
            if metric=='mean_net_R':
                ax.scatter(xx,values[metric],color=COLORS[variant],s=55,label=LABELS[variant],zorder=3)
                ax.vlines(xx,values[metric+'_lo95'],values[metric+'_hi95'],color=COLORS[variant],linewidth=2)
                for z,lo,hi in zip(xx,values[metric+'_lo95'],values[metric+'_hi95']):
                    ax.hlines([lo,hi],z-.045,z+.045,color=COLORS[variant],linewidth=2)
            else:
                ax.bar(xx,values[metric],width=.30,color=COLORS[variant],label=LABELS[variant])
        ax.set_xticks(x,PERIODS); ax.set_xlim(-.5,2.5)
        ax.set_title(title,fontweight='bold',fontsize=13,pad=12); ax.set_ylabel(ylabel)
        ax.grid(axis='y',alpha=.16); ax.set_axisbelow(True)
        if metric in ('mean_net_R','net_cash'): ax.axhline(0,color='#8c98a8',linewidth=.8)
        else: ax.set_ylim(bottom=0)
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='lower center',ncol=2,frameon=False,bbox_to_anchor=(.53,.02))
    save(fig,'rtl-width-filter')
    annual=pd.read_csv(RUN/'yearly.csv')
    annual=annual[(annual['sample']=='full_sample')&(annual['mode']=='rtl')&(annual.cost_roundtrip==1.05)]
    years=sorted(annual.year.unique()); x=np.arange(len(years))
    fig,ax=plt.subplots(figsize=(15,5.2))
    fig.subplots_adjust(left=.07,right=.98,bottom=.20,top=.72)
    fig.text(.07,.94,'Year-by-year net dollars',fontsize=22,fontweight='bold')
    fig.text(.07,.87,'Fixed one-MES sizing, $1.05 per round trip. Partial years: 2010 from June; 2026 through July 13.',fontsize=11,color='#536176')
    for variant,offset in [('baseline',-.17),('min50',.17)]:
        q=annual[annual.variant==variant].set_index('year').reindex(years)
        ax.bar(x+offset,q.net_cash,width=.30,color=COLORS[variant],label=LABELS[variant])
    ax.set_xticks(x,[str(y)+('*' if y in (2010,2026) else '') for y in years]); ax.set_ylabel('Net USD')
    ax.grid(axis='y',alpha=.16); ax.set_axisbelow(True); ax.axhline(0,color='#8c98a8',linewidth=.8)
    ax.legend(frameon=False,ncol=2,loc='upper left')
    save(fig,'rtl-yearly-net')


if __name__=='__main__': main()
