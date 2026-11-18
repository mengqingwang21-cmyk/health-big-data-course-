"""Create the research report and fully answered worksheet from saved CSV results."""
import json
from research_style import *
from verify_sources import REFERENCES

def pct(x):return f'{100*x:.1f}%'
def f4(x):return f'{x:.4f}'

class Study:
    def __init__(self):
        self.cv=read('cv_summary').set_index('model').loc[ORDER]
        self.val=read('validation_metrics').set_index('model').loc[ORDER]
        self.st=read('stability_summary').set_index('model').loc[ORDER]
        self.dif=read('paired_differences')
        self.info=json.loads((RES/'run_info.json').read_text(encoding='utf-8'))
    def cvstr(self,n,metric='roc_auc'):
        r=self.cv.loc[n];return f'{r[metric+"_mean"]:.4f} ± {r[metric+"_sd"]:.4f}'
    def interval(self,a,b,metric='roc_auc'):
        r=self.dif[(self.dif.model_a==a)&(self.dif.model_b==b)&(self.dif.metric==metric)].iloc[0]
        return f'{r.point:+.4f} [{r.low:+.4f}, {r.high:+.4f}]'
    def main_table(self):
        return pd.DataFrame([{'模型':LABEL[n],'CV AUC均值±SD':self.cvstr(n),'CV AP':f4(self.cv.loc[n,'average_precision_mean']),
                              'CV BA':f4(self.cv.loc[n,'balanced_accuracy_mean']),'验证AUC':f4(self.val.loc[n,'roc_auc']),
                              '验证AP':f4(self.val.loc[n,'average_precision']),
                              '验证BA':f4(self.val.loc[n,'balanced_accuracy'])} for n in ORDER])

def make_memo(s):
    memo=(f'在WDBC现有划分和预设参数下，我优先保留逻辑回归，RBF-SVM作为性能参照，随机森林作为非线性候选。'
          f'开发集五折AUC中，LR为{s.cv.loc["logistic","roc_auc_mean"]:.4f}，RF为{s.cv.loc["random_forest","roc_auc_mean"]:.4f}；'
          f'RF改善了同深度单树，但未证明复杂模型必然优于简单基线。'
          f'共享30份训练重抽样后，单树与RF的类别翻转样本比例分别为{pct(s.st.loc["single_tree","any_flip_fraction"])}和{pct(s.st.loc["random_forest","any_flip_fraction"])}，支持聚合降低扰动。'
          'LR系数易审阅，但相关变量会影响系数解释；RF需额外置换分析，训练和解释成本更高。'
          '概率波动依赖模型尺度，验证差值区间只条件于当前模型与样本，折间SD不是显著性证据。'
          '目前锁定测试集尚未评价，缺少患者分组、时间信息和外部队列；重要性不代表因果，当前良恶性分类不是未来风险。'
          '若预先锁定的独立多中心验证显示RF在临床阈值下稳定减少漏诊，且校准与净获益改善，我会改变选择。')
    assert 250<=len(memo)<=400,(len(memo),memo)
    return memo

def run():
    s=Study();cv,val,st=s.cv,s.val,s.st
    audit=read('dataset_audit');depth=read('tree_depth');roots=read('bootstrap_tree_roots')
    sim=read('bootstrap_sampling');large=sim[sim.n==341]
    tc=read('tree_count_curve');co=read('tree_correlation_summary');imp=read('feature_importance')
    ctrl=co.set_index(['model','kind'])
    mechanism_result=(f'本次同实现RF-all→RF-sqrt的概率相关从'
                      f'{ctrl.loc[("rf_all_features","probability"),"mean_correlation"]:.3f}降至'
                      f'{ctrl.loc[("random_forest","probability"),"mean_correlation"]:.3f}；'
                      f'但二值错误相关从{ctrl.loc[("rf_all_features","binary_error"),"mean_correlation"]:.3f}变为'
                      f'{ctrl.loc[("random_forest","binary_error"),"mean_correlation"]:.3f}，没有下降，'
                      '因此H2在错误同步性上未得到支持。不能用“RF必然降低错误相关”解释本次所有收益。')
    high=read('correlated_feature_pairs');nhigh=int((high.pearson_r.abs()>.9).sum())
    memo=make_memo(s)
    importance=imp.sort_values('mdi',ascending=False).head(8)
    perm=imp.sort_values('permutation_auc_drop_mean',ascending=False).head(8)
    valtable=val.reset_index()[['model','roc_auc','average_precision','balanced_accuracy','sensitivity','specificity','tn','fp','fn','tp']]
    valtable['model']=valtable.model.map(LABEL)
    stability=st.reset_index()[['model','mean_probability_sd','median_probability_sd','any_flip_fraction','n_any_flip','mean_pair_disagreement']]
    stability['model']=stability.model.map(LABEL)
    dif=s.dif[s.dif.metric=='roc_auc'].copy()
    dif['model_a']=dif.model_a.map(LABEL);dif['model_b']=dif.model_b.map(LABEL)
    refs='\n'.join(f'- [{code}] {citation} <{url}>' for code,citation,url in REFERENCES)
    comparison='''| 方面 | Bagging（含随机森林） | Boosting |
| --- | --- | --- |
| 训练方式 | 各基树可并行；最终平均概率 | 阶段顺序依赖；同一阶段内部可有工程并行 |
| 每轮数据或权重 | 独立有放回抽样；RF另随机化节点候选特征 | AdaBoost改变样本权重；GB在当前损失负梯度上拟合新树 |
| 基学习器 | 常用充分生长的深树；并非每棵都是“弱”分类器 | AdaBoost常用树桩；GB常用浅树，可调整复杂度 |
| 偏差与方差 | 主要降低不稳定基学习器的方差，未保证降低偏差 | 逐步修正函数，常降低偏差；也受方差和正则影响 |
| 噪声及轮数 | 更多树一般减少Monte Carlo波动并趋于平台；不保证每个验证指标单调 | Ada可能强调噪声；GB过多轮可能拟合噪声；需训练内部选择或早停 |
| 关键参数 | n_estimators、max_features、max_samples、max_depth、min_samples_leaf | learning_rate与n_estimators联动，max_depth、min_samples_leaf、subsample及损失 |
'''
    voting=pd.DataFrame([['A',1,1,.65,1],['B',0,1,(.2+.6+.65)/3,0],['C',1,1,(.35+.75+.8)/3,1],['D',0,0,(.15+.25+.7)/3,0]],
                         columns=['样本','真值','硬投票类别','软投票P(1)','软投票类别(>=.5)'])
    roots_table=roots.groupby('root_feature').agg(次数=('repeat','size'),阈值最小=('root_threshold','min'),阈值最大=('root_threshold','max')).reset_index()
    boosting=read('boosting_curves');curve_end=boosting[boosting.stage.isin([50,100,200])].copy()
    curve_end.to_csv(RES/'boosting_selected_stages.csv',index=False,encoding='utf-8-sig')
    ada=read('adaboost_weight_rounds')
    alternatives='''XGBoost与LightGBM都是梯度提升树系统，并非与GB完全不同的学习范式。XGBoost的经典工作使用带树复杂度惩罚的目标、二阶梯度近似、采样和稀疏感知计算；LightGBM的经典论文提出GOSS和EFB，并以直方图、按叶生长等工程策略提高效率。经典sklearn GradientBoosting逐阶段拟合负梯度并进行损失相关叶节点更新。不能把XGBoost/LightGBM概括为“一定更准”，也不把所有版本和模式的缺失值、类别支持混为一谈。本次未安装或运行二者，不给出虚构实验排名。[R5–R7,S1,S5,S6]'''
    worksheet=f'''# 工作单 A—H：完成稿

题目：集成学习何时值得？生物医学分类中的性能、稳定性与复杂度权衡。

姓名/小组：未提供，留待填写。运行时间：{s.info['started_at']}。主数据WDBC，malignant=1。所有表格来自本次实际CSV；教师参考材料中的数字不作为结果。

## 数据与验证协议

一行是一条乳腺肿块细针穿刺图像的细胞核形态汇总记录，不是一颗细胞或可追踪的患者。30个预测特征为10类形态量的mean、standard error、worst汇总；sample_id只用于追踪，潜在的recording_id仅用于分组，均不进入输入。恶性标签是当前诊断分类，不是未来患病概率。

train用于拟合，validation用于固定划分分析；开发集train+validation共享五折CV是主比较，检验预设算法在开发样本内的迁移表现。CV与固定验证共享数据，不能称两次独立复制。测试集用于最后一次锁定评价，本次明确**锁定测试集尚未评价**。用户要求优先于workplan E8的揭示测试安排，未运行数据重建脚本，未打开teacher-reference.md，也未读取teacher/或原始数据源。

{md_table(audit)}

## A. 决策树

1. 课件第5页示例：worst perimeter=120 >105.95，走右支；mean concave points=.08 >.05，再走右支，进入“良3、恶112”的叶子，预测恶性，P(恶性)=112/(3+112)=0.9739。该数字是工作单引用的**教学示例计数**，不是本研究新增实验结果。叶概率是叶节点训练样本中恶性比例；若有权重则用加权比例，不能直接解释成经外部校准的患者风险。本次拟合树见example_tree_depth2.txt、example_tree_nodes.csv及图稿。
2. 每节点遍历候选特征和阈值，使父节点不纯度减去按子节点样本权重加权的不纯度最大。Gini=1−Σp_k²；二分类为2p(1−p)，纯节点为0，p=.5时最大。不纯度下降是局部贪心目标，不保证全局最优树。
3. 本次深度实验如下。训练准确率可随深度上升直至拟合全部训练记录，验证指标不保证单调；叶概率变化可能让AUC和准确率呈现不同趋势。浅树depth2用于可读规则，不限深度单树用于与集成基树对齐；不能把深度差异误认为集成收益。

{md_table(depth[['max_depth','split','leaves','accuracy','roc_auc','balanced_accuracy']])}

4. 相同30份bootstrap训练样本拟合depth2树后，根节点如下。同特征阈值也会改变，说明单树对训练扰动敏感；不同特征的阈值单位不同，不合并阈值范围。

{md_table(roots_table)}

5. 树的候选切分依赖特征大小次序，严格递增线性单位变换通常保留切分；数值并列/浮点可能产生细微差异。LR的正则化、SVM的距离和核宽度对尺度敏感，因此StandardScaler在Pipeline里、每训练折内拟合。不是“一切集成模型都不需要标准化”。

## B. 投票与方差

{md_table(voting)}

硬投票取类别众数；软投票先平均三个P(1)，再用.5阈值。B的硬投票错分，而软概率均值.4833落在正确类别0一侧。这是给定教学表的手算，不是WDBC实验。

对随机训练样本引起的固定输入x预测，若B个预测都具有相同方差σ²，且任意两模型相关系数相同ρ，则Var(平均预测)=ρσ²+(1−ρ)σ²/B。B趋于无穷时剩余ρσ²；ρ≈1时平均几乎没有收益。该简式要求相同边际方差与共同两两协方差，是可交换近似，不表示真实树完全等方差或等相关。一般形式为B⁻²Σ_iΣ_jCov(f_i,f_j)。它不直接给出AUC或分类错误率。

平均并不自动消除偏差；固定同分布基学习器时平均的期望仍等于单个预测的期望。深树常具有较低训练偏差、较高训练扰动方差，适合聚合；稳定LR的bagging收益往往较小，但不是数学上永远为零。验证样本方向的树间错误相关性只能作机制佐证，不等于该式训练扰动方向的ρ。

## C. Bootstrap

1. [2,2,5,1,2]中索引2出现3次，独特记录{{1,2,5}}占3/5，OOB为{{3,4}}占2/5。
2. 主模拟每次从341条抽341次、重复2000次：独特比例均值{large.unique_fraction.mean():.5f}、样本SD{large.unique_fraction.std(ddof=1):.5f}；OOB均值{large.oob_fraction.mean():.5f}。有限样本理论OOB=(1−1/n)^n={large.expected_oob.iloc[0]:.5f}，独特比例为其补数。极限e⁻¹≈36.8%及1−e⁻¹≈63.2%是期望规律，不是每次固定；n=5理论独特比例1−(.8)^5=.67232，不能强套63.2%。完整模拟见bootstrap_sampling.csv。
3. Bagging对训练记录独立有放回抽样，为各基树制造不同训练集；树彼此不依赖，可以并行，本次为可比计时统一单线程。
4. 对每条训练记录，仅汇总没有抽到它的树的概率，再对这些OOB预测计算指标；不是把每棵树OOB误差简单平均。OOB可在近似独立同分布条件下估计袋装模型内部表现，B不足时某些记录可能没有足够OOB预测；反复用OOB调参也产生选择偏差。它不能替代锁定测试、外部验证、校准检验或群体迁移评估。CTG按行OOB会混入同录音其他片段，可能偏乐观，需分组方法。本次CTG未运行。

## D. 单树、Bagging与随机森林

{md_table(pd.DataFrame([{'模型':LABEL[n],'验证AUC':val.loc[n,'roc_auc'],'验证BA':val.loc[n,'balanced_accuracy'],
                       '平均概率SD':st.loc[n,'mean_probability_sd'],'any-flip比例':st.loc[n,'any_flip_fraction']} for n in ['single_tree','bagging','random_forest']]))}

单树、Bagging基树和RF基树均不限深度；Bagging每节点全特征，RF每节点候选sqrt(30)（sklearn取整数5）。特征子抽样可阻止强特征在所有树根节点重复被选，减少同步错误，但会降低单树强度；结果取决于权衡。额外RF-all与RF-sqrt使用同一RF实现且本次bootstrap索引完全一致={s.info['rf_control_bootstrap_indices_identical']}，尽量隔离特征随机化。

{md_table(tc[['model','n_trees','validation_roc_auc','validation_balanced_accuracy','oob_accuracy','oob_roc_auc']])}

{md_table(co)}

相关性来自相同114条验证记录上的100棵树两两预测/残差/二值错误，恒定向量排除，n_pairs如表。样本中的容易/困难记录和类别结构也会影响相关性，因此不能据此证明ρ精确下降或把相关变化都归因于随机特征。增加树数减少有限B的Monte Carlo波动并趋于平台，不能宣称每个验证指标单调提高或“绝不会过拟合”。本次不根据最优曲线点重选树数，100棵仍是预设主模型。

{mechanism_result} 三组曲线从1→10棵改善明显，50→300棵趋于平台且验证AUC略有回落；这是单次探索，不把50棵宣称为已验证最优值。

不纯度重要性前列：{', '.join(importance.feature.head(5))}；置换前列：{', '.join(perm.feature.head(5))}。二者不必一致：MDI归因训练中实际分裂，偏好有更多分裂机会的变量；置换衡量当前模型和数据分布下打乱单变量的性能变化。train341中|r|>.9的特征对为{nhigh}/435，相关变量可分摊MDI、互相替代并稀释单变量置换。联合置换见grouped_permutation.csv，也仅是描述性敏感性分析。

## E. Boosting

1. 二类SAMME第t轮加权错误e_t，sklearn基学习器权重a_t=ηlog((1−e_t)/e_t)。错分记录的未归一化权重乘exp(a_t)，正确记录不变，再全体归一化。等价于经典±1记号下α_t=(η/2)log((1−e_t)/e_t)、w_i←w_i exp(−α_t y_i h_t(x_i))。提高错分权重令下一轮集中于之前未解释的样本，也可能过度关注噪声；不同于Bagging的独立同权重抽样。首轮真实加权错误={ada.iloc[0].weighted_error:.4f}，a={ada.iloc[0].estimator_weight:.4f}，错分未归一化倍数={ada.iloc[0].unnormalized_wrong_multiplier:.3f}。前8轮每条训练记录权重均已保存，并核对加权错误与sklearn一致。
2. 对logit F、p=sigmoid(F)，二类log-loss对F的负梯度为y−p，正确预测但概率不足的样本也贡献梯度；新树近似拟合残差方向，随后作损失相关叶节点更新并乘learning_rate。GB不是只找错分记录。保存的gradient_directions.csv追踪按sample_id预先排序取前6条、前5轮的p、y−p和log-odds更新。
3. lr=.03/.1/.3各200轮的训练/验证log-loss及AUC已完整保存。两者有联动：小学习率通常需要更多轮；训练损失改善不确保验证改善，过多轮可追随噪声。主Ada的lr=1/50轮、主GB的lr=.1/100轮均未改动。探索数据参与了曲线审阅，不是调参后独立验证；若要据此选参数，后续用嵌套CV或独立的内层早停集合，再对外层评价。
   具体观察：GB lr=.1的验证log-loss从50轮0.0788升到200轮0.1133，尽管训练损失继续下降；lr=.3时50轮0.1086到200轮0.1588。这些值由boosting_curves.csv四舍五入而来，支持本次H3的非单调验证预期。
4. {alternatives}

## F. 公平比较

{md_table(s.main_table())}

{md_table(valtable)}

ROC-AUC评价排序；AP=Σ_k(R_k−R_{{k−1}})P_k，使用sklearn average_precision_score，不是梯形插值PR-AUC；AP对阳性率敏感。BA=(敏感度+特异度)/2。概率阈值统一>=.5；SVM为训练内部三折sigmoid校准版本，ensemble=False后在当前全部训练部分拟合最终SVC，校准折内也独立标准化。主模型不调参数、不调阈值。SVM margin未作为概率计算log-loss。

本次LR CV AUC={s.cvstr('logistic')}，SVM={s.cvstr('rbf_svm')}，RF={s.cvstr('random_forest')}。应报告数值差异与折间波动，但不能把“差距小于某个SD”当正式检验，也不能用互相关联的五折结果当五个独立重复。集成相对于同深度单树的改善不能直接外推为胜过LR/SVM。当前保留LR与SVM性能基线，RF作为非线性候选；LR在成本和参数审阅方面有优势，但系数也受相关性及建模假设限制，不能写作因果效应。

## G. 稳定性与不确定性

每个模型用完全相同的30份训练bootstrap；算法种子不变，114条验证记录不变。SVM校准内按原训练记录索引分组，避免重复抽中的同一记录跨校准折。

{md_table(stability)}

逐样本概率SD按30次概率以ddof=1计算，表中为114条的平均/中位。any-flip=114⁻¹Σ_j I(0<q_j<1)，q_j为30次中预测恶性的比例，即至少出现过两种类别的样本比例，不是“30次所有预测的错误率”，也不是相对原模型的一次翻转概率。另报pair disagreement=平均[2n_1n_0/(R(R−1))]，即随机选两个不同重拟合模型时预测类别不一致的经验概率；modal disagreement=平均min(q,1−q)。any-flip依赖R，故各模型必须共享R=30。

概率SD的跨模型比较要谨慎：AdaBoost概率可能压缩，SVM进行了sigmoid校准而其他模型未统一校准；较小概率SD可能只是尺度效应。结合类别翻转和主性能共同判断，不能称为“患者风险置信区间”。固定train变10个算法种子的补充见algorithm_seed_stability.csv，描述不同于训练样本扰动的随机来源。

主要固定模型验证AUC差值：

{md_table(dif[['model_a','model_b','point','low','high']])}

区间由固定train模型在validation内按类别分层、成对bootstrap2000次的2.5%/97.5%百分位得到。每个重抽样索引用于所有模型，类别数量固定；差值区间利用配对，不能用两个单模型区间简单相减。它们条件于已拟合模型、当前验证经验分布和类别数量，未包括训练变化、反复模型选择或外部人群变化；接近满分时经验bootstrap也可能给出退化区间，不能表示总体性能确定。固定验证已用于机制探索，区间不是选模后无偏推断，不宣告多重比较显著性。五折SD仅描述折间变动，不是CI或显著性证据。

| 证据 | 回答 | 不覆盖 |
| --- | --- | --- |
| 训练bootstrap重拟合 | 当前训练经验分布扰动时预测变化 | 外部人群与固定模型指标CI |
| 固定模型验证bootstrap | 当前模型在验证经验分布下的指标及配对差值变化 | 重训、选模、类别比例迁移 |
| 外部独立人群验证 | 新人群/机构/时间上的适用性 | 本次没有这类证据 |

## H. 解释、选择与备忘录

{comparison}

### 研究备忘录（{len(memo)}字符，含标点）

{memo}

## 图表、参数与来源

所有完整精度CSV在results/；图稿PNG/SVG/PDF在figures/；运行协议protocol.md、模型参数/版本/数据哈希run_info.json、依赖pip_freeze.txt。正式汇报和逐页讲稿在presentation/。所有运行结果来自本次脚本；例题树计数和投票表明确为课程手算来源，不混入实验表。

{refs}
'''
    (OUT/'worksheet_completed.md').write_text(worksheet,encoding='utf-8')
    notes_checks=''
    if (RES/'reference_checks.json').exists():
        checks=json.loads((RES/'reference_checks.json').read_text(encoding='utf-8'))
        notes_checks='\n'.join(f'- {r["id"]}: HTTP {r.get("http_status","未获取")}；{r["status"]}。' for r in checks)
    report=f'''# 集成学习何时值得？生物医学分类中的性能、稳定性与复杂度权衡

## 摘要

在保留WDBC课程原始划分、恶性=1的条件下，对8个预设模型开展开发集共享五折比较，并以固定验证集分析机制与稳定性。LR、RBF-SVM、深树、Bagging和RF的CV AUC分别为{cv.loc['logistic','roc_auc_mean']:.4f}、{cv.loc['rbf_svm','roc_auc_mean']:.4f}、{cv.loc['single_tree','roc_auc_mean']:.4f}、{cv.loc['bagging','roc_auc_mean']:.4f}和{cv.loc['random_forest','roc_auc_mean']:.4f}。30份共享训练重抽样下，深树/Bagging/RF的any-flip比例为{pct(st.loc['single_tree','any_flip_fraction'])}/{pct(st.loc['bagging','any_flip_fraction'])}/{pct(st.loc['random_forest','any_flip_fraction'])}。结果支持考察集成的降波动收益，同时不支持预设复杂模型必然替代简单基线。贡献是可复现实证比较和机制分析，不提出新算法。**锁定测试集尚未评价。**

## 1. 研究问题与运行前假设

RQ1：集成相较同深度单树改善哪些表现？RQ2：训练扰动下是否更稳定，抽样/相关性的证据是什么？RQ3：综合表现、计算、稳定性与解释成本，复杂模型是否值得？

运行前已将H1–H4、参数、阈值、种子、主次分析写入[protocol.md](protocol.md)，本地时间在run_info.json中；这不是公共预注册。H1预期Bagging/RF优于同深度单树且更稳；H2预期sqrt随机化降低同步错误，但可能因相关冗余而收益有限；H3预期树数边际递减、Boosting训练改善不保证验证改善；H4允许简单基线综合占优。未使用教师参考数字作为实验结果。

## 2. 数据、验证与指标

数据来源UCI WDBC，DOI:10.24432/C5DW2B，课程CSV由sklearn版本载入数据离线制备。一行是细针穿刺图像形态汇总，不是未来风险。仅打开student/train.csv、validation.csv，未调用完整数据加载器，未运行prepare_data，未访问teacher目录或锁定测试特征。源文档写明全量569及锁定114；本次数据审计只针对455条开放标签记录。

{md_table(audit)}

保留原train341、validation114；主结果是455条开发集共享五折分层CV；固定验证用于机制、混淆矩阵、解释及bootstrap区间。开发CV与固定验证共享样本，因此并非独立复制。CV训练规模364，与固定train341不同，且CV验证折可包含原train和原validation；两类结果回答相近但不相同的条件问题，不拼接成测试结论。数据缺乏患者ID及时间，无法核验患者独立性；逐行分层和bootstrap依赖记录近似独立的假设。

LR标准化在Pipeline内；SVM的校准器包裹完整标准化+SVC Pipeline，在当前训练部分内部三折校准、ensemble=False；训练bootstrap中的重复原记录按组留在同一校准折。SVM排序来自sigmoid后的predict_proba，非把margin当概率；其单调性保持同一最终SVC的排序。

主指标ROC-AUC；AP=ΣΔRecall×Precision，使用非插值average_precision_score，不是梯形PR面积；BA、敏感度、特异度及混淆矩阵均报告，malignant为阳性。分类阈值预设概率>=.5，未经验证优化；漏诊成本没有单独建模。所有模型的概率未统一校准，log-loss和概率SD需连同概率尺度局限解释。

## 3. 预设方法与主要结果

完整参数见results/run_info.json。浅树depth2用于解释；主单树和Bagging/RF基树均不限深度，隔离深度混杂。Bagging100全特征；RF100每节点sqrt；Ada50树桩lr1（SAMME）；GB100深度3、lr.1；LR与SVM均C1。主比较不根据探索曲线改参数。

{md_table(s.main_table())}

CV为均值±折间样本SD（ddof=1），不是置信区间。验证数值来自341拟合、114评价；未评价锁定测试。主要完整阈值结果：

{md_table(valtable)}

![开发集主比较](figures/performance_cv.png)

相对深树，集成的改善应在同深度条件下判断；LR/SVM已具有很高排序性能，集成的额外复杂度需要另外证明收益。排名差异不能仅用折间SD或五折平均的大小宣布显著性。

## 4. 机制消融

深度实验包含1/2/3/4/不限；训练指标与验证指标不单调一致。30份bootstrap的根特征/阈值变化提供单树不稳定的结构证据。2000次n=341抽样独特比例均值{large.unique_fraction.mean():.5f}，OOB均值{large.oob_fraction.mean():.5f}，与有限n期望一致。63.2%是训练记录被至少抽中一次的期望，不是只抽63.2%次。

![树深](figures/tree_depth.png)
![根变化](figures/root_variation.png)
![Bootstrap](figures/bootstrap_sampling.png)

树数1/10/50/100/300的比较和RF-all/sqrt对照见下图。RF两组同实现且bootstrap索引完全相同={s.info['rf_control_bootstrap_indices_identical']}；Bagging与RF之间仍有实现细节。树数曲线为单固定种子，无误差线，不据此挑选主模型。100棵树错误相关性来自验证记录方向、排除了恒定错误向量，不直接等于Var公式的训练扰动ρ。

{md_table(co[co.kind=='binary_error'])}

{mechanism_result}

![树数与错误相关](figures/tree_count_mechanism.png)

方差公式ρσ²+(1−ρ)σ²/B假设同方差、等两两相关；一般形式为B⁻²ΣCov。B增加仅缩小有限平均项，相关残差构成下界。公式不保证偏差、AUC或阈值错误同步改善。

## 5. Boosting探索及算法对照

AdaBoost按当前加权错误提高错分记录权重；真实首轮e={ada.iloc[0].weighted_error:.4f}，SAMME权重a={ada.iloc[0].estimator_weight:.4f}。GB在logit空间拟合y−p负梯度，随后更新叶值与函数，样本不必错分也会有非零残差。完整权重和梯度诊断已保存。

![Boosting曲线](figures/boosting_curves.png)

lr=.03/.1/.3各200轮的曲线是探索，不是独立调参结果；主Ada lr1/50和GB lr.1/100不变。训练损失下降不能保证验证性能改善，需通过内层CV/早停控制轮数。若未来采纳曲线最优设置，必须嵌套CV或另留独立评价并报告选择偏差。

本次GB lr=.1在50/100/200轮的验证log-loss为0.0788/0.0903/0.1133；lr=.3为0.1086/0.1137/0.1588，训练损失仍下降。H3的验证回升现象在当前固定曲线上可见，不能因此进行调参后的独立性能宣称。

{alternatives}

## 6. 训练稳定性与固定模型条件区间

{md_table(stability)}

![稳定性](figures/training_stability.png)

同一30份训练bootstrap，模型随机种子固定；概率SD是逐样本30次预测的样本SD，箱线图跨114个验证样本；any-flip为30次出现过两类的样本比例，随重复次数改变。pair disagreement为两个不同重拟合模型的类别不一致概率，提供不依赖“是否曾翻过”的补充。SVM有校准、AdaBoost输出压缩，低概率SD不能单独证明更可靠；类别稳定性和预测性能必须同时看。算法种子10次补充结果在algorithm_seed_stability.csv。

{md_table(dif[['model_a','model_b','point','low','high']])}

![条件区间](figures/paired_intervals.png)

固定模型在validation114中按类别分层配对bootstrap2000次，百分位95%区间。区间条件于当前已拟合模型、验证经验分布与类别数量，不包含重训、选模、外部人群变化；验证数据也用于探索，不是对选出赢家的无偏推断。满分AUC的经验bootstrap可能退化，不能视为总体性能已知。未作多重比较显著性声明，CV折间SD也不作为显著性证据。

## 7. 解释、计算与模型选择

![特征解释](figures/importance_comparison.png)

train341中|r|>.9有{nhigh}/435对。MDI在相关替代变量间分摊，单特征置换也会因替代预测而很小或为负；置换20次误差线只反映置换随机性。组置换提供相关尺寸变量共同依赖的敏感性证据，亦不识别因果。LR标准化系数也不能在共线性下简单当作独立效应。

![表现与训练成本](figures/performance_cost.png)

计时是本机、单线程、wall time，CV每折记录；SVM含三折校准。它受硬件、缓存和调度影响，不是普适速度基准。模型节点数及固定验证预测耗时见validation_metrics.csv。LR系数可直接审阅；浅树规则最直观但性能/稳定性有限；SVM需要支持向量、尺度和校准解释；Bagging/RF/Boosting需要额外全局和局部解释分析。解释成本为定性判断，未虚构人工计时或临床可用性分数。

{memo}

{comparison}

## 8. 局限与下一步

小样本、单一历史数据，近似可分且高度相关，性能存在天花板；没有患者分组、时间或机构信息；未做嵌套调参、临床阈值优化、全面概率校准和外部评价。外部人群泛化不确定性无法由本次bootstrap回答。下一步先锁定候选、临床漏诊成本、阈值及校准评价，再安排一次锁定测试，随后用独立多中心/时间外队列检查敏感度、校准、净获益及亚组公平性。CTG可作为独立方法对照，但必须按recording_id划分和重抽样；不称其为WDBC模型的外部验证。本次未开展CTG扩展。

## 9. 复现与审计

运行环境及全量依赖：results/run_info.json、pip_freeze.txt。开始{s.info['started_at']}，结束{s.info['finished_at']}，核心实验wall time {s.info['total_wall_seconds']:.1f}秒。模型/折种子1010，模拟1011，训练bootstrap1012，配对bootstrap1013，置换1014。文件哈希、全部参数、CV分配、两种bootstrap索引、每折指标、预测、机制结果和joblib模型均保存。执行说明见项目RUN_RESEARCH.md；原数据及课程课件保留。

## 参考文献与可访问性

{refs}

链接检查只检查公开网页，不下载数据集；HTTP访问限制与书目真实性分别记录，不把403称为文献不存在。检查记录：

{notes_checks}
'''
    (OUT/'report.md').write_text(report,encoding='utf-8')
    (RES/'research_memo.json').write_text(json.dumps({'characters_including_punctuation':len(memo),'text':memo},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Generated report + completed worksheet; memo characters:',len(memo))

if __name__=='__main__':run()
