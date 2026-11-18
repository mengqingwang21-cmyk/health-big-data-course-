"""Figures composed and sized for the A4 manuscript, independent of slide graphics."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from research_style import *

def save(name,fig):
    fig.tight_layout(pad=1.1)
    for ext in ['png','svg','pdf']:fig.savefig(FIG/f'{name}.{ext}',dpi=260,bbox_inches='tight',facecolor='white')
    plt.close(fig)

def run():
    plt.rcParams.update({'font.family':'Microsoft YaHei','font.size':13,'axes.labelsize':13,'axes.titlesize':14,
        'xtick.labelsize':11,'ytick.labelsize':12,'legend.fontsize':11,'axes.spines.top':False,
        'axes.spines.right':False,'axes.edgecolor':'#AAB8B5','grid.color':'#DCE3E1',
        'svg.fonttype':'none','axes.unicode_minus':False,'figure.facecolor':'white','axes.facecolor':'white'})
    cv=read('cv_summary').set_index('model').loc[ORDER]
    fig,ax=plt.subplots(figsize=(8.2,5.2));lo,hi=.88,1.008
    for i,n in enumerate(ORDER):
        ax.errorbar(cv.loc[n,'roc_auc_mean'],i,xerr=cv.loc[n,'roc_auc_sd'],fmt='o',color=COLOR[n],capsize=4,ms=6)
    ax.set_yticks(range(8),[LABEL[n] for n in ORDER]);ax.invert_yaxis();ax.set_xlim(lo,hi)
    ax.set_xlabel('Development-set five-fold ROC-AUC: mean ± fold SD');ax.grid(axis='x',alpha=.55)
    save('paper_performance',fig)

    imp=read('feature_importance')
    fig,axes=plt.subplots(2,1,figsize=(7.1,7.0))
    for ax,metric,title,c in [(axes[0],'mdi','Train: impurity importance (MDI)',TEAL),
                              (axes[1],'permutation_auc_drop_mean','Validation: permutation AUC drop',COLOR['logistic'])]:
        a=imp.nlargest(7,metric).iloc[::-1]
        err=None if metric=='mdi' else a.permutation_auc_drop_sd
        ax.barh(a.feature,a[metric],xerr=err,capsize=3,color=c,alpha=.9)
        ax.set_title(title);ax.tick_params(axis='y',labelsize=11);ax.tick_params(axis='x',labelsize=10);ax.grid(axis='x',alpha=.45)
        if metric=='mdi':ax.set_xlabel('Normalized MDI')
        else:ax.set_xlabel('Mean AUC decrease ± permutation SD (20 repeats)')
    save('paper_importance',fig)

    corr=pd.read_csv(RES/'feature_correlation.csv',index_col=0)
    cols=['mean radius','mean perimeter','mean area','worst radius','worst perimeter','worst area']
    names=['mean radius','mean perimeter','mean area','worst radius','worst perimeter','worst area']
    fig,ax=plt.subplots(figsize=(5.8,4.9));a=corr.loc[cols,cols]
    im=ax.imshow(a,vmin=0,vmax=1,cmap='YlGnBu')
    ax.set_xticks(range(6),names,rotation=48,ha='right');ax.set_yticks(range(6),names)
    for i in range(6):
        for j in range(6):ax.text(j,i,f'{a.iloc[i,j]:.2f}',ha='center',va='center',fontsize=10,
                                  color='white' if a.iloc[i,j]>.72 else INK)
    ax.set_title('Pearson correlation in train');fig.colorbar(im,ax=ax,shrink=.82,label='r')
    save('paper_correlation',fig)
    print('Generated 3 figures sized for the A4 paper.')

if __name__=='__main__':run()
