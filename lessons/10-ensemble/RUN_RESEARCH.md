# 一键复现与交付索引

在本项目目录的 PowerShell 中运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\run_research.ps1
```

脚本在项目 `.venv` 内安装 `requirements-research.txt`，然后运行实验、核验来源、生成图表、报告、工作单、PPT及备注，尝试用已安装的 Microsoft PowerPoint 导出PDF，最后做数值/文件审核。一般个人电脑核心实验约1–3分钟，安装和排版导出另计。本机实际运行时间见 `outputs/results/run_info.json`。首次依赖下载可使用清华PyPI镜像；不会更改全局Python环境。网络不可用时，只要已有完整环境，实验与图表仍可离线运行，公开来源检查会记录失败状态。

若当前机器禁止PowerShell脚本，可逐行执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-research.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
.\.venv\Scripts\python.exe -X utf8 scripts/run_research.py
.\.venv\Scripts\python.exe -X utf8 scripts/verify_sources.py
.\.venv\Scripts\python.exe -X utf8 scripts/make_figures.py
.\.venv\Scripts\python.exe -X utf8 scripts/make_report.py
.\.venv\Scripts\python.exe -X utf8 scripts/build_research_presentation.py
.\.venv\Scripts\python.exe -X utf8 scripts/export_and_check_presentation.py
.\.venv\Scripts\python.exe -X utf8 scripts/audit_research.py
```

复现实验的精确全量依赖锁定见 `outputs/results/pip_freeze.txt`；顶层依赖固定在 `requirements-research.txt`。可在新环境将前者作为requirements使用。Windows的PowerPoint PDF导出需要本机Office，实验、PPTX、PNG/SVG/PDF科学图稿不依赖Office。

## 阅读顺序

- `outputs/presentation/ensemble_report.pptx`：可编辑16:9正式汇报，16页正文+4页备份；主结果点线图、文字、表格和机制框图为原生对象。
- `outputs/presentation/ensemble_report.pdf`：本机PowerPoint导出的演示稿。
- `outputs/presentation/speaker_notes.md`：与PPT备注一致的逐页讲稿，正文建议11.1分钟。
- PPT 与 Word 的逐页预览缓存未复制；可按本页的一键命令重新生成。
- `outputs/report.md`：研究报告、真实结果、解释、局限及引用。
- `outputs/worksheet_completed.md`：A—H完整回答与250—400字备忘录。
- `outputs/paper/ensemble_study_paper.docx`：独立整理成论文结构的可编辑Word课程作业稿。
- `outputs/paper/ensemble_study_paper.pdf`：由本机Microsoft Word导出的对应PDF；含中英文摘要、关键词、引言、材料与方法、结果表和图、讨论、限制、结论及参考文献。作者姓名和班级留空供学生填写。
- `outputs/paper/pdf_check.json`、`build_info.json`：页数、中文文字提取、字体替代符与 Word 版本检查记录。逐页预览缓存未复制。构建脚本：`scripts/build_academic_paper.py`，论文专用图：`scripts/make_paper_figures.py`。
- `outputs/protocol.md`：首次实验运行前固定的假设与协议，不是公共预注册。
- `outputs/results/`：每折指标、OOF预测、验证预测、全部参数/版本/种子/哈希/计时、重抽样索引和结果、重要性及引用检查。
- `outputs/figures/`：科研图和投影专用图，每图PNG+SVG+PDF。PPT中的科学图嵌入PNG以保持投影稳定，矢量源和绘图代码可继续编辑。
- 拟合模型文件未复制；需要时可按研究脚本重新训练。
- `outputs/audit.md`、`outputs/results/audit_checks.json`：数值和交付审核。

## 分析边界与必要假设

仅WDBC主实验；不扩展CTG。只读原 `data/student/train.csv` 和 `validation.csv`，不重建划分，不读取teacher、完整原始数据、锁定测试标签或测试特征。**锁定测试集尚未评价。** 样本ID不参与建模；原始数据与课程课件保留。`demo_ensemble.py`的错误输出路径已修正为项目内 `outputs/demo/<数据名>/`。

开发集共享五折是预设参数主比较；固定验证用于机制和稳定性，两者共享样本。探索曲线不改变主模型。SVM为训练内部三折sigmoid校准的标准化Pipeline（非调参），统一概率≥.5分类。训练bootstrap内部校准按原训练行分组。模型间概率尺度不同，概率SD不能独立当作稳定性总排名。普通记录bootstrap假设记录近似独立，但WDBC缺少患者分组，不能核验患者独立性。

## 结果文件结构

| 文件组 | 内容 |
| --- | --- |
| `cv_assignments` / `cv_per_fold` / `cv_summary` / `cv_oof_predictions` | 共享五折分配、每折指标、摘要、逐样本OOF概率 |
| `validation_metrics` / `validation_predictions` | 所有8模型固定验证指标及预测，阈值.5 |
| `tree_depth` / `bootstrap_tree_roots` / `example_tree_*` | 树深、30次根节点变化、真实浅树结构 |
| `bootstrap_sampling` | n=341及n=5各2000次独特/OOB比例 |
| `tree_count_curve` / `tree_*correlation*` | 1/10/50/100/300树、RF-all对照、相关性及OOB |
| `boosting_curves` / `adaboost_*` / `gradient_directions` | 探索性阶段曲线、实际SAMME权重、GB负梯度 |
| `stability_*` / `training_bootstrap_indices.npz` | 30份共享训练重抽样、全部预测、逐样本波动及摘要 |
| `algorithm_seed_stability` | 固定train、变化10个算法种子的补充 |
| `paired_*` / `fixed_model_intervals` | 2000次固定模型验证分层成对重抽样、配对差值及区间 |
| `feature_importance` / `permutation_repeats` / `grouped_permutation` / `feature_correlation` | 同一RF100的MDI、20次验证置换、组置换及train相关性 |
| `fit_times` / `run_info` / `pip_freeze` | 每次拟合计时、全部预设参数、随机种子、版本、哈希 |

所有CSV使用UTF-8 BOM以兼容Excel，JSON/Markdown/Python使用UTF-8；浮点原始精度在CSV中保留，报告/PPT统一四舍五入。

