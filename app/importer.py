"""Pull plain script text out of .txt, .md and .docx files. Standard library only."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

MAX_BYTES = 15 * 1024 * 1024
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class ImportFileError(ValueError):
    pass


def _decode(raw: bytes) -> str:
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def _docx(raw: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            try:
                info = z.getinfo("word/document.xml")
            except KeyError:
                raise ImportFileError("That does not look like a Word (.docx) document.")
            if info.file_size > 60 * 1024 * 1024:
                raise ImportFileError("That document is too large to import.")
            xml = z.read(info)
    except zipfile.BadZipFile:
        raise ImportFileError("That file is not a valid .docx document.")
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        raise ImportFileError("Could not read the text inside that document.")
    paragraphs = []
    for p in root.iter(_W + "p"):
        parts = []
        for node in p.iter():
            if node.tag == _W + "t" and node.text:
                parts.append(node.text)
            elif node.tag == _W + "tab":
                parts.append(" ")
            elif node.tag in (_W + "br", _W + "cr"):
                parts.append("\n")
        text = "".join(parts).strip()
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)  # a blank line between paragraphs gives a longer pause


def extract_text(filename: str, raw: bytes) -> str:
    if len(raw) > MAX_BYTES:
        raise ImportFileError("That file is larger than 15 MB.")
    ext = Path(filename or "").suffix.lower()
    if ext in (".txt", ".md", ".text"):
        text = _decode(raw)
    elif ext == ".docx":
        text = _docx(raw)
    elif ext == ".doc":
        raise ImportFileError("Old .doc files are not supported. In Word choose File > Save As > .docx, then try again.")
    else:
        raise ImportFileError("Use a .txt, .md or .docx file.")
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        raise ImportFileError("No text was found in that file.")
    return text
