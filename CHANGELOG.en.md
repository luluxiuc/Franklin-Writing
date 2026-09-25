[English](CHANGELOG.en.md) · [中文](CHANGELOG.md)

# Changelog

This file records notable changes to this project. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

**One honest word about version numbers:** this project went from a research method to a usable tool in three days, changed direction once along the way, and never went through a formal release process. So the first formal entry is **Unreleased (preparing the first public release)**, which explains all the prior work in one go, rather than inventing a string of version numbers after the fact.

---

## [Unreleased] — preparing the first public release

The first public release contains all of the work below. Project timeline: research completed and the direction set on 2026-09-23, the tool built from 2026-09-23 to 09-25.

### Research

- **Measured whether an LLM can judge "does it sound like the author".** 5 independent judges / 18 anonymous text blocks (8 passages of real published prose + 10 imitation drafts, 5 of which had a named defect planted in them) / preregistered decision criteria.
  - Real texts misjudged as imitation: **0%** (all 5 judges, 8/8)
  - Imitations with an obvious planted defect seen through: **100%** (all 5 judges, 5/5)
  - **Imitations with no defect seen through: 0%** (majority verdict; 3 of the 5 judges were at 0/5)
  - Unanimous agreement rate between judges 13/18 = 72%, and **100% of the disagreement fell on "imitations with no defect"**
  - Conclusion: **100% of the discriminative power comes from "is there an obvious defect", 0% from "does it sound like the author".**
- **Recorded a more serious finding: the direction of the misjudgements is systematic.** What the judges rejected was precisely the author's own signature devices (the "meta-statements about memory" that the author uses heavily were judged as flaws; the author's own trailing off into silence was judged as "the sentiment arrives too punctually"; in one case **the original was misread and linguistic evidence was fabricated** to support a style judgment).
- **Ruled out one alternative explanation.** A comparison of normalised features showed that the imitation drafts had a higher density of named entities than the originals (9.2 vs 4.7), so "the judges just thought the drafts were too short" does not hold; the only things genuinely separable by mechanical means were connectives and emotion words.
- **Measured that the wrong calls were not produced by hesitation.** The 3 judges with records on file made 10 wrong calls in total, **all of them self-reported at confidence ≥ 4**, 1 of them a full 5.
- **The purely computational part of the measurements (zero model calls)** overturned two common impressions: "this author is good at short sentences" (measured mean sentence length 17.8 characters, longest run of consecutive short sentences only 2; the real feature is at the level of the clause, mean length 7.5 characters), and "he does not write emotion words" (only 2 occurrences, and neither states an emotion; the correct formulation is "he does not use emotion words as the predicate of a main clause").
- **Recorded the study's own defects honestly**: human agreement not measured, 3 judges searched external sources in violation of the protocol, the same-length pairing test failed, the sample size is small, the person who ran it both built the material and designed the experiment, and **the preregistered rules missed the real failure mode**. See [`docs/research/`](docs/research/).
- The preregistration file, the material parameters, all analysis scripts and the judge verdicts on file are published with the repository.

### Decisions

- **Deleted every AI judgment module from the design**: the comparison engine (where it does not match / why / how to change it), the author-model judgment layer, gap ranking, convergence trends, ability conclusions.
- **The project's direction was set as a pure tool that does not judge**: the system handles splitting, hinting, hiding, delaying and recording; understanding and evaluation are entirely up to the user. The decision process is in [`docs/research/why-no-llm-judgment.md`](docs/research/why-no-llm-judgment.md).

### Added

- **A local web tool** (Python standard library + vanilla frontend, zero dependencies, fully offline):
  - the complete flow: bookshelf → reading → writing desk → sentence-by-sentence comparison
  - splitting: two levels, section (reading unit) + paragraph (practice unit), **reversible** (stitching every paragraph back together equals the original exactly)
  - paragraphs are about 300 characters by default, adjustable in settings
  - per-sentence hints: one hint per sentence, the count determined by the number of sentences in the original; a character cap per hint; the cache key is `content hash of the original + model name + prompt version`
  - hints for a whole book prepared in a background batch, with a token estimate available up front (clearly labelled as an estimate)
  - an enforced delay between finishing reading and being able to write (3 minutes by default, adjustable 0–240), and other paragraphs can be practised while waiting
  - sentence-by-sentence comparison: aligned with the longest common subsequence, extra and missing text marked separately; hit words highlighted; "fragments that are in the original but that you did not write" laid out as they are
  - single-sentence practice: see one hint and write only that sentence, then immediately see it side by side with that sentence of the original
  - notes: one entry point, following the book, tagged "sentence n" or "whole paragraph", exportable as markdown
  - typing animation: canvas overlay, four levels (fade in / rise / write / off), the choice is remembered
  - accounting records only the `usage` the provider sends back; if it is unavailable, 0 is recorded, nothing is estimated
  - all data lives in `app/data/`, plain text, deleting it leaves no trace

### Fixed

Problems genuinely caught and fixed during development, recorded here as well:

- **Splitting fallback**: pasting 2000 characters with no sentence punctuation was treated as "one paragraph", so one practice round meant memorising 2000 characters. Now it splits inside the sentence on punctuation, and if that still does not work it hard-splits on character count.
- **Whitespace normalisation**: articles copied from web pages carry leading and trailing spaces and whole blank lines, which made the split produce empty fragments and shifted the sentence numbering. Import now normalises whitespace only and **does not move a single content character**.
- **The anti-leak self-check caught a title leak**: a section title had been cut from the first sentence of the original, yet it was attached to the practice page's title bar, which handed the opening of that passage to the user. The practice page now shows no section title, and before returning anything the service layer scans the data it is about to send against the original.
- **Hints copying the original**: the model occasionally moved a short sentence of the original into a hint. Every hint is now checked mechanically, and any hint with ≥ 8 consecutive characters identical to the original is removed; if both attempts are copying, no hint is given at all.
- **An API key containing Chinese characters or spaces** reported an unreadable encoding error. It is now caught on the spot with the reason explained.
- **Non-ASCII filenames** broke in `Content-Disposition`. Switched to RFC 5987 `filename*=UTF-8''` with an ASCII fallback.
- **Autosave being treated as a submitted draft**: after the draft autosaved, the user could no longer change it or submit it. The state machine now keys off "has a draft actually been submitted".
- **The animation button did nothing when clicked**: `FONTS_ANIM` was declared **after** the function that used it, hit the temporal dead zone, threw an exception on the function's first line, and the interface showed no message at all.
- **The animation could not be turned off**: whether it was on was decided with `!!S.anim`, while the "off" level is numbered 4 and `!!4` is true — choosing "off" turned the animation on instead. It now goes through the single check `animOn()`.
- **Three of the animation levels looked exactly the same**: the drawing function never read the current level at all. Each level now has its own drawing parameters, and there are tests asserting that they really differ.
- Several 404s caused by a wrong length check on routes, `POST` routes swallowed by a layer above, and value lookups failing after a field was moved.

### Tests

- 7 test groups, **370-plus checks**, all run in one go by `python tests/run_all.py`. The runner starts its own server with a fake model and shuts it down when it is done, **no network, no money**.
- The key groups among them:
  - **splitting reversibility** (not one character of the original lost) is a hard assertion
  - **no endpoint returns the original during the writing stage**
  - **frontend contract**: whether the elements and endpoints the JS references actually exist
  - **buttons are really clickable**: actually render the template, find every button, click it and see whether the state changed
  - **typing animation**: only settled characters are animated, the levels really do draw differently, the amount of animation does not grow with the length of the text, it can be attached and detached
  - **frontend rendering**: really run through each page's rendering once in Node

### Documentation

- Bilingual detail pages: READMEs in both languages, plus bilingual versions of the research reports, the measured data and the experiment data notes.
- [`docs/design/`](docs/design/): methodology, the no-judgment design, the tool user guide, the test report.

---

## Earlier (for the record)

This work happened before the formal release, is not numbered separately, and is listed here so that the history does not break:

- **Methodology documents v0.1 → v0.2 → v0.3**: from the complete design of an "AI Franklin writing training system", progressively converging on the identification of "proxy drift" as the core risk. v0.3 was the first to write "proxy drift" up as the project's most dangerous failure mode.
- **No-judgment design v1.0**: the product design after all AI judgment was deleted, triggered by the experimental conclusions.
- **A command-line prototype** `fk_tool/fk.py`: a single file, zero model calls, usable offline, containing 11 smoke assertions and 7 constraint self-checks. It verified that "the method still holds after judgment is deleted", and was afterwards replaced by the web version. **Kept in the repository for the record, no longer maintained.**
- **Test report for the fingerprint and feedback engine**: recorded four structural false positives produced by hand-written threshold rules (the author's own text judged as "deviating from the author", sampling at the wrong level, low-frequency features treated as per-paragraph requirements, and drafts written closer to the author scoring a comparable number of serious problems). These failures showed that "passing thresholds off as judgment goes off the rails", and were the early evidence for deleting judgment later on.
