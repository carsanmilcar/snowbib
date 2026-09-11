"""Adapter for the Sci-Hub client vendored as a git submodule.

snowbib carries none of that code. `vendor/scihub-mcp` is a submodule pointing at
<https://github.com/carsanmilcar/Sci-Hub-MCP-Server>, itself a fork of
<https://github.com/JackKuo666/Sci-Hub-MCP-Server>, which publishes no licence.
Cloning snowbib does not bring it down; you opt in explicitly:

    git submodule update --init vendor/scihub-mcp
    pip install -r vendor/scihub-mcp/requirements.txt

Whether using it is lawful where you are is your call, not this tool's. It is not
wired into any default: `fetch` only touches it when you pass --scihub.

This module is the seam and nothing else: it puts the submodule on the path, calls
it, and checks that what comes back is a PDF.
"""
import os
import sys

VENDOR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "vendor", "scihub-mcp")
PDF_MAGIC = b"%PDF"

MISSING = (
    "snowbib: the Sci-Hub submodule is not present.\n"
    "  git submodule update --init vendor/scihub-mcp\n"
    "  pip install -r vendor/scihub-mcp/requirements.txt\n"
    "It is not bundled with snowbib and is not installed by default; see the\n"
    "'Closed access' section of REFERENCE.md before using it."
)


def available():
    return os.path.isfile(os.path.join(VENDOR, "sci_hub_search.py"))


def _load():
    if not available():
        raise RuntimeError(MISSING)
    if VENDOR not in sys.path:
        sys.path.insert(0, VENDOR)
    try:
        import sci_hub_search
    except ImportError as exc:
        raise RuntimeError(
            f"{MISSING}\n(the submodule is there but will not import: {exc})") from exc
    return sci_hub_search


def fetch(doi, dest):
    """Resolve a DOI through the vendored client and save the PDF at `dest`.

    Returns the size in bytes. Raises RuntimeError when the submodule is absent
    and ValueError when nothing usable comes back — never leaves a non-PDF behind.
    """
    client = _load()
    info = client.search_paper_by_doi(doi)
    url = (info or {}).get("pdf_url")
    if not url:
        raise ValueError(f"no PDF url for {doi}")

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if not client.download_paper(url, dest):
        raise ValueError(f"download failed for {doi}")

    with open(dest, "rb") as fh:
        magic = fh.read(4)
    if not magic.startswith(PDF_MAGIC):
        os.remove(dest)          # outside the `with`: Windows will not delete an open file
        raise ValueError(f"what came back for {doi} is not a PDF")
    return os.path.getsize(dest)
