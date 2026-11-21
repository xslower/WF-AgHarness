# -*- coding: utf-8 -*-
from __future__ import annotations

import zipfile
from pathlib import Path

CT = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'


# ---------------------------------------------------------------- xlsx

def _col(i: int) -> str:
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def make_xlsx(path: Path, rows: list[list], sheet_names: list[str] | None = None) -> Path:
    sheets = sheet_names or ["Sheet1"]
    xml_parts = []
    for sh in sheets:
        cells = []
        for r, row in enumerate(rows, 1):
            cs = []
            for c, v in enumerate(row):
                ref = f"{_col(c)}{r}"
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    cs.append(f'<c r="{ref}"><v>{v}</v></c>')
                else:
                    esc = str(v).replace("&", "&amp;").replace("<", "&lt;")
                    cs.append(f'<c r="{ref}" t="inlineStr"><is><t>{esc}</t></is></c>')
            cells.append(f'<row r="{r}">{"".join(cs)}</row>')
        xml_parts.append(
            CT + '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{"".join(cells)}</sheetData></worksheet>')

    sheet_entries = "".join(
        f'<sheet name="{sh}" sheetId="{i}" r:id="rId{i}"/>'
        for i, sh in enumerate(sheets, 1))
    rels = "".join(
        f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/'
        f'officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, len(sheets) + 1))
    overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/'
        f'vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(1, len(sheets) + 1))

    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", CT +
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-'
                   'package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.'
                   f'openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>{overrides}</Types>')
        z.writestr("_rels/.rels", CT +
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
                   'officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                   '</Relationships>')
        z.writestr("xl/workbook.xml", CT +
                   '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                   f'<sheets>{sheet_entries}</sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", CT +
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   f'{rels}</Relationships>')
        for i, xml in enumerate(xml_parts, 1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", xml)
    return path


BAD_STYLES = (
    CT +
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
    # 关键：gradientFill 让 openpyxl 在 load_workbook 阶段直接抛 TypeError(expected Fill)
    '<fills count="1"><fill><gradientFill degree="90"><stop position="0">'
    '<color rgb="FFFFFFFF"/></stop></gradientFill></fill></fills>'
    '<borders count="1"><border/></borders>'
    '<cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="1"><xf/></cellXfs>'
    '</styleSheet>')


def make_xlsx_bad_styles(path: Path, rows: list[list]) -> Path:
    make_xlsx(path, rows)
    tmp = path.with_suffix(".tmp.xlsx")
    path.rename(tmp)
    with zipfile.ZipFile(tmp) as zin, zipfile.ZipFile(path, "w") as zout:
        for item in zin.infolist():
            if item.filename == "xl/styles.xml":
                continue
            zout.writestr(item, zin.read(item.filename))
        zout.writestr("xl/styles.xml", BAD_STYLES)
    tmp.unlink()
    return path


# ---------------------------------------------------------------- docx

def make_docx(path: Path, paragraphs: list[dict]) -> Path:
    body = []
    for item in paragraphs:
        if item.get("table"):
            rows = "".join(
                "<w:tr>" + "".join(
                    f'<w:tc><w:p><w:r><w:t>{c}</w:t></w:r></w:p></w:tc>' for c in r) + "</w:tr>"
                for r in item["table"])
            body.append(f"<w:tbl>{rows}</w:tbl>")
            continue
        style = item.get("style")
        ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
        esc = str(item.get("text") or "")
        body.append(f'<w:p>{ppr}<w:r><w:t xml:space="preserve">{esc}</w:t></w:r></w:p>')

    doc = (CT + '<w:document xmlns:w="http://schemas.openxmlformats.org/'
           'wordprocessingml/2006/main"><w:body>' + "".join(body) + "</w:body></w:document>")
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", CT +
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-'
                   'package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/word/document.xml" ContentType="application/vnd.'
                   'openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr("_rels/.rels", CT +
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
                   'officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                   '</Relationships>')
        z.writestr("word/document.xml", doc)
    return path


# ---------------------------------------------------------------- pptx

def make_pptx(path: Path, slides: list[dict]) -> Path:
    n = len(slides)
    parts = []
    for s in slides:
        shapes = []
        if s.get("title"):
            shapes.append(
                '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title 1"/><p:cNvSpPr/>'
                '<p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>'
                '<p:txBody><a:bodyPr/><a:p><a:r><a:t>%s</a:t></a:r></a:p></p:txBody></p:sp>'
                % s["title"])
        if s.get("text"):
            paras = "".join(f"<a:p><a:r><a:t>{ln}</a:t></a:r></a:p>"
                            for ln in s["text"].splitlines())
            shapes.append(
                '<p:sp><p:nvSpPr><p:cNvPr id="3" name="Content 2"/><p:cNvSpPr/>'
                '<p:nvPr><p:ph idx="1"/></p:nvPr></p:nvSpPr>'
                f"<p:txBody><a:bodyPr/>{paras}</p:txBody></p:sp>")
        if s.get("table"):
            rows = "".join(
                "<a:tr>" + "".join(f"<a:tc><a:t>{c}</a:t></a:tc>" for c in r) + "</a:tr>"
                for r in s["table"])
            shapes.append('<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="4" name="Table 3"/>'
                          '<p:cNvGraphicFramePr/></p:nvGraphicFramePr>'
                          '<a:graphic><a:graphicData '
                          'uri="http://schemas.openxmlformats.org/drawingml/2006/table">'
                          '<a:tbl><a:tblGrid/>'
                          f"{rows}</a:tbl></a:graphicData></a:graphic></p:graphicFrame>")
        parts.append(
            CT + '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            f'<p:cSld><p:spTree>{"".join(shapes)}</p:spTree></p:cSld></p:sld>')

    ids = "".join(f'<p:sldId id="{255 + i}" r:id="rId{i}"/>' for i in range(1, n + 1))
    rels = "".join(
        f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        f'relationships/slide" Target="slides/slide{i}.xml"/>' for i in range(1, n + 1))
    with zipfile.ZipFile(path, "w") as z:
        # slide 的 content-type override 不能少：python-pptx 靠 content type 决定
        # Part 类型，缺了就退化成通用 Part（访问 .slide 报 AttributeError）。
        slide_ct = "".join(
            f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.'
            f'openxmlformats-officedocument.presentationml.slide+xml"/>'
            for i in range(1, n + 1))
        z.writestr("[Content_Types].xml", CT +
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-'
                   'package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.'
                   'openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
                   f'{slide_ct}</Types>')
        z.writestr("_rels/.rels", CT +
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
                   'officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>'
                   '</Relationships>')
        z.writestr("ppt/presentation.xml", CT +
                   '<p:presentation xmlns:p="http://schemas.openxmlformats.org/'
                   'presentationml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                   f"<p:sldIdLst>{ids}</p:sldIdLst></p:presentation>")
        z.writestr("ppt/_rels/presentation.xml.rels", CT +
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   f"{rels}</Relationships>")
        for i, xml in enumerate(parts, 1):
            z.writestr(f"ppt/slides/slide{i}.xml", xml)
    return path
