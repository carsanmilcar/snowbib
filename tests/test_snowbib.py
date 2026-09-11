"""Tests for snowbib. Run: python -m unittest discover -s tests

Most cases here are a bug that shipped once: front matter that is not double
quoted, CRLF line endings, counting link occurrences instead of citing notes, a
vault path with brackets, a non-PDF saved as one, a DOI reaching a subprocess.

No network: anything that would call OpenAlex is either stubbed or not exercised.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snowbib import check, frontmatter, index  # noqa: E402


def note(**fm):
    body = fm.pop("body", "")
    lines = "\n".join(f"{k}: {v}" for k, v in fm.items())
    return f"---\n{lines}\n---\n\n{body}\n"


class VaultCase(unittest.TestCase):
    def setUp(self, dirname="vault"):
        self.tmp = tempfile.mkdtemp(prefix="snowbib-test-")
        self.vault = os.path.join(self.tmp, dirname)
        self.papers = os.path.join(self.vault, "papers")
        os.makedirs(self.papers)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, name, text):
        with open(os.path.join(self.papers, name), "w", encoding="utf-8") as fh:
            fh.write(text)

    def build(self, **kw):
        kw.setdefault("quiet", True)
        return index.build(self.vault, **kw)

    def verdicts(self, *candidates):
        idx = self.build()
        idx["_excluded_dois"] = set(idx.get("excluded_dois", []))
        idx["_excluded_ids"] = set(idx.get("excluded_ids", []))
        return [check.lookup(c, idx)[0] for c in candidates]


class TestFrontMatterSpellings(VaultCase):
    """A note must be found whichever way YAML allows writing its title."""

    def test_all_spellings_are_indexed(self):
        self.write("double.md", note(title='"Double quoted"'))
        self.write("single.md", note(title="'Single quoted'"))
        self.write("bare.md", note(title="Bare unquoted title"))
        self.write("folded.md", "---\ntitle: >\n  folded over\n  two lines\n---\n\nbody\n")
        self.assertEqual(
            self.verdicts("Double quoted", "Single quoted", "Bare unquoted title",
                          "folded over two lines"),
            ["FILED"] * 4)

    def test_doi_in_any_spelling(self):
        self.write("a.md", note(title="A", doi='"10.1000/double"'))
        self.write("b.md", note(title="B", doi="10.1000/bare"))
        self.write("c.md", note(title="C", doi="'10.1000/single'"))
        self.assertEqual(
            self.verdicts("10.1000/double", "10.1000/bare",
                          "https://doi.org/10.1000/single"),
            ["FILED"] * 3)

    def test_missing_fields_do_not_crash(self):
        self.write("bare.md", note(status="read"))
        self.write("empty.md", "")
        self.write("nofm.md", "# Just a heading\ntitle: not a field\n")
        idx = self.build()
        self.assertEqual(idx["notes"]["nofm"]["title"], "",
                         "a note without front matter must not have the body parsed")


class TestCitationCounts(VaultCase):
    """CITED xN means N notes, not N occurrences of the link."""

    def test_repeated_link_in_one_note_counts_once(self):
        self.write("a.md", note(title="A", body="[[ghost]] again [[ghost]] and [[ghost]]"))
        idx = self.build()
        self.assertEqual(idx["ghosts"]["ghost"], 1)

    def test_distinct_notes_accumulate(self):
        for n in "abc":
            self.write(f"{n}.md", note(title=n.upper(), body="[[ghost]] [[ghost]]"))
        idx = self.build()
        self.assertEqual(idx["ghosts"]["ghost"], 3)

    def test_self_link_is_not_a_citation(self):
        self.write("a.md", note(title="A", body="see [[a]]"))
        self.assertNotIn("a", self.build()["ghosts"])

    def test_moc_prefix_ignored(self):
        self.write("a.md", note(title="A", body="[[MOC-topic]] [[real]]"))
        ghosts = self.build()["ghosts"]
        self.assertIn("real", ghosts)
        self.assertNotIn("MOC-topic", ghosts)


class TestAwkwardPaths(VaultCase):
    """glob treats [...] as a character class unless escaped."""

    def setUp(self):
        super().setUp(dirname="vault [2026]")

    def test_brackets_in_vault_path(self):
        self.write("a.md", note(title="Bracketed"))
        self.assertEqual(self.verdicts("Bracketed"), ["FILED"])


class TestVerdicts(VaultCase):
    def test_four_verdicts(self):
        self.write("filed.md", note(title='"Filed paper"', doi='"10.1000/filed"',
                                    body="[[ghostkey]]"))
        tools = os.path.join(self.vault, ".snowbib")
        os.makedirs(tools, exist_ok=True)
        with open(os.path.join(tools, "excluded.json"), "w", encoding="utf-8") as fh:
            json.dump({"ids": ["W999888777"], "dois": ["10.1000/buried"]}, fh)
        self.assertEqual(
            self.verdicts("10.1000/filed", "10.1000/buried", "ghostkey", "10.1000/unseen"),
            ["FILED", "DROPPED", "CITED", "NEW"])

    def test_new_only_filters(self):
        self.write("filed.md", note(title='"Filed paper"'))
        idx = self.build()
        idx["_excluded_dois"], idx["_excluded_ids"] = set(), set()
        out = io.StringIO()
        known = check.run(["Filed paper", "Something else"], idx, new_only=True, out=out)
        self.assertEqual(known, 1)
        self.assertNotIn("Filed paper", out.getvalue())
        self.assertIn("Something else", out.getvalue())

    def test_title_matching_ignores_accents_and_punctuation(self):
        self.write("fr.md", note(title='"Prévision d\'ensemble"'))
        self.assertEqual(self.verdicts("prevision densemble"), ["FILED"])


class TestMissingVault(unittest.TestCase):
    def test_missing_papers_dir_exits(self):
        tmp = tempfile.mkdtemp(prefix="snowbib-test-")
        try:
            with self.assertRaises(SystemExit):
                index.build(os.path.join(tmp, "nope"), quiet=True)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestFrontMatterUnit(unittest.TestCase):
    def test_split_requires_leading_marker(self):
        self.assertIsNone(frontmatter.split("no front matter\n---\nlater\n"))
        self.assertIsNone(frontmatter.split(""))
        self.assertIsNotNone(frontmatter.split("---\na: 1\n---\n"))

    def test_get_strips_inline_comment_only_when_unquoted(self):
        fm = frontmatter.split('---\na: bare # note\nb: "quoted # kept"\n---\n')
        self.assertEqual(frontmatter.get(fm, "a"), "bare")
        self.assertEqual(frontmatter.get(fm, "b"), "quoted # kept")



class TestLineEndings(VaultCase):
    """Windows editors write CRLF; the closing --- must still be recognised."""

    def write_crlf(self, name, text):
        with open(os.path.join(self.papers, name), "wb") as fh:
            fh.write(text.replace("\n", "\r\n").encode("utf-8"))

    def test_crlf_note_is_indexed(self):
        self.write_crlf("crlf.md", note(title='"CRLF paper"', doi='"10.1000/crlf"'))
        self.assertEqual(self.verdicts("CRLF paper", "10.1000/crlf"), ["FILED", "FILED"])


class TestProfileReader(unittest.TestCase):
    """The profile reader is not YAML: check the subset we document."""

    def test_nested_lists_scalars_and_folded_blocks(self):
        from snowbib import profile
        data = profile.parse(
            "name: demo\n"
            "openalex:\n"
            "  field: fields/26            # a trailing comment\n"
            "  queries:\n"
            '    - "first phrase"\n'
            "    - second phrase\n"
            "  min_year: 2000\n"
            "fields:\n"
            '  setting: ""\n'
            "  technique: []\n"
            "screening_prompt: >\n"
            "  folded over\n"
            "  two lines\n")
        self.assertEqual(data["name"], "demo")
        self.assertEqual(data["openalex"]["field"], "fields/26")
        self.assertEqual(data["openalex"]["queries"], ["first phrase", "second phrase"])
        self.assertEqual(data["openalex"]["min_year"], 2000)
        self.assertEqual(data["fields"], {"setting": "", "technique": []})
        self.assertEqual(data["screening_prompt"], "folded over two lines")

    def test_shipped_profiles_parse(self):
        from snowbib import profile
        for name in profile.available():
            p = profile.load(name)
            self.assertTrue(p.get("name"))
            self.assertTrue(p["openalex"].get("queries"), f"{name} has no queries")


class TestCitekeys(unittest.TestCase):
    def test_shape_and_stopwords(self):
        from snowbib import notes
        self.assertEqual(
            notes.citekey({"first": "Gunnar Carlsson", "year": 2009,
                           "title": "Topology and data"}),
            "carlsson2009topology")

    def test_collisions_get_a_suffix(self):
        from snowbib import notes
        taken = {"carlsson2009topology"}
        second = notes.citekey({"first": "Gunnar Carlsson", "year": 2009,
                                "title": "Topology and data"}, taken)
        self.assertEqual(second, "carlsson2009topologya")

    def test_missing_metadata_does_not_crash(self):
        from snowbib import notes
        self.assertEqual(notes.citekey({}), "anonndUNTITLED".replace("UNTITLED", "untitled"))


class TestDiscoverFilter(unittest.TestCase):
    """No network: just the filter string sent to OpenAlex."""

    def test_filter_composition(self):
        from snowbib import discover
        f = discover.build_filter(["persistent homology"], field="fields/26",
                                  min_year=2015, min_citations=50)
        self.assertIn("title_and_abstract.search:persistent homology", f)
        self.assertIn("primary_topic.field.id:fields/26", f)
        self.assertIn("publication_year:>2014", f)
        self.assertIn("cited_by_count:>49", f)

    def test_several_queries_are_unioned_with_a_pipe_not_the_word_or(self):
        """OpenAlex unions with "|". "a OR b" searches for the literal word and
        returns fewer works than either phrase alone — measured: 3,046 for one
        phrase, 715 for the two joined by OR, 7,691 joined by "|"."""
        from snowbib import discover
        f = discover.build_filter(["a", "b"])
        self.assertIn("search:a|b", f)
        self.assertNotIn(" OR ", f)


class TestInit(unittest.TestCase):
    def test_creates_layout(self):
        from snowbib import init
        tmp = tempfile.mkdtemp(prefix="snowbib-test-")
        try:
            root = os.path.join(tmp, "vault")
            init.create(root)
            self.assertTrue(os.path.isdir(os.path.join(root, "papers")))
            self.assertTrue(os.path.isdir(os.path.join(root, ".snowbib")))
            self.assertTrue(os.path.isfile(os.path.join(root, "README.md")))
            init.create(root)  # idempotent
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestLowMatchWarning(unittest.TestCase):
    """A near-zero count is almost always a non-English query; say so."""

    def test_warns_and_names_the_language_trap(self):
        import contextlib
        from snowbib import discover, openalex
        tmp = tempfile.mkdtemp(prefix="snowbib-test-")
        try:
            os.makedirs(os.path.join(tmp, "papers"))
            original = openalex.count
            openalex.count = lambda filters: 3
            err = io.StringIO()
            try:
                with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                    discover.run(tmp, ["mecanica cuantica supersimetrica"], dry_run=True)
            finally:
                openalex.count = original
            self.assertIn("ENGLISH", err.getvalue())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestEphemeralVaultWarning(unittest.TestCase):
    """A vault in a scratch or sandbox folder is lost when the session ends."""

    def test_temp_directory_is_flagged(self):
        from snowbib import init
        tmp = tempfile.mkdtemp(prefix="snowbib-test-")
        try:
            self.assertIsNotNone(init.looks_ephemeral(os.path.join(tmp, "vault")))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_normal_home_folder_is_not_flagged(self):
        from snowbib import init
        self.assertIsNone(
            init.looks_ephemeral(os.path.join(os.path.expanduser("~"),
                                              "Documents", "my-field-vault")))

    def test_agent_session_folders_are_flagged(self):
        from snowbib import init
        home = os.path.expanduser("~")
        for bad in ("Documents/Codex/2026-09-11/some-session",
                    "workspace/vault", "sandbox/vault"):
            self.assertIsNotNone(init.looks_ephemeral(os.path.join(home, *bad.split("/"))),
                                 f"{bad} should be flagged")


class TestFetch(VaultCase):
    """No network: the parts that decide what to download and what to keep."""

    def test_pending_lists_notes_with_an_open_link(self):
        from snowbib import fetch
        self.write("open.md", note(title='"Open"', oa_pdf='"https://x/y.pdf"'))
        self.write("closed.md", note(title='"Closed"', oa_pdf='""'))
        items = {i["citekey"]: i for i in fetch.pending(self.vault)}
        self.assertEqual(items["open"]["oa_pdf"], "https://x/y.pdf")
        self.assertEqual(items["closed"]["oa_pdf"], "")
        self.assertFalse(items["open"]["have"])

    def test_unscreened_filter(self):
        from snowbib import fetch
        self.write("a.md", note(title='"A"', status="to_read"))
        self.write("b.md", note(title='"B"', status="reference"))
        keys = [i["citekey"] for i in fetch.pending(self.vault, only_unscreened=True)]
        self.assertEqual(keys, ["a"])

    def test_a_landing_page_is_not_saved_as_a_pdf(self):
        """A publisher answering with HTML must not leave a corrupt .pdf behind."""
        from snowbib import fetch
        page = os.path.join(self.tmp, "landing.html")
        with open(page, "w", encoding="utf-8") as fh:
            fh.write("<html><body>Access denied</body></html>")
        dest = os.path.join(self.tmp, "x.pdf")
        with self.assertRaises(ValueError):
            fetch.download("file:///" + page.replace("\\", "/").lstrip("/"), dest)
        self.assertFalse(os.path.exists(dest))

    def test_a_real_pdf_is_saved(self):
        from snowbib import fetch
        src = os.path.join(self.tmp, "real.pdf")
        with open(src, "wb") as fh:
            fh.write(b"%PDF-1.4\n...body...")
        dest = os.path.join(self.tmp, "out.pdf")
        size = fetch.download("file:///" + src.replace("\\", "/").lstrip("/"), dest)
        self.assertTrue(os.path.exists(dest))
        self.assertEqual(size, os.path.getsize(dest))


class TestConvertWithoutDependency(unittest.TestCase):
    def test_missing_pymupdf_exits_with_instructions(self):
        import importlib
        from snowbib import convert
        try:
            importlib.import_module("pymupdf4llm")
            self.skipTest("pymupdf4llm is installed here")
        except ImportError:
            pass
        with self.assertRaises(SystemExit) as cm:
            convert._require_pymupdf()
        self.assertIn("pip install pymupdf4llm", str(cm.exception))


class TestResolverHook(unittest.TestCase):
    """The external-fetcher hook: snowbib ships none, so this is the seam."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="snowbib-test-")
        self.script = os.path.join(self.tmp, "resolver.py")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_resolver(self, payload):
        with open(self.script, "w", encoding="utf-8") as fh:
            fh.write("import sys\n"
                     "out = sys.argv[sys.argv.index('--output') + 1]\n"
                     f"open(out, 'wb').write({payload!r})\n")

    def _cmd(self):
        return f'"{sys.executable}" "{self.script}" --doi {{doi}} --output {{out}}'

    def test_a_pdf_from_the_hook_is_kept(self):
        from snowbib import fetch
        self._write_resolver(b"%PDF-1.4\nbody")
        dest = os.path.join(self.tmp, "out.pdf")
        size = fetch.run_resolver_cmd(self._cmd(), "10.1000/ok", dest)
        self.assertTrue(os.path.exists(dest))
        self.assertGreater(size, 0)

    def test_html_from_the_hook_is_deleted_not_kept(self):
        from snowbib import fetch
        self._write_resolver(b"<html>denied</html>")
        dest = os.path.join(self.tmp, "out.pdf")
        with self.assertRaises(ValueError):
            fetch.run_resolver_cmd(self._cmd(), "10.1000/ok", dest)
        self.assertFalse(os.path.exists(dest), "a non-PDF must not be left behind")

    def test_a_doi_that_is_not_one_never_reaches_the_process(self):
        from snowbib import fetch
        self._write_resolver(b"%PDF-1.4\n")
        for bad in ("10.1000/x & whoami", "not-a-doi", "10.1000/x; rm -rf /"):
            with self.assertRaises(ValueError) as cm:
                fetch.run_resolver_cmd(self._cmd(), bad, os.path.join(self.tmp, "o.pdf"))
            self.assertIn("unexpected shape", str(cm.exception))


class TestScihubAdapter(unittest.TestCase):
    """The submodule seam. No network: the client is stubbed."""

    def test_absent_submodule_explains_how_to_get_it(self):
        from snowbib import scihub
        real = scihub.VENDOR
        scihub.VENDOR = os.path.join(real, "definitely-not-here")
        try:
            self.assertFalse(scihub.available())
            with self.assertRaises(RuntimeError) as cm:
                scihub.fetch("10.1000/x", os.path.join(tempfile.gettempdir(), "x.pdf"))
            self.assertIn("git submodule update --init", str(cm.exception))
        finally:
            scihub.VENDOR = real

    def test_a_non_pdf_is_deleted_not_kept(self):
        from snowbib import scihub
        tmp = tempfile.mkdtemp(prefix="snowbib-test-")
        dest = os.path.join(tmp, "out.pdf")

        class FakeClient:
            @staticmethod
            def search_paper_by_doi(doi):
                return {"pdf_url": "https://example.invalid/x.pdf"}

            @staticmethod
            def download_paper(url, out):
                with open(out, "wb") as fh:
                    fh.write(b"<html>not a pdf</html>")
                return True

        real = scihub._load
        scihub._load = lambda: FakeClient
        try:
            with self.assertRaises(ValueError):
                scihub.fetch("10.1000/x", dest)
            self.assertFalse(os.path.exists(dest))
        finally:
            scihub._load = real
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_pdf_url_is_an_error_not_an_empty_file(self):
        from snowbib import scihub
        real = scihub._load
        scihub._load = lambda: type("C", (), {"search_paper_by_doi": staticmethod(lambda d: {})})
        try:
            with self.assertRaises(ValueError):
                scihub.fetch("10.1000/x", os.path.join(tempfile.gettempdir(), "y.pdf"))
        finally:
            scihub._load = real


class TestCuratedSelection(VaultCase):
    """Downloading what someone chose, not the first N alphabetically."""

    def test_citekeys_restrict_the_set(self):
        from snowbib import fetch
        for k in ("aaa2020first", "mmm2020middle", "zzz2020last"):
            self.write(k + ".md", note(title=f'"{k}"', oa_pdf='"https://x/y.pdf"'))
        keys = {i["citekey"] for i in fetch.pending(self.vault, keys={"zzz2020last"})}
        self.assertEqual(keys, {"zzz2020last"})

    def test_no_keys_means_everything(self):
        from snowbib import fetch
        self.write("a.md", note(title='"A"'))
        self.write("b.md", note(title='"B"'))
        self.assertEqual(len(fetch.pending(self.vault)), 2)

if __name__ == "__main__":
    unittest.main()
