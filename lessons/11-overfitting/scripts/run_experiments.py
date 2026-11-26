"""第 11 讲实验：欠拟合与过拟合的识别。

在本课目录运行：
    python scripts/run_experiments.py                  # 运行全部实验
    python scripts/run_experiments.py --experiment E4  # 只运行一个实验
    python scripts/run_experiments.py --prepare        # 重新生成 data/ 下的输入文件（一般不需要）

结果 CSV 写到本课目录 .tmp/lesson11/。每个实验对应一个同名小写函数（E1 -> e1()）。
想改实验条件时，优先修改下面“可修改的实验条件”，其余条件保持不变再比较。
"""
from pathlib import Path
import argparse
import json
import platform

import numpy as np
import pandas as pd
import sklearn
from sklearn.datasets import load_breast_cancer
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit, StratifiedKFold, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

BASE = Path(__file__).resolve().parents[1]   # 本课目录
DATA = BASE / 'data'
SEED = 1111

# ---- 可修改的实验条件 ----
DEPTHS = [1, 2, 3, 5, 10, None]       # E1：决策树深度，None 表示不限深度
TRAIN_SIZES = [40, 100, 200, 398]     # E1：训练样本量，398 = 全部训练记录
N_NOISE = 300                         # E1：加入的无关（纯噪声）特征数
K_SELECT = 20                         # E4：特征筛选保留的特征数
BUDGETS = [1, 5, 20, 100, 200]        # E6：从多少个候选模型里挑最高分


def save(rows, name, out):
    df = pd.DataFrame(rows)
    df.to_csv(out / f'{name}.csv', index=False)
    return df


def prepare():
    """生成课程输入数据。WDBC 来自 sklearn；其余为模拟数据，标签与特征无关。"""
    DATA.mkdir(exist_ok=True)
    raw = load_breast_cancer()
    df = pd.DataFrame(raw.data, columns=[s.replace(' ', '_') for s in raw.feature_names])
    df.insert(0, 'sample_id', [f'W{i:04d}' for i in range(len(df))])
    df['malignant'] = (raw.target == 0).astype(int)          # sklearn 原标签 0=恶性，这里改为 1=恶性
    train, validation = train_test_split(np.arange(len(df)), test_size=0.30,
                                         stratify=df['malignant'], random_state=SEED)
    df['split'] = np.where(df.index.isin(train), 'train', 'validation')
    df.to_csv(DATA / 'wdbc.csv', index=False)

    rng = np.random.default_rng(SEED)
    # null-omics：180 条记录 × 1000 个纯噪声“基因”，标签随机
    null = pd.DataFrame(rng.normal(size=(180, 1000)), columns=[f'gene_{i:04d}' for i in range(1000)])
    null.insert(0, 'sample_id', [f'N{i:04d}' for i in range(180)])
    null['y'] = rng.permutation(np.tile([0, 1], 90))
    null.to_csv(DATA / 'null-omics.csv', index=False)

    # repeated-patients：100 位患者各 4 条记录。同一患者的 4 条记录几乎相同（“身份指纹”），
    # 标签按患者随机赋值，所以特征里没有任何可推广到新患者的信号。
    fingerprints = rng.normal(size=(100, 40))
    y = rng.permutation(np.tile([0, 1], 50))
    patients = pd.DataFrame(np.repeat(fingerprints, 4, axis=0) + rng.normal(0, 0.01, (400, 40)),
                            columns=[f'marker_{i:02d}' for i in range(40)])
    patients.insert(0, 'patient_id', np.repeat([f'P{i:03d}' for i in range(100)], 4))
    patients['visit'] = np.tile(np.arange(4), 100)
    patients['y'] = np.repeat(y, 4)
    patients.to_csv(DATA / 'repeated-patients.csv', index=False)

    manifest = {'seed': SEED, 'python': platform.python_version(), 'sklearn': sklearn.__version__,
                'wdbc_rows': len(df), 'train': len(train), 'validation': len(validation),
                'simulations': 'null-omics and repeated-patients have random labels; teaching use only.'}
    (DATA / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')


def load_wdbc():
    """返回 X_train, X_val, y_train, y_val（固定的 70/30 分层划分）。"""
    df = pd.read_csv(DATA / 'wdbc.csv')
    features = [c for c in df.columns if c not in ['sample_id', 'malignant', 'split']]
    is_train = df['split'].eq('train').to_numpy()
    X, y = df[features].to_numpy(), df['malignant'].to_numpy()
    return X[is_train], X[~is_train], y[is_train], y[~is_train]


def proba(model, X):
    return model.predict_proba(X)[:, 1]


def e1(out):
    """E1 复杂度、样本量与无关特征。"""
    X_tr, X_val, y_tr, y_val = load_wdbc()

    # A：只改变决策树深度，看训练/验证表现怎样随复杂度变化
    rows = []
    for depth in DEPTHS:
        tree = DecisionTreeClassifier(max_depth=depth, random_state=SEED).fit(X_tr, y_tr)
        rows.append(dict(depth='unlimited' if depth is None else str(depth),
                         train_auc=roc_auc_score(y_tr, proba(tree, X_tr)),
                         validation_auc=roc_auc_score(y_val, proba(tree, X_val)),
                         train_accuracy=accuracy_score(y_tr, tree.predict(X_tr)),
                         validation_accuracy=accuracy_score(y_val, tree.predict(X_val))))
    save(rows, 'E1-complexity', out)

    # B：逻辑回归，改变训练样本量，并比较“原始 30 个特征”与“再加 N_NOISE 个纯噪声特征”
    rows = []
    for repeat in range(10):
        rng = np.random.default_rng(SEED + repeat)
        order = rng.permutation(len(X_tr))                      # 每轮随机抽取不同的训练子集
        noise_tr = rng.normal(size=(len(X_tr), N_NOISE))
        noise_val = rng.normal(size=(len(X_val), N_NOISE))
        for n in TRAIN_SIZES:
            idx = order[:n]
            for n_noise in [0, N_NOISE]:
                A = np.column_stack([X_tr, noise_tr[:, :n_noise]])[idx]
                B = np.column_stack([X_val, noise_val[:, :n_noise]])
                model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=5000))
                model.fit(A, y_tr[idx])
                rows.append(dict(repeat=repeat, n=n, noise_features=n_noise,
                                 train_auc=roc_auc_score(y_tr[idx], proba(model, A)),
                                 validation_auc=roc_auc_score(y_val, proba(model, B))))
    save(rows, 'E1-sample-features', out)


def e2(out):
    """E2 交叉验证的折间波动，以及删除单条训练记录对预测的影响。"""
    X_tr, X_val, y_tr, y_val = load_wdbc()

    # A：只在训练部分做 5 次重复的五折 CV，树与逻辑回归使用相同的折
    rows = []
    for repeat in range(5):
        cv = StratifiedKFold(5, shuffle=True, random_state=SEED + repeat)
        for fold, (a, b) in enumerate(cv.split(X_tr, y_tr)):
            models = [('tree', DecisionTreeClassifier(random_state=SEED)),
                      ('logistic', make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)))]
            for name, model in models:
                model.fit(X_tr[a], y_tr[a])
                rows.append(dict(repeat=repeat, fold=fold, model=name,
                                 auc=roc_auc_score(y_tr[b], proba(model, X_tr[b]))))
    save(rows, 'E2-cv', out)

    # B：每次删掉一条训练记录，重训同一棵不限深度的树，看验证集预测变了多少
    reference = proba(DecisionTreeClassifier(random_state=SEED).fit(X_tr, y_tr), X_val)
    rows = []
    for i in range(len(X_tr)):
        keep = np.arange(len(X_tr)) != i
        p = proba(DecisionTreeClassifier(random_state=SEED).fit(X_tr[keep], y_tr[keep]), X_val)
        rows.append(dict(removed_train_index=i,
                         mean_absolute_probability_change=np.abs(p - reference).mean(),
                         validation_auc=roc_auc_score(y_val, p),
                         baseline_auc=roc_auc_score(y_val, reference)))
    save(rows, 'E2-case-deletion', out)


def e3(out):
    """E3 标准化（StandardScaler）在哪些记录上 fit。"""
    X_tr, X_val, y_tr, y_val = load_wdbc()
    X_all = np.vstack([X_tr, X_val])
    rows = []
    for scope in ['all_X_leaky', 'training_only']:
        # 错误做法：scaler 看到了验证集的特征（虽然没看到验证集标签）
        scaler = StandardScaler().fit(X_all if scope == 'all_X_leaky' else X_tr)
        model = LogisticRegression(C=0.1, max_iter=2000).fit(scaler.transform(X_tr), y_tr)
        rows.append(dict(scaler_fit=scope,
                         auc=roc_auc_score(y_val, proba(model, scaler.transform(X_val))),
                         first_feature_mean=scaler.mean_[0],
                         n_seen=int(scaler.n_samples_seen_)))
    save(rows, 'E3-scaling', out)


def e4(out):
    """E4 特征筛选放在 CV 之前还是每个训练折之内（数据无信号）。"""
    df = pd.read_csv(DATA / 'null-omics.csv')
    X = df.filter(like='gene_').to_numpy()
    rows = []
    for repeat in range(20):
        rng = np.random.default_rng(SEED + repeat)
        y = rng.permutation(df['y'].to_numpy())   # 每轮一组新的随机标签，与 X 无关
        cv = StratifiedKFold(5, shuffle=True, random_state=SEED + repeat)
        # 错误流程：先用全部记录（包括之后的验证折）的标签挑出 K_SELECT 个特征
        X_selected = SelectKBest(f_classif, k=K_SELECT).fit_transform(X, y)
        for fold, (a, b) in enumerate(cv.split(X, y)):
            for method in ['global_selection_leaky', 'fold_pipeline']:
                if method == 'global_selection_leaky':
                    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
                    data = X_selected
                else:
                    # 正确流程：筛选、标准化、模型都放进 Pipeline，每个训练折内重新 fit
                    model = make_pipeline(SelectKBest(f_classif, k=K_SELECT), StandardScaler(),
                                          LogisticRegression(max_iter=2000))
                    data = X
                model.fit(data[a], y[a])
                rows.append(dict(repeat=repeat, fold=fold, method=method,
                                 auc=roc_auc_score(y[b], proba(model, data[b]))))
    save(rows, 'E4-feature-selection', out)


def e5(out):
    """E5 按行随机划分 vs 按患者分组划分（同一患者的记录几乎相同）。"""
    df = pd.read_csv(DATA / 'repeated-patients.csv')
    X = df.filter(like='marker_').to_numpy()   # patient_id、visit 不进入模型
    y = df['y'].to_numpy()
    groups = df['patient_id'].to_numpy()
    rows = []
    for repeat in range(10):
        for method in ['row_split_leaky', 'group_split']:
            if method == 'row_split_leaky':
                a, b = train_test_split(np.arange(len(df)), test_size=0.3, stratify=y,
                                        random_state=SEED + repeat)
            else:
                splitter = GroupShuffleSplit(n_splits=1, test_size=0.3, random_state=SEED + repeat)
                a, b = next(splitter.split(X, y, groups))
            model = KNeighborsClassifier(n_neighbors=1).fit(X[a], y[a])
            rows.append(dict(repeat=repeat, method=method,
                             overlap_patients=len(set(groups[a]) & set(groups[b])),
                             auc=roc_auc_score(y[b], proba(model, X[b]))))
    save(rows, 'E5-patient-split', out)


def e6(out):
    """E6 反复用同一份留出集挑最高分。候选“模型”是与标签无关的随机预测分数。"""
    rows = []
    for repeat in range(100):
        rng = np.random.default_rng(SEED + repeat)
        y_holdout = rng.permutation(np.tile([0, 1], 40))      # 被反复查看的留出集：80 条
        y_fresh = rng.permutation(np.tile([0, 1], 200))       # 从未用于挑选的新数据：400 条
        holdout_scores = rng.normal(size=(200, len(y_holdout)))
        fresh_scores = rng.normal(size=(200, len(y_fresh)))
        holdout_auc = np.array([roc_auc_score(y_holdout, s) for s in holdout_scores])
        for budget in BUDGETS:
            winner = int(np.argmax(holdout_auc[:budget]))        # 在前 budget 个候选里挑留出集最高者
            rows.append(dict(repeat=repeat, candidates=budget, selected=winner,
                             reused_holdout_auc=holdout_auc[winner],
                             fresh_audit_auc=roc_auc_score(y_fresh, fresh_scores[winner])))
    save(rows, 'E6-repeated-selection', out)


def e7(out):
    """E7 模拟新中心：一个真实疾病指标 + 一个只在原中心与标签相关的“中心代理”指标。"""
    rng = np.random.default_rng(SEED)

    def cohort(n, flip=False):
        y = rng.integers(0, 2, n)
        disease_marker = y + rng.normal(0, 1.2, n)                # 与疾病有关，但噪声较大
        site_marker = (1 - y if flip else y) + rng.normal(0, 0.2, n)  # flip=True：新中心关系反转
        return np.column_stack([disease_marker, site_marker]), y

    X_train, y_train = cohort(400)
    X_internal, y_internal = cohort(200)
    X_new_site, y_new_site = cohort(200, flip=True)
    rows = []
    for name, cols in [('both_markers', [0, 1]), ('biological_only', [0])]:
        model = make_pipeline(StandardScaler(), LogisticRegression()).fit(X_train[:, cols], y_train)
        for cohort_name, X, y in [('internal', X_internal, y_internal),
                                  ('shifted_simulated_site', X_new_site, y_new_site)]:
            rows.append(dict(model=name, cohort=cohort_name, auc=roc_auc_score(y, proba(model, X[:, cols]))))
    save(rows, 'E7-domain-shift', out)


def summarize(out):
    summary = {}
    specs = [('E1-complexity', ['depth'], ['train_auc', 'validation_auc']),
             ('E1-sample-features', ['n', 'noise_features'], ['train_auc', 'validation_auc']),
             ('E2-cv', ['model'], ['auc']),
             ('E3-scaling', ['scaler_fit'], ['auc']),
             ('E4-feature-selection', ['method'], ['auc']),
             ('E5-patient-split', ['method'], ['auc', 'overlap_patients']),
             ('E6-repeated-selection', ['candidates'], ['reused_holdout_auc', 'fresh_audit_auc']),
             ('E7-domain-shift', ['model', 'cohort'], ['auc'])]
    for name, groups, values in specs:
        df = pd.read_csv(out / f'{name}.csv')
        summary[name] = df.groupby(groups, dropna=False)[values].mean().reset_index().to_dict('records')
    deletion = pd.read_csv(out / 'E2-case-deletion.csv')
    summary['E2-case-deletion'] = (deletion.sort_values('mean_absolute_probability_change', ascending=False)
                                   .head(5).to_dict('records'))
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--experiment', choices=['all', 'E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7'], default='all')
    args = parser.parse_args()
    if args.prepare:
        prepare()
    if not (DATA / 'wdbc.csv').exists():
        raise SystemExit('Missing data: run with --prepare once.')
    out = BASE / '.tmp' / 'lesson11'
    out.mkdir(parents=True, exist_ok=True)
    experiments = {'E1': e1, 'E2': e2, 'E3': e3, 'E4': e4, 'E5': e5, 'E6': e6, 'E7': e7}
    for name, fn in experiments.items():
        if args.experiment in ['all', name]:
            fn(out)
            print(f'Completed {name}', flush=True)
    if args.experiment == 'all':
        summarize(out)
    print(f'Evidence: {out}')


if __name__ == '__main__':
    main()
