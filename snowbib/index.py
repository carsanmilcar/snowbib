"""Build the vault's "already seen" index, used to filter search candidates.

Two levels of knowledge:
  FILED  -> a note exists in papers/
  CITED  -> it appears in the citation graph without a note of its own

Output: <vault>/.snowbib/seen_index.json
Usage:  python -m snowbib.index [--vault PATH] [--recursive]
"""
import argparse
import collections
import glob
import json
import os
import re
import sys
import unicodedata

from . import config, frontmatter

# Wikilink prefixes that are not papers. Obsidian vaults often use "MOC-" for
# Maps of Content; add your own with --ignore-prefix.
DEFAULT_IGNORED = ("MOC-",)

LINK_RE = re.compile(r"\[\[([^\]|#]+)")


def norm_title(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def norm_doi(s):
    s = (s or "").strip().strip('"').strip("'").lower()
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", s).strip()


def read_note(path):
    """Read a note as UTF-8, warning (not silently mangling) on bad bytes.

    Line endings are normalised: notes written on Windows arrive with CRLF and
    the closing "---" would otherwise be "---" + CR, which no line-anchored
    pattern matches.
    """
    with open(path, "rb") as fh:
        raw = fh.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        print(f"snowbib: {path} is not valid UTF-8; decoded with replacements, "
              f"its title may not match. Re-save it as UTF-8.", file=sys.stderr)
        text = raw.decode("utf-8", errors="replace")
    return frontmatter.normalize_newlines(text)


def load_json(tools, name):
    path = os.path.join(tools, name)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        print(f"snowbib: ignoring {path}: {exc}", file=sys.stderr)
        return {}


def build(root=None, recursive=False, ignored=DEFAULT_IGNORED, quiet=False):
    papers, tools = config.papers_dir(root), config.tools_dir(root)
    if not os.path.isdir(papers):
        sys.exit(f"snowbib: no papers directory at {papers}\n"
                 f"Point at your vault with --vault PATH or {config.ENV_VAULT}, "
                 f"and make sure it contains a papers/ folder.")

    pattern = os.path.join(glob.escape(papers), "**", "*.md") if recursive \
        else os.path.join(glob.escape(papers), "*.md")
    paths = sorted(glob.glob(pattern, recursive=recursive))

    by_doi, by_oa, by_title, notes = {}, {}, {}, {}
    cited = collections.Counter()
    skipped = []

    for path in paths:
        key = os.path.splitext(os.path.basename(path))[0]
        text = read_note(path)
        fm = frontmatter.split(text)
        if fm is None:
            skipped.append(os.path.basename(path))
        title = frontmatter.get(fm, "title")
        doi = norm_doi(frontmatter.get(fm, "doi"))
        oa = frontmatter.get(fm, "openalex_id")
        oa = oa if re.fullmatch(r"W\d+", oa or "") else ""
        notes[key] = {"title": title, "doi": doi, "openalex_id": oa,
                      "status": frontmatter.get(fm, "status")}
        if doi:
            by_doi[doi] = key
        if oa:
            by_oa[oa] = key
        if title:
            by_title[norm_title(title)] = key
        # Count NOTES that cite something, not how many times each note says it.
        links = {m.strip() for m in LINK_RE.findall(text)}
        for link in links:
            if link and link != key and not link.startswith(tuple(ignored)):
                cited[link] += 1

    ghosts = {k: n for k, n in cited.items() if k not in notes}

    key2oa = load_json(tools, "citekey_openalex_map.json")
    ghost_meta = load_json(tools, "ghost_meta.json")
    oa2ghost = {oa: k for k, oa in key2oa.items() if k in ghosts}

    # Ghosts must be findable by DOI and title too: a web search returns those,
    # never an OpenAlex id.
    g_doi, g_title = {}, {}
    for wid, meta in ghost_meta.items():
        k = oa2ghost.get(wid)
        if not k or not isinstance(meta, dict):
            continue
        if norm_doi(meta.get("doi")):
            g_doi[norm_doi(meta["doi"])] = k
        if norm_title(meta.get("title")):
            g_title[norm_title(meta["title"])] = k

    excluded = load_json(tools, "excluded.json")
    out = {"notes": notes, "by_doi": by_doi, "by_openalex": by_oa,
           "by_title": by_title, "ghosts": ghosts, "ghost_by_openalex": oa2ghost,
           "ghost_by_doi": g_doi, "ghost_by_title": g_title,
           "excluded_ids": sorted(excluded.get("ids", [])),
           "excluded_dois": sorted(norm_doi(x) for x in excluded.get("dois", []))}

    os.makedirs(tools, exist_ok=True)
    dst = os.path.join(tools, "seen_index.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False)

    if not quiet:
        print(f"notes={len(notes)} doi={len(by_doi)} openalex={len(by_oa)} "
              f"ghosts={len(ghosts)} (doi={len(g_doi)} title={len(g_title)}) "
              f"excluded={len(out['excluded_ids'])}+{len(out['excluded_dois'])} -> {dst}")
        if skipped:
            print(f"snowbib: {len(skipped)} note(s) have no YAML front matter and were "
                  f"indexed by filename only: {', '.join(skipped[:5])}"
                  f"{' ...' if len(skipped) > 5 else ''}", file=sys.stderr)
        if not notes:
            print(f"snowbib: WARNING {papers} contains no .md notes, so every "
                  f"candidate will come back NEW."
                  f"{' Try --recursive if your notes live in subfolders.' if not recursive else ''}",
                  file=sys.stderr)
    return out


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m snowbib.index",
                                description="Build the vault's seen-index.")
    p.add_argument("vault", nargs="?", help="vault root (default: $SNOWBIB_VAULT or cwd)")
    p.add_argument("--vault", dest="vault_opt", help="same, as an option")
    p.add_argument("--recursive", action="store_true", help="also index papers/**/ subfolders")
    p.add_argument("--ignore-prefix", action="append", default=[],
                   help="wikilink prefix that is not a paper (default: MOC-)")
    p.add_argument("--quiet", action="store_true")
    a = p.parse_args(argv)
    build(a.vault_opt or a.vault, recursive=a.recursive,
          ignored=tuple(a.ignore_prefix) or DEFAULT_IGNORED, quiet=a.quiet)


if __name__ == "__main__":
    main()
