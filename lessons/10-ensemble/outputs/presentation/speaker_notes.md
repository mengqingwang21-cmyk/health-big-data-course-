# 逐页中文讲稿

正文16页，建议时长约11.1分钟；备份4页不计入时长。
每页PPT的备注中也保存同一份讲稿。可根据课堂语速调整停顿；全程未评价锁定测试集。

## 01. 集成学习何时值得？（约25秒）

今天关注性能、稳定性和复杂度的权衡。我们实际比较了八个预设模型，先固定协议，再运行实验。最主要的观察是：集成相较同深度单树改善了排序性能和训练扰动稳定性，但开发集CV中LR仍有竞争力。贡献是可复现实证与机制分析，不是新算法。接下来按三个研究问题说明证据和边界。

证据来源：WDBC [D1]；本次共享五折与重抽样实验
备注：本研究未评价锁定测试集；结论限于当前数据和验证协议。

## 02. 先固定假设，再让实验决定结论（约35秒）

三个问题分别问改善什么、为什么更稳、以及复杂度是否值得。H1预期Bagging和RF相对同深度单树改善性能并减少训练扰动。H2预期额外随机特征减少同步错误，但我们允许相关特征冗余使收益有限。H3预期加树边际递减，训练损失下降不保证验证下降。H4允许LR或SVM综合占优。这些判读规则和参数在首次运行前已保存，属于本地分析承诺，未声称公共预注册。

证据来源：运行前协议 outputs/protocol.md；预设参数、不调主模型
备注：本研究未评价锁定测试集；结论限于当前数据和验证协议。

## 03. 共享五折是主比较，固定验证用于机制分析（约50秒）

仅读取课程现成的341条训练和114条验证记录，恶性为1。30个连续特征，ID不进入模型。原划分保留：固定验证分析始终只用341条拟合。主比较另在455条开发数据上做共享五折，每个模型使用完全相同折索引。两种分析重叠，不能当两次独立复现。LR的Scaler在Pipeline里，SVM的校准器包裹Scaler与SVC，在每个训练内部三折做sigmoid校准。没有读锁定测试或teacher数据，缺少患者分组信息也作为限制记录。

证据来源：data/README.md [D1]；results/dataset_audit.csv、cv_assignments.csv；[S2,S3]
备注：本研究未评价锁定测试集；结论限于当前数据和验证协议。

## 04. 树越深训练越好，训练样本一变根节点也会变（约40秒）

左图中训练准确率随深度增加到1，但固定验证准确率在depth3后没有继续提高。这说明拟合训练数据和获得可迁移表现不是一回事。右图来自相同30份训练bootstrap，各拟合depth2树，根节点出现多种特征，阈值也在同一特征内变化。结构变化给出不稳定的直观证据，后面还会用预测变化直接测量。公平机制对照采用不限深度单树，与Bagging和RF基树保持一致；浅树只承担可读示例角色。

证据来源：train341 / validation114；单种子深度曲线；30份共享bootstrap；results/tree_depth.csv、bootstrap_tree_roots.csv
备注：本研究未评价锁定测试集；结论限于当前数据和验证协议。

## 05. 平均降低方差，但相关性决定收益下限（约40秒）

从341条记录有放回抽341次，2000次模拟中独特比例平均0.6321，OOB平均0.3679。有限n的理论是1减去(1减1/n)的n次方，63.2%和36.8%只是大样本期望。聚合公式要求等方差、相同两两相关，B增大只能压低第二项，相关项保留。这里的ρ指固定输入在训练扰动方向的相关性，不等于后面跨验证样本计算的树间错误相关。投票手算中B样本硬投票错，但平均概率0.4833预测正确。OOB只聚合未见该记录的树，不能替代外部验证。

证据来源：2000次、n=341；results/bootstrap_sampling.csv；投票题来自student-worksheet.md；[R1–R3]
备注：本研究未评价锁定测试集；结论限于当前数据和验证协议。

## 06. 共享五折：集成改善单树，LR仍保持竞争力（约50秒）

这是核心公平比较，所有模型采用相同五折与预设参数。LR AUC均值0.9942，SVM 0.9928，RF 0.9893，不限深度单树0.9267。树聚合改善了单树，未超过LR/SVM。表格也给出AP和BA，避免只报一个好看的排序指标。横线是折间样本SD，不是置信区间，不能把五折视作五个独立实验，也不据此宣称显著胜出。浅树和深树都保留，避免把基树深度变化当成聚合机制。

证据来源：开发集455条；共享五折；均值±折间样本SD（ddof=1，非CI）；results/cv_per_fold.csv；[S1,S2]
备注：本研究未评价锁定测试集；结论限于当前数据和验证协议。

## 07. 排序接近满分，不代表默认阈值没有错误（约40秒）

在341条拟合、114条固定验证上，LR和SVM的AUC都是1，但LR在0.5阈值有1个假阳性，SVM该阈值恰好全部正确。AUC衡量排序，阈值决定敏感度和特异度，二者不能互换。RF有2个假阴性，提醒我们具体选择要考虑漏诊代价，而不是只看AUC。这个验证集与开发CV共享样本，且用于机制分析，不是额外独立测试；这里的零漏诊或满分不代表总体性能确定。

证据来源：train341拟合 / validation114：阳性43、阴性71；统一p≥.5；results/validation_metrics.csv；测试未评价
备注：本研究未评价锁定测试集；结论限于当前数据和验证协议。

## 08. 加树收益很快趋缓；错误相关性未按假设下降（约45秒）

树数从1到10明显改善固定验证AUC，50到300之间差异很小，且没有单调上升。额外RF-all和RF-sqrt使用同一实现、相同bootstrap索引，隔离特征随机化。概率相关从0.821降至0.805，但二值错误相关从0.277变为0.280，并未下降。因此H2在错误同步性上没有得到支持；RF的训练扰动稳定性改善不能只用这一相关指标解释。这里相关性跨114条验证记录计算，受类别和难例影响，不直接是方差公式的ρ。

证据来源：train341 / validation114；单种子、无误差线；RF-all/sqrt共享抽样；100树、4950对；results/tree_count_curve.csv、tree_correlation_summary.csv
备注：本研究未评价锁定测试集；结论限于当前数据和验证协议。

## 09. Boosting持续降低训练损失，验证损失却会回升（约55秒）

AdaBoost和GB都是顺序依赖，但修正对象不同。AdaBoost的首轮真实加权错误0.0674，sklearn二类SAMME权重为2.627，错分者未归一化权重乘13.83，再整体归一化。GB在logit空间拟合y减p的负梯度，并作叶节点更新。图中虚线训练、实线验证，在lr0.1时验证损失从50轮约0.0788到200轮约0.1133，而训练继续下降。曲线只是探索，没有修改主GB的0.1和100轮，不能把审阅后的最优点称独立验证。

证据来源：train341 / validation114；lr=.03/.1/.3各200轮；虚线训练、实线验证；results/boosting_curves.csv；[R4–R7,S1]
备注：本研究未评价锁定测试集；结论限于当前数据和验证协议。

## 10. 共享训练扰动下，树聚合减少了预测类别翻转（约55秒）

每个模型用同一30份训练bootstrap，种子固定，验证114条固定。左边是每条验证记录在30次重拟合中的概率SD，再跨114条画箱线。右边更直接：31条记录在单树中曾出现两种类别，Bagging是17条，RF是9条，即27.2%、14.9%和7.9%。这里翻转不是错误率，而是30次中曾改变类别的记录比例；它依赖重拟合次数。概率尺度也不同，尤其AdaBoost输出压缩、SVM经校准，不能只靠概率SD跨模型下结论。

证据来源：相同30份train341 bootstrap；固定validation114；箱线=中位/IQR/1.5IQR、隐藏离群点，非CI；results/stability_predictions.csv
备注：本研究未评价锁定测试集；结论限于当前数据和验证协议。

## 11. 配对区间支持比较当前模型，覆盖不了换人群（约45秒）

这里换了bootstrap的对象：模型已经固定，不再重训，只在验证索引上按类别分层配对重抽样2000次。RF减单树的AUC差值是+0.0298 [+0.0057, +0.0631]，RF减LR是-0.0029 [-0.0092, +0.0000]。配对保留了同一记录上两个模型的关联。该区间条件于当前模型、验证经验分布和类别数量，不包含重训、选模型或跨机构迁移。LR验证AUC为1使经验区间可能退化，这是有限经验样本的限制，不是性能已确定。CV折间SD也不能替代这个条件区间或外部验证。

证据来源：固定train模型；validation114按类分层配对bootstrap2000次；线=百分位95%条件区间；results/paired_differences.csv
备注：本研究未评价锁定测试集；结论限于当前数据和验证协议。

## 12. 相关特征能互相替代，单变量重要性会误导（约50秒）

比较同一主RF100模型的两类重要性。MDI记录训练时不纯度下降，置换重要性记录固定验证AUC下降，误差线只是20次置换SD。训练集中435个特征对有21对绝对相关大于0.9，尺寸特征尤其冗余。单独置换worst radius、perimeter、area的下降很小甚至为负，但将这三者用同一排列联合置换，AUC平均下降0.120。这提示模型对相关变量组合的依赖，不表示其因果效应；置换也可能破坏与组外变量的联合分布，不能把组重要性解读成因果贡献。

证据来源：RF100：train341 MDI / Pearson；validation114、20次置换；误差线=置换SD非CI；results/feature_importance.csv、grouped_permutation.csv；[S4]
备注：本研究未评价锁定测试集；结论限于当前数据和验证协议。

## 13. 性能之外，训练与解释成本也要付账（约35秒）

同机单线程计时中，LR每折约4.0毫秒，SVM含校准约23.6毫秒，RF约99.9毫秒，Bagging约303.4毫秒。绝对成本在这份小数据上都不高，但没有性能增益时，额外复杂度仍需理由。LR系数易审阅，相关特征却会影响解释；RF拥有数千节点，通常要额外置换或局部解释。解释成本是定性判断，没有虚构人工计时。wall time受环境影响，不能推广成通用硬件基准。

证据来源：开发集共享五折、单线程wall time；SVM含三折校准；节点数来自固定train模型；results/cv_per_fold.csv、validation_metrics.csv
备注：本研究未评价锁定测试集；结论限于当前数据和验证协议。

## 14. 当前优先保留LR，SVM和RF作为候选参照（约40秒）

综合证据后，我们优先保留LR：主CV表现高、训练快，预测扰动也低。SVM保留为非线性性能参照；RF相比单树明显更稳定，可作为非线性候选，但在当前主比较中没有超过简单基线。H1获得描述性支持，H2在错误相关性上未获得支持，H3呈现树数平台和验证损失回升，H4支持有条件保留简单模型。会改变建议的证据是预先锁定阈值后，在独立多中心或时间外数据上，RF持续减少漏诊且校准、净获益更好。不能因为眼前验证满分直接部署。

证据来源：综合results/cv_summary.csv、stability_summary.csv、fit_times.csv；模型建议仅限当前数据和协议
备注：本研究未评价锁定测试集；结论限于当前数据和验证协议。

## 15. 当前证据没有覆盖临床部署与外部人群（约35秒）

研究限制包括：单一小样本历史数据、近似可分和性能天花板；缺少患者分组、时间及机构信息，不能核验患者独立性；固定验证还参与了机制探索；概率没有统一校准，未按漏诊代价选择阈值；锁定测试尚未评价。后续应先锁定候选和临床代价、校准与净获益指标，再一次性测试，最后开展独立人群验证。CTG可以作为方法对照，但必须按recording_id分组划分和重抽样，普通按行OOB可能偏乐观；它不是WDBC模型的外部验证。

证据来源：data/README.md、data-ctg/README.md；本次仅WDBC；锁定测试集尚未评价
备注：本研究未评价锁定测试集；结论限于当前数据和验证协议。

## 16. 选择模型，要同时回答三个问题（约25秒）

回到三个问题。第一，集成主要改善了同深度单树的排序表现和训练扰动稳定性，但不保证超过LR或SVM。第二，平均和训练多样性解释部分收益，不过错误相关性并未按预期下降，机制证据要区分统计方向。第三，在本数据和预设协议下，没有足够理由仅因模型更复杂就替代LR。我们交付了可复现实验、原始结果、图稿、报告和讲稿；所有结论都限定在当前验证范围，锁定测试集尚未评价。

证据来源：完整复现：RUN_RESEARCH.md；报告outputs/report.md；全部结果outputs/results/；[D1,R1–R7,S1–S6]
备注：本研究未评价锁定测试集；结论限于当前数据和验证协议。

## 17. 备份：固定验证的完整指标（备份）

这里保留所有八个模型的AP、BA、敏感度、特异度与混淆矩阵，方便课堂追问。所有数值来自同一validation_metrics.csv，恶性为阳性，统一概率0.5阈值，SVM已在训练内部校准。AP不是梯形PR面积。请不要把这个固定验证表当成锁定测试结果。

证据来源：train341 / validation114；p≥.5；CM按TN/FP/FN/TP顺序；AP=ΣΔRecall×Precision；results/validation_metrics.csv
备注：本研究未评价锁定测试集；结论限于当前数据和验证协议。

## 18. 备份：稳定性定义与参数（备份）

any-flip是30次中出现两种类别的验证记录比例，pair disagreement是随机选两个不同重拟合模型时类别不一致概率，概率SD使用ddof1。所有模型共享训练bootstrap，SVM校准按原记录ID分组。主参数为LR和SVM的C1，浅树depth2，单树及Bagging/RF基树不限深度，100棵Bagging/RF，Ada50树桩lr1，GB100深度3lr0.1。完整默认参数、版本和哈希见run_info.json。

证据来源：seed1010；训练bootstrap1012；N=30；results/run_info.json、stability_summary.csv
备注：本研究未评价锁定测试集；结论限于当前数据和验证协议。

## 19. 备份：Bagging、Boosting与常用实现（备份）

Bagging的基树可独立训练，主要平均高方差；Boosting逐阶段依赖，Ada改变权重，GB拟合负梯度。XGBoost的经典贡献包括正则目标、二阶近似和稀疏感知计算；LightGBM经典论文包括GOSS、EFB和高效直方图方案。它们仍属于梯度提升树框架，不能承诺在所有数据上更准确。我们只做文献对照，没有运行XGBoost或LightGBM，也没有给它们编造实验数字。工作单A到H包含更完整的手算和对照表。

证据来源：[R2–R7,S1,S5,S6]；仅文献对照，未运行XGBoost/LightGBM
备注：本研究未评价锁定测试集；结论限于当前数据和验证协议。

## 20. 备份：数据、论文与软件文档（备份）

完整可核验引用和链接如下，公开网页访问状态保存于reference_checks.json。HTTP核验只访问文献和文档，不下载数据集或恢复锁定标签。

[D1] Wolberg, Street & Mangasarian. Breast Cancer Wisconsin (Diagnostic). UCI (1995). DOI:10.24432/C5DW2B.
https://archive.ics.uci.edu/dataset/17/breast+cancer+wisconsin+diagnostic
[R1] Efron B. Bootstrap Methods: Another Look at the Jackknife. Annals of Statistics 7(1):1–26 (1979). DOI:10.1214/aos/1176344552.
https://doi.org/10.1214/aos/1176344552
[R2] Breiman L. Bagging Predictors. Machine Learning 24:123–140 (1996). DOI:10.1007/BF00058655.
https://doi.org/10.1007/BF00058655
[R3] Breiman L. Random Forests. Machine Learning 45:5–32 (2001). DOI:10.1023/A:1010933404324.
https://doi.org/10.1023/A:1010933404324
[R4] Freund Y, Schapire RE. A Decision-Theoretic Generalization of On-Line Learning and an Application to Boosting. JCSS 55(1):119–139 (1997). DOI:10.1006/jcss.1997.1504.
https://doi.org/10.1006/jcss.1997.1504
[R5] Friedman JH. Greedy Function Approximation: A Gradient Boosting Machine. Annals of Statistics 29(5):1189–1232 (2001). DOI:10.1214/aos/1013203451.
https://doi.org/10.1214/aos/1013203451
[R6] Chen T, Guestrin C. XGBoost: A Scalable Tree Boosting System. KDD (2016):785–794. DOI:10.1145/2939672.2939785.
https://arxiv.org/abs/1603.02754
[R7] Ke G et al. LightGBM: A Highly Efficient Gradient Boosting Decision Tree. NeurIPS 30 (2017).
https://papers.nips.cc/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html
[S1] scikit-learn 1.7 User Guide: Ensemble methods.
https://scikit-learn.org/1.7/modules/ensemble.html
[S2] scikit-learn 1.7 API: average_precision_score (non-interpolated AP).
https://scikit-learn.org/1.7/modules/generated/sklearn.metrics.average_precision_score.html
[S3] scikit-learn 1.7 User Guide: Probability calibration.
https://scikit-learn.org/1.7/modules/calibration.html
[S4] scikit-learn 1.7 User Guide: Permutation feature importance.
https://scikit-learn.org/1.7/modules/permutation_importance.html
[S5] XGBoost official documentation: Introduction to Boosted Trees.
https://xgboost.readthedocs.io/en/stable/tutorials/model.html
[S6] LightGBM official documentation: Features.
https://lightgbm.readthedocs.io/en/stable/Features.html

证据来源：全部公开链接已检查；完整条目与URL见outputs/report.md、results/reference_checks.json
备注：本研究未评价锁定测试集；结论限于当前数据和验证协议。
