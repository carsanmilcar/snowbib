"""PDF to markdown: python -m snowbib.convert [--vault PATH]

Extracts the text layer of downloaded PDFs into `.snowbib/text/<citekey>.md`, so
an agent can screen a paper from its body — the reported numbers and the results
prose — instead of trusting the abstract.

Needs pymupdf4llm. Journal PDFs are born digital, so a plain text extraction is
instant and good enough for screening; its one weak spot is display equations,
which do not survive. For those, read the PDF.

A scanned PDF has no text layer and is reported as such rather than silently
producing an empty file.
"""
import argparse
import glob
import os
import sys

from . import config

MIN_CHARS_PER_PAGE = 100


def text_dir(root=None):
    return os.path.join(config.tools_dir(root), "text")


def _require_pymupdf():
    try:
        import pymupdf
        import pymupdf4llm
        return pymupdf, pymupdf4llm
    except ImportError:
        sys.exit("snowbib: this command needs pymupdf4llm.\n"
                 "  pip install pymupdf4llm\n"
                 "Everything else in snowbib works without it.")


def convert_one(pdf_path, out_path):
    """Return (chars, pages, verdict). verdict is 'ok' or 'scanned'."""
    pymupdf, pymupdf4llm = _require_pymupdf()
    doc = pymupdf.open(pdf_path)
    pages = doc.page_count
    raw = sum(len(p.get_text()) for p in doc)
    doc.close()
    md = pymupdf4llm.to_markdown(pdf_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(md)
    per_page = raw / pages if pages else 0
    return len(md), pages, "ok" if per_page >= MIN_CHARS_PER_PAGE else "scanned"


def run(root=None, limit=None, overwrite=False):
    root = config.vault_root(root)
    from .fetch import pdf_dir
    pdfs = sorted(glob.glob(os.path.join(glob.escape(pdf_dir(root)), "*.pdf")))
    if not pdfs:
        sys.exit(f"snowbib: no PDFs in {pdf_dir(root)}\n"
                 f"Run: python -m snowbib.fetch --vault {root}")

    done = scanned = skipped = 0
    for pdf in pdfs:
        key = os.path.splitext(os.path.basename(pdf))[0]
        out = os.path.join(text_dir(root), key + ".md")
        if os.path.exists(out) and not overwrite:
            skipped += 1
            continue
        chars, pages, verdict = convert_one(pdf, out)
        if verdict == "scanned":
            scanned += 1
            print(f"  scanned {key}: {pages} page(s), almost no text layer. "
                  f"Needs OCR; snowbib does not do that.", file=sys.stderr)
        else:
            done += 1
            print(f"  ok      {key}  ({pages} pages, {chars // 1000}k chars)")
        if limit and done >= limit:
            break

    print(f"\nconverted={done} scanned={scanned} already-done={skipped}")
    if done:
        print(f"Text in {text_dir(root)}\n"
              f"Screen it with: python -m snowbib.screen --vault {root}\n"
              f"Give each agent ONE file from that folder — never read them all into one "
              f"conversation.")
    return {"converted": done, "scanned": scanned, "skipped": skipped}


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m snowbib.convert",
                                description="Convert downloaded PDFs to markdown.")
    p.add_argument("--vault", help="vault root (default: $SNOWBIB_VAULT or cwd)")
    p.add_argument("--limit", type=int, help="stop after N conversions")
    p.add_argument("--overwrite", action="store_true", help="redo files already converted")
    a = p.parse_args(argv)
    run(a.vault, a.limit, a.overwrite)


if __name__ == "__main__":
    main()
