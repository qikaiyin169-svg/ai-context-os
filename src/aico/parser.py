"""Conservative structure extraction. No semantic understanding is claimed."""

import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .util import AicoError, digest

MAX_BYTES = 2_000_000
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
EXPLICIT = re.compile(r"^(?:[-*+]\s+|\d+[.)、]\s*|(?:RULE|规则)\s*:\s*)", re.I)


def paragraphs(path):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise AicoError("Source exceeds 2 MB compressed/plain limit")
    if path.suffix.lower() == ".docx":
        with zipfile.ZipFile(path) as archive:
            if len(archive.infolist()) > 1000:
                raise AicoError("DOCX contains too many entries")
            info = archive.getinfo("word/document.xml")
            if info.file_size > MAX_BYTES:
                raise AicoError("DOCX document.xml exceeds 2 MB")
            xml = archive.read(info)
        if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper() or b"\x00" in xml:
            raise AicoError("DTD/entities/UTF-16 XML are not supported")
        root = ET.fromstring(xml)
        for index, para in enumerate(root.findall(".//w:p", NS), 1):
            text = "".join(n.text or "" for n in para.findall(".//w:t", NS)).strip()
            style = para.find("w:pPr/w:pStyle", NS)
            heading = (
                style is not None
                and "heading" in style.get("{" + NS["w"] + "}val", "").lower()
            )
            numbered = para.find("w:pPr/w:numPr", NS) is not None
            yield index, text, heading, numbered
    elif path.suffix.lower() in (".md", ".markdown", ".txt"):
        for index, text in enumerate(
            path.read_text(encoding="utf-8-sig").splitlines(), 1
        ):
            yield index, text.strip(), text.lstrip().startswith("#"), False
    else:
        raise AicoError("Supported sources: DOCX, Markdown, UTF-8 TXT")


def extract(path, include_prose=False):
    """Return pending candidates with filename+hash provenance, never the raw file."""
    candidates = []
    section = ""
    fenced = False
    if Path(path).stat().st_size > MAX_BYTES:
        raise AicoError("Source exceeds 2 MB compressed/plain limit")
    source_hash = digest(Path(path).read_bytes())
    for index, text, heading, numbered in paragraphs(path):
        if text.startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if fenced or not text:
            continue
        if heading:
            section = text.lstrip("# ")[:200]
            continue
        match = EXPLICIT.match(text)
        if match or numbered or include_prose:
            value = text[match.end() :] if match else text
            if not value or len(value) > 8000:
                continue
            candidates.append(
                {
                    "text": value,
                    "source": {
                        "name": Path(path).name,
                        "sha256": source_hash,
                        "position": index,
                        "section": section,
                    },
                }
            )
    return candidates
