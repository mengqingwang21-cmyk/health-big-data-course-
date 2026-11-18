# 集成学习何时值得？生物医学分类中的性能、稳定性与复杂度权衡

## 摘要

在保留WDBC课程原始划分、恶性=1的条件下，对8个预设模型开展开发集共享五折比较，并以固定验证集分析机制与稳定性。LR、RBF-SVM、深树、Bagging和RF的CV AUC分别为0.9942、0.9928、0.9267、0.9869和0.9893。30份共享训练重抽样下，深树/Bagging/RF的any-flip比例为27.2%/14.9%/7.9%。结果支持考察集成的降波动收益，同时不支持预设复杂模型必然替代简单基线。贡献是可复现实证比较和机制分析，不提出新算法。**锁定测试集尚未评价。**

## 1. 研究问题与运行前假设

RQ1：集成相较同深度单树改善哪些表现？RQ2：训练扰动下是否更稳定，抽样/相关性的证据是什么？RQ3：综合表现、计算、稳定性与解释成本，复杂模型是否值得？

运行前已将H1–H4、参数、阈值、种子、主次分析写入[protocol.md](protocol.md)，本地时间在run_info.json中；这不是公共预注册。H1预期Bagging/RF优于同深度单树且更稳；H2预期sqrt随机化降低同步错误，但可能因相关冗余而收益有限；H3预期树数边际递减、Boosting训练改善不保证验证改善；H4允许简单基线综合占优。未使用教师参考数字作为实验结果。

## 2. 数据、验证与指标

数据来源UCI WDBC，DOI:10.24432/C5DW2B，课程CSV由sklearn版本载入数据离线制备。一行是细针穿刺图像形态汇总，不是未来风险。仅打开student/train.csv、validation.csv，未调用完整数据加载器，未运行prepare_data，未访问teacher目录或锁定测试特征。源文档写明全量569及锁定114；本次数据审计只针对455条开放标签记录。

| split | n | negative | positive | prevalence | missing_cells | duplicate_feature_rows |
| --- | --- | --- | --- | --- | --- | --- |
| train | 341 | 214 | 127 | 0.3724 | 0 | 0 |
| validation | 114 | 71 | 43 | 0.3772 | 0 | 0 |
| development | 455 | 285 | 170 | 0.3736 | 0 | 0 |

保留原train341、validation114；主结果是455条开发集共享五折分层CV；固定验证用于机制、混淆矩阵、解释及bootstrap区间。开发CV与固定验证共享样本，因此并非独立复制。CV训练规模364，与固定train341不同，且CV验证折可包含原train和原validation；两类结果回答相近但不相同的条件问题，不拼接成测试结论。数据缺乏患者ID及时间，无法核验患者独立性；逐行分层和bootstrap依赖记录近似独立的假设。

LR标准化在Pipeline内；SVM的校准器包裹完整标准化+SVC Pipeline，在当前训练部分内部三折校准、ensemble=False；训练bootstrap中的重复原记录按组留在同一校准折。SVM排序来自sigmoid后的predict_proba，非把margin当概率；其单调性保持同一最终SVC的排序。

主指标ROC-AUC；AP=ΣΔRecall×Precision，使用非插值average_precision_score，不是梯形PR面积；BA、敏感度、特异度及混淆矩阵均报告，malignant为阳性。分类阈值预设概率>=.5，未经验证优化；漏诊成本没有单独建模。所有模型的概率未统一校准，log-loss和概率SD需连同概率尺度局限解释。

## 3. 预设方法与主要结果

完整参数见results/run_info.json。浅树depth2用于解释；主单树和Bagging/RF基树均不限深度，隔离深度混杂。Bagging100全特征；RF100每节点sqrt；Ada50树桩lr1（SAMME）；GB100深度3、lr.1；LR与SVM均C1。主比较不根据探索曲线改参数。

| 模型 | CV AUC均值±SD | CV AP | CV BA | 验证AUC | 验证AP | 验证BA |
| --- | --- | --- | --- | --- | --- | --- |
| LR | 0.9942 ± 0.0099 | 0.9944 | 0.9865 | 1.0000 | 1.0000 | 0.9930 |
| RBF-SVM | 0.9928 ± 0.0096 | 0.9924 | 0.9695 | 1.0000 | 1.0000 | 1.0000 |
| Tree (depth 2) | 0.9328 ± 0.0325 | 0.9032 | 0.9278 | 0.9718 | 0.9368 | 0.9510 |
| Tree (full) | 0.9267 ± 0.0329 | 0.8490 | 0.9267 | 0.9672 | 0.9204 | 0.9672 |
| Bagging | 0.9869 ± 0.0125 | 0.9848 | 0.9536 | 0.9984 | 0.9974 | 0.9813 |
| RF (sqrt) | 0.9893 ± 0.0100 | 0.9881 | 0.9583 | 0.9971 | 0.9955 | 0.9697 |
| AdaBoost | 0.9874 ± 0.0139 | 0.9880 | 0.9641 | 0.9944 | 0.9929 | 0.9651 |
| Gradient Boosting | 0.9883 ± 0.0125 | 0.9874 | 0.9559 | 0.9967 | 0.9950 | 0.9581 |

CV为均值±折间样本SD（ddof=1），不是置信区间。验证数值来自341拟合、114评价；未评价锁定测试。主要完整阈值结果：

| model | roc_auc | average_precision | balanced_accuracy | sensitivity | specificity | tn | fp | fn | tp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LR | 1.0000 | 1.0000 | 0.9930 | 1.0000 | 0.9859 | 70 | 1 | 0 | 43 |
| RBF-SVM | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 71 | 0 | 0 | 43 |
| Tree (depth 2) | 0.9718 | 0.9368 | 0.9510 | 0.9302 | 0.9718 | 69 | 2 | 3 | 40 |
| Tree (full) | 0.9672 | 0.9204 | 0.9672 | 0.9767 | 0.9577 | 68 | 3 | 1 | 42 |
| Bagging | 0.9984 | 0.9974 | 0.9813 | 0.9767 | 0.9859 | 70 | 1 | 1 | 42 |
| RF (sqrt) | 0.9971 | 0.9955 | 0.9697 | 0.9535 | 0.9859 | 70 | 1 | 2 | 41 |
| AdaBoost | 0.9944 | 0.9929 | 0.9651 | 0.9302 | 1.0000 | 71 | 0 | 3 | 40 |
| Gradient Boosting | 0.9967 | 0.9950 | 0.9581 | 0.9302 | 0.9859 | 70 | 1 | 3 | 40 |

![开发集主比较](figures/performance_cv.png)

相对深树，集成的改善应在同深度条件下判断；LR/SVM已具有很高排序性能，集成的额外复杂度需要另外证明收益。排名差异不能仅用折间SD或五折平均的大小宣布显著性。

## 4. 机制消融

深度实验包含1/2/3/4/不限；训练指标与验证指标不单调一致。30份bootstrap的根特征/阈值变化提供单树不稳定的结构证据。2000次n=341抽样独特比例均值0.63210，OOB均值0.36790，与有限n期望一致。63.2%是训练记录被至少抽中一次的期望，不是只抽63.2%次。

![树深](figures/tree_depth.png)
![根变化](figures/root_variation.png)
![Bootstrap](figures/bootstrap_sampling.png)

树数1/10/50/100/300的比较和RF-all/sqrt对照见下图。RF两组同实现且bootstrap索引完全相同=True；Bagging与RF之间仍有实现细节。树数曲线为单固定种子，无误差线，不据此挑选主模型。100棵树错误相关性来自验证记录方向、排除了恒定错误向量，不直接等于Var公式的训练扰动ρ。

| model | kind | mean_correlation | median_correlation | n_pairs | excluded_constant_trees |
| --- | --- | --- | --- | --- | --- |
| bagging | binary_error | 0.2700 | 0.2614 | 4950 | 0 |
| random_forest | binary_error | 0.2801 | 0.2779 | 4950 | 0 |
| rf_all_features | binary_error | 0.2770 | 0.2677 | 4950 | 0 |

本次同实现RF-all→RF-sqrt的概率相关从0.821降至0.805；但二值错误相关从0.277变为0.280，没有下降，因此H2在错误同步性上未得到支持。不能用“RF必然降低错误相关”解释本次所有收益。

![树数与错误相关](figures/tree_count_mechanism.png)

方差公式ρσ²+(1−ρ)σ²/B假设同方差、等两两相关；一般形式为B⁻²ΣCov。B增加仅缩小有限平均项，相关残差构成下界。公式不保证偏差、AUC或阈值错误同步改善。

## 5. Boosting探索及算法对照

AdaBoost按当前加权错误提高错分记录权重；真实首轮e=0.0674，SAMME权重a=2.6266。GB在logit空间拟合y−p负梯度，随后更新叶值与函数，样本不必错分也会有非零残差。完整权重和梯度诊断已保存。

![Boosting曲线](figures/boosting_curves.png)

lr=.03/.1/.3各200轮的曲线是探索，不是独立调参结果；主Ada lr1/50和GB lr.1/100不变。训练损失下降不能保证验证性能改善，需通过内层CV/早停控制轮数。若未来采纳曲线最优设置，必须嵌套CV或另留独立评价并报告选择偏差。

本次GB lr=.1在50/100/200轮的验证log-loss为0.0788/0.0903/0.1133；lr=.3为0.1086/0.1137/0.1588，训练损失仍下降。H3的验证回升现象在当前固定曲线上可见，不能因此进行调参后的独立性能宣称。

XGBoost与LightGBM都是梯度提升树系统，并非与GB完全不同的学习范式。XGBoost的经典工作使用带树复杂度惩罚的目标、二阶梯度近似、采样和稀疏感知计算；LightGBM的经典论文提出GOSS和EFB，并以直方图、按叶生长等工程策略提高效率。经典sklearn GradientBoosting逐阶段拟合负梯度并进行损失相关叶节点更新。不能把XGBoost/LightGBM概括为“一定更准”，也不把所有版本和模式的缺失值、类别支持混为一谈。本次未安装或运行二者，不给出虚构实验排名。[R5–R7,S1,S5,S6]

## 6. 训练稳定性与固定模型条件区间

| model | mean_probability_sd | median_probability_sd | any_flip_fraction | n_any_flip | mean_pair_disagreement |
| --- | --- | --- | --- | --- | --- |
| LR | 0.0217 | 0.0018 | 0.0526 | 6 | 0.0202 |
| RBF-SVM | 0.0246 | 0.0042 | 0.0702 | 8 | 0.0158 |
| Tree (depth 2) | 0.0806 | 0.0127 | 0.2544 | 29 | 0.0608 |
| Tree (full) | 0.0930 | 0.0000 | 0.2719 | 31 | 0.0699 |
| Bagging | 0.0436 | 0.0108 | 0.1491 | 17 | 0.0338 |
| RF (sqrt) | 0.0294 | 0.0144 | 0.0789 | 9 | 0.0207 |
| AdaBoost | 0.0399 | 0.0389 | 0.1316 | 15 | 0.0276 |
| Gradient Boosting | 0.0398 | 0.0002 | 0.1228 | 14 | 0.0322 |

![稳定性](figures/training_stability.png)

同一30份训练bootstrap，模型随机种子固定；概率SD是逐样本30次预测的样本SD，箱线图跨114个验证样本；any-flip为30次出现过两类的样本比例，随重复次数改变。pair disagreement为两个不同重拟合模型的类别不一致概率，提供不依赖“是否曾翻过”的补充。SVM有校准、AdaBoost输出压缩，低概率SD不能单独证明更可靠；类别稳定性和预测性能必须同时看。算法种子10次补充结果在algorithm_seed_stability.csv。

| model_a | model_b | point | low | high |
| --- | --- | --- | --- | --- |
| RF (sqrt) | Tree (full) | 0.0298 | 0.0057 | 0.0631 |
| Bagging | Tree (full) | 0.0311 | 0.0064 | 0.0662 |
| RF (sqrt) | Bagging | -0.0013 | -0.0049 | 0.0000 |
| RF (sqrt) | LR | -0.0029 | -0.0092 | 0.0000 |
| RF (sqrt) | RBF-SVM | -0.0029 | -0.0092 | 0.0000 |
| Gradient Boosting | LR | -0.0033 | -0.0105 | 0.0000 |
| Gradient Boosting | RF (sqrt) | -0.0003 | -0.0039 | 0.0026 |

![条件区间](figures/paired_intervals.png)

固定模型在validation114中按类别分层配对bootstrap2000次，百分位95%区间。区间条件于当前已拟合模型、验证经验分布与类别数量，不包含重训、选模、外部人群变化；验证数据也用于探索，不是对选出赢家的无偏推断。满分AUC的经验bootstrap可能退化，不能视为总体性能已知。未作多重比较显著性声明，CV折间SD也不作为显著性证据。

## 7. 解释、计算与模型选择

![特征解释](figures/importance_comparison.png)

train341中|r|>.9有21/435对。MDI在相关替代变量间分摊，单特征置换也会因替代预测而很小或为负；置换20次误差线只反映置换随机性。组置换提供相关尺寸变量共同依赖的敏感性证据，亦不识别因果。LR标准化系数也不能在共线性下简单当作独立效应。

![表现与训练成本](figures/performance_cost.png)

计时是本机、单线程、wall time，CV每折记录；SVM含三折校准。它受硬件、缓存和调度影响，不是普适速度基准。模型节点数及固定验证预测耗时见validation_metrics.csv。LR系数可直接审阅；浅树规则最直观但性能/稳定性有限；SVM需要支持向量、尺度和校准解释；Bagging/RF/Boosting需要额外全局和局部解释分析。解释成本为定性判断，未虚构人工计时或临床可用性分数。

在WDBC现有划分和预设参数下，我优先保留逻辑回归，RBF-SVM作为性能参照，随机森林作为非线性候选。开发集五折AUC中，LR为0.9942，RF为0.9893；RF改善了同深度单树，但未证明复杂模型必然优于简单基线。共享30份训练重抽样后，单树与RF的类别翻转样本比例分别为27.2%和7.9%，支持聚合降低扰动。LR系数易审阅，但相关变量会影响系数解释；RF需额外置换分析，训练和解释成本更高。概率波动依赖模型尺度，验证差值区间只条件于当前模型与样本，折间SD不是显著性证据。目前锁定测试集尚未评价，缺少患者分组、时间信息和外部队列；重要性不代表因果，当前良恶性分类不是未来风险。若预先锁定的独立多中心验证显示RF在临床阈值下稳定减少漏诊，且校准与净获益改善，我会改变选择。

| 方面 | Bagging（含随机森林） | Boosting |
| --- | --- | --- |
| 训练方式 | 各基树可并行；最终平均概率 | 阶段顺序依赖；同一阶段内部可有工程并行 |
| 每轮数据或权重 | 独立有放回抽样；RF另随机化节点候选特征 | AdaBoost改变样本权重；GB在当前损失负梯度上拟合新树 |
| 基学习器 | 常用充分生长的深树；并非每棵都是“弱”分类器 | AdaBoost常用树桩；GB常用浅树，可调整复杂度 |
| 偏差与方差 | 主要降低不稳定基学习器的方差，未保证降低偏差 | 逐步修正函数，常降低偏差；也受方差和正则影响 |
| 噪声及轮数 | 更多树一般减少Monte Carlo波动并趋于平台；不保证每个验证指标单调 | Ada可能强调噪声；GB过多轮可能拟合噪声；需训练内部选择或早停 |
| 关键参数 | n_estimators、max_features、max_samples、max_depth、min_samples_leaf | learning_rate与n_estimators联动，max_depth、min_samples_leaf、subsample及损失 |


## 8. 局限与下一步

小样本、单一历史数据，近似可分且高度相关，性能存在天花板；没有患者分组、时间或机构信息；未做嵌套调参、临床阈值优化、全面概率校准和外部评价。外部人群泛化不确定性无法由本次bootstrap回答。下一步先锁定候选、临床漏诊成本、阈值及校准评价，再安排一次锁定测试，随后用独立多中心/时间外队列检查敏感度、校准、净获益及亚组公平性。CTG可作为独立方法对照，但必须按recording_id划分和重抽样；不称其为WDBC模型的外部验证。本次未开展CTG扩展。

## 9. 复现与审计

运行环境及全量依赖：results/run_info.json、pip_freeze.txt。开始2026-11-14T00:02:23.907237+08:00，结束2026-11-14T00:03:25.019478+08:00，核心实验wall time 61.1秒。模型/折种子1010，模拟1011，训练bootstrap1012，配对bootstrap1013，置换1014。文件哈希、全部参数、CV分配、两种bootstrap索引、每折指标、预测、机制结果和joblib模型均保存。执行说明见项目RUN_RESEARCH.md；原数据及课程课件保留。

## 参考文献与可访问性

- [D1] Wolberg, Street & Mangasarian. Breast Cancer Wisconsin (Diagnostic). UCI (1995). DOI:10.24432/C5DW2B. <https://archive.ics.uci.edu/dataset/17/breast+cancer+wisconsin+diagnostic>
- [R1] Efron B. Bootstrap Methods: Another Look at the Jackknife. Annals of Statistics 7(1):1–26 (1979). DOI:10.1214/aos/1176344552. <https://doi.org/10.1214/aos/1176344552>
- [R2] Breiman L. Bagging Predictors. Machine Learning 24:123–140 (1996). DOI:10.1007/BF00058655. <https://doi.org/10.1007/BF00058655>
- [R3] Breiman L. Random Forests. Machine Learning 45:5–32 (2001). DOI:10.1023/A:1010933404324. <https://doi.org/10.1023/A:1010933404324>
- [R4] Freund Y, Schapire RE. A Decision-Theoretic Generalization of On-Line Learning and an Application to Boosting. JCSS 55(1):119–139 (1997). DOI:10.1006/jcss.1997.1504. <https://doi.org/10.1006/jcss.1997.1504>
- [R5] Friedman JH. Greedy Function Approximation: A Gradient Boosting Machine. Annals of Statistics 29(5):1189–1232 (2001). DOI:10.1214/aos/1013203451. <https://doi.org/10.1214/aos/1013203451>
- [R6] Chen T, Guestrin C. XGBoost: A Scalable Tree Boosting System. KDD (2016):785–794. DOI:10.1145/2939672.2939785. <https://arxiv.org/abs/1603.02754>
- [R7] Ke G et al. LightGBM: A Highly Efficient Gradient Boosting Decision Tree. NeurIPS 30 (2017). <https://papers.nips.cc/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html>
- [S1] scikit-learn 1.7 User Guide: Ensemble methods. <https://scikit-learn.org/1.7/modules/ensemble.html>
- [S2] scikit-learn 1.7 API: average_precision_score (non-interpolated AP). <https://scikit-learn.org/1.7/modules/generated/sklearn.metrics.average_precision_score.html>
- [S3] scikit-learn 1.7 User Guide: Probability calibration. <https://scikit-learn.org/1.7/modules/calibration.html>
- [S4] scikit-learn 1.7 User Guide: Permutation feature importance. <https://scikit-learn.org/1.7/modules/permutation_importance.html>
- [S5] XGBoost official documentation: Introduction to Boosted Trees. <https://xgboost.readthedocs.io/en/stable/tutorials/model.html>
- [S6] LightGBM official documentation: Features. <https://lightgbm.readthedocs.io/en/stable/Features.html>

链接检查只检查公开网页，不下载数据集；HTTP访问限制与书目真实性分别记录，不把403称为文献不存在。检查记录：

- D1: HTTP 200；HTTP checked。
- R1: HTTP 200；HTTP checked。
- R2: HTTP 200；HTTP checked。
- R3: HTTP 200；HTTP checked。
- R4: HTTP 200；HTTP checked。
- R5: HTTP 200；HTTP checked。
- R6: HTTP 200；HTTP checked。
- R7: HTTP 200；HTTP checked。
- S1: HTTP 200；HTTP checked。
- S2: HTTP 200；HTTP checked。
- S3: HTTP 200；HTTP checked。
- S4: HTTP 200；HTTP checked。
- S5: HTTP 200；HTTP checked。
- S6: HTTP 200；HTTP checked。
