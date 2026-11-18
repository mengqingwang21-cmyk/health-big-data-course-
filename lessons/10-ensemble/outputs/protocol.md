# 运行前固定的研究协议

本文件先于实验脚本的第一次运行写入。它是本地分析承诺，不是第三方预注册。创建及实验时间由运行清单以 Asia/Shanghai 记录；不引用教师参考数字作为结果。

题目：集成学习何时值得？生物医学分类中的性能、稳定性与复杂度权衡。

## 假设与判读规则

- H1：不限深度树的 Bagging 和随机森林较同深度单树具有更高开发集 CV ROC-AUC、更低训练重抽样预测波动。分别检查性能与稳定性，不要求两者同时成立。
- H2：sqrt 特征随机化较全特征树聚合降低树间错误相关性；性能收益可能因形态特征冗余和天花板效应而很小。采用同一 RandomForest 实现的 max_features=1.0 对照，区别于 API 差异。
- H3：树数增加主要带来边际递减；Boosting 训练损失下降不保证验证损失持续下降。
- H4：预设集成在当前数据上的性能优势不足以自动替代 LR / RBF-SVM；选择同时考虑预测表现、训练扰动稳定性、计算和解释成本。允许拒绝假设；不预设赢家，不用显著性筛选结论。

## 数据及边界

只读取 data/student/train.csv、validation.csv。保留原行序和划分；sample_id 仅追踪，malignant=1。禁止读取 teacher/、完整测量表、原始数据或 sklearn 完整数据加载器；不读取锁定测试特征。锁定测试集尚未评价。已阅读两套数据 README，主实验仅 WDBC，CTG 不在核心实验范围。

## 设计

- 主比较：train+validation（455 条）共享五折 StratifiedKFold，shuffle=True，seed=1010。报告每折、均值及样本 SD（ddof=1），不把 SD 称为 CI。所有模型用相同折索引。
- 固定验证：train（341 条）拟合，validation（114 条）评价；用于机制图、混淆矩阵、稳定性、置换解释及条件区间。它与开发集 CV 共享样本，不是额外独立证据。
- 8 个预设模型：LR(C=1, lbfgs, max_iter=5000)；RBF-SVM(C=1,gamma=scale)；浅树(depth=2)；不限深度单树；Bagging(100棵不限深度树、全特征)；RF(100棵、sqrt、不限深度)；AdaBoost(50棵树桩、lr=1、SAMME)；GradientBoosting(100阶段、depth=3、lr=.1、log_loss)。其余 sklearn 默认值完整保存。
- LR 标准化置于 Pipeline。SVM 为 CalibratedClassifierCV(Pipeline(StandardScaler,SVC), method=sigmoid, ensemble=False)：三折校准只用当前训练部分，Pipeline 在每个校准训练折拟合。sigmoid 单调转换保持排序；统一使用概率>=.5分类。校准不是超参数搜索。训练 bootstrap 内的校准按原训练行索引分组，避免重复抽中的同一记录跨校准折。概率波动依赖概率尺度，尤其不能将不同模型未经统一校准的 SD 当作临床风险精度排名。
- 指标：ROC-AUC 主指标；AP=Σ(R_k−R_{k−1})P_k（sklearn average_precision_score，非梯形 PR 面积）；balanced accuracy、恶性敏感度、特异度、TN/FP/FN/TP。阈值全为预设 .5；未优化阈值。log-loss 仅对 predict_proba 输出计算，绝不把 SVM margin 当概率。
- 模型和 CV seed=1010；bootstrap模拟=1011；训练扰动=1012；验证配对重抽样=1013；置换=1014。每次随机算法种子固定，n_jobs=1，并限制 BLAS 线程为1。记录 wall time、软件版本、所有参数、数据和代码 SHA256。

## 机制与不确定性

- 深度 1/2/3/4/不限；30 份共享 bootstrap 的浅树根节点及阈值。
- 2000 次 n=341 有放回抽样，保存独特比例和 OOB 比例；另 n=5 展示有限样本效应。
- Bagging、RF-sqrt、RF-all 树数 1/10/50/100/300；B>=50 记录 OOB accuracy/AUC；在114个验证样本上记录100棵树两两概率、残差及二值错误相关性。它们是验证样本方向的描述性相关，不能直接代入训练扰动方差公式。
- AdaBoost 和 GB 的 lr=.03/.1/.3，每条200轮，保存各轮训练/验证 AUC、log-loss；仅探索，不用曲线改动主模型或宣称最优轮数的独立验证性能。额外追踪实际 AdaBoost 前8轮权重及 GB 前5轮 y-p。
- 训练扰动：同一30份 n=341 有放回训练样本用于全部8模型，验证114条固定；计算逐样本概率样本SD、any-flip比例（30次中出现过两类的验证样本占比）、平均两次重拟合类别不一致概率和偏离众数比例。any-flip随重拟合次数变化。另固定train改变10个算法种子考察树类算法随机性。
- 固定模型条件区间：验证集中按类别分层、成对重抽样2000次，同一索引用于全部模型；保存 AUC/AP/BA 和差值的百分位95%区间。预设差值 RF−单树、Bagging−单树、RF−Bagging、RF−LR、RF−SVM、GB−LR、GB−RF。区间条件于当前拟合模型、验证样本经验分布及类别数量，排除重训、模型选择和外部人群不确定性，不作多重比较显著性宣告。
- 主 RF100 的 MDI 与验证集20次置换 AUC 重要性；训练集 Pearson 相关矩阵；额外相关特征联合置换。置换 SD 是重复置换波动，不是抽样CI；重要性不是因果效应。

## 作业与展示

完成工作单A–H和250–400字备忘录；正式汇报16页正文、少量备份，约11分钟，每页讲稿。输出 CSV、PNG/SVG/PDF图、可编辑PPT、PDF（本机PowerPoint可用时）、报告、运行说明与审核记录。课程原数据和课件保留；旧演示脚本仅修正输出到本项目 outputs/demo/。
