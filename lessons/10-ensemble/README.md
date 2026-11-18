# Ensemble：集成学习与 Bootstrapping

本课目录是课程仓库的第一份样板，整理了原项目 `10. Ensemble` 的 WDBC 分析、工作单、论文和汇报。原项目保持不变。本目录中的代码可独立运行。

## 研究问题

在 WDBC 恶性分类中，Bagging、随机森林和 Boosting 相比单树改善了什么？训练数据改变时预测是否更稳定？综合表现、稳定性、计算和解释成本，复杂模型是否值得替代逻辑回归或 RBF-SVM？

## 数据与边界

- 只包含课程原有的学生 `train.csv` 与 `validation.csv`，标签为 `malignant=1`。
- `sample_id` 仅追踪记录，不作为特征。
- 本次实验未评价锁定测试集；数据缺少患者分组信息，不能核验患者独立性。
- 教师参考材料、教师测试标签、完整测量表、锁定测试特征和 CTG 原始数据没有复制。
- 结论只适用于本数据和本验证协议，不表示未来患病风险、因果关系或外部人群表现。

## 复现

在本目录的 PowerShell 中运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\run_research.ps1
```

该脚本建立本地 `.venv`，运行实验、图表、报告、论文、汇报和审计脚本。具体步骤、环境版本和各 CSV 内容见 [RUN_RESEARCH.md](RUN_RESEARCH.md)。

## 仓库内容

- `data/`：允许共享的学生训练/验证划分与数据说明。
- `scripts/`：分析、图表、报告、论文和汇报生成脚本；保留项目内输出路径。
- `AI-conversations/`：课程相关 AI 对话整理记录；文件注明了摘要与逐字记录的区别。
- `outputs/results/`：每折与验证指标、预测、重抽样、重要性、计时、引用和运行信息。
- `outputs/figures/`：PNG、SVG、PDF 图稿。
- `outputs/report.md`、`outputs/worksheet_completed.md`：研究报告与 A—H 工作单。
- `outputs/paper/`：论文 Word/PDF；
- `outputs/presentation/`：课堂汇报 PPT/PDF 和逐页讲稿。
- `homework/`：原学生工作单及已完成工作单。
- `slides/`：原课程 PBL 课件。
- `reflection.md`：留给同伴复现和课程反思记录。

## 按助教要求查看本课材料

课件在 `slides/`，学生数据和说明在 `data/`，工作单及完成稿在 `homework/`，研究代码在 `scripts/`，论文在 `report/`，实验结果和汇报材料在 `outputs/`。AI 对话整理记录见 [`AI-conversations/ensemble-learning-dialogue.md`](AI-conversations/ensemble-learning-dialogue.md)。

拟合后的 joblib 模型和本机虚拟环境不纳入仓库；运行脚本会按需重新生成模型文件。
