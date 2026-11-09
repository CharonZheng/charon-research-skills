"""Read OOXML and apply a small, content-preserving formatting allowlist."""
from __future__ import annotations

import copy
import hashlib
import re
import zipfile
from pathlib import Path

from lxml import etree as E

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
      "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main"}


def tag(name):
    prefix, local = name.split(":")
    return "{" + NS[prefix] + "}" + local


def parse(data):
    return E.fromstring(data, E.XMLParser(resolve_entities=False, no_network=True))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            raise ValueError("DOCX has duplicate ZIP member names")
        if sum(i.file_size for i in z.infolist()) > 512 * 1024 * 1024:
            raise ValueError("DOCX uncompressed size exceeds 512 MiB")
        parts = {n: z.read(n) for n in names}
    if "word/document.xml" not in parts or "[Content_Types].xml" not in parts:
        raise ValueError("Not a DOCX package")
    return parts, parse(parts["word/document.xml"])


def text(node):
    return "".join(t.text or "" for t in node.iter(tag("w:t"))
                   if not any(a.tag == tag("w:del") for a in t.iterancestors()))


def in_table(node):
    return any(a.tag == tag("w:tbl") for a in node.iterancestors())


def heading_level(p, styles):
    direct = p.find("w:pPr/w:outlineLvl", NS)
    if direct is not None:
        n = int(direct.get(tag("w:val")))
        return n + 1 if n < 9 else None
    style = p.find("w:pPr/w:pStyle", NS)
    sid = style.get(tag("w:val")) if style is not None else ""
    seen = set()
    while sid and sid not in seen:
        seen.add(sid)
        info = styles.get(sid, {})
        if info.get("level") is not None:
            return info["level"]
        match = re.fullmatch(r"(?:heading|标题)\s*(\d+)", info.get("name", sid), re.I)
        if match:
            return int(match[1])
        sid = info.get("based_on", "")
    return None


def audit(path):
    parts, root = load(path)
    styles = {}
    if "word/styles.xml" in parts:
        for s in parse(parts["word/styles.xml"]).findall("w:style", NS):
            name, base, level = (s.find(k, NS) for k in
                                 ("w:name", "w:basedOn", "w:pPr/w:outlineLvl"))
            n = int(level.get(tag("w:val"))) if level is not None else 9
            styles[s.get(tag("w:styleId"))] = {
                "name": name.get(tag("w:val")) if name is not None else "",
                "based_on": base.get(tag("w:val")) if base is not None else "",
                "level": n + 1 if n < 9 else None}
    paras = []
    for i, p in enumerate(root.findall(".//w:body//w:p", NS)):
        st = p.find("w:pPr/w:pStyle", NS)
        paras.append({"index": i, "text": text(p), "in_table": in_table(p),
                      "style": st.get(tag("w:val")) if st is not None else None,
                      "heading_level": heading_level(p, styles),
                      "has_drawing": bool(p.findall('.//w:drawing', NS)),
                      "has_equation": bool(p.findall('.//m:oMath', NS))})
    captions = {"figures": [], "tables": []}
    for p in paras:
        for kind, pattern in (("figures", r"^(?:Figure|Fig\.)\s*(\d+)\b"),
                              ("tables", r"^Table\s*(\d+)\b")):
            match = re.match(pattern, p["text"], re.I)
            if match:
                captions[kind].append({"number": int(match[1]), "paragraph": p["index"]})
    ref_start = next((i for i, p in enumerate(paras)
                      if re.fullmatch(r"(?:\d+[.\s]*)?(?:References|Bibliography|参考文献)",
                                      p["text"].strip(), re.I)), None)
    refs, cited, ref_entries = set(), set(), []
    ref_end, boundary = None, None
    if ref_start is not None:
        for p in paras[ref_start + 1:]:
            if p["heading_level"] or p["in_table"] or p["has_drawing"] or re.match(
                    r'^(?:(?:Supplementary|Supplemental)\s+)?(?:Figures?|Fig\.|Tables?)\s+\d+\b', p['text'], re.I):
                ref_end, boundary = p['index'], 'heading, table, figure or caption'
                break
            m = re.match(r"^\s*(?:\[(\d+)\]|(\d+)[.)])\s*", p["text"])
            if m:
                number = int(m[1] or m[2])
                if number > 0:
                    refs.add(number); ref_entries.append(number)
        if ref_end is None:
            ref_end, boundary = len(paras), 'document end'
        for p in paras[:ref_start] + paras[ref_end:]:
            for group in re.findall(r"\[([\d\s,;–-]+)\]", p["text"]):
                for token in re.split(r"[,;]", group):
                    m = re.fullmatch(r"\s*(\d+)(?:\s*[-–]\s*(\d+))?\s*", token)
                    if m:
                        lo, hi = int(m[1]), int(m[2] or m[1])
                        if 0 < lo <= hi and hi - lo < 1000:
                            cited.update(range(lo, hi + 1))
    counts = {name: len(root.findall(xpath, NS)) for name, xpath in {
        "tables": ".//w:tbl", "equations": ".//m:oMath", "drawings": ".//w:drawing",
        "field_codes": ".//w:instrText", "simple_fields": ".//w:fldSimple",
        "bookmarks": ".//w:bookmarkStart", "insertions": ".//w:ins",
        "deletions": ".//w:del", "comment_anchors": ".//w:commentRangeStart",
        "footnote_references": ".//w:footnoteReference"}.items()}
    # Lazy import keeps the OOXML reader reusable by the formatting module.
    from formatting import formatting_parts
    labels = []
    for i, p in enumerate(root.findall('.//w:body//w:p', NS)):
        if in_table(p) or not p.findall('.//m:oMath', NS):
            continue
        for n in p.findall('.//m:t', NS) + p.findall('w:r/w:t', NS):
            match = re.fullmatch(r'\s*\(([\d\s]+|\d+[a-z]|\d+\.\d+)\)[.,]?', n.text or '')
            if match:
                labels.append({'paragraph': i, 'label': re.sub(r'\s+', '', match[1])})
    numeric_labels = [int(x['label']) for x in labels if x['label'].isdigit()]
    citation_orders = {}
    caption_paras = {c['paragraph'] for values in captions.values() for c in values}
    for kind, word in [('figures', r'Figures?|Fig\.'), ('tables', r'Tables?')]:
        order = []
        for p in paras:
            if p['in_table'] or p['index'] in caption_paras or (ref_start is not None and ref_start <= p['index'] < ref_end):
                continue
            for m in re.finditer(r'\b(?:(Supplementary|Supplemental)\s+)?(?:' + word + r')\s+(\d+)[a-z]?\b', p['text'], re.I):
                number = int(m[2])
                if not m[1] and number not in order:
                    order.append(number)
        citation_orders[kind] = order
    return {"file": str(Path(path).resolve()), "sha256": digest(Path(path).read_bytes()),
            "paragraphs": paras, "objects": counts,
            "parts": {n: digest(b) for n, b in parts.items()},
            "caption_candidates": captions,
            "first_display_citation_order": citation_orders,
            "equation_number_candidates": {"labels": labels, "duplicates": sorted({n for n in numeric_labels if numeric_labels.count(n) > 1}),
                "sequential_from_one": bool(numeric_labels) and numeric_labels == list(range(1, len(numeric_labels) + 1)) and len(numeric_labels) == len(labels)},
            "numeric_reference_candidates": {"list": sorted(refs), "cited": sorted(cited),
                "possibly_uncited": sorted(refs - cited), "possibly_undefined": sorted(cited - refs),
                "duplicates": sorted({n for n in ref_entries if ref_entries.count(n) > 1}),
                "range": {"start": ref_start, "end_exclusive": ref_end, "boundary": boundary}},
            "formatting": formatting_parts(parts),
            "limitations": ["Structure and object inventory cover the main document; headings/captions/numeric references are heuristic. Formatting includes supported text stories.",
                "Footnote markers, superscript citations, reference plugins and text inside graphics need separate review.",
                "No rendering, author-fact, image-quality or official-policy verification."]}


P_PROPS = {"alignment": "w:jc", "first_line_indent_mm": "w:ind",
           "line_spacing": "w:spacing", "space_before_pt": "w:spacing",
           "space_after_pt": "w:spacing", "page_break_before": "w:pageBreakBefore"}


def child(parent, name):
    node = parent.find(name, NS)
    if node is None:
        node = E.Element(tag(name))
        orders = {
            tag("w:pPr"): "pStyle keepNext keepLines pageBreakBefore framePr widowControl numPr suppressLineNumbers pBdr shd tabs suppressAutoHyphens kinsoku wordWrap overflowPunct topLinePunct autoSpaceDE autoSpaceDN bidi adjustRightInd snapToGrid spacing ind contextualSpacing mirrorIndents suppressOverlap jc textDirection textAlignment textboxTightWrap outlineLvl divId cnfStyle rPr sectPr pPrChange",
            tag("w:rPr"): "rStyle rFonts b bCs i iCs caps smallCaps strike dstrike outline shadow emboss imprint noProof snapToGrid vanish webHidden color spacing w kern position sz szCs highlight u effect bdr shd fitText vertAlign rtl cs em lang eastAsianLayout specVanish oMath rPrChange",
            tag("w:sectPr"): "headerReference footerReference footnotePr endnotePr type pgSz pgMar paperSrc pgBorders lnNumType pgNumType cols formProt vAlign noEndnote titlePg textDirection bidi rtlGutter docGrid printerSettings sectPrChange"}
        order = orders.get(parent.tag, "").split()
        rank = order.index(name.split(":")[1]) if name.split(":")[1] in order else len(order)
        for i, sibling in enumerate(parent):
            local = E.QName(sibling).localname
            if local in order and order.index(local) > rank:
                parent.insert(i, node)
                break
        else:
            parent.append(node)
    return node


def numeric(value, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
        raise ValueError(f"Expected a number in [{low}, {high}]")
    return value


def apply_operations(root, operations, styles_root=None):
    from formatting import apply_paragraph
    paras = root.findall(".//w:p", NS)
    sections = root.findall(".//w:sectPr", NS)
    if not operations:
        raise ValueError("Formatting plan must contain operations")
    for op in operations:
        kind = op.get("kind")
        if kind == "paragraph_format":
            i = op["paragraph"]
            if type(i) is not int or not 0 <= i < len(paras):
                raise ValueError("Invalid paragraph index")
            p = paras[i]
            if text(p) != op["expected_text"]:
                raise ValueError(f"Paragraph {i} text changed since audit")
            if in_table(p) and op.get("allow_table") is not True:
                raise ValueError("Table paragraph requires explicit allow_table=true")
            if any(p.findall('.//w:' + n, NS) for n in ('ins', 'del', 'pPrChange', 'rPrChange')):
                raise ValueError("Resolve the target paragraph's revision view before formatting")
            apply_paragraph(p, op["format"], styles_root, op.get('run_exemptions', []))
        elif kind == "page_margins":
            i = op["section"]
            if type(i) is not int or not 0 <= i < len(sections):
                raise ValueError("Invalid section index")
            margins = op["margins_mm"]
            if not isinstance(margins, dict) or not margins or set(margins) - {"top", "bottom", "left", "right"}:
                raise ValueError("Unknown or empty margins")
            node = child(sections[i], "w:pgMar")
            for key, value in margins.items():
                node.set(tag("w:" + key), str(round(numeric(value, 1, 100) * 1440 / 25.4)))
        else:
            raise ValueError(f"Unsupported operation: {kind}")


def normalized(root):
    root = copy.deepcopy(root)
    removals = {"w:jc": None, "w:pageBreakBefore": None, "w:pStyle": None,
                "w:outlineLvl": None, "w:contextualSpacing": None, "w:snapToGrid": None,
                "w:ind": ("firstLine", "hanging", "hangingChars", "firstLineChars"),
                "w:spacing": ("line", "lineRule", "before", "after", "beforeLines", "afterLines", "beforeAutospacing", "afterAutospacing"),
                "w:rFonts": ("ascii", "hAnsi", "eastAsia", "cs", "asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"),
                "w:sz": None, "w:szCs": None, "w:b": None, "w:bCs": None, "w:i": None, "w:iCs": None,
                "w:pgMar": ("top", "bottom", "left", "right")}
    # Only strip properties from the locations the formatter is permitted to edit.
    for name, attrs in removals.items():
        parent = "w:pPr" if name in set(P_PROPS.values()) | {"w:pStyle", "w:outlineLvl", "w:contextualSpacing", "w:snapToGrid"} else "w:rPr"
        xp = ".//w:sectPr/w:pgMar" if name == "w:pgMar" else f".//{parent}/{name}"
        for node in root.findall(xp, NS):
            if attrs is None:
                node.getparent().remove(node)
            else:
                for attr in attrs:
                    node.attrib.pop(tag("w:" + attr), None)
                if not node.attrib and len(node) == 0:
                    node.getparent().remove(node)
    for name in ("w:pPr", "w:rPr"):
        for node in root.findall(".//" + name, NS):
            if len(node) == 0 and not node.attrib:
                node.getparent().remove(node)
    return E.tostring(root, method="c14n")


def verify(before, after):
    from formatting import story_part
    a, _ = load(before); b, _ = load(after)
    changed = sorted(n for n in set(a) | set(b) if a.get(n) != b.get(n))
    unexpected = [n for n in changed if not story_part(n) or n not in a or n not in b]
    comparisons = {n: normalized(parse(a[n])) == normalized(parse(b[n]))
                   for n in changed if story_part(n) and n in a and n in b}
    content_equal = all(comparisons.values())
    return {"passed": not unexpected and content_equal,
            "before_sha256": digest(Path(before).read_bytes()),
            "after_sha256": digest(Path(after).read_bytes()),
            "changed_parts": changed, "unexpected_parts": unexpected,
            "nonformat_document_equal": content_equal, "story_comparisons": comparisons,
            "visual_validation": "not_checked"}


def write_docx(source, out, root, updates=None):
    payloads = updates if updates is not None else {
        "word/document.xml": E.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)}
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(out, "w") as dst:
        for info in src.infolist():
            dst.writestr(info, payloads.get(info.filename, src.read(info.filename)))
