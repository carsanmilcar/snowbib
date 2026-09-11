"""Download the PDFs of notes that have one: python -m snowbib.fetch [--vault PATH]

Open access only. Every note carries the `oa_pdf` link OpenAlex publishes for it;
this walks the vault and downloads those into `.snowbib/pdf/<citekey>.pdf`.

Papers with no open version are reported, not guessed at. Fetching those is a
separate decision — a library proxy, an interlibrary loan, or a tool you plug in
yourself through `--resolver`.
"""
import argparse
import glob
import gzip
import os
import re
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zlib

from . import config, frontmatter, index, scihub

UA = ("Mozilla/5.0 (compatible; snowbib/0.1; "
      "+https://github.com/carsanmilcar/snowbib)")
PDF_MAGIC = b"%PDF"
DOI_RE = re.compile(r"^10\.[0-9]{4,9}/[-._;()/:a-zA-Z0-9<>\[\]]+$")


def pdf_dir(root=None):
    return os.path.join(config.tools_dir(root), "pdf")


def download(url, dest, timeout=90):
    """Fetch one URL and keep it only if it really is a PDF."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        # Several publishers answer a bare urllib request with 403; these are the
        # headers a browser sends, and asking for PDF first avoids landing pages.
        "Accept": "application/pdf,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        encoding = (resp.headers.get("Content-Encoding") or "").lower()
    if encoding == "gzip" or data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    elif encoding == "deflate":
        data = zlib.decompress(data, -zlib.MAX_WBITS)
    if not data.startswith(PDF_MAGIC):
        raise ValueError(f"not a PDF (starts with {data[:8]!r}); "
                         f"the link probably leads to a landing page")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as fh:
        fh.write(data)
    return len(data)


def pending(root=None, only_unscreened=False, keys=None):
    """Notes with an open-access link and no PDF downloaded yet.

    `keys` restricts to a chosen set of citekeys: the usual case is a person
    picking which papers are worth reading, which is not the same as the first N
    in alphabetical order.
    """
    papers, out = config.papers_dir(root), []
    for path in sorted(glob.glob(os.path.join(glob.escape(papers), "*.md"))):
        key = os.path.splitext(os.path.basename(path))[0]
        if keys and key not in keys:
            continue
        fm = frontmatter.split(index.read_note(path))
        if only_unscreened and frontmatter.get(fm, "status") not in ("to_read", ""):
            continue
        dest = os.path.join(pdf_dir(root), key + ".pdf")
        out.append({"citekey": key,
                    "oa_pdf": frontmatter.get(fm, "oa_pdf"),
                    "doi": frontmatter.get(fm, "doi"),
                    "title": frontmatter.get(fm, "title"),
                    "dest": dest,
                    "have": os.path.exists(dest)})
    return out


def run_resolver_cmd(template, doi, dest):
    """Hand a DOI to an external program and let it produce the PDF.

    snowbib ships no way of getting papers that are not open access, and does not
    want one: which sources are acceptable depends on your institution and your
    jurisdiction, not on this tool. This hook lets you plug in whatever you
    already use — a library client, a publisher API you have a key for, a script
    of your own — without snowbib carrying or endorsing it.

    The command gets {doi} and {out} substituted. It must leave a PDF at {out}.
    """
    # A DOI reaches us from OpenAlex and is about to be handed to a process, so
    # check it looks like a DOI before it can turn into arguments of its own.
    if not DOI_RE.match(doi):
        raise ValueError(f"refusing to pass a DOI of an unexpected shape: {doi!r}")
    filled = template.replace("{doi}", doi).replace("{out}", dest)
    # shlex is POSIX-only: on Windows it eats the backslashes of every path.
    cmd = filled if os.name == "nt" else shlex.split(filled)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    proc = subprocess.run(cmd, capture_output=True, timeout=300, shell=False)
    if proc.returncode != 0:
        raise ValueError(f"resolver exited {proc.returncode}: "
                         f"{proc.stderr.decode('utf-8', 'replace')[:200]}")
    if not os.path.exists(dest):
        raise ValueError("resolver wrote no file")
    with open(dest, "rb") as fh:
        magic = fh.read(4)
    if not magic.startswith(PDF_MAGIC):
        # Outside the `with`: Windows refuses to delete a file that is still open.
        os.remove(dest)
        raise ValueError("resolver produced something that is not a PDF")
    return os.path.getsize(dest)


def run(root=None, limit=None, only_unscreened=False, resolver=None, pause=1.0,
        resolver_cmd=None, use_scihub=False, keys=None):
    root = config.vault_root(root)
    if not os.path.isdir(config.papers_dir(root)):
        sys.exit(f"snowbib: no vault at {root}")

    items = pending(root, only_unscreened, keys)
    if keys:
        missing = sorted(set(keys) - {i["citekey"] for i in items})
        if missing:
            print(f"snowbib: no note for {', '.join(missing[:5])}"
                  f"{' ...' if len(missing) > 5 else ''}", file=sys.stderr)
        if not items:
            sys.exit("snowbib: none of the citekeys you asked for exist in this vault.")
    todo = [i for i in items if not i["have"]]
    have = len(items) - len(todo)
    print(f"{len(items)} note(s), {have} already downloaded, {len(todo)} to try")

    ok = failed = closed = 0
    for item in todo:
        if limit and ok >= limit:
            break
        url = item["oa_pdf"]
        if not url and resolver and item["doi"]:
            url = resolver.replace("{doi}", item["doi"])
        use_cmd = not url and resolver_cmd and item["doi"]
        use_sh = not url and not use_cmd and use_scihub and item["doi"]
        if not url and not use_cmd and not use_sh:
            closed += 1
            continue
        try:
            if use_cmd:
                size = run_resolver_cmd(resolver_cmd, item["doi"], item["dest"])
                label = "ok(cmd)"
            elif use_sh:
                size = scihub.fetch(item["doi"], item["dest"])
                label = "ok(sh)"
            else:
                size = download(url, item["dest"])
                label = "ok"
            ok += 1
            print(f"  {label:7} {item['citekey']}  ({size // 1024} KB)")
        except (urllib.error.URLError, TimeoutError, ValueError, OSError,
                RuntimeError, subprocess.SubprocessError) as exc:
            failed += 1
            print(f"  failed  {item['citekey']}: {exc}", file=sys.stderr)
        time.sleep(pause)

    print(f"\ndownloaded={ok} failed={failed} no-open-version={closed}")
    if closed:
        print(f"{closed} paper(s) have no open-access link in OpenAlex. snowbib does not\n"
              f"guess at those: get them through your library, or pass --resolver with a\n"
              f"URL template containing {{doi}} if you have a service that resolves them.")
    if ok:
        print(f"PDFs in {pdf_dir(root)}\n"
              f"Next: python -m snowbib.convert --vault {root}")
    return {"downloaded": ok, "failed": failed, "closed": closed}


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="python -m snowbib.fetch",
        description="Download open-access PDFs for the notes in a vault.")
    p.add_argument("--vault", help="vault root (default: $SNOWBIB_VAULT or cwd)")
    p.add_argument("--limit", type=int, help="stop after N successful downloads")
    p.add_argument("--citekey", action="append", default=[], metavar="KEY",
                   help="only this note; repeat for several. Use it to download the "
                        "papers someone actually chose, rather than the first N")
    p.add_argument("--from-file", metavar="PATH",
                   help="file with one citekey per line (blank lines and # ignored)")
    p.add_argument("--unscreened", action="store_true",
                   help="only notes still at status: to_read")
    p.add_argument("--resolver", metavar="URL",
                   help="URL template with {doi} for papers with no open version, "
                        "e.g. a library proxy. You are responsible for what you point "
                        "it at.")
    p.add_argument("--resolver-cmd", metavar="CMD",
                   help="external command for papers with no open version, with {doi} "
                        "and {out} substituted, e.g. "
                        "\"my-fetcher --doi {doi} --output {out}\". snowbib ships no "
                        "such tool and takes no position on which you use; what is "
                        "acceptable depends on your institution and jurisdiction.")
    p.add_argument("--scihub", action="store_true",
                   help="for papers with no open version, try the Sci-Hub client in the "
                        "vendor/scihub-mcp submodule. Not bundled and not installed by "
                        "default; see REFERENCE.md. Whether this is lawful where you are "
                        "is your call.")
    p.add_argument("--pause", type=float, default=1.0,
                   help="seconds between downloads (default 1.0; be kind to servers)")
    a = p.parse_args(argv)
    keys = set(a.citekey)
    if a.from_file:
        with open(a.from_file, encoding="utf-8") as fh:
            keys |= {l.strip() for l in fh
                     if l.strip() and not l.lstrip().startswith("#")}
    run(a.vault, a.limit, a.unscreened, a.resolver, a.pause, a.resolver_cmd,
        a.scihub, keys or None)


if __name__ == "__main__":
    main()
