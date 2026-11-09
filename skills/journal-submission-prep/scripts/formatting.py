"""Resolve supported Word formatting and independently check a scoped contract.

This reads declared effective properties, not installed fonts or pixel geometry.
Unresolved themes, conditional table styles and revisions cannot earn a pass.
"""
from __future__ import annotations

import re
from pathlib import Path

from docx_tools import NS, child, digest, in_table, load, numeric, parse, tag, text

FONT_SLOTS = {"font_ascii": "ascii", "font_hansi": "hAnsi",
              "font_east_asia": "eastAsia", "font_cs": "cs"}
THEMES = {"ascii": "asciiTheme", "hAnsi": "hAnsiTheme", "eastAsia": "eastAsiaTheme", "cs": "cstheme"}
PARAGRAPH_KEYS = {"line_spacing", "line_spacing_pt", "line_rule", "space_before_pt", "space_after_pt",
                  "first_line_indent_mm", "first_line_indent_chars", "alignment", "heading_level",
                  "page_break_before", "contextual_spacing", "snap_to_grid", "style_id"}
RUN_KEYS = {"font_name", "font_size_pt", "font_size_cs_pt", "bold", "italic", *FONT_SLOTS}
EXPECTED_KEYS = PARAGRAPH_KEYS | RUN_KEYS


def story_part(name: str) -> bool:
    return name == "word/document.xml" or bool(re.fullmatch(r"word/(?:header\d+|footer\d+|footnotes|endnotes)\.xml", name))


def onoff(node, default=False):
    return default if node is None else node.get(tag("w:val"), "1").lower() not in {"0", "false", "off"}


def attributes(node):
    return {} if node is None else {k.rsplit("}", 1)[-1]: v for k, v in node.attrib.items()}


def font_slot(char: str) -> str:
    n = ord(char)
    if n < 128:
        return "ascii"
    if 0x2E80 <= n <= 0xA4CF or 0xAC00 <= n <= 0xD7AF or 0xF900 <= n <= 0xFAFF or 0xFE30 <= n <= 0xFFEF or 0x20000 <= n <= 0x3134F:
        return "eastAsia"
    if 0x0590 <= n <= 0x0DFF or 0xFB1D <= n <= 0xFEFC:
        return "cs"
    return "hAnsi"


class FormatResolver:
    def __init__(self, parts: dict):
        self.parts = parts
        self.styles_root = parse(parts["word/styles.xml"]) if "word/styles.xml" in parts else None
        self.styles = {} if self.styles_root is None else {
            s.get(tag("w:styleId")): s for s in self.styles_root.findall("w:style", NS)}
        self.default_style = next((sid for sid, s in self.styles.items()
                                   if s.get(tag("w:type")) == "paragraph" and s.get(tag("w:default")) in {"1", "true"}), None)
        self.theme = parse(parts["word/theme/theme1.xml"]) if "word/theme/theme1.xml" in parts else None

    def chain(self, sid):
        result, seen = [], set()
        while sid:
            if sid in seen:
                raise ValueError("Cyclic Word style inheritance")
            seen.add(sid)
            style = self.styles.get(sid)
            if style is None:
                break
            result.append(style)
            base = style.find("w:basedOn", NS)
            sid = base.get(tag("w:val")) if base is not None else None
        return list(reversed(result))

    def theme_font(self, token, slot, lang):
        if self.theme is None or not token or not token.startswith(("major", "minor")):
            return None
        family = "majorFont" if token.startswith("major") else "minorFont"
        group = self.theme.find(f".//a:fontScheme/a:{family}", NS)
        if group is None:
            return None
        name = "ea" if slot == "eastAsia" else "cs" if slot == "cs" else "latin"
        node = group.find("a:" + name, NS)
        if node is not None and node.get("typeface"):
            return node.get("typeface")
        script = {"zh-cn": "Hans", "zh-sg": "Hans", "zh-tw": "Hant", "zh-hk": "Hant",
                  "ja-jp": "Jpan", "ko-kr": "Hang"}.get((lang or "").lower())
        if script:
            node = group.find(f"a:font[@script='{script}']", NS)
            return None if node is None else node.get("typeface")
        return None

    def complete_chain(self, sid):
        seen = set()
        while sid:
            if sid in seen:
                raise ValueError('Cyclic Word style inheritance')
            seen.add(sid)
            if sid not in self.styles:
                return False
            base = self.styles[sid].find('w:basedOn', NS)
            sid = base.get(tag('w:val')) if base is not None else None
        return True

    def paragraph(self, p, section=None):
        sid_node = p.find("w:pPr/w:pStyle", NS)
        sid = sid_node.get(tag("w:val")) if sid_node is not None else self.default_style
        styles = self.chain(sid)
        table_layers, table_uncertain = [], False
        if in_table(p):
            table = next(a for a in p.iterancestors() if a.tag == tag("w:tbl"))
            table_style = table.find("w:tblPr/w:tblStyle", NS)
            if table_style is not None:
                table_layers = self.chain(table_style.get(tag("w:val")))
                table_uncertain = any(s.findall("w:tblStylePr/w:rPr", NS) or s.findall("w:tblStylePr/w:pPr", NS)
                                      for s in table_layers)
        defaults = self.styles_root.find("w:docDefaults/w:pPrDefault/w:pPr", NS) if self.styles_root is not None else None
        layers = [defaults, *[s.find("w:pPr", NS) for s in table_layers + styles], p.find("w:pPr", NS)]
        spacing, indent, vals = {}, {}, {}
        for layer in layers:
            if layer is None:
                continue
            spacing.update(attributes(layer.find("w:spacing", NS)))
            indent.update(attributes(layer.find("w:ind", NS)))
            for name in ("jc", "outlineLvl", "pageBreakBefore", "contextualSpacing", "snapToGrid"):
                n = layer.find("w:" + name, NS)
                if n is not None:
                    vals[name] = n.get(tag("w:val"), "1")
        grid = section.find("w:docGrid", NS) if section is not None else None
        has_grid = grid is not None and grid.get(tag("w:type"), "default") in {"lines", "linesAndChars", "snapToChars"}
        rule = spacing.get("lineRule", "auto")
        line = float(spacing.get("line", 240))
        def space(side):
            if spacing.get(side + "Autospacing", "0").lower() not in {"0", "false", "off"}:
                return None
            if side + "Lines" in spacing and float(spacing[side + "Lines"]) != 0:
                return None
            return float(spacing.get(side, 0)) / 20
        char_indent = float(indent["firstLineChars"]) / 100 if "firstLineChars" in indent else None
        hung = "hanging" in indent or "hangingChars" in indent
        effective = {
            "style_id": sid, "heading_level": int(vals.get("outlineLvl", 9)) + 1 if int(vals.get("outlineLvl", 9)) < 9 else 0,
            "line_rule": rule, "line_spacing": line / 240 if rule == "auto" else None,
            "line_spacing_pt": line / 20 if rule in {"exact", "atLeast"} else None,
            "space_before_pt": space("before"), "space_after_pt": space("after"),
            "first_line_indent_chars": char_indent,
            "first_line_indent_mm": None if char_indent is not None or hung else float(indent.get("firstLine", 0)) * 25.4 / 1440,
            "alignment": vals.get("jc", "left"),
            "page_break_before": vals.get("pageBreakBefore", "0").lower() not in {"0", "false", "off"},
            "contextual_spacing": vals.get("contextualSpacing", "0").lower() not in {"0", "false", "off"},
            "snap_to_grid": vals.get("snapToGrid", "1" if has_grid else "0").lower() not in {"0", "false", "off"}}
        issues = []
        referenced_styles = [sid] + [n.get(tag('w:val')) for n in p.findall('.//w:rStyle', NS)]
        if in_table(p):
            referenced_styles += [n.get(tag('w:val')) for n in table.findall('w:tblPr/w:tblStyle', NS)]
        if any(not self.complete_chain(s) for s in referenced_styles):
            issues.append('missing_style_definition')
        if p.findall('.//w:txbxContent', NS) or any(a.tag == tag('w:txbxContent') for a in p.iterancestors()):
            issues.append('text_box_layout_not_checked')
        if table_uncertain:
            issues.append("conditional_table_style")
        if p.findall(".//w:pPrChange", NS) or p.findall(".//w:rPrChange", NS) or p.findall(".//w:ins", NS) or p.findall(".//w:del", NS):
            issues.append("unaccepted_revisions")
        if any(layer is not None and layer.find('w:numPr', NS) is not None for layer in layers):
            issues.append("numbering_marker_format_not_checked")
        if p.findall('.//w:rtl', NS) or any(s.findall('w:rPr/w:rtl', NS) or s.findall('w:rPr/w:cs', NS) for s in styles):
            issues.append('complex_script_override_not_checked')
        runs = []
        for i, r in enumerate(p.findall(".//w:r", NS)):
            if not r.findall("w:t", NS) or any(a.tag == tag("w:del") for a in r.iterancestors()):
                continue
            if r.find("w:rPr/w:vanish", NS) is not None and onoff(r.find("w:rPr/w:vanish", NS)):
                continue
            runs.append(self.run(r, i, styles, table_layers))
        return {"text": text(p), "in_table": in_table(p), "paragraph": effective, "runs": runs,
                "issues": issues, "raw_spacing": spacing}

    def run(self, run, index, pstyles, table_styles):
        default = self.styles_root.find("w:docDefaults/w:rPrDefault/w:rPr", NS) if self.styles_root is not None else None
        direct = run.find("w:rPr", NS)
        rstyle = run.find("w:rPr/w:rStyle", NS)
        cstyles = self.chain(rstyle.get(tag("w:val"))) if rstyle is not None else []
        layers = [(default, False), *[(s.find("w:rPr", NS), True) for s in table_styles + pstyles + cstyles], (direct, False)]
        fonts, sizes, toggles, lang = {}, {}, {"b": False, "i": False, "bCs": False, "iCs": False}, {}
        for layer, toggle in layers:
            if layer is None:
                continue
            incoming = attributes(layer.find("w:rFonts", NS))
            for slot, theme in THEMES.items():
                if slot in incoming:
                    fonts.pop(theme, None)
                if theme in incoming:
                    fonts.pop(slot, None)
            fonts.update(incoming)
            lang.update(attributes(layer.find("w:lang", NS)))
            for key in ("sz", "szCs"):
                n = layer.find("w:" + key, NS)
                if n is not None:
                    sizes[key] = float(n.get(tag("w:val"))) / 2
            for key in toggles:
                n = layer.find("w:" + key, NS)
                if n is not None:
                    if toggle:
                        if onoff(n): toggles[key] = not toggles[key]
                    else:
                        toggles[key] = onoff(n)
        txt = text(run)
        forced_cs = onoff(run.find("w:rPr/w:cs", NS))
        slots = sorted({"cs" if forced_cs else font_slot(c) for c in txt if not c.isspace()})
        resolved = {}
        for slot in slots:
            theme = fonts.get(THEMES[slot])
            resolved[slot] = self.theme_font(theme, slot, lang.get("eastAsia" if slot == "eastAsia" else "bidi" if slot == "cs" else "val")) if theme else fonts.get(slot)
        return {"index": index, "text": txt, "fonts": resolved, "font_size_pt": sizes.get("sz"),
                "font_size_cs_pt": sizes.get("szCs"), "bold": toggles["b"], "italic": toggles["i"],
                "bold_cs": toggles["bCs"], "italic_cs": toggles["iCs"]}


def formatting_parts(parts):
    resolver = FormatResolver(parts)
    result = {}
    for name, data in parts.items():
        if not story_part(name):
            continue
        root = parse(data)
        paragraphs = root.findall(".//w:p", NS)
        # A sectPr belongs to the content preceding it, including its paragraph.
        current = None
        sections = {}
        for p in reversed(paragraphs):
            own = p.find("w:pPr/w:sectPr", NS)
            if current is None:
                current = root.find("w:body/w:sectPr", NS)
            if own is not None:
                current = own
            sections[id(p)] = current
        result[name] = [{"index": i, **resolver.paragraph(p, sections[id(p)])} for i, p in enumerate(paragraphs)]
    return result


def same(actual, expected, key):
    if isinstance(expected, bool):
        return type(actual) is bool and actual == expected
    if isinstance(expected, (int, float)):
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            return False
        tolerance = 0.009 if key.endswith("_mm") else 0.0021 if key == "line_spacing" else 0.025 if key.endswith("_pt") and key.startswith("space_") else 0.0001
        return abs(actual - expected) <= tolerance
    return actual == expected


def match_format(row, expected, run_exemptions=()):
    if not expected or set(expected) - EXPECTED_KEYS:
        raise ValueError("Unknown or empty expected format")
    exempt = {}
    for item in run_exemptions:
        if not item.get('reason') or type(item.get('run')) is not int or not item.get('properties') or set(item['properties']) - RUN_KEYS:
            raise ValueError('Run exemption needs run, supported properties and reason')
        if item['run'] not in {r['index'] for r in row['runs']}:
            raise ValueError('Run exemption points to a non-text run')
        exempt.setdefault(item['run'], set()).update(item['properties'])
    findings = []
    if set(expected) & RUN_KEYS and not any(r['fonts'] for r in row['runs']):
        findings.append({'property': 'text_run_coverage', 'status': 'not_checked'})
    for key, value in expected.items():
        if key in PARAGRAPH_KEYS:
            actual = row["paragraph"].get(key)
            findings.append({"property": key, "expected": value, "actual": actual,
                             "status": "not_checked" if actual is None else "pass" if same(actual, value, key) else "fail"})
        elif key in RUN_KEYS:
            for run in row["runs"]:
                if key in exempt.get(run['index'], set()):
                    findings.append({'run': run['index'], 'property': key, 'status': 'exempt'})
                    continue
                targets = []
                if key == "font_name":
                    targets = [("font_" + slot, family) for slot, family in run["fonts"].items()
                               if slot not in {FONT_SLOTS[k] for k in expected if k in FONT_SLOTS}]
                elif key in FONT_SLOTS:
                    slot = FONT_SLOTS[key]
                    targets = [(key, run["fonts"][slot])] if slot in run["fonts"] else []
                elif key in {"font_size_pt", "bold", "italic"}:
                    targets = []
                    if set(run['fonts']) - {'cs'}:
                        targets.append((key, run[key]))
                    if 'cs' in run['fonts'] and not (key == 'font_size_pt' and 'font_size_cs_pt' in expected):
                        cs_key = {"font_size_pt": "font_size_cs_pt", "bold": "bold_cs", "italic": "italic_cs"}[key]
                        targets.append((cs_key, run[cs_key]))
                elif key == 'font_size_cs_pt':
                    targets = [(key, run.get(key))] if 'cs' in run['fonts'] else []
                else:
                    targets = [(key, run.get(key))]
                for prop, actual in targets:
                    findings.append({"run": run["index"], "property": prop, "expected": value, "actual": actual,
                                     "status": "not_checked" if actual is None else "pass" if same(actual, value, key) else "fail"})
    if 'font_name' not in expected and set(expected) & set(FONT_SLOTS):
        for run in row['runs']:
            missing = set(run['fonts']) - {FONT_SLOTS[k] for k in expected if k in FONT_SLOTS}
            if missing:
                findings.append({'run': run['index'], 'property': 'font_slot_coverage', 'status': 'not_checked', 'uncovered_slots': sorted(missing)})
    if any(f["status"] == "fail" for f in findings):
        status = "fail"
    elif any(f["status"] == "not_checked" for f in findings) or not any(f['status'] != 'exempt' for f in findings):
        status = "not_checked"
    elif any(i in row["issues"] for i in ("conditional_table_style", "unaccepted_revisions", 'missing_style_definition', 'text_box_layout_not_checked', 'numbering_marker_format_not_checked', 'complex_script_override_not_checked')):
        status = "needs_confirmation"
    elif any(k in expected for k in ("line_spacing", "line_spacing_pt")) and row["paragraph"]["snap_to_grid"]:
        status = "needs_confirmation"
    elif any(k in expected for k in ("space_before_pt", "space_after_pt")) and row["paragraph"]["contextual_spacing"]:
        status = "needs_confirmation"
    else:
        status = "pass"
    return {"status": status, "findings": findings, "issues": row["issues"], "paragraph": row["index"]}


def apply_paragraph(p, fmt, styles_root=None, run_exemptions=()):
    """Set only explicitly requested properties; never rebuild text or math."""
    if not isinstance(fmt, dict) or not fmt or set(fmt) - EXPECTED_KEYS:
        raise ValueError('Unknown or empty paragraph format')
    if 'line_spacing' in fmt and 'line_spacing_pt' in fmt:
        raise ValueError('Multiple and point line spacing cannot be combined')
    if 'line_rule' in fmt and not {'line_spacing', 'line_spacing_pt'} & set(fmt):
        raise ValueError('line_rule needs an explicit spacing value')
    if 'line_spacing_pt' in fmt and fmt.get('line_rule') not in {'exact', 'atLeast'}:
        raise ValueError('Point line spacing needs exact or atLeast line_rule')
    if 'line_spacing' in fmt and fmt.get('line_rule', 'auto') != 'auto':
        raise ValueError('Multiple line spacing needs auto line_rule')
    if 'first_line_indent_mm' in fmt and 'first_line_indent_chars' in fmt:
        raise ValueError('Choose millimetres or characters for first-line indentation')
    pr = p.find('w:pPr', NS)
    if pr is None:
        from lxml import etree as E
        pr = E.Element(tag('w:pPr')); p.insert(0, pr)
    if 'style_id' in fmt:
        if styles_root is None:
            raise ValueError('No style definitions available')
        node = next((s for s in styles_root.findall('w:style', NS)
                     if s.get(tag('w:styleId')) == fmt['style_id'] and s.get(tag('w:type')) == 'paragraph'), None)
        if node is None:
            raise ValueError('Unknown paragraph style_id')
        child(pr, 'w:pStyle').set(tag('w:val'), fmt['style_id'])
    booleans = {'page_break_before': 'pageBreakBefore', 'contextual_spacing': 'contextualSpacing', 'snap_to_grid': 'snapToGrid'}
    for key, value in fmt.items():
        if key in RUN_KEYS or key in {'style_id', 'line_rule'}:
            continue
        if key in booleans:
            if type(value) is not bool:
                raise ValueError(key + ' must be boolean')
            child(pr, 'w:' + booleans[key]).set(tag('w:val'), '1' if value else '0')
        elif key == 'heading_level':
            if type(value) is not int or not 0 <= value <= 9:
                raise ValueError('heading_level must be 0 (body) or 1-9')
            child(pr, 'w:outlineLvl').set(tag('w:val'), str(value-1 if value else 9))
        elif key == 'alignment':
            if value not in {'left', 'center', 'right', 'both'}:
                raise ValueError('Unsupported alignment')
            child(pr, 'w:jc').set(tag('w:val'), value)
        elif key.startswith('first_line_indent_'):
            node = child(pr, 'w:ind')
            for attr in ('firstLine', 'firstLineChars', 'hanging', 'hangingChars'):
                node.attrib.pop(tag('w:' + attr), None)
            chars = key.endswith('_chars')
            encoded = round(numeric(value, 0, 20 if chars else 100) * (100 if chars else 1440/25.4))
            node.set(tag('w:firstLineChars' if chars else 'w:firstLine'), str(encoded))
        elif key in {'line_spacing', 'line_spacing_pt'}:
            node = child(pr, 'w:spacing')
            node.set(tag('w:line'), str(round(numeric(value, 0.5 if key=='line_spacing' else 1, 5 if key=='line_spacing' else 200) * (240 if key=='line_spacing' else 20))))
            node.set(tag('w:lineRule'), 'auto' if key=='line_spacing' else fmt['line_rule'])
            # Disable inherited grid pitch; a multiplicative value alone is not enough.
            if 'snap_to_grid' not in fmt:
                child(pr, 'w:snapToGrid').set(tag('w:val'), '0')
        elif key in {'space_before_pt', 'space_after_pt'}:
            side = 'before' if key=='space_before_pt' else 'after'
            node = child(pr, 'w:spacing')
            node.set(tag('w:' + side), str(round(numeric(value, 0, 200)*20)))
            node.set(tag('w:' + side + 'Autospacing'), '0')
            node.attrib.pop(tag('w:' + side + 'Lines'), None)
            if 'contextual_spacing' not in fmt:
                child(pr, 'w:contextualSpacing').set(tag('w:val'), '0')
    exemptions = {}
    text_runs = p.findall('.//w:r', NS)
    for item in run_exemptions:
        if not item.get('reason') or type(item.get('run')) is not int or not 0 <= item['run'] < len(text_runs) or not item.get('properties') or set(item['properties']) - RUN_KEYS:
            raise ValueError('Invalid run exemption')
        exemptions.setdefault(item['run'], set()).update(item['properties'])
    for i, run in enumerate(text_runs):
        if not run.findall('w:t', NS) or any(a.tag.startswith('{' + NS['m'] + '}') for a in run.iterancestors()):
            continue
        for key in sorted(set(fmt) & RUN_KEYS, key=lambda k: (k != 'font_name', k != 'font_size_pt', k)):
            if key in exemptions.get(i, set()):
                continue
            value = fmt[key]
            rp = run.find('w:rPr', NS)
            if rp is None:
                from lxml import etree as E
                rp = E.Element(tag('w:rPr')); run.insert(0, rp)
            if key == 'font_name' or key in FONT_SLOTS:
                if not isinstance(value, str) or not value.strip():
                    raise ValueError('Font family must be a nonempty string')
                node = child(rp, 'w:rFonts')
                for slot in THEMES if key=='font_name' else [FONT_SLOTS[key]]:
                    node.attrib.pop(tag('w:' + THEMES[slot]), None)
                    node.set(tag('w:' + slot), value)
            elif key in {'font_size_pt', 'font_size_cs_pt'}:
                value = numeric(value, 1, 200)
                if abs(value * 2 - round(value * 2)) > 1e-8:
                    raise ValueError('Word font sizes must use half-point increments')
                for name in ('sz', 'szCs') if key=='font_size_pt' else ['szCs']:
                    child(rp, 'w:' + name).set(tag('w:val'), str(round(value*2)))
            elif key in {'bold', 'italic'}:
                if type(value) is not bool:
                    raise ValueError(key + ' must be boolean')
                for name in ('b', 'bCs') if key=='bold' else ('i', 'iCs'):
                    child(rp, 'w:' + name).set(tag('w:val'), '1' if value else '0')


def check_contract(path, contract):
    file_hash = digest(Path(path).read_bytes())
    if contract.get("input_sha256") != file_hash:
        raise ValueError("Format contract hash does not match the inspected document")
    parts, _ = load(path)
    rows = formatting_parts(parts)
    covered, exempt, results = set(), set(), []
    groups = contract.get("groups")
    if not isinstance(groups, list) or not groups:
        raise ValueError("Format contract needs groups")
    ids = set()
    for group in groups:
        if group["id"] in ids:
            raise ValueError("Duplicate format group ID")
        ids.add(group["id"])
        basis = group.get("basis", {})
        if basis.get("kind") not in {"official", "user", "preserved", "editorial_choice"} or not basis.get("source"):
            raise ValueError("Format group needs an explicit basis")
        if not group.get("targets"):
            raise ValueError("Format group has no targets")
        expected = group['expected']
        if 'line_spacing_pt' in expected and expected.get('line_rule') not in {'exact', 'atLeast'}:
            raise ValueError('Point spacing contract must distinguish exact from atLeast')
        if 'line_spacing' in expected and ('line_spacing_pt' in expected or expected.get('line_rule', 'auto') != 'auto'):
            raise ValueError('Conflicting line spacing contract')
        required = {'font_size_pt', 'space_before_pt', 'space_after_pt', 'heading_level'}
        if required - set(expected) or not ({'font_name', *FONT_SLOTS} & set(expected)) or not ({'line_spacing', 'line_spacing_pt'} & set(expected)):
            raise ValueError('Every format group must cover font, size, line spacing, paragraph spacing and heading level')
        for target in group["targets"]:
            part = target.get("part", "word/document.xml"); index = target["paragraph"]
            if part not in rows or type(index) is not int or not 0 <= index < len(rows[part]):
                raise ValueError("Invalid format target")
            row = rows[part][index]
            if row["text"] != target["expected_text"]:
                raise ValueError("Stale format target text")
            key = (part, index)
            if key in covered:
                raise ValueError("Overlapping format groups")
            covered.add(key)
            results.append({"group": group["id"], "role": group.get("role"), "part": part,
                            "basis": basis, **match_format(row, expected, target.get('run_exemptions', []))})
    for target in contract.get("exemptions", []):
        part = target.get("part", "word/document.xml"); index = target["paragraph"]
        if part not in rows or type(index) is not int or not 0 <= index < len(rows[part]) or not target.get("reason"):
            raise ValueError("Invalid format exemption")
        if rows[part][index]["text"] != target["expected_text"]:
            raise ValueError("Stale exemption text")
        key = (part, index)
        if key in covered or key in exempt:
            raise ValueError("Duplicate or overlapping exemption")
        exempt.add(key)
    uncovered = [{"part": part, "paragraph": row["index"]} for part, values in rows.items()
                 for row in values if row["text"].strip() and (part, row["index"]) not in covered | exempt]
    passed = all(r["status"] == "pass" for r in results) and not uncovered
    return {"passed": passed, "input_sha256": file_hash, "results": results, "uncovered": uncovered,
            "exemptions": contract.get("exemptions", []), "visual_validation": "not_checked",
            "limitations": ["Resolves declared Word properties; does not prove font availability or rendered glyph choice.",
                            "Conditional table styles and tracked formatting need separate review; equation text uses OMML and is outside text-run checks.",
                            "Paragraph spacing settings do not equal measured inter-paragraph gaps."]}
