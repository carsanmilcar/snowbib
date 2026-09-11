# Installation instructions for an AI assistant

**You are reading this because a researcher asked you to set up snowbib for them.**
Assume they do not program. Follow these steps in order, explain what you are doing in
plain language, and stop where this document tells you to stop.

## Ask for everything at once, in three lines

Three things you cannot invent. If any is missing, **your first reply asks for all of
them together and nothing else** — not a diagnosis, not a summary of this document, not a
list of what you have read. A researcher who said "set up snowbib for my field" wants a
question they can answer in one line, not a status report.

| What | Why you cannot guess it |
|---|---|
| **A permanent folder for the vault** | It is their data and they have to find it later. See step 0. |
| **A folder for the tool clone** | Must be separate from the vault. `Documents/snowbib-tool` is fine. |
| **An email address** | Required by OpenAlex before any search. Not a sign-up; stays in a local file. |

Offer defaults in the same breath, so they can just say yes: *"If you have no preference
I'll use `Documents/<field>-vault` and `Documents/snowbib-tool` — I just need your
email."*

Their **field** you can take from whatever they said, but you will search OpenAlex **in
English**, in the words a paper would put in its title. Show them the phrasing you used.

**To report a paper count before installing anything** — useful when they want to decide
first — open this and read `meta.count`:

```
https://api.openalex.org/works?filter=title_and_abstract.search:<their phrase>,cited_by_count:>19&per-page=1
```

Same number step 5 prints, nothing installed.

---

## Rules for this job

1. **Never invent a verdict.** If you want to know whether a paper is in the vault, run
   `check`. Do not answer from memory — you will be wrong and they will not be able to
   tell.
2. **Stop at step 5** and wait for a real answer before downloading anything. Getting
   this wrong wastes their time and fills their disk with notes they did not want.
3. **Never read a paper's full text into this conversation.** See [Screening](#screening).
4. **Report what actually happened**, including the counts snowbib prints. If something
   fails, say so and show the error; do not paper over it.
5. **When you are blocked, ask; do not report.** Stopping with a diagnosis of what the
   documentation requires is useless to someone who does not program. Name what you need
   in one short question and offer a default they can accept.
6. **The vault goes on their disk, not in yours.** If you run in a container, a sandbox or
   a per-session working directory, anything you create there is gone when the session
   ends. See step 0 before you create anything.
7. **You cannot use Obsidian for them.** It is a desktop app with no command line. Your
   job is to walk them through it, one instruction at a time, and wait.
8. **Do not save Obsidian for the end.** The moment the vault has its first notes, tell
   them how to open it, even if the conversation has gone somewhere else since. A vault
   they cannot look at is not a result. If the session drifts — they ask about a
   different paper, they tell you to stop running things — the Obsidian walkthrough is
   the one thing you still owe them.

---

## Step 0 — Decide where the vault lives. Ask, do not assume.

This is the step that goes silently wrong. The vault is **theirs**: it has to sit on their
own disk, in a folder they can still find months from now and open in Obsidian.

Ask them where to put it, and offer a sensible default — `Documents/my-field-vault` on
either platform. It must **not** be:

- a temporary or per-session directory: anything under `/tmp`, `%TEMP%`, `/var/folders`,
  or a working folder you created for this conversation
- inside a container or sandbox that does not map to their real filesystem
- inside the `snowbib-tool` clone

**If you are running in a sandbox with no access to their real disk, stop and say so
now.** Do not build a vault that will evaporate. Telling them the setup needs an assistant
with access to their filesystem is a useful answer; a vanished vault is not.

`init` prints a warning when the path looks temporary. Do not ignore it — confirm the
location with the user and start again in the right place.

## Step 1 — Check Python

```bash
python --version     # or python3 --version
```

Needs 3.9 or newer. If it is missing:

- **Windows** — point them at [python.org/downloads](https://www.python.org/downloads/)
  and tell them to tick **"Add python.exe to PATH"** on the first screen of the
  installer. That checkbox is the one everybody misses. They must reopen the app after.
- **macOS** — `brew install python` if they have Homebrew; otherwise the python.org
  installer.

## Step 2 — Clone the tool

Clone it into a **subfolder**, so the tool stays separate from their notes:

```bash
git clone https://github.com/carsanmilcar/snowbib snowbib-tool
```

Run every later command from inside `snowbib-tool`, pointing at the vault with
`--vault`. If `git` is missing on Windows, send them to
[git-scm.com/downloads/win](https://git-scm.com/downloads/win) and have them restart the
app afterwards.

## Step 2b — Install, in a virtual environment

```bash
cd snowbib-tool
python -m venv .venv
.venv/bin/python -m pip install -e .        # Windows: .venv\Scripts\python -m pip install -e .
```

From here on, **`PY` means `.venv/bin/python`** (`.venv\Scripts\python` on Windows).
Writing a bare `python` runs the system one, where snowbib is not installed and `convert`
cannot find its dependency.

**Use the venv, do not skip it.** On macOS with Homebrew and on most Linux distributions a
plain `pip install` fails with `externally-managed-environment` (PEP 668), because the
system Python refuses to be written to. Do not reach for `--break-system-packages`: create
the environment, and run every later snowbib command with `.venv/bin/python -m snowbib.…`
rather than a bare `python`.

This installs `pymupdf4llm`, needed only to turn downloaded PDFs into text. Everything
else — the vault, the citation graph, the filter — works without it, so if this step
fails, say so and carry on rather than stopping the setup.

## Step 3 — Configure the email

```bash
cp .env.example .env      # Windows PowerShell: copy .env.example .env
```

(You are already inside `snowbib-tool` from the previous step.)

Edit `.env` so it reads `SNOWBIB_MAILTO=their@address`. Explain why: OpenAlex gives
identified callers a faster, more reliable service, the file stays on their machine, and
it is git-ignored so it can never be committed.

## Step 4 — Create the vault

```bash
PY -m snowbib.init --vault <THE FOLDER FROM STEP 0>
```

Add `--profile math` if their field is mathematical, or `--profile nwp` for weather and
climate work. Profiles only decide which extra fields go in each note; if neither fits,
leave it out and write them one later.

Check the output names the right folder. The vault must **not** be inside `snowbib-tool`.

## Step 5 — Count before you fetch. STOP HERE.

```bash
PY -m snowbib.discover --vault <VAULT> --query "<their topic>" --min-citations 20 --dry-run
```

`--dry-run` writes nothing. Report the number to them in their own terms and wait:

| Matches | What to tell them |
|---|---|
| Under 2,000 | Comfortable. Ask if you should go ahead. |
| 2,000 – 10,000 | Large but workable. Suggest narrowing the phrase or raising `--min-citations`. |
| Over 10,000 | Too wide to be readable. Propose a narrower phrase and re-run the dry run. |
| Under 50 | **Check the language first.** See below. |

Pass `--query` several times to widen with alternative phrasings; they are unioned.
`--min-year` cuts off old work. **Do not proceed until they answer.**

**If the count is near zero, the query language is almost always the cause.** OpenAlex
indexes titles and abstracts overwhelmingly in English. A user describing their field in
Spanish, French, German or Portuguese will get nothing:

```
"mecanica cuantica supersimetrica"   ->     3 works
"supersymmetric quantum mechanics"   -> 3,046 works
```

Translate their field into the terms a paper would use **in its title**, show them the
translation you used, and re-run the dry run. Do not report "your field has no papers"
until you have tried it in English.

## Step 6 — Fetch

```bash
PY -m snowbib.discover --vault <VAULT> --query "<their topic>" --min-citations 20
PY -m snowbib.cites    --vault <VAULT>
PY -m snowbib.index    --vault <VAULT>
```

The middle command is the slow one — it asks OpenAlex for every paper's reference list
and can take several minutes on a few hundred notes. Warn them before starting, and do
not kill it; results are cached in `.snowbib/cache`, so a re-run is fast.

## Step 7 — Show them what came out

`cites` ends with a line like:

```
most co-cited: edelsbrunner2002topological x55, zomorodian2004computing x53, ...
```

Explain it properly, because it is the payoff: **those are papers their own collection
cites constantly and that are not in it**. Not a recommendation — a count. Offer to add
notes for the top ones:

```bash
PY -m snowbib.check --vault <VAULT> "<title or DOI>"     # confirm it is CITED, not FILED
PY -m snowbib.discover --vault <VAULT> --query "<exact title>" --limit 1
PY -m snowbib.cites --vault <VAULT> && PY -m snowbib.index --vault <VAULT>
```

## Step 8 — Walk them through Obsidian. You cannot do this part for them.

Obsidian is a desktop app: there is no command you can run, no file you can edit to do it
for them. Give these instructions one at a time, in plain language, and wait for them to
confirm each one. Assume they have never seen it.

1. **Install it** from [obsidian.md/download](https://obsidian.md/download) if they have
   not already. Free, no account, and it changes nothing — it just reads the folder you
   built.
2. **Open the vault.** On the welcome screen: *Open folder as vault* → choose **their
   vault folder**, giving them the exact path you used → *Open*. If it asks about trusting
   the folder, it is their own, so yes.
3. **Look at one note.** The file list is on the left. Click any paper: the metadata is at
   the top, then the summary, then its citations.
4. **Open the graph** — the circular icon in the left sidebar, or Ctrl/Cmd+G. Explain what
   they are looking at: each dot is a paper, each line a citation, **solid dots are papers
   they have and hollow dots are papers cited by theirs that have no note**. The hollow
   ones with many lines arriving are the reading list.
5. **Show them how to find things.** Ctrl/Cmd+Shift+F searches the whole vault;
   Ctrl/Cmd+O jumps to a note by name.

Tell them the folder is theirs and stays readable without any of this: plain markdown
files, no account, no sync, nothing that breaks if they stop using snowbib or Obsidian.
Backing it up means copying the folder.

Finish by telling them the three things they can ask you from now on: whether a paper is
already in their vault, what the most co-cited unfiled papers are, and to screen a batch.

---

## Afterwards

### Checking a candidate

```bash
PY -m snowbib.check --vault <VAULT> "10.1090/S0273-0979-09-01249-X" "Computing Persistent Homology"
```

Accepts DOIs, doi.org URLs, OpenAlex ids, citekeys and bare titles — as arguments or on
stdin, one per line. `--new-only` prints just the unknowns, which is what you want when
filtering a long search result.

Verdicts: `FILED` (has a note), `DROPPED` (buried in `.snowbib/excluded.json`),
`CITED xN` (N notes cite it, no note of its own), `NEW`.

If everything comes back `NEW`, the index is empty or you are pointing at the wrong
folder. Re-run `index` and read its warnings before believing the answer.

### Getting the papers themselves

```bash
PY -m snowbib.fetch   --vault <VAULT> --citekey KEY1 --citekey KEY2   # what they chose
PY -m snowbib.convert --vault <VAULT>
```

`fetch` downloads only the open-access versions OpenAlex knows about, into
`.snowbib/pdf/`. When the user has chosen which papers are worth reading, download exactly
those with `--citekey KEY` (repeatable) or `--from-file list.txt` — never `--limit N`,
which takes the first N alphabetically and has nothing to do with what they picked. It will report some papers as having no open version — that is expected,
not a failure, and you do not work around it: tell the user which ones and let them decide
whether to get them through their library.

`convert` turns the downloaded PDFs into `.snowbib/text/<citekey>.md`. Those text files
are what you hand to screening agents, one file each.

### Screening

```bash
PY -m snowbib.screen --vault <VAULT> --limit 20
```

This prints a work order; snowbib never calls a model itself. Follow it exactly, and in
particular: **one sub-agent per paper**, each reading only its own paper and reporting
back a filled note. A paper's text is 12–25k tokens and a filled note is about 600. If
you read the papers yourself in the main conversation, you will burn through their quota
for no benefit and lose the thread. Screen from abstracts first; fetch a PDF only for
papers that survive.

After editing notes, re-run `index` so `check` sees the changes.

### Keeping it current

Re-run `discover` with the same query later and it skips everything already filed.
`cites` and `index` after that. To bury papers they rejected, add them to
`.snowbib/excluded.json` as `{"ids": ["W..."], "dois": ["10..."]}` so they come back
`DROPPED` instead of `NEW`.

---

## Things that go wrong

| Symptom | Cause and fix |
|---|---|
| `SNOWBIB_MAILTO is unset or malformed` | No `.env`, or it has no valid address. Step 3. |
| `no papers directory at ...` | Wrong `--vault`, or `init` never ran. Step 4. |
| `WARNING this vault is being created at ...` | You are building in a scratch, sandbox or session folder. Stop, agree a real location with the user, start again. Step 0. |
| `WARNING the index has no notes` | Pointing at the wrong folder, or the vault is genuinely empty. Never report verdicts from an empty index. |
| Everything comes back `NEW` | Same cause as above, nine times out of ten. |
| `matches : 0` or a handful | The query is probably not in English. Translate it and re-run. Never conclude the field is empty from a non-English phrase. |
| `refuses: N matches is too broad` | Working as intended. Narrow the query; do not reach for `--limit` to force it. |
| `no note has an openalex_id` | `cites` ran before `discover`. Order matters. |
| Notes exist but have no citations | Normal: OpenAlex publishes reference lists for about half of all works. Not a bug, do not retry. |
| Unicode errors on Windows | Set `PYTHONIOENCODING=utf-8` before the command. |
| `error: externally-managed-environment` | The system Python refuses global installs. Create the venv from step 1b; never pass `--break-system-packages`. |
| `discover` returns 0 with several `--query` | Fixed: they are unioned now. If an old clone, `git pull`. |

## What not to do

- Do not edit anything inside `.snowbib/` by hand except `excluded.json`. The rest is
  generated and will be overwritten.
- Do not commit the vault into the `snowbib-tool` clone. They are separate on purpose.
- Do not put the user's email anywhere except `.env`.
- Do not tell them a paper is or is not in their vault without running `check`.
