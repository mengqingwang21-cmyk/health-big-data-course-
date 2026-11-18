"""WDBC empirical study. Reads ONLY the existing student train/validation CSVs.

Run from any directory: .venv/Scripts/python scripts/run_research.py
Analysis choices are fixed in outputs/protocol.md before the first run.
"""
from __future__ import annotations
import os
for _key in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import time
import warnings
import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import AdaBoostClassifier, BaggingClassifier, GradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, balanced_accuracy_score,
                             confusion_matrix, log_loss, roc_auc_score)
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier, export_text
from threadpoolctl import threadpool_limits

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'outputs'
RES = OUT / 'results'
SEED = 1010
N_REFITS = 30
N_BOOT = 2000
NAMES = ['logistic','rbf_svm','tree_shallow','single_tree','bagging','random_forest','adaboost','gradient_boosting']
TIMES = []

def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

def csv(name, rows):
    df = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    df.to_csv(RES / (name + '.csv'), index=False, encoding='utf-8-sig')
    return df

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def stamp():
    return datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()

def model(name, seed=SEED, calibration_cv=None):
    tree = DecisionTreeClassifier(max_depth=None, max_features=None, random_state=seed)
    if name == 'logistic':
        return make_pipeline(StandardScaler(), LogisticRegression(C=1, max_iter=5000, random_state=seed))
    if name == 'rbf_svm':
        pipe = make_pipeline(StandardScaler(), SVC(C=1, kernel='rbf', gamma='scale', probability=False, random_state=seed))
        cv = calibration_cv if calibration_cv is not None else StratifiedKFold(3, shuffle=True, random_state=seed)
        return CalibratedClassifierCV(pipe, method='sigmoid', cv=cv, ensemble=False, n_jobs=1)
    if name == 'tree_shallow':
        return DecisionTreeClassifier(max_depth=2, random_state=seed)
    if name == 'single_tree':
        return tree
    if name == 'bagging':
        return BaggingClassifier(estimator=tree, n_estimators=100, max_features=1.0,
                                 max_samples=1.0, bootstrap=True, bootstrap_features=False, random_state=seed, n_jobs=1)
    if name == 'random_forest':
        return RandomForestClassifier(n_estimators=100, max_depth=None, max_features='sqrt', random_state=seed, n_jobs=1)
    if name == 'adaboost':
        return AdaBoostClassifier(estimator=DecisionTreeClassifier(max_depth=1, random_state=seed),
                                  n_estimators=50, learning_rate=1., random_state=seed)
    if name == 'gradient_boosting':
        return GradientBoostingClassifier(n_estimators=100, learning_rate=.1, max_depth=3,
                                          loss='log_loss', random_state=seed)
    raise KeyError(name)

def metrics(y, p):
    pred = (np.asarray(p) >= .5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0,1]).ravel()
    return dict(roc_auc=roc_auc_score(y, p), average_precision=average_precision_score(y, p),
                balanced_accuracy=balanced_accuracy_score(y, pred), sensitivity=tp/(tp+fn),
                specificity=tn/(tn+fp), accuracy=accuracy_score(y,pred),
                log_loss=log_loss(y,np.column_stack([1-np.asarray(p),p]),labels=[0,1]),
                tn=int(tn),fp=int(fp),fn=int(fn),tp=int(tp))

def timed_fit(m, X, y, phase, name, repeat=0):
    t = time.perf_counter()
    m.fit(X,y)
    elapsed = time.perf_counter()-t
    TIMES.append(dict(phase=phase,model=name,repeat=repeat,fit_seconds=elapsed,n_train=len(y)))
    return elapsed

def pair_corr(matrix, name, kind):
    good = np.std(matrix, axis=1) > 1e-12
    indices = np.flatnonzero(good)
    c = np.corrcoef(matrix[good])
    a,b = np.triu_indices(len(indices),1)
    frame = pd.DataFrame(dict(model=name,kind=kind,tree_i=indices[a],tree_j=indices[b],correlation=c[a,b]))
    return frame, dict(model=name,kind=kind,mean_correlation=float(np.mean(c[a,b])),
                       median_correlation=float(np.median(c[a,b])),n_pairs=len(a),
                       excluded_constant_trees=int((~good).sum()))

def run():
    RES.mkdir(parents=True,exist_ok=True)
    (OUT/'models').mkdir(exist_ok=True)
    protocol = OUT/'protocol.md'
    assert protocol.exists(), 'Write protocol before experiments.'
    started, start_time = stamp(), time.perf_counter()
    paths = [BASE/'data/student/train.csv',BASE/'data/student/validation.csv']
    train, valid = [pd.read_csv(p) for p in paths]
    features=[c for c in train if c not in {'sample_id','recording_id','malignant'}]
    assert len(features)==30 and set(train.malignant)=={0,1}
    assert not set(train.sample_id) & set(valid.sample_id)
    assert not train[features].isna().any().any() and not valid[features].isna().any().any()
    X,y,Xv,yv=train[features],train.malignant,valid[features],valid.malignant
    dev=pd.concat([train,valid],ignore_index=True)
    Xd,yd=dev[features],dev.malignant
    info=dict(started_at=started,seed=SEED,bootstrap_sim_seed=1011,training_bootstrap_seed=1012,
              paired_bootstrap_seed=1013,permutation_seed=1014,n_refits=N_REFITS,n_paired_bootstrap=N_BOOT,
              python=sys.version,platform=platform.platform(),processor=platform.processor(),
              threads=1,read_files=[str(p.relative_to(BASE)) for p in paths],
              data_sha256={str(p.relative_to(BASE)):sha(p) for p in paths},protocol_sha256=sha(protocol),
              features=features,label='malignant=1',classification_threshold=.5,
              test_status='锁定测试集尚未评价',teacher_files_read=False,
              versions={p:importlib.metadata.version(p) for p in
                        ['numpy','pandas','scipy','scikit-learn','matplotlib','python-pptx','Pillow','joblib']},
              parameters={n:model(n).get_params(deep=True) for n in NAMES})
    write_json(RES/'run_info.json',info)
    (RES/'pip_freeze.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True),encoding='utf-8')
    csv('dataset_audit',[dict(split=n,n=len(d),negative=int((d.malignant==0).sum()),positive=int(d.malignant.sum()),
                               prevalence=float(d.malignant.mean()),missing_cells=int(d[features].isna().sum().sum()),
                               duplicate_feature_rows=int(d[features].duplicated().sum()))
                         for n,d in [('train',train),('validation',valid),('development',dev)]] )
    print('Protocol locked; loaded student train/validation only.',flush=True)
    folds=list(StratifiedKFold(5,shuffle=True,random_state=SEED).split(Xd,yd))
    assignments=[]
    for fold,(_,te) in enumerate(folds,1):
        assignments.extend(dict(sample_id=dev.iloc[i].sample_id,development_row=int(i),fold=fold,
                                original_split='train' if i<len(train) else 'validation') for i in te)
    csv('cv_assignments',assignments)
    cv_rows, pred_rows=[],[]
    for name in NAMES:
        for fold,(tr,te) in enumerate(folds,1):
            m=model(name)
            seconds=timed_fit(m,Xd.iloc[tr],yd.iloc[tr],'development_cv',name,fold)
            p=m.predict_proba(Xd.iloc[te])[:,1]
            cv_rows.append(dict(model=name,fold=fold,n_train=len(tr),n_eval=len(te),fit_seconds=seconds,**metrics(yd.iloc[te],p)))
            pred_rows.extend(dict(model=name,fold=fold,sample_id=dev.iloc[i].sample_id,y=int(yd.iloc[i]),probability=float(prob),predicted=int(prob>=.5)) for i,prob in zip(te,p))
        print('CV:',name,flush=True)
    cv=csv('cv_per_fold',cv_rows)
    csv('cv_oof_predictions',pred_rows)
    measures=['roc_auc','average_precision','balanced_accuracy','sensitivity','specificity','log_loss','fit_seconds']
    summary=cv.groupby('model',sort=False)[measures].agg(['mean','std'])
    summary.columns=[f'{a}_{"sd" if b=="std" else b}' for a,b in summary.columns]
    csv('cv_summary',summary.reset_index())
    fitted={}; rows=[]; predictions=[]
    for name in NAMES:
        m=model(name)
        seconds=timed_fit(m,X,y,'fixed_validation',name)
        t=time.perf_counter(); p=m.predict_proba(Xv)[:,1]; predict_seconds=time.perf_counter()-t
        row=dict(model=name,fit_seconds=seconds,predict_seconds=predict_seconds,**metrics(yv,p))
        if hasattr(m,'estimators_'):
            ts=np.asarray(m.estimators_,dtype=object).ravel()
            row['tree_count']=len(ts); row['total_nodes']=sum(t.tree_.node_count for t in ts if hasattr(t,'tree_'))
        elif hasattr(m,'tree_'):
            row['tree_count']=1; row['total_nodes']=m.tree_.node_count
        rows.append(row)
        predictions.extend(dict(model=name,sample_id=s,y=int(target),probability=float(prob),predicted=int(prob>=.5))
                           for s,target,prob in zip(valid.sample_id,yv,p))
        fitted[name]=m
        joblib.dump(m,OUT/'models'/f'{name}.joblib',compress=3)
    csv('validation_metrics',rows); csv('validation_predictions',predictions)
    print('Fixed validation finished.',flush=True)

    # A: depth and shared training bootstrap roots.
    depth_rows=[]
    for depth in [1,2,3,4,None]:
        m=DecisionTreeClassifier(max_depth=depth,random_state=SEED).fit(X,y)
        for split,xx,yy in [('train',X,y),('validation',Xv,yv)]:
            depth_rows.append(dict(max_depth='unlimited' if depth is None else str(depth),split=split,
                                   leaves=m.get_n_leaves(),nodes=m.tree_.node_count,**metrics(yy,m.predict_proba(xx)[:,1])))
    csv('tree_depth',depth_rows)
    (RES/'example_tree_depth2.txt').write_text(export_text(fitted['tree_shallow'],feature_names=features,decimals=5,show_weights=True),encoding='utf-8')
    tree=fitted['tree_shallow'].tree_
    csv('example_tree_nodes',[dict(node=i,feature=features[tree.feature[i]] if tree.feature[i]>=0 else 'leaf',
                                    threshold=float(tree.threshold[i]),left=int(tree.children_left[i]),right=int(tree.children_right[i]),
                                    n=int(tree.n_node_samples[i]),p_malignant=float(tree.value[i,0,1]/tree.value[i,0].sum())) for i in range(tree.node_count)])
    rng=np.random.default_rng(1012)
    samples=np.asarray([rng.choice(len(y),size=len(y),replace=True) for _ in range(N_REFITS)])
    np.savez_compressed(RES/'training_bootstrap_indices.npz',indices=samples,sample_ids=train.sample_id.to_numpy())
    roots=[]
    for r,idx in enumerate(samples):
        m=DecisionTreeClassifier(max_depth=2,random_state=SEED).fit(X.iloc[idx],y.iloc[idx])
        roots.append(dict(repeat=r,root_feature=features[m.tree_.feature[0]],root_threshold=m.tree_.threshold[0],
                          n_unique=len(np.unique(idx)),validation_roc_auc=roc_auc_score(yv,m.predict_proba(Xv)[:,1])))
    csv('bootstrap_tree_roots',roots)
    # C: exact finite n expectations and Monte Carlo distributions.
    rng=np.random.default_rng(1011); simulations=[]
    for n in [5,len(y)]:
        for r in range(N_BOOT):
            unique=len(np.unique(rng.integers(0,n,n)))/n
            simulations.append(dict(n=n,repeat=r,unique_fraction=unique,oob_fraction=1-unique,
                                     expected_unique=1-(1-1/n)**n,expected_oob=(1-1/n)**n))
    csv('bootstrap_sampling',simulations)

    # D: full-feature RF implementation control isolates node feature randomization.
    curves=[]; pair_frames=[]; correlations=[]; rf_controls={}
    for name in ['bagging','random_forest','rf_all_features']:
        for count in [1,10,50,100,300]:
            m=model('bagging' if name=='bagging' else 'random_forest')
            m.set_params(n_estimators=count,oob_score=count>=50)
            if name=='rf_all_features': m.set_params(max_features=1.0)
            seconds=timed_fit(m,X,y,'tree_count',name,count)
            p=m.predict_proba(Xv)[:,1]
            row=dict(model=name,n_trees=count,fit_seconds=seconds,validation_roc_auc=roc_auc_score(yv,p),
                     validation_balanced_accuracy=balanced_accuracy_score(yv,p>=.5),
                     training_roc_auc=roc_auc_score(y,m.predict_proba(X)[:,1]),oob_accuracy=np.nan,oob_roc_auc=np.nan)
            if count>=50:
                oob=m.oob_decision_function_[:,1]
                row.update(oob_accuracy=m.oob_score_,oob_roc_auc=roc_auc_score(y,oob))
            curves.append(row)
            if count==100:
                if name!='bagging': rf_controls[name]=m
                matrix=np.asarray([t.predict_proba(Xv.to_numpy())[:,1] for t in m.estimators_])
                for kind,values in [('probability',matrix),('residual',matrix-yv.to_numpy()[None,:]),
                                     ('binary_error',(matrix>=.5)!=yv.to_numpy()[None,:])]:
                    frame,summary=pair_corr(values.astype(float),name,kind)
                    pair_frames.append(frame);correlations.append(summary)
    csv('tree_count_curve',curves)
    csv('tree_pair_correlations',pd.concat(pair_frames,ignore_index=True))
    csv('tree_correlation_summary',correlations)
    info['rf_control_bootstrap_indices_identical']=all(np.array_equal(a,b) for a,b in zip(
        rf_controls['random_forest'].estimators_samples_,rf_controls['rf_all_features'].estimators_samples_))
    print('Depth, sampling and tree-count mechanisms finished.',flush=True)

    # E: explorations do NOT change main model settings.
    boost_rows=[]
    for name in ['adaboost','gradient_boosting']:
        for lr in [.03,.1,.3]:
            m=model(name).set_params(learning_rate=lr,n_estimators=200)
            timed_fit(m,X,y,'boosting_exploration',name,lr)
            for stage,(pt,pv) in enumerate(zip(m.staged_predict_proba(X),m.staged_predict_proba(Xv)),1):
                for split,yy,pp in [('train',y,pt[:,1]),('validation',yv,pv[:,1])]:
                    boost_rows.append(dict(model=name,learning_rate=lr,stage=stage,split=split,
                                           roc_auc=roc_auc_score(yy,pp),log_loss=log_loss(yy,np.column_stack([1-pp,pp]),labels=[0,1])))
    csv('boosting_curves',boost_rows)
    ada=fitted['adaboost']; w=np.ones(len(y))/len(y); weight_rows=[]; rounds=[]
    for stage,(tree,alpha) in enumerate(zip(ada.estimators_[:8],ada.estimator_weights_[:8]),1):
        wrong=tree.predict(X.to_numpy())!=y.to_numpy()
        error=float(np.dot(w,wrong)); assert np.isclose(error,ada.estimator_errors_[stage-1],atol=1e-8)
        wn=w*np.exp(alpha*wrong);wn=wn/wn.sum()
        rounds.append(dict(stage=stage,weighted_error=error,estimator_weight=alpha,
                           unnormalized_wrong_multiplier=float(np.exp(alpha)),misclassified=int(wrong.sum())))
        weight_rows.extend(dict(stage=stage,sample_id=s,y=int(yy),wrong=int(er),weight_before=float(a),weight_after=float(b))
                           for s,yy,er,a,b in zip(train.sample_id,y,wrong,w,wn))
        w=wn
    csv('adaboost_weight_rounds',rounds);csv('adaboost_sample_weights',weight_rows)
    gb=fitted['gradient_boosting']; p=np.repeat(y.mean(),len(y)); grad=[]
    raw=np.repeat(np.log(y.mean()/(1-y.mean())),len(y))
    selected=np.argsort(train.sample_id.to_numpy())[:6]
    for stage,t in enumerate(gb.estimators_[:5,0],1):
        update=gb.learning_rate*t.predict(X.to_numpy())
        grad.extend(dict(stage=stage,sample_id=train.iloc[i].sample_id,y=int(y.iloc[i]),p_before=float(p[i]),
                         negative_gradient=float(y.iloc[i]-p[i]),log_odds_update=float(update[i])) for i in selected)
        raw+=update;p=1/(1+np.exp(-raw))
    csv('gradient_directions',grad)

    # G1: same training perturbations; SVM calibration keeps duplicate original IDs together.
    stability=[]; individual=[]; all_preds=[]
    for name in NAMES:
        probabilities=[]
        for r,idx in enumerate(samples):
            cal=None
            if name=='rbf_svm':
                splitter=StratifiedGroupKFold(3,shuffle=True,random_state=SEED)
                cal=list(splitter.split(X.iloc[idx],y.iloc[idx],groups=idx))
                assert all(not set(idx[a]) & set(idx[b]) for a,b in cal)
            m=model(name,calibration_cv=cal)
            timed_fit(m,X.iloc[idx],y.iloc[idx],'training_bootstrap',name,r)
            p=m.predict_proba(Xv)[:,1];probabilities.append(p)
            all_preds.extend(dict(model=name,repeat=r,sample_id=s,y=int(yy),probability=float(pp),predicted=int(pp>=.5))
                             for s,yy,pp in zip(valid.sample_id,yv,p))
        probabilities=np.asarray(probabilities); cl=probabilities>=.5
        q=cl.mean(axis=0); sd=probabilities.std(axis=0,ddof=1)
        flip=(q>0)&(q<1); pair=2*(cl.sum(axis=0))*(N_REFITS-cl.sum(axis=0))/(N_REFITS*(N_REFITS-1))
        stability.append(dict(model=name,n_refits=N_REFITS,mean_probability_sd=sd.mean(),median_probability_sd=np.median(sd),
                               max_probability_sd=sd.max(),any_flip_fraction=flip.mean(),n_any_flip=int(flip.sum()),
                               mean_pair_disagreement=pair.mean(),mean_modal_disagreement=np.minimum(q,1-q).mean()))
        individual.extend(dict(model=name,sample_id=s,y=int(yy),probability_sd=float(d),positive_fraction=float(qq),
                               any_flip=int(f),pair_disagreement=float(p)) for s,yy,d,qq,f,p in zip(valid.sample_id,yv,sd,q,flip,pair))
        print('Training bootstrap:',name,flush=True)
    csv('stability_summary',stability);csv('stability_per_sample',individual);csv('stability_predictions',all_preds)
    algorithm_rows=[]
    for name in ['single_tree','bagging','random_forest']:
        probs=[]
        for seed in range(SEED,SEED+10):
            m=model(name,seed=seed);timed_fit(m,X,y,'algorithm_seed',name,seed);probs.append(m.predict_proba(Xv)[:,1])
        probs=np.asarray(probs);q=(probs>=.5).mean(axis=0)
        algorithm_rows.append(dict(model=name,n_seeds=10,mean_probability_sd=probs.std(axis=0,ddof=1).mean(),
                                   any_flip_fraction=((q>0)&(q<1)).mean()))
    csv('algorithm_seed_stability',algorithm_rows)

    # G2: fixed fitted models; stratified shared validation indices. No model refits here.
    rng=np.random.default_rng(1013); strata=[np.flatnonzero(yv.to_numpy()==k) for k in [0,1]]
    ids=np.asarray([np.concatenate([rng.choice(a,len(a),replace=True) for a in strata]) for _ in range(N_BOOT)])
    np.savez_compressed(RES/'paired_validation_bootstrap_indices.npz',indices=ids,sample_ids=valid.sample_id.to_numpy())
    fixed={n:fitted[n].predict_proba(Xv)[:,1] for n in NAMES};boot=[]
    for r,idx in enumerate(ids):
        yy=yv.to_numpy()[idx]
        for name in NAMES:
            pp=fixed[name][idx]
            boot.append(dict(repeat=r,model=name,roc_auc=roc_auc_score(yy,pp),
                             average_precision=average_precision_score(yy,pp),balanced_accuracy=balanced_accuracy_score(yy,pp>=.5)))
    boot=csv('paired_bootstrap_metrics',boot)
    intervals=[]
    for name,g in boot.groupby('model',sort=False):
        for metric in ['roc_auc','average_precision','balanced_accuracy']:
            lo,hi=np.quantile(g[metric],[.025,.975])
            intervals.append(dict(model=name,metric=metric,point=metrics(yv,fixed[name])[metric],low=lo,high=hi))
    csv('fixed_model_intervals',intervals)
    pairs=[('random_forest','single_tree'),('bagging','single_tree'),('random_forest','bagging'),
           ('random_forest','logistic'),('random_forest','rbf_svm'),('gradient_boosting','logistic'),('gradient_boosting','random_forest')]
    diff_rows=[];diff_raw=[]
    for a,b in pairs:
        for metric in ['roc_auc','average_precision','balanced_accuracy']:
            pivot=boot.pivot(index='repeat',columns='model',values=metric)
            delta=pivot[a]-pivot[b];lo,hi=np.quantile(delta,[.025,.975])
            diff_rows.append(dict(model_a=a,model_b=b,metric=metric,point=metrics(yv,fixed[a])[metric]-metrics(yv,fixed[b])[metric],low=lo,high=hi))
            diff_raw.extend(dict(repeat=int(i),model_a=a,model_b=b,metric=metric,difference=float(v)) for i,v in delta.items())
    csv('paired_differences',diff_rows);csv('paired_differences_resamples',diff_raw)
    print('Paired conditional intervals finished.',flush=True)

    # H: same main RF100, unpermuted train correlation and validation AUC permutation.
    forest=fitted['random_forest']
    perm=permutation_importance(forest,Xv,yv,scoring='roc_auc',n_repeats=20,random_state=1014,n_jobs=1)
    csv('feature_importance',pd.DataFrame(dict(feature=features,mdi=forest.feature_importances_,
        permutation_auc_drop_mean=perm.importances_mean,permutation_auc_drop_sd=perm.importances_std)))
    csv('permutation_repeats',[dict(feature=f,repeat=r,auc_drop=float(v)) for f,arr in zip(features,perm.importances) for r,v in enumerate(arr)])
    corr=X.corr();corr.to_csv(RES/'feature_correlation.csv',encoding='utf-8-sig')
    pairs_corr=[dict(feature_a=features[i],feature_b=features[j],pearson_r=corr.iloc[i,j])
                for i in range(len(features)) for j in range(i+1,len(features))]
    csv('correlated_feature_pairs',sorted(pairs_corr,key=lambda x:-abs(x['pearson_r'])))
    groups={'worst_size':['worst radius','worst perimeter','worst area'],
            'mean_and_worst_size':['mean radius','mean perimeter','mean area','worst radius','worst perimeter','worst area']}
    rng=np.random.default_rng(1014);group_rows=[];baseline=roc_auc_score(yv,fixed['random_forest'])
    for group,cols in groups.items():
        for r in range(20):
            shuffled=Xv.copy();idx=rng.permutation(len(yv));shuffled.loc[:,cols]=Xv[cols].to_numpy()[idx]
            group_rows.append(dict(group=group,features=';'.join(cols),repeat=r,
                                   auc_drop=baseline-roc_auc_score(yv,forest.predict_proba(shuffled)[:,1])))
    csv('grouped_permutation',group_rows)
    csv('fit_times',TIMES)
    info.update(finished_at=stamp(),total_wall_seconds=time.perf_counter()-start_time,
                code_sha256={p.name:sha(p) for p in [Path(__file__),BASE/'scripts/demo_ensemble.py']})
    write_json(RES/'run_info.json',info)
    print('COMPLETE',round(info['total_wall_seconds'],1),'seconds; output:',OUT,flush=True)

if __name__=='__main__':
    with threadpool_limits(limits=1):
        run()
