"""A small PDF builder for review attacks: free-form header text plus rows of label and figures."""
import io

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from support import statement_pdf as sp

CUR, PRIOR = sp.CUR, sp.PRIOR


def mk(pages, scale_line="Unaudited (in thousands)", font=9):
    """pages: list of dicts {pre: [(align, x, y, text)], rows: [(label, {x_right: text, ...})], y0, dy, label_x}"""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, invariant=1)
    for page in pages:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, 760, page.get("title", "Harrowgate Tool & Die, Inc."))
        c.setFont("Helvetica", font)
        if scale_line and page.get("scale", True):
            c.drawString(72, 746, scale_line)
        for align, x, y, text in page.get("pre", []):
            (c.drawRightString if align == "r" else c.drawCentredString if align == "c" else c.drawString)(x, y, text)
        y = page.get("y0", 688)
        for row in page["rows"]:
            label, figs = row[0], row[1]
            lx = row[2] if len(row) > 2 else page.get("label_x", 72)
            if label:
                c.drawString(lx, y, label)
            for x, text in figs.items():
                c.drawRightString(x, y, text)
            y -= page.get("dy", 15)
        c.drawString(72, 40, "SYNTHETIC - FOR DEMONSTRATION")
        c.showPage()
    c.save()
    return buf.getvalue()


def std_rows(page_no, cur_x=440, prior_x=560, pages=None):
    return [(label, {cur_x: cur, prior_x: prior}) for _k, label, cur, prior in (pages or sp.PAGES)[page_no]]


def std_header(cur_x=440, prior_x=560, y=706):
    return [("r", cur_x, y, CUR), ("r", prior_x, y, PRIOR)]


def cells(column="current", header=CUR, pages=None, only=None, page_map=None):
    out = []
    for page, rows in (pages or sp.PAGES).items():
        for key, label, cur, prior in rows:
            if only and not only(key):
                continue
            out.append({"key": ("stated." + key) if key in sp.COMPUTED else key,
                        "page": (page_map or {}).get(page, page),
                        "printed_figure": cur if column == "current" else prior,
                        "printed_label": label, "column_header": header})
    return out


def answer(cells_, **over):
    a = {"scale_statement": "(in thousands)", "scale_page": 1, "cells": cells_, "comparative_cells": [],
         "absent_keys": list(sp.ABSENT), "notes": []}
    a.update(over)
    return a
