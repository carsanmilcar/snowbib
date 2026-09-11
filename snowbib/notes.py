"""Turn OpenAlex works into vault notes, and name them.

A citekey is the vault's primary key, so it has to be stable and readable:
`lastname + year + first meaningful title word`, the convention BibTeX users
already expect.
"""
import os
import re
import unicodedata

from . import openalex

STOPWORDS = {"the", "a", "an", "on", "of", "in", "for", "and", "to", "with",
             "from", "at", "by", "as", "is", "are"}


def _ascii(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def citekey(meta, taken=None):
    """lastname+year+word, with a letter suffix when two papers collide."""
    first = (meta.get("first") or "").split()
    last = _ascii(first[-1]) if first else "anon"
    year = meta.get("year") or "nd"
    words = [w for w in re.split(r"\W+", meta.get("title") or "")
             if _ascii(w) and _ascii(w) not in STOPWORDS]
    base = f"{last or 'anon'}{year}{_ascii(words[0]) if words else 'untitled'}"
    if taken is None or base not in taken:
        return base
    for i in range(ord("a"), ord("z") + 1):
        candidate = f"{base}{chr(i)}"
        if candidate not in taken:
            return candidate
    return f"{base}{len(taken)}"


def _yaml_list(values):
    return "[" + ", ".join('"' + str(v).replace('"', "'") + '"' for v in values) + "]"


def from_work(work, profile=None, extra_fields=None):
    """Render a note (front matter + body) for one OpenAlex work."""
    authors = [a["author"]["display_name"] for a in (work.get("authorships") or [])]
    shown = ", ".join(authors[:8]) + (f", et al. ({len(authors)} authors)"
                                      if len(authors) > 8 else "")
    loc = (work.get("primary_location") or {}).get("source") or {}
    topics = [t["display_name"] for t in (work.get("topics") or [])[:3]]
    oa = work.get("open_access") or {}
    doi = (work.get("doi") or "").replace("https://doi.org/", "")
    title = (work.get("display_name") or work.get("title") or "").replace('"', "'")

    fields = [
        ("type", "paper"),
        ("status", "to_read"),
        ("title", f'"{title}"'),
        ("authors", f'"{shown}"'),
        ("year", work.get("publication_year") or ""),
        ("venue", f'"{(loc.get("display_name") or "").replace(chr(34), chr(39))}"'),
        ("doi", f'"{doi}"'),
        ("url", f'"https://doi.org/{doi}"' if doi else '""'),
        ("openalex_id", f'"{openalex.short_id(work.get("id"))}"'),
        ("cited_by", work.get("cited_by_count", 0)),
        ("oa_pdf", f'"{oa.get("oa_url") or ""}"'),
        ("topics", _yaml_list(topics)),
    ]
    for key, default in (extra_fields or {}).items():
        fields.append((key, _yaml_list(default) if isinstance(default, list)
                       else f'"{default}"'))
    if profile:
        fields.append(("profile", profile))

    fm = "\n".join(f"{k}: {v}" for k, v in fields)
    body = (f"# {title}\n\n"
            "## Summary\n_Not screened yet._\n\n"
            "## Relevance\n_Not screened yet._\n")
    return f"---\n{fm}\n---\n\n{body}"


def write(papers_dir, key, text, overwrite=False):
    path = os.path.join(papers_dir, key + ".md")
    if os.path.exists(path) and not overwrite:
        return False
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return True
