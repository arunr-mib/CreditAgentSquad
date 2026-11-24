"""Content-Disposition for a file name a person chose: an ASCII `filename` fallback with nothing that can break out
of the quotes, and the real name in RFC 5987 `filename*`, so a name outside Latin-1 does not break the header."""
import re
from urllib.parse import quote


def content_disposition(kind: str, name: str) -> str:
    """`kind` is "attachment" or "inline"."""
    base = name.replace("\\", "/").rsplit("/", 1)[-1].strip() or "file"
    fallback = re.sub(r'[^A-Za-z0-9 ._()\-]', "_", base.encode("ascii", "replace").decode("ascii")) or "file"
    return f"{kind}; filename=\"{fallback}\"; filename*=UTF-8''{quote(base, safe='')}"
