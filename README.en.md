# Franklin Writing

### A measured study, and the tool it decided

**From a controlled experiment with 5 independent LLM judges, 18 anonymized text blocks, and a pre-registered decision rule:**

> **Discriminating power came 100% from "does it contain an obvious defect" and 0% from "does it sound like the author".**

| Metric | Result |
| --- | --- |
| Real text misjudged as imitation | **0%** |
| Imitations with an injected defect, detected | **100%** |
| **Imitations with no injected defect, detected** | **0%** |

**So this tool does not score, does not evaluate, and never says whether your writing "sounds like the author".** It does one thing: it puts the right actions of the Franklin method in the right order — splitting, hinting, hiding, delaying, recording — and leaves all understanding and all judgment to you.

**Full study (every figure recomputable):** [English](docs/research/) · [中文](docs/研究/) · [One-page conclusion](docs/research/llm-authorship-judgment.md) · [All measured data](docs/research/appendix-measured-data.md) · [Decision report](docs/research/why-no-llm-judgment.md)

[中文](README.md) · [Roadmap](ROADMAP.en.md) · [Changelog](CHANGELOG.en.md) · [Contributing](CONTRIBUTING.en.md)

> **Note on language.** The tool's interface is in Chinese, because the method is being applied to Chinese prose. Every document in this repository now has an English version; the interface strings do not yet.

<!-- badges -->
[![Tests](https://github.com/luluxiuc/Franklin-Writing/actions/workflows/test.yml/badge.svg)](https://github.com/luluxiuc/Franklin-Writing/actions/workflows/test.yml)
[![License: PolyForm Noncommercial](https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-blue)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Zero dependencies](https://img.shields.io/badge/dependencies-stdlib%20only-success)](#quick-start)
[![Works offline](https://img.shields.io/badge/offline-works-success)](#what-it-does-not-do)

---

## Contents

- [The study: can an LLM judge "sounds like the author"?](#the-study-can-an-llm-judge-sounds-like-the-author)
- [What this tool does](#what-this-tool-does)
- [Quick start](#quick-start)
- [How to use it](#how-to-use-it)
- [How the hints stay cheap and leak nothing](#how-the-hints-stay-cheap-and-leak-nothing)
- [What it does not do](#what-it-does-not-do)
- [Repository layout](#repository-layout)
- [Where your data lives](#where-your-data-lives)
- [Tests](#tests)
- [Limitations of this research](#limitations-of-this-research)
- [Contributing](#contributing)
- [License](#license)

---

## The study: can an LLM judge "sounds like the author"?

This project originally had an "author similarity" scoring and gap-diagnosis engine at its core: you imitate a passage, and the AI tells you where you don't sound like the author, why, and what to fix next.

**We measured it and deleted the entire engine. Not because it performed poorly, but because it turned out to be doing something different from what it claimed to do.**

### Experiment 1: a controlled judge experiment

| Item | Detail |
| --- | --- |
| Material | 8 real published prose passages + 10 AI imitations (5 with no injected defect, 5 with one named defect each), presented as 18 anonymized blocks in fixed-seed shuffled order |
| Presentation | No author name, no reference original |
| Protocol | Explicit instruction "do not assume who the author is"; evidence must point at concrete language facts; a verdict of "imitation" must quote the most suspicious fragment |
| Judges | 5 independent LLM instances, identical protocol |
| Decision rule | **Frozen before any result was seen** → [`PREREGISTRATION.json`](docs/research/experiment-data/PREREGISTRATION.json) |

**Per-block votes** (all 18 rows):

| Block | Truth | Type | J1 | J2 | J3 | J4 | J5 | Agreement |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | imitation | defective | B | B | B | B | B | unanimous |
| 2–5 | real | — | A | A | A | A | A | unanimous |
| 6 | imitation | defective | B | B | B | B | B | unanimous |
| **7** | **imitation** | **clean** | A | **B** | **B** | A | A | **split** |
| 8 | imitation | defective | B | B | B | B | B | unanimous |
| **9** | **imitation** | **clean** | A | A | **B** | A | A | **split** |
| 10 | real | — | A | A | A | A | A | unanimous |
| **11** | **imitation** | **clean** | A | **B** | **B** | A | A | **split** |
| 12 | real | — | A | A | A | A | A | unanimous |
| **13** | **imitation** | **clean** | A | **B** | **B** | A | A | **split** |
| 14 | imitation | defective | B | B | B | B | B | unanimous |
| **15** | **imitation** | **clean** | A | A | **B** | A | A | **split** |
| 16 | imitation | defective | B | B | B | B | B | unanimous |
| 17–18 | real | — | A | A | A | A | A | unanimous |

**Inter-judge unanimity: 13/18 = 72%. Disagreement fell 100% on the "clean imitation" blocks — the only category that matters.**

**Per-judge cross-tabulation:**

| Judge | Real→A | Real→B | Imit→B | Imit→A | Clean caught | Overall |
| --- | --- | --- | --- | --- | --- | --- |
| J1 | 8/8 | 0/8 | 5/10 | 5/10 | **0/5** | 13/18 |
| J2 | 8/8 | 0/8 | 8/10 | 2/10 | 3/5 | 16/18 |
| J3 | 8/8 | 0/8 | 10/10 | 0/10 | 5/5 | 18/18 |
| J4 | 8/8 | 0/8 | 5/10 | 5/10 | **0/5** | 13/18 |
| J5 | 8/8 | 0/8 | 5/10 | 5/10 | **0/5** | 13/18 |

### The problem is not inaccuracy — it is that the errors point one way

Inaccuracy is just noise. What made us delete the engine is this: **the judges rejected the author's own signature devices.**

| The judge's stated reason | The fact |
| --- | --- |
| "Merely a meta-statement about memory" is a flaw; real writing would describe the thing itself | This author uses meta-statements constantly: "the rest I can't recall, can't count them out", "perhaps *twelve red* is just a name", "this point I am not misremembering" |
| "The rhythm is carried by mood rather than information" | The same criterion would condemn confirmed-authentic passages by this author: "some look stupid, some look elegant", "eating it plain is fine too" |
| "In reality a spool holds only one color of thread — a flaw from inexperience with physical objects" | **A misreading of the text** (the original has two spools). The judge **fabricated textual evidence** to support a style judgment |
| "The ending leaves a blank; the sentiment arrives too punctually" | Structurally identical to this author's own closings: "I didn't ask either", "eating it plain is fine too" |
| "Dropping the possessive particle is a deliberately manufactured rupture" | Judging precise language as manufactured rupture |

Wire that feedback into a training loop and here is what a user does: **delete "I didn't ask either", fill the blank with an explanation, add subjects and connectives.**

**They become a competent, ordinary writer — not the author they set out to learn from.**

### The errors are not hedged

The 3 judges whose per-block verdicts were archived (J1, J3, J5) produced 45 verdicts in total, **10 of them wrong — all at self-reported confidence ≥ 4**, one at the maximum of 5.

| Group | n | Correct | Mean confidence when correct | Mean confidence when wrong |
| --- | --- | --- | --- | --- |
| A real | 24 | 24/24 | 4.88 | — |
| B clean imitation | 15 | 5/15 | 3.80 | **4.10 (n=10)** |
| B defective imitation | 15 | 15/15 | 4.80 | — |

**So "just filter out the low-confidence judgments" is not an escape route either.** Recompute with `python docs/research/experiment-data/confidence_stats.py`.

### The obvious alternative explanation is ruled out

| Group | Concrete-noun density | Verb density | Connectives | Emotion words | Mean chars |
| --- | --- | --- | --- | --- | --- |
| A real (8) | 4.7 | 4.1 | 0.39 | 0.25 | 87.8 |
| Clean imitation (5) | **9.2** | **6.2** | 0.00 | 0.00 | 59.4 |
| Defective imitation (5) | 2.4 | 1.1 | **4.38** | **1.40** | 73.0 |

**The imitations have a *higher* concrete-noun density than the originals (9.2 vs 4.7)**, so "the judges just found them thin" does not hold. The only mechanically separable features are **connectives and emotion words**: high in the defective group, zero in the clean group — and zero in the real passages too.

**The conclusion tightens to: the judges reliably detect explicitly injected defect markers. Once an imitation matches the original on those two features, attribution drops to chance.**

### Purely computational findings (zero model calls)

Corpus: one real 1,351-character prose piece.

| Metric | Measured |
| --- | --- |
| Sentence length | mean **17.8** chars, SD 10.0, min 1, max 43 |
| Clause length | mean **7.5** chars, SD 3.8 |
| **Longest run of consecutive short sentences (≤8 chars)** | **2** |
| Connective density | **0.74 per 100 chars** |
| Concrete nouns | 47 distinct types, 165 occurrences (≈1 object every 8 chars) |
| Comma density | 6.9 per 100 chars (comma:period ratio 1.48) |
| Emotion words | only 2, and **neither states an emotion** |

**Two common assumptions the measurements killed:**

- **"This author favors short sentences" is false.** Mean sentence length 17.8 characters; longest run of short sentences is 2. At the sentence level the rhythm is not clipped at all. The real feature is one level down (mean clause length 7.5). Train against "short sentences" and you are pointing the wrong way from the start.
- **"He avoids emotion words" is imprecise.** There are exactly two instances of the word "happy", one negated and one as an adverbial clause ("whenever the child got *happy*…"). **Neither uses emotion as the predicate.** The accurate statement is: *he does not use emotion words as the main-clause predicate.*

**The same batch of hand-written threshold rules also produced four structural false positives**: flagging the author's own original text as "deviating from the author"; sampling at the wrong level; treating a low-frequency feature as a per-passage requirement; and **scoring a passage that was measurably closer to the author's fingerprint no better than a badly-written one**. None of these can be fixed by tuning thresholds — they are modelling errors, not parameter errors.

### Why a stronger model does not fix this

A model never compares *your text* against *the author*. It compares *your text* against *its understanding of the author*. That gap does not close as models improve — **a stronger model produces a finer-grained proxy, and a finer-grained proxy is still a proxy.**

Four structural reasons on top of that:

1. **The description itself can point at the wrong level.** Even the most natural first impression — "this author favors short sentences" — was false.
2. **A reader with only the text in front of them cannot see much of what determines "sounding like" someone** (the choices the author didn't make, who they were in conversation with, what they deliberately avoided). **Some disagreements are not model failures; they are task failures.**
3. **The remaining subjective layer is unstable even between humans**, and the disagreement concentrates exactly on "competent writing that may or may not be the author" — which is every text a learner will ever produce.
4. **The cost of error is asymmetric.** Get it right: a useful hint. Get it wrong: the user deletes a correct device, **and the loss is irreversible and invisible to them.**

> **In the business of teaching someone to write, wrong guidance is worse than no guidance.**

Deleting the judgment costs nothing, because the Franklin method's engine was never the judgment. It is the *actions*: read, reconstruct away from the source, delay, compare side by side. Franklin himself worked exactly this way — **his critic was himself.**

### Read the full study

| What you want | English | 中文 |
| --- | --- | --- |
| Full reasoning, costs, follow-ups | [decision report](docs/research/why-no-llm-judgment.md) | [决策报告](docs/研究/为什么不做LLM判断评分.md) |
| The whole conclusion (three layers decomposed) | [research conclusion](docs/research/llm-authorship-judgment.md) | [研究结论](docs/研究/LLM能否判断像不像作者.md) |
| Where every number comes from (recomputable) | [measured data](docs/research/appendix-measured-data.md) | [实测数据汇总](docs/研究/附录-实测数据汇总.md) |
| Per-block votes and cross-tabs | [experiment 1 results](docs/research/experiment-1-final-results.md) | [实验一最终结果](docs/研究/实验一最终结果.md) |
| Experiment 2 design (not run) | [experiment 2 design](docs/research/experiment-2-design.md) | [实验二设计](docs/研究/实验一结果与实验二设计.md) |
| Raw material and every script | [`docs/research/experiment-data/`](docs/research/experiment-data/) | [`docs/研究/实验数据/`](docs/研究/实验数据/) |

**The corpus is not distributed with this repository** (published, copyrighted work). The material-construction script `build_material.py` records every parameter including the fixed shuffle seed, so the blocks can be rebuilt from it.

---

## What this tool does

**It turns the Franklin method into a workflow you can actually keep up. The system handles splitting, hinting, hiding, delaying, recording; all understanding and all judgment stay with you.**

Import an essay or a book. Read the original. Wait a few minutes. Rewrite it from memory. Then see your version and the original side by side, sentence by sentence.

| | The system handles | You handle |
| --- | --- | --- |
| Splitting | Chapters (reading units) and passages (practice units), losslessly — not one character lost | Confirming or re-splitting |
| Hints | One short hint **per sentence**, batch-warmable in the background | Using them as a foothold, or turning them off |
| Hiding | Not a single character of the original appears during the writing phase | — |
| Delay | Enforced wait between finishing reading and being allowed to write (default 3 min, 0–240) | Waiting, or practising another passage |
| Comparison | Sentence-paired LCS alignment, mechanical hit/miss marking | **Reading it yourself and saying what you see** |
| Records | Per-sentence notes, whole-passage observations, every draft — all local | Writing them down |

**Key design decisions:**

- **Hints are per sentence, not per paragraph.** This is what Franklin actually did — he wrote *short hints of the sentiment of each sentence*, waited a few days, and rebuilt the whole piece from those hints. It is also what the exercise trains: writing each sentence well. A paragraph summary reorganises the original, and that structure belongs to the model, not to you.
- **A hint says what the sentence is about — never the wording, never a technique, never an evaluation.** And the tool checks mechanically: any hint containing 8 or more consecutive characters identical to the source is dropped.
- **Comparison aligns by longest common subsequence, not by index.** Skip one sentence and index pairing misreports everything after it — worse than showing nothing.
- **The delay sits between reading and writing.** Write immediately and you write the afterimage in your eyes; wait a few minutes and you write what you actually retained.
- **Notes belong to the book, not to a single round.** Single-sentence notes and the closing observation go into one list, tagged "sentence n" or "whole passage".

---

## Quick start

Requires **Python 3.10 or newer**. **No other dependencies** — no `pip install`, no Node, no network needed to run.

```bash
git clone https://github.com/luluxiuc/Franklin-Writing.git
cd Franklin-Writing
python app/fk_server.py
```

The browser opens `http://127.0.0.1:8137` automatically.

On **Windows** you can also double-click `启动.cmd`; on **macOS / Linux** run `./启动.sh`.

Common options:

```bash
python app/fk_server.py --port 9000          # port (default 8137; auto-increments if taken)
python app/fk_server.py --data ./my-library  # data directory
```

The server binds to `127.0.0.1` only — other machines on your LAN cannot reach it.

### Optional: add an API key

Open Settings, pick a provider, paste a key, hit **Test connection**.

- Works with DeepSeek, OpenAI, Qwen, Kimi, Zhipu, OpenRouter, local Ollama, and any OpenAI-compatible endpoint.
- The key is stored only in `app/data/index.json` on your machine. It is never uploaded.
- **The tool works without a key** — you just get no hint cards and write purely from memory. **That is arguably closer to Franklin's original method.**
- Keys containing non-ASCII characters or spaces (common when copy-pasting from a web page) are rejected immediately with a readable message, instead of failing later with an incomprehensible codec error.

---

## How to use it

### 1. Import something

Click **Import a book** on the shelf. Give a path to a local `.txt` / `.md` file, or just paste the text in.

The tool splits it into **chapters** (reading units) and **passages** (practice units), ~300 characters per passage by default, adjustable. Importing normalizes whitespace only (collapsing runs of spaces, at most one blank line) — **not one content character is touched**, and "concatenating the passages reproduces the source exactly" is a hard assertion in the test suite.

### 2. Read the original

Open any passage from the chapter contents. The full text is in front of you.

### 3. Wait a few minutes

Click **Done reading — go write this passage**. The original closes and the countdown starts.

> Those minutes are the heart of the method. You can practise other passages while you wait — the chapter contents show the state of every passage, so waiting time is never wasted.

### 4. Hints on the left, paper on the right, original nowhere

When the countdown ends you land on the writing desk. **Not one character of the original is on this page.**

On the left, one hint per sentence — as many hints as the original has sentences.

```
1  about the several Dragon Boat Festival customs back home
2  lists practices like tying the five-colour cord and making scent sachets
3  the origin of the charm, and the relationship between that Daoist and the author
```

If you can't remember, leave it blank — don't invent. Press `Ctrl+Enter` or click **Done — compare**.

**To drill one sentence at a time**, click **Practise sentence by sentence** at the top of the hint column. Read one hint, write only that sentence, and it appears immediately beside the corresponding original sentence, with the words you did produce highlighted.

### 5. Compare, sentence by sentence

The moment you submit, the page becomes a paired view: **each original sentence** directly above **the sentence you wrote**, with that sentence's hint attached to the pair. Anything extra or missing is marked separately.

Below that:

- Words you did produce are highlighted (present in the original, present in yours).
- **Fragments present in the original but absent from your draft** are listed verbatim, with no evaluation.
- Expand **by word** for a token-level view.

Finally, write one line under **What I noticed**. One line is enough — "I dropped the causal link in sentence two", "I merged three short clauses into one long sentence". It goes into this book's notes.

---

## How the hints stay cheap and leak nothing

"Call an LLM" is the easiest way to build a quietly expensive product. Every item below exists to close that hole.

| Mechanism | How |
| --- | --- |
| **Each text is generated once** | The cache key is **content hash + model name + prompt version** — independent of which book, chapter, or passage the text sits in. The same text used twice is read locally; a paragraph repeated inside a book is generated once; switching models or editing the prompt invalidates the cache automatically. |
| **Pre-warm instead of waiting** | **Prepare in advance** batch-generates hints for a whole book in the background (concurrency 2 by default; `FK_LLM_CONCURRENCY`, set to 1 on tight free tiers). By the time you reach a passage, the hints are already local — **no model wait during practice.** |
| **Count is set by sentence count; length is capped** | One hint per source sentence, so **the model does not decide how many hints you get.** Per-hint cap: 22 chars for ≤4 sentences, 18 for ≤8, 15 beyond that. Output tokens are bounded by *sentences × cap*. |
| **Quote the cost before spending** | Batch warming shows how many passages remain and roughly how many tokens it will take, and asks again above a threshold. The figure is explicitly labelled an **estimate**. |
| **The ledger records real numbers only** | Settings shows the `usage` the provider **returned**. If it isn't available, the tool records 0 and says so — **no estimating, no pretending to know.** You can reconcile it against your bill. |
| **Hints that copy the source are stripped** | Every hint is checked mechanically: any hint containing 8 or more consecutive characters identical to the source is removed. Two attempts both copying, and you get none. **This is not only about cost — the moment a hint hands you the original's words, you are no longer writing from memory and the exercise is void.** |
| **Very short passages are skipped** | Under 40 characters, batch generation is skipped: not worth the call, and you'd remember it anyway. |

---

## What it does not do

- **No scoring.** No scores, no similarity, no "sounds like the author", no ranking, no levels.
- **No evaluation of your draft.** No "you should change this", no advice.
- **No writing for you.** Apart from one hint per sentence, it generates no prose.
- **No progress report.** It shows raw records; you find the patterns.
- **No network** unless you enable hints. Sources and drafts never leave the machine.

The comparison page does exactly one thing: it puts two texts and one mechanical diff in front of you. **The judgment is yours.**

---

## Repository layout

```
启动.cmd / 启动.sh          launchers (double-click)
app/
  fk_store.py               data layer: splitting (chapter/passage), store, state machine, notes
  fk_llm.py                 talking to the model: the per-sentence prompt, quotas, readable errors
  fk_summary.py             hint cache, token ledger, batch warming, copy detection
  fk_core.py                pure functions for splitting and comparison (LCS alignment, leak scan)
  fk_server.py              local HTTP server + built-in self-checks
  web/                      frontend: shelf / reading / writing desk / sentence drill / comparison
  data/                     your books, drafts, notes, hint cache (not in the repo)
tests/                      seven suites + a stub-model server + repository self-checks
docs/
  research/ 研究/            the study and all measured data (English / 中文)
  design/ 设计/              methodology, no-judgment design, user guide (English / 中文)
_capability/                experiment material, judge verdicts, analysis scripts
_probe/                     development-time probe scripts
_extract/                   extracted text of the three original input documents (where it started)
fk_tool/                    the CLI prototype the web version replaced (kept for record, unmaintained)
```

---

## Where your data lives

Everything is under `app/data/`:

```
app/data/
  index.json        library, every draft, observations, notes, settings (incl. API key)
  index.json.bak    previous version, in case a write goes wrong
  texts/<id>.txt    each book's source text, one file each
  summaries.json    hint cache (plain text; deleting it loses nothing else)
```

All plain text. Open it, copy it, back it up; move the whole `app/data` directory to another machine and carry on.

**Delete that directory and nothing about you remains in this tool.**

Each practice round can also be exported to Markdown, and notes export in one click.

---

## Tests

```bash
python tests/run_all.py
```

| Suite | What it checks |
| --- | --- |
| Data layer | Splitting is reversible (not one character lost), hard-cut fallback, store I/O, state machine |
| Hint cards | Per-sentence count alignment, cache hits, ledger truthfulness, batch warming, bad-key handling, copy detection |
| Server | End-to-end HTTP; **no endpoint returns the source during the writing phase**; notes bound to books |
| Frontend contract | Every element and endpoint the JS references actually exists (guards against "I clicked it and nothing happened") |
| Buttons actually work | Renders the templates, finds every button, clicks it, asserts state changed |
| Typing animation | Only committed text animates, the modes are genuinely different, cost does not grow with document length, attaches and detaches |
| Frontend rendering | Runs every page's render path under Node against real API data |

**378 checks** (the number the runner itself reports). The runner starts its own stub-model server for the rendering checks and shuts it down afterwards — no manual setup, and no real model calls (so it never costs money).

There is also a **repository self-check** (`python tests/docs_check.py`) for dead links, leaked keys, private data and unparseable JSON. CI runs both.

A few self-checks are worth calling out, because **each one caught a real bug during development**:

- **Before returning, the writing-phase endpoints re-scan their own payload against the source** and refuse to serve if anything looks like a leak. This caught a chapter title — derived from the source's first sentence — being displayed in the practice page header, handing the user the opening of the passage they were about to write.
- **The same check caught the model pasting a whole source sentence into a hint.** That is now stripped at generation time.
- **Hard-cut fallback:** pasting 2,000 characters with no sentence punctuation used to produce a single "passage", meaning one practice round had to memorise 2,000 characters. It now splits inside the run on soft punctuation, then by character count.
- **Buttons actually being clickable:** two consecutive attempts to fix the animation buttons failed because the tests verified "the data differs" rather than "the click reaches the code". That is now a hard assertion.

---

## Limitations of this research

**We list the problems in our own study, because a project that claims to be honest cannot report only the favourable data.**

| Limitation | Detail | Status |
| --- | --- | --- |
| **Human agreement was never measured** | All judges are LLMs, which is circular — this measures self-consistency, not agreement with human experts. The tooling exists (`docs/research/experiment-data/human_kit.py`); **it needs 3+ qualified readers to each annotate once.** | Open |
| **The retrieval channel was not removed** | 3 of 5 judges violated the protocol and looked up the source. **So "0% misjudgment on real text" cannot be credited purely to style recognition** — and the real use case is precisely non-canonical text. | Open |
| **The same-length paired test failed** | With lengths strictly matched, the judge's stated reason was "passage B is verbatim identical to the original, i.e. an excerpt", with a citation link — it bypassed style comparison. | Recorded |
| **Experiment 2 (single-sentence discrimination) is designed but not run** | Pair an author's real sentence against a rewrite with identical content, length and objects, varying only the *writing*. | Open |
| **The experimenter built the materials *and* designed the study** | The imitations carry the experimenter's own fingerprint; there is no way to separate "recognised the author's hand" from "recognised the experimenter's hand". | Structural |
| **Small sample** | 18 blocks, 5 judges — directional conclusions only, not a precise ceiling on ability. | Recorded |
| **The pre-registered rule missed the real failure mode** | Its trigger was "misjudgment rate on real text ≥ 37.5%"; measured 0%, so it never fired. The actual failure was accepting competent imitations. | Recorded |
| **The raw logs were not all kept** | Per-block verdicts survive for only 3 of the 5 judges, and the verdict values were hand-transcribed constants. | Recorded |

**But these limitations can only strengthen the conclusion, not overturn it**: the judgment is unstable between humans too, and the disagreement concentrates on exactly the kind of text a learner produces. See [section 4.3 of the decision report](docs/research/why-no-llm-judgment.md).

---

## Contributing

Contributions are welcome. Where help is most useful:

| Area | Specifically |
| --- | --- |
| **Run the missing experiments** | Human annotation (3+ qualified readers) and a non-canonical corpus retest. This is the single most valuable contribution. |
| **Interface and feel** | Typography, fonts, immersion. For a writing tool, the feel *is* the product. |
| **Corpus handling** | Splitting rules for other forms — classical Chinese, poetry, translated prose, technical writing. |
| **Packaging** | Single-file builds for Windows/macOS, Docker, Homebrew. |
| **Translation** | UI strings into more languages — the interface is still Chinese-only. |
| **Bug reports** | Especially "I clicked it and nothing happened" and "the split is wrong" — please include reproduction steps. |

Read [CONTRIBUTING.en.md](CONTRIBUTING.en.md) before you start. By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.en.md).

**Have an idea that isn't fully formed?** Take it to [Discussions](https://github.com/luluxiuc/Franklin-Writing/discussions) rather than opening an issue.

---

## License

[PolyForm Noncommercial License 1.0.0](LICENSE) — **all noncommercial use is permitted.**

You may use, study, research, modify, distribute, fork, teach with it, use it inside a nonprofit or educational institution, and evaluate it internally at a company for noncommercial purposes. **You may not use it for commercial purposes without permission** — including selling the tool or a modified version, using it to power a paid service, or bundling it into a commercial product.

> **Plainly: this is not an OSI-approved open-source license; it is source-available.** It restricts commercial use, and the OSI definition does not permit field-of-use restrictions. **That restriction is deliberate** — the thing this project exists to prevent is someone turning this method into a paid course or a paid scoring service. Everything else is open.

Need a commercial license, or unsure whether your use counts as commercial? Open an [issue](https://github.com/luluxiuc/Franklin-Writing/issues/new/choose) and ask rather than guessing.

---

## Credits

- **Benjamin Franklin** — the method is his. This project only arranges it into a workflow that is easy to keep up.
- All corpus material comes from public publications. **The repository ships no copyrighted source text**; obtain any experimental corpus from public sources yourself.

---

<p align="center">
  <b>The system puts the right actions in the right order. The rest is yours.</b>
</p>
