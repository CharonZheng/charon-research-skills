#!/usr/bin/env python3
"""Offline capability probes; runs without third-party Python dependencies."""
import argparse
import importlib
import json
import shutil
import subprocess
import sys

from report_io import json_out


def module_probe(name):
    try:
        module = importlib.import_module(name)
        return {'status': 'pass', 'version': str(getattr(module, '__version__', 'unknown'))}
    except Exception as exc:
        return {'status': 'fail', 'reason': f'{type(exc).__name__}: {exc}'}


def font_probe(family):
    executable = shutil.which('fc-match')
    if not executable:
        return {'family': family, 'status': 'not_checked', 'reason': 'fc-match is unavailable'}
    try:
        result = subprocess.run([executable, '-f', '%{family}\n', '--', family],
                                capture_output=True, text=True, timeout=10, check=True)
        names = [name.strip() for line in result.stdout.splitlines() for name in line.split(',')]
        normal = lambda value: ''.join(c for c in value.casefold() if c.isalnum())
        found = any(normal(family) == normal(name) for name in names)
        return {'family': family, 'status': 'pass' if found else 'needs_confirmation',
                'matched_families': names, 'reason': 'Fontconfig match only; verify the rendered PDF separately'}
    except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
        return {'family': family, 'status': 'not_checked', 'reason': str(exc)}


def inspect_environment(mode='docx', fonts=()):
    if mode not in {'requirements', 'docx', 'pdf', 'render'}:
        raise ValueError('Unknown doctor mode')
    if any(not isinstance(font, str) or not font.strip() for font in fonts):
        raise ValueError('Font families must be nonempty strings')
    python_ok = sys.version_info >= (3, 10)
    checks = {'python': {'status': 'pass' if python_ok else 'fail',
                         'executable': sys.executable, 'version': sys.version.split()[0],
                         'minimum': '3.10'}}
    if mode != 'requirements':
        checks['lxml'] = module_probe('lxml.etree')
    if mode in {'pdf', 'render'}:
        checks['pdfplumber'] = module_probe('pdfplumber')
    tools = {name: shutil.which(name) for name in ('soffice', 'libreoffice', 'pdftoppm', 'fc-match')}
    if mode == 'render':
        checks['renderer'] = {'status': 'pass' if tools['soffice'] or tools['libreoffice'] else 'not_checked',
                              'reason': 'CLI discovery only; Word or host-provided rendering must be verified separately'}
        checks['page_images'] = {'status': 'pass' if tools['pdftoppm'] else 'not_checked',
                                 'reason': 'pdftoppm discovery only; other host tools may supply page images'}
    font_checks = [font_probe(font.strip()) for font in fonts]
    states = [item['status'] for item in checks.values()] + [item['status'] for item in font_checks]
    # Requirements research does not depend on this Python interpreter or DOCX tools.
    if mode == 'requirements':
        states = [item['status'] for item in font_checks]
    status = 'blocked' if 'fail' in states else 'incomplete' if any(s != 'pass' for s in states) else 'ready'
    return {'schema_version': 1, 'mode': mode, 'status': status, 'checks': checks,
            'tools': tools, 'fonts': font_checks,
            'limitations': ['No packages or fonts were installed; no network requests were made.',
                            'Tool discovery and font matching do not prove rendering or visual correctness.',
                            'Official-source browsing and visual inspection depend on the host agent and are not probed.']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('requirements', 'docx', 'pdf', 'render'), default='docx')
    parser.add_argument('--font-family', action='append', default=[])
    parser.add_argument('--out')
    args = parser.parse_args(argv)
    try:
        result = inspect_environment(args.mode, args.font_family)
        if args.out:
            json_out(args.out, result)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return {'ready': 0, 'blocked': 1, 'incomplete': 3}[result['status']]
    except (OSError, ValueError, TypeError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
