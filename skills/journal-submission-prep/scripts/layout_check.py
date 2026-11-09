"""Conservative rendered-PDF triage; never substitutes for page-by-page viewing."""
import re


def check_pdf(path, font_families=()):
    if any(not isinstance(f, str) or not f.strip() for f in font_families):
        raise ValueError('Expected font families must be nonempty strings')
    try:
        import pdfplumber
    except ImportError as exc:
        raise ValueError('PDF triage requires pdfplumber; visual validation remains incomplete') from exc
    findings, fonts = [], set()
    with pdfplumber.open(path) as pdf:
        for number, page in enumerate(pdf.pages, 1):
            fonts.update(c.get('fontname', '') for c in page.chars)
            outside = [c for c in page.chars if c['x0'] < -1 or c['x1'] > page.width + 1 or c['top'] < -1 or c['bottom'] > page.height + 1]
            if outside:
                findings.append({'page': number, 'kind': 'text_outside_page', 'count': len(outside), 'status': 'needs_confirmation'})
            bad = [c for c in page.chars if '\ufffd' in c.get('text', '') or '\x00' in c.get('text', '')]
            if bad:
                findings.append({'page': number, 'kind': 'replacement_character', 'count': len(bad), 'status': 'needs_confirmation'})
            if not page.chars and not page.images and not page.curves and not page.rects and not page.lines:
                findings.append({'page': number, 'kind': 'blank_page_candidate', 'status': 'needs_confirmation'})
        count = len(pdf.pages)
    def normal(value):
        return ''.join(c for c in re.sub(r'^[A-Z]{6}\+', '', value).casefold() if c.isalnum())
    missing = [family for family in font_families if not any(normal(family) in normal(font) for font in fonts)]
    findings.extend({'kind': 'expected_font_absent', 'family': f, 'status': 'needs_confirmation'} for f in missing)
    return {'pages': count, 'fonts': sorted(fonts), 'findings': findings,
            'automated_triage_clear': not findings, 'visual_validation': 'not_checked',
            'limitations': ['No automated check can establish absence of overlap, clipped equations, missing glyph outlines or bad page breaks.',
                            'PDF font-name presence does not prove every glyph uses the intended font; inspect pages and substitutions.']}
