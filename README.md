# 健康大数据实践课程仓库

本仓库用于按课次保存课程材料、数据说明、作业代码、结果和研究文档，目标是让同学和老师能够顺着 README 复现结果并检查结论依据。

## 课程目录

| 课次/主题 | 仓库位置 | 当前状态 | 已发现的原始材料 |
| --- | --- | --- | --- |
| 第5课：多重检验 | `lessons/05-multiple-testing/` | 课件、数据、工作单和 Notebook 已归档；未运行 | `5-multiple-test.zip`、`第五课作业_多重检验校正.docx` |
| 第6课：朴素贝叶斯 | `lessons/06-naive-bayes/` | 课件、学生数据、工作单和代码已归档；编号待核对 | `6.Naive-Bayes.zip`、`朴素贝叶斯.docx` |
| 第7课：线性模型 | `lessons/07-linear-models/` | 课件、数据、工作单和 Notebook 已归档；编号待核对 | `7. Linear-models.zip`、`Linear-models-作业/` |
| 第9课：Ensemble 压缩包 | `lessons/09-ensemble-archive-pending-review/` | 课件、学生数据、工作单和脚本已归档；与第10课关系待核对 | `9. Ensemble.zip` |
| 第9课：SVM | `lessons/09-svm-pending-review/` | 课件、学生数据、工作单和代码已归档；编号待核对 | `9. SVM.zip`、SVM课件及作业文件 |
| Ensemble 作业样板 | `lessons/10-ensemble/` | 已整理第一份课程样板 | 当前 `10. Ensemble/` 项目 |
| 第11课：欠拟合与过拟合 | [课次目录](lessons/11-overfitting/) | 课件、数据、实验代码、已有结果及论文已归档 | `11. Over-fitting/` |

现有材料中同时出现 `9. Ensemble.zip` 和 `10. Ensemble/`。在核对材料内容前，暂时分别记录。其他课程的 `slides/`、`data/`、`homework/`、`notebooks/` 与 `scripts/` 保存从对应课程压缩包中摘出的课件、学生数据、工作单和实际代码；这些 Notebook/脚本尚未运行，且未生成新的结果或研究报告。细节见各课 README。

## 目录约定

每课使用相同的基本结构；只放该课实际需要的文件：

```text
lessons/<课次-主题>/
├── README.md          # 研究问题、数据说明、运行方法、证据边界
├── slides/            # 课程课件和汇报材料
├── data/              # 数据来源、字段说明；只放允许共享的数据
├── notebooks/         # 课堂 Notebook
├── scripts/           # Python 脚本和辅助模块
├── notebooks/         # 可选分析笔记本
├── outputs/           # 结果表、图表和运行记录
├── homework/          # 工作单、作业材料
├── report/            # 研究报告或论文
└── reflection.md      # 同伴复现、失败记录和下一步
```

## 当前样板：Ensemble

`lessons/10-ensemble/` 使用原课程划分中的学生训练集和验证集，包含课件、作业、实验脚本、结果、研究报告、论文、可编辑汇报、A—H 工作单和 AI 对话整理记录。其 `README.md` 提供本课导航与运行说明。虚拟环境、教师文件、锁定测试标签和模型缓存没有复制到课程仓库。

## 开始与验收

先选择一课，补全该课 README，确认数据共享边界，按 README 命令运行并记录结果；再请同伴按说明复现。完成样板后，逐步整理其它课次。

完整流程和建议的版本记录方式见 [COURSE_WORKFLOW.md](COURSE_WORKFLOW.md)。老师发的项目型任务说明放在 [course-materials/](course-materials/)。

