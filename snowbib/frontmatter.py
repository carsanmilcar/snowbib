"""Minimal YAML front matter reader.

Deliberately not a YAML parser: it reads the handful of scalar fields snowbib
needs, in the three spellings Obsidian and hand-written notes actually produce.

    title: "Quoted"
    title: 'Single quoted'
    title: Bare, unquoted
    title: >
      folded over
      several lines
"""
import re

_KEY = r"^{key}:[ \t]*(.*)$"
_BLOCK = (">", "|", ">-", "|-", ">+", "|+")


def normalize_newlines(text):
    """CRLF and CR to LF.

    Notes written on Windows arrive with CRLF, which would leave the closing
    front matter marker as "---\r" — something no line-anchored pattern matches.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n")


def split(text):
    """Return the front matter block, or None when the note has none.

    A note must start with a `---` line; anything else is treated as having no
    front matter, rather than scanning the body for things that look like keys.
    """
    text = normalize_newlines(text)
    if not text.startswith("---"):
        return None
    head, _, rest = text.partition("\n")
    if head.strip() != "---" or not rest:
        return None
    end = re.search(r"^(---|\.\.\.)[ \t]*$", rest, re.M)
    return rest[:end.start()] if end else None


def get(fm, key):
    """Read one scalar field. Returns "" when absent or empty."""
    if not fm:
        return ""
    m = re.search(_KEY.format(key=re.escape(key)), fm, re.M)
    if not m:
        return ""
    raw = m.group(1).strip()
    if raw in _BLOCK:
        # Folded or literal block: take the indented lines that follow.
        out = []
        for line in fm[m.end():].split("\n")[1:]:
            if line.strip() and not line[:1].isspace():
                break
            out.append(line.strip())
        return " ".join(x for x in out if x).strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1].strip()
    return raw.split(" #", 1)[0].strip()
