"""Standard-library report I/O; preserve inputs and existing outputs."""
import hashlib
import json
import os
from pathlib import Path
import tempfile


def digest_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError('JSON root must be an object')
    return data


def available(path, inputs=()):
    path = Path(path)
    if path.is_symlink() or path.exists():
        raise ValueError(f'Output already exists: {path}')
    if path.resolve() in {Path(item).resolve() for item in inputs}:
        raise ValueError('Output aliases an input')
    return path


def publish(path, writer):
    path = available(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.submission-', dir=path.parent)
    os.close(fd)
    try:
        writer(Path(name))
        os.link(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def json_out(path, data):
    publish(path, lambda target: target.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'))
