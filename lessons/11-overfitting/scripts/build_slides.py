"""Build slides/overfitting-pbl-questions.pptx with python-pptx.

Run from the lesson folder:  python scripts/build_slides.py
"""
from pathlib import Path
import math

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Pt

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'slides' / 'overfitting-pbl-questions.pptx'

FONT = 'Microsoft YaHei'
INK, MUTED, TEAL = '173D3D', '526969', '087C77'
PAPER, LINE, TINT = 'FAFBF8', 'D7E2DF', 'EAF3F1'
WARM, WARM_TINT, MINT = 'C0602A', 'F8EDE5', 'AFDCD0'
WHITE = 'FFFFFF'
L, W = 52, 856            # left margin and content width, in pt (slide is 960 x 540 pt)
FOOTER = '第 11 讲　欠拟合与过拟合的识别'

prs = Presentation()
prs.slide_width, prs.slide_height = Pt(960), Pt(540)
BLANK = prs.slide_layouts[6]


def rgb(h):
    return RGBColor.from_string(h)


def style_run(run, size, color, bold=False):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = rgb(color)
    rpr = run._r.get_or_add_rPr()
    rpr.set('lang', 'zh-CN')
    rpr.set('altLang', 'en-US')
    for tag in ('a:latin', 'a:ea', 'a:cs'):
        el = rpr.find(qn(tag))
        if el is None:
            el = etree.SubElement(rpr, qn(tag))
        el.set('typeface', FONT)


def fill_frame(tf, paras, size, color, bold=False, align=PP_ALIGN.LEFT, spacing=1.15, after=4):
    """paras: list of paragraphs; each is a str, or a list of (text, overrides) runs.
    A paragraph given as ('•', text) becomes a bullet item."""
    tf.word_wrap = True
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        p.space_after = Pt(after)
        bullet = isinstance(para, tuple) and para[0] == '•'
        if bullet:
            para = para[1]
            ppr = p._p.get_or_add_pPr()
            ppr.set('marL', str(Pt(size * 0.95)))
            ppr.set('indent', str(-Pt(size * 0.95)))
            bu = etree.SubElement(ppr, qn('a:buChar'))
            bu.set('char', '•')
        runs = [(para, {})] if isinstance(para, str) else para
        for text, opt in runs:
            r = p.add_run()
            r.text = text
            style_run(r, opt.get('size', size), opt.get('color', color), opt.get('bold', bold))


def text(slide, x, y, w, h, paras, size=18, color=INK, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, spacing=1.15, after=4):
    box = slide.shapes.add_textbox(Pt(x), Pt(y), Pt(w), Pt(h))
    tf = box.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    fill_frame(tf, paras if isinstance(paras, list) else [paras], size, color, bold, align, spacing, after)
    return box


def rect(slide, x, y, w, h, fill, line=None, shape=MSO_SHAPE.RECTANGLE):
    s = slide.shapes.add_shape(shape, Pt(x), Pt(y), Pt(w), Pt(h))
    s.fill.solid()
    s.fill.fore_color.rgb = rgb(fill)
    if line:
        s.line.color.rgb = rgb(line)
        s.line.width = Pt(0.75)
    else:
        s.line.fill.background()
    s.shadow.inherit = False
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = 0.06
    return s


def card(slide, x, y, w, h, paras, size=16, fill=TINT, color=INK, pad=14, anchor=MSO_ANCHOR.TOP):
    s = rect(slide, x, y, w, h, fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    tf = s.text_frame
    tf.margin_left = tf.margin_right = Pt(pad)
    tf.margin_top = tf.margin_bottom = Pt(pad * 0.8)
    tf.vertical_anchor = anchor
    fill_frame(tf, paras, size, color)
    return s


def line(slide, x1, y1, x2, y2, color=INK, width=1.25, arrow=False, dash=False):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Pt(x1), Pt(y1), Pt(x2), Pt(y2))
    c.line.color.rgb = rgb(color)
    c.line.width = Pt(width)
    ln = c.line._get_or_add_ln()
    if dash:
        etree.SubElement(ln, qn('a:prstDash')).set('val', 'dash')
    if arrow:
        tail = etree.SubElement(ln, qn('a:tailEnd'))
        tail.set('type', 'triangle')
    return c


def curve(slide, fn, x0, y0, w, h, color, width=3, steps=60):
    """Plot fn: [0,1] -> [0,1] inside the box (x0, y0, w, h); y=1 is the top."""
    pts = [(x0 + w * t / steps, y0 + h * (1 - fn(t / steps))) for t in range(steps + 1)]
    ff = slide.shapes.build_freeform(Pt(pts[0][0]), Pt(pts[0][1]), scale=1.0)
    ff.add_line_segments([(Pt(px), Pt(py)) for px, py in pts[1:]], close=False)
    s = ff.convert_to_shape()
    s.fill.background()
    s.line.color.rgb = rgb(color)
    s.line.width = Pt(width)
    s.shadow.inherit = False
    return s


def table(slide, rows, x, y, widths, row_h, size=15, header_fill=INK, first_col_bold=False):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), Pt(x), Pt(y), Pt(sum(widths)), Pt(row_h * len(rows)))
    tbl = shape.table
    tbl_pr = shape._element.graphic.graphicData.tbl.tblPr
    tbl_pr.set('bandRow', '0')
    tbl_pr.set('firstRow', '0')
    for j, wd in enumerate(widths):
        tbl.columns[j].width = Pt(wd)
    for i, row in enumerate(rows):
        tbl.rows[i].height = Pt(row_h)
        for j, value in enumerate(row):
            cell = tbl.cell(i, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = rgb(header_fill if i == 0 else (PAPER if i % 2 else WHITE))
            cell.margin_left = cell.margin_right = Pt(8)
            cell.margin_top = cell.margin_bottom = Pt(4)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = cell.text_frame
            tf.paragraphs[0].text = ''
            head = i == 0
            fill_frame(tf, [value], size, WHITE if head else INK,
                       bold=head or (first_col_bold and j == 0), spacing=1.05, after=0)
            tc_pr = cell._tc.get_or_add_tcPr()
            for side in ('a:lnL', 'a:lnR', 'a:lnT', 'a:lnB'):
                ln = etree.SubElement(tc_pr, qn(side))
                ln.set('w', str(Pt(0.75)))
                sf = etree.SubElement(ln, qn('a:solidFill'))
                etree.SubElement(sf, qn('a:srgbClr')).set('val', LINE)
            # schema order: borders must come before the cell fill
            fill_el = tc_pr.find(qn('a:solidFill'))
            if fill_el is not None:
                tc_pr.remove(fill_el)
                tc_pr.append(fill_el)
    return shape


def new_slide(tag, title, notes=''):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = rgb(PAPER)
    text(s, L, 30, W, 20, tag, 14, TEAL, bold=True)
    text(s, L, 52, W, 46, title, 29, INK, bold=True)
    text(s, L, 508, 600, 16, FOOTER, 11, MUTED)
    text(s, 860, 508, 48, 16, f'{len(prs.slides):02d}', 11, MUTED, align=PP_ALIGN.RIGHT)
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


def box_height(body, width, size):
    units = sum(1.0 if ord(ch) > 0x2E80 else 0.55 for ch in body)
    lines = math.ceil(units * size / (width - 6))
    return max(72, 34 + lines * size * 1.55)


def task(tag, title, experiment, do, answer, extra='', notes=''):
    """Inquiry slide: the same frame for every question, so students can scan it."""
    s = new_slide(tag, title, notes)
    rows = [('实验', experiment), ('你要做', do), ('要回答', answer)]
    y = 122
    heights = [box_height(body, W - 138, 19) for _, body in rows]
    for (label, body), h in zip(rows, heights):
        rect(s, L, y, W, h, TINT if label != '要回答' else WARM_TINT, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        text(s, L + 18, y + 16, 90, 24, label, 18, TEAL if label != '要回答' else WARM, bold=True)
        text(s, L + 118, y + 15, W - 138, h - 24, body, 19, INK, spacing=1.25)
        y += h + 16
    if extra:
        text(s, L, y + 6, W, 40, extra, 15, MUTED, spacing=1.2)
    return s


# 01 cover --------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
s.background.fill.solid()
s.background.fill.fore_color.rgb = rgb(INK)
text(s, 60, 80, 820, 26, '生物医学数据科学　第 11 讲', 18, MINT)
text(s, 60, 150, 840, 150, ['模型看起来很好，', '为什么可能是假的？'], 46, WHITE, bold=True, spacing=1.1)
text(s, 60, 330, 840, 34, '欠拟合与过拟合的识别', 26, MINT, bold=True)
text(s, 60, 378, 840, 30, '先自学概念，再预测、做对照实验，用证据回答问题', 18, 'D6E8E3')
s.notes_slide.notes_text_frame.text = (
    '课堂启动约 20 分钟：重点讲概念页（第 4–6、8、11、14 页）和小结页，任务页只需说明每个实验在比较什么。'
    '学生课后自学并完成实验，下次翻转课堂随机抽签讲解。')

# 02 three questions -----------------------------------------------------------------
s = new_slide('导入', '本课要回答的三个问题',
              '对应课程大纲第 10a 讲的三个核心问题。三个问题由浅入深：先会识别，再知道原因，最后学会审查评价流程。')
qs = [('01', '什么是欠拟合和过拟合？', '怎样从训练表现与验证表现中把它们识别出来'),
      ('02', '哪些条件让模型更容易过拟合？', '模型复杂度、样本量、特征数，以及过拟合留下的征兆'),
      ('03', '为什么评价分数会“虚高”？', '信息泄露、反复挑选最高分、新中心的分布变化')]
y = 124
for num, head, sub in qs:
    rect(s, L, y, W, 96, TINT, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, L + 24, y + 20, 80, 56, num, 38, TEAL, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    text(s, L + 116, y + 18, W - 140, 30, head, 22, INK, bold=True)
    text(s, L + 116, y + 54, W - 140, 26, sub, 16, MUTED)
    y += 110
text(s, L, 460, W, 26, [[('学习方式　', {'bold': True, 'color': TEAL}),
                          ('自学概念 → 写下预测 → 运行对照实验 → 用结果解释概念 → 翻转课堂讲解', {})]], 16)

# 03 data -----------------------------------------------------------------------------
s = new_slide('导入', '本课数据：一套真实数据 + 几组“答案已知”的模拟数据',
              'WDBC 第 10 课方案 A 已用过，学生熟悉。模拟数据的作用：真实数据里我们不知道模型“真实”能做到多好，'
              '模拟数据的标签与特征无关，正确流程应接近随机（AUC≈0.5），因此能看清泄露带来的虚高。'
              'Golub 数据为第 3、4、6 课所用，适合作为第二个备选：p≫n，可打乱标签重做 E4。')
cols = [('默认 · 真实数据', 'WDBC 乳腺肿块细针穿刺',
         [('•', '569 条记录，30 个细胞核形态特征'), ('•', '恶性 212 / 良性 357；固定 70/30 训练/验证划分'),
          ('•', '用于 E1–E3：复杂度、样本量、波动、标准化')]),
        ('模拟数据', '随机标签，答案已知',
         [('•', 'null-omics：180 条 × 1000 个噪声基因（E4）'), ('•', 'repeated-patients：100 位患者 × 4 次记录（E5）'),
          ('•', 'E6、E7 的数据在脚本中生成')]),
        ('备选 · 真实数据', 'Golub 白血病表达谱',
         [('•', '72 份样本 × 7129 个探针，典型的 p≫n'), ('•', '第 3、4、6 课用过'),
          ('•', '适合在真实表达数据上重做特征筛选泄露（打乱标签）')])]
cw, gap = 272, 20
for i, (tag, head, items) in enumerate(cols):
    x = L + i * (cw + gap)
    rect(s, x, 122, cw, 282, TINT if i != 1 else WARM_TINT, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, x + 18, 140, cw - 36, 22, tag, 15, TEAL if i != 1 else WARM, bold=True)
    text(s, x + 18, 166, cw - 36, 30, head, 20, INK, bold=True, spacing=1.1)
    text(s, x + 18, 212, cw - 36, 180, items, 16, INK, spacing=1.2, after=8)
text(s, L, 424, W, 40, '也可以用自己找的数据集，按本课的问题做同样的诊断。Golub 数据：3. High-dimension/data/leukemia.csv', 14, MUTED)

# 04 concept 1: generalisation and data roles -----------------------------------------
s = new_slide('概念 1 · 泛化', '我们关心的是模型在新样本上的表现',
              '核心：评价必须用模型没见过的数据。三份数据各有用途，验证集一旦用来挑选，就不再是独立的最终评价。'
              '交叉验证在第 7 课以后反复用过，这里强调它的角色：在训练部分内部模拟“没见过的数据”。')
text(s, L, 120, 400, 300,
     [[('是什么　', {'bold': True, 'color': TEAL}), ('泛化指模型在没见过的样本上的表现。训练集上的表现只说明模型“记住”了多少。', {})],
      [('为什么重要　', {'bold': True, 'color': TEAL}), ('医学模型最终用于下一位患者。只报告训练表现，相当于用考过的原题检验学生。', {})],
      [('核心要点　', {'bold': True, 'color': TEAL}), ('数据按用途分三份，各司其职；数据少时，用交叉验证代替单独的验证集。', {})]],
     17, spacing=1.3, after=14)
text(s, L, 448, 400, 40, '自学关键词：generalization；cross-validation', 13, MUTED)
boxes = [('训练集', '拟合模型参数'), ('验证集', '比较模型、调超参数'), ('测试集', '全部定好后评价一次')]
bx, by, bw, bh = 492, 128, 416, 92
for i, (name, role) in enumerate(boxes):
    yy = by + i * (bh + 30)
    fill = [TEAL, '3E8F88', INK][i]
    b = rect(s, bx, yy, bw, bh, fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, bx + 22, yy + 16, 120, 30, name, 22, WHITE, bold=True)
    text(s, bx + 22, yy + 52, bw - 44, 26, role, 16, 'E3F1EE')
    if i < 2:
        line(s, bx + bw / 2, yy + bh + 2, bx + bw / 2, yy + bh + 28, MUTED, 1.5, arrow=True)

# 05 concept 2: under- and over-fitting ------------------------------------------------
s = new_slide('概念 2 · 欠拟合与过拟合', '欠拟合学得太少，过拟合连噪声也记住了',
              '用偏差–方差连接第 10 课：欠拟合≈高偏差（系统性学不到规律）；过拟合≈高方差（换一批训练样本，模型就变很多）。'
              '“合适”不是训练满分，而是验证表现最好、且与训练差距不大。')
rows = [['', '欠拟合', '合适', '过拟合'],
        ['含义', '模型太简单，连训练数据中的规律都没学到', '学到了能推广到新样本的规律', '把训练样本特有的噪声也当成规律'],
        ['训练表现', '偏低', '高', '很高，常接近满分'],
        ['验证表现', '偏低，与训练接近', '高，与训练接近', '明显低于训练'],
        ['常见原因', '模型过简单、有用特征不足、正则化过强', '—', '模型过复杂、样本少、特征多'],
        ['改进方向', '增加模型复杂度或有用特征', '—', '简化模型、增加样本、正则化（第 12 课）']]
table(s, rows, L, 118, [116, 250, 220, 270], 52, size=15, first_col_bold=True)
text(s, L, 448, W, 44,
     [[('与第 10 课的联系　', {'bold': True, 'color': TEAL}), ('欠拟合对应高偏差，过拟合对应高方差。', {})],
      [('自学关键词：underfitting；overfitting；generalization gap；bias–variance trade-off', {'color': MUTED, 'size': 13})]],
     16, after=4)

# 06 concept 2: how to recognise (schematic curves) ------------------------------------
s = new_slide('概念 2 · 怎样识别', '看两条曲线：复杂度曲线与学习曲线',
              '两张都是示意图。复杂度曲线（validation curve）回答“模型该多复杂”；学习曲线（learning curve）回答“加数据有没有用”。'
              '欠拟合时两条学习曲线很快靠拢且都偏低，加数据帮助不大；过拟合时差距大，加数据通常能缩小差距。')
panels = [(L, '复杂度曲线', '模型复杂度 →（树更深、k 更小、C 或 gamma 更大）'),
          (L + 448, '学习曲线', '训练样本量 →')]
for px, name, xlabel in panels:
    text(s, px, 116, 400, 24, name, 18, INK, bold=True)
    ox, oy, pw, ph = px + 30, 150, 370, 220          # plot box
    if name == '复杂度曲线':
        rect(s, ox + pw * 0.0, oy, pw * 0.25, ph, 'EEF1F0')
        rect(s, ox + pw * 0.25, oy, pw * 0.30, ph, 'E2F0EC')
        rect(s, ox + pw * 0.55, oy, pw * 0.45, ph, WARM_TINT)
        for zx, zw, zname, zc in [(0, .25, '欠拟合', MUTED), (.25, .30, '合适', TEAL), (.55, .45, '过拟合', WARM)]:
            text(s, ox + pw * zx, oy + 6, pw * zw, 20, zname, 14, zc, bold=True, align=PP_ALIGN.CENTER)
        curve(s, lambda t: 0.12 + 0.72 * (1 - math.exp(-4 * t)), ox, oy + 30, pw, ph - 34, TEAL)
        curve(s, lambda t: 0.08 + 0.56 * (1 - math.exp(-5 * t)) - 0.42 * t * t, ox, oy + 30, pw, ph - 34, WARM)
        text(s, ox + pw - 120, oy + 40, 120, 20, '训练表现', 14, TEAL, bold=True, align=PP_ALIGN.RIGHT)
        text(s, ox + pw - 120, oy + 188, 120, 20, '验证表现', 14, WARM, bold=True, align=PP_ALIGN.RIGHT)
    else:
        curve(s, lambda t: 0.90 - 0.18 * (1 - math.exp(-3 * t)), ox, oy + 30, pw, ph - 34, TEAL)
        curve(s, lambda t: 0.20 + 0.40 * (1 - math.exp(-3 * t)), ox, oy + 30, pw, ph - 34, WARM)
        text(s, ox + pw - 120, oy + 56, 120, 20, '训练表现', 14, TEAL, bold=True, align=PP_ALIGN.RIGHT)
        text(s, ox + pw - 120, oy + 116, 120, 20, '验证表现', 14, WARM, bold=True, align=PP_ALIGN.RIGHT)
        line(s, ox + pw * 0.30, oy + 72, ox + pw * 0.30, oy + 132, MUTED, 1, dash=True)
        text(s, ox + pw * 0.30 + 8, oy + 96, 150, 20, '差距随样本增加而缩小', 13, MUTED)
    line(s, ox, oy + ph, ox + pw + 6, oy + ph, INK, 1.25, arrow=True)     # x axis
    line(s, ox, oy + ph, ox, oy - 6, INK, 1.25, arrow=True)               # y axis
    text(s, px, oy - 4, 26, 60, '表现', 13, MUTED)
    text(s, ox, oy + ph + 6, pw, 20, xlabel, 13, MUTED)
card(s, L, 412, W, 76,
     [[('判断要点　', {'bold': True, 'color': TEAL}),
       ('两条线都低且接近 → 欠拟合；训练远高于验证 → 过拟合。要看验证表现和差距，不能只看训练分数。', {})],
      [('示意图，不是实测数据。自学关键词：validation curve；learning curve', {'color': MUTED, 'size': 13})]],
     16, pad=14)

# 07 Q1 ---------------------------------------------------------------------------------
task('探究 Q1 · 实验 E1-A', 'Q1　这个模型是欠拟合还是过拟合？',
     'WDBC，同一训练/验证划分，只改变决策树深度：1、2、3、5、10、不限。',
     '先预测训练与验证表现随深度怎样变化；再画出训练/验证 AUC（或准确率）随深度变化的曲线，标出欠拟合、合适、过拟合三个区域。',
     '哪个深度欠拟合、哪个过拟合？分别用哪两组数字支持？用自己的话定义两者。',
     '可选：换一个学过的模型重画复杂度曲线，如 kNN 的 k（第 3 课）、RBF-SVM 的 gamma（第 9 课）、逻辑回归的 C（第 8 课）。',
     notes='参考：深度 1 训练/验证 AUC 0.906/0.867（准确率 0.927/0.889），两者都低，属欠拟合；深度 2–3 验证 AUC 约 0.927，最好；'
           '深度≥5 训练趋近 1.0、验证降到 0.892，属过拟合。第 10 课工作单 A 做过类似实验，可作复习。'
           '可选扩展参考（同一划分，训练/验证准确率）：kNN k=1 1.00/0.94，k=301 0.63/0.63；SVM C=10、gamma=10 时 1.00/0.63。')

# 08 concept 3: causes and symptoms ------------------------------------------------------
s = new_slide('概念 3 · 原因与征兆', '过拟合从哪里来，会留下什么征兆',
              '三个风险因素对应 Q2；征兆对应 Q2、Q3。外部掉分放在概念 5 讨论，因为它不一定是过拟合。'
              '第 3 课已讲过 p≫n 与 1-近邻训练满分，可请学生回忆。')
halves = [('风险因素', TINT, TEAL,
           [('•', [('模型复杂度高　', {'bold': True}), ('参数多、树深、k 小：越能“记住”噪声', {})]),
            ('•', [('样本量小　', {'bold': True}), ('样本少时，噪声更容易被当成规律', {})]),
            ('•', [('无关特征多　', {'bold': True}), ('特征越多，偶然与标签相关的特征越多（第 3 课 p≫n）', {})])]),
          ('征兆：模型方差高', WARM_TINT, WARM,
           [('•', '训练表现远高于验证表现'),
            ('•', '交叉验证各折分数波动大'),
            ('•', '删掉或换掉少数训练样本，预测明显改变'),
            ('•', '换一批数据表现下降（但不一定是过拟合，见概念 5）')])]
for i, (head, fill, hc, items) in enumerate(halves):
    x = L + i * 438
    rect(s, x, 120, 418, 270, fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, x + 20, 138, 378, 28, head, 20, hc, bold=True)
    text(s, x + 20, 180, 378, 200, items, 17, INK, spacing=1.25, after=12)
text(s, L, 410, W, 50,
     [[('与第 10 课的联系　', {'bold': True, 'color': TEAL}), ('bagging 和随机森林通过平均多个模型来降低方差。', {})],
      [('自学关键词：model capacity；curse of dimensionality；variance；influential observation', {'color': MUTED, 'size': 13})]],
     16, after=4)

# 09 Q2 ---------------------------------------------------------------------------------
task('探究 Q2 · 实验 E1-B', 'Q2　样本量和无关特征怎样影响过拟合？',
     'WDBC，逻辑回归。训练样本 n = 40、100、200、398；原始 30 个特征，对比再加 300 个纯噪声特征；每个条件随机抽样 10 次。',
     '先预测；画两条学习曲线（有/无噪声特征）：验证 AUC 均值随 n 的变化，同时记录训练 AUC。',
     '噪声特征让验证表现下降了多少？样本增加后差距怎样变化？这对“样本少、特征多”的组学研究意味着什么？',
     '可选：把模型换成不限深度的决策树重做。为什么树对无关特征没那么敏感？',
     notes='参考（验证 AUC 均值，无噪声/加 300 噪声）：n=40 0.983/0.953；n=100 0.986/0.963；n=200 0.986/0.970；n=398 0.988/0.975。'
           '训练 AUC 始终约 1.0。树的可选题：树每次只挑最能区分类别的特征切分，多数噪声特征不会被用到；但样本很少时噪声特征仍可能被选中。')

# 10 Q3 ---------------------------------------------------------------------------------
task('探究 Q3 · 实验 E2', 'Q3　分数和预测稳定吗？',
     'WDBC 训练部分做 5 次重复的五折交叉验证，比较决策树与逻辑回归；另外每次删掉一条训练记录，重训决策树。',
     '报告两个模型 25 个折分数的均值、标准差和范围；找出删掉后验证集预测变化最大的几条记录。',
     '哪个模型更不稳定？这与过拟合有什么关系？影响最大的记录就是错误数据、应该删掉吗？',
     '折间标准差描述分数的波动大小，不等于置信区间。',
     notes='参考：25 折 AUC，树 0.942±0.025（0.884–0.983），逻辑回归 0.998±0.003。删除训练索引 69 后验证概率平均变化 0.117，'
           'AUC 由 0.892 变为 0.917。高影响只说明模型敏感，不说明记录错误；不能按验证分数删病例再报告提高后的分数。')

# 11 concept 4: leakage -----------------------------------------------------------------
s = new_slide('概念 4 · 信息泄露', '信息泄露：评价数据被“提前看见”了',
              '原则：任何需要“学习”的步骤（标准化、特征选择、降维、缺失值填补、调参）都只能在训练部分 fit，再应用到验证部分。'
              '第 3 课 T5.2、第 4 课 PCA 泄露题都练过，可请学生回忆。Pipeline 只保护放进去的步骤。')
text(s, L, 112, W, 52,
     [[('是什么　', {'bold': True, 'color': TEAL}),
       ('验证或测试数据的信息，在拟合或挑选模型时被用到了。分数因此偏高，模型对新患者却没有变好。', {})],
      [('原则　', {'bold': True, 'color': TEAL}),
       ('需要 fit 的步骤只在训练部分 fit；用 Pipeline 把这些步骤和模型一起交给交叉验证。', {})]],
     16, spacing=1.2, after=4)
rows = [['常见做法', '泄露了什么', '正确做法', '实验'],
        ['用全部数据做标准化', '验证集特征的均值、标准差', 'scaler 只在训练折内 fit', 'E3'],
        ['用全部数据筛选特征', '验证集的标签', '筛选放进 Pipeline，每折重做', 'E4'],
        ['同一患者的记录分到训练和验证两边', '患者身份', '按患者分组划分', 'E5'],
        ['先做数据增强，再随机划分', '同一原样本的副本', '先划分，只增强训练部分', 'E5 同理'],
        ['反复用测试集调参、挑模型', '测试集的结果', '在开发集内调参，测试集只用一次', 'E6']]
table(s, rows, L, 176, [262, 196, 300, 98], 44, size=15)
text(s, L, 448, W, 40, '自学关键词：data leakage；sklearn Pipeline；GroupKFold；“common pitfalls”（sklearn 文档）', 13, MUTED)

# 12 Q4 ---------------------------------------------------------------------------------
task('探究 Q4 · 实验 E3 + E4', 'Q4　标准化和特征筛选应该在哪里 fit？',
     'E3：WDBC，scaler 在全部数据上 fit 对比只在训练集上 fit。E4：180 条记录 × 1000 个噪声基因、随机标签；特征筛选放在交叉验证之前，对比放进每个训练折。',
     '记录两组对照的 AUC；在 e3()、e4() 中标出每一次 fit 用到了哪些记录。',
     '数据完全没有信号，错误流程为什么还能得到高分？这两种泄露哪个影响更大，为什么？',
     '可选：改变筛选的特征数 K_SELECT（如 5、50）；或用 Golub 白血病数据打乱标签后重做 E4。',
     notes='参考：E3 全数据缩放 0.987、训练内缩放 0.988，本例影响很小，但仍违反原则。E4（20 轮随机标签）：CV 前筛选 0.844，折内筛选 0.496。'
           '有监督的筛选用到了验证折的标签，所以虚高明显。Golub 打乱标签的试跑：全局筛选约 0.88–0.91，折内筛选 0.46–0.77（样本少，波动大）。')

# 13 Q5 ---------------------------------------------------------------------------------
task('探究 Q5 · 实验 E5', 'Q5　我们在预测新患者，还是认出见过的患者？',
     '100 位模拟患者，每人 4 条几乎相同的记录，标签按患者随机给定（特征里没有疾病信号）；1-近邻分类器。',
     '对比按行随机划分与按患者分组划分，记录验证 AUC，以及训练和验证两边共有的患者数。',
     '按行划分为什么得到了高分？删掉 patient_id 这一列能解决问题吗？数据增强产生的副本为什么也要按原样本分组？',
     '划分单位由预测对象决定：预测新患者 → 按患者划分；预测同一患者的未来 → 按时间划分。',
     notes='参考：按行划分 AUC 0.987，平均 74.9 位患者同时出现在两边；按患者分组 0.473，重叠 0。'
           '模型靠近乎相同的“身份指纹”认出见过的患者，删掉 ID 列无济于事。增强副本与原样本几乎相同，机制与此完全一样。')

# 14 concept 5: selection and shift ---------------------------------------------------------
s = new_slide('概念 5 · 选择偏差与分布变化', '分数虚高的另外两个来源',
              '选择偏差与第 6 课多重检验同理：比较的候选越多，最高分里的运气成分越大。嵌套交叉验证、外部验证的具体设计放到第 12 课；'
              '本课只要求学生能识别这两种情况，并区分它们与过拟合。')
halves = [('反复挑选最高分', TINT, TEAL,
           [('•', '在同一份数据上比较很多模型或参数，再报告最高分：这个分数偏乐观，部分是运气。'),
            ('•', '用来挑选的数据就成了验证集，不能再当独立测试。'),
            ('•', [('做法　', {'bold': True}), ('事先定好比较什么；在开发集内部调参；测试集锁定，最后只用一次（嵌套交叉验证见第 12 课）。', {})])],
           'selection bias；locked test set'),
          ('分布变化', WARM_TINT, WARM,
           [('•', '新医院、新设备、新人群的数据分布可能不同；模型可能依赖了只在原中心成立的“捷径”特征。'),
            ('•', '外部数据上掉分不一定是过拟合：也可能是分布变化、测量差异或样本太少。'),
            ('•', [('做法　', {'bold': True}), ('弄清数据来源；用独立的外部数据验证（第 12 课）。', {})])],
           'dataset shift；external validation')]
for i, (head, fill, hc, items, kw) in enumerate(halves):
    x = L + i * 438
    rect(s, x, 120, 418, 340, fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, x + 20, 136, 378, 28, head, 20, hc, bold=True)
    text(s, x + 20, 176, 378, 240, items, 16, INK, spacing=1.25, after=10)
    text(s, x + 20, 428, 378, 22, '自学关键词：' + kw, 13, MUTED)

# 15 Q6 ---------------------------------------------------------------------------------
task('探究 Q6 · 实验 E6', 'Q6　反复挑最高分会怎样？',
     '200 个“候选模型”都是随机打分，没有任何预测能力。在同一份 80 条的留出集上，从前 1、5、20、100、200 个候选中挑 AUC 最高者，再到 400 条新数据上评价它；重复 100 次。',
     '以候选数为横轴画两条曲线：被挑中者在留出集上的 AUC，以及在新数据上的 AUC。',
     '候选越多，留出集上的分数怎样变化？新数据上呢？这与第 6 课的多重检验有什么相似之处？',
     notes='参考（100 次平均，留出集/新数据）：1 个候选 0.493/0.500；5 个 0.580/0.503；20 个 0.624/0.500；100 个 0.663/0.500；200 个 0.675/0.500。'
           '被反复查看的集合已经承担了“挑选”的角色，改名叫 test 也不能恢复独立性。')

# 16 Q7 ---------------------------------------------------------------------------------
task('探究 Q7 · 实验 E7', 'Q7　外部数据上掉分，一定是过拟合吗？',
     '模拟数据：一个与疾病相关但噪声大的指标，一个只在原中心与标签相关的“中心代理”指标；在新中心里，代理指标与标签的关系反转。',
     '先读 e7() 中的 cohort() 函数并写下预测；比较“两个指标”模型与“只用疾病指标”模型在内部验证和新中心的 AUC。',
     '哪个模型内部分数高、到新中心却崩溃了？这算过拟合吗？要判断真实数据的外部掉分原因，还需要哪些信息？',
     notes='参考：两个指标模型内部 0.9997、新中心 0.0005（AUC 低于 0.5 表示排序完全颠倒）；只用疾病指标 0.750/0.663。'
           '两指标模型在内部没有过拟合，它学到的相关性在原中心是真实的，只是换了中心就不成立。真实数据需要中心、设备、时间、人群和测量方案等信息。')

# 17 Q8 ---------------------------------------------------------------------------------
s = new_slide('综合 Q8', 'Q8　把学到的用起来：设计并审查一个评价流程',
              'B 项对应课程大纲本讲作业“阅读一段机器学习方法描述，指出可能的信息泄露风险”。'
              '翻转课堂上可请学生展示 A 的流程图，或讲 B 中发现的一个问题。')
tasks = [('A　设计', '一批患者，每人有多次采样；计划做数据增强，并比较多个模型；目标是预测新患者。',
          ['画出数据流程：在哪一步划分、按什么单位划分', '增强、标准化、特征选择、调参分别放在哪里', '测试集什么时候用、用几次']),
         ('B　审查', '找一段论文的方法描述，或用你自己第 8–10 课的分析流程。',
          ['逐项对照五种泄露（概念 4）', '有没有欠拟合或过拟合的证据（概念 2–3）', '写出发现的问题和改法'])]
for i, (head, lead, items) in enumerate(tasks):
    x = L + i * 438
    rect(s, x, 120, 418, 300, TINT if i == 0 else WARM_TINT, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, x + 20, 138, 378, 28, head, 21, TEAL if i == 0 else WARM, bold=True)
    text(s, x + 20, 178, 378, 80, lead, 17, INK, spacing=1.25)
    text(s, x + 20, 258, 378, 150, [('•', it) for it in items], 17, INK, spacing=1.25, after=10)

# 18 summary checklist ---------------------------------------------------------------------
s = new_slide('小结', '识别清单：拿到一个“看起来很好”的模型时问七个问题',
              '可作为翻转课堂的提问框架：请学生任选一条，用自己的实验结果说明。最后区分三对概念：欠拟合与过拟合；过拟合与信息泄露；过拟合与分布变化。')
checks = ['训练和验证表现差多少？两者都低，还是训练远高于验证？',
          '改变复杂度或样本量时，两条曲线怎样走？',
          '交叉验证各折波动大吗？少数样本会左右结果吗？',
          '每个需要 fit 的步骤，是否只用了训练部分？',
          '划分单位与预测对象一致吗（患者、原样本、时间）？',
          '测试集只用了一次吗？报告的是不是挑出来的最高分？',
          '外部数据与训练数据同分布吗？掉分可能有哪些原因？']
for i, c in enumerate(checks):
    col, row = divmod(i, 4)
    x = L + col * 438
    y = 122 + row * 78
    circ = rect(s, x, y + 6, 38, 38, TEAL if i < 3 else (INK if i < 6 else WARM), shape=MSO_SHAPE.OVAL)
    text(s, x, y + 6, 38, 38, str(i + 1), 17, WHITE, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 52, y + 1, 370, 50, c, 16, INK, spacing=1.15, anchor=MSO_ANCHOR.MIDDLE)
card(s, L + 438, 122 + 3 * 78, 418, 70,
     [[('三对要分清', {'bold': True, 'color': TEAL})], '欠拟合 / 过拟合；过拟合 / 泄露；过拟合 / 分布变化'],
     15, pad=14, anchor=MSO_ANCHOR.MIDDLE)

# 19 after class -----------------------------------------------------------------------------
s = new_slide('课后与翻转课堂', '课后任务与翻转课堂',
              '评分建议：概念 25%，实验与可复现 30%，证据解释 30%，流程设计或审查 15%。')
items = [('运行', [('python scripts/run_experiments.py（全部实验），加 --experiment E1 只运行一个', {})],
          '结果写在仓库根目录 .tmp/lesson11/；想改实验条件，修改脚本顶部的参数'),
         ('提交', [('工作单（可在模板基础上改写）、Q1–Q7 的实验证据、至少一个自己修改条件的实验、Q8 的流程图或审查记录', {})],
          '工作单只是默认模板，也可以换成自己的数据集，按同样的问题完成'),
         ('翻转课堂', [('随机抽签讲解：学到了哪些概念、哪个实验结果改变了你的判断、做实验时遇到了什么问题', {})],
          '老师会追问概念，也会追问你的实验细节')]
y = 122
for head, body, sub in items:
    rect(s, L, y, W, 106, TINT, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, L + 20, y + 16, 110, 28, head, 19, TEAL, bold=True)
    text(s, L + 140, y + 16, W - 160, 52, [body], 17, INK, spacing=1.2)
    text(s, L + 140, y + 72, W - 160, 24, sub, 14, MUTED)
    y += 120

prs.save(OUT)
print(f'saved {OUT} ({len(prs.slides)} slides)')
