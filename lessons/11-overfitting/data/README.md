# 数据说明

## wdbc.csv（真实公开数据，默认）

Breast Cancer Wisconsin (Diagnostic)，由 sklearn 内置版本导出：569 条乳腺肿块细针穿刺图像的细胞核特征记录，30 个连续特征，恶性 212 条、良性 357 条。一行是一份样本，不是一个细胞。表中没有患者分组或中心字段。

- `sample_id`：课程生成的编号，不作为特征。
- `malignant`：1 = 恶性（与 sklearn 原标签方向相反）。
- `split`：seed=1111 的分层 70/30 训练/验证划分（398 / 171）。
- 其余 30 列（`mean_*`、`*_error`、`worst_*`）为特征，定义见 sklearn 数据说明。

来源：https://archive.ics.uci.edu/dataset/17/breast+cancer+wisconsin+diagnostic （DOI 10.24432/C5DW2B，CC BY 4.0；Wolberg、Street、Mangasarian）。sklearn 加载说明：https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_breast_cancer.html 。

## 模拟数据（由本课脚本生成，无真实受试者）

| 文件 | 规模与字段 | 用途 |
|---|---|---|
| null-omics.csv | 180 行，1000 个 `gene_*`，`sample_id`、`y` | 纯噪声特征 + 随机标签，用于 E4 特征筛选泄露 |
| repeated-patients.csv | 400 行，40 个 `marker_*`，`patient_id`、`visit`、`y` | 100 位患者各 4 条近乎相同的记录，标签按患者随机，用于 E5 |

“基因”“marker”只是教学命名，没有生物学含义。ID、`visit` 和 `y` 不能作为特征。E6、E7 的数据在脚本中按固定种子生成。`manifest.json` 记录生成时的种子、划分大小和软件版本。

## 备选数据：Golub 白血病表达谱

第 3、4、6 课使用过的 `3. High-dimension/data/leukemia.csv`：72 份样本（ALL 47 / AML 25）× 7129 个探针，典型的“样本少、特征多”。适合在真实表达数据上重做 E4：打乱诊断标签后，对比全局筛选与折内筛选。来源与字段说明见该目录下的 `README.md`。

## 重建

CSV 已随课程提供，运行实验不需要联网。`python scripts/run_experiments.py --prepare` 会用固定种子重新生成本目录的文件。
