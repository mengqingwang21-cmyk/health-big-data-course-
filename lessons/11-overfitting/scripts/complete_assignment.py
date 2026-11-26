"""Run supplied experiments, one controlled variation, tables and figures.
Run this file with the isolated Python environment; outputs stay in results/.
"""
from pathlib import Path
import json
import platform
import hashlib
import numpy as np
import pandas as pd
import sklearn
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import run_experiments as exp

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'results'
RAW = OUT / 'baseline'
FIG = OUT / 'figures'
TAB = OUT / 'tables'
for folder in (RAW, FIG, TAB):
    folder.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({'font.family': 'Microsoft YaHei', 'axes.unicode_minus': False})

predictions = {
    'Q1': '树加深时训练表现提高，验证表现先改善再下降。',
    'Q2': '样本减少、噪声特征增加会降低验证AUC；样本增多后差距预计缩小。',
    'Q3': '不限深度决策树的折间波动预计大于逻辑回归。',
    'Q4': '无信号数据全局筛选会产生虚高分数，折内筛选预计接近0.5。',
    'Q5': '按行划分预计分数较高，按患者划分预计接近0.5。',
    'Q6': '候选增加会推高被反复使用的留出集分数，新数据预计仍接近0.5。',
    'Q7': '含中心代理的模型内部表现好，关系反转后会明显恶化。',
    'variation': '只修改E4的K_SELECT：20改为5和50；错误流程预计仍高于正确流程，正确流程均值预计接近0.5。错误流程偏差大小随k变化，不预设单调。'
}
(OUT / 'predictions.json').write_text(json.dumps(predictions, ensure_ascii=False, indent=2), encoding='utf-8')
for name in ('e1', 'e2', 'e3', 'e4', 'e5', 'e6', 'e7'):
    getattr(exp, name)(RAW)
    print('Completed', name.upper(), flush=True)
exp.summarize(RAW)

def read(name):
    return pd.read_csv(RAW / (name + '.csv'))

def table(df, name):
    df.to_csv(TAB / (name + '.csv'), index=False, encoding='utf-8-sig')
    return df

def finish(name):
    plt.tight_layout()
    plt.savefig(FIG / (name + '.png'), dpi=180)
    plt.close()

q1 = table(read('E1-complexity'), 'Q1-complexity')
plt.figure(figsize=(8, 4.5))
for col, label in [('train_auc','训练AUC'),('validation_auc','验证AUC')]:
    plt.plot(range(len(q1)), q1[col], 'o-', label=label)
plt.xticks(range(len(q1)), q1.depth)
for lo, hi, label, color in [(-.4,.4,'相对欠拟合','#ffe3a0'),(.5,2.4,'较合适','#c8edd1'),(2.5,5.4,'过拟合','#f7cccc')]:
    plt.axvspan(lo,hi,alpha=.35,color=color)
    plt.text((lo+hi)/2,.84,label,ha='center')
plt.ylim(.82,1.01); plt.xlabel('决策树最大深度'); plt.ylabel('AUC'); plt.legend()
finish('Q1-complexity')
q2 = table(read('E1-sample-features').groupby(['n','noise_features'])[['train_auc','validation_auc']].mean().reset_index(), 'Q2-learning-summary')
wide = q2.pivot(index='n',columns='noise_features',values='validation_auc').reset_index()
wide.columns=['n','original_30_features','plus_300_noise']
wide['difference_original_minus_noise']=wide.original_30_features-wide.plus_300_noise
table(wide,'Q2-comparison')
fig,axes=plt.subplots(1,2,figsize=(10,4))
for noise,group in q2.groupby('noise_features'):
    for ax,col in zip(axes,['train_auc','validation_auc']):
        ax.plot(group.n,group[col],'o-',label=f'噪声特征数={noise}')
        ax.set(xlabel='训练样本量',ylabel=col,ylim=(.5,1.02)); ax.legend()
finish('Q2-learning-curves')
q3=table(read('E2-cv').groupby('model').auc.agg(['count','mean','std','min','max']).reset_index(),'Q3-cv-statistics')
top=table(read('E2-case-deletion').sort_values(['mean_absolute_probability_change','removed_train_index'],ascending=[False,True]).head(3),'Q3-deletion-top3')
cv=read('E2-cv'); plt.figure(figsize=(6,4)); plt.boxplot([cv[cv.model.eq(m)].auc for m in ['tree','logistic']],tick_labels=['决策树','逻辑回归']); plt.ylabel('25折AUC'); finish('Q3-cv')
table(read('E3-scaling'),'Q4-scaling')
q4=table(read('E4-feature-selection').groupby('method').auc.agg(['count','mean','std']).reset_index(),'Q4-feature-selection')
q5=table(read('E5-patient-split').groupby('method')[['auc','overlap_patients']].mean().reset_index(),'Q5-patient-split')
q6=table(read('E6-repeated-selection').groupby('candidates')[['reused_holdout_auc','fresh_audit_auc']].mean().reset_index(),'Q6-selection')
plt.figure(figsize=(7,4))
for col,label in [('reused_holdout_auc','反复使用的留出集'),('fresh_audit_auc','全新审计数据')]:
    plt.plot(q6.candidates,q6[col],'o-',label=label)
plt.axhline(.5,color='gray',ls='--'); plt.xlabel('候选数量'); plt.ylabel('100轮平均AUC'); plt.legend(); finish('Q6-selection')
q7=table(read('E7-domain-shift').pivot(index='model',columns='cohort',values='auc').reset_index(),'Q7-domain-shift')
q7.set_index('model').plot.bar(figsize=(8,4),rot=0); plt.ylabel('AUC'); finish('Q7-domain-shift')

variation=[]
for k in [5,20,50]:
    if k == 20:
        df=read('E4-feature-selection')
    else:
        folder=OUT / f'variation-k{k}'; folder.mkdir(exist_ok=True)
        exp.K_SELECT=k; exp.e4(folder)
        df=pd.read_csv(folder / 'E4-feature-selection.csv')
    df=df.copy(); df['k']=k; variation.append(df)
exp.K_SELECT=20
v=pd.concat(variation,ignore_index=True)
v.to_csv(OUT / 'variation-all.csv',index=False)
vs=table(v.groupby(['k','method']).auc.agg(['count','mean','std']).reset_index(),'variation-summary')
plt.figure(figsize=(7,4))
for method,g in vs.groupby('method'):
    plt.plot(g.k,g['mean'],'o-',label=method)
plt.axhline(.5,color='gray',ls='--'); plt.xlabel('保留特征数量k'); plt.ylabel('100折平均AUC'); plt.legend(); finish('variation-k')
metadata={'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__,'matplotlib':matplotlib.__version__,'seed':exp.SEED,'data_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE/'data').glob('*.csv')},'std_definition':'sample standard deviation, ddof=1; repeated CV folds are not independent'}
(OUT/'environment.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
assert len(read('E2-cv'))==50 and len(read('E2-case-deletion'))==398
assert len(read('E4-feature-selection'))==200 and len(v)==600
assert (read('E5-patient-split').query("method == 'group_split'").overlap_patients==0).all()
print('All experiments, variation, tables and figures completed:',OUT,flush=True)
