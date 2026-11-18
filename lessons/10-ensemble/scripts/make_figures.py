"""Generate publication-style PNG + SVG + PDF figures from saved experiment outputs."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from sklearn.metrics import roc_curve, precision_recall_curve
from sklearn.tree import plot_tree
import joblib
from research_style import *

plt.rcParams.update({'font.family':'Microsoft YaHei','font.size':11,'axes.titlesize':13,
    'axes.labelsize':11,'xtick.labelsize':10,'ytick.labelsize':10,'axes.spines.top':False,
    'axes.spines.right':False,'axes.labelcolor':INK,'text.color':INK,'axes.edgecolor':'#AAB8B5',
    'xtick.color':MUTED,'ytick.color':MUTED,'grid.color':'#DCE3E1','grid.alpha':.6,
    'savefig.facecolor':'white','figure.facecolor':'white','svg.fonttype':'none','axes.unicode_minus':False})
CAPTIONS={}

def save(name, fig, caption):
    FIG.mkdir(parents=True,exist_ok=True)
    fig.tight_layout(pad=1.6)
    for ext in ['png','svg','pdf']:
        fig.savefig(FIG/f'{name}.{ext}',dpi=190,bbox_inches='tight')
    CAPTIONS[name]=caption
    plt.close(fig)

def grid(ax,axis='y'):
    ax.grid(axis=axis);ax.set_axisbelow(True)

def run():
    cv=read('cv_summary').set_index('model').loc[ORDER]
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),sharey=True)
    for ax,metric,title in zip(axes,['roc_auc','average_precision'],['开发集五折 ROC-AUC','开发集五折 Average precision']):
        for i,n in enumerate(ORDER):
            ax.errorbar(cv.loc[n,metric+'_mean'],i,xerr=cv.loc[n,metric+'_sd'],fmt='o',color=COLOR[n],capsize=4,ms=7)
        ax.set_yticks(range(8),[LABEL[n] for n in ORDER]);ax.invert_yaxis();ax.set_title(title)
        ax.set_xlabel('五折均值 ± 折间样本 SD（不是 CI）');ax.set_xlim(.86,1.008);grid(ax,'x')
    save('performance_cv',fig,'455条开发数据，共享五折；点=折均值，线=±1折间样本SD，非置信区间。所有参数预设。')

    d=read('tree_depth');fig,axes=plt.subplots(1,2,figsize=(11.6,4.3))
    for ax,metric,title in zip(axes,['accuracy','roc_auc'],['深度与准确率','深度与排序性能']):
        for split,c,ls in [('train',COLOR['single_tree'],'--'),('validation',TEAL,'-')]:
            a=d[d.split==split];ax.plot(range(5),a[metric],ls+'o',color=c,label=split)
        ax.set_xticks(range(5),['1','2','3','4','不限']);ax.set_xlabel('max_depth');ax.set_ylabel(metric);ax.set_title(title)
        ax.legend(frameon=False);grid(ax)
    save('tree_depth',fig,'原train341拟合、validation114评价；种子1010；单次曲线无误差线，未据此选主模型深度。')

    sim=read('bootstrap_sampling');b=sim[sim.n==341]
    fig,axes=plt.subplots(1,2,figsize=(11.6,4.0))
    for ax,metric,c,title in zip(axes,['unique_fraction','oob_fraction'],[TEAL,COLOR['single_tree']],['独特训练记录比例','袋外 OOB 比例']):
        vals=b[metric];ax.hist(vals,bins=23,color=c,alpha=.8,edgecolor='white')
        mean=vals.mean();theory=b['expected_unique' if metric=='unique_fraction' else 'expected_oob'].iloc[0]
        ax.axvline(theory,color=INK,ls='--',label=f'有限 n 期望 {theory:.4f}')
        ax.set_title(f'{title}：均值 {mean:.4f}');ax.set_xlabel('占原始341条记录的比例');ax.set_ylabel('模拟次数')
        ax.xaxis.set_major_formatter(PercentFormatter(1));ax.legend(frameon=False,fontsize=10);grid(ax)
    save('bootstrap_sampling',fig,'从341条训练记录有放回抽341次，独立重复2000次；虚线=有限n理论期望；直方图反映抽样变动。')

    roots=read('bootstrap_tree_roots');counts=roots.root_feature.value_counts()
    fig,ax=plt.subplots(figsize=(10,3.8));ax.barh(counts.index,counts,color=TEAL)
    for i,(f,n) in enumerate(counts.items()):
        sub=roots[roots.root_feature==f].root_threshold
        ax.text(n+.25,i,f'{n} / 30；阈值 {sub.min():.4g}—{sub.max():.4g}',va='center',fontsize=11)
    ax.set_xlim(0,max(counts)+14);ax.invert_yaxis();ax.set_xlabel('30次 bootstrap 中根节点使用次数');grid(ax,'x')
    save('root_variation',fig,'同一30份训练bootstrap；每份拟合depth=2、seed1010浅树。阈值范围仅在同一特征内有可比性。')

    tc=read('tree_count_curve');co=read('tree_correlation_summary')
    fig,axes=plt.subplots(1,2,figsize=(12,4.6),gridspec_kw={'width_ratios':[1.5,1]})
    for n in ['bagging','random_forest','rf_all_features']:
        a=tc[tc.model==n];axes[0].plot(a.n_trees,a.validation_roc_auc,'o-',color=COLOR[n],label=LABEL[n])
    axes[0].set_xscale('symlog',linthresh=1);axes[0].set_xticks([1,10,50,100,300],['1','10','50','100','300'])
    axes[0].set_xlabel('树数 B（压缩横轴）');axes[0].set_ylabel('固定验证 ROC-AUC');axes[0].legend(frameon=False,fontsize=10);grid(axes[0])
    a=co[co.kind=='binary_error'].set_index('model').loc[['bagging','rf_all_features','random_forest']]
    axes[1].bar([LABEL[n] for n in a.index],a.mean_correlation,color=[COLOR[n] for n in a.index],width=.65)
    for i,v in enumerate(a.mean_correlation):axes[1].text(i,v+.015,f'{v:.3f}',ha='center')
    axes[1].set_ylim(0,max(.8,a.mean_correlation.max()+.12));axes[1].set_ylabel('树间二值错误 Pearson r 均值')
    axes[1].tick_params(axis='x',labelsize=9);axes[1].set_title('100棵树；排除常数错误向量');grid(axes[1])
    save('tree_count_mechanism',fig,'train341 / validation114，固定种子；左：单次性能曲线无误差线。右：100棵树在相同114条上的错误相关，排除恒定向量；非训练扰动ρ估计。RF-all/sqrt同实现且共享bootstrap索引。')

    bc=read('boosting_curves');fig,axes=plt.subplots(2,2,figsize=(12,6.5))
    lr_colors={.03:'#2F8993',.1:'#D69C30',.3:'#A65A72'}
    for j,n in enumerate(['adaboost','gradient_boosting']):
        for lr,c in lr_colors.items():
            for split,ls in [('train','--'),('validation','-')]:
                a=bc[(bc.model==n)&np.isclose(bc.learning_rate,lr)&(bc.split==split)]
                for ax,metric in [(axes[0,j],'log_loss'),(axes[1,j],'roc_auc')]:
                    ax.plot(a.stage,a[metric],ls,color=c,label=f'lr={lr:g} '+split,lw=1.6)
        axes[0,j].set_title(LABEL[n]);axes[0,j].set_ylabel('Log-loss ↓');axes[1,j].set_ylabel('ROC-AUC ↑')
        axes[1,j].set_xlabel('顺序迭代阶段');axes[0,j].legend(frameon=False,fontsize=8,ncol=2)
        grid(axes[0,j]);grid(axes[1,j])
    save('boosting_curves',fig,'train341 / validation114；lr=.03/.1/.3各200阶段；虚线训练、实线验证，无误差线。探索曲线未用于主模型选择，validation不是独立调参后验证。Ada主模型另预设lr=1/50轮。')

    sp=read('stability_per_sample');ss=read('stability_summary').set_index('model').loc[ORDER]
    fig,axes=plt.subplots(1,2,figsize=(12.4,4.7),gridspec_kw={'width_ratios':[1.6,1]})
    data=[sp[sp.model==n].probability_sd.to_numpy() for n in ORDER]
    b=axes[0].boxplot(data,patch_artist=True,showfliers=False,widths=.6,vert=False)
    for n,patch in zip(ORDER,b['boxes']):patch.set_facecolor(COLOR[n]);patch.set_alpha(.6)
    axes[0].set_yticks(range(1,9),[LABEL[n] for n in ORDER]);axes[0].invert_yaxis()
    axes[0].set_xlabel('逐验证样本的概率 SD（30次重拟合，ddof=1）');grid(axes[0],'x')
    axes[1].barh(range(8),ss.any_flip_fraction,color=[COLOR[n] for n in ORDER]);axes[1].invert_yaxis()
    axes[1].set_yticks(range(8),[LABEL[n] for n in ORDER]);axes[1].xaxis.set_major_formatter(PercentFormatter(1))
    axes[1].set_xlim(0,ss.any_flip_fraction.max()+.11)
    for i,(n,r) in enumerate(ss.iterrows()):axes[1].text(r.any_flip_fraction+.008,i,f'{int(r.n_any_flip)}/114',va='center',fontsize=9)
    axes[1].set_xlabel('30次中曾出现两类的验证样本比例');grid(axes[1],'x')
    save('training_stability',fig,'相同30份train bootstrap，全部模型固定算法种子，validation114不变。箱线：114个逐样本概率SD的中位/IQR/1.5IQR，隐藏离群点；不是CI。右：any-flip定义为30次中类别出现过改变的样本占比，依赖重复次数。模型概率尺度不同。')

    dif=read('paired_differences');a=dif[dif.metric=='roc_auc'].copy()
    fig,ax=plt.subplots(figsize=(11,4.8))
    for i,r in enumerate(a.itertuples()):
        ax.plot([r.low,r.high],[i,i],lw=2.5,color=COLOR[r.model_a]);ax.plot(r.point,i,'o',color=COLOR[r.model_a])
        ax.text(.105,i,f'{r.point:+.4f} [{r.low:+.4f}, {r.high:+.4f}]',va='center',fontsize=9)
    ax.axvline(0,c=MUTED,ls='--');ax.set_yticks(range(len(a)),[LABEL[x]+' − '+LABEL[y] for x,y in zip(a.model_a,a.model_b)])
    ax.set_xlim(min(-.025,a.low.min()-.01),.19);ax.invert_yaxis();ax.set_xlabel('固定模型验证 AUC 差值；成对分层 bootstrap 百分位95%区间');grid(ax,'x')
    save('paired_intervals',fig,'固定train341拟合模型，validation114按类别分层成对重抽样2000次。线=百分位95%区间；条件于当前模型/验证经验分布/类别数量；不含重训、选择或外部人群变化。')

    imp=read('feature_importance');corr=pd.read_csv(RES/'feature_correlation.csv',index_col=0)
    fig,axes=plt.subplots(1,3,figsize=(15,4.9),gridspec_kw={'width_ratios':[1.1,1.1,1]})
    mdi=imp.nlargest(8,'mdi').iloc[::-1];pe=imp.nlargest(8,'permutation_auc_drop_mean').iloc[::-1]
    axes[0].barh(mdi.feature,mdi.mdi,color=TEAL);axes[0].set_title('RF100：训练不纯度重要性');axes[0].set_xlabel('归一化 MDI')
    axes[1].barh(pe.feature,pe.permutation_auc_drop_mean,xerr=pe.permutation_auc_drop_sd,color=COLOR['logistic'],capsize=3)
    axes[1].set_title('验证置换：AUC下降');axes[1].set_xlabel('均值 ± 重复置换SD（非CI）');axes[1].axvline(0,color=MUTED,lw=.8)
    cols=['mean radius','mean perimeter','mean area','worst radius','worst perimeter','worst area']
    im=axes[2].imshow(corr.loc[cols,cols],vmin=0,vmax=1,cmap='YlGnBu')
    short=['mean R','mean P','mean A','worst R','worst P','worst A']
    axes[2].set_xticks(range(6),short,rotation=60,ha='right');axes[2].set_yticks(range(6),short)
    for i in range(6):
        for j in range(6):axes[2].text(j,i,f'{corr.loc[cols[i],cols[j]]:.2f}',ha='center',va='center',fontsize=8,color='white' if corr.loc[cols[i],cols[j]]>.7 else INK)
    axes[2].set_title('train341：尺寸特征 Pearson r')
    grid(axes[0],'x');grid(axes[1],'x')
    save('importance_comparison',fig,'同一主模型RF100；MDI来自train341，置换来自validation114、20次重复、误差线=置换SD；相关矩阵仅train341。重要性不等于因果；相关特征可替代。')

    fig,ax=plt.subplots(figsize=(11,9));im=ax.imshow(corr,vmin=-1,vmax=1,cmap='RdBu_r')
    ax.set_xticks(range(30),corr.columns,rotation=90,fontsize=8);ax.set_yticks(range(30),corr.index,fontsize=8)
    fig.colorbar(im,ax=ax,shrink=.8,label='Pearson r');save('feature_correlation_full',fig,'train341的30特征Pearson相关；435个唯一特征对；描述关联，非因果。')

    val=read('validation_metrics').set_index('model').loc[ORDER]
    fig,axes=plt.subplots(2,4,figsize=(12,6.2))
    for ax,n in zip(axes.flat,ORDER):
        r=val.loc[n];cm=np.array([[r.tn,r.fp],[r.fn,r.tp]],dtype=int);ax.imshow(cm,cmap='Blues',vmin=0,vmax=75)
        for i in range(2):
            for j in range(2):ax.text(j,i,str(cm[i,j]),ha='center',va='center',fontsize=17,color='white' if cm[i,j]>40 else INK)
        ax.set_title(LABEL[n],color=COLOR[n]);ax.set_xticks([0,1],['预测0','预测1']);ax.set_yticks([0,1],['真实0','真实1'])
    save('confusion_matrices',fig,'train341拟合、validation114评价；真实行/预测列；malignant=1，所有模型使用预测概率>=.5，SVM训练内三折sigmoid校准。')

    predictions=read('validation_predictions');fig,axes=plt.subplots(1,2,figsize=(11.5,4.7))
    for n in ORDER:
        a=predictions[predictions.model==n];fpr,tpr,_=roc_curve(a.y,a.probability)
        precision,recall,_=precision_recall_curve(a.y,a.probability)
        axes[0].plot(fpr,tpr,color=COLOR[n],label=LABEL[n]);axes[1].step(recall,precision,where='post',color=COLOR[n])
    axes[0].set(xlabel='False positive rate',ylabel='Sensitivity',title='固定验证 ROC');axes[1].set(xlabel='Recall',ylabel='Precision',title='固定验证 PR（指标报告 AP）')
    axes[0].legend(frameon=False,fontsize=8);axes[1].axhline(predictions.y.mean(),ls='--',color=MUTED)
    grid(axes[0]);grid(axes[1]);save('validation_roc_pr',fig,'train341拟合、validation114评价；PR图以曲线显示，表格AP使用ΣΔRecall×Precision，不是梯形PR面积。PR虚线=固定验证阳性比例。无误差线。')

    fig,ax=plt.subplots(figsize=(10.5,5))
    for n in ORDER:
        r=cv.loc[n];ax.scatter(r.fit_seconds_mean,r.roc_auc_mean,s=75,color=COLOR[n])
        offset=(6,6) if n not in ['bagging','adaboost','rbf_svm','single_tree'] else (6,-14)
        ax.annotate(LABEL[n],(r.fit_seconds_mean,r.roc_auc_mean),xytext=offset,textcoords='offset points',fontsize=10)
    ax.set_xscale('log');ax.set_xlabel('每折训练 wall time 均值 / 秒（含SVM校准，单线程）');ax.set_ylabel('开发集五折 ROC-AUC 均值');grid(ax)
    save('performance_cost',fig,'同机单线程、共享五折，每折训练wall time均值，含预处理和SVM三折校准；非硬件通用基准；点无误差线。')

    tree=joblib.load(OUT/'models/tree_shallow.joblib');features=json.loads((RES/'run_info.json').read_text(encoding='utf-8'))['features']
    fig,ax=plt.subplots(figsize=(13,5.5));plot_tree(tree,feature_names=features,class_names=['benign','malignant'],filled=True,rounded=True,precision=3,fontsize=10,ax=ax)
    save('example_tree',fig,'本次真实train341的depth2示例树，seed1010；叶概率为训练叶节点恶性比例，非外部校准风险。与课件手算题分开报告。')
    (FIG/'captions.json').write_text(json.dumps(CAPTIONS,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Generated',len(CAPTIONS),'figures in PNG/SVG/PDF:',FIG)

if __name__=='__main__':run()
