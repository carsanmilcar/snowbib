"""Reconstruct the citation graph: python -m snowbib.cites [--vault PATH]

Reads `referenced_works` from OpenAlex for every note that has an `openalex_id`,
then writes into each note:

  - `cites_vault` in the front matter: the references that have a note of their own
  - a `## Citations` section: those, plus the ones that do not, as unresolved
    wikilinks — a record of what your corpus cites, with no obligation to file it

Papers known only as citations ("ghosts") are also written to `.snowbib/` so a
later `check` can recognise them by DOI or title, which is what a web search
returns.

OpenAlex publishes `referenced_works` for roughly half of all works, so expect
some notes to end up with no outgoing citations. That is the source, not a bug.
"""
import argparse
import collections
import glob
import json
import os
import sys

from . import config, frontmatter, index, notes, openalex

SECTION = "## Citations"


def run(root=None, quiet=False):
    root = config.vault_root(root)
    papers, tools = config.papers_dir(root), config.tools_dir(root)
    if not os.path.isdir(papers):
        sys.exit(f"snowbib: no vault at {root}")

    oa2key, key2oa = {}, {}
    for path in sorted(glob.glob(os.path.join(glob.escape(papers), "*.md"))):
        key = os.path.splitext(os.path.basename(path))[0]
        fm = frontmatter.split(index.read_note(path))
        oa = frontmatter.get(fm, "openalex_id")
        if oa.startswith("W"):
            oa2key[oa] = key
            key2oa[key] = oa
    if not oa2key:
        sys.exit(f"snowbib: no notes with an openalex_id in {papers}. "
                 f"Run discover first, or add the ids by hand.")

    print(f"fetching references for {len(oa2key)} notes ...")
    refs = openalex.references(oa2key, tools=tools)
    with_refs = {k: v for k, v in refs.items() if v}
    print(f"OpenAlex returned references for {len(with_refs)} of {len(oa2key)}")

    external = sorted({r for rs in with_refs.values() for r in rs if r not in oa2key})
    print(f"resolving {len(external)} cited works that have no note ...")
    meta = openalex.metadata(external, tools=tools)

    ghost_key, taken = {}, set(oa2key.values())
    for wid in external:
        if wid in meta:
            k = notes.citekey(meta[wid], taken)
            # A generated key may collide with a note that lacks an openalex_id:
            # that means it IS that paper, so resolve to it instead of inventing.
            if k in taken and k not in ghost_key.values():
                ghost_key[wid] = k
                continue
            taken.add(k)
        else:
            k = wid                      # no metadata left: keep the raw id
        ghost_key[wid] = k

    ghost_meta = {w: meta[w] for w in external if w in meta}
    with open(os.path.join(tools, "ghost_meta.json"), "w", encoding="utf-8") as fh:
        json.dump(ghost_meta, fh, ensure_ascii=False)
    with open(os.path.join(tools, "citekey_openalex_map.json"), "w", encoding="utf-8") as fh:
        json.dump({k: w for w, k in ghost_key.items()}, fh, ensure_ascii=False)

    written, edges_in, edges_out = 0, 0, 0
    vault_keys = set(oa2key.values())
    for key, oa in key2oa.items():
        rs = refs.get(oa) or []
        if not rs:
            continue
        inside, outside = set(), set()
        for r in rs:
            k = oa2key.get(r) or ghost_key.get(r)
            if not k or k == key:
                continue
            (inside if k in vault_keys else outside).add(k)
        inside, outside = sorted(inside), sorted(outside)

        path = os.path.join(papers, key + ".md")
        text = index.read_note(path)
        if SECTION in text:
            text = text.split(SECTION)[0].rstrip() + "\n"
        fm = frontmatter.split(text)
        if fm is None:
            continue
        fm_end = text.index("\n---", 3)
        line = ("cites_vault: [" + ", ".join('"[[' + k + ']]"' for k in inside) + "]\n"
                f"cites_n: {len(inside) + len(outside)}\n")
        text = text[:fm_end + 1] + line + text[fm_end + 1:]

        body = [f"\n{SECTION}\n",
                "_Reconstructed from OpenAlex `referenced_works`. Links without a note "
                "are unresolved on purpose: a record, not a debt._\n"]
        if inside:
            body.append(f"\n**In this vault ({len(inside)}):**\n")
            body += [f"- [[{k}]]\n" for k in inside]
        if outside:
            body.append(f"\n**Cited, no note ({len(outside)}):**\n")
            body.append(" · ".join(f"[[{k}]]" for k in outside) + "\n")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text.rstrip() + "\n" + "".join(body))
        written += 1
        edges_in += len(inside)
        edges_out += len(outside)

    ghosts = collections.Counter()
    for key, oa in key2oa.items():
        for r in refs.get(oa) or []:
            k = ghost_key.get(r)
            if k and k not in vault_keys:
                ghosts[k] += 1

    if not quiet:
        print(f"\nnotes updated      : {written}")
        print(f"edges inside vault : {edges_in}")
        print(f"edges to no-note   : {edges_out} across {len(ghosts)} papers")
        if ghosts:
            top = ", ".join(f"{k} x{n}" for k, n in ghosts.most_common(5))
            print(f"most co-cited      : {top}")
            print("  ^ cited often by your own corpus and not filed: the obvious "
                  "candidates to add next.")
        print(f"\nNow rebuild the index:  python -m snowbib.index --vault {root}")
        print(f"\nTo look at what you just built: open Obsidian (free, no account, "
              f"obsidian.md),\nchoose 'Open folder as vault' and pick\n  {root}\n"
              f"The graph view shows each paper as a dot and each citation as a line; "
              f"hollow dots\nare papers yours cite that have no note yet. "
              f"If you are an assistant, walk the user\nthrough those clicks — "
              f"they cannot be done from a command line.")
    return {"updated": written, "inside": edges_in, "outside": edges_out}


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m snowbib.cites",
                                description="Reconstruct the vault's citation graph.")
    p.add_argument("--vault", help="vault root (default: $SNOWBIB_VAULT or cwd)")
    p.add_argument("--quiet", action="store_true")
    a = p.parse_args(argv)
    run(a.vault, a.quiet)


if __name__ == "__main__":
    main()
