"""Add the verified session-flat benchmark and render the extended comparison."""
import json
import shutil
import numpy as np
import pandas as pd
from project_paths import PROJECT_ROOT as ROOT
from run_rtl_vwap_replay import digest, save_json

RUN=ROOT/'Reports/buy_hold_20261108/comparison'
SESSION=ROOT/'Reports/buy_hold_20261108/session_flat'
NAME='Hold, flatten/reopen each session'

def extend(table,chart):
 audit=json.loads((SESSION/'verification.json').read_text())
 assert audit['all_passed'] and audit['all_native_fills_verified'] and audit['gross_equity_dd_matches_mt5']
 assert digest(SESSION/'summaries.csv')==audit['summaries_sha256']
 extra=pd.read_csv(SESSION/'summaries.csv')
 assert set(extra.period)==set(table.period) and len(extra)==5
 old=table.loc[table.strategy.ne(NAME)].copy()
 out=pd.concat([old,extra],ignore_index=True)
 pd.testing.assert_frame_equal(out.iloc[:len(old)].reset_index(drop=True),old.reset_index(drop=True))
 daily=pd.read_csv(SESSION/'daily_equity.csv')
 et=pd.to_datetime(daily.time).to_numpy(dtype='datetime64[s]').astype(np.int64)
 times=pd.to_datetime(chart.time).to_numpy(dtype='datetime64[s]').astype(np.int64)
 idx=np.searchsorted(et,times,side='right')-1
 chart=chart.copy();chart[NAME]=np.where(idx>=0,daily.equity.to_numpy()[np.maximum(idx,0)],0.)
 expected=extra.loc[extra.period.eq('Full 2010-26'),'net'].iloc[0]
 assert abs(chart[NAME].iloc[-1]-expected)<1e-7
 return out,chart

def plot(chart):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 plt.style.use('seaborn-v0_8-whitegrid')
 fig,axes=plt.subplots(1,2,figsize=(14,5.5),sharey=True)
 for ax,family in zip(axes,['RTL','GG']):
  colors={'Hold raw series':'#a3aab3','Hold with rollovers':'#202c39',NAME:'#9c43ad',
          family:'#a67c52',family+' + VWAP':'#1769aa',family+' + VWAP + exclude 16-17':'#09866e'}
  for name,color in colors.items():
   label='Hold, daily flatten/reopen' if name==NAME else name.replace(family+' + ','')
   ax.plot(pd.to_datetime(chart.time),chart[name]/1000,label=label,color=color,lw=1.6)
  ax.set(title=family,xlabel='');ax.legend(loc='upper left',frameon=True,fontsize=8)
  ax.axhline(0,color='#667085',lw=.7)
 axes[0].set_ylabel('Cumulative net profit (USD thousands)')
 fig.suptitle('One contract: passive holding, session flattening, and RTL/GG filters',fontsize=14)
 fig.text(.06,.015,'MNQ sizing (USD 2/point), USD 1.05 per completed position. Daily chart; table drawdowns measured intraday. Final data: 1 Oct 2026.',fontsize=9)
 fig.tight_layout(rect=[0,.04,1,.94]);fig.savefig(RUN/'comparison.png',dpi=160);plt.close(fig)

def main():
 current=json.loads((RUN/'verification.json').read_text())
 assert current['all_passed'] and digest(RUN/'comparison.csv')==current['comparison_sha256']
 for name in ['comparison.csv','daily_equity.csv','verification.json','comparison.png']:
  dest=RUN/('before_session_'+name)
  if not dest.exists():shutil.copyfile(RUN/name,dest)
 s,c=extend(pd.read_csv(RUN/'comparison.csv'),pd.read_csv(RUN/'daily_equity.csv'))
 s.to_csv(RUN/'comparison.csv',index=False,float_format='%.10f')
 c.to_csv(RUN/'daily_equity.csv',index=False)
 plot(c)
 current.update(session_benchmark_verified=True,previous_vwap_comparison_unchanged=True,
  session_verification_sha256=digest(SESSION/'verification.json'),comparison_sha256=digest(RUN/'comparison.csv'))
 save_json(RUN/'verification.json',current)
 print(s.loc[s.strategy.eq(NAME),['period','positions','net','equity_dd','net_dd']].to_string(index=False))

if __name__=='__main__':main()
