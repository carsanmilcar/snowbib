"""Create an empty vault: python -m snowbib.init [--vault PATH] [--profile NAME]"""
import argparse
import os
import shutil

from . import config, profile

README = """# {name}

A snowbib vault. Notes live in `papers/`, one markdown file per paper.

- Build the index:   `python -m snowbib.index --vault .`
- Filter candidates: `python -m snowbib.check --vault . "<doi or title>"`
- Add papers:        `python -m snowbib.discover --vault . --query "<your topic>"`

`.snowbib/` holds the index and ledgers; it is generated, safe to delete and
rebuild. Open this folder as an Obsidian vault to read and link the notes.
"""


def create(root=None, profile_name=None):
    root = config.vault_root(root)
    papers, tools = config.papers_dir(root), config.tools_dir(root)
    made = []
    for path in (root, papers, tools):
        if not os.path.isdir(path):
            os.makedirs(path, exist_ok=True)
            made.append(path)

    readme = os.path.join(root, "README.md")
    if not os.path.exists(readme):
        with open(readme, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(README.format(name=os.path.basename(root) or "vault"))
        made.append(readme)

    if profile_name:
        prof = profile.load(profile_name)
        dst = os.path.join(tools, "profile.yaml")
        src = os.path.join(profile.BUILTIN, profile_name + ".yaml")
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copyfile(src, dst)
            made.append(dst)
        elif not os.path.exists(dst):
            shutil.copyfile(profile_name, dst)
            made.append(dst)
        print(f"profile: {prof.get('name')}")

    print(f"vault ready at {root}")
    for path in made:
        print(f"  created {os.path.relpath(path, root) if path != root else '.'}")
    if not made:
        print("  (everything already existed)")
    return root


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m snowbib.init",
                                description="Create an empty snowbib vault.")
    p.add_argument("vault", nargs="?", help="where to create it (default: cwd)")
    p.add_argument("--vault", dest="vault_opt", help="same, as an option")
    p.add_argument("--profile", help=f"field profile to copy in: {', '.join(profile.available())}")
    a = p.parse_args(argv)
    create(a.vault_opt or a.vault, a.profile)


if __name__ == "__main__":
    main()
