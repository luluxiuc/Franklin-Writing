[English](ROADMAP.en.md) · [中文](ROADMAP.md)

# Roadmap

**This roadmap has two entrances: more research, and more tool.** The former matters more — every design decision in this project comes from measured data; where the data is not enough, a decision can only be a guess.

A note on the labels: **Difficulty** is from the point of view of a contributor who is not familiar with the codebase. The entries tagged 「priority」 are where help is needed most.

---

## 1. Research: finish measuring what has not been measured

Every entry in this section corresponds to a defect explicitly recorded in the research reports. **They are not nice-to-haves, they are the soft spots in the conclusions.**

### 1. Human annotation (inter-annotator agreement) - priority, most important

**What is missing:** the judges in Experiment 1 were **all LLMs**, which is circular — what was measured is the model's self-consistency, not agreement with human experts. The preregistration file states this metric, but it was never collected.

**Why it matters:** this is the only data that can answer "is this judgment automatable in principle". If **humans do not agree among themselves**, then "aligning with the human consensus" has no object, and the conclusion is upgraded from "current models cannot do it" to "this road itself does not go through".

**How to do it:**
- The tool is already prepared: [`docs/research/experiment-data/human_kit.py`](docs/research/experiment-data/human_kit.py)
- It can generate annotation material that **contains no answers**, collect annotations, compute pairwise human agreement, and compare that against the LLM judges
- **It needs 3 or more qualified readers, each annotating once** (qualified = has a stable amount of reading, and can explain clearly why they judged the way they did)
- The corpus has to be obtained from public sources by yourself (the repository does not distribute copyrighted originals)

**Output:** a set of annotation results + a comparison of human agreement against LLM agreement.

### 2. Re-testing on a non-famous corpus - priority, high value

**What is missing:** 3 of the 5 judges **searched in violation of the protocol and verified the sources** (the protocol explicitly requires that author identity must not be inferred). So "0% misjudgement on real texts" cannot be credited entirely to style-recognition ability.

**Why it matters:** what users actually need is precisely a **non-famous corpus** — authors they like, who are not famous yet, who are contemporary. Under famous texts there are always shortcuts to take; under non-famous texts the ability can only be weaker.

**How to do it:** switch to a contemporary author the model has no memory of, and re-run Experiment 1. **Expect the clean judgment ability to be lower** — but that is the real ability.

**Output:** a comparison of the results from the two corpora.

### 3. Re-run Experiment 1 keeping the raw logs

**What is missing:** only 3 of the 5 judges have per-block verdicts on file; the rulings of judges 2 and 4 exist only in the report's tables; and the verdict values are **manually transcribed constants**, not read automatically out of the collection logs.

**Why it matters:** the current cross-check can only prove "the transcription is self-consistent with the report", not "the transcription matches what the model actually output at the time".

**How to do it:** run it again and **keep every raw response**. Write the verdicts straight to disk, without passing through human hands.

### 4. Run Experiment 2 (single-sentence discrimination)

**What is missing:** Experiment 1 is whole-passage attribution, and it **cannot separate "a judgment of style" from "a judgment of length / information content"**.

**How to do it:** pair an author's own sentence against a rewrite that has "**the same content, the same character count, the same named entities, only the phrasing changed**" in a forced choice, and permute the proper nouns to block the search channel. The design is already written: [`docs/research/experiment-2-design.md`](docs/research/experiment-2-design.md).

**Note one limitation the design states:** who constructs the material matters a great deal. **If the same person both constructs the material and designs the experiment, there is no way to distinguish "recognizing the author's hand" from "recognizing the experimenter's hand".** Ideally a different writer constructs the material.

### 5. Have a different writer rebuild the material

**What is missing:** all the imitation drafts in Experiment 1 were written by the person who ran it, so they inevitably carry that person's own stylistic fingerprint. This is a structural limitation, not something that can be solved by adding sample size.

---

## 2. Tool: things that can be done immediately

### 6. Screenshots and a demo

The README currently has a screenshot placeholder in it. **This is the single thing that most affects whether people are willing to open the repository.** Five images are enough: bookshelf, reading, writing desk, single-sentence practice, sentence-by-sentence comparison.

### 7. Better splitting rules

The current splitting works well on modern vernacular prose. The following forms have no dedicated handling yet:

| Form | Problem |
| --- | --- |
| Classical Chinese / parallel prose | different sentence-pause rules, a different punctuation system |
| Poetry | the unit problem of line length vs sentence length; is a line break content or formatting |
| Translations | many long attributive clauses, so splitting on punctuation produces very long paragraphs |
| Technical documentation | code blocks, lists and tables get treated as body text |

**This category of contribution is very practical:** import a piece of text that splits badly, fix the splitting rule, add tests.

### 8. Feel and typography

The feel of a writing tool is the product itself. What is currently known to be improvable:

- the defaults for font size, line spacing and page width, and whether the user should be allowed to adjust them
- how progress and state are presented after a long text is imported
- keyboard flow: can you get through a full round of practice without a mouse
- state messages on a weak or absent network

### 9. Packaging

Right now you need Python installed to run it. The goal: **double-click one file and it works, with nothing installed.**

| Platform | Approach |
| --- | --- |
| Windows | PyInstaller single-file exe |
| macOS | package as a .app, or a Homebrew formula |
| Linux | AppImage, or a Docker image |

**Note how this relates to the "zero dependencies" constraint:** the packaging tools are used at build time only and **must not introduce a runtime dependency**.

### 10. Data portability

- **Batch** import of existing books (right now it is one book at a time)
- Whole-library export / import (right now you can copy `app/data` by hand, but it is worth making into an interface action)
- Searching past drafts by book, by time, by paragraph

### 11. Multiple people practising on the same book?

That needs to be thought through first: **notes are private, and so are drafts.** To support it, the boundary of what is shared has to be decided first. **This feature will not be built until that discussion is clear.**

---

## 3. Explicitly not doing

Written down here so that nobody spends time on it:

| Not doing | Reason |
| --- | --- |
| Scoring / similarity / "does it sound like the author" | Measured conclusion: it only pushes the user away from the target author. See [`docs/research/`](docs/research/). |
| Automatic revision, automatically writing sentences for the user | Everything this tool generates is "one hint per sentence". |
| Cloud accounts, sync, social | Local-first is this product's identity, not a temporary implementation detail. |
| A phone app | Long-form writing practice does not work as an experience on a phone; the web version can already be opened in a mobile browser. |
| Adding pip / npm dependencies | It has to still be openable by double-click ten years from now. |
| Subscriptions, per-use charging | The license already forbids commercial use; this is an extension of it. |

---

## 4. Already done

- Splitting (two levels, section / paragraph, with reversibility as a hard assertion)
- Per-sentence hints (one per sentence, the count determined by the number of sentences, a per-hint character cap, a copying check)
- Hint caching (content hash + model name + prompt version), batch preparation for a whole book, token estimation
- An enforced delay (between finishing reading and being able to write, 3 minutes by default)
- Prevention of original-text leaks during the writing stage (reverse-lookup self-check in the service layer)
- Sentence-by-sentence comparison (LCS alignment, highlighting of hits, a list of missing fragments)
- Single-sentence practice
- Notes (one entry point, following the book, exportable)
- Typing animation (canvas overlay, four levels, only on settled characters)
- Accounting records only the real `usage`
- 7 test groups, 370-plus checks
- Bilingual Chinese/English research documentation and public measured data

---

## How to get involved

1. Pick one and say so in the corresponding Issue (open one if there is none)
2. Read [CONTRIBUTING.en.md](CONTRIBUTING.en.md), especially the **hard constraints** in it
3. If you are unsure before starting, come and talk in [Discussions](https://github.com/luluxiuc/Franklin-Writing/discussions)

**Research work (items 1–5) has the highest priority.** If you do only one thing, do human annotation.
