"""Refresh labels and legends using existing measured results only."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
B=Path(__file__).resolve().parents[1]; R=B/'results'; F=R/'figures'
plt.rcParams.update({'font.family':'Microsoft YaHei','axes.unicode_minus':False,'font.size':11})
def save(name):
    plt.tight_layout(); plt.savefig(F/(name+'.png'),dpi=220); plt.close()
def table(name): return pd.read_csv(R/'tables'/(name+'.csv'))
c=['#1677b3','#d46a20']
q=table('Q1-complexity'); fig,ax=plt.subplots(figsize=(8,4.7))
for col,label,color,marker in [('train_auc','训练集',c[0],'o'),('validation_auc','验证集',c[1],'s')]:
    ax.plot(range(len(q)),q[col],marker=marker,color=color,label=label)
ax.set_xticks(range(len(q)),['1','2','3','5','10','unlimited'])
for lo,hi,label,color in [(-.4,.4,'相对欠拟合','#ffe3a0'),(.5,2.4,'较合适','#c8edd1'),(2.5,5.4,'过拟合','#f7cccc')]:
    ax.axvspan(lo,hi,alpha=.35,color=color); ax.text((lo+hi)/2,.84,label,ha='center')
ax.set(xlabel='决策树最大深度 max_depth',ylabel='AUC',ylim=(.82,1.01),title='WDBC  决策树复杂度曲线'); ax.legend(); save('Q1-complexity')
q=table('Q2-learning-summary'); fig,axes=plt.subplots(1,2,figsize=(10,4.5))
for idx,(noise,g) in enumerate(q.groupby('noise_features')):
    for ax,col in zip(axes,['train_auc','validation_auc']):
        ax.plot(g.n,g[col],marker=['o','s'][idx],color=c[idx],label=['原始30特征','原始30特征 + 300噪声'][idx])
for ax,title in zip(axes,['A  训练集','B  验证集']):
    ax.set(xlabel='训练记录数 n',ylabel='平均AUC',ylim=(.5,1.02),title=title); ax.legend(fontsize=8)
fig.suptitle('WDBC  标准化与逻辑回归的学习曲线'); save('Q2-learning-curves')
q=pd.read_csv(R/'baseline/E2-cv.csv'); fig,ax=plt.subplots(figsize=(6.5,4.5))
ax.boxplot([q[q.model.eq(m)].auc for m in ['tree','logistic']],tick_labels=['不限深度决策树','标准化 + 逻辑回归'],whis=1.5)
ax.set(xlabel='分类模型',ylabel='每折AUC',title='WDBC训练部分  5次重复五折CV'); save('Q3-cv')
q=table('Q6-selection'); fig,ax=plt.subplots(figsize=(7.5,4.5))
for idx,(col,label) in enumerate([('reused_holdout_auc','重复使用留出集（80条）'),('fresh_audit_auc','新审计数据（400条）')]):
    ax.plot(q.candidates,q[col],marker=['o','s'][idx],color=c[idx],label=label)
ax.axhline(.5,color='gray',ls='--',label='随机水平 AUC = 0.5')
ax.set(xlabel='候选数量 B',ylabel='100轮平均AUC',title='随机预测模拟  重复选择偏差'); ax.legend(fontsize=9); save('Q6-selection')
q=table('Q7-domain-shift').set_index('model').loc[['both_markers','biological_only']]
fig,ax=plt.subplots(figsize=(7.5,4.8)); x=[0,1]
ax.bar([i-.18 for i in x],q.internal,width=.36,color=c[0],label='内部验证（200条）')
ax.bar([i+.18 for i in x],q.shifted_simulated_site,width=.36,color=c[1],label='模拟新中心（200条）')
ax.set_xticks(x,['双指标（含中心代理）','仅疾病指标'])
ax.set(xlabel='模型输入',ylabel='AUC',ylim=(0,1.13),title='模拟队列  中心代理关系反转'); ax.legend(fontsize=9); save('Q7-domain-shift')
q=table('variation-summary'); fig,ax=plt.subplots(figsize=(7.5,4.5))
for idx,(method,label) in enumerate([('fold_pipeline','正确：训练折内筛选'),('global_selection_leaky','错误：全部记录筛选')]):
    g=q[q.method.eq(method)]; ax.plot(g.k,g['mean'],marker=['o','s'][idx],color=c[idx],label=label)
ax.set_xticks([5,20,50]); ax.axhline(.5,color='gray',ls='--',label='随机水平 AUC = 0.5')
ax.set(xlabel='保留特征数 k',ylabel='100折平均AUC',title='null-omics  特征筛选数量敏感性分析'); ax.legend(fontsize=9); save('variation-k')
print('Refreshed 6 numeric figures with explicit dataset, axis labels and Chinese legends.')
