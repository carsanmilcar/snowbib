"""Prepare a screening batch: python -m snowbib.screen [--vault PATH] [--limit N]

snowbib does not call a language model. This command prints the work order: the
profile's screening prompt, the notes still unscreened, and the rule that keeps
screening cheap — one agent per paper, so no paper body ever enters the
conversation you are reading.

Paste the output into Claude, ChatGPT or whatever agent you use.
"""
import argparse
import glob
import json
import os
import sys

from . import config, frontmatter, index, profile

INSTRUCTIONS = """\
HOW TO SCREEN THESE, CHEAPLY AND WITHOUT LYING

1. One agent per paper, in batches of about 8. Each agent reads ONLY its own
   paper and reports back a filled note. A paper body is 12-25k tokens; a filled
   note is about 600. Never read the papers in the conversation that is
   orchestrating the work.
2. Screen from the abstract first. Fetch the PDF only for papers that survive.
3. Fill `status` (reference if useful, discarded if not), the summary, the
   relevance, and the profile fields listed below.
4. Record citations worth chasing as [[citekey]] wikilinks. That is what makes
   the vault a graph rather than a pile of notes.
5. If a claim is not in the paper, leave the field empty. Do not infer, and do
   not copy the abstract's marketing.
"""


def unscreened(root=None, limit=None):
    papers = config.papers_dir(root)
    out = []
    for path in sorted(glob.glob(os.path.join(glob.escape(papers), "*.md"))):
        fm = frontmatter.split(index.read_note(path))
        if frontmatter.get(fm, "status") in ("to_read", ""):
            out.append({
                "citekey": os.path.splitext(os.path.basename(path))[0],
                "title": frontmatter.get(fm, "title"),
                "doi": frontmatter.get(fm, "doi"),
                "oa_pdf": frontmatter.get(fm, "oa_pdf"),
                "cited_by": frontmatter.get(fm, "cited_by"),
                "path": path,
            })
        if limit and len(out) >= limit:
            break
    return out


def run(root=None, limit=None, as_json=False):
    root = config.vault_root(root)
    if not os.path.isdir(config.papers_dir(root)):
        sys.exit(f"snowbib: no vault at {root}")

    prof_path = os.path.join(config.tools_dir(root), "profile.yaml")
    prof = profile.load(prof_path) if os.path.exists(prof_path) else {}
    queue = unscreened(root, limit)

    if as_json:
        print(json.dumps({"profile": prof, "queue": queue}, ensure_ascii=False, indent=1))
        return queue

    if not queue:
        print("Nothing to screen: every note has a status other than to_read.")
        return queue

    print(f"{len(queue)} note(s) to screen in {root}\n")
    print(INSTRUCTIONS)
    if prof.get("screening_prompt"):
        print(f"WHAT TO EXTRACT (profile: {prof.get('name')})\n{prof['screening_prompt']}\n")
    if prof.get("fields"):
        print("FIELDS TO FILL IN THE FRONT MATTER")
        for key, default in prof["fields"].items():
            empty = "[]" if isinstance(default, list) else '""'
            print("  " + key + ": " + empty)
        print()
    print("QUEUE")
    for item in queue:
        cited = f"  (cited {item['cited_by']})" if item["cited_by"] else ""
        print(f"  {item['citekey']}{cited}\n    {item['title'][:90]}")
        if item["doi"]:
            print(f"    doi: {item['doi']}")
    return queue


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m snowbib.screen",
                                description="Print the screening work order.")
    p.add_argument("--vault", help="vault root (default: $SNOWBIB_VAULT or cwd)")
    p.add_argument("--limit", type=int, help="only the first N unscreened notes")
    p.add_argument("--json", dest="as_json", action="store_true",
                   help="machine-readable output, for scripting the batch")
    a = p.parse_args(argv)
    run(a.vault, a.limit, a.as_json)


if __name__ == "__main__":
    main()
