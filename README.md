<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/snowbib-logo-dark.png">
    <img src="assets/snowbib-logo.png" alt="snowbib" width="420">
  </picture>
</p>

<p align="center">
  <strong>Turn a research field into a map you can actually read.</strong><br>
  One note per paper, the citation graph drawn for you, and an assistant that stops
  suggesting papers you already have.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-0a2540" alt="MIT">
  <img src="https://img.shields.io/badge/python-3.9%2B-0a2540" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/dependencies-none-4a90d9" alt="No dependencies">
  <img src="https://img.shields.io/badge/tests-23%20passing-4a90d9" alt="23 tests">
  <img src="https://img.shields.io/badge/status-alpha-8bb8e8" alt="Alpha">
</p>

---

## What this is

You pick a topic. snowbib asks [OpenAlex](https://openalex.org) — a free, open catalogue
of 250 million scholarly works — which papers belong to it, and writes one small note per
paper into a folder on your computer.

Then it does the part that matters: it looks up **which of those papers cite which**, and
draws the links. You open the folder in [Obsidian](https://obsidian.md) and your field is
a map.

<p align="center">
  <em>It works out a field's canon by counting, not by asking anyone's opinion.</em>
</p>

On a test run over *topological data analysis* — 159 papers, no human input — the papers
most cited by the collection turned out to be Edelsbrunner, Zomorodian & Carlsson and
Ghrist. Which is exactly right, and nobody told it so.

## Who it is for

Researchers who read with an AI assistant and are tired of it suggesting the same paper
for the third time. **You do not need to know how to program.** An AI assistant can
install and run all of this for you — see [Quick start](#quick-start-no-programming).

## What you get

| | |
|---|---|
| 📄 **A note per paper** | Title, authors, year, DOI, citation count, open-access link |
| 🔗 **The citation graph** | Who cites whom, as links you can click and see |
| 🕳️ **Your blind spots** | Papers your collection cites constantly that you never filed |
| 🚦 **A memory for your assistant** | Four answers to "do I already have this?" |
| 📁 **Plain files** | Markdown on your disk. No account, no lock-in, no database |

### The four answers

Whenever a paper turns up — in a search, a recommendation, a reference list — you ask
snowbib about it and get one of these:

| Answer | Meaning |
|---|---|
| ✅ `FILED` | You already have it. Move on. |
| 🗑️ `DROPPED` | You looked at it before and said no. |
| ⭐ `CITED x53` | **53 of your papers cite it and you never filed it.** Read this one. |
| 🆕 `NEW` | Genuinely unseen. Have a look. |

The starred one is the reason to bother. It is not a recommendation engine guessing what
you might like — it is a count of what the literature you already trust keeps leaning on.

---

## Quick start (no programming)

Twenty minutes, most of it waiting. You will not type a single command: your AI
assistant does that, you read what it says and answer.

### 1. Install three free things

| | What | Where |
|---|---|---|
| 🤖 | **Claude Desktop** — the app, not the website | [claude.ai/download](https://claude.ai/download) |
| 🗂️ | **Obsidian** — to read your vault | [obsidian.md/download](https://obsidian.md/download) |
| 🔧 | **Git** — only on Windows; macOS already has it | [git-scm.com/downloads/win](https://git-scm.com/downloads/win) |

On Windows, install Git with all the default options, then **close and reopen Claude
Desktop** so it notices. On macOS, skip it — if it turns out to be missing, Claude will
tell you what to do.

You also need **Python 3.9 or newer**. Do not go hunting for it: Claude checks and walks
you through it if it is missing.

### 2. Make an empty folder

Anywhere you keep your work. Call it something like `my-field-vault`. Your notes will
live there.

### 3. Set up Claude Desktop

Open it, go to the **Code** tab, and set four things before writing anything:

| Setting | Choose |
|---|---|
| **Environment** | `Local` |
| **Project folder** | the folder you just made |
| **Model** | any current Claude model |
| **Permission mode** | `Accept edits` |

### 4. Send it this

Copy the block below, **replace the two lines in capitals**, and send it.

```text
Please set up a snowbib vault in this folder by following the instructions at
https://github.com/carsanmilcar/snowbib/blob/master/AGENT-INSTALL.md

I don't program, so do everything yourself and explain each step in plain
language. Stop and ask me before anything slow or irreversible.

MY FIELD IS: persistent homology and topological data analysis
MY EMAIL IS: me@university.edu
```

That address is not a sign-up. OpenAlex asks who is calling so it can give you the fast
lane instead of the throttled one. It stays on your computer.

### 5. The one question that matters

Claude will tell you how many papers matched **before downloading anything**:

- **Under ~2,000** — comfortable, go ahead.
- **More than that** — your topic is too wide. Narrow it, or ask for only well-cited
  papers. Notes are easy to add later and tedious to delete.

### 6. Open it in Obsidian

Obsidian → **Open folder as vault** → pick your folder. That is the whole setup; there
is no import and no sync.

Click the graph icon in the left sidebar. Solid dots are papers you have; hollow ones are
papers yours cite that you have never filed. Those hollow dots are the point.

---

## Using it day to day

**"Do I already have this one?"**

> Ask your assistant: *Is this paper already in my vault? Check it with snowbib.*

**"What am I missing?"**

> *Show me the most co-cited papers that have no note, and add notes for the top 20.*

**"Read these properly for me."**

> *Run snowbib screen and follow its instructions.*

That last one prints a work order built to stay cheap: one assistant per paper, so no
paper's full text ever piles up in your conversation. snowbib itself never calls an AI
model — it only tells yours how to work.

---

## Honest limits

Read these before you trust it with something important.

- **Searching by words is blunt.** Looking for *persistent homology* also drags in a
  molecular-biology paper about a protein called CDYL1. Expect noise; deleting a note
  costs nothing.
- **OpenAlex knows the reference list of roughly half of all papers** — 54% in
  mathematics, 43% in earth sciences, and worse in some journals. Some of your notes will
  show no citations. That is the catalogue's limit, not a bug.
- **Matching titles is exact, not fuzzy.** A paper with no DOI whose title differs by a
  word can slip through as `NEW`.
- **Mathematicians:** OpenAlex has no MSC codes, so its idea of your subfield is coarser
  than zbMATH's. The `math` profile leaves an `msc` field for you to fill.
- **snowbib does not download papers.** Metadata and the citation graph only. PDFs are
  your business, through your library or the open-access links already in each note.

---

## Documentation

| Document | For |
|---|---|
| [AGENT-INSTALL.md](AGENT-INSTALL.md) | The AI assistant doing the installation |
| [REFERENCE.md](REFERENCE.md) | Commands, options, file formats, profiles |

## How it compares

Zotero, ResearchRabbit, Connected Papers and Litmaps all do parts of this, most of them
better. snowbib exists for one thing they do not do: your files stay plain markdown on
your disk, and your AI assistant gets a **mechanical** answer to "have I seen this
before" — an intersection of identifiers, not a model trying to remember your library and
inventing an answer when it cannot.

## License

MIT. See [LICENSE](LICENSE).
