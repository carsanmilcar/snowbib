"""Create an empty vault: python -m snowbib.init [--vault PATH] [--profile NAME]"""
import argparse
import os
import shutil
import sys
import tempfile

from . import config, profile

README = """# {name}

A snowbib vault. Notes live in `papers/`, one markdown file per paper.

- Build the index:   `python -m snowbib.index --vault .`
- Filter candidates: `python -m snowbib.check --vault . "<doi or title>"`
- Add papers:        `python -m snowbib.discover --vault . --query "<your topic>"`

`.snowbib/` holds the index and ledgers; it is generated, safe to delete and
rebuild. Open this folder as an Obsidian vault to read and link the notes.
"""


# Path fragments that suggest a scratch directory, a sandbox, or an agent's own
# working folder. A vault there is lost the moment the session ends, and the user
# will never find it from Obsidian.
EPHEMERAL = ("/tmp/", "\\temp\\", "/var/folders/", "/private/var/", "\\appdata\\local\\temp\\",
             "/sandbox", "/workspace/", "/mnt/data", "/session", "/codex/", "/.cache/")


def looks_ephemeral(path):
    p = os.path.abspath(path).replace("\\", "/").lower() + "/"
    tmp = tempfile.gettempdir().replace("\\", "/").lower()
    if p.startswith(tmp.rstrip("/") + "/"):
        return "it is inside the system temporary directory"
    for frag in EPHEMERAL:
        if frag.replace("\\", "/") in p:
            return f"its path contains '{frag.strip('/').strip(chr(92))}'"
    home = os.path.expanduser("~").replace("\\", "/").lower()
    if home not in p:
        return "it is outside the user's home directory"
    return None


def create(root=None, profile_name=None):
    root = config.vault_root(root)
    reason = looks_ephemeral(root)
    if reason:
        print(f"snowbib: WARNING this vault is being created at\n  {root}\n"
              f"and {reason}.\n"
              f"  A vault must live on the user's own disk, somewhere they can find it "
              f"again\n  and open in Obsidian — Documents/my-field-vault, for example. If "
              f"this path is\n  a container, a sandbox or a per-session working folder, the "
              f"notes disappear\n  when the session ends and nothing is kept.\n"
              f"  Confirm the location with the user before going any further.",
              file=sys.stderr)
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
    print("  ^ this folder is the vault: open it in Obsidian (obsidian.md, free) with "
          "'Open folder as vault' once it has notes in it.")
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
