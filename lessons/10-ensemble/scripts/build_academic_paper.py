"""Build a Chinese course paper (editable DOCX + Word-exported PDF) from actual results."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import importlib.metadata
import platform
import sys
import hashlib
import numpy as np
import pandas as pd
import fitz
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT,WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from research_style import *
from make_report import Study,pct,f4
from verify_sources import REFERENCES
from make_paper_figures import run as paper_figures

DEST=OUT/'paper'
DOCX=DEST/'ensemble_study_paper.docx'
PDF=DEST/'ensemble_study_paper.pdf'
DOC=None

def east_asia(run,font='宋体'):
    run.font.name=font
    rpr=run._element.get_or_add_rPr()
    rf=rpr.rFonts
    if rf is None:rf=OxmlElement('w:rFonts');rpr.insert(0,rf)
    rf.set(qn('w:eastAsia'),font);rf.set(qn('w:ascii'),'Times New Roman');rf.set(qn('w:hAnsi'),'Times New Roman')

def format_para(p,align=None,before=0,after=0,spacing=1.5,keep=False):
    if align is not None:p.alignment=align
    pf=p.paragraph_format;pf.space_before=Pt(before);pf.space_after=Pt(after);pf.line_spacing=spacing;pf.keep_together=True
    if keep:pf.keep_with_next=True

def add_run(p,text,size=12,bold=False,color=None,font='宋体',italic=False):
    r=p.add_run(str(text));r.bold=bold;r.italic=italic;r.font.size=Pt(size);east_asia(r,font)
    if color:r.font.color.rgb=RGBColor.from_string(color.lstrip('#'))
    return r

def para(text='',style=None,first=True,align=WD_ALIGN_PARAGRAPH.JUSTIFY,after=0):
    p=DOC.add_paragraph(style=style);format_para(p,align=align,after=after)
    if first and text:p.paragraph_format.first_line_indent=Cm(.74)
    if text:add_run(p,text)
    return p

def heading(text,level=1):
    p=DOC.add_paragraph(style=f'Heading {level}');p.paragraph_format.keep_with_next=True
    p.paragraph_format.keep_together=True
    add_run(p,text,16 if level==1 else (13 if level==2 else 12),True,INK,'黑体')
    return p

def caption(text):
    p=DOC.add_paragraph();format_para(p,WD_ALIGN_PARAGRAPH.CENTER,before=4,after=4,spacing=1.05,keep=True)
    add_run(p,text,10.5,color='52686A')
    return p

def image(name,width=15.5):
    p=DOC.add_paragraph();format_para(p,WD_ALIGN_PARAGRAPH.CENTER,before=2,after=1,spacing=1.0,keep=True)
    p.add_run().add_picture(str(FIG/f'{name}.png'),width=Cm(width))
    return p

def shade(cell,color):
    tcpr=cell._tc.get_or_add_tcPr();shd=tcpr.find(qn('w:shd'))
    if shd is None:shd=OxmlElement('w:shd');tcpr.append(shd)
    shd.set(qn('w:fill'),color.lstrip('#'))

def borders(table):
    pr=table._tbl.tblPr;bs=pr.find(qn('w:tblBorders'))
    if bs is None:bs=OxmlElement('w:tblBorders');pr.append(bs)
    for edge in ['top','left','bottom','right','insideH','insideV']:
        el=OxmlElement('w:'+edge);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'4');el.set(qn('w:color'),'D5DFDC');bs.append(el)

def repeat_header(row):
    trpr=row._tr.get_or_add_trPr();el=OxmlElement('w:tblHeader');el.set(qn('w:val'),'true');trpr.append(el)

def add_table(title,headers,rows,widths=None,font_size=9.3):
    caption(title)
    t=DOC.add_table(rows=1,cols=len(headers));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
    if widths:
        for c,w in zip(t.columns,widths):c.width=Cm(w)
    repeat_header(t.rows[0]);data=[headers]+rows
    for ri,rowdata in enumerate(data):
        row=t.rows[0] if ri==0 else t.add_row()
        trpr=row._tr.get_or_add_trPr();cant=OxmlElement('w:cantSplit');trpr.append(cant)
        if widths:
            for c,w in zip(row.cells,widths):c.width=Cm(w)
        for j,value in enumerate(rowdata):
            cell=row.cells[j];cell.text='';cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cell.margin_top=Cm(.06);cell.margin_bottom=Cm(.06)
            shade(cell,INK if ri==0 else ('EEF4F2' if ri%2 else 'FFFFFF'))
            p=cell.paragraphs[0];format_para(p,WD_ALIGN_PARAGRAPH.LEFT if j==0 else WD_ALIGN_PARAGRAPH.CENTER,spacing=1.03)
            add_run(p,str(value),font_size,bold=ri==0,color='FFFFFF' if ri==0 else INK)
    borders(t)
    DOC.add_paragraph().paragraph_format.space_after=Pt(2)
    return t

def bullet(text):
    p=DOC.add_paragraph(style='List Bullet');format_para(p,after=1,spacing=1.3)
    for r in p.runs:east_asia(r)
    p.add_run(text);return p

def make_document():
    global DOC
    DEST.mkdir(parents=True,exist_ok=True);d=Study();DOC=Document()
    sec=DOC.sections[0];sec.page_width=Cm(21);sec.page_height=Cm(29.7)
    sec.top_margin=Cm(2.25);sec.bottom_margin=Cm(2.15);sec.left_margin=Cm(2.55);sec.right_margin=Cm(2.35)
    sec.header_distance=Cm(1.05);sec.footer_distance=Cm(1.0)
    normal=DOC.styles['Normal'];normal.font.name='Times New Roman';normal.font.size=Pt(12)
    normal._element.rPr.rFonts.set(qn('w:eastAsia'),'宋体')
    normal.paragraph_format.line_spacing=1.5;normal.paragraph_format.space_after=Pt(0)
    for lev,size in [(1,16),(2,13),(3,12)]:
        st=DOC.styles[f'Heading {lev}'];st.font.name='Microsoft YaHei';st.font.size=Pt(size);st.font.bold=True;st.font.color.rgb=RGBColor.from_string(INK.lstrip('#'))
        st._element.rPr.rFonts.set(qn('w:eastAsia'),'黑体');st.paragraph_format.space_before=Pt(lev*5+6);st.paragraph_format.space_after=Pt(5);st.paragraph_format.keep_with_next=True
    for stname in ['List Bullet']:
        DOC.styles[stname].font.name='Times New Roman';DOC.styles[stname].font.size=Pt(12);DOC.styles[stname]._element.rPr.rFonts.set(qn('w:eastAsia'),'宋体')
    # Running header and dynamic page number.
    hp=sec.header.paragraphs[0];format_para(hp,WD_ALIGN_PARAGRAPH.RIGHT,spacing=1.0)
    add_run(hp,'课程研究论文  |  集成学习与 Bootstrap',9.5,color=MUTED)
    fp=sec.footer.paragraphs[0];format_para(fp,WD_ALIGN_PARAGRAPH.CENTER,spacing=1.0)
    add_run(fp,'第 ',9,color=MUTED)
    fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');fp._p.append(fld);add_run(fp,' 页',9,color=MUTED)

    title='集成学习何时值得？'
    sub='乳腺肿块分类中的性能、稳定性与复杂度权衡'
    p=DOC.add_paragraph();format_para(p,WD_ALIGN_PARAGRAPH.CENTER,before=18,after=7,spacing=1.1,keep=True)
    add_run(p,title,22,True,INK,'黑体')
    p=DOC.add_paragraph();format_para(p,WD_ALIGN_PARAGRAPH.CENTER,after=16,spacing=1.15,keep=True)
    add_run(p,sub,16,True,INK,'黑体')
    p=DOC.add_paragraph();format_para(p,WD_ALIGN_PARAGRAPH.CENTER,after=14,spacing=1.1,keep=True)
    add_run(p,'课程作业论文   ·   集成学习与 Bootstrapping',11,color=MUTED)
    p=DOC.add_paragraph();format_para(p,WD_ALIGN_PARAGRAPH.CENTER,after=4,spacing=1.1,keep=True)
    add_run(p,'姓名：____________    班级：____________    日期：2026年11月14日',10.5,color=MUTED)

    heading('摘要',1)
    cv=d.cv;st=d.st
    abstract=(f'目的：评估Bagging、随机森林与Boosting相较单棵决策树的预测表现与训练扰动稳定性，并检验复杂集成是否值得替代逻辑回归和RBF-SVM。方法：以WDBC课程划分为主实验，仅使用341条训练记录和114条固定验证记录；在455条开放开发数据上使用共享五折分层交叉验证。预设比较逻辑回归、校准RBF-SVM、浅树、深树、Bagging、随机森林、AdaBoost和Gradient Boosting。主要指标为ROC-AUC，并报告average precision、balanced accuracy、敏感度、特异度及混淆矩阵。通过2000次有放回抽样描述Bootstrap独特样本比例，通过30份共享训练重抽样评估预测波动，并用2000次配对分层重抽样估计固定模型验证性能差值的条件区间。结果：开发集五折ROC-AUC为逻辑回归{cv.loc["logistic","roc_auc_mean"]:.4f}、RBF-SVM {cv.loc["rbf_svm","roc_auc_mean"]:.4f}、随机森林{cv.loc["random_forest","roc_auc_mean"]:.4f}、不限深度单树{cv.loc["single_tree","roc_auc_mean"]:.4f}。30次训练扰动中曾发生类别改变的验证记录比例分别为深树{pct(st.loc["single_tree","any_flip_fraction"])}、Bagging {pct(st.loc["bagging","any_flip_fraction"])}和随机森林{pct(st.loc["random_forest","any_flip_fraction"])}。额外特征随机化降低了树间概率相关性，但没有降低本次验证样本上的二值错误相关性。结论：集成改善了单树表现与训练扰动稳定性，但本协议下没有显示其必须替代简单基线。结果限于当前数据与验证方案；锁定测试集尚未评价。')
    para(abstract,first=False)
    p=DOC.add_paragraph();format_para(p,after=6,spacing=1.2)
    add_run(p,'关键词：',12,True);add_run(p,'集成学习；Bootstrap；随机森林；模型稳定性；WDBC；交叉验证',12)

    heading('1 引言',1)
    para('集成学习把多个学习器的预测组合起来，常见动机是通过平均降低不稳定基学习器的方差。Bagging使用有放回抽样产生多个训练集；随机森林在此基础上随机限制节点候选特征；Boosting则按顺序更新模型，以逐步减少经验损失[2–6]。这些机制并不保证集成模型在每个数据集、每项指标或每种验证协议下都优于简单模型。')
    para('本研究围绕三个问题展开：（1）Bagging、随机森林和Boosting相较单树改善了什么？（2）训练数据扰动下的预测是否更稳定，样本重抽样与树间相关性提供什么机制证据？（3）综合性能、稳定性、计算和解释成本，复杂模型是否值得替代逻辑回归或RBF-SVM？')
    para('在实验前固定四项可检验预期：H1，Bagging与随机森林相较基树深度一致的单树具有更高开发集交叉验证ROC-AUC及更低训练扰动；H2，节点特征随机化降低树间错误相关性，但特征冗余可能使性能收益有限；H3，树数增加呈边际递减，Boosting训练损失下降不保证验证损失持续下降；H4，复杂模型的表现和稳定性收益不足以自动抵消其成本，简单基线可能仍值得优先保留。该协议在本地首次实验前写入protocol.md，属于事前固定的课程分析方案，不声称公开注册或原创算法贡献。')
    para('贡献限于可复现实证比较和机制分析。所有结论针对当前WDBC样本及指定验证程序，不作因果、未来患病风险或临床部署推断。')

    heading('2 材料与方法',1)
    heading('2.1 数据与样本边界',2)
    para('数据为Breast Cancer Wisconsin (Diagnostic)（WDBC），课堂离线表格源自scikit-learn数据集，原始数据出处为UCI Repository[1]。一行代表由乳腺肿块细针穿刺图像提取并汇总的细胞核形态特征记录，不代表单个细胞。输入为30个连续特征，分属形态量的mean、standard error和worst汇总；标签重编码为malignant=1。sample_id只追踪记录，不进入模型。本研究仅读取现成的student/train.csv和student/validation.csv；未访问teacher目录、锁定测试特征、完整测量表或原始数据源。')
    add_table('表1  开放分析样本审计',['集合','记录数','良性 / 0','恶性 / 1','阳性率','缺失单元格'],[
        [str(r.split),str(r.n),str(r.negative),str(r.positive),f'{r.prevalence:.3f}',str(r.missing_cells)]
        for r in read('dataset_audit').itertuples()],widths=[3.5,2.2,2.5,2.5,2.3,3.0],font_size=9.5)
    para('原固定划分为train 341条、validation 114条。train单独用于固定验证拟合；开发集train+validation共455条用于共享五折交叉验证。交叉验证与固定验证共享样本，其结果不是相互独立的重复验证。CV每折使用约364条训练数据，而固定验证分析使用341条；两者回答不同训练样本规模和划分条件下的表现。数据缺少可用患者ID及时间信息，因而无法核验患者独立性，也不能估计跨机构迁移表现。')

    heading('2.2 比较协议与模型',2)
    para('主比较采用五折StratifiedKFold，shuffle=True、random_state=1010；八个模型共享完全相同的折索引，所有参数在查看实验结果前预设，没有根据性能曲线重选主模型。LR的StandardScaler置于Pipeline内。RBF-SVM为StandardScaler与SVC构成的Pipeline，再由三折sigmoid CalibratedClassifierCV校准；校准折只使用当前外层训练数据，ensemble=False时最终分类器在该训练部分拟合。SVM概率排序对应单调sigmoid转换后的decision score；未将原始decision_function当作概率计算log-loss。训练重抽样中的SVM校准折按原训练行索引分组，以免重复抽中的同一原记录跨校准折。')
    add_table('表2  预设模型与关键参数',['模型','结构与预设参数','预处理 / 输出'],[
        ['逻辑回归','C=1；max_iter=5000','折内StandardScaler；概率'],
        ['RBF-SVM','C=1；gamma=scale','折内Pipeline标准化；三折sigmoid校准'],
        ['浅树','max_depth=2','固定种子1010'],
        ['单树','不限深度','与集成基树深度对照'],
        ['Bagging','100棵；不限深度；全特征；bootstrap','每折内拟合'],
        ['随机森林','100棵；不限深度；max_features=sqrt','节点级随机特征'],
        ['AdaBoost','50棵树桩；learning_rate=1；SAMME','顺序加权'],
        ['Gradient Boosting','100阶段；depth=3；lr=.1；log-loss','逐阶段梯度更新']],widths=[2.4,7.3,4.8],font_size=8.8)
    para('单棵树的深度分析另比较max_depth=1、2、3、4及不限深度。Bagging和随机森林使用不限深度基树，避免深度混杂。随机森林消融比较树数1、10、50、100、300，并加入同一RandomForestClassifier实现、相同bootstrap索引的全特征(max_features=1.0)控制；同时与全特征Bagging对照。')

    heading('2.3 指标与固定阈值',2)
    para('主要指标为ROC-AUC。Average precision (AP)按非插值定义计算：AP=Σₖ(Rₖ−Rₖ₋₁)Pₖ，其中Rₖ和Pₖ分别为按阈值排序得到的召回率与精确率；该定义为scikit-learn average_precision_score，不等于梯形积分PR-AUC[10]。另报告balanced accuracy=[敏感度+特异度]/2、恶性类敏感度、特异度和TN/FP/FN/TP。分类统一使用预设概率阈值0.5，未在验证集或测试集优化阈值。')
    para('模型概率均用于ROC-AUC和AP排序；SVM排序分数来自其训练内校准概率。模型概率没有统一外部校准，因此log-loss及跨模型概率标准差应谨慎比较；本研究不把它们解释为个体风险精度。所有训练计时使用单线程wall time，包含对应Pipeline和校准过程。记录软件版本、完整参数、随机种子和输入文件哈希。')

    heading('2.4 Bootstrap、稳定性及条件区间',2)
    para('抽样模拟分别对n=5与n=341执行2000次有放回抽取，每次抽n次，保存独特样本比例及OOB比例。有限样本中单个原记录未被抽中的概率为(1−1/n)ⁿ，故独特比例期望为1−(1−1/n)ⁿ；大样本极限近似36.8% OOB和63.2%独特样本[2]。')
    para('训练扰动分析从341条train生成同一批30份有放回训练样本，所有八个模型共享抽样并固定算法种子，在固定114条validation上重拟合。对每个验证记录计算30次预测概率的样本标准差（ddof=1）。定义any-flip为30次中预测类别曾出现两类的记录比例，即mean[I(0<qⱼ<1)]，其中qⱼ为该记录预测恶性的比例；该比例依赖重复次数。另计算两个不同重拟合模型的类别不一致概率2n₁n₀/[R(R−1)]，区分训练样本扰动稳定性与概率尺度。')
    para('固定模型区间在完成train拟合后，对validation按类别分层、成对重抽样2000次；同一抽样索引用于所有模型。报告主要模型差值和百分位95%区间。区间条件于当前拟合模型、验证经验分布和类别数量，不涵盖重训、反复选模或外部人群变化。五折SD仅作描述，不当作置信区间或显著性检验。')

    heading('2.5 解释性与Boosting机制分析',2)
    para('对预设RF100比较训练不纯度重要性(mean decrease in impurity, MDI)与validation上以ROC-AUC下降定义的置换重要性；置换重复20次。以train计算Pearson相关，并对worst-size三特征、mean与worst六个尺寸特征进行联合置换。重要性只表示当前模型依赖和预测关联，不表示因果效应；相关特征可能互为替代。')
    para('AdaBoost记录主模型前八轮样本权重、加权错误及分类器权重。二类SAMME每轮增加错分样本的相对权重。Gradient Boosting二分类对log-loss的logit负梯度为y−p，新树拟合该残差方向后作阶段更新[5–6]。另以learning_rate=.03、.1、.3及最多200阶段生成训练和固定验证损失曲线；曲线为探索分析，未用于改变主模型参数。')

    heading('3 结果',1)
    heading('3.1 主比较：集成改善单树，未超过简单基线',2)
    cvrows=[]
    for n in ORDER:
        r=d.cv.loc[n];cvrows.append([LABEL[n],f'{r.roc_auc_mean:.4f} ± {r.roc_auc_sd:.4f}',f'{r.average_precision_mean:.4f}',f'{r.balanced_accuracy_mean:.4f}',f'{r.fit_seconds_mean:.3f}'])
    add_table('表3  开发集共享五折结果（均值±SD为五折间描述统计）',['模型','ROC-AUC 均值±SD','AP 均值','BA 均值','每折训练秒'],cvrows,widths=[3.2,3.4,2.4,2.4,2.6],font_size=9.0)
    caption('图1  开发集五折ROC-AUC与AP。误差线为五折间样本标准差（ddof=1），不是置信区间。')
    image('paper_performance',width=14.8)
    para(f'逻辑回归五折ROC-AUC为{d.cv.loc["logistic","roc_auc_mean"]:.4f}±{d.cv.loc["logistic","roc_auc_sd"]:.4f}，RBF-SVM为{d.cv.loc["rbf_svm","roc_auc_mean"]:.4f}±{d.cv.loc["rbf_svm","roc_auc_sd"]:.4f}。相较之下，Bagging为{d.cv.loc["bagging","roc_auc_mean"]:.4f}±{d.cv.loc["bagging","roc_auc_sd"]:.4f}，随机森林为{d.cv.loc["random_forest","roc_auc_mean"]:.4f}±{d.cv.loc["random_forest","roc_auc_sd"]:.4f}，均高于深单树的{d.cv.loc["single_tree","roc_auc_mean"]:.4f}±{d.cv.loc["single_tree","roc_auc_sd"]:.4f}，但未超过LR/SVM。折间SD本身不提供模型差异的显著性证据。')
    valrows=[]
    for n in ORDER:
        r=d.val.loc[n];valrows.append([LABEL[n],f'{r.roc_auc:.4f}',f'{r.average_precision:.4f}',f'{r.balanced_accuracy:.4f}',f'{r.sensitivity:.3f}',f'{r.specificity:.3f}',f'{int(r.tn)}/{int(r.fp)}/{int(r.fn)}/{int(r.tp)}'])
    add_table('表4  固定验证表现：train拟合、validation评价，阈值p≥0.5',['模型','ROC-AUC','AP','BA','敏感度','特异度','TN/FP/FN/TP'],valrows,widths=[2.4,1.8,1.7,1.7,1.8,1.8,3.1],font_size=8.6)
    para('固定验证AUC中LR与SVM均为1.000；在阈值0.5下，LR有1个FP，SVM为0 FP/0 FN。随机森林的混淆矩阵为TN=70、FP=1、FN=2、TP=41。排序指标、固定阈值分类与漏诊代价是不同决策维度；114条验证记录的结果不代表总体性能已确定。')

    heading('3.2 树深与结构扰动',2)
    depth=read('tree_depth');rows=[]
    for r in depth.itertuples():rows.append([str(r.max_depth),r.split,str(int(r.leaves)),f'{r.accuracy:.3f}',f'{r.roc_auc:.3f}',f'{r.balanced_accuracy:.3f}'])
    add_table('表5  不同最大深度树的训练与固定验证表现',['max_depth','数据部分','叶节点','Accuracy','ROC-AUC','BA'],rows,widths=[2.2,2.4,2.1,2.3,2.3,2.5],font_size=9.0)
    caption('图2  max_depth对准确率的影响；训练准确率持续增加，而验证值不单调。')
    image('slide_depth',width=13.8)
    root=read('bootstrap_tree_roots');grp=root.groupby('root_feature').agg(count=('repeat','size'),low=('root_threshold','min'),high=('root_threshold','max')).sort_values('count',ascending=False)
    add_table('表6  30份共享Bootstrap样本下，depth=2树的根节点变化',['根节点特征','出现次数','同特征内阈值范围'],[[f,str(int(r['count'])),f'{r.low:.5g}–{r.high:.5g}'] for f,r in grp.iterrows()],widths=[5.8,2.7,6.3],font_size=9.0)
    DOC.paragraphs[-1].paragraph_format.space_after=Pt(0)
    caption('图3  Bootstrap重抽样后根节点特征使用次数；特征内阈值范围见表6。')
    image('slide_roots',width=13.8)
    para('深度为3时固定验证AUC为0.973，略高于depth2的0.972；depth4回落至0.953，不限深度为0.967。训练AUC随深度升至1.000。重复训练抽样后，根节点从worst perimeter延伸至尺寸和凹点类特征，阈值在同一特征内也会变化，体现单树结构的训练扰动敏感性。该深度曲线是单一固定划分的探索结果，不据此改变主模型选择。')

    heading('3.3 Bootstrap与树数/相关性机制',2)
    sim=read('bootstrap_sampling').query('n == 341')
    unique=sim.unique_fraction.mean();oob=sim.oob_fraction.mean();theory=sim.expected_unique.iloc[0]
    add_table('表7  n=341、2000次Bootstrap模拟',['统计量','本次模拟均值','有限样本理论期望','大样本近似'],[
        ['独特样本比例',f'{unique:.5f}',f'{theory:.5f}',f'{1-np.exp(-1):.5f}'],
        ['OOB比例',f'{oob:.5f}',f'{1-theory:.5f}',f'{np.exp(-1):.5f}']],widths=[3.8,3.8,4.2,4.0],font_size=9.1)
    para('每轮有放回抽341次，模拟独特记录比例均值为63.2%左右，约36.8%记录平均未被某一棵树抽中。这是每轮的期望比例而非固定样本数。OOB可汇总各记录在未参与该树训练时的预测，形成内部表现估计；当记录有群组依赖、OOB参与反复调参或有效OOB树数不足时，边界会改变，不能替代独立外部验证。')
    tc=read('tree_count_curve');tcrows=[]
    for name in ['bagging','random_forest','rf_all_features']:
        for r in tc[tc.model==name].itertuples():tcrows.append([LABEL[name],str(r.n_trees),f'{r.validation_roc_auc:.4f}',f'{r.validation_balanced_accuracy:.4f}',('—' if pd.isna(r.oob_roc_auc) else f'{r.oob_roc_auc:.4f}')])
    caption('表8  树数消融的完整曲线（固定validation，单次种子；非调参比较）')
    add_table('表8（续）  各方法验证排序/分类表现与OOB AUC',['方法','树数','验证AUC','验证BA','OOB AUC'],tcrows,widths=[4.0,2.0,3.0,3.0,3.6],font_size=8.8)
    caption('图4  树数与随机特征对照。右图使用100棵树在同一114条验证记录上的两两相关。')
    image('slide_trees',width=14.8)
    c=read('tree_correlation_summary')
    pivot=c.pivot(index='model',columns='kind',values='mean_correlation')
    add_table('表9  100棵基树在固定验证样本上的树间相关性均值',['方法','概率相关','残差相关','二值错误相关','两两配对数'],[
        [LABEL[n],f'{pivot.loc[n,"probability"]:.3f}',f'{pivot.loc[n,"residual"]:.3f}',f'{pivot.loc[n,"binary_error"]:.3f}',str(int(c[(c.model==n)&(c.kind=='binary_error')].n_pairs.iloc[0]))]
        for n in ['bagging','rf_all_features','random_forest']],widths=[3.2,2.8,2.8,3.3,2.5],font_size=8.9)
    p_all=pivot.loc['rf_all_features','probability'];p_sqrt=pivot.loc['random_forest','probability']
    e_all=pivot.loc['rf_all_features','binary_error'];e_sqrt=pivot.loc['random_forest','binary_error']
    para(f'树数从1升到10时性能改善最明显，50至300棵后曲线趋于平台，且各指标不严格单调。RF-all与RF-sqrt使用同一实现，bootstrap索引核验一致。概率相关均值由{p_all:.3f}降至{p_sqrt:.3f}，但二值错误相关由{e_all:.3f}变为{e_sqrt:.3f}，没有降低；因此H2关于错误同步性的机制预期未得到支持。相关性来自固定验证样本方向、排除恒定错误向量，共4950对，受到记录难度及类别结构影响，不能直接等同于训练扰动方差公式中的ρ。')

    heading('3.4 Boosting顺序更新与验证曲线',2)
    ada=read('adaboost_weight_rounds').iloc[0]
    para(f'AdaBoost首轮加权错误为{ada.weighted_error:.4f}，sklearn二类SAMME分类器权重为{ada.estimator_weight:.4f}。错分样本在归一化前的相对乘数为exp(α)={ada.unnormalized_wrong_multiplier:.2f}，之后对全体样本权重重新归一化。逐轮权重、错误与梯度样本记录均另存CSV。梯度提升拟合log-loss负梯度y−p，意味着分类正确但概率仍不准确的样本也可贡献更新。')
    bc=read('boosting_curves');rows=[]
    for model_name in ['gradient_boosting','adaboost']:
        for lr in [.03,.1,.3]:
            for stage in [50,100,200]:
                a=bc[(bc.model==model_name)&np.isclose(bc.learning_rate,lr)&(bc.stage==stage)]
                tr=a[a.split=='train'].iloc[0];va=a[a.split=='validation'].iloc[0]
                rows.append([LABEL[model_name],f'{lr:g}',str(stage),f'{tr.log_loss:.4f}',f'{va.log_loss:.4f}',f'{va.roc_auc:.4f}'])
    add_table('表10  Boosting探索曲线选定阶段的训练/验证损失',['方法','lr','阶段','训练log-loss','验证log-loss','验证AUC'],rows,widths=[3.2,1.7,1.7,3.0,3.0,2.0],font_size=8.6)
    caption('图5  GB在不同学习率下的log-loss曲线；虚线训练、实线固定验证。')
    image('slide_boost',width=14.8)
    a=bc[(bc.model=='gradient_boosting')&np.isclose(bc.learning_rate,.1)&(bc.split=='validation')].set_index('stage')
    tr=bc[(bc.model=='gradient_boosting')&np.isclose(bc.learning_rate,.1)&(bc.split=='train')].set_index('stage')
    para(f'以GB、learning_rate=.1为例，验证log-loss由50阶段的{a.loc[50,"log_loss"]:.4f}上升到200阶段的{a.loc[200,"log_loss"]:.4f}，而训练损失由{tr.loc[50,"log_loss"]:.4f}继续降至{tr.loc[200,"log_loss"]:.4f}。此现象与过多轮次可能追随训练噪声的假设一致。该曲线参与探索审阅，不能将其中表现较好的阶段称为独立验证结果；若据此调参，应使用嵌套交叉验证或另外独立评价。XGBoost与LightGBM作为梯度提升树的正则化和效率扩展作文献对照，本次没有安装或运行这两个包[7–8,13–14]。')

    heading('3.5 训练扰动稳定性与固定模型条件区间',2)
    stab=read('stability_summary').set_index('model').loc[ORDER]
    rows=[[LABEL[n],f'{stab.loc[n,"mean_probability_sd"]:.4f}',f'{stab.loc[n,"median_probability_sd"]:.4f}',f'{pct(stab.loc[n,"any_flip_fraction"])} ({int(stab.loc[n,"n_any_flip"])}/114)',f'{pct(stab.loc[n,"mean_pair_disagreement"])}'] for n in ORDER]
    add_table('表11  30份共享训练bootstrap下的预测稳定性',['模型','逐例概率SD均值','逐例概率SD中位','any-flip比例','两次重拟合不一致率'],rows,widths=[3.0,3.0,3.0,3.4,3.0],font_size=8.7)
    caption('图6  各验证记录的概率SD分布与类别翻转；箱线为中位数、四分位数及1.5×IQR，隐藏离群点。')
    image('slide_stability',width=14.8)
    para(f'不限深度单树有31/114条记录在30次重拟合中曾出现类别改变，Bagging为17/114，随机森林为9/114。any-flip比例描述这批训练经验扰动下类别是否改变，不是分类错误率或患者风险置信区间。概率SD还受各模型输出尺度和SVM校准影响。固定train改变10个算法种子的补充数据与训练样本扰动分开保存。')
    dif=read('paired_differences');rows=[]
    for r in dif[dif.metric=='roc_auc'].itertuples():rows.append([LABEL[r.model_a],LABEL[r.model_b],f'{r.point:+.4f}',f'[{r.low:+.4f}, {r.high:+.4f}]'])
    add_table('表12  固定模型验证AUC差值的配对分层Bootstrap条件区间',['模型A','模型B','差值AUC','百分位95%区间'],rows,widths=[3.1,3.1,3.0,5.5],font_size=8.8)
    caption('图7  主要配对模型AUC差值及条件区间；虚线标示零差值。')
    image('slide_intervals',width=14.8)
    para('区间以同一批类别分层验证索引成对重抽样2000次得到，保留同一记录上不同模型的配对关系。它条件于当前固定模型、validation经验分布和阳性/阴性数量；不涵盖模型重训、反复选型或新医院/新人群。验证样本已参与机制分析，因此这些区间不构成对经验证据挑选后赢家的无偏确认。AUC接近1时部分经验区间会退化，不能解读为总体不确定性消失。')

    heading('3.6 特征解释与计算成本',2)
    imp=read('feature_importance');topm=imp.nlargest(8,'mdi');topp=imp.nlargest(8,'permutation_auc_drop_mean')
    n_corr=int((read('correlated_feature_pairs').pearson_r.abs()>.9).sum())
    caption('图8  训练MDI与验证置换重要性；误差线为20次置换SD。')
    image('paper_importance',width=12.8)
    add_table('表13  主要特征重要性对照',['特征','RF训练MDI','验证置换AUC下降均值','置换SD'],[
        [r.feature,f'{r.mdi:.4f}',f'{r.permutation_auc_drop_mean:.5f}',f'{r.permutation_auc_drop_sd:.5f}'] for r in topm.itertuples()],
        widths=[5.1,3.0,4.3,2.3],font_size=9.0)
    DOC.add_page_break()
    caption('图9  训练集中尺寸特征Pearson相关矩阵。')
    image('paper_correlation',width=12.8)
    groups=read('grouped_permutation').groupby('group').auc_drop.agg(['mean','std'])
    para(f'训练数据435个特征对中，有{n_corr}对Pearson |r|>0.9。MDI按训练分裂分摊变量贡献；相关特征可分享分裂机会。验证置换衡量当前模型在特定验证分布中对单一特征排序信息的依赖，相关替代变量会缓冲打乱影响。worst radius、worst perimeter、worst area联合置换时平均AUC下降{groups.loc["worst_size","mean"]:.3f}（重复置换SD {groups.loc["worst_size","std"]:.3f}），但联合打乱可能破坏变量联合分布，也不构成因果效应。')
    times=d.cv[['fit_seconds_mean','roc_auc_mean']].copy()
    rows=[]
    for n in ['logistic','rbf_svm','single_tree','bagging','random_forest','adaboost','gradient_boosting']:
        r=d.cv.loc[n];vr=d.val.loc[n];nodes='—' if pd.isna(vr.total_nodes) else f'{int(vr.total_nodes)}'
        rows.append([LABEL[n],f'{r.fit_seconds_mean*1000:.2f}',nodes,'低' if n=='logistic' else ('中' if n in ['rbf_svm','single_tree'] else '较高')])
    add_table('表14  单线程每折拟合时间与固定train拟合模型规模',['模型','每折训练毫秒','总树节点数','全局解释成本（定性）'],rows,widths=[3.2,3.3,3.0,5.2],font_size=9.1)
    para('在当前小数据上，LR最易通过系数审阅且训练速度快，但特征共线会限制单个系数的解释；浅树规则可读但较不稳定；SVM需解释尺度、核边界和校准；集成包含多棵树，需要全局置换或局部分析。复杂度评价为定性说明，不是预设的临床可用性评分。wall time只代表本次单线程环境。')

    heading('4 讨论',1)
    heading('4.1 主要发现与机制含义',2)
    para('在WDBC开放开发数据上，Bagging和随机森林都比深单树获得更高五折排序表现，且训练扰动下类别翻转比例较低，支持“平均能提高不稳定树的稳健性”这一有限结论[2–4]。这并不说明模型能对真实患者输出更准确或更可校准的风险概率。')
    para('随机森林的节点特征随机化降低了本次树间概率相关性，却未降低验证记录方向的二值错误相关性。此结果不满足H2最直接的错误同步预测，也提醒读者：等方差等相关简化公式用于说明平均过程，并非把任一观测相关系数直接代入后就能精确预测分类性能。RF训练扰动表现与横截面树相关性回答的是不同统计问题。')
    para('LR和SVM的五折AUC已较高，集成的主收益来自超过单树，而非普遍超越简单分类器。LR成本低、可直接审阅参数，仍是合理首选基线；SVM与RF保留为性能和非线性候选。选择需要结合阈值下的假阴性代价、校准和外部证据，不能按本次单一指标排序机械决定。')

    heading('4.2 研究备忘录',2)
    memo=json.loads((RES/'research_memo.json').read_text(encoding='utf-8'))['text']
    p=DOC.add_paragraph();format_para(p,after=3);p.paragraph_format.left_indent=Cm(.65);p.paragraph_format.right_indent=Cm(.65)
    add_run(p,memo,11.5)

    heading('5 证据边界与后续工作',1)
    para('样本规模有限，WDBC形态变量高度相关且多个模型接近性能天花板；数据缺少患者分组、时间和机构字段，患者独立性无法从本表核验。固定验证仅114条且在机制研究中重复使用。没有进行嵌套调参、外部校准、临床阈值选择或外部队列验证。固定模型bootstrap不包含重训或人群变化，无法回答跨医院泛化。')
    para('后续研究应先预先确定候选模型、可接受漏诊成本、阈值、校准和净获益指标，再在协议锁定后一次性评价测试集。更有说服力的下一步是独立、多中心或时间外样本验证，并评估分层表现。CTG可作为独立数据上的方法对照；必须按recording_id分组划分和重抽样，普通逐行OOB可能偏乐观，不能把CTG称作WDBC模型的外部验证。')

    heading('6 结论',1)
    para('本研究在预设WDBC比较中发现，Bagging和随机森林较深单树改善了交叉验证排序表现，并在共享训练Bootstrap扰动下减少类别翻转。LR和RBF-SVM在开发集交叉验证中仍有竞争力，故当前结果不足以支持复杂模型必然替代简单基线。随机特征降低概率相关性，但本次二值错误相关性没有下降；Boosting训练损失下降也不保证验证损失持续下降。结论限于当前开放数据和验证协议，预测重要性不代表因果，当前良恶性分类不代表未来患病风险。')
    p=DOC.add_paragraph();format_para(p,WD_ALIGN_PARAGRAPH.CENTER,before=3,after=4,spacing=1.1)
    add_run(p,'锁定测试集尚未评价。',12,True,INK)

    DOC.add_page_break()
    heading('参考文献',1)
    refs=REFERENCES
    for i,(code,citation,url) in enumerate(refs,1):
        p=DOC.add_paragraph();format_para(p,after=3,spacing=1.12)
        p.paragraph_format.left_indent=Cm(.65);p.paragraph_format.first_line_indent=Cm(-.65)
        add_run(p,f'[{i}] {citation} ',10.5)
        add_run(p,url,9.5,color=TEAL)
    DOC.core_properties.title='集成学习何时值得？乳腺肿块分类中的性能、稳定性与复杂度权衡'
    DOC.core_properties.subject='WDBC课程研究论文；锁定测试集尚未评价'
    DOC.core_properties.author='课程作业（作者信息待填写）'
    DOC.core_properties.keywords='集成学习；Bootstrap；随机森林；WDBC；模型稳定性'
    DOC.save(DOCX)
    return d

def export_pdf():
    import pythoncom,win32com.client
    pythoncom.CoInitialize();app=None;doc=None
    try:
        app=win32com.client.DispatchEx('Word.Application');app.Visible=False;app.DisplayAlerts=0
        doc=app.Documents.Open(str(DOCX.resolve()),ReadOnly=True,AddToRecentFiles=False,Visible=False)
        pages=int(doc.ComputeStatistics(2))
        doc.ExportAsFixedFormat(str(PDF.resolve()),17)
        doc.Close(False);doc=None
        return app.Version,pages
    finally:
        if doc is not None:doc.Close(False)
        if app is not None:app.Quit()

def inspect_pdf(word_version,word_pages):
    checks={'word_version':word_version,'word_reported_pages':word_pages,'pdf_exists':PDF.exists()}
    preview=DEST/'previews';preview.mkdir(exist_ok=True)
    extracted=[]
    with fitz.open(PDF) as pdf:
        checks['pdf_pages']=len(pdf);checks['page_size_points']=[round(pdf[0].rect.width,1),round(pdf[0].rect.height,1)]
        checks['page_aspect_ratio']=round(pdf[0].rect.width/pdf[0].rect.height,4)
        checks['page_text_lengths']=[]
        for i,page in enumerate(pdf,1):
            content=page.get_text();extracted.append(content);checks['page_text_lengths'].append(len(content))
            pix=page.get_pixmap(matrix=fitz.Matrix(1.25,1.25),alpha=False);pix.save(preview/f'paper_{i:02d}.png')
    all_text='\n'.join(extracted)
    checks['replacement_character_count']=all_text.count('\ufffd')
    required=['摘要','1 引言','2 材料与方法','3 结果','4 讨论','5 证据边界与后续工作','6 结论','参考文献','锁定测试集尚未评价']
    checks['required_headings']={h:h in all_text for h in required}
    checks['nonempty_pages']=all(x>30 for x in checks['page_text_lengths'])
    checks['references_not_orphaned']=checks['page_text_lengths'][-1]>350
    checks['created_at']=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
    (DEST/'pdf_check.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    if len(PDF.read_bytes())<20000 or checks['replacement_character_count'] or not checks['nonempty_pages'] or not checks['references_not_orphaned'] or not all(checks['required_headings'].values()):
        raise RuntimeError('Word/PDF export checks failed: '+json.dumps(checks,ensure_ascii=False))
    info={'built_at':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'python':sys.version,
          'platform':platform.platform(),'python_docx':importlib.metadata.version('python-docx'),
          'PyMuPDF':importlib.metadata.version('PyMuPDF'),'Microsoft_Word':word_version,
          'word_reported_pages':word_pages,'pdf_pages':checks['pdf_pages'],
          'paper_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'PDF_bytes':PDF.stat().st_size,'DOCX_bytes':DOCX.stat().st_size,
          'test_status':'锁定测试集尚未评价'}
    (DEST/'build_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(checks,ensure_ascii=False,indent=2))

def main():
    paper_figures();make_document();version,pages=export_pdf();inspect_pdf(version,pages)
    print('Word paper:',DOCX,'\nPDF paper:',PDF)

if __name__=='__main__':main()
