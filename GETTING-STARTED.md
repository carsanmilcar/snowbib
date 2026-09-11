# Getting started — no programming needed

This guide is for researchers, not developers. You will not type a single command:
Claude does it, you read what it says and answer.

It takes about twenty minutes, most of it waiting.

---

## What you will end up with

A folder on your computer with one small note per paper in your field — title,
authors, DOI, how often it is cited, and **which papers cite which**. You open it
with [Obsidian](https://obsidian.md) (free) and it becomes a map of your field.
Your AI assistant can then read it, so it stops inventing references and stops
suggesting papers you already know.

---

## Step 1 — Install the two free things

1. **[Claude Desktop](https://claude.ai/download)** — the app, not the website.
2. **Git**:
   - **Windows**: [download Git for Windows](https://git-scm.com/downloads/win),
     install it with all the default options, then **close and reopen Claude Desktop**.
   - **macOS**: usually already there. Skip this; if Claude says it is missing,
     it will tell you what to do.

You also need **Python 3.9 or newer**. Do not go looking for it — Claude will check
in step 3 and walk you through it if it is missing.

## Step 2 — Make an empty folder

Anywhere you like. Call it something like `my-field-vault`. That is where your
notes will live, so put it wherever you keep your work — Documents is fine.

## Step 3 — Tell Claude what to do

Open Claude Desktop, go to the **Code** tab, and set four things before writing
anything:

| Setting | Choose |
|---|---|
| **Environment** | `Local` |
| **Project folder** | the folder you just made |
| **Model** | any current Claude model |
| **Permission mode** | `Accept edits` |

Then copy the text below, **replace the two lines in capitals**, and send it.

---

```
I want to set up a snowbib vault in this folder. I don't program, so please do
everything yourself and explain each step in plain language. Ask me before
anything that takes more than a few minutes.

MY FIELD IS: persistent homology and topological data analysis
MY EMAIL IS: me@university.edu

Please:

1. Check that Python 3.9+ is installed. If not, install it or tell me exactly
   what to download.
2. Clone https://github.com/carsanmilcar/snowbib into a subfolder called
   `snowbib-tool`, so the tool stays separate from my notes.
3. Create a `.env` file inside `snowbib-tool` containing SNOWBIB_MAILTO with my
   email. Explain to me why OpenAlex wants it.
4. Run `python -m snowbib.init` pointing at THIS folder as the vault, with
   `--profile math` if my field is mathematical, otherwise without a profile.
5. Run `python -m snowbib.discover --dry-run` with a query for my field and
   `--min-citations 20`. TELL ME HOW MANY PAPERS IT FOUND AND WAIT FOR MY ANSWER
   before downloading anything. If it is more than about 2000, suggest a narrower
   query first.
6. Once I agree, run it for real, then `python -m snowbib.cites` to reconstruct
   the citation graph, then `python -m snowbib.index`.
7. Show me the most co-cited papers that have no note of their own, and explain
   what that list means.
8. Tell me how to open the folder in Obsidian.
```

---

## Step 4 — What Claude will ask you

**"How many papers matched?"** — This is the one decision that matters. Under
about 2,000 is comfortable. If your query returns 20,000, the field is too wide:
narrow it, or raise `--min-citations`. Notes are cheap to add later and tedious to
delete.

**"Can I download them?"** — Yes. It is metadata only: no PDFs, no paywalls,
nothing that costs money. It comes from [OpenAlex](https://openalex.org), an open
catalogue of scholarly works.

---

## Step 5 — The interesting part

When it finishes, Claude will show you something like:

```
most co-cited: edelsbrunner2002topological x55, zomorodian2004computing x53,
               edelsbrunner2010computational x47, carlsson2009topology x44
```

Those are papers that **the papers in your field cite constantly and that you have
not filed**. Not somebody's opinion of what matters — a count of what your own
corpus leans on. It is the shortest useful reading list you will get.

Ask Claude: *"add notes for the top 20 most co-cited papers"* and it will.

## Step 6 — Using it from then on

Open the folder in Obsidian: `Open folder as vault`, pick your folder. The graph
view shows your field; hollow circles are papers cited but not filed.

Whenever you or your assistant find a paper, ask:

> Is this already in my vault? Check it with snowbib.

You will get one of four answers: `FILED` (you have it), `CITED x12` (twelve of
your papers cite it, you never filed it — probably worth reading), `DROPPED` (you
decided against it before), `NEW`.

To screen papers properly — reading them and filling in what each contributes —
ask Claude: *"run snowbib screen and follow its instructions"*. It prints a work
order designed to keep the cost low, and Claude follows it.

---

## Honest warnings

- **Text search is blunt.** Searching "persistent homology" also catches a
  molecular-biology paper about a protein called CDYL1. Expect some noise; delete
  those notes, it costs nothing.
- **OpenAlex knows the references of about half of all papers**, and less in some
  journals. Some notes will have no citations listed. That is the catalogue's
  limit, not a failure.
- **Mathematicians:** OpenAlex has no MSC codes, so its idea of your subfield is
  coarser than zbMATH's. The `math` profile leaves an `msc` field for you.
- **snowbib does not download papers.** It handles metadata and the citation graph.
  Getting PDFs is your business, through your library or the open-access links the
  notes already carry.
