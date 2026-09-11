"""Read a field profile.

A tiny indentation-based reader for the subset of YAML the profiles in
`profiles/` use — nested mappings, `- ` lists, folded `>` blocks and scalars.
Not a YAML parser: snowbib ships with no dependencies, and the profile format is
one we define and document ourselves.
"""
import os
import re

BUILTIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "profiles")


def _strip_comment(raw):
    """Drop a trailing `# comment`, but never one inside quotes."""
    raw = raw.strip()
    if raw[:1] in ("'", '"'):
        end = raw.find(raw[0], 1)
        return raw[:end + 1] if end > 0 else raw
    if raw.startswith("["):
        end = raw.find("]")
        return raw[:end + 1] if end > 0 else raw
    return raw.split("#", 1)[0].strip()


def _scalar(raw):
    raw = _strip_comment(raw)
    if raw == "[]":
        return []
    if raw.startswith("[") and raw.endswith("]"):
        return [x.strip().strip("\"'") for x in raw[1:-1].split(",") if x.strip()]
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    return raw


def parse(text):
    """Parse into nested dicts. Lists are `- item` lines; `>` folds the block."""
    root = {}
    stack = [(-1, root)]
    lines = text.replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        content = line.strip()

        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if content.startswith("- "):
            if not isinstance(parent, list):
                continue
            parent.append(_scalar(content[2:]))
            continue

        if ":" not in content:
            continue
        key, _, raw = content.partition(":")
        key, raw = key.strip(), raw.strip()

        if raw in (">", "|", ">-", "|-"):
            block = []
            while i < len(lines) and (not lines[i].strip()
                                      or len(lines[i]) - len(lines[i].lstrip()) > indent):
                block.append(lines[i].strip())
                i += 1
            parent[key] = " ".join(x for x in block if x).strip()
        elif raw == "":
            # Either a nested mapping or a list; decide from the next real line.
            nxt = next((l for l in lines[i:] if l.strip()
                        and not l.lstrip().startswith("#")), "")
            child = [] if nxt.strip().startswith("- ") else {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _scalar(raw)
    return root


def load(name_or_path):
    """Load a profile by name (from profiles/) or by path."""
    path = name_or_path
    if not os.path.exists(path):
        path = os.path.join(BUILTIN, name_or_path + ".yaml")
    if not os.path.exists(path):
        available = ", ".join(sorted(
            os.path.splitext(f)[0] for f in os.listdir(BUILTIN) if f.endswith(".yaml")))
        raise SystemExit(f"snowbib: no profile '{name_or_path}'. Available: {available}\n"
                         f"Or pass a path to your own .yaml.")
    with open(path, encoding="utf-8") as fh:
        data = parse(fh.read())
    data.setdefault("name", os.path.splitext(os.path.basename(path))[0])
    data.setdefault("openalex", {})
    data.setdefault("fields", {})
    return data


def available():
    if not os.path.isdir(BUILTIN):
        return []
    return sorted(os.path.splitext(f)[0] for f in os.listdir(BUILTIN)
                  if f.endswith(".yaml"))
