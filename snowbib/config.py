"""snowbib configuration: vault paths and OpenAlex identity.

The OpenAlex helpers (`mailto`, `headers`) are not used by the indexing and
checking commands, which touch no network. They exist for the discovery half of
the project, still being ported.
"""
import os
import sys

ENV_MAIL = "SNOWBIB_MAILTO"
ENV_VAULT = "SNOWBIB_VAULT"
UA = "snowbib/{} (https://github.com/carsanmilcar/snowbib)"

_dotenv_loaded = False


def load_dotenv(root=None):
    """Read KEY=VALUE lines from a .env into the environment, once.

    Looked up in `root`, then the cwd, then the repo root. Dependency-free on
    purpose. Real environment variables win, so an explicit export or a CI
    secret always overrides the file.
    """
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    _dotenv_loaded = True
    candidates = [root, os.getcwd(),
                  os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]
    for base in [c for c in candidates if c]:
        path = os.path.join(base, ".env")
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                lines = fh.readlines()
        except OSError as exc:
            print(f"snowbib: cannot read {path}: {exc}", file=sys.stderr)
            return
        for line in lines:
            line = line.strip()
            if line.startswith("export "):
                line = line[len("export "):].strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip()
            # Strip an inline comment, but only outside quotes.
            if v[:1] in ("'", '"'):
                closing = v.find(v[0], 1)
                v = v[1:closing] if closing > 0 else v[1:]
            else:
                v = v.split("#", 1)[0].strip()
            os.environ.setdefault(k.strip(), v)
        return


def version():
    from . import __version__
    return __version__


def mailto():
    """Contact email for OpenAlex's polite pool.

    Without it you fall back to the anonymous pool, which is heavily throttled.
    Never hardcode one: whoever clones this would hit OpenAlex identifying as
    the repo author, spending someone else's reputation.
    """
    load_dotenv()
    m = os.environ.get(ENV_MAIL, "").strip()
    if not m or "@" not in m or any(c.isspace() for c in m):
        sys.exit(
            f"{ENV_MAIL} is unset or malformed. OpenAlex needs a contact email to\n"
            f"give you polite-pool access (far more reliable than anonymous).\n"
            f"  .env file  : cp .env.example .env  and put your address in it\n"
            f"  PowerShell : $env:{ENV_MAIL} = 'you@example.com'\n"
            f"  bash       : export {ENV_MAIL}=you@example.com"
        )
    return m


def headers():
    return {"User-Agent": f"{UA.format(version())} (mailto:{mailto()})"}


def vault_root(path=None):
    """Vault root: explicit argument, then SNOWBIB_VAULT (env or .env), then cwd."""
    if path:
        return os.path.abspath(path)
    load_dotenv()
    return os.path.abspath(os.environ.get(ENV_VAULT) or os.getcwd())


def papers_dir(root=None):
    return os.path.join(vault_root(root), "papers")


def tools_dir(root=None):
    return os.path.join(vault_root(root), ".snowbib")
