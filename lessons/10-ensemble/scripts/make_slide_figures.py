"""Reduced-panel figures with fonts sized for projection (also PNG/SVG/PDF)."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from research_style import *

def save(name,fig):
    fig.tight_layout(pad=1)
    for ext in ['png','svg','pdf']:fig.savefig(FIG/f'slide_{name}.{ext}',dpi=200,bbox_inches='tight',facecolor=PAPER)
    plt.close(fig)

def run():
    plt.rcParams.update({'font.family':'Microsoft YaHei','font.size':15,'axes.labelsize':15,
                         'xtick.labelsize':13,'ytick.labelsize':14,'legend.fontsize':12,
                         'axes.spines.top':False,'axes.spines.right':False,
                         'axes.edgecolor':'#AAB8B5','grid.color':'#DCE3E1','axes.unicode_minus':False,
                         'svg.fonttype':'none','figure.facecolor':PAPER,'axes.facecolor':PAPER})
    d=read('tree_depth');fig,ax=plt.subplots(figsize=(6.2,3.5))
    for split,c,ls in [('train',COLOR['single_tree'],'--'),('validation',TEAL,'-')]:
        a=d[d.split==split];ax.plot(range(5),a.accuracy,ls+'o',color=c,label=split,lw=2.2)
    ax.set_xticks(range(5),['1','2','3','4','不限']);ax.set_xlabel('max_depth');ax.set_ylabel('Accuracy');ax.legend(frameon=False,loc='lower right');ax.grid(axis='y',alpha=.5)
    save('depth',fig)
    roots=read('bootstrap_tree_roots').root_feature.value_counts()
    fig,ax=plt.subplots(figsize=(6.2,3.5));ax.barh(roots.index,roots,color=TEAL)
    for i,n in enumerate(roots):ax.text(n+.2,i,str(n),va='center',fontsize=15)
    ax.set_xlim(0,roots.max()+2);ax.invert_yaxis();ax.set_xlabel('30次重抽样中的根特征使用次数');ax.tick_params(axis='y',labelsize=12);ax.grid(axis='x',alpha=.4)
    save('roots',fig)
    tc=read('tree_count_curve');fig,ax=plt.subplots(figsize=(8.4,4.3))
    for n in ['bagging','random_forest','rf_all_features']:
        a=tc[tc.model==n];ax.plot(a.n_trees,a.validation_roc_auc,'o-',lw=2.2,color=COLOR[n],label=LABEL[n])
    ax.set_xscale('symlog',linthresh=1);ax.set_xticks([1,10,50,100,300],['1','10','50','100','300']);ax.set_xlabel('树数 B（压缩横轴）');ax.set_ylabel('Validation ROC-AUC');ax.legend(frameon=False,loc='lower right');ax.grid(axis='y',alpha=.5)
    save('trees',fig)
    bc=read('boosting_curves');fig,ax=plt.subplots(figsize=(8.2,4.25))
    for lr,c in zip([.03,.1,.3],['#2F8993','#D69C30','#A65A72']):
        for split,ls in [('train','--'),('validation','-')]:
            a=bc[(bc.model=='gradient_boosting')&np.isclose(bc.learning_rate,lr)&(bc.split==split)]
            ax.plot(a.stage,a.log_loss,ls,color=c,lw=2,label=f'{lr:g} / {split}')
    ax.set(xlabel='GB顺序迭代阶段',ylabel='Log-loss ↓');ax.legend(frameon=False,ncol=2,fontsize=11);ax.grid(axis='y',alpha=.5)
    save('boost',fig)
    sp=read('stability_per_sample');fig,ax=plt.subplots(figsize=(8.1,4.5))
    b=ax.boxplot([sp[sp.model==n].probability_sd.to_numpy() for n in ORDER],vert=False,patch_artist=True,showfliers=False,widths=.6)
    for n,patch in zip(ORDER,b['boxes']):patch.set_facecolor(COLOR[n]);patch.set_alpha(.65)
    ax.set_yticks(range(1,9),[LABEL[n] for n in ORDER]);ax.invert_yaxis();ax.set_xlabel('逐验证样本的30次预测概率 SD');ax.grid(axis='x',alpha=.5)
    save('stability',fig)
    dd=read('paired_differences');keep=[('random_forest','single_tree'),('random_forest','bagging'),('random_forest','logistic'),('gradient_boosting','random_forest')]
    fig,ax=plt.subplots(figsize=(8.4,4.2))
    for i,(a,b) in enumerate(keep):
        r=dd[(dd.model_a==a)&(dd.model_b==b)&(dd.metric=='roc_auc')].iloc[0]
        ax.plot([r.low,r.high],[i,i],c=COLOR[a],lw=3);ax.plot(r.point,i,'o',c=COLOR[a],ms=8)
    ax.axvline(0,color=MUTED,ls='--');ax.set_yticks(range(4),[LABEL[a]+' − '+LABEL[b] for a,b in keep]);ax.invert_yaxis()
    ax.set_xlabel('固定模型验证 AUC 差值 / 百分位95%区间');ax.grid(axis='x',alpha=.5)
    save('intervals',fig)
    imp=read('feature_importance');fig,axes=plt.subplots(1,2,figsize=(12.2,3.8))
    for ax,metric,c,title in [(axes[0],'mdi',TEAL,'训练不纯度重要性 MDI'),(axes[1],'permutation_auc_drop_mean',COLOR['logistic'],'验证置换重要性：AUC下降')]:
        a=imp.nlargest(5,metric).iloc[::-1];xerr=a.permutation_auc_drop_sd if metric!='mdi' else None
        ax.barh(a.feature,a[metric],xerr=xerr,color=c,capsize=3);ax.set_title(title,fontsize=16);ax.grid(axis='x',alpha=.5);ax.tick_params(axis='y',labelsize=13)
        ax.tick_params(axis='x',labelsize=12)
    save('importance',fig)
    print('Generated 7 projection figures in PNG/SVG/PDF.')

if __name__=='__main__':run()
