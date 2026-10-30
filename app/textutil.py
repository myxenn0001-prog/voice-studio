"""Split a script into chunks the TTS models handle well."""
import re

_SENT = re.compile(r"(?<=[.!?…।॥؟۔])\s+|(?<=[。！？])\s*")


def split_sentences(paragraph: str) -> list[str]:
    parts = [p.strip() for p in _SENT.split(paragraph) if p.strip()]
    return parts or ([paragraph.strip()] if paragraph.strip() else [])


def _hard_wrap(sentence: str, limit: int) -> list[str]:
    """Split an over-long sentence on commas/semicolons, then on spaces."""
    if len(sentence) <= limit:
        return [sentence]
    out, current = [], ""
    for piece in re.split(r"(?<=[,;:])\s+", sentence):
        if len(current) + len(piece) + 1 <= limit:
            current = f"{current} {piece}".strip()
        else:
            if current:
                out.append(current)
            if len(piece) > limit:
                words, current = piece.split(), ""
                for w in words:
                    if len(current) + len(w) + 1 <= limit:
                        current = f"{current} {w}".strip()
                    else:
                        out.append(current)
                        current = w
            else:
                current = piece
    if current:
        out.append(current)
    return out


def make_chunks(text: str, max_chars: int = 240) -> list[dict]:
    """Return [{'text': str, 'paragraph_end': bool}, ...]."""
    text = text.replace("\r\n", "\n").strip()
    chunks: list[dict] = []
    for para in re.split(r"\n\s*\n+", text):
        para = " ".join(para.split())
        if not para:
            continue
        buf = ""
        para_chunks: list[str] = []
        for sent in split_sentences(para):
            for piece in _hard_wrap(sent, max_chars):
                if buf and len(buf) + len(piece) + 1 > max_chars:
                    para_chunks.append(buf)
                    buf = piece
                else:
                    buf = f"{buf} {piece}".strip()
        if buf:
            para_chunks.append(buf)
        for i, c in enumerate(para_chunks):
            chunks.append({"text": c, "paragraph_end": i == len(para_chunks) - 1})
    return chunks
