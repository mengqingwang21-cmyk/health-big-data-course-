"""Use installed Microsoft PowerPoint to export PDF, measure overflow, and render previews.

Opens a separate COM application with WithWindow=False; never modifies user presentations.
When PowerPoint is unavailable, records the limitation and retains the editable PPTX.
"""
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import fitz
from PIL import Image,ImageDraw,ImageFont
from research_style import OUT

def run():
    dest=OUT/'presentation';check={'checked_at':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()}
    app=None;deck=None;overflows=[]
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        app=win32com.client.DispatchEx('PowerPoint.Application')
        deck=app.Presentations.Open(str((dest/'ensemble_report.pptx').resolve()),ReadOnly=True,Untitled=False,WithWindow=False)
        check['powerpoint_version']=app.Version
        for page in range(1,deck.Slides.Count+1):
            slide=deck.Slides.Item(page)
            for i in range(1,slide.Shapes.Count+1):
                sh=slide.Shapes.Item(i)
                if sh.HasTable:
                    for r in range(1,sh.Table.Rows.Count+1):
                        for c in range(1,sh.Table.Columns.Count+1):
                            cell=sh.Table.Cell(r,c).Shape
                            tf=cell.TextFrame2
                            available=cell.Height-tf.MarginTop-tf.MarginBottom
                            if tf.TextRange.BoundHeight>available+1.5:
                                overflows.append(dict(page=page,shape=sh.Name,cell=f'{r},{c}',
                                    text=tf.TextRange.Text,bound_height=tf.TextRange.BoundHeight,available_height=available))
                elif sh.HasTextFrame and sh.TextFrame.HasText:
                    tf=sh.TextFrame2
                    available=sh.Height-tf.MarginTop-tf.MarginBottom
                    if tf.TextRange.BoundHeight>available+1.5:
                        overflows.append(dict(page=page,shape=sh.Name,text=tf.TextRange.Text,
                            bound_height=tf.TextRange.BoundHeight,available_height=available))
        check['text_overflows']=overflows
        deck.SaveAs(str((dest/'ensemble_report.pdf').resolve()),32)
        check['pdf_export']='exported by Microsoft PowerPoint'
        check['n_slides']=deck.Slides.Count
    except Exception as exc:
        check['pdf_export']='unavailable';check['error']=str(exc)
    finally:
        if deck is not None:deck.Close()
        if app is not None:app.Quit()
    pdf=dest/'ensemble_report.pdf'
    if pdf.exists():
        render=dest/'previews';render.mkdir(exist_ok=True)
        text_pages=[];thumbs=[]
        with fitz.open(pdf) as document:
            check['pdf_n_pages']=len(document)
            check['pdf_aspect_ratios']=[round(p.rect.width/p.rect.height,5) for p in document]
            for i,page in enumerate(document,1):
                t=page.get_text();text_pages.append(f'--- PAGE {i} ---\n'+t)
                pix=page.get_pixmap(matrix=fitz.Matrix(1.6,1.6),alpha=False)
                path=render/f'slide_{i:02d}.png';pix.save(path)
                with Image.open(path) as im:
                    thumb=im.copy();thumb.thumbnail((480,270));thumbs.append(thumb)
        (dest/'rendered_text.txt').write_text('\n\n'.join(text_pages),encoding='utf-8')
        canvas=Image.new('RGB',(480*4,300*5),'#E6ECE9');draw=ImageDraw.Draw(canvas)
        font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
        for i,thumb in enumerate(thumbs):
            x=(i%4)*480;y=(i//4)*300
            canvas.paste(thumb,(x,y));draw.text((x+8,y+274),f'{i+1:02d}'+(' 备份' if i>=16 else ''),font=font,fill='#193638')
        canvas.save(dest/'contact_sheet.png')
        check['rendered_replacement_characters']=sum(t.count('\ufffd') for t in text_pages)
    (dest/'render_audit.json').write_text(json.dumps(check,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(check,ensure_ascii=False,indent=2))

if __name__=='__main__':run()
