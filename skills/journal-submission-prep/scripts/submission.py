#!/usr/bin/env python3
"""Offline submission helpers. Policy retrieval and semantic edits belong to the agent."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
import re
import sys
import zipfile

from report_io import available, json_out, publish, read_json

# Keep diagnostics available even when this interpreter cannot load DOCX dependencies.
if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] in {'doctor', 'readiness'}:
    if sys.argv[1] == 'doctor':
        from doctor import main as entry
    else:
        from readiness import main as entry
    sys.exit(entry(sys.argv[2:]))

if sys.version_info < (3, 10):
    raise SystemExit('Python 3.10+ is required. Run scripts/doctor.py with an available interpreter to inspect capabilities.')

try:
    from lxml import etree as E
    from lxml.etree import XMLSyntaxError
except (ImportError, OSError):
    raise SystemExit('This interpreter cannot load lxml.etree. Run scripts/doctor.py; select an existing Python 3.10+ environment with working lxml.')

from docx_tools import NS, apply_operations, audit, digest, load, parse, tag, verify, write_docx
from formatting import check_contract, formatting_parts, match_format, same, story_part
from workflow import consolidate, compare_profiles

CHECKS = {"required_section", "forbidden_section", "section_order", "max_heading_level",
          "max_heading_characters", "word_limit", "display_limit", "manual"}


def profile(path):
    data = read_json(path)
    for key in ("journal", "article_type", "stage", "checked_on", "sources", "rules"):
        if key not in data:
            raise ValueError(f"Profile missing {key}")
    for key in ("journal", "article_type"):
        if not isinstance(data[key], str) or not data[key].strip():
            raise ValueError(f"Profile {key} must be nonempty")
    date.fromisoformat(data["checked_on"])
    if data["stage"] not in ("initial", "revision", "accepted"):
        raise ValueError("stage must be initial, revision, or accepted")
    if not isinstance(data["sources"], list) or not isinstance(data["rules"], list) or not data["sources"] or not data["rules"]:
        raise ValueError("sources and rules must be nonempty lists")
    sources = {}
    for source in data["sources"]:
        if not isinstance(source, dict):
            raise ValueError("Each source must be an object")
        if source["id"] in sources:
            raise ValueError("Duplicate source ID")
        if source["kind"] not in ("official", "editor_current", "historical", "user"):
            raise ValueError("Invalid source kind")
        if not source.get("locator") or not source.get("evidence"):
            raise ValueError("Source needs locator and evidence")
        date.fromisoformat(source["checked_on"])
        sources[source["id"]] = source
    ids = set()
    for rule in data["rules"]:
        if not isinstance(rule, dict):
            raise ValueError("Each rule must be an object")
        for key in ("id", "description", "mandatory", "applicability", "source_ids", "check"):
            if key not in rule:
                raise ValueError(f"Rule missing {key}")
        if rule["id"] in ids:
            raise ValueError("Duplicate rule ID")
        ids.add(rule["id"])
        if type(rule["mandatory"]) is not bool:
            raise ValueError("mandatory must be boolean")
        if rule["applicability"] not in ("applicable", "not_applicable", "unknown"):
            raise ValueError("Invalid applicability")
        if rule["applicability"] != "applicable" and not rule.get("applicability_reason"):
            raise ValueError("Non-applicable or unknown rule needs a reason")
        if not isinstance(rule["source_ids"], list) or not rule["source_ids"] or any(s not in sources for s in rule["source_ids"]):
            raise ValueError("Rule must reference known sources")
        check = rule["check"]
        if not isinstance(check, dict):
            raise ValueError("Rule check must be an object")
        if check["type"] not in CHECKS:
            raise ValueError(f"Unsupported check: {check['type']}")
        kind = check["type"]
        if kind in ("required_section", "forbidden_section", "word_limit") and not isinstance(check.get("section"), str):
            raise ValueError("Check needs section name")
        if kind in ("max_heading_level", "max_heading_characters", "word_limit", "display_limit"):
            if type(check.get("max")) is not int or check["max"] < 0:
                raise ValueError("Check max must be a nonnegative integer")
        if kind == "section_order" and (not isinstance(check.get("sections"), list) or not check["sections"] or any(not isinstance(n, str) for n in check["sections"])):
            raise ValueError("section_order needs section names")
        if kind == "word_limit" and check.get("count_mode", "whitespace") != "whitespace":
            raise ValueError("Only whitespace word count is supported")
        if rule.get("resolution", "resolved") not in ("resolved", "unresolved"):
            raise ValueError("Invalid resolution")
        if rule.get("conflict_group") and rule.get("resolution") == "resolved" and not rule.get("resolution_note"):
            raise ValueError("Resolved conflict needs resolution_note")
    unresolved_groups = {r["conflict_group"] for r in data["rules"] if r.get("conflict_group")
                         and (r.get("resolution") != "resolved" or not r.get("resolution_note"))}
    for rule in data["rules"]:
        if rule.get("conflict_group") in unresolved_groups:
            rule["resolution"] = "unresolved"
    return data, sources


def gate(rule, sources):
    if rule["applicability"] == "not_applicable":
        return "not_applicable", rule["applicability_reason"]
    if rule["applicability"] == "unknown":
        return "needs_confirmation", rule["applicability_reason"]
    if rule.get("resolution") == "unresolved" or (rule.get("conflict_group") and not rule.get("resolution_note")):
        return "needs_confirmation", "Conflicting requirements have not been resolved"
    if all(sources[s]["kind"] == "historical" for s in rule["source_ids"]):
        return "needs_confirmation", "Historical sources alone do not establish current applicability"
    return None, None


def section_name(value):
    return re.sub(r"^\s*\d+(?:\.\d+)*[.\s]+", "", value).strip().casefold()


def evaluate(rule, report):
    check = rule["check"]; kind = check["type"]
    paras = report["paragraphs"]
    headings = [p for p in paras if p["heading_level"] and not p["in_table"]]
    names = [section_name(p["text"]) for p in headings]
    target = section_name(check.get("section", ""))
    if kind == "manual":
        return "not_checked", "Requires semantic, factual, file or visual review"
    if kind == "display_limit":
        c = report["caption_candidates"]
        count = sum(len({i["number"] for i in c[k]}) for k in ("figures", "tables"))
        return "needs_confirmation", {"unique_main_caption_candidates": count, "max": check["max"], "over_limit": count > check["max"], "reason": "Caption candidates are not a verified display-item inventory"}
    if not headings:
        return "not_checked", "No reliably styled headings detected"
    if kind in ("required_section", "forbidden_section"):
        found = target in names
        ok = found if kind == "required_section" else not found
        return ("pass" if ok else "fail"), {"section": target, "found_in_styled_headings": found}
    if kind == "section_order":
        expected = [section_name(n) for n in check["sections"]]
        if any(n not in names for n in expected) or any(names.count(n) != 1 for n in expected):
            return "needs_confirmation", "Expected section missing or repeated; inspect structure"
        positions = [names.index(n) for n in expected]
        return ("pass" if positions == sorted(positions) else "fail"), {"order": names}
    if kind == "max_heading_level":
        bad = [p["index"] for p in headings if p["heading_level"] > check["max"]]
        return ("fail" if bad else "pass"), {"paragraphs_exceeding_limit": bad}
    if kind == "max_heading_characters":
        scope = section_name(check["within_section"]) if check.get("within_section") else None
        selected, active = [], scope is None
        found = scope is None
        boundary = None
        for p in headings:
            if scope and section_name(p["text"]) == scope:
                active = True; found = True; boundary = p["heading_level"]; continue
            if scope and active and p["heading_level"] <= boundary:
                active = False
            if active:
                selected.append(p)
        if not found:
            return "not_checked", "Requested heading scope not found"
        bad = [p["index"] for p in selected if len(p["text"]) > check["max"]]
        return ("fail" if bad else "pass"), {"paragraphs_exceeding_limit": bad, "count_includes_spaces_and_numbering": True}
    if kind == "word_limit":
        matches = [p for p in headings if section_name(p["text"]) == target]
        if len(matches) != 1:
            return "not_checked", "Section boundary missing or ambiguous"
        start = matches[0]
        end = next((p["index"] for p in headings if p["index"] > start["index"] and p["heading_level"] <= start["heading_level"]), len(paras))
        value = sum(len(p["text"].split()) for p in paras if start["index"] < p["index"] < end)
        return ("pass" if value <= check["max"] else "fail"), {"words": value, "method": "whitespace; includes all content within detected section"}
    raise ValueError(f"Unsupported check: {kind}")


def check_document(path, data, sources):
    report = audit(path); results = []
    revisions = report["objects"]["insertions"] + report["objects"]["deletions"]
    for rule in data["rules"]:
        status, detail = gate(rule, sources)
        if status is None:
            status, detail = evaluate(rule, report)
            if revisions and status == "pass":
                status = "needs_confirmation"
                detail = {"reason": "Unaccepted revisions may affect the reading view", "finding": detail}
        results.append({"id": rule["id"], "description": rule["description"], "mandatory": rule["mandatory"],
                        "status": status, "detail": detail, "source_ids": rule["source_ids"]})
    required = [r['status'] for r in results if r['mandatory']]
    status = 'fail' if 'fail' in required else 'pass' if all(s in {'pass', 'not_applicable'} for s in required) else 'incomplete'
    return {"journal": data["journal"], "article_type": data["article_type"], "stage": data["stage"],
            "profile_checked_on": data["checked_on"], "manuscript_sha256": report["sha256"],
            "results": results, "summary": dict(Counter(r["status"] for r in results)),
            "required_checks_status": status,
            "limitations": report["limitations"] + ["Profile sources were not fetched or verified by this offline script."]}


def format_document(args):
    available(args.out, (args.input, args.profile, args.plan))
    available(args.log, (args.input, args.profile, args.plan, args.out))
    if Path(args.out).resolve() == Path(args.log).resolve():
        raise ValueError("DOCX and log outputs must differ")
    data, sources = profile(args.profile); plan = read_json(args.plan)
    source_hash = digest(Path(args.input).read_bytes())
    if plan.get("input_sha256") != source_hash:
        raise ValueError("Plan input hash does not match manuscript")
    operations = plan["operations"]
    if not isinstance(operations, list) or not operations or any(not isinstance(op, dict) for op in operations):
        raise ValueError("Plan operations must be a nonempty list of objects")
    rules = {r["id"]: r for r in data["rules"]}
    for op in operations:
        rule = rules.get(op.get("rule_id"))
        if rule is None or gate(rule, sources)[0] is not None:
            raise ValueError("Operation needs an applicable, resolved rule with current evidence")
    parts, root = load(args.input)
    before_rows = formatting_parts(parts)
    updates, roots = {}, {}
    styles = parse(parts['word/styles.xml']) if 'word/styles.xml' in parts else None
    for op in operations:
        part = op.get('part', 'word/document.xml')
        if not story_part(part) or part not in parts:
            raise ValueError('Operation part must be an existing document, header, footer or note story')
        if part not in roots:
            roots[part] = parse(parts[part])
        if part != 'word/document.xml' and op['kind'] == 'page_margins':
            raise ValueError('Page margins belong to document sections')
        apply_operations(roots[part], [op], styles)
    for part, tree in roots.items():
        updates[part] = E.tostring(tree, xml_declaration=True, encoding='UTF-8', standalone=True)
    changes = []
    for op in operations:
        part = op.get('part', 'word/document.xml')
        entry = {'operation': op, 'source_ids': rules[op['rule_id']]['source_ids']}
        if op['kind'] == 'paragraph_format':
            entry['before'] = before_rows[part][op['paragraph']]
        changes.append(entry)
    log = {"input_sha256": source_hash, "operations": operations,
           "source_ids": sorted({s for op in operations for s in rules[op["rule_id"]]["source_ids"]}),
           "changes": changes,
           "visual_validation": "not_checked"}
    def readback(candidate_parts):
        rows = formatting_parts(candidate_parts)
        results = []
        for op in operations:
            part = op.get('part', 'word/document.xml')
            if op['kind'] == 'paragraph_format':
                row = rows[part][op['paragraph']]
                result = match_format(row, op['format'], op.get('run_exemptions', []))
                result['actual'] = row
            else:
                tree = parse(candidate_parts[part]); section = tree.findall('.//w:sectPr', NS)[op['section']]
                margin = section.find('w:pgMar', NS)
                actual = {k: float(margin.get(tag('w:' + k))) * 25.4 / 1440 if margin is not None and margin.get(tag('w:' + k)) is not None else None for k in op['margins_mm']}
                result = {'status': 'pass' if all(same(actual[k], v, k + '_mm') for k, v in op['margins_mm'].items()) else 'fail', 'actual': actual}
            results.append({'part': part, 'rule_id': op['rule_id'], **result})
        return results
    predicted = readback({**parts, **updates})
    if any(r['status'] != 'pass' for r in predicted):
        raise ValueError('Planned format is not verifiable; unresolved inheritance, revisions, spacing or text scope needs review')
    for change, result in zip(changes, predicted):
        change['predicted_after'] = result['actual']
    if args.dry_run:
        print(json.dumps({"dry_run": True, **log}, ensure_ascii=False, indent=2))
        return 0

    def writer(tmp):
        write_docx(args.input, tmp, root, updates)
        result = verify(args.input, tmp)
        if not result["passed"] or digest(Path(args.input).read_bytes()) != source_hash:
            raise ValueError("Integrity validation failed or source changed during operation")
        log["integrity"] = result
        actual_parts, _ = load(tmp)
        log['readback'] = readback(actual_parts)
        if any(r['status'] != 'pass' for r in log['readback']):
            raise ValueError('Saved DOCX formatting does not match the plan; output rejected')
    publish(args.out, writer)
    json_out(args.log, log)
    print(f"Created {args.out}; operation readback passed; full format contract and visual validation remain separate")
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in {'doctor', 'readiness'}:
        if argv[0] == 'doctor':
            from doctor import main as entry
        else:
            from readiness import main as entry
        return entry(argv[1:])
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser('doctor', help='Inspect Python, dependencies, rendering tools and fonts', add_help=False)
    sub.add_parser('readiness', help='Aggregate hash-bound delivery evidence', add_help=False)
    for name in ("audit", "check", "format"):
        p = sub.add_parser(name); p.add_argument("input", type=Path); p.add_argument("--out", type=Path, required=True)
        if name in ("check", "format"):
            p.add_argument("--profile", type=Path, required=True)
        if name == "format":
            p.add_argument("--plan", type=Path, required=True); p.add_argument("--log", type=Path, required=True)
            p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("verify"); p.add_argument("before", type=Path); p.add_argument("after", type=Path); p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("manifest"); p.add_argument("directory", type=Path); p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser('format-audit'); p.add_argument('input', type=Path); p.add_argument('--contract', type=Path, required=True); p.add_argument('--out', type=Path, required=True)
    p = sub.add_parser('facts'); p.add_argument('--observations', type=Path, required=True); p.add_argument('--existing', type=Path); p.add_argument('--out', type=Path, required=True); p.add_argument('--questions', type=Path, required=True)
    p = sub.add_parser('compare-profiles'); p.add_argument('old', type=Path); p.add_argument('new', type=Path); p.add_argument('--out', type=Path, required=True)
    p = sub.add_parser('layout'); p.add_argument('input', type=Path); p.add_argument('--font-family', action='append', default=[]); p.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "format":
            return format_document(args)
        if args.command == 'facts':
            available(args.out, [args.observations, *([args.existing] if args.existing else [])])
            available(args.questions, [args.observations, args.out, *([args.existing] if args.existing else [])])
            registry, questions = consolidate(read_json(args.observations), read_json(args.existing) if args.existing else None)
            json_out(args.out, registry); json_out(args.questions, questions)
            print(f'Created {args.out} and {args.questions}')
            return 0
        inputs = [v for k, v in vars(args).items() if isinstance(v, Path) and k != "out"]
        available(args.out, inputs)
        code = 0
        if args.command == "audit":
            result = audit(args.input)
        elif args.command == "check":
            data, sources = profile(args.profile)
            result = check_document(args.input, data, sources)
            code = {'pass': 0, 'fail': 1, 'incomplete': 3}[result['required_checks_status']]
        elif args.command == "verify":
            result = verify(args.before, args.after); code = 0 if result["passed"] else 1
        elif args.command == 'format-audit':
            result = check_contract(args.input, read_json(args.contract)); code = 0 if result['passed'] else 1
        elif args.command == 'compare-profiles':
            old, _ = profile(args.old); new, _ = profile(args.new)
            result = compare_profiles(old, new)
        elif args.command == 'layout':
            from layout_check import check_pdf
            result = check_pdf(args.input, args.font_family); code = 0 if result['automated_triage_clear'] else 1
            result['input_sha256'] = digest(args.input.read_bytes())
        else:
            directory = args.directory.resolve()
            if args.directory.is_symlink() or not directory.is_dir() or Path(args.out).resolve().is_relative_to(directory):
                raise ValueError("Manifest output must be outside an existing staging directory")
            files = []
            for p in sorted(directory.rglob("*")):
                if p.is_symlink():
                    raise ValueError("Staging directory must not contain symlinks")
                if p.is_file():
                    files.append({"path": p.relative_to(directory).as_posix(), "bytes": p.stat().st_size, "sha256": digest(p.read_bytes())})
            result = {"files": files, "completeness": "not_checked"}
        json_out(args.out, result)
        print(f"Created {args.out}")
        return code
    except (ValueError, KeyError, TypeError, OSError, ArithmeticError, zipfile.BadZipFile, XMLSyntaxError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
