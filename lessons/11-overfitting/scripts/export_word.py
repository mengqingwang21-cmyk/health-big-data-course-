"""Export the existing manuscript to an editable Word document."""
from pathlib import Path
import re
from equations import EQUATIONS
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image

B=Path(__file__).resolve().parents[1]
D=Document()
sec=D.sections[0]
sec.page_width=Cm(21); sec.page_height=Cm(29.7)
sec.top_margin=Cm(2.1); sec.bottom_margin=Cm(2.0)
sec.left_margin=Cm(2.2); sec.right_margin=Cm(2.2)
sec.header_distance=Cm(.9); sec.footer_distance=Cm(.9)
def font(style,size,east='宋体',bold=False):
    s=D.styles[style]; s.font.name='Times New Roman'; s.font.size=Pt(size); s.font.bold=bold
    s.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),east)
font('Normal',10.5)
n=D.styles['Normal'].paragraph_format
n.line_spacing=1.35; n.space_after=Pt(6); n.widow_control=True
for name,size in [('Title',20),('Heading 1',15),('Heading 2',12),('Heading 3',11)]:
    font(name,size,'黑体',True)
    D.styles[name].font.color.rgb=RGBColor.from_string('000000')
    D.styles[name].paragraph_format.keep_with_next=True
    D.styles[name].paragraph_format.space_before=Pt(14)
font('Caption',9,'宋体')
D.styles['Caption'].font.color.rgb=RGBColor(0,0,0)
for style in D.styles:
    if style.type==1:
        pp=style.element.find(qn('w:pPr'))
        if pp is not None:
            for border in list(pp.findall(qn('w:pBdr'))): pp.remove(border)
D.styles['Caption'].paragraph_format.space_after=Pt(9)
header=sec.header.paragraphs[0]; header.text='健康大数据实践  |  过拟合与评价偏差'; header.style='Caption'
footer=sec.footer.paragraphs[0]; footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
field=OxmlElement('w:fldSimple'); field.set(qn('w:instr'),'PAGE'); footer._p.append(field)

def inline(p,text):
    # Preserve emphasis and code labels without exposing Markdown markers.
    for token in re.split(r'(\*\*.*?\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))',text):
        if not token: continue
        if token.startswith('**'):
            p.add_run(token[2:-2]).bold=True
        elif token.startswith('`'):
            r=p.add_run(token[1:-1]); r.font.name='Consolas'; r.font.size=Pt(9)
        elif re.match(r'\[.*\]\(',token):
            p.add_run(re.match(r'\[([^\]]+)\]',token).group(1))
        else: p.add_run(token)

lines=(B/'worksheet-manuscript.md').read_text(encoding='utf-8').splitlines()
i=0; figures=0; tables=0
while i<len(lines):
    line=lines[i].strip()
    if not line: i+=1; continue
    if line.startswith('|'):
        rows=[]
        while i<len(lines) and lines[i].strip().startswith('|'):
            cells=[x.strip() for x in lines[i].strip().strip('|').split('|')]
            if not all(re.fullmatch(r':?-+:?',x) for x in cells): rows.append(cells)
            i+=1
        t=D.add_table(rows=1,cols=len(rows[0])); t.autofit=True
        for j,txt in enumerate(rows[0]): inline(t.rows[0].cells[j].paragraphs[0],txt)
        for row in rows[1:]:
            cells=t.add_row().cells
            for j,txt in enumerate(row): inline(cells[j].paragraphs[0],txt)
        for ri,row in enumerate(t.rows):
            props=row._tr.get_or_add_trPr(); props.append(OxmlElement('w:cantSplit'))
            if ri==0: props.append(OxmlElement('w:tblHeader'))
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.space_after=Pt(4); p.paragraph_format.space_before=Pt(4)
                    p.paragraph_format.line_spacing=1.1
                    if tables>0 and ri<len(t.rows)-1: p.paragraph_format.keep_with_next=True
                    for r in p.runs:
                        r.font.size=Pt(8.5); r.bold=ri==0
        borders=OxmlElement('w:tblBorders')
        for side in ['top','bottom','left','right','insideH','insideV']:
            e=OxmlElement('w:'+side); e.set(qn('w:val'),'single'); e.set(qn('w:sz'),'4'); e.set(qn('w:color'),'D9D9D9'); borders.append(e)
        t._tbl.tblPr.append(borders)
        for cell in t.rows[0].cells:
            shade=OxmlElement('w:shd'); shade.set(qn('w:fill'),'EAF0F5'); cell._tc.get_or_add_tcPr().append(shade)
            e=OxmlElement('w:tcBorders'); b=OxmlElement('w:bottom'); b.set(qn('w:val'),'single'); b.set(qn('w:sz'),'6'); e.append(b); cell._tc.get_or_add_tcPr().append(e)
        tables+=1; continue
    image=re.match(r'!\[([^\]]*)\]\(([^)]+)\)',line)
    if line.startswith('$$'):
        num=int(re.search(r'（(\d+)）',line).group(1))
        for ni,latex in enumerate(EQUATIONS[num]):
            ep=D.add_paragraph(); ep.alignment=WD_ALIGN_PARAGRAPH.CENTER
            ep.paragraph_format.keep_together=True
            if ni<len(EQUATIONS[num])-1: ep.paragraph_format.keep_with_next=True
            eqpath=B/'results'/'equations'/f'eq-{num}-{ni}.png'
            with Image.open(eqpath) as eqimg: ew,eh=eqimg.size
            ep.add_run().add_picture(str(eqpath),width=Cm(min(15.2,ew/240*2.54)))
            if ni==len(EQUATIONS[num])-1: ep.add_run(f'    ({num})')
    elif image:
        path=B/image.group(2)
        with Image.open(path) as im: width,height=im.size
        max_width=16.5 if 'Q2-learning' in path.name else 14.5
        width_cm=min(max_width,17.0*width/height)
        p=D.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next=True
        p.add_run().add_picture(str(path),width=Cm(width_cm)); figures+=1
    elif line.startswith('# '):
        p=D.add_paragraph(line[2:],style='Title'); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    elif line.startswith('### '): D.add_heading(line[4:],level=2)
    elif line.startswith('## '): D.add_heading(line[3:],level=1)
    elif line.startswith('*') and line.endswith('*') and not line.startswith('**'):
        p=D.add_paragraph(line[1:-1],style='Caption')
    elif re.match(r'\*\*表\d+',line):
        p=D.add_paragraph(style='Caption'); inline(p,line); p.paragraph_format.keep_with_next=True
    elif line.startswith('**Overfitting'):
        p=D.add_paragraph(); inline(p,line); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    else:
        p=D.add_paragraph(); inline(p,line)
        p.alignment=WD_ALIGN_PARAGRAPH.LEFT if re.match(r'^\d+\.',line) else WD_ALIGN_PARAGRAPH.JUSTIFY
    i+=1
out=B/'过拟合与评价偏差_引言方法与图注修订版.docx'
try:
    D.save(out)
except PermissionError:
    out=B/'过拟合与评价偏差_论文式Worksheet_摘要修订版.docx'
    D.save(out)
check=Document(out)
assert figures==7 and len(check.inline_shapes)==7+sum(map(len,EQUATIONS.values()))
assert len(check.tables)==tables and tables==13
print(f'Saved {out}; {len(check.paragraphs)} paragraphs, {tables} tables, {figures} embedded figures.')
