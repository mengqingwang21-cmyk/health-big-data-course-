from pathlib import Path
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
OUT=BASE/'outputs'
RES=OUT/'results'
FIG=OUT/'figures'
ORDER=['logistic','rbf_svm','tree_shallow','single_tree','bagging','random_forest','adaboost','gradient_boosting']
LABEL={'logistic':'LR','rbf_svm':'RBF-SVM','tree_shallow':'Tree (depth 2)','single_tree':'Tree (full)',
       'bagging':'Bagging','random_forest':'RF (sqrt)','adaboost':'AdaBoost','gradient_boosting':'Gradient Boosting',
       'rf_all_features':'RF (all features)'}
COLOR={'logistic':'#2762A0','rbf_svm':'#7452A3','tree_shallow':'#B99B7B','single_tree':'#B85C3B',
       'bagging':'#D29B2C','random_forest':'#16887F','adaboost':'#CB6689','gradient_boosting':'#354E6B',
       'rf_all_features':'#7F9295'}
INK='#193638'
TEAL='#087C77'
MUTED='#52686A'
PAPER='#FAFBF8'

def read(name):
    return pd.read_csv(RES/f'{name}.csv')

def md_table(df, digits=4):
    def fmt(x):
        if isinstance(x,float): return f'{x:.{digits}f}'
        return str(x)
    lines=['| '+' | '.join(map(str,df.columns))+' |','| '+' | '.join(['---']*len(df.columns))+' |']
    lines.extend('| '+' | '.join(fmt(x) for x in row)+' |' for row in df.itertuples(index=False,name=None))
    return '\n'.join(lines)
