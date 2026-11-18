# 工作单 A—H：完成稿

题目：集成学习何时值得？生物医学分类中的性能、稳定性与复杂度权衡。

姓名/小组：未提供，留待填写。运行时间：2026-11-14T00:02:23.907237+08:00。主数据WDBC，malignant=1。所有表格来自本次实际CSV；教师参考材料中的数字不作为结果。

## 数据与验证协议

一行是一条乳腺肿块细针穿刺图像的细胞核形态汇总记录，不是一颗细胞或可追踪的患者。30个预测特征为10类形态量的mean、standard error、worst汇总；sample_id只用于追踪，潜在的recording_id仅用于分组，均不进入输入。恶性标签是当前诊断分类，不是未来患病概率。

train用于拟合，validation用于固定划分分析；开发集train+validation共享五折CV是主比较，检验预设算法在开发样本内的迁移表现。CV与固定验证共享数据，不能称两次独立复制。测试集用于最后一次锁定评价，本次明确**锁定测试集尚未评价**。用户要求优先于workplan E8的揭示测试安排，未运行数据重建脚本，未打开teacher-reference.md，也未读取teacher/或原始数据源。

| split | n | negative | positive | prevalence | missing_cells | duplicate_feature_rows |
| --- | --- | --- | --- | --- | --- | --- |
| train | 341 | 214 | 127 | 0.3724 | 0 | 0 |
| validation | 114 | 71 | 43 | 0.3772 | 0 | 0 |
| development | 455 | 285 | 170 | 0.3736 | 0 | 0 |

## A. 决策树

1. 课件第5页示例：worst perimeter=120 >105.95，走右支；mean concave points=.08 >.05，再走右支，进入“良3、恶112”的叶子，预测恶性，P(恶性)=112/(3+112)=0.9739。该数字是工作单引用的**教学示例计数**，不是本研究新增实验结果。叶概率是叶节点训练样本中恶性比例；若有权重则用加权比例，不能直接解释成经外部校准的患者风险。本次拟合树见example_tree_depth2.txt、example_tree_nodes.csv及图稿。
2. 每节点遍历候选特征和阈值，使父节点不纯度减去按子节点样本权重加权的不纯度最大。Gini=1−Σp_k²；二分类为2p(1−p)，纯节点为0，p=.5时最大。不纯度下降是局部贪心目标，不保证全局最优树。
3. 本次深度实验如下。训练准确率可随深度上升直至拟合全部训练记录，验证指标不保证单调；叶概率变化可能让AUC和准确率呈现不同趋势。浅树depth2用于可读规则，不限深度单树用于与集成基树对齐；不能把深度差异误认为集成收益。

| max_depth | split | leaves | accuracy | roc_auc | balanced_accuracy |
| --- | --- | --- | --- | --- | --- |
| 1 | train | 2 | 0.9326 | 0.9351 | 0.9351 |
| 1 | validation | 2 | 0.9123 | 0.9158 | 0.9158 |
| 2 | train | 4 | 0.9560 | 0.9741 | 0.9457 |
| 2 | validation | 4 | 0.9561 | 0.9718 | 0.9510 |
| 3 | train | 7 | 0.9795 | 0.9846 | 0.9772 |
| 3 | validation | 7 | 0.9737 | 0.9735 | 0.9743 |
| 4 | train | 11 | 0.9883 | 0.9925 | 0.9859 |
| 4 | validation | 11 | 0.9649 | 0.9528 | 0.9627 |
| unlimited | train | 17 | 1.0000 | 1.0000 | 1.0000 |
| unlimited | validation | 17 | 0.9649 | 0.9672 | 0.9672 |

4. 相同30份bootstrap训练样本拟合depth2树后，根节点如下。同特征阈值也会改变，说明单树对训练扰动敏感；不同特征的阈值单位不同，不合并阈值范围。

| root_feature | 次数 | 阈值最小 | 阈值最大 |
| --- | --- | --- | --- |
| mean concave points | 2 | 0.0539 | 0.0539 |
| worst area | 5 | 874.8500 | 884.7500 |
| worst concave points | 6 | 0.1366 | 0.1472 |
| worst perimeter | 14 | 103.2500 | 115.4500 |
| worst radius | 3 | 16.8050 | 17.4200 |

5. 树的候选切分依赖特征大小次序，严格递增线性单位变换通常保留切分；数值并列/浮点可能产生细微差异。LR的正则化、SVM的距离和核宽度对尺度敏感，因此StandardScaler在Pipeline里、每训练折内拟合。不是“一切集成模型都不需要标准化”。

## B. 投票与方差

| 样本 | 真值 | 硬投票类别 | 软投票P(1) | 软投票类别(>=.5) |
| --- | --- | --- | --- | --- |
| A | 1 | 1 | 0.6500 | 1 |
| B | 0 | 1 | 0.4833 | 0 |
| C | 1 | 1 | 0.6333 | 1 |
| D | 0 | 0 | 0.3667 | 0 |

硬投票取类别众数；软投票先平均三个P(1)，再用.5阈值。B的硬投票错分，而软概率均值.4833落在正确类别0一侧。这是给定教学表的手算，不是WDBC实验。

对随机训练样本引起的固定输入x预测，若B个预测都具有相同方差σ²，且任意两模型相关系数相同ρ，则Var(平均预测)=ρσ²+(1−ρ)σ²/B。B趋于无穷时剩余ρσ²；ρ≈1时平均几乎没有收益。该简式要求相同边际方差与共同两两协方差，是可交换近似，不表示真实树完全等方差或等相关。一般形式为B⁻²Σ_iΣ_jCov(f_i,f_j)。它不直接给出AUC或分类错误率。

平均并不自动消除偏差；固定同分布基学习器时平均的期望仍等于单个预测的期望。深树常具有较低训练偏差、较高训练扰动方差，适合聚合；稳定LR的bagging收益往往较小，但不是数学上永远为零。验证样本方向的树间错误相关性只能作机制佐证，不等于该式训练扰动方向的ρ。

## C. Bootstrap

1. [2,2,5,1,2]中索引2出现3次，独特记录{1,2,5}占3/5，OOB为{3,4}占2/5。
2. 主模拟每次从341条抽341次、重复2000次：独特比例均值0.63210、样本SD0.01685；OOB均值0.36790。有限样本理论OOB=(1−1/n)^n=0.36734，独特比例为其补数。极限e⁻¹≈36.8%及1−e⁻¹≈63.2%是期望规律，不是每次固定；n=5理论独特比例1−(.8)^5=.67232，不能强套63.2%。完整模拟见bootstrap_sampling.csv。
3. Bagging对训练记录独立有放回抽样，为各基树制造不同训练集；树彼此不依赖，可以并行，本次为可比计时统一单线程。
4. 对每条训练记录，仅汇总没有抽到它的树的概率，再对这些OOB预测计算指标；不是把每棵树OOB误差简单平均。OOB可在近似独立同分布条件下估计袋装模型内部表现，B不足时某些记录可能没有足够OOB预测；反复用OOB调参也产生选择偏差。它不能替代锁定测试、外部验证、校准检验或群体迁移评估。CTG按行OOB会混入同录音其他片段，可能偏乐观，需分组方法。本次CTG未运行。

## D. 单树、Bagging与随机森林

| 模型 | 验证AUC | 验证BA | 平均概率SD | any-flip比例 |
| --- | --- | --- | --- | --- |
| Tree (full) | 0.9672 | 0.9672 | 0.0930 | 0.2719 |
| Bagging | 0.9984 | 0.9813 | 0.0436 | 0.1491 |
| RF (sqrt) | 0.9971 | 0.9697 | 0.0294 | 0.0789 |

单树、Bagging基树和RF基树均不限深度；Bagging每节点全特征，RF每节点候选sqrt(30)（sklearn取整数5）。特征子抽样可阻止强特征在所有树根节点重复被选，减少同步错误，但会降低单树强度；结果取决于权衡。额外RF-all与RF-sqrt使用同一RF实现且本次bootstrap索引完全一致=True，尽量隔离特征随机化。

| model | n_trees | validation_roc_auc | validation_balanced_accuracy | oob_accuracy | oob_roc_auc |
| --- | --- | --- | --- | --- | --- |
| bagging | 1 | 0.9274 | 0.9274 | nan | nan |
| bagging | 10 | 0.9975 | 0.9743 | nan | nan |
| bagging | 50 | 0.9987 | 0.9813 | 0.9355 | 0.9802 |
| bagging | 100 | 0.9984 | 0.9813 | 0.9443 | 0.9826 |
| bagging | 300 | 0.9980 | 0.9743 | 0.9472 | 0.9833 |
| random_forest | 1 | 0.9369 | 0.9369 | nan | nan |
| random_forest | 10 | 0.9966 | 0.9672 | nan | nan |
| random_forest | 50 | 0.9972 | 0.9627 | 0.9560 | 0.9840 |
| random_forest | 100 | 0.9971 | 0.9697 | 0.9619 | 0.9869 |
| random_forest | 300 | 0.9969 | 0.9697 | 0.9619 | 0.9893 |
| rf_all_features | 1 | 0.9437 | 0.9437 | nan | nan |
| rf_all_features | 10 | 0.9980 | 0.9602 | nan | nan |
| rf_all_features | 50 | 0.9990 | 0.9813 | 0.9384 | 0.9809 |
| rf_all_features | 100 | 0.9984 | 0.9813 | 0.9472 | 0.9826 |
| rf_all_features | 300 | 0.9980 | 0.9743 | 0.9531 | 0.9832 |

| model | kind | mean_correlation | median_correlation | n_pairs | excluded_constant_trees |
| --- | --- | --- | --- | --- | --- |
| bagging | probability | 0.8249 | 0.8297 | 4950 | 0 |
| bagging | residual | 0.3129 | 0.3070 | 4950 | 0 |
| bagging | binary_error | 0.2700 | 0.2614 | 4950 | 0 |
| random_forest | probability | 0.8053 | 0.8043 | 4950 | 0 |
| random_forest | residual | 0.3298 | 0.3306 | 4950 | 0 |
| random_forest | binary_error | 0.2801 | 0.2779 | 4950 | 0 |
| rf_all_features | probability | 0.8210 | 0.8202 | 4950 | 0 |
| rf_all_features | residual | 0.3218 | 0.3165 | 4950 | 0 |
| rf_all_features | binary_error | 0.2770 | 0.2677 | 4950 | 0 |

相关性来自相同114条验证记录上的100棵树两两预测/残差/二值错误，恒定向量排除，n_pairs如表。样本中的容易/困难记录和类别结构也会影响相关性，因此不能据此证明ρ精确下降或把相关变化都归因于随机特征。增加树数减少有限B的Monte Carlo波动并趋于平台，不能宣称每个验证指标单调提高或“绝不会过拟合”。本次不根据最优曲线点重选树数，100棵仍是预设主模型。

本次同实现RF-all→RF-sqrt的概率相关从0.821降至0.805；但二值错误相关从0.277变为0.280，没有下降，因此H2在错误同步性上未得到支持。不能用“RF必然降低错误相关”解释本次所有收益。 三组曲线从1→10棵改善明显，50→300棵趋于平台且验证AUC略有回落；这是单次探索，不把50棵宣称为已验证最优值。

不纯度重要性前列：worst area, worst perimeter, worst concave points, worst radius, mean concave points；置换前列：worst area, worst concave points, worst texture, worst smoothness, mean concave points。二者不必一致：MDI归因训练中实际分裂，偏好有更多分裂机会的变量；置换衡量当前模型和数据分布下打乱单变量的性能变化。train341中|r|>.9的特征对为21/435，相关变量可分摊MDI、互相替代并稀释单变量置换。联合置换见grouped_permutation.csv，也仅是描述性敏感性分析。

## E. Boosting

1. 二类SAMME第t轮加权错误e_t，sklearn基学习器权重a_t=ηlog((1−e_t)/e_t)。错分记录的未归一化权重乘exp(a_t)，正确记录不变，再全体归一化。等价于经典±1记号下α_t=(η/2)log((1−e_t)/e_t)、w_i←w_i exp(−α_t y_i h_t(x_i))。提高错分权重令下一轮集中于之前未解释的样本，也可能过度关注噪声；不同于Bagging的独立同权重抽样。首轮真实加权错误=0.0674，a=2.6266，错分未归一化倍数=13.826。前8轮每条训练记录权重均已保存，并核对加权错误与sklearn一致。
2. 对logit F、p=sigmoid(F)，二类log-loss对F的负梯度为y−p，正确预测但概率不足的样本也贡献梯度；新树近似拟合残差方向，随后作损失相关叶节点更新并乘learning_rate。GB不是只找错分记录。保存的gradient_directions.csv追踪按sample_id预先排序取前6条、前5轮的p、y−p和log-odds更新。
3. lr=.03/.1/.3各200轮的训练/验证log-loss及AUC已完整保存。两者有联动：小学习率通常需要更多轮；训练损失改善不确保验证改善，过多轮可追随噪声。主Ada的lr=1/50轮、主GB的lr=.1/100轮均未改动。探索数据参与了曲线审阅，不是调参后独立验证；若要据此选参数，后续用嵌套CV或独立的内层早停集合，再对外层评价。
   具体观察：GB lr=.1的验证log-loss从50轮0.0788升到200轮0.1133，尽管训练损失继续下降；lr=.3时50轮0.1086到200轮0.1588。这些值由boosting_curves.csv四舍五入而来，支持本次H3的非单调验证预期。
4. XGBoost与LightGBM都是梯度提升树系统，并非与GB完全不同的学习范式。XGBoost的经典工作使用带树复杂度惩罚的目标、二阶梯度近似、采样和稀疏感知计算；LightGBM的经典论文提出GOSS和EFB，并以直方图、按叶生长等工程策略提高效率。经典sklearn GradientBoosting逐阶段拟合负梯度并进行损失相关叶节点更新。不能把XGBoost/LightGBM概括为“一定更准”，也不把所有版本和模式的缺失值、类别支持混为一谈。本次未安装或运行二者，不给出虚构实验排名。[R5–R7,S1,S5,S6]

## F. 公平比较

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

ROC-AUC评价排序；AP=Σ_k(R_k−R_{k−1})P_k，使用sklearn average_precision_score，不是梯形插值PR-AUC；AP对阳性率敏感。BA=(敏感度+特异度)/2。概率阈值统一>=.5；SVM为训练内部三折sigmoid校准版本，ensemble=False后在当前全部训练部分拟合最终SVC，校准折内也独立标准化。主模型不调参数、不调阈值。SVM margin未作为概率计算log-loss。

本次LR CV AUC=0.9942 ± 0.0099，SVM=0.9928 ± 0.0096，RF=0.9893 ± 0.0100。应报告数值差异与折间波动，但不能把“差距小于某个SD”当正式检验，也不能用互相关联的五折结果当五个独立重复。集成相对于同深度单树的改善不能直接外推为胜过LR/SVM。当前保留LR与SVM性能基线，RF作为非线性候选；LR在成本和参数审阅方面有优势，但系数也受相关性及建模假设限制，不能写作因果效应。

## G. 稳定性与不确定性

每个模型用完全相同的30份训练bootstrap；算法种子不变，114条验证记录不变。SVM校准内按原训练记录索引分组，避免重复抽中的同一记录跨校准折。

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

逐样本概率SD按30次概率以ddof=1计算，表中为114条的平均/中位。any-flip=114⁻¹Σ_j I(0<q_j<1)，q_j为30次中预测恶性的比例，即至少出现过两种类别的样本比例，不是“30次所有预测的错误率”，也不是相对原模型的一次翻转概率。另报pair disagreement=平均[2n_1n_0/(R(R−1))]，即随机选两个不同重拟合模型时预测类别不一致的经验概率；modal disagreement=平均min(q,1−q)。any-flip依赖R，故各模型必须共享R=30。

概率SD的跨模型比较要谨慎：AdaBoost概率可能压缩，SVM进行了sigmoid校准而其他模型未统一校准；较小概率SD可能只是尺度效应。结合类别翻转和主性能共同判断，不能称为“患者风险置信区间”。固定train变10个算法种子的补充见algorithm_seed_stability.csv，描述不同于训练样本扰动的随机来源。

主要固定模型验证AUC差值：

| model_a | model_b | point | low | high |
| --- | --- | --- | --- | --- |
| RF (sqrt) | Tree (full) | 0.0298 | 0.0057 | 0.0631 |
| Bagging | Tree (full) | 0.0311 | 0.0064 | 0.0662 |
| RF (sqrt) | Bagging | -0.0013 | -0.0049 | 0.0000 |
| RF (sqrt) | LR | -0.0029 | -0.0092 | 0.0000 |
| RF (sqrt) | RBF-SVM | -0.0029 | -0.0092 | 0.0000 |
| Gradient Boosting | LR | -0.0033 | -0.0105 | 0.0000 |
| Gradient Boosting | RF (sqrt) | -0.0003 | -0.0039 | 0.0026 |

区间由固定train模型在validation内按类别分层、成对bootstrap2000次的2.5%/97.5%百分位得到。每个重抽样索引用于所有模型，类别数量固定；差值区间利用配对，不能用两个单模型区间简单相减。它们条件于已拟合模型、当前验证经验分布和类别数量，未包括训练变化、反复模型选择或外部人群变化；接近满分时经验bootstrap也可能给出退化区间，不能表示总体性能确定。固定验证已用于机制探索，区间不是选模后无偏推断，不宣告多重比较显著性。五折SD仅描述折间变动，不是CI或显著性证据。

| 证据 | 回答 | 不覆盖 |
| --- | --- | --- |
| 训练bootstrap重拟合 | 当前训练经验分布扰动时预测变化 | 外部人群与固定模型指标CI |
| 固定模型验证bootstrap | 当前模型在验证经验分布下的指标及配对差值变化 | 重训、选模、类别比例迁移 |
| 外部独立人群验证 | 新人群/机构/时间上的适用性 | 本次没有这类证据 |

## H. 解释、选择与备忘录

| 方面 | Bagging（含随机森林） | Boosting |
| --- | --- | --- |
| 训练方式 | 各基树可并行；最终平均概率 | 阶段顺序依赖；同一阶段内部可有工程并行 |
| 每轮数据或权重 | 独立有放回抽样；RF另随机化节点候选特征 | AdaBoost改变样本权重；GB在当前损失负梯度上拟合新树 |
| 基学习器 | 常用充分生长的深树；并非每棵都是“弱”分类器 | AdaBoost常用树桩；GB常用浅树，可调整复杂度 |
| 偏差与方差 | 主要降低不稳定基学习器的方差，未保证降低偏差 | 逐步修正函数，常降低偏差；也受方差和正则影响 |
| 噪声及轮数 | 更多树一般减少Monte Carlo波动并趋于平台；不保证每个验证指标单调 | Ada可能强调噪声；GB过多轮可能拟合噪声；需训练内部选择或早停 |
| 关键参数 | n_estimators、max_features、max_samples、max_depth、min_samples_leaf | learning_rate与n_estimators联动，max_depth、min_samples_leaf、subsample及损失 |


### 研究备忘录（340字符，含标点）

在WDBC现有划分和预设参数下，我优先保留逻辑回归，RBF-SVM作为性能参照，随机森林作为非线性候选。开发集五折AUC中，LR为0.9942，RF为0.9893；RF改善了同深度单树，但未证明复杂模型必然优于简单基线。共享30份训练重抽样后，单树与RF的类别翻转样本比例分别为27.2%和7.9%，支持聚合降低扰动。LR系数易审阅，但相关变量会影响系数解释；RF需额外置换分析，训练和解释成本更高。概率波动依赖模型尺度，验证差值区间只条件于当前模型与样本，折间SD不是显著性证据。目前锁定测试集尚未评价，缺少患者分组、时间信息和外部队列；重要性不代表因果，当前良恶性分类不是未来风险。若预先锁定的独立多中心验证显示RF在临床阈值下稳定减少漏诊，且校准与净获益改善，我会改变选择。

## 图表、参数与来源

所有完整精度CSV在results/；图稿PNG/SVG/PDF在figures/；运行协议protocol.md、模型参数/版本/数据哈希run_info.json、依赖pip_freeze.txt。正式汇报和逐页讲稿在presentation/。所有运行结果来自本次脚本；例题树计数和投票表明确为课程手算来源，不混入实验表。

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
