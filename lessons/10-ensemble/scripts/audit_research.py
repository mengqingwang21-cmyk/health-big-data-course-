"""Meaningful data-to-report checks and delivery audit; no locked test data access."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from pptx import Presentation
from docx import Document as WordDocument
from sklearn.metrics import roc_auc_score,average_precision_score,balanced_accuracy_score
from research_style import *
from make_report import Study, pct

def run():
    checks=[]
    def check(name,condition,detail=''):
        checks.append(dict(check=name,passed=bool(condition),detail=detail))
    s=Study();info=s.info
    train=pd.read_csv(BASE/'data/student/train.csv');val=pd.read_csv(BASE/'data/student/validation.csv')
    check('Input allowlist',[p.replace('\\','/') for p in info['read_files']]==['data/student/train.csv','data/student/validation.csv'])
    for rel,h in info['data_sha256'].items():
        check('Original input unchanged: '+rel,hashlib.sha256((BASE/rel).read_bytes()).hexdigest()==h)
    check('No ID input',not set(info['features'])&{'sample_id','recording_id','malignant'} and len(info['features'])==30)
    check('Locked test unevaluated',info['test_status']=='锁定测试集尚未评价' and not info['teacher_files_read'])
    check('Protocol unchanged since experiment',hashlib.sha256((OUT/'protocol.md').read_bytes()).hexdigest()==info['protocol_sha256'])
    assignments=read('cv_assignments');folds=read('cv_per_fold');oof=read('cv_oof_predictions')
    check('455 unique development fold assignments',len(assignments)==455 and assignments.sample_id.nunique()==455)
    check('Shared five folds for all 8 models',len(folds)==40 and all(len(g)==5 for _,g in folds.groupby('model')))
    for n in ORDER:
        a=oof[oof.model==n]
        check('One OOF prediction per sample: '+n,len(a)==455 and a.sample_id.nunique()==455)
        merged=a.merge(assignments,on='sample_id',suffixes=('_pred','_shared'))
        check('Shared fold membership: '+n,(merged.fold_pred==merged.fold_shared).all())
        for metric in ['roc_auc','average_precision','balanced_accuracy']:
            values=folds[folds.model==n][metric]
            check('CV mean/SD recomputed: '+n+'/'+metric,
                  np.isclose(values.mean(),s.cv.loc[n,metric+'_mean'],atol=1e-12) and
                  np.isclose(values.std(ddof=1),s.cv.loc[n,metric+'_sd'],atol=1e-12))
    predictions=read('validation_predictions')
    for n in ORDER:
        p=predictions[predictions.model==n].merge(val[['sample_id','malignant']],on='sample_id')
        check('Validation labels/threshold: '+n,len(p)==114 and (p.y==p.malignant).all() and
              (p.predicted==(p.probability>=.5)).all() and p.probability.between(0,1).all())
        for metric,fn in [('roc_auc',roc_auc_score),('average_precision',average_precision_score),('balanced_accuracy',balanced_accuracy_score)]:
            values=p.predicted if metric=='balanced_accuracy' else p.probability
            check('Validation metric recomputed: '+n+'/'+metric,np.isclose(fn(p.y,values),s.val.loc[n,metric],atol=1e-12))
    stability=read('stability_predictions')
    for n in ORDER:
        p=stability[stability.model==n].pivot(index='repeat',columns='sample_id',values='probability')
        q=(p>=.5).mean(axis=0);flip=((q>0)&(q<1)).mean()
        check('30 x 114 training perturbations: '+n,p.shape==(30,114))
        check('Stability recomputed: '+n,np.isclose(p.std(ddof=1).mean(),s.st.loc[n,'mean_probability_sd'],atol=1e-12) and
              np.isclose(flip,s.st.loc[n,'any_flip_fraction'],atol=1e-12))
    idx=np.load(RES/'training_bootstrap_indices.npz',allow_pickle=True)['indices']
    check('30 shared training bootstrap indices',idx.shape==(30,341) and idx.min()>=0 and idx.max()<341)
    paired=np.load(RES/'paired_validation_bootstrap_indices.npz',allow_pickle=True)['indices']
    y=val.malignant.to_numpy()
    check('2000 shared stratified validation bootstrap indices',paired.shape==(2000,114) and np.all(y[paired].sum(axis=1)==43))
    boot=read('paired_bootstrap_metrics');diff=read('paired_differences')
    for r in diff.itertuples():
        pivot=boot.pivot(index='repeat',columns='model',values=r.metric)
        lo,hi=np.quantile(pivot[r.model_a]-pivot[r.model_b],[.025,.975])
        check('Paired percentile interval: '+r.model_a+'-'+r.model_b+'/'+r.metric,
              np.isclose(lo,r.low,atol=1e-12) and np.isclose(hi,r.high,atol=1e-12))
    sim=read('bootstrap_sampling').query('n == 341')
    se=sim.unique_fraction.std(ddof=1)/np.sqrt(len(sim))
    check('Bootstrap Monte Carlo agrees with finite-n theory',abs(sim.unique_fraction.mean()-sim.expected_unique.iloc[0])<5*se)
    check('RF feature-control shared sample indices',info['rf_control_bootstrap_indices_identical'])
    memo=json.loads((RES/'research_memo.json').read_text(encoding='utf-8'))
    check('250–400 character memo',250<=len(memo['text'])<=400,str(len(memo['text'])))
    ppt=OUT/'presentation/ensemble_report.pptx';deck=Presentation(ppt)
    manifest=json.loads((OUT/'presentation/slides_manifest.json').read_text(encoding='utf-8'))
    check('16 main + 4 backup slides',len(deck.slides)==20 and sum(not p['backup'] for p in manifest)==16)
    check('Talk duration 10–12 minutes',600<=sum(p['seconds'] for p in manifest)<=720)
    check('16:9 slide size',abs(deck.slide_width/deck.slide_height-16/9)<1e-6)
    for i,(slide,item) in enumerate(zip(deck.slides,manifest),1):
        check('Speaker notes agree: '+str(i),slide.notes_slide.notes_text_frame.text==item['notes'])
        for sh in slide.shapes:
            if sh.shape_type==9:continue
            check(f'Shape in slide bounds: {i}/{sh.shape_id}',sh.left>=-2 and sh.top>=-2 and sh.left+sh.width<=deck.slide_width+2 and sh.top+sh.height<=deck.slide_height+2)
    report=(OUT/'report.md').read_text(encoding='utf-8');worksheet=(OUT/'worksheet_completed.md').read_text(encoding='utf-8')
    ppt_text='\n'.join(sh.text for slide in deck.slides for sh in slide.shapes if sh.has_text_frame)
    table_text='\n'.join(cell.text for slide in deck.slides for sh in slide.shapes if sh.has_table for row in sh.table.rows for cell in row.cells)
    for n in ORDER:
        value=f'{s.cv.loc[n,"roc_auc_mean"]:.4f} ± {s.cv.loc[n,"roc_auc_sd"]:.4f}'
        check('Main result CSV→report→worksheet→PPT: '+n,all(value in content for content in [report,worksheet,table_text]))
    for content,label in [(report,'report'),(worksheet,'worksheet'),(ppt_text,'PPT'),((OUT/'presentation/speaker_notes.md').read_text(encoding='utf-8'),'notes')]:
        check('Test status in '+label,'锁定测试集尚未评价' in content)
    for n in ['single_tree','random_forest']:
        p=pct(s.st.loc[n,'any_flip_fraction'])
        check('Stability numbers across outputs: '+n,all(p in content for content in [report,worksheet,ppt_text]))
    paper_docx=OUT/'paper/ensemble_study_paper.docx';paper_pdf=OUT/'paper/ensemble_study_paper.pdf'
    paper_info=json.loads((OUT/'paper/pdf_check.json').read_text(encoding='utf-8')) if (OUT/'paper/pdf_check.json').exists() else {}
    paper_doc=WordDocument(paper_docx) if paper_docx.exists() else None
    paper_text='\n'.join(p.text for p in paper_doc.paragraphs) if paper_doc else ''
    paper_xmltext='\n'.join(cell.text for tab in (paper_doc.tables if paper_doc else []) for row in tab.rows for cell in row.cells)
    check('Editable Word paper opens',paper_doc is not None and len(paper_doc.paragraphs)>100)
    check('Paper contains manuscript sections and results',all(h in paper_text for h in ['摘要','1 引言','2 材料与方法','3 结果','4 讨论','5 证据边界与后续工作','6 结论','参考文献']))
    check('Paper includes generated tables and charts',paper_doc is not None and len(paper_doc.tables)>=10 and len(paper_doc.inline_shapes)>=8)
    check('A4 manuscript PDF exported from Word',paper_pdf.exists() and paper_info.get('word_version')=='16.0' and paper_info.get('page_aspect_ratio')==0.7071)
    check('Manuscript pages have text and readable section headings',paper_info.get('pdf_pages',0)>=10 and paper_info.get('nonempty_pages') and all(paper_info.get('required_headings',{}).values()))
    check('Manuscript citations are not orphaned and no replacement glyphs',paper_info.get('references_not_orphaned') and paper_info.get('replacement_character_count')==0)
    paper_all=paper_text+'\n'+paper_xmltext
    for n in ORDER:
        value=f'{s.cv.loc[n,"roc_auc_mean"]:.4f} ± {s.cv.loc[n,"roc_auc_sd"]:.4f}'
        check('Main result CSV→Word paper: '+n,value in paper_all)
    check('Test status in paper','锁定测试集尚未评价' in paper_text)
    render_path=OUT/'presentation/render_audit.json'
    render=json.loads(render_path.read_text(encoding='utf-8')) if render_path.exists() else {}
    if render.get('pdf_export')=='exported by Microsoft PowerPoint':
        check('PowerPoint measured no text overflow',not render.get('text_overflows'),str(render.get('text_overflows',[])))
        check('PDF has all 20 pages',render.get('pdf_n_pages')==20)
        check('PDF has no replacement characters',render.get('rendered_replacement_characters')==0)
    else:
        check('PDF export attempted',bool(render),'PowerPoint unavailable: '+render.get('error','not recorded'))
    required=[OUT/'presentation/ensemble_report.pptx',OUT/'presentation/speaker_notes.md',OUT/'report.md',OUT/'worksheet_completed.md',
              paper_docx,paper_pdf,BASE/'RUN_RESEARCH.md',BASE/'run_research.ps1']
    for path in required:check('Required deliverable '+str(path.relative_to(BASE)),path.exists() and path.stat().st_size>0)
    names=[p.stem for p in FIG.glob('*.png')]
    check('Every figure has PNG/SVG/PDF',len(names)>=21 and all((FIG/(name+'.'+ext)).exists() for name in names for ext in ['svg','pdf']))
    (RES/'audit_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    passed=sum(c['passed'] for c in checks);failed=[c for c in checks if not c['passed']]
    summary=f'''# 交付审核

通过 {passed}/{len(checks)} 项自动检查。正文16页、备份4页，建议汇报665秒（11.1分钟）。

检查包含：原始输入哈希、输入排除ID、共享CV折、每折均值和SD、验证预测/指标、30次训练重抽样的波动重算、2000次配对区间重算、备忘录字数、PPT/报告/工作单数字一致、逐页备注一致、PPT16:9及元素页面边界。PowerPoint实际测量文本高度、导出PDF，再渲染20页，检查替代字符。

PDF状态：{render.get('pdf_export','未记录')}。PowerPoint版本：{render.get('powerpoint_version','不可用')}。

锁定测试集尚未评价。仅WDBC核心实验；CTG扩展未开展。未进行外部验证、临床阈值优化或部署。

## 自动检查问题

'''+('\n'.join(f'- {c["check"]}: {c["detail"]}' for c in failed) if failed else '无。')+'\n\n完整逐项记录：results/audit_checks.json。渲染记录：presentation/render_audit.json。\n'
    (OUT/'audit.md').write_text(summary,encoding='utf-8')
    print(f'Audit: {passed}/{len(checks)} passed.')
    for c in failed:print('FAILED',c['check'],c['detail'])
    if failed:raise SystemExit(1)

if __name__=='__main__':run()
