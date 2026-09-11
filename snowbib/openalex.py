"""Thin OpenAlex client: paging, the polite pool, and an on-disk cache.

Only the pieces snowbib needs. No dependencies: urllib is enough for a JSON API.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from . import config

API = "https://api.openalex.org"
PAGE = 200          # OpenAlex allows up to 200 per page
MAX_IDS = 50        # ...but only 50 ids in one openalex_id filter
RETRIES = 3


def _cache_path(tools, key):
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)[:120]
    return os.path.join(tools, "cache", safe + ".json")


def get(path, params=None, tools=None, cache_key=None):
    """GET one OpenAlex URL, with retries and an optional on-disk cache."""
    params = dict(params or {})
    params["mailto"] = config.mailto()
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}"

    cached = _cache_path(tools, cache_key) if tools and cache_key else None
    if cached and os.path.exists(cached):
        try:
            with open(cached, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            pass

    last = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers=config.headers())
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.load(resp)
            break
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            last = exc
            if attempt == RETRIES - 1:
                raise RuntimeError(f"OpenAlex request failed: {url}\n{last}") from exc
            time.sleep(2 ** attempt)

    if cached:
        os.makedirs(os.path.dirname(cached), exist_ok=True)
        with open(cached, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
    return data


def count(filters):
    """How many works match, without downloading them."""
    data = get("works", {"filter": filters, "per-page": 1})
    return data["meta"]["count"]


def works(filters, select=None, limit=None, tools=None, progress=None):
    """Yield works matching `filters`, paging with a cursor."""
    cursor, seen = "*", 0
    select = select or ("id,doi,title,display_name,publication_year,authorships,"
                        "primary_location,cited_by_count,topics,open_access,"
                        "referenced_works_count")
    while cursor:
        params = {"filter": filters, "per-page": PAGE, "cursor": cursor,
                  "select": select}
        data = get("works", params, tools=tools,
                   cache_key=f"works_{filters}_{cursor}" if tools else None)
        for w in data["results"]:
            yield w
            seen += 1
            if limit and seen >= limit:
                return
        if progress:
            progress(seen, data["meta"]["count"])
        cursor = data["meta"].get("next_cursor")
        if not data["results"]:
            return


def references(ids, tools=None):
    """Map OpenAlex id -> list of referenced ids, for the given works."""
    out = {}
    ids = list(ids)
    for i in range(0, len(ids), MAX_IDS):
        chunk = ids[i:i + MAX_IDS]
        data = get("works", {"filter": "openalex_id:" + "|".join(chunk),
                             "select": "id,referenced_works", "per-page": MAX_IDS},
                   tools=tools, cache_key=f"refs_{chunk[0]}_{len(chunk)}" if tools else None)
        for w in data["results"]:
            out[short_id(w["id"])] = [short_id(r) for r in w.get("referenced_works") or []]
        time.sleep(0.2)
    return out


def metadata(ids, tools=None):
    """Map OpenAlex id -> minimal metadata, for works you only know by id."""
    out = {}
    ids = list(ids)
    for i in range(0, len(ids), MAX_IDS):
        chunk = ids[i:i + MAX_IDS]
        data = get("works", {"filter": "openalex_id:" + "|".join(chunk),
                             "select": "id,display_name,publication_year,authorships,doi",
                             "per-page": MAX_IDS},
                   tools=tools, cache_key=f"meta_{chunk[0]}_{len(chunk)}" if tools else None)
        for w in data["results"]:
            authors = w.get("authorships") or []
            out[short_id(w["id"])] = {
                "title": w.get("display_name") or "",
                "year": w.get("publication_year"),
                "first": authors[0]["author"]["display_name"] if authors else "",
                "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
            }
        time.sleep(0.2)
    return out


def short_id(url_or_id):
    """W2741809807 from https://openalex.org/W2741809807."""
    return (url_or_id or "").rsplit("/", 1)[-1]
