"""
label_renderer.py — Генерация PDF этикеток через ReportLab
pip install reportlab python-barcode[images] Pillow
"""
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io, os


def hex2color(h):
    h = h.strip("#")
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return (r/255, g/255, b/255)


def render_barcode_image(code_str):
    """Returns a PIL Image of the barcode or None."""
    try:
        import barcode
        from barcode.writer import ImageWriter
        buf = io.BytesIO()
        bc = barcode.Code128(str(code_str), writer=ImageWriter())
        bc.write(buf, options={
            "module_width": 0.4, "module_height": 10.0,
            "quiet_zone": 2.0, "write_text": False, "dpi": 300
        })
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Barcode error: {e}")
        return None


def render_pdf(path, queue, tmpl):
    """
    queue: list of {art, name, mp, bc, qty}
    tmpl:  dict with width_mm, height_mm, bg_color, border, blocks
    """
    w_mm = tmpl.get("width_mm",  58)
    h_mm = tmpl.get("height_mm", 40)
    W = w_mm * mm
    H = h_mm * mm

    c = rl_canvas.Canvas(path, pagesize=(W, H))

    for item in queue:
        for _ in range(item["qty"]):
            _draw_label(c, item, tmpl, W, H)
            c.showPage()

    c.save()


def _draw_label(c, item, tmpl, W, H):
    bg = tmpl.get("bg_color", "#ffffff")
    r, g, b = hex2color(bg)
    c.setFillColorRGB(r, g, b)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    if tmpl.get("border", True):
        c.setStrokeColorRGB(0.75, 0.75, 0.75)
        c.setLineWidth(0.5)
        c.rect(0, 0, W, H, fill=0, stroke=1)

    for block in tmpl.get("blocks", []):
        if not block.get("visible", True): continue
        _draw_block(c, block, item, W, H)


def _draw_block(c, block, item, W, H):
    btype = block["type"]
    x_rel = block.get("x", 0.05)
    y_rel = block.get("y", 0.05)
    # ReportLab Y is bottom-up, so flip
    x = x_rel * W
    y = H - y_rel * H   # will adjust per block

    color = block.get("color", "#000000")
    cr, cg, cb = hex2color(color)
    fs = block.get("font_size", 9)
    bold = block.get("bold", False)
    italic = block.get("italic", False)
    align = block.get("align", "left")
    avail_w = W * 0.90 - x

    def set_font(size=None, b=None, it=None):
        s = size or fs; bb = b if b is not None else bold; ii = it if it is not None else italic
        fname = "Helvetica"
        font_type = block.get("font","sans")
        if font_type == "serif":
            fname = "Times-Roman"
            if bb and ii: fname = "Times-BoldItalic"
            elif bb: fname = "Times-Bold"
            elif ii: fname = "Times-Italic"
        elif font_type == "mono":
            fname = "Courier"
            if bb: fname = "Courier-Bold"
        else:
            if bb and ii: fname = "Helvetica-BoldOblique"
            elif bb: fname = "Helvetica-Bold"
            elif ii: fname = "Helvetica-Oblique"
        c.setFont(fname, s)
        return fname

    if btype == "divider":
        div_y = H - y_rel * H
        dc = hex2color(block.get("color","#cccccc"))
        c.setStrokeColorRGB(*dc)
        c.setLineWidth(0.4)
        c.line(W*0.03, div_y, W*0.97, div_y)

    elif btype == "barcode":
        bc_str = item.get("bc","")
        if not bc_str: return
        buf = render_barcode_image(bc_str)
        if buf:
            bh = block.get("height_ratio", 0.30) * H
            bw = W * 0.90
            bx = W * 0.05
            by = H - y_rel*H - bh
            img = ImageReader(buf)
            c.drawImage(img, bx, by, width=bw, height=bh, preserveAspectRatio=False)

    elif btype == "mp_badge":
        mp = item.get("mp","")
        if not mp: return
        badge_color = hex2color("#7b1fa2" if mp=="WB" else "#0d47a1")
        set_font(max(6,fs), b=True, it=False)
        tw = c.stringWidth(mp, c._fontname, c._fontsize)
        pad = 2*mm
        bx = x_rel * W
        bh = fs * 0.4 * mm + 2
        by = H - y_rel*H - bh
        c.setFillColorRGB(*badge_color)
        c.roundRect(bx, by, tw + pad*2, bh, 1, fill=1, stroke=0)
        c.setFillColorRGB(1,1,1)
        c.drawString(bx + pad, by + 1.5, mp)

    else:
        text_map = {
            "name":      item.get("name",""),
            "art":       item.get("art",""),
            "logo":      block.get("text","SharmGlow"),
            "bc_number": item.get("bc",""),
            "price":     "999 ₽",
        }
        text = text_map.get(btype, "")
        if not text: return

        set_font()
        c.setFillColorRGB(cr, cg, cb)
        ty = H - y_rel*H - fs*0.35*mm

        # Truncate if too wide
        while c.stringWidth(text, c._fontname, c._fontsize) > avail_w and len(text) > 3:
            text = text[:-4] + "…"

        if align == "center":
            tx = (W - c.stringWidth(text, c._fontname, c._fontsize)) / 2
        elif align == "right":
            tx = W - c.stringWidth(text, c._fontname, c._fontsize) - W*0.05
        else:
            tx = x

        c.drawString(tx, ty, text)
