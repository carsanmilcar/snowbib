# Installation instructions for an AI assistant

**You are reading this because a researcher asked you to set up snowbib for them.**
Assume they do not program. Follow these steps in order, explain what you are doing in
plain language, and stop where this document tells you to stop.

Two things you need from them. Ask now if you do not have both:

- **Their field**, as they would describe it to a colleague.
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

---

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
python -m snowbib.init --vault <THE FOLDER THEY CHOSE>
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
| Under 50 | Probably too narrow or a typo. Offer a broader phrase. |

Pass `--query` several times to widen with alternative phrasings; they are OR-ed.
`--min-year` cuts off old work. **Do not proceed until they answer.**

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

Then tell them how to open the folder in Obsidian: **Open folder as vault**, pick the
folder, click the graph icon. Solid dots are filed papers, hollow ones are cited but
unfiled.

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
| `WARNING the index has no notes` | Pointing at the wrong folder, or the vault is genuinely empty. Never report verdicts from an empty index. |
| Everything comes back `NEW` | Same cause as above, nine times out of ten. |
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
