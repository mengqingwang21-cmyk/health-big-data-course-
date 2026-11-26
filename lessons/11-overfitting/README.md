# 第 11 讲：欠拟合与过拟合的识别

**模型看起来很好，为什么可能是假的？**

学生先自学 5 个核心概念（泛化与数据角色、欠拟合与过拟合、过拟合的原因与征兆、信息泄露、选择偏差与分布变化），再用 7 个对照实验回答 Q1–Q7，最后在 Q8 中设计或审查一个模型评价流程。

## 材料

- `slides/overfitting-pbl-questions.pptx`：课堂启动课件（19 页），概念页与探究问题交替展开。由 `scripts/build_slides.py` 生成（需要 python-pptx）。
- `student-worksheet.md`：默认工作单模板，学生可以改写或换成自己的数据。
- [已完成工作单](worksheet-completed.md)、[论文修订版](论文修订版.md)及 [Word 稿](王梦晴_过拟合与评价偏差_论文修订版.docx)。
- [实验结果和图表](results/)：保留原作业生成的表格、图稿与分析记录。
- `workplan.md`：概念与问题对应、与课程大纲的对应、三阶段安排。
- `experiment-design.md`：E1–E7 的数据、对照和输出文件。
- `data/`：WDBC 与两份模拟数据；备选数据 Golub 白血病见 `data/README.md`。
- `scripts/run_experiments.py`：实验脚本，可以只运行单个实验。

## 运行

在本课目录打开终端：

```powershell
python -m pip install -r requirements.txt
python scripts/run_experiments.py --experiment E1
python scripts/run_experiments.py
```

上面的实验命令将新结果写到本课 `.tmp/lesson11/`。实验条件（树深度、样本量、噪声特征数、筛选数、候选数）在脚本顶部，可以修改。默认读取随课程提供的 CSV。

如需重新生成归档中的分析结果，先安装文稿和绘图依赖，再运行 PowerShell 脚本。该脚本会更新 `results/` 中的已有文件。

```powershell
python -m pip install -r requirements-artifacts.txt
.\run_assignment.ps1
```

WDBC 的留出集是验证集，不是独立测试集；E6、E7 是模拟，不代表真实的外部临床验证。
