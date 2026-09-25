# Experiment 1 Results and Experiment 2 Design: can an LLM judge whether writing "sounds like the author"?

**Language:** English translation of the original Chinese report [`docs/研究/experiment-2-design.md`](experiment-2-design.md).
**Date:** 2026-09

> *Translator's note: this file is an interim snapshot written while only 3 of the 5 judges had reported. The `2026-01` date carried by the source has been corrected to 2026-09, which is when the repository's file timestamps show this work was actually done.*

## 1. Experiment 1 (already run, 3/5 judges recovered)

**Material:** 8 real original passages (Wang Zengqi, "Duck Eggs of the Dragon Boat Festival") + 10 AI imitations (5 with no injected defect, 5 each with one named defect injected), 18 blocks anonymized and shuffled, no author name given, no reference text given.
**Judges:** 3 independent LLM instances (the other 2 not yet recovered), same protocol.

### Results

| Item | Value |
| --- | --- |
| Verdicts on the 8 real passages | **all 3 judges got them right, 0 misjudgments** |
| The 5 imitations with an injected defect | **all 3 judges saw through them** |
| The 5 imitations with no injected defect | **all the splits concentrate here**: J1 and J5 ruled A (taken in), J3 ruled B (saw through it) |
| Pairwise agreement rate between judges | J1–J5 = **18/18**; J1–J3 = 13/18; J3–J5 = 13/18 |
| Blocks of full unanimity | 13 blocks (8 real + 5 defect imitations) |
| Blocks where a split appeared | **5 blocks, and all of them "imitations with no injected defect"** |

**The distribution of the splits is too precise to be coincidence:** the three judges agree completely on "what is an obvious AI accent", and **100% of the splits fall on text that is "written decently, but I am not sure whether it is him"**.

### Two important findings

**Finding A: judge 5 violated the protocol and looked up external sources.** In its reasoning it actively retrieved and verified the provenance of each duck-egg block (citing China Writers' Network and others), confirming it was Wang Zengqi's original text. **The protocol explicitly required that the author's identity must not be guessed; it went around this clause.** This exposes a real risk: as long as the corpus is a famous piece, the model's "judgment" may come partly from memory retrieval rather than style analysis. This also means that this round's 100% correctness on Class A cannot be credited entirely to style-identification ability.

**Finding B: the judges rely on enumerable surface defects, not on style understanding.** The "bad" blocks the three judges saw through all relied on the same set of markers:

- Naming emotions directly (惆怅／温暖／幸福／怀念／敬畏 — "melancholy / warm / happy / nostalgia / awe")
- Spinning phrases that manufacture depth (「仿佛在诉说着什么」("as if telling of something"), 「令人不禁」("one cannot help but"))
- Explanatory connectives (因为／所以／而且 — "because / so / moreover")
- An ending that rises into abstraction
- No concrete physical object landing on the page

**Not one judge saw through a block by "this passage's rhythm is not like his."** What they relied on is "this passage carries the obvious markers of an AI accent". These two things are completely different: the former is style identification, the latter is **defect detection**.

### Design flaw in the material (must be admitted)

| Type | Character range | Mean |
| --- | --- | --- |
| A real | 52–114 | **88** |
| B-bad (injected defect) | 67–81 | 73 |
| **B-good (no defect)** | **47–71** | **59** |

**The "defect-free imitations" I wrote are on average one third shorter than the original text.** When ruling A/B the judges can make use of "is this passage too short, too thin", and that has nothing to do with style. Therefore **experiment 1 cannot separate "style-judgment ability" from "length / information-content judgment"** — the splits concentrate on B-good, and very likely come at least partly from the length difference, rather than from the judge doing style identification.

**This is a design flaw, not a conclusion.** So experiment 1 can support only one weaker inference:

> An LLM can reliably see through imitations with **obvious defects**; for imitations that are **written decently**, the judgment is unstable. But whether it possesses genuine author-style identification ability, experiment 1 cannot answer.

---

## 2. Experiment 2 design: single-sentence discrimination (removing the length confound)

### Core idea

**Length, information and physical objects all locked down, varying only "how it is written", and then asking: can it pick out the author's own sentence?**

Pair construction:

- **X (real)**: the author's original sentence (proper names substituted to reduce memory retrieval)
- **Y (imitation)**: a rewrite with exactly the same content, as close as possible to the same character count, the same number of clauses, and the concrete physical objects completely untouched

This way the **only difference** between X and Y **is the way it is written**. This is exactly the judgment the Franklin training asks the user to make.

### Construction rules (constraints on generating Y)

1. The concrete physical objects, the actions and the order of information **must be exactly the same**;
2. total character-count difference ≤ 10%;
3. the same number of clauses;
4. no emotion-naming words may be introduced, and no spinning phrases of the "仿佛／令人不禁" ("as if / one cannot help but") kind may be introduced;
5. it must not be more "fluent" than X — that is, no subjects may be supplied and no connectives added.

Constraints 4 and 5 are the key ones: **if Y is worse than X, the experiment turns into defect detection again.** Y has to be "another way of writing at the same level", not "a worse way of writing".

### Substituting proper names

Retrievable identifiers such as 高邮／袁子才／城隍庙／苏南 (Gaoyou / Yuan Zicai / the City God Temple / southern Jiangsu) are replaced with neutral references (such as "我们那里"("where we are from"), "古书上说"("the old books say"), "庙里"("in the temple")), keeping sentence length and rhythm unchanged. The purpose is to block the memory-retrieval channel (aimed at finding A).

### Pre-registered decision rules

| No. | Condition | Conclusion | Project action |
| --- | --- | --- | --- |
| **E1** | accuracy ≤ 60%, and confidence uncorrelated with whether the ruling was right | cannot distinguish the author's original sentence from a same-level rewrite | **delete the "does it resemble" judgment**. The system does only mechanical comparison with the original text and posing questions |
| **E2** | accuracy ≥ 75% and significantly above chance | possesses single-sentence-level style identification ability | keep **single-sentence-level** judgment, and it must be accompanied by evidence |
| **E3** | accuracy 60–75% | weak signal | the judgment is downgraded to a question ("why did you change this spot this way?"), with no conclusion drawn |
| **E4** | cases of ruling X (the author's original sentence) as Y ≥ 20% | would wrongly penalize correct writing | when it conflicts with E2, E4 prevails: must not be used for training feedback |

### Limitations this experiment still has (must be written into the conclusion)

- **The executor both built the Ys and designed the experiment**, so Y inevitably carries the executor's own style fingerprint. If the judge can pick out Y, there is no way to distinguish "recognised the author's hand" from "recognised the executor's hand". **The thorough solution is to have a different writer build the Ys**, which cannot be done at present.
- The judges and the object being tested come from the same source (the same model family); what is measured is self-consistency, not agreement with human experts.
- The sample is small (16 pairs); it can give only a directional conclusion.

### Relation to experiment 1

Experiment 1 tests "whole-passage attribution judgment"; experiment 2 tests "the choice between two ways of writing the same content". **The user's real need is closer to experiment 2** — what he has in hand is always one passage of the original author's text and one passage of his own writing of the same content, and what has to be judged is "where does my way of writing differ from his". So it is experiment 2 that is the experiment deciding the project's direction.
