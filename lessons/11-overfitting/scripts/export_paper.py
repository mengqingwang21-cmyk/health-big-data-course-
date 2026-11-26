"""Word export using native OMML equations and three-rule academic tables."""
from pathlib import Path
import re
from latex2mathml.converter import convert
from lxml import etree
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image
from equations import EQUATIONS
B=Path(__file__).resolve().parents[1]
XSL=etree.XSLT(etree.parse(r'C:/Program Files/Microsoft Office/root/Office16/MML2OMML.XSL'))
D=Document(); sec=D.sections[0]
sec.page_width=Cm(21);sec.page_height=Cm(29.7)
sec.top_margin=Cm(2);sec.bottom_margin=Cm(2);sec.left_margin=Cm(2.2);sec.right_margin=Cm(2.2)
sec.header_distance=Cm(.8);sec.footer_distance=Cm(.8)
for name,size,east in [('Normal',10.5,'宋体'),('Title',18,'黑体'),('Heading 1',14,'黑体'),('Heading 2',11.5,'黑体'),('Caption',9,'宋体')]:
    st=D.styles[name];st.font.name='Times New Roman';st.font.size=Pt(size);st.font.color.rgb=RGBColor(0,0,0)
    st.font.bold=False
    st.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),east)
    st.paragraph_format.space_after=Pt(6)
    if name in ['Title','Heading 1','Heading 2']:
        st.font.bold=True;st.paragraph_format.keep_with_next=True;st.paragraph_format.space_before=Pt(12)
for st in D.styles:
    pp=st.element.find(qn('w:pPr'))
    if pp is not None:
        for border in list(pp.findall(qn('w:pBdr'))): pp.remove(border)
D.styles['Normal'].paragraph_format.line_spacing=1.35
D.styles['Normal'].paragraph_format.widow_control=True
mathpr=OxmlElement('m:mathPr');mf=OxmlElement('m:mathFont');mf.set(qn('m:val'),'Cambria Math');mathpr.append(mf);D.settings.element.append(mathpr)
hp=sec.header.paragraphs[0];hp.style='Caption';hp.text='健康数据预测模型的过拟合与评价偏差'
fp=sec.footer.paragraphs[0];fp.alignment=WD_ALIGN_PARAGRAPH.CENTER
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');fp._p.append(fld)

def math(latex):
    node=XSL(etree.fromstring(convert(latex).encode())).getroot()
    for run in node.iter(qn('m:r')):
        wp=OxmlElement('w:rPr');f=OxmlElement('w:rFonts');f.set(qn('w:ascii'),'Cambria Math');f.set(qn('w:hAnsi'),'Cambria Math');wp.append(f);run.insert(0,wp)
    return node

def inline(p,text):
    for token in re.split(r'(\$[^$]+\$|\*\*.*?\*\*|`[^`]+`)',text):
        if not token:continue
        if token.startswith('$'):p._p.append(math(token[1:-1]))
        elif token.startswith('**'):p.add_run(token[2:-2]).bold=True
        elif token.startswith('`'):p.add_run(token[1:-1])
        else:p.add_run(token)

def cell_border(cell,top=None,bottom=None):
    pr=cell._tc.get_or_add_tcPr(); borders=OxmlElement('w:tcBorders')
    for side,size in [('top',top),('bottom',bottom),('left',None),('right',None)]:
        el=OxmlElement('w:'+side);el.set(qn('w:val'),'single' if size else 'nil')
        if size:el.set(qn('w:sz'),str(size));el.set(qn('w:color'),'000000')
        borders.append(el)
    pr.append(borders)

lines=(B/'论文修订版.md').read_text(encoding='utf-8').splitlines()
i=0;figures=0;tables=0;equations=0
while i<len(lines):
    line=lines[i].strip()
    if not line:i+=1;continue
    if line.startswith('|'):
        rows=[]
        while i<len(lines) and lines[i].strip().startswith('|'):
            vals=[v.strip() for v in lines[i].strip().strip('|').split('|')]
            if not all(re.fullmatch(r':?-+:?',x) for x in vals):rows.append(vals)
            i+=1
        t=D.add_table(rows=0,cols=len(rows[0]));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
        widths=([2.5,7.3,6.8] if tables==0 else [16.6/len(rows[0])]*len(rows[0]))
        if tables==0:
            # The design table contains long prose; allow normal page continuation.
            pass
        elif len(rows[0])==3: widths=[5.7,5.0,5.9]
        for col,w in zip(t.columns,widths):col.width=Cm(w)
        for ri,values in enumerate(rows):
            row=t.add_row(); trp=row._tr.get_or_add_trPr();trp.append(OxmlElement('w:cantSplit'))
            if ri==0:trp.append(OxmlElement('w:tblHeader'))
            for j,(cell,text) in enumerate(zip(row.cells,values)):
                cell.width=Cm(widths[j]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
                p=cell.paragraphs[0];p.paragraph_format.line_spacing=1.15;p.paragraph_format.space_before=Pt(4);p.paragraph_format.space_after=Pt(4)
                p.alignment=WD_ALIGN_PARAGRAPH.LEFT if tables==0 or j==0 else WD_ALIGN_PARAGRAPH.CENTER
                if tables>0 and ri<len(rows)-1:p.paragraph_format.keep_with_next=True
                inline(p,text)
                for run in p.runs:run.font.size=Pt(8.5);run.bold=ri==0
                cell_border(cell,top=10 if ri==0 else None,bottom=6 if ri==0 else (10 if ri==len(rows)-1 else None))
        # Three-rule tables are explicitly requested for this paper.
        borders=OxmlElement('w:tblBorders')
        for side in ['top','bottom','left','right','insideH','insideV']:
            e=OxmlElement('w:'+side);e.set(qn('w:val'),'nil');borders.append(e)
        t._tbl.tblPr.append(borders)
        tables+=1;continue
    if line.startswith('$$'):
        number=int(re.search(r'\((\d+)\)',line).group(1))
        eqs=[x.replace('n_T','n').replace('n_t','N_t').replace('n_L','N_L').replace('n_R','N_R') for x in EQUATIONS[number]]
        if len(eqs)>1:
            display=OxmlElement('m:oMath');array=OxmlElement('m:eqArr')
            pr=OxmlElement('m:eqArrPr');base=OxmlElement('m:baseJc');base.set(qn('m:val'),'center');pr.append(base);array.append(pr)
            for latex in eqs:
                row=OxmlElement('m:e')
                for child in list(math(latex)):row.append(child)
                array.append(row)
            display.append(array)
        else:display=math(eqs[0])
        p=D.add_paragraph();p.paragraph_format.keep_together=True
        p.paragraph_format.keep_with_next=True
        p.paragraph_format.space_before=Pt(5);p.paragraph_format.space_after=Pt(8)
        p.paragraph_format.tab_stops.add_tab_stop(Cm(8.3),WD_TAB_ALIGNMENT.CENTER)
        p.paragraph_format.tab_stops.add_tab_stop(Cm(16.6),WD_TAB_ALIGNMENT.RIGHT)
        p.add_run('\t');p._p.append(display);p.add_run(f'\t({number})')
        equations+=1
    elif line.startswith('!['):
        match=re.match(r'!\[(.*?)\]\((.*?)\)',line);path=B/match.group(2)
        with Image.open(path) as im:w,h=im.size
        width=min(16.6 if 'Q2-' in path.name or 'Q6-' in path.name else 14.5,16.8*w/h)
        p=D.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.keep_with_next=True
        pic=p.add_run().add_picture(str(path),width=Cm(width));pic._inline.docPr.set('descr',match.group(1));figures+=1
    elif line.startswith('# '):
        p=D.add_paragraph(line[2:],style='Title');p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    elif line.startswith('### '):D.add_heading(line[4:],level=2)
    elif line.startswith('## '):D.add_heading(line[3:],level=1)
    elif line.startswith('**Overfitting'):
        p=D.add_paragraph();inline(p,line);p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:run.font.size=Pt(11)
    elif line.startswith('*图'):
        p=D.add_paragraph(line[1:-1],style='Caption')
    elif line.startswith('**表'):
        p=D.add_paragraph(style='Caption');inline(p,line);p.paragraph_format.keep_with_next=True
    else:
        p=D.add_paragraph();inline(p,line)
        if line.startswith('作者：'):p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        elif line.startswith('['):p.alignment=WD_ALIGN_PARAGRAPH.LEFT
        else:p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
        if line.startswith('**关键词'):p.paragraph_format.space_before=Pt(6)
        following=next((x.strip() for x in lines[i+1:] if x.strip()),'')
        if following.startswith('$$'):p.paragraph_format.keep_with_next=True
    i+=1
out=B/'王梦晴_过拟合与评价偏差_论文修订版.docx';D.save(out)
assert equations==10 and figures==7 and tables==10
check=Document(out);assert len(check.inline_shapes)==7
assert len(check.element.findall('.//'+qn('m:oMath')))>10
print(f'Saved {out.name}: {equations} native display equations, {figures} figures, {tables} three-rule tables.')
