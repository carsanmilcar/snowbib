"""Populate a vault from OpenAlex: python -m snowbib.discover --query "your topic"

Metadata only. Nothing here reads a paper or calls a language model: it fetches
what OpenAlex knows and writes one note per work. Screening comes later, on the
subset you choose (see python -m snowbib.screen).
"""
import argparse
import os
import sys

from . import config, index, notes, openalex, profile


def build_filter(queries, field=None, min_year=None, min_citations=None):
    parts = []
    if queries:
        parts.append("title_and_abstract.search:" + " OR ".join(queries)
                     if len(queries) > 1 else f"title_and_abstract.search:{queries[0]}")
    if field:
        parts.append(f"primary_topic.field.id:{field}")
    if min_year:
        parts.append(f"publication_year:>{int(min_year) - 1}")
    if min_citations:
        parts.append(f"cited_by_count:>{int(min_citations) - 1}")
    return ",".join(parts)


def run(root=None, queries=None, prof=None, limit=None, min_year=None,
        min_citations=None, dry_run=False):
    root = config.vault_root(root)
    papers, tools = config.papers_dir(root), config.tools_dir(root)
    if not os.path.isdir(papers):
        sys.exit(f"snowbib: no vault at {root}. Create one first:\n"
                 f"  python -m snowbib.init --vault {root}")

    prof = prof or {}
    oa = prof.get("openalex", {})
    queries = queries or oa.get("queries") or []
    if not queries:
        sys.exit("snowbib: nothing to search for. Pass --query, or use a profile "
                 "whose openalex.queries is filled in.")

    filters = build_filter(queries, oa.get("field"),
                           min_year or oa.get("min_year"), min_citations)
    total = openalex.count(filters)
    print(f"query   : {' OR '.join(queries)}")
    print(f"filter  : {filters}")
    print(f"matches : {total:,}" + (f"  (fetching the first {limit:,})" if limit and limit < total else ""))

    if dry_run:
        print("\nDry run: nothing written. Drop --dry-run to fetch, or narrow the "
              "query first — a vault of tens of thousands of notes is hard to read.")
        return {"matched": total, "written": 0, "skipped": 0}

    if total > 20000 and not limit:
        sys.exit(f"snowbib: {total:,} matches is too broad to write as notes.\n"
                 f"Narrow the query, add --min-citations, or set --limit if you "
                 f"really want the first N.")

    existing = set()
    if os.path.isdir(papers):
        existing = {os.path.splitext(f)[0] for f in os.listdir(papers) if f.endswith(".md")}
    seen_dois = {}
    idx_path = os.path.join(tools, "seen_index.json")
    if os.path.exists(idx_path):
        seen_dois = index.build(root, quiet=True)["by_doi"]

    written = skipped = 0
    for work in openalex.works(filters, limit=limit, tools=tools):
        doi = (work.get("doi") or "").replace("https://doi.org/", "").lower()
        if doi and doi in seen_dois:
            skipped += 1
            continue
        authors = work.get("authorships") or []
        meta = {"title": work.get("display_name") or "",
                "year": work.get("publication_year"),
                "first": authors[0]["author"]["display_name"] if authors else ""}
        key = notes.citekey(meta, existing)
        text = notes.from_work(work, profile=prof.get("name"),
                               extra_fields=prof.get("fields"))
        if notes.write(papers, key, text):
            existing.add(key)
            written += 1
        else:
            skipped += 1
        if written and written % 100 == 0:
            print(f"  ... {written} notes", flush=True)

    print(f"\nwritten={written} skipped={skipped} (already in the vault)")
    print(f"Next:\n  python -m snowbib.cites --vault {root}   # reconstruct the citation graph\n"
          f"  python -m snowbib.index --vault {root}   # rebuild the seen-index")
    return {"matched": total, "written": written, "skipped": skipped}


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="python -m snowbib.discover",
        description="Populate a vault from OpenAlex (metadata only).")
    p.add_argument("--vault", help="vault root (default: $SNOWBIB_VAULT or cwd)")
    p.add_argument("--query", action="append", default=[],
                   help="search phrase; repeat for several (they are OR-ed)")
    p.add_argument("--profile", help="field profile providing queries and extra fields")
    p.add_argument("--limit", type=int, help="stop after N works")
    p.add_argument("--min-year", type=int)
    p.add_argument("--min-citations", type=int,
                   help="skip works cited fewer than N times: a blunt but effective filter")
    p.add_argument("--dry-run", action="store_true",
                   help="report how many works match, write nothing")
    a = p.parse_args(argv)
    prof = profile.load(a.profile) if a.profile else {}
    run(a.vault, a.query, prof, a.limit, a.min_year, a.min_citations, a.dry_run)


if __name__ == "__main__":
    main()
