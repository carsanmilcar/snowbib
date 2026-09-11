# Installation instructions for an AI assistant

**You are reading this because a researcher asked you to set up snowbib for them.**
Assume they do not program. Follow these steps in order, explain what you are doing in
plain language, and stop where this document tells you to stop.

Two things you need from them. Ask now if you do not have both:

- **Their field.** Whatever language they answer in, you will search OpenAlex **in
  English**, using the words a paper would put in its title. See step 5.
- **An email address**, for OpenAlex's polite pool. It is not a sign-up and it never
  leaves their machine. Tell them that when you ask.

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
5. **The vault goes on their disk, not in yours.** If you run in a container, a sandbox or
   a per-session working directory, anything you create there is gone when the session
   ends. See step 0 before you create anything.
6. **You cannot use Obsidian for them.** It is a desktop app with no command line. Your
   job at the end is to walk them through it, one instruction at a time, and wait.

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

No other dependencies exist. Do not create a virtualenv, do not run pip install for
requirements: there are none.

## Step 2 — Clone the tool

Clone it into a **subfolder**, so the tool stays separate from their notes:

```bash
git clone https://github.com/carsanmilcar/snowbib snowbib-tool
```

Run every later command from inside `snowbib-tool`, pointing at the vault with
`--vault`. If `git` is missing on Windows, send them to
[git-scm.com/downloads/win](https://git-scm.com/downloads/win) and have them restart the
app afterwards.

## Step 3 — Configure the email

```bash
cd snowbib-tool
cp .env.example .env      # Windows PowerShell: copy .env.example .env
```

Edit `.env` so it reads `SNOWBIB_MAILTO=their@address`. Explain why: OpenAlex gives
identified callers a faster, more reliable service, the file stays on their machine, and
it is git-ignored so it can never be committed.

## Step 4 — Create the vault

```bash
python -m snowbib.init --vault <THE FOLDER FROM STEP 0>
```

Add `--profile math` if their field is mathematical, or `--profile nwp` for weather and
climate work. Profiles only decide which extra fields go in each note; if neither fits,
leave it out and write them one later.

Check the output names the right folder. The vault must **not** be inside `snowbib-tool`.

## Step 5 — Count before you fetch. STOP HERE.

```bash
python -m snowbib.discover --vault <VAULT> --query "<their topic>" --min-citations 20 --dry-run
```

`--dry-run` writes nothing. Report the number to them in their own terms and wait:

| Matches | What to tell them |
|---|---|
| Under 2,000 | Comfortable. Ask if you should go ahead. |
| 2,000 – 10,000 | Large but workable. Suggest narrowing the phrase or raising `--min-citations`. |
| Over 10,000 | Too wide to be readable. Propose a narrower phrase and re-run the dry run. |
| Under 50 | **Check the language first.** See below. |

Pass `--query` several times to widen with alternative phrasings; they are OR-ed.
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
python -m snowbib.discover --vault <VAULT> --query "<their topic>" --min-citations 20
python -m snowbib.cites    --vault <VAULT>
python -m snowbib.index    --vault <VAULT>
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
python -m snowbib.check --vault <VAULT> "<title or DOI>"     # confirm it is CITED, not FILED
python -m snowbib.discover --vault <VAULT> --query "<exact title>" --limit 1
python -m snowbib.cites --vault <VAULT> && python -m snowbib.index --vault <VAULT>
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
python -m snowbib.check --vault <VAULT> "10.1090/S0273-0979-09-01249-X" "Computing Persistent Homology"
```

Accepts DOIs, doi.org URLs, OpenAlex ids, citekeys and bare titles — as arguments or on
stdin, one per line. `--new-only` prints just the unknowns, which is what you want when
filtering a long search result.

Verdicts: `FILED` (has a note), `DROPPED` (buried in `.snowbib/excluded.json`),
`CITED xN` (N notes cite it, no note of its own), `NEW`.

If everything comes back `NEW`, the index is empty or you are pointing at the wrong
folder. Re-run `index` and read its warnings before believing the answer.

### Screening

```bash
python -m snowbib.screen --vault <VAULT> --limit 20
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

## What not to do

- Do not edit anything inside `.snowbib/` by hand except `excluded.json`. The rest is
  generated and will be overwritten.
- Do not commit the vault into the `snowbib-tool` clone. They are separate on purpose.
- Do not put the user's email anywhere except `.env`.
- Do not tell them a paper is or is not in their vault without running `check`.
