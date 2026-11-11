#!/usr/bin/env python3
"""Build a runtime-only skill ZIP; never include tests or generated outputs."""
import argparse
from pathlib import Path
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('skill', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    skill = args.skill.resolve()
    for name in ('SKILL.md', 'LICENSE', 'THIRD_PARTY_LICENSES.txt'):
        if not (skill / name).is_file():
            parser.error(f'Missing runtime file: {name}')
    if args.out.resolve().is_relative_to(skill):
        parser.error('Archive must be outside the skill directory')
    files = []
    for path in sorted(skill.rglob('*')):
        parts = path.relative_to(skill).parts
        if any(part.startswith('.') or part == '__pycache__' for part in parts):
            continue
        if path.is_symlink():
            parser.error('Runtime packages must not contain symlinks')
        if path.is_file():
            if path.suffix in {'.pyc', '.pyo'}:
                continue
            files.append(path)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.out, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, Path(skill.name) / path.relative_to(skill))
    print(f'Created {args.out}: {len(files)} runtime files; {args.out.stat().st_size} bytes')


if __name__ == '__main__':
    main()
