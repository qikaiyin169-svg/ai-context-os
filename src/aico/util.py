"""Small bounded, private, atomic filesystem helpers."""

import hashlib
import json
import os
import tempfile
from pathlib import Path


class AicoError(Exception):
    """Expected user-facing failure."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(data):
    return (
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def no_links(path):
    path = Path(path).absolute()
    for node in (path, *path.parents):
        if node.is_symlink():
            raise AicoError("Refusing symlink path: " + str(node))
    return path


def private_dir(path):
    path = no_links(path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def atomic_write(path, data, mode=0o600):
    path = no_links(path)
    private_dir(path.parent)
    fd, tmp = tempfile.mkstemp(prefix=".aico-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def read_json(path):
    path = Path(path)
    if path.stat().st_size > 8_000_000:
        raise AicoError("JSON file exceeds 8 MB")
    return json.loads(path.read_text(encoding="utf-8"))
