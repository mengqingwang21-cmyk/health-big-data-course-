"""Improve readability of existing figures; never change measured values."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
B=Path(__file__).resolve().parents[1]; R=B/'results'; F=R/'figures'
plt.rcParams.update({'font.family':'Microsoft YaHei','axes.unicode_minus':False,'font.size':11})
colors=['#1677b3','#d46a20']
def save(name):
    plt.savefig(F/(name+'.png'),dpi=300,bbox_inches='tight'); plt.close()
q=pd.read_csv(R/'tables/Q2-learning-summary.csv')
fig,ax=plt.subplots(figsize=(8.5,5.5))
inset=ax.inset_axes([.52,.16,.44,.36])
for idx,(noise,g) in enumerate(q.groupby('noise_features')):
    label=['原始30特征','增加300个噪声特征'][idx]
    style=dict(marker=['o','s'][idx],color=colors[idx],lw=1.7,ms=6,label=label)
    ax.plot(g.n,g.validation_auc,**style)
    inset.plot(g.n,g.train_auc,**style,ls=['-','--'][idx],mfc=['white',colors[idx]][idx],zorder=4-idx)
inset.set(title='训练集局部放大',ylim=(.99945,1.00008),xticks=[40,200,398],yticks=[.9995,1.0])
inset.tick_params(labelsize=8); inset.title.set_size(9); inset.ticklabel_format(axis='y',style='plain',useOffset=False)
ax.set(xlabel='训练记录数 n',ylabel='验证集平均AUC',ylim=(.94,1.002),xticks=[40,100,200,398],title='WDBC  逻辑回归学习曲线')
ax.legend(loc='upper left',fontsize=10); ax.grid(alpha=.15); fig.tight_layout(); save('Q2-learning-curves')
q=pd.read_csv(R/'tables/Q6-selection.csv'); fig,axes=plt.subplots(1,2,figsize=(10.5,4.6),gridspec_kw={'width_ratios':[1.6,1]})
for idx,(col,label) in enumerate([('reused_holdout_auc','重复使用留出集'),('fresh_audit_auc','新审计数据')]):
    axes[0].plot(q.candidates,q[col],marker=['o','s'][idx],color=colors[idx],label=label,mfc=['white',colors[idx]][idx],zorder=4)
axes[1].plot(q.candidates,q.fresh_audit_auc,'s-',color=colors[1],label='新审计数据',zorder=4)
for ax in axes:
    ax.set_xscale('log'); ax.set_xticks([1,5,20,100,200],['1','5','20','100','200'])
    ax.axhline(.5,color='#777777',ls='--',lw=1,label='随机水平',zorder=1); ax.set(xlabel='候选数 B（对数刻度）',ylabel='100轮平均AUC'); ax.grid(alpha=.15)
axes[0].set(title='A  留出集与新数据',ylim=(.48,.70)); axes[0].legend(fontsize=9)
axes[1].set(title='B  新数据局部放大',ylim=(.495,.506)); axes[1].legend(fontsize=9)
fig.tight_layout(); save('Q6-selection')
q=pd.read_csv(R/'tables/Q7-domain-shift.csv').set_index('model').loc[['both_markers','biological_only']]
fig,ax=plt.subplots(figsize=(8,5)); x=[0,1]
for idx,(col,label) in enumerate([('internal','内部验证'),('shifted_simulated_site','模拟新中心')]):
    xx=[i+[-.18,.18][idx] for i in x]
    bars=ax.bar(xx,q[col],width=.36,color=colors[idx],label=label)
    for bar,value in zip(bars,q[col]):
        ax.text(bar.get_x()+bar.get_width()/2,max(float(value),.005)+.015,f'{value:.4f}',ha='center',va='bottom',fontsize=11)
        if value<.01: ax.plot(bar.get_x()+bar.get_width()/2,value,marker='_',ms=14,color=colors[idx],zorder=5)
ax.set_xticks(x,['双指标（含中心代理）','仅疾病指标']); ax.set(xlabel='模型输入',ylabel='AUC',ylim=(0,1.16),title='模拟中心变化  模型表现'); ax.legend(loc='upper right',fontsize=9)
fig.tight_layout(); save('Q7-domain-shift')
print('Updated learning curve inset, logarithmic selection plot, and all four bar labels.')
