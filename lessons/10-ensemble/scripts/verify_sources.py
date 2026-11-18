"""Verify public bibliographic/documentation links; never downloads any dataset."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import re
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parents[1]
REFERENCES=[
 ('D1','Wolberg, Street & Mangasarian. Breast Cancer Wisconsin (Diagnostic). UCI (1995). DOI:10.24432/C5DW2B.',
  'https://archive.ics.uci.edu/dataset/17/breast+cancer+wisconsin+diagnostic'),
 ('R1','Efron B. Bootstrap Methods: Another Look at the Jackknife. Annals of Statistics 7(1):1–26 (1979). DOI:10.1214/aos/1176344552.',
  'https://doi.org/10.1214/aos/1176344552'),
 ('R2','Breiman L. Bagging Predictors. Machine Learning 24:123–140 (1996). DOI:10.1007/BF00058655.',
  'https://doi.org/10.1007/BF00058655'),
 ('R3','Breiman L. Random Forests. Machine Learning 45:5–32 (2001). DOI:10.1023/A:1010933404324.',
  'https://doi.org/10.1023/A:1010933404324'),
 ('R4','Freund Y, Schapire RE. A Decision-Theoretic Generalization of On-Line Learning and an Application to Boosting. JCSS 55(1):119–139 (1997). DOI:10.1006/jcss.1997.1504.',
  'https://doi.org/10.1006/jcss.1997.1504'),
 ('R5','Friedman JH. Greedy Function Approximation: A Gradient Boosting Machine. Annals of Statistics 29(5):1189–1232 (2001). DOI:10.1214/aos/1013203451.',
  'https://doi.org/10.1214/aos/1013203451'),
 ('R6','Chen T, Guestrin C. XGBoost: A Scalable Tree Boosting System. KDD (2016):785–794. DOI:10.1145/2939672.2939785.',
  'https://arxiv.org/abs/1603.02754'),
 ('R7','Ke G et al. LightGBM: A Highly Efficient Gradient Boosting Decision Tree. NeurIPS 30 (2017).',
  'https://papers.nips.cc/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html'),
 ('S1','scikit-learn 1.7 User Guide: Ensemble methods.',
  'https://scikit-learn.org/1.7/modules/ensemble.html'),
 ('S2','scikit-learn 1.7 API: average_precision_score (non-interpolated AP).',
  'https://scikit-learn.org/1.7/modules/generated/sklearn.metrics.average_precision_score.html'),
 ('S3','scikit-learn 1.7 User Guide: Probability calibration.',
  'https://scikit-learn.org/1.7/modules/calibration.html'),
 ('S4','scikit-learn 1.7 User Guide: Permutation feature importance.',
  'https://scikit-learn.org/1.7/modules/permutation_importance.html'),
 ('S5','XGBoost official documentation: Introduction to Boosted Trees.',
  'https://xgboost.readthedocs.io/en/stable/tutorials/model.html'),
 ('S6','LightGBM official documentation: Features.',
  'https://lightgbm.readthedocs.io/en/stable/Features.html'),
]

def verify(ref):
    code,citation,url=ref
    out=dict(id=code,citation=citation,url=url,checked_at=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat())
    try:
        response=requests.get(url,timeout=(8,18),headers={'User-Agent':'Mozilla/5.0 (academic classroom reference verification)'})
        title=re.search(r'<title[^>]*>(.*?)</title>',response.text,re.S|re.I)
        out.update(http_status=response.status_code,resolved_url=response.url,
                   page_title=re.sub(r'\s+',' ',title.group(1)).strip() if title else '',
                   status='HTTP checked' if response.ok else 'access limited; bibliographic identifier provided')
    except requests.RequestException as exc:
        out.update(status='network check unavailable; bibliographic identifier provided',error=str(exc))
    return out

if __name__=='__main__':
    out=BASE/'outputs/results';out.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as pool: results=list(pool.map(verify,REFERENCES))
    (out/'reference_checks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    for r in results: print(r['id'],r.get('http_status','network unavailable'),r.get('page_title','')[:100])
