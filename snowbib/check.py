"""Filter search candidates against what the vault already knows.

Input: one reference per line (DOI, doi.org URL, OpenAlex W-id, citekey, or a
bare title), via stdin or as arguments.

Verdicts:
  FILED    <citekey> [status]  -> already has a note; do not propose it again
  DROPPED                      -> decided and buried in a previous round
  CITED    <citekey> xN        -> N notes in your vault cite it, but it has no
                                  note: your own corpus already voted for it
  NEW                          -> unknown to the vault

Usage:
  python -m snowbib.check 10.1090/S0273-0979-09-01249-X "Computing Persistent Homology"
  cat candidates.txt | python -m snowbib.check --new-only
"""
import argparse
import json
import os
import re
import sys

from . import config
from .index import norm_doi, norm_title

OPENALEX_RE = re.compile(r"^W\d{6,}$")


def load_index(root=None):
    path = os.path.join(config.tools_dir(root), "seen_index.json")
    if not os.path.exists(path):
        sys.exit(f"snowbib: no index at {path}\nRun: python -m snowbib.index")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def lookup(raw, idx):
    """Classify one candidate. Cheapest and most reliable keys first."""
    q = raw.strip()
    if not q:
        return None
    doi = norm_doi(q)
    if doi in idx["_excluded_dois"]:
        return ("DROPPED", "-", "previous round")
    if doi in idx["by_doi"]:
        return ("FILED", idx["by_doi"][doi], "")
    if doi in idx["ghost_by_doi"]:
        g = idx["ghost_by_doi"][doi]
        return ("CITED", g, f"x{idx['ghosts'].get(g, 0)}")
    if OPENALEX_RE.match(q):
        if q in idx["_excluded_ids"]:
            return ("DROPPED", "-", "previous round")
        if q in idx["by_openalex"]:
            return ("FILED", idx["by_openalex"][q], "")
        g = idx["ghost_by_openalex"].get(q)
        if g:
            return ("CITED", g, f"x{idx['ghosts'].get(g, 0)}")
    if q in idx["notes"]:
        return ("FILED", q, "")
    if q in idx["ghosts"]:
        return ("CITED", q, f"x{idx['ghosts'][q]}")
    t = norm_title(q)
    if t and t in idx["by_title"]:
        return ("FILED", idx["by_title"][t], "")
    if t and t in idx["ghost_by_title"]:
        g = idx["ghost_by_title"][t]
        return ("CITED", g, f"x{idx['ghosts'].get(g, 0)}")
    return ("NEW", "-", "")


def run(candidates, idx, new_only=False, out=sys.stdout):
    known = 0
    for raw in candidates:
        res = lookup(raw, idx)
        if not res:
            continue
        verdict, key, extra = res
        if verdict != "NEW":
            known += 1
            if new_only:
                continue
        status = idx["notes"].get(key, {}).get("status", "")
        left = f"{verdict:10} {key:28} {extra} {status}".rstrip()
        print(f"{left}  <- {raw.strip()[:70]}", file=out)
    return known


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="python -m snowbib.check",
        description="Filter paper candidates against the vault's seen-index.")
    p.add_argument("candidates", nargs="*",
                   help="DOI, doi.org URL, OpenAlex id, citekey or title")
    p.add_argument("--vault", help="vault root (default: $SNOWBIB_VAULT or cwd)")
    p.add_argument("--new-only", action="store_true",
                   help="print only the candidates the vault does not know")
    a = p.parse_args(argv)

    idx = load_index(a.vault)
    idx["_excluded_dois"] = set(idx.get("excluded_dois", []))
    idx["_excluded_ids"] = set(idx.get("excluded_ids", []))
    if not idx.get("notes"):
        print("snowbib: WARNING the index has no notes, so everything will come "
              "back NEW. Did you run python -m snowbib.index on the right vault?",
              file=sys.stderr)

    lines = a.candidates or sys.stdin.read().splitlines()
    known = run(lines, idx, new_only=a.new_only)
    if not a.new_only:
        total = len([x for x in lines if x.strip()])
        print(f"\n# {known} already known out of {total}", file=sys.stderr)


if __name__ == "__main__":
    main()
