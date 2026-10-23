"""Build the dissertation and the journal paper (.docx) from the markdown sources.

    python scripts/build_docs.py dissertation|paper|all [--no-pdf]

Placeholders {{path::fmt}} are filled from facts/facts.json. Directives [[...]] insert tables built from facts.
Fields (TOC, list of figures, list of tables, SEQ captions, PAGE) are refreshed and the PDF is produced by
Microsoft Word through COM (scripts/word_refresh.py) when available.
"""
import json, os, re, sys, shutil, unicodedata
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "output", "figures")
F = json.load(open(os.path.join(ROOT, "facts", "facts.json"), encoding="utf-8"))
FONT = "Times New Roman"
UNRESOLVED = []

TITLE = ("A Cloud-Based Traffic Control System for Sub-Saharan African Cities Combining Chain-of-Thought, "
         "Vision-Language-Action Models and Latent World Models")
SUBTITLE = "Cloud-Hosted Reasoning with Edge Fallback for Intermittent Connectivity"
CTRL_ORDER = ["fixed_time", "count_timer", "max_pressure", "africot_nowm", "africot_noslow", "africot_full"]
SCEN = ["normal", "market", "incident", "outage"]


# ---------------------------------------------------------------- placeholders
def lookup(path):
    cur = F
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return cur


def fmt_val(v, f):
    if f.startswith("pct"):
        return f"{v * 100:.{int(f[3:])}f}"
    if f.isdigit():
        return f"{v:.{int(f)}f}"
    return str(v)


def fill(text, where=""):
    def rep(m):
        raw = m.group(1)
        path, _, f = raw.partition("::")
        try:
            return fmt_val(lookup(path.strip()), f.strip())
        except Exception as e:  # noqa
            UNRESOLVED.append((where, raw, repr(e)))
            return "[UNRESOLVED]"
    return re.sub(r"\{\{(.+?)\}\}", rep, text)


# ---------------------------------------------------------------- directive tables
def S(sc, c):
    return F["summary"].get(f"{sc}|{c}")


def present_controllers():
    return [c for c in CTRL_ORDER if any(S(s, c) for s in SCEN)]


def tbl_awt():
    cs = present_controllers()
    rows = [["Scenario"] + cs]
    for s in SCEN:
        rows.append([s] + [f"{S(s, c)['awt_mean']:.1f} ({S(s, c)['awt_sd']:.1f})" if S(s, c) else "n/a" for c in cs])
    return rows


def tbl_full():
    rows = [["Scenario", "Controller", "AWT (s)", "ATT (s)", "AQL (veh)", "Throughput", "Ped. wait (s)", "Violations"]]
    for s in SCEN:
        for c in present_controllers():
            r = S(s, c)
            if r:
                rows.append([s, c, f"{r['awt_mean']:.1f} ({r['awt_sd']:.1f})", f"{r['att_mean']:.1f} ({r['att_sd']:.1f})",
                             f"{r['aql_mean']:.1f} ({r['aql_sd']:.1f})", f"{r['throughput_mean']:.0f} ({r['throughput_sd']:.0f})",
                             f"{r['ped_wait_mean']:.1f} ({r['ped_wait_sd']:.1f})", f"{r['safety_violations_mean']:.0f}"])
    return rows


def tbl_paired():
    rows = [["Scenario", "Comparison (A versus B)", "Mean AWT difference, A minus B (s)", "SD of difference (s)",
             "Paired t-test p", "Wilcoxon p", "Seeds with A lower"]]
    for p in F["paired_tests"]:
        w = p["wilcoxon_exact_p_two_sided"]
        rows.append([p["scenario"], f"{p['a']} vs {p['b']}", f"{p['mean_diff_a_minus_b']:.1f}", f"{p['sd_diff']:.1f}",
                     f"{p['t_p_two_sided']:.3f}", "n/a" if w is None else f"{w:.4f}", f"{p['a_lower_in_seeds']} of 5"])
    return rows


def tbl_wm():
    T = F["world_model"]["test"]
    rows = [["Horizon", "Queue MAE model", "Queue MAE persistence", "Improvement (%)", "Pedestrian MAE model", "Pedestrian MAE persistence",
             "Departure MAE model", "Departure MAE persistence"]]
    for k, lab in (("1step", "1 step"), ("2step", "2 steps"), ("3step", "3 steps")):
        t = T[k]
        rows.append([lab, f"{t['queue_mae_model']:.2f}", f"{t['queue_mae_persistence']:.2f}", f"{t['queue_improvement_vs_persistence'] * 100:.1f}",
                     f"{t['ped_mae_model']:.2f}", f"{t['ped_mae_persistence']:.2f}", f"{t['dep_mae_model']:.2f}", f"{t['dep_mae_persistence']:.2f}"])
    return rows


def tbl_shield():
    d = F["shield_corrections_by_controller_rule"]
    rows = [["Controller", "Pedestrian crossing", "Maximum green", "Starvation guard", "Total corrections", "Safety violations"]]
    for c in CTRL_ORDER:
        if c in d:
            v = d[c]
            tot = sum(v.values())
            viol = sum(S(s, c)["safety_violations_mean"] * S(s, c)["n_seeds"] for s in SCEN if S(s, c))
            rows.append([c, str(v.get("ped_crossing", 0)), str(v.get("max_green", 0)), str(v.get("starvation", 0)), str(tot), f"{viol:.0f}"])
    return rows


def tbl_scenario():
    ev = {"normal": "none", "market": "none", "incident": "kerb lane of east approach closed 1200 to 2100 s",
          "outage": "slow loop unreachable 1200 to 2400 s"}
    rows = [["Scenario", "West, East (veh/h)", "South (veh/h)", "Mix car/danfo/keke/okada (%)", "Pedestrians (per h)", "Event"]]
    for s in SCEN:
        c = F["scenario_config"][s]
        fl = c["flows"]
        mix = "/".join(f"{c['mix'][k] * 100:.0f}" for k in ("car", "danfo", "keke", "okada"))
        rows.append([s, f"{fl['W']}, {fl['E']}", str(fl["S"]), mix, str(c["ped_per_h"]), ev[s]])
    return rows


def directive(name):
    if name == "results_table:awt":
        return tbl_awt()
    if name == "results_table:full":
        return tbl_full()
    return {"paired_table": tbl_paired, "wm_table": tbl_wm, "shield_table": tbl_shield, "scenario_table": tbl_scenario}[name]()


# ---------------------------------------------------------------- docx helpers
def set_font(run, size=None, bold=None, italic=None):
    run.font.name = FONT
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(a), FONT)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def style_setup(doc, kind):
    body = 12
    st = doc.styles["Normal"]
    st.font.name = FONT
    st.font.size = Pt(body)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    pf = st.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.line_spacing = 1.5 if kind == "dissertation" else 1.15
    pf.space_after = Pt(6) if kind == "dissertation" else Pt(6)
    for name, size, align in (("Heading 1", 14, WD_ALIGN_PARAGRAPH.CENTER if kind == "dissertation" else WD_ALIGN_PARAGRAPH.LEFT),
                              ("Heading 2", 12, WD_ALIGN_PARAGRAPH.LEFT), ("Heading 3", 12, WD_ALIGN_PARAGRAPH.LEFT)):
        h = doc.styles[name]
        h.font.name = FONT
        h.font.size = Pt(size)
        h.font.bold = True
        h.font.italic = name == "Heading 3"
        h.font.color.rgb = RGBColor(0, 0, 0)
        h.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        h.element.rPr.rFonts.set(qn("w:ascii"), FONT)
        h.element.rPr.rFonts.set(qn("w:hAnsi"), FONT)
        h.paragraph_format.alignment = align
        h.paragraph_format.space_before = Pt(12)
        h.paragraph_format.space_after = Pt(6)
        h.paragraph_format.keep_with_next = True
        h.paragraph_format.line_spacing = 1.15
    c = doc.styles["Caption"]
    c.font.name = FONT
    c.font.size = Pt(10.5)
    c.font.bold = False
    c.font.italic = False
    c.font.color.rgb = RGBColor(0, 0, 0)
    c.element.rPr.rFonts.set(qn("w:ascii"), FONT)
    c.element.rPr.rFonts.set(qn("w:hAnsi"), FONT)
    c.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    c.paragraph_format.line_spacing = 1.0
    c.paragraph_format.space_after = Pt(8)
    for lvl in (1, 2, 3):
        try:
            t = doc.styles[f"TOC {lvl}"]
        except KeyError:
            t = doc.styles.add_style(f"TOC {lvl}", 1)
        t.font.name = FONT
        t.font.size = Pt(12)
        t.paragraph_format.left_indent = Inches(0.25 * (lvl - 1))
        t.paragraph_format.line_spacing = 1.15
        t.paragraph_format.space_after = Pt(3)
        t.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    try:
        tf = doc.styles["Table of Figures"]
    except KeyError:
        tf = doc.styles.add_style("Table of Figures", 1)
    tf.font.name = FONT
    tf.font.size = Pt(12)
    tf.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    tf.paragraph_format.line_spacing = 1.15
    tf.paragraph_format.space_after = Pt(3)
    sec = doc.sections[0]
    sec.page_width = Inches(8.27)
    sec.page_height = Inches(11.69)
    for m in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, m, Inches(1))
    sec.left_margin = Inches(1.25) if kind == "dissertation" else Inches(1)


def add_field(par, instr, result_text="", size=None, italic=None, bold=None):
    def fc(t):
        r = par.add_run()
        e = OxmlElement("w:fldChar")
        e.set(qn("w:fldCharType"), t)
        r._r.append(e)
        return r
    fc("begin")
    r = par.add_run()
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = f" {instr} "
    r._r.append(it)
    fc("separate")
    rr = par.add_run(result_text)
    set_font(rr, size, bold, italic)
    fc("end")


def page_break(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def pgnum(section, fmt=None, start=None):
    sp = section._sectPr
    for e in sp.findall(qn("w:pgNumType")):
        sp.remove(e)
    e = OxmlElement("w:pgNumType")
    if fmt:
        e.set(qn("w:fmt"), fmt)
    if start is not None:
        e.set(qn("w:start"), str(start))
    sp.append(e)


def footer_page(section, show=True):
    section.footer.is_linked_to_previous = False
    for p in section.footer.paragraphs:
        for r in list(p.runs):
            r._r.getparent().remove(r._r)
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if show:
        add_field(p, "PAGE", "1", size=11)


def para(doc, text="", align=None, bold=False, italic=False, size=None, space_after=None, spacing=None, keep=False):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    if text:
        r = p.add_run(text)
        set_font(r, size, bold, italic)
    if space_after is not None:
        p.paragraph_format.space_after = Pt(space_after)
    if spacing is not None:
        p.paragraph_format.line_spacing = spacing
    return p


STATE = {"colab": False}
INLINE = re.compile(r"(\*\*.+?\*\*|\*[^*\s][^*]*?\*|`[^`]+`|<!--/?COLAB[^>]*-->)")


def add_inline(p, text, size=None, base_bold=False, base_italic=False):
    for tok in INLINE.split(text):
        if not tok:
            continue
        if tok.startswith("<!--"):
            STATE["colab"] = tok.startswith("<!--COLAB")
            continue
        b, i, code = base_bold, base_italic, False
        if tok.startswith("**") and tok.endswith("**") and len(tok) > 4:
            tok, b = tok[2:-2], True
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
            tok, i = tok[1:-1], True
        elif tok.startswith("`") and tok.endswith("`"):
            tok, code = tok[1:-1], True
        r = p.add_run(tok)
        set_font(r, size, b, i)
        if code:
            r.font.name = "Courier New"
            r.font.size = Pt((size or 12) - 1)
        if STATE["colab"]:
            r.font.highlight_color = WD_COLOR_INDEX.YELLOW


def set_cell_border(cell, **kw):
    tcPr = cell._tc.get_or_add_tcPr()
    b = tcPr.find(qn("w:tcBorders"))
    if b is None:
        b = OxmlElement("w:tcBorders")
        tcPr.append(b)
    for edge, val in kw.items():
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), val)
        e.set(qn("w:sz"), "6")
        e.set(qn("w:color"), "000000")
        b.append(e)


def add_table(doc, rows):
    ncol = len(rows[0])
    t = doc.add_table(rows=len(rows), cols=ncol)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    size = 10 if ncol <= 5 else (9 if ncol <= 7 else 8)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.text = ""
            p = c.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 or ncol > 6 and j <= 1 else WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.space_after = Pt(1)
            add_inline(p, val, size=size, base_bold=(i == 0))
            if i == 0:
                set_cell_border(c, top="single", bottom="single")
            if i == len(rows) - 1:
                set_cell_border(c, bottom="single")
    if ncol >= 7:
        t.autofit = True
    # keep header row repeating
    trPr = t.rows[0]._tr.get_or_add_trPr()
    h = OxmlElement("w:tblHeader")
    trPr.append(h)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def caption(doc, label, text, counters):
    counters[label] += 1
    p = doc.add_paragraph(style="Caption")
    p.paragraph_format.keep_with_next = label == "Table"
    r = p.add_run(f"{label} ")
    set_font(r, 10.5, True)
    add_field(p, f"SEQ {label} \\* ARABIC", str(counters[label]), size=10.5, bold=True)
    r = p.add_run(". ")
    set_font(r, 10.5, True)
    add_inline(p, text, size=10.5)
    return p


# ---------------------------------------------------------------- markdown body
def render_md(doc, text, kind, counters, where, num_h1=False, h1_counter=None):
    text = fill(text, where)
    lines = text.split("\n")
    i = 0
    buf = []
    pending_caption = None

    def flush():
        nonlocal buf
        if buf:
            p = doc.add_paragraph()
            add_inline(p, " ".join(s.strip() for s in buf))
            buf = []

    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if s.startswith("<!--") and s.endswith("-->") and "COLAB" in s and not buf:
            STATE["colab"] = s.startswith("<!--COLAB")
            i += 1
            continue
        if not s:
            flush(); i += 1; continue
        if s.startswith("% "):
            i += 1; continue
        m = re.match(r"^(#{1,3}) (.*)", s)
        if m:
            flush()
            lvl, title = len(m.group(1)), m.group(2).strip()
            if lvl == 1 and num_h1 and title not in ("Abstract", "Keywords", "References"):
                h1_counter[0] += 1
                title = f"{h1_counter[0]} {title}"
            if lvl == 1 and kind == "dissertation":
                doc.add_page_break()
            h = doc.add_heading("", level=lvl)
            add_inline(h, title, size=None)
            for r in h.runs:
                set_font(r, None, True, lvl == 3)
                r.font.color.rgb = RGBColor(0, 0, 0)
            i += 1; continue
        m = re.match(r"^!\[\[figure:([^|]+)\|(.*)\]\]$", s)
        if m:
            flush()
            fn, cap = m.group(1), m.group(2)
            path = os.path.join(FIG, fn)
            if not os.path.exists(path):
                UNRESOLVED.append((where, fn, "figure missing"))
            else:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.keep_with_next = True
                p.paragraph_format.line_spacing = 1.0
                p.add_run().add_picture(path, width=Inches(5.6 if kind == "dissertation" else 5.9))
                caption(doc, "Figure", cap, counters)
            i += 1; continue
        if s.startswith("Table: "):
            flush()
            pending_caption = s[7:]
            i += 1; continue
        m = re.match(r"^\[\[([a-z_:]+)\]\]$", s)
        if m:
            flush()
            if pending_caption:
                caption(doc, "Table", pending_caption, counters)
                pending_caption = None
            add_table(doc, directive(m.group(1)))
            i += 1; continue
        if s.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.match(r"^:?-{2,}:?$", c) for c in cells):
                    rows.append(cells)
                i += 1
            if pending_caption:
                caption(doc, "Table", pending_caption, counters)
                pending_caption = None
            n = len(rows[0])
            rows = [r + [""] * (n - len(r)) if len(r) < n else r[:n] for r in rows]
            add_table(doc, rows)
            continue
        m = re.match(r"^(\s*)([-*]|\d+\.) (.*)", ln)
        if m:
            flush()
            style = "List Number" if m.group(2)[0].isdigit() else "List Bullet"
            p = doc.add_paragraph(style=style)
            p.paragraph_format.line_spacing = 1.15
            add_inline(p, m.group(3).strip())
            i += 1
            while i < len(lines) and lines[i].startswith("  ") and lines[i].strip() and not re.match(r"^\s*([-*]|\d+\.) ", lines[i]):
                add_inline(p, " " + lines[i].strip()); i += 1
            continue
        buf.append(ln)
        i += 1
    flush()


# ---------------------------------------------------------------- references
def strip_acc(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def collect_refs(files):
    seen, out = set(), []
    for f in files:
        if not os.path.exists(f):
            continue
        for ln in open(f, encoding="utf-8").read().splitlines():
            ln = ln.strip()
            if ln and ln not in seen:
                seen.add(ln); out.append(ln)
    out.sort(key=lambda s: re.sub(r"[^a-z0-9 ]", "", strip_acc(s)))
    return out


def add_references(doc, refs, kind):
    h = doc.add_heading("References", level=1)
    if kind == "dissertation":
        pass
    for r in h.runs:
        set_font(r, None, True)
    for ln in refs:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.first_line_indent = Inches(-0.5)
        p.paragraph_format.line_spacing = 1.15 if kind == "dissertation" else 1.0
        p.paragraph_format.space_after = Pt(6)
        # italicise APA venue/title cannot be inferred from plain text; entries are plain
        add_inline(p, ln.replace("*", "\\*") if False else ln)


# ---------------------------------------------------------------- dissertation
def read(p):
    return open(os.path.join(ROOT, p), encoding="utf-8").read()


def build_dissertation(out_path):
    doc = Document()
    style_setup(doc, "dissertation")
    counters = {"Figure": 0, "Table": 0}
    C = WD_ALIGN_PARAGRAPH.CENTER
    # cover
    para(doc, TITLE.upper(), C, bold=True, size=16, space_after=14, spacing=1.15)
    para(doc, SUBTITLE, C, bold=True, size=13, space_after=24, spacing=1.15)
    para(doc, "BY", C, bold=True, size=13, space_after=12)
    para(doc, "ARIYO, TEMITOPE WILLIAMS", C, bold=True, size=14, space_after=6)
    para(doc, "249074175", C, bold=True, size=13, space_after=30)
    para(doc, "SUBMITTED TO", C, bold=True, size=12, space_after=6)
    para(doc, "THE DEPARTMENT OF COMPUTER SCIENCES, FACULTY OF COMPUTING AND INFORMATICS, SCHOOL OF POSTGRADUATE STUDIES, UNIVERSITY OF LAGOS, LAGOS, NIGERIA.",
         C, bold=True, size=12, space_after=14, spacing=1.15)
    para(doc, "IN PARTIAL FULFILMENT OF THE REQUIREMENTS FOR THE AWARD OF THE DEGREE OF", C, bold=True, size=12, space_after=14, spacing=1.15)
    para(doc, "MASTER OF INFORMATION TECHNOLOGY IN COMPUTER SCIENCE", C, bold=True, size=12, space_after=30, spacing=1.15)
    para(doc, "OCTOBER, 2026", C, bold=True, size=12)
    # section 2: front matter, roman numerals
    s2 = doc.add_section(WD_SECTION.NEW_PAGE)
    footer_page(doc.sections[0], show=False)
    pgnum(s2, "lowerRoman", 1)
    footer_page(s2, True)

    def heading_plain(t):
        p = para(doc, t, C, bold=True, size=14, space_after=18)
        p.paragraph_format.keep_with_next = True
        return p

    heading_plain("CERTIFICATION")
    p = para(doc, "", WD_ALIGN_PARAGRAPH.JUSTIFY)
    r = p.add_run("This is to certify that Ariyo, Temitope Williams with Matriculation Number 249074175 carried out this project entitled “")
    set_font(r)
    r = p.add_run(TITLE.upper())
    set_font(r, bold=True)
    r = p.add_run("” under the supervision of Dr. E. P. Fasina, Department of Computer Sciences, Faculty of Computing and Informatics, University of Lagos, "
                  "in partial fulfilment of the requirements for the award of the Master of Information Technology degree in Computer Science.")
    set_font(r)
    for _ in range(2):
        para(doc, "")
    for name, role in (("Dr. E. P. Fasina", "Supervisor"), ("Prof. F. A. Oladeji", "Head of Department")):
        t = doc.add_table(rows=3, cols=2)
        for j in range(2):
            t.cell(0, j).text = "__________________________"
        t.cell(1, 0).text = name
        t.cell(1, 1).text = "Date"
        t.cell(2, 0).text = role
        t.cell(2, 1).text = ""
        for row in t.rows:
            for c in row.cells:
                for pp in c.paragraphs:
                    pp.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    pp.paragraph_format.line_spacing = 1.0
                    for rr in pp.runs:
                        set_font(rr, 12)
        para(doc, "")
        para(doc, "")
    page_break(doc)
    heading_plain("DEDICATION")
    render_md(doc, read("output/dissertation/src/dedication.md"), "front", counters, "dedication")
    page_break(doc)
    heading_plain("ACKNOWLEDGEMENT")
    render_md(doc, read("output/dissertation/src/acknowledgement.md"), "front", counters, "acknowledgement")
    page_break(doc)
    heading_plain("TABLE OF CONTENTS")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    add_field(p, 'TOC \\o "1-3" \\h \\z \\u', "Right-click and choose Update Field to build the table of contents.", size=12)
    page_break(doc)
    heading_plain("LIST OF FIGURES")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    add_field(p, 'TOC \\h \\z \\c "Figure"', "Update field to build the list of figures.", size=12)
    page_break(doc)
    heading_plain("LIST OF TABLES")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    add_field(p, 'TOC \\h \\z \\c "Table"', "Update field to build the list of tables.", size=12)
    page_break(doc)
    heading_plain("ABSTRACT")
    render_md(doc, read("output/dissertation/src/abstract.md"), "front", counters, "abstract")
    # section 3: body
    s3 = doc.add_section(WD_SECTION.NEW_PAGE)
    pgnum(s3, "decimal", 1)
    footer_page(s3, True)
    first = True
    for ch in ("ch1", "ch2", "ch3", "ch4", "ch5"):
        txt = read(f"output/dissertation/src/{ch}.md")
        if first:
            # first chapter starts on the new section page: avoid a blank page
            txt_lines = txt.split("\n")
            first = False
            h_idx = next(i for i, l in enumerate(txt_lines) if l.startswith("# "))
            h = txt_lines[h_idx][2:]
            hh = doc.add_heading("", level=1)
            add_inline(hh, h.strip())
            for r in hh.runs:
                set_font(r, None, True)
                r.font.color.rgb = RGBColor(0, 0, 0)
            txt = "\n".join(txt_lines[h_idx + 1:])
        render_md(doc, txt, "dissertation", counters, ch)
    refs = collect_refs([os.path.join(ROOT, f"output/dissertation/src/refs_used_{n}.txt") for n in ("ch1", "ch2", "ch3", "ch4", "ch5")])
    doc.add_page_break()
    add_references(doc, refs, "dissertation")
    render_md(doc, read("output/dissertation/src/appendices.md"), "dissertation", counters, "appendices")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    doc.save(out_path)
    return len(refs)


# ---------------------------------------------------------------- paper
def build_paper(out_path):
    doc = Document()
    style_setup(doc, "paper")
    counters = {"Figure": 0, "Table": 0}
    C = WD_ALIGN_PARAGRAPH.CENTER
    src = read("output/journal_paper/src/paper.md")
    title = next(l[2:].strip() for l in src.split("\n") if l.startswith("% ") and not l.startswith("% Authors"))
    p = para(doc, title, C, bold=True, size=16, space_after=10, spacing=1.1)
    p = para(doc, "", C, space_after=2)
    r = p.add_run("Temitope W. Ariyo"); set_font(r, 12)
    r = p.add_run("1*"); set_font(r, 12); r.font.superscript = True
    r = p.add_run(" and Ebun P. Fasina"); set_font(r, 12)
    r = p.add_run("1"); set_font(r, 12); r.font.superscript = True
    p = para(doc, "", C, space_after=2)
    r = p.add_run("1"); set_font(r, 10.5); r.font.superscript = True
    r = p.add_run("Machine Learning Research Group, Department of Artificial Intelligence and Robotics, Faculty of Computing and Informatics, University of Lagos, Akoka, Lagos, Nigeria")
    set_font(r, 10.5)
    para(doc, "temitopeariyo6@gmail.com, efasina@unilag.edu.ng", C, size=10.5, space_after=2)
    para(doc, "*Corresponding author", C, italic=True, size=10.5, space_after=12)
    sec = doc.sections[0]
    footer_page(sec, True)
    h1 = [0]
    render_md(doc, "\n".join(l for l in src.split("\n") if not l.startswith("% ")), "paper", counters, "paper", num_h1=True, h1_counter=h1)
    refs = collect_refs([os.path.join(ROOT, "output/journal_paper/src/refs_used_paper.txt")])
    add_references(doc, refs, "paper")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    doc.save(out_path)
    return len(refs)


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    pdf = "--no-pdf" not in sys.argv
    outs = []
    if which in ("dissertation", "all"):
        o = os.path.join(ROOT, "output/dissertation/Ariyo_AfriCoT-VLA_Dissertation.docx")
        print("dissertation refs:", build_dissertation(o)); outs.append(o)
    if which in ("paper", "all"):
        o = os.path.join(ROOT, "output/journal_paper/Ariyo_Fasina_AfriCoT-VLA_Journal_Paper.docx")
        print("paper refs:", build_paper(o)); outs.append(o)
    print("unresolved:", UNRESOLVED)
    if pdf:
        import subprocess
        lo = os.environ.get("LO_PROGRAM", "C:/lo/SourceDir/LibreOffice/program")
        for o in outs:
            subprocess.run([os.path.join(lo, "python.exe"), "-I", os.path.join(ROOT, "scripts", "lo_refresh.py"), o],
                           env={**os.environ, "LO_PROGRAM": lo})


if __name__ == "__main__":
    main()
