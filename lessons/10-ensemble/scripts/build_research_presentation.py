"""Editable 16:9 academic deck: 16 main slides + 4 backup slides, with speaker notes.

Text, tables, diagrams and the main performance plot are native PowerPoint objects.
Scientific figure sources are separately available as PNG/SVG/PDF and Python code.
"""
from pathlib import Path
import json
import math
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.oxml.xmlchemy import OxmlElement
from PIL import Image
from research_style import *
from make_report import Study, pct, f4
from verify_sources import REFERENCES
from make_slide_figures import run as slide_figures

W,H=13.333333,7.5
FONT='Microsoft YaHei'
SHORT={'logistic':'LR','rbf_svm':'RBF-SVM','tree_shallow':'Tree-2','single_tree':'Tree-full',
       'bagging':'Bagging','random_forest':'RF-sqrt','adaboost':'AdaBoost','gradient_boosting':'GB'}
prs=Presentation();prs.slide_width=Inches(W);prs.slide_height=Inches(H)
prs.core_properties.title='集成学习何时值得？生物医学分类中的性能、稳定性与复杂度权衡'
prs.core_properties.subject='WDBC empirical ensemble study; locked test not evaluated'
prs.core_properties.author='机器学习课程研究汇报'
SLIDES=[]
AUDIT=[]

def rgb(color):return RGBColor.from_string(color.lstrip('#'))

def set_font(run,size=20,color=INK,bold=False):
    run.font.name=FONT;run.font.size=Pt(size);run.font.bold=bold;run.font.color.rgb=rgb(color)
    rpr=run._r.get_or_add_rPr();rpr.set('lang','zh-CN')
    for tag in ['a:ea','a:cs']:
        child=rpr.find('{http://schemas.openxmlformats.org/drawingml/2006/main}'+tag.split(':')[1])
        if child is None:child=OxmlElement(tag);rpr.append(child)
        child.set('typeface',FONT)

def text(s,content,x,y,w,h,size=20,color=INK,bold=False,align=PP_ALIGN.LEFT):
    sh=s.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));tf=sh.text_frame
    tf.clear();tf.word_wrap=True;tf.auto_size=MSO_AUTO_SIZE.NONE
    tf.margin_left=tf.margin_right=0;tf.margin_top=tf.margin_bottom=0
    for i,line in enumerate(str(content).split('\n')):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.alignment=align
        p.space_after=Pt(5);p.line_spacing=1.12
        r=p.add_run();r.text=line;set_font(r,size,color,bold)
    return sh

def rect(s,x,y,w,h,fill='#FFFFFF',line=None,rounded=False):
    sh=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h))
    sh.fill.solid();sh.fill.fore_color.rgb=rgb(fill)
    if line:sh.line.color.rgb=rgb(line);sh.line.width=Pt(.8)
    else:sh.line.fill.background()
    if rounded:
        try:sh.adjustments[0]=.08
        except (ValueError,IndexError):pass
    return sh

def line(s,x1,y1,x2,y2,color=TEAL,width=1.5):
    sh=s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,Inches(x1),Inches(y1),Inches(x2),Inches(y2));sh.line.color.rgb=rgb(color);sh.line.width=Pt(width)
    return sh

def box(s,head,body,x,y,w,h,color=TEAL,size=19):
    rect(s,x,y,w,h,fill='#EDF4F1',rounded=True)
    text(s,head,x+.2,y+.15,w-.4,.42,20,color,True)
    text(s,body,x+.2,y+.72,w-.4,h-.87,size)

def picture(s,name,x,y,w,h):
    path=FIG/(name+'.png')
    with Image.open(path) as im:iw,ih=im.size
    scale=min(w/iw,h/ih);pw,ph=iw*scale,ih*scale
    sh=s.shapes.add_picture(str(path),Inches(x+(w-pw)/2),Inches(y+(h-ph)/2),width=Inches(pw),height=Inches(ph))
    sh.name='Figure: '+name
    return sh

def table(s,rows,x,y,widths,row_h=.46,size=15):
    sh=s.shapes.add_table(len(rows),len(rows[0]),Inches(x),Inches(y),Inches(sum(widths)),Inches(row_h*len(rows)))
    t=sh.table
    for j,w in enumerate(widths):t.columns[j].width=Inches(w)
    for i,row in enumerate(rows):
        t.rows[i].height=Inches(row_h)
        for j,v in enumerate(row):
            cell=t.cell(i,j);cell.text=str(v);cell.vertical_anchor=MSO_ANCHOR.MIDDLE
            cell.margin_left=Inches(.09);cell.margin_right=Inches(.06);cell.margin_top=Inches(.025);cell.margin_bottom=Inches(.025)
            cell.fill.solid();cell.fill.fore_color.rgb=rgb(INK if i==0 else ('#EDF4F1' if i%2 else PAPER))
            for p in cell.text_frame.paragraphs:
                p.alignment=PP_ALIGN.LEFT if j==0 else PP_ALIGN.CENTER;p.space_after=Pt(0);p.line_spacing=1
                for r in p.runs:set_font(r,size,'#FFFFFF' if i==0 else INK,i==0)
    return sh

def slide(title,kicker,note,seconds=40,source='本次实验；锁定测试集尚未评价',backup=False):
    s=prs.slides.add_slide(prs.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=rgb(PAPER)
    text(s,kicker,.55,.25,12.2,.3,13,TEAL,True)
    text(s,title,.55,.85,12.2,.82,29,INK,True)
    line(s,.55,1.66,12.78,1.66,'#D8E1DE',1)
    text(s,source,.55,7.02,11.65,.26,10.5,MUTED)
    page=len(prs.slides);text(s,f'{page:02d}'+(' / 备份' if backup else ' / 16'),12.0,7.01,.78,.28,10.5,MUTED,align=PP_ALIGN.RIGHT)
    fullnote=note+'\n\n证据来源：'+source+'\n备注：本研究未评价锁定测试集；结论限于当前数据和验证协议。'
    s.notes_slide.notes_text_frame.text=fullnote
    SLIDES.append(dict(page=page,title=title,kicker=kicker,seconds=seconds,backup=backup,notes=fullnote))
    return s

def native_performance(s,study,x=.6,y=2.0,w=5.4,h=4.1):
    left=x+1.38;right=x+w-.1;top=y+.2;row=.43
    lo,hi=.88,1.008
    px=lambda v:left+(v-lo)/(hi-lo)*(right-left)
    for tick in [.90,.95,1.00]:
        line(s,px(tick),top-.06,px(tick),top+7*row+.18,'#D8E1DE',.8)
        text(s,f'{tick:.2f}',px(tick)-.18,top+7*row+.33,.5,.25,12,MUTED)
    for i,n in enumerate(ORDER):
        yy=top+i*row;mean=study.cv.loc[n,'roc_auc_mean'];sd=study.cv.loc[n,'roc_auc_sd']
        text(s,SHORT[n],x,yy-.12,1.3,.3,15,COLOR[n],True)
        line(s,px(mean-sd),yy+.04,px(mean+sd),yy+.04,COLOR[n],1.7)
        for z in [mean-sd,mean+sd]:line(s,px(z),yy-.025,px(z),yy+.105,COLOR[n],1.2)
        sh=s.shapes.add_shape(MSO_SHAPE.OVAL,Inches(px(mean)-.045),Inches(yy-.005),Inches(.09),Inches(.09));sh.fill.solid();sh.fill.fore_color.rgb=rgb(COLOR[n]);sh.line.fill.background()
    text(s,'ROC-AUC：折均值 ± 折间SD',x+1.1,top+7*row+.82,4.4,.35,15,MUTED)

def run():
    slide_figures()
    d=Study();cv,val,st=d.cv,d.val,d.st
    co=read('tree_correlation_summary').set_index(['model','kind'])
    sim=read('bootstrap_sampling').query('n == 341');ada=read('adaboost_weight_rounds').iloc[0]
    grouped=read('grouped_permutation').groupby('group').auc_drop.mean()
    corr=read('correlated_feature_pairs');n_high=int((corr.pearson_r.abs()>.9).sum())
    refs='\n'.join(f'[{c}] {citation}\n{url}' for c,citation,url in REFERENCES)
    # 1
    s=slide('集成学习何时值得？','实证研究 · WDBC 生物医学分类',
        f'今天关注性能、稳定性和复杂度的权衡。我们实际比较了八个预设模型，先固定协议，再运行实验。最主要的观察是：集成相较同深度单树改善了排序性能和训练扰动稳定性，但开发集CV中LR仍有竞争力。贡献是可复现实证与机制分析，不是新算法。接下来按三个研究问题说明证据和边界。',25,
        'WDBC [D1]；本次共享五折与重抽样实验')
    text(s,'生物医学分类中的\n性能、稳定性与复杂度权衡',.6,2.0,11.9,1.4,36,INK,True)
    text(s,'集成改善单树；简单基线仍有竞争力',.62,3.85,12,.7,28,TEAL,True)
    for i,(head,value) in enumerate([('共享五折','8 个模型'),('训练扰动','30 份共享重抽样'),('条件区间','2,000 次配对抽样')]):
        x=.62+i*4.17;rect(s,x,5.08,3.9,1.02,'#EDF4F1',rounded=True);text(s,head,x+.18,5.22,3.5,.3,15,MUTED);text(s,value,x+.18,5.6,3.5,.35,20,INK,True)
    text(s,'当前诊断分类；锁定测试集尚未评价',.62,6.45,12,.35,17,MUTED)
    # 2
    s=slide('先固定假设，再让实验决定结论','研究问题与假设',
        '三个问题分别问改善什么、为什么更稳、以及复杂度是否值得。H1预期Bagging和RF相对同深度单树改善性能并减少训练扰动。H2预期额外随机特征减少同步错误，但我们允许相关特征冗余使收益有限。H3预期加树边际递减，训练损失下降不保证验证下降。H4允许LR或SVM综合占优。这些判读规则和参数在首次运行前已保存，属于本地分析承诺，未声称公共预注册。',35,
        '运行前协议 outputs/protocol.md；预设参数、不调主模型')
    for i,(q,hyp) in enumerate([
        ('01  改善了什么？','H1：Bagging / RF相较同深度单树\n提升排序表现，并降低训练扰动。'),
        ('02  稳定来自哪里？','H2：特征随机化有望减少同步错误；\nH3：增加树数的收益逐渐变小。'),
        ('03  复杂模型值得吗？','H4：LR / SVM可能已足够；\n把表现、稳定性与成本一起比较。')]):
        box(s,q,hyp,.62+i*4.18,2.08,3.9,3.14,size=20)
    text(s,'允许假设不成立；不根据探索曲线重选主模型。',.7,5.78,11.9,.65,23,TEAL,True)
    # 3
    s=slide('共享五折是主比较，固定验证用于机制分析','数据与评价协议',
        '仅读取课程现成的341条训练和114条验证记录，恶性为1。30个连续特征，ID不进入模型。原划分保留：固定验证分析始终只用341条拟合。主比较另在455条开发数据上做共享五折，每个模型使用完全相同折索引。两种分析重叠，不能当两次独立复现。LR的Scaler在Pipeline里，SVM的校准器包裹Scaler与SVC，在每个训练内部三折做sigmoid校准。没有读锁定测试或teacher数据，缺少患者分组信息也作为限制记录。',50,
        'data/README.md [D1]；results/dataset_audit.csv、cv_assignments.csv；[S2,S3]')
    box(s,'原始训练','341 条：恶性127 / 良性214\n拟合与训练扰动重抽样',.65,2.05,5.7,1.65,size=19)
    box(s,'固定验证','114 条：恶性43 / 良性71\n机制、稳定性与解释',6.95,2.05,5.7,1.65,size=19)
    text(s,'开发集455条 → 共享五折分层CV（seed=1010）',.75,4.0,11.9,.45,23,TEAL,True)
    for i in range(5):
        rect(s,.78+i*2.43,4.68,2.22,.48,TEAL if i==0 else '#BBD6CF',rounded=True)
        text(s,f'Fold {i+1}',.78+i*2.43,4.78,2.22,.23,14,'#FFFFFF' if i==0 else INK,True,PP_ALIGN.CENTER)
    text(s,'主指标 ROC-AUC；AP = ΣΔRecall × Precision；分类阈值 p ≥ 0.5',.75,5.53,12,.45,20)
    text(s,'折内标准化 + SVM训练内校准；CV与固定验证共享样本。',.75,6.15,12,.4,19,MUTED)
    # 4
    s=slide('树越深训练越好，训练样本一变根节点也会变','单树诊断 · 工作单 A',
        '左图中训练准确率随深度增加到1，但固定验证准确率在depth3后没有继续提高。这说明拟合训练数据和获得可迁移表现不是一回事。右图来自相同30份训练bootstrap，各拟合depth2树，根节点出现多种特征，阈值也在同一特征内变化。结构变化给出不稳定的直观证据，后面还会用预测变化直接测量。公平机制对照采用不限深度单树，与Bagging和RF基树保持一致；浅树只承担可读示例角色。',40,
        'train341 / validation114；单种子深度曲线；30份共享bootstrap；results/tree_depth.csv、bootstrap_tree_roots.csv')
    text(s,'深度：训练准确率≠验证准确率',.65,1.93,6.1,.4,20,TEAL,True)
    text(s,'30次训练重抽样：根节点不固定',6.95,1.93,5.8,.4,20,TEAL,True)
    picture(s,'slide_depth',.5,2.48,6.25,3.65);picture(s,'slide_roots',6.85,2.48,5.95,3.65)
    text(s,'深树对照：不限深度；Bagging与RF的基树也不限深度。',.75,6.32,12,.4,21,INK,True)
    # 5
    s=slide('平均降低方差，但相关性决定收益下限','Bootstrap与聚合 · 工作单 B–C',
        f'从341条记录有放回抽341次，2000次模拟中独特比例平均{sim.unique_fraction.mean():.4f}，OOB平均{sim.oob_fraction.mean():.4f}。有限n的理论是1减去(1减1/n)的n次方，63.2%和36.8%只是大样本期望。聚合公式要求等方差、相同两两相关，B增大只能压低第二项，相关项保留。这里的ρ指固定输入在训练扰动方向的相关性，不等于后面跨验证样本计算的树间错误相关。投票手算中B样本硬投票错，但平均概率0.4833预测正确。OOB只聚合未见该记录的树，不能替代外部验证。',40,
        '2000次、n=341；results/bootstrap_sampling.csv；投票题来自student-worksheet.md；[R1–R3]')
    rect(s,.65,2.0,12.0,1.02,'#EDF4F1',rounded=True)
    text(s,'Var(平均预测) = ρσ² + (1 − ρ)σ² / B',.85,2.28,11.5,.55,31,TEAL,True)
    box(s,'更多模型 B','减少有限平均的波动；\nB趋大后仍剩ρσ²。',.65,3.42,3.78,1.86,size=20)
    box(s,'更低相关 ρ','需要不同训练扰动；\n同步错误无法被平均消除。',4.77,3.42,3.78,1.86,size=20)
    box(s,'实际抽样验证',f'独特比例 {pct(sim.unique_fraction.mean())}\nOOB比例 {pct(sim.oob_fraction.mean())}',8.9,3.42,3.78,1.86,size=20)
    text(s,'简化假设：各模型等方差、任意两模型等相关；不直接保证AUC改善。',.75,5.78,11.9,.48,19,MUTED)
    text(s,'投票例 B：硬投票 1（错）；软投票 (0.20+0.60+0.65)/3=0.4833 → 0。',.75,6.34,11.9,.4,17)
    # 6
    s=slide('共享五折：集成改善单树，LR仍保持竞争力','主结果 · 工作单 F',
        f'这是核心公平比较，所有模型采用相同五折与预设参数。LR AUC均值{cv.loc["logistic","roc_auc_mean"]:.4f}，SVM {cv.loc["rbf_svm","roc_auc_mean"]:.4f}，RF {cv.loc["random_forest","roc_auc_mean"]:.4f}，不限深度单树{cv.loc["single_tree","roc_auc_mean"]:.4f}。树聚合改善了单树，未超过LR/SVM。表格也给出AP和BA，避免只报一个好看的排序指标。横线是折间样本SD，不是置信区间，不能把五折视作五个独立实验，也不据此宣称显著胜出。浅树和深树都保留，避免把基树深度变化当成聚合机制。',50,
        '开发集455条；共享五折；均值±折间样本SD（ddof=1，非CI）；results/cv_per_fold.csv；[S1,S2]')
    native_performance(s,d)
    rows=[['模型','AUC 均值±SD','AP','BA']]
    rows += [[SHORT[n],d.cvstr(n),f4(cv.loc[n,'average_precision_mean']),f4(cv.loc[n,'balanced_accuracy_mean'])] for n in ORDER]
    table(s,rows,6.28,2.0,[1.30,2.28,1.10,1.10],row_h=.46,size=14)
    text(s,'参数预设；未用探索曲线改变主模型。',6.4,6.32,6.1,.35,17,TEAL,True)
    # 7
    s=slide('排序接近满分，不代表默认阈值没有错误','固定验证 · 互补指标',
        '在341条拟合、114条固定验证上，LR和SVM的AUC都是1，但LR在0.5阈值有1个假阳性，SVM该阈值恰好全部正确。AUC衡量排序，阈值决定敏感度和特异度，二者不能互换。RF有2个假阴性，提醒我们具体选择要考虑漏诊代价，而不是只看AUC。这个验证集与开发CV共享样本，且用于机制分析，不是额外独立测试；这里的零漏诊或满分不代表总体性能确定。',40,
        'train341拟合 / validation114：阳性43、阴性71；统一p≥.5；results/validation_metrics.csv；测试未评价')
    rows=[['模型','AUC','敏感度','特异度','TN','FP','FN','TP']]
    rows += [[SHORT[n],f4(val.loc[n,'roc_auc']),f4(val.loc[n,'sensitivity']),f4(val.loc[n,'specificity'])]+[int(val.loc[n,c]) for c in ['tn','fp','fn','tp']] for n in ORDER]
    table(s,rows,.65,2.05,[1.6,1.15,1.2,1.2,.83,.83,.83,.83],row_h=.46,size=15)
    box(s,'LR：AUC=1',f'FP={int(val.loc["logistic","fp"])}；FN={int(val.loc["logistic","fn"])}\n排序和阈值是两件事。',9.7,2.15,2.95,1.72,size=18)
    box(s,'证据范围','固定验证仅114条；\n并非独立测试结果。',9.7,4.25,2.95,1.72,size=18)
    text(s,'AP为非插值平均精确率；BA、AP和完整混淆矩阵另见备份17。',.75,6.45,12,.35,18,MUTED)
    # 8
    p_all=co.loc[('rf_all_features','probability'),'mean_correlation'];p_sqrt=co.loc[('random_forest','probability'),'mean_correlation']
    e_all=co.loc[('rf_all_features','binary_error'),'mean_correlation'];e_sqrt=co.loc[('random_forest','binary_error'),'mean_correlation']
    s=slide('加树收益很快趋缓；错误相关性未按假设下降','机制消融 · 工作单 D',
        f'树数从1到10明显改善固定验证AUC，50到300之间差异很小，且没有单调上升。额外RF-all和RF-sqrt使用同一实现、相同bootstrap索引，隔离特征随机化。概率相关从{p_all:.3f}降至{p_sqrt:.3f}，但二值错误相关从{e_all:.3f}变为{e_sqrt:.3f}，并未下降。因此H2在错误同步性上没有得到支持；RF的训练扰动稳定性改善不能只用这一相关指标解释。这里相关性跨114条验证记录计算，受类别和难例影响，不直接是方差公式的ρ。',45,
        'train341 / validation114；单种子、无误差线；RF-all/sqrt共享抽样；100树、4950对；results/tree_count_curve.csv、tree_correlation_summary.csv')
    picture(s,'slide_trees',.55,1.98,8.5,4.55)
    box(s,'100树：同实现对照',f'概率相关\n{p_all:.3f} → {p_sqrt:.3f}\n\n错误相关\n{e_all:.3f} → {e_sqrt:.3f}',9.45,2.05,3.2,3.65,size=22)
    text(s,'这是跨验证样本的相关性，\n不能直接代入训练扰动ρ。',9.6,5.95,3,.65,16,MUTED)
    # 9
    s=slide('Boosting持续降低训练损失，验证损失却会回升','顺序更新 · 工作单 E',
        f'AdaBoost和GB都是顺序依赖，但修正对象不同。AdaBoost的首轮真实加权错误{ada.weighted_error:.4f}，sklearn二类SAMME权重为{ada.estimator_weight:.3f}，错分者未归一化权重乘{ada.unnormalized_wrong_multiplier:.2f}，再整体归一化。GB在logit空间拟合y减p的负梯度，并作叶节点更新。图中虚线训练、实线验证，在lr0.1时验证损失从50轮约0.0788到200轮约0.1133，而训练继续下降。曲线只是探索，没有修改主GB的0.1和100轮，不能把审阅后的最优点称独立验证。',55,
        'train341 / validation114；lr=.03/.1/.3各200轮；虚线训练、实线验证；results/boosting_curves.csv；[R4–R7,S1]')
    picture(s,'slide_boost',.55,2.02,8.4,4.5)
    box(s,'AdaBoost：重加权',f'首轮 e={ada.weighted_error:.4f}\n错分权重 ×{ada.unnormalized_wrong_multiplier:.2f}\n（归一化之前）',9.25,2.05,3.4,2.05,size=18)
    box(s,'GB：拟合负梯度','二类log-loss：y − p\n不是仅修正错分类。',9.25,4.15,3.4,1.6,size=18)
    text(s,'探索曲线不用于重选主模型；\nXGBoost / LightGBM仅文献对照。',9.4,6.04,3.15,.68,15,MUTED)
    # 10
    s=slide('共享训练扰动下，树聚合减少了预测类别翻转','稳定性 · 工作单 G',
        f'每个模型用同一30份训练bootstrap，种子固定，验证114条固定。左边是每条验证记录在30次重拟合中的概率SD，再跨114条画箱线。右边更直接：31条记录在单树中曾出现两种类别，Bagging是17条，RF是9条，即{pct(st.loc["single_tree","any_flip_fraction"])}、{pct(st.loc["bagging","any_flip_fraction"])}和{pct(st.loc["random_forest","any_flip_fraction"])}。这里翻转不是错误率，而是30次中曾改变类别的记录比例；它依赖重拟合次数。概率尺度也不同，尤其AdaBoost输出压缩、SVM经校准，不能只靠概率SD跨模型下结论。',55,
        '相同30份train341 bootstrap；固定validation114；箱线=中位/IQR/1.5IQR、隐藏离群点，非CI；results/stability_predictions.csv')
    picture(s,'slide_stability',.5,1.95,8.6,4.65)
    text(s,'曾出现两种类别的记录',9.4,2.08,3.3,.45,19,TEAL,True)
    for i,n in enumerate(['single_tree','bagging','random_forest']):
        y=2.84+i*1.08;text(s,SHORT[n],9.45,y,2,.3,17,COLOR[n],True)
        text(s,f'{int(st.loc[n,"n_any_flip"])}/114  ·  {pct(st.loc[n,"any_flip_fraction"])}',9.45,y+.4,3.2,.45,24,COLOR[n],True)
    text(s,'any-flip：30次中至少出现过两类；\n不是错误率，也不是风险CI。',9.43,6.05,3.25,.62,15,MUTED)
    # 11
    s=slide('配对区间支持比较当前模型，覆盖不了换人群','固定模型的不确定性 · 工作单 G',
        f'这里换了bootstrap的对象：模型已经固定，不再重训，只在验证索引上按类别分层配对重抽样2000次。RF减单树的AUC差值是{d.interval("random_forest","single_tree")}，RF减LR是{d.interval("random_forest","logistic")}。配对保留了同一记录上两个模型的关联。该区间条件于当前模型、验证经验分布和类别数量，不包含重训、选模型或跨机构迁移。LR验证AUC为1使经验区间可能退化，这是有限经验样本的限制，不是性能已确定。CV折间SD也不能替代这个条件区间或外部验证。',45,
        '固定train模型；validation114按类分层配对bootstrap2000次；线=百分位95%条件区间；results/paired_differences.csv')
    picture(s,'slide_intervals',.5,2.0,8.6,4.5)
    box(s,'RF − Tree-full',d.interval('random_forest','single_tree'),9.22,2.15,3.45,1.5,size=17)
    box(s,'三种范围要分开','训练扰动稳定性\n固定模型指标区间\n外部人群不确定性',9.22,4.04,3.45,2.08,size=19)
    text(s,'区间不含重训和模型选择；不作多重比较显著性宣告。',.75,6.49,12,.35,17,MUTED)
    # 12
    s=slide('相关特征能互相替代，单变量重要性会误导','解释与相关性 · 工作单 H',
        f'比较同一主RF100模型的两类重要性。MDI记录训练时不纯度下降，置换重要性记录固定验证AUC下降，误差线只是20次置换SD。训练集中435个特征对有{n_high}对绝对相关大于0.9，尺寸特征尤其冗余。单独置换worst radius、perimeter、area的下降很小甚至为负，但将这三者用同一排列联合置换，AUC平均下降{grouped["worst_size"]:.3f}。这提示模型对相关变量组合的依赖，不表示其因果效应；置换也可能破坏与组外变量的联合分布，不能把组重要性解读成因果贡献。',50,
        'RF100：train341 MDI / Pearson；validation114、20次置换；误差线=置换SD非CI；results/feature_importance.csv、grouped_permutation.csv；[S4]')
    picture(s,'slide_importance',.55,1.98,12.25,3.85)
    rect(s,.75,5.94,5.8,.82,'#EDF4F1',rounded=True)
    text(s,f'训练集 |Pearson r| > 0.9：{n_high} / 435 对',.93,6.12,5.42,.35,17,TEAL,True)
    rect(s,6.85,5.94,5.78,.82,'#EDF4F1',rounded=True)
    text(s,f'联合置换worst尺寸三变量：AUC下降 {grouped["worst_size"]:.3f}',7.03,6.12,5.42,.35,17,TEAL,True)
    # 13
    s=slide('性能之外，训练与解释成本也要付账','复杂度与代价',
        f'同机单线程计时中，LR每折约{cv.loc["logistic","fit_seconds_mean"]*1000:.1f}毫秒，SVM含校准约{cv.loc["rbf_svm","fit_seconds_mean"]*1000:.1f}毫秒，RF约{cv.loc["random_forest","fit_seconds_mean"]*1000:.1f}毫秒，Bagging约{cv.loc["bagging","fit_seconds_mean"]*1000:.1f}毫秒。绝对成本在这份小数据上都不高，但没有性能增益时，额外复杂度仍需理由。LR系数易审阅，相关特征却会影响解释；RF拥有数千节点，通常要额外置换或局部解释。解释成本是定性判断，没有虚构人工计时。wall time受环境影响，不能推广成通用硬件基准。',35,
        '开发集共享五折、单线程wall time；SVM含三折校准；节点数来自固定train模型；results/cv_per_fold.csv、validation_metrics.csv')
    rows=[['模型','CV AUC','每折训练(ms)','解释成本（定性）']]
    for n,ex in [('logistic','系数易审阅；共线性需谨慎'),('rbf_svm','核边界 + 尺度 + 校准'),('random_forest',f'{int(val.loc["random_forest","total_nodes"])}节点；需额外解释'),('bagging',f'{int(val.loc["bagging","total_nodes"])}节点；需额外解释'),('gradient_boosting','顺序树组合；解释更新累积')]:
        rows.append([SHORT[n],f4(cv.loc[n,'roc_auc_mean']),f'{cv.loc[n,"fit_seconds_mean"]*1000:.1f}',ex])
    table(s,rows,.7,2.1,[1.65,1.5,2.4,6.25],row_h=.62,size=18)
    text(s,'当前数据规模下成本都可接受；复杂度增加仍应换来可验证的收益。',.8,6.35,11.8,.43,22,TEAL,True)
    # 14
    s=slide('当前优先保留LR，SVM和RF作为候选参照','模型选择 · 有条件的建议',
        '综合证据后，我们优先保留LR：主CV表现高、训练快，预测扰动也低。SVM保留为非线性性能参照；RF相比单树明显更稳定，可作为非线性候选，但在当前主比较中没有超过简单基线。H1获得描述性支持，H2在错误相关性上未获得支持，H3呈现树数平台和验证损失回升，H4支持有条件保留简单模型。会改变建议的证据是预先锁定阈值后，在独立多中心或时间外数据上，RF持续减少漏诊且校准、净获益更好。不能因为眼前验证满分直接部署。',40,
        '综合results/cv_summary.csv、stability_summary.csv、fit_times.csv；模型建议仅限当前数据和协议')
    box(s,'优先基线 · LR',f'CV AUC {cv.loc["logistic","roc_auc_mean"]:.4f}\nany-flip {pct(st.loc["logistic","any_flip_fraction"])}\n成本低，系数可审阅。',.7,2.12,3.78,2.72,size=21)
    box(s,'性能参照 · SVM',f'CV AUC {cv.loc["rbf_svm","roc_auc_mean"]:.4f}\nany-flip {pct(st.loc["rbf_svm","any_flip_fraction"])}\n需标准化和校准说明。',4.8,2.12,3.78,2.72,size=21)
    box(s,'集成候选 · RF',f'CV AUC {cv.loc["random_forest","roc_auc_mean"]:.4f}\nany-flip {pct(st.loc["random_forest","any_flip_fraction"])}\n相较单树更稳。',8.9,2.12,3.78,2.72,size=21)
    text(s,'改变选择的证据',.8,5.28,11.8,.4,22,TEAL,True)
    text(s,'独立多中心 / 时间外验证：在预设临床阈值下，\nRF稳定减少漏诊，并改善校准与净获益。',.8,5.92,11.8,.96,23)
    # 15
    s=slide('当前证据没有覆盖临床部署与外部人群','局限与下一步',
        '研究限制包括：单一小样本历史数据、近似可分和性能天花板；缺少患者分组、时间及机构信息，不能核验患者独立性；固定验证还参与了机制探索；概率没有统一校准，未按漏诊代价选择阈值；锁定测试尚未评价。后续应先锁定候选和临床代价、校准与净获益指标，再一次性测试，最后开展独立人群验证。CTG可以作为方法对照，但必须按recording_id分组划分和重抽样，普通按行OOB可能偏乐观；它不是WDBC模型的外部验证。',35,
        'data/README.md、data-ctg/README.md；本次仅WDBC；锁定测试集尚未评价')
    box(s,'当前限制','小样本 + 性能天花板\n缺少患者分组 / 时间 / 机构\n验证集参与机制探索\n未统一校准或优化临床阈值',.7,2.08,5.8,3.32,size=22)
    box(s,'下一步证据','先锁定候选与临床代价\n安排一次锁定测试\n独立人群评价校准与净获益\n必要时嵌套CV选择参数',6.86,2.08,5.8,3.32,size=22)
    text(s,'预测关联≠因果；当前良恶性分类≠未来患病风险。',.8,5.93,11.8,.5,24,TEAL,True)
    text(s,'CTG若扩展须按recording_id分组；独立方法对照不等于WDBC外部验证。',.8,6.52,11.8,.3,16,MUTED)
    # 16
    s=slide('选择模型，要同时回答三个问题','结论',
        '回到三个问题。第一，集成主要改善了同深度单树的排序表现和训练扰动稳定性，但不保证超过LR或SVM。第二，平均和训练多样性解释部分收益，不过错误相关性并未按预期下降，机制证据要区分统计方向。第三，在本数据和预设协议下，没有足够理由仅因模型更复杂就替代LR。我们交付了可复现实验、原始结果、图稿、报告和讲稿；所有结论都限定在当前验证范围，锁定测试集尚未评价。',25,
        '完整复现：RUN_RESEARCH.md；报告outputs/report.md；全部结果outputs/results/；[D1,R1–R7,S1–S6]')
    for i,(head,body) in enumerate([
        ('改善什么？','集成胜过同深度单树；\n本次未超过简单基线。'),
        ('为什么更稳？','聚合减少训练扰动；\n相关性证据有边界。'),
        ('复杂度值得吗？','先保留LR与候选参照；\n用独立证据决定是否替换。')]):
        y=2.03+i*1.43
        rect(s,.7,y,11.95,1.23,'#EDF4F1',rounded=True)
        text(s,head,.93,y+.35,2.75,.48,23,TEAL,True)
        text(s,body,4.0,y+.22,8.25,.82,21)
    text(s,'锁定测试集尚未评价。',.82,6.52,11.7,.45,22,TEAL,True)
    # 17 backup
    s=slide('备份：固定验证的完整指标','完整结果',
        '这里保留所有八个模型的AP、BA、敏感度、特异度与混淆矩阵，方便课堂追问。所有数值来自同一validation_metrics.csv，恶性为阳性，统一概率0.5阈值，SVM已在训练内部校准。AP不是梯形PR面积。请不要把这个固定验证表当成锁定测试结果。',0,
        'train341 / validation114；p≥.5；CM按TN/FP/FN/TP顺序；AP=ΣΔRecall×Precision；results/validation_metrics.csv',True)
    rows=[['模型','AUC','AP','BA','敏感度','特异度','TN/FP/FN/TP']]
    rows += [[SHORT[n]]+[f4(val.loc[n,c]) for c in ['roc_auc','average_precision','balanced_accuracy','sensitivity','specificity']]+['/'.join(str(int(val.loc[n,c])) for c in ['tn','fp','fn','tp'])] for n in ORDER]
    table(s,rows,.7,2.13,[1.6,1.35,1.35,1.35,1.35,1.35,3.0],row_h=.49,size=15)
    text(s,'CV每折敏感度、特异度及全部预测也已保存，未用验证阈值优化。',.8,6.64,12,.3,17,MUTED)
    # 18 backup
    s=slide('备份：稳定性定义与参数','复现细节',
        'any-flip是30次中出现两种类别的验证记录比例，pair disagreement是随机选两个不同重拟合模型时类别不一致概率，概率SD使用ddof1。所有模型共享训练bootstrap，SVM校准按原记录ID分组。主参数为LR和SVM的C1，浅树depth2，单树及Bagging/RF基树不限深度，100棵Bagging/RF，Ada50树桩lr1，GB100深度3lr0.1。完整默认参数、版本和哈希见run_info.json。',0,
        'seed1010；训练bootstrap1012；N=30；results/run_info.json、stability_summary.csv',True)
    rows=[['模型','平均概率SD','any-flip','两次重拟合不一致率']]
    rows += [[SHORT[n],f4(st.loc[n,'mean_probability_sd']),pct(st.loc[n,'any_flip_fraction']),pct(st.loc[n,'mean_pair_disagreement'])] for n in ORDER]
    table(s,rows,.7,2.0,[1.6,1.8,1.6,2.7],row_h=.43,size=15)
    box(s,'预设参数','LR / SVM：C=1\n单树及Bag/RF基树：不限深度\nBag / RF：100棵\nAda：50树桩，lr=1\nGB：100轮，depth3，lr=.1',8.8,2.0,3.85,3.85,size=17)
    text(s,'any-flip = mean I(0<q<1)；pair disagreement = mean[2n₁n₀ / R(R−1)]',.8,6.35,11.8,.4,17)
    # 19 backup
    s=slide('备份：Bagging、Boosting与常用实现','机制对照',
        'Bagging的基树可独立训练，主要平均高方差；Boosting逐阶段依赖，Ada改变权重，GB拟合负梯度。XGBoost的经典贡献包括正则目标、二阶近似和稀疏感知计算；LightGBM经典论文包括GOSS、EFB和高效直方图方案。它们仍属于梯度提升树框架，不能承诺在所有数据上更准确。我们只做文献对照，没有运行XGBoost或LightGBM，也没有给它们编造实验数字。工作单A到H包含更完整的手算和对照表。',0,
        '[R2–R7,S1,S5,S6]；仅文献对照，未运行XGBoost/LightGBM',True)
    rows=[['方面','Bagging / RF','Boosting'],['训练','基树独立，可并行','顺序依赖'],['制造差异','训练bootstrap；RF另随机特征','Ada重加权 / GB拟合负梯度'],['常见基树','深树，平均降方差','树桩或浅树，逐步修正'],['轮数','趋于平台；指标不保证单调','学习率与轮数联动；可能追随噪声']]
    table(s,rows,.7,2.0,[2.0,4.6,5.3],row_h=.56,size=17)
    text(s,'XGBoost：正则化目标、二阶近似、稀疏感知与采样。\nLightGBM：直方图、按叶生长；经典GOSS与EFB。',.85,5.25,11.6,1.05,21)
    text(s,'完整投票手算、树例题与250–400字备忘录：outputs/worksheet_completed.md',.85,6.57,11.6,.3,15,MUTED)
    # 20 backup
    s=slide('备份：数据、论文与软件文档','参考文献',
        '完整可核验引用和链接如下，公开网页访问状态保存于reference_checks.json。HTTP核验只访问文献和文档，不下载数据集或恢复锁定标签。\n\n'+refs,0,
        '全部公开链接已检查；完整条目与URL见outputs/report.md、results/reference_checks.json',True)
    left='[D1] WDBC. UCI (1995). DOI 10.24432/C5DW2B\n[R1] Efron (1979). Bootstrap Methods. Ann. Stat.\n[R2] Breiman (1996). Bagging Predictors. ML\n[R3] Breiman (2001). Random Forests. ML\n[R4] Freund & Schapire (1997). JCSS 55:119–139\n[R5] Friedman (2001). Gradient Boosting. Ann. Stat.\n[R6] Chen & Guestrin (2016). XGBoost. KDD\n[R7] Ke et al. (2017). LightGBM. NeurIPS 30'
    right='软件与定义（scikit-learn 1.7.2）\n[S1] Ensemble methods\n[S2] average_precision_score\n[S3] Probability calibration\n[S4] Permutation feature importance\n\n[S5] XGBoost：Introduction to Boosted Trees\n[S6] LightGBM：Features'
    text(s,left,.75,2.07,7.25,4.5,17);text(s,right,8.3,2.07,4.3,4.5,17)
    # All notes and tables remain native/editable.
    dest=OUT/'presentation';dest.mkdir(exist_ok=True)
    prs.save(dest/'ensemble_report.pptx')
    (dest/'slides_manifest.json').write_text(json.dumps(SLIDES,ensure_ascii=False,indent=2),encoding='utf-8')
    notes=['# 逐页中文讲稿','',f'正文16页，建议时长约{sum(x["seconds"] for x in SLIDES)/60:.1f}分钟；备份4页不计入时长。',
           '每页PPT的备注中也保存同一份讲稿。可根据课堂语速调整停顿；全程未评价锁定测试集。','']
    for x in SLIDES:
        notes += [f'## {x["page"]:02d}. {x["title"]}'+('（备份）' if x['backup'] else f'（约{x["seconds"]}秒）'),'',x['notes'],'']
    (dest/'speaker_notes.md').write_text('\n'.join(notes),encoding='utf-8')
    print('Generated',len(prs.slides),'slides; main talk seconds:',sum(x['seconds'] for x in SLIDES))

if __name__=='__main__':run()
