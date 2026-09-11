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
import sys
import time
import urllib.error
import urllib.request
import zlib

from . import config, frontmatter, index

UA = ("Mozilla/5.0 (compatible; snowbib/0.1; "
      "+https://github.com/carsanmilcar/snowbib)")
PDF_MAGIC = b"%PDF"


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


def pending(root=None, only_unscreened=False):
    """Notes with an open-access link and no PDF downloaded yet."""
    papers, out = config.papers_dir(root), []
    for path in sorted(glob.glob(os.path.join(glob.escape(papers), "*.md"))):
        key = os.path.splitext(os.path.basename(path))[0]
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


def run(root=None, limit=None, only_unscreened=False, resolver=None, pause=1.0):
    root = config.vault_root(root)
    if not os.path.isdir(config.papers_dir(root)):
        sys.exit(f"snowbib: no vault at {root}")

    items = pending(root, only_unscreened)
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
        if not url:
            closed += 1
            continue
        try:
            size = download(url, item["dest"])
            ok += 1
            print(f"  ok      {item['citekey']}  ({size // 1024} KB)")
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
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
    p.add_argument("--unscreened", action="store_true",
                   help="only notes still at status: to_read")
    p.add_argument("--resolver", metavar="URL",
                   help="URL template with {doi} for papers with no open version, "
                        "e.g. a library proxy. You are responsible for what you point "
                        "it at.")
    p.add_argument("--pause", type=float, default=1.0,
                   help="seconds between downloads (default 1.0; be kind to servers)")
    a = p.parse_args(argv)
    run(a.vault, a.limit, a.unscreened, a.resolver, a.pause)


if __name__ == "__main__":
    main()
