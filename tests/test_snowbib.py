"""Tests for snowbib. Run: python -m unittest discover -s tests

Every case here is a bug that shipped once: front matter that is not double
quoted, counting link occurrences instead of citing notes, a vault path with
brackets, notes without front matter.
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


if __name__ == "__main__":
    unittest.main()


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

    def test_several_queries_are_or_ed(self):
        from snowbib import discover
        self.assertIn(" OR ", discover.build_filter(["a", "b"]))


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
