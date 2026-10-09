"""Render matched path and target-retention figures from validated analysis tables."""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

from project_paths import PROJECT_ROOT as ROOT

RUN=ROOT/'Reports/path_experiment_20261009'
OUT=ROOT/'docs/baseline/path-interaction'
COLORS={'NQ':'#15877e','NQcoarse':'#cf862f','ES':'#4669a2'}
INSTRUMENTS=('NQ','NQcoarse','ES')
RETENTION=(
    ('p_actual_same_bar_close_above_given_reach1','Qualifying close','#15877e'),
    ('p_actual_same_bar_close_below_given_reach1','Checked below target','#e1c468'),
    ('p_stop_before_same_bar_check_given_reach1','Stopped before check','#c56456'),
    ('p_administrative_exit_before_same_bar_check_given_reach1','Administrative exit','#7f97b3'),
    ('p_no_available_same_bar_check_given_reach1','No touch-bar check','#b6bdc6'),
)


def select(data,mode,metric):
    frame=data[(data['mode']==mode)&(data.metric==metric)].set_index('instrument').reindex(INSTRUMENTS)
    if frame.value.isna().any() or len(frame)!=3:
        raise ValueError(f'Missing six-arm matched metric {mode}/{metric}')
    return frame


def intervals(ax,frame,offset,marker,scale=1):
    for index,instrument in enumerate(INSTRUMENTS):
        row=frame.loc[instrument]
        x=index+offset
        ax.vlines(x,row.lo95*scale,row.hi95*scale,color=COLORS[instrument],linewidth=1.8)
        ax.hlines([row.lo95*scale,row.hi95*scale],x-.035,x+.035,color=COLORS[instrument],linewidth=1.8)
        ax.plot(x,row.value*scale,marker,color=COLORS[instrument],markersize=8,markeredgewidth=1.8)


def save(fig,stem):
    OUT.mkdir(parents=True,exist_ok=True)
    for ext in ('png','svg'):
        target=OUT/f'{stem}.{ext}'
        fig.savefig(target,dpi=180,facecolor='white',bbox_inches='tight')
        print(f'Wrote {target}')
    plt.close(fig)


def main():
    checks=__import__('json').loads((RUN/'analysis_checks.json').read_text())
    if not checks['all_passed'] or len(checks['jobs'])!=6:
        raise ValueError('Six validated complete path jobs required')
    metrics=pd.read_csv(RUN/'matched_metrics.csv')
    data=metrics[(metrics.period=='2020-26')&(metrics.panel=='six_arm_common')&
                 (metrics.size_basis=='effective')&(metrics['sample']=='primary')]
    if data.empty:
        raise ValueError('Recent six-arm effective-step overlap unavailable')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,
                         'axes.spines.right':False,'axes.labelcolor':'#334155','text.color':'#17212d',
                         'xtick.color':'#475569','ytick.color':'#475569'})
    fig,axes=plt.subplots(2,3,figsize=(15,8.2),sharex=True)
    fig.subplots_adjust(left=.075,right=.98,bottom=.135,top=.79,wspace=.28,hspace=.31)
    fig.text(.075,.955,'Matched post-entry paths, 2020-26',fontsize=22,fontweight='bold')
    fig.text(.075,.914,'Same year, entry session and signal-size bins; fixed common weights across all six arms.',fontsize=12,color='#536176')
    fig.text(.075,.875,'Points and bars show adjusted estimates and paired-day 95% intervals. Paths end at actual exit.',fontsize=11,color='#536176')
    specifications=(
        ('Excursion over the holding period','R using actual filled risk','mean_mfe_R','MFE','o','mean_mae_R','MAE','x',1),
        ('First barrier and +1R reach','Percent of all trades','p_reach1','Reach +1R','o','p_stop_before1','Stop before +1R','x',100),
        ('Retention at the touch-bar close','Percent of +1R reachers','p_actual_same_bar_close_above_given_reach1','Qualifying close','o',
         'p_stop_before_same_bar_check_given_reach1','Stopped before check','x',100),
    )
    for row,mode in enumerate(('rtl','control')):
        for col,(title,ylabel,m1,l1,s1,m2,l2,s2,scale) in enumerate(specifications):
            ax=axes[row,col]
            intervals(ax,select(data,mode,m1),-.1,s1,scale)
            intervals(ax,select(data,mode,m2),.1,s2,scale)
            ax.set_title(('RTL: ' if mode=='rtl' else 'Control: ')+title,fontsize=12,fontweight='bold',pad=13)
            ax.set_ylabel(ylabel)
            ax.set_xticks(range(3),['NQ','Coarse NQ','ES'])
            ax.set_xlim(-.4,2.4)
            ax.grid(axis='y',alpha=.16)
            ax.set_axisbelow(True)
            if scale==100: ax.set_ylim(0,100)
            else: ax.set_ylim(bottom=0)
            ax.legend(handles=[Line2D([0],[0],marker=s1,linestyle='none',color='#334155',label=l1),
                               Line2D([0],[0],marker=s2,linestyle='none',color='#334155',label=l2)],
                      frameon=False,fontsize=9,loc='upper right')
    fig.text(.075,.055,'Coarse NQ uses the existing yearly ES-like grid. Matching coverage and broader coarse-NQ/ES results are disclosed in RESULTS.md.',fontsize=10,color='#536176')
    save(fig,'matched-paths-2020-26')
    fig,axes=plt.subplots(1,2,figsize=(14,4.8),sharex=True,sharey=True)
    fig.subplots_adjust(left=.09,right=.98,bottom=.22,top=.70,wspace=.18)
    fig.text(.09,.94,'What happens after reaching +1R?',fontsize=22,fontweight='bold')
    fig.text(.09,.88,'2020-26, same six-arm matched population. Every reacher belongs to one category; after-exit prices do not count as success.',fontsize=11,color='#536176')
    for ax,mode in zip(axes,('rtl','control')):
        left=np.zeros(3)
        for metric,label,color in RETENTION:
            values=select(data,mode,metric).value.to_numpy()*100
            ax.barh(range(3),values,left=left,color=color,height=.58,label=label)
            left+=values
        if not np.allclose(left,100,atol=1e-7):
            raise ValueError('Retained reacher categories do not partition 100%')
        ax.set_title('RTL' if mode=='rtl' else 'Market control',fontweight='bold',fontsize=14,pad=13)
        ax.set_yticks(range(3),['NQ','Coarse NQ','ES'])
        ax.set_xlim(0,100)
        ax.set_xlabel('Percent of trades reaching +1R')
        ax.grid(axis='x',alpha=.15)
        ax.set_axisbelow(True)
    axes[0].invert_yaxis()
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='lower center',ncol=3,frameon=False,bbox_to_anchor=(.53,.01),fontsize=10)
    save(fig,'touch-retention-2020-26')


if __name__=='__main__':
    main()
