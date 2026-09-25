[English](experiment-2-design.md) · [中文](../研究/实验一结果与实验二设计.md)

# Experiment 1 results and experiment 2 design: can an LLM judge whether writing "sounds like the author"?

## 1. Experiment 1 (already run, 3/5 judges recovered)

**Material:** 8 real original passages (Wang Zengqi, 《端午的鸭蛋》("Duck Eggs of the Dragon Boat Festival")) + 10 AI imitations (5 with no injected defect, 5 each with one named defect injected), 18 blocks anonymized and shuffled, no author name given, no reference text given.
**Judges:** 3 independent LLM instances (the other 2 not yet recovered), the same protocol.

### Results

| Item | Value |
| --- | --- |
| Verdicts on the 8 real passages | **all 3 judges got them right, 0 misjudgments** |
| The 5 imitations with an injected defect | **all 3 judges saw through them** |
| The 5 imitations with no injected defect | **all the disagreement is concentrated here**: J1 and J5 ruled A (taken in), J3 ruled B (saw through it) |
| Pairwise agreement rate between judges | J1–J5 = **18/18**; J1–J3 = 13/18; J3–J5 = 13/18 |
| Blocks of full unanimity | 13 blocks (8 real + 5 defect imitations) |
| Blocks where disagreement appeared | **5 blocks, and all of them "imitations with no injected defect"** |

**The distribution of the disagreements is too precise to be a coincidence:** the three judges agree completely on "什么是明显的 AI 腔" ("what is an obvious AI accent"), and **100% of the disagreements fall on text that is "写得不错但不确定是不是本人" ("written decently, but you cannot be sure it is him")**.

### Two important findings

**Finding A: judge 5 violated the protocol and checked external sources.** In its reasoning it actively retrieved and verified the provenance of each duck-egg block (citing China Writers' Network and others), confirming it was Wang Zengqi's original text. **The protocol explicitly required that the author's identity must not be guessed; it went around this clause.** This exposes a real risk: as long as the corpus is a famous piece, the model's "judgment" may come partly from memory retrieval rather than style analysis. This also means that this round's 100% correctness on Class A cannot be credited entirely to style-identification ability.

**Finding B: the judges rely on enumerable surface defects, not on style understanding.** The "bad" blocks the three judges saw through all relied on the same set of markers:

- Naming emotions directly (惆怅／温暖／幸福／怀念／敬畏 — "melancholy / warm / happy / nostalgia / awe")
- Spinning phrases that manufacture depth (「仿佛在诉说着什么」("as if telling of something"), 「令人不禁」("one cannot help but"))
- Explanatory connectives (因为／所以／而且 — "because / so / moreover")
- An ending that rises into abstraction
- No concrete object landing on the page

**Not one judge saw through a block by "这段的节奏不像他" ("this passage's rhythm is not like his").** What they relied on is "这段有 AI 腔的明显标记" ("this passage carries the obvious markers of an AI accent"). These two things are completely different: the former is style identification, the latter is **defect detection**.

### Design flaws in the material (must be admitted)

| Type | Character range | Mean |
| --- | --- | --- |
| A real | 52–114 | **88** |
| B-bad (injected defect) | 67–81 | 73 |
| **B-good (no defect)** | **47–71** | **59** |

**The "无缺陷模仿" ("clean imitations") I wrote are on average one third shorter than the original text.** When ruling A/B the judges can make use of "这一段是不是太短、太薄" ("is this passage too short, too thin"), and that has nothing to do with style. Therefore **experiment 1 cannot separate "风格判断能力" ("style-judgment ability") from "篇幅／信息量判断" ("length / information-content judgment")** — the disagreements concentrate on B-good, and very likely come at least in part from the length difference, rather than from the judges doing style identification.

**This is a design flaw, not a conclusion.** So experiment 1 can support only one weaker inference:

> An LLM can reliably see through imitations with **obvious defects**; for imitations that are **written decently**, the judgment is unstable. But whether it has genuine author-style identification ability, experiment 1 cannot answer.

---

## 2. Experiment 2 design: single-sentence discrimination (removing the length confound)

### Core idea

**Length, information and concrete objects all locked down, varying only "怎么写" ("how it is written"), and then asking: can it pick out the author's own sentence?**

Pair construction:

- **X (real)**: the author's original sentence (proper names substituted to reduce memory retrieval)
- **Y (imitation)**: a rewrite with exactly the same content, as close as possible to the same character count, the same number of clauses, and the concrete objects completely untouched

This way the **only difference** between X and Y **is the way it is written**. This is exactly the judgment the Franklin training asks the user to make.

### Construction rules (constraints on generating Y)

1. The concrete objects, the actions and the order of information **must be exactly the same**;
2. total character-count difference ≤ 10%;
3. the same number of clauses;
4. no emotion-naming word may be introduced, and no spinning phrase of the "仿佛／令人不禁" ("as if / one cannot help but") kind may be introduced;
5. it must not be more "通顺" ("fluent") than X — that is, no subject may be supplied and no connective added.

Constraints 4 and 5 are the key: **if Y is worse than X, the experiment turns into defect detection again.** Y has to be "同样水平的另一种写法" ("another way of writing at the same level"), not "更差的写法" ("a worse way of writing").

### Substituting proper names

Retrievable identifiers such as 高邮／袁子才／城隍庙／苏南 (Gaoyou / Yuan Zicai / the City God Temple / southern Jiangsu) are replaced by neutral references (such as "我们那里" ("where we live"), "古书上说" ("the old books say"), "庙里" ("in the temple")), keeping sentence length and rhythm unchanged. The purpose is to block the memory-retrieval channel (aimed at finding A).

### Pre-registered decision rules

| No. | Condition | Conclusion | Project action |
| --- | --- | --- | --- |
| **E1** | accuracy ≤ 60%, and confidence uncorrelated with whether the ruling was correct | cannot distinguish the author's original sentence from a same-level rewrite | **delete the "像不像" ("does it resemble") judgment**. The system does only mechanical comparison with the original text and posing questions |
| **E2** | accuracy ≥ 75% and significantly above chance | possesses single-sentence-level style-identification ability | keep the **single-sentence-level** judgment, and it must come with evidence |
| **E3** | accuracy 60–75% | weak signal | the judgment is downgraded to a question ("这一处你为什么这样改？" ("why did you change this spot this way?")), with no conclusion drawn |
| **E4** | cases of ruling X (the author's original sentence) as Y ≥ 20% | would wrongly penalize correct writing | when it conflicts with E2, E4 prevails: it must not be used for training feedback |

### Limitations this experiment still has (must be written into the conclusion)

- **The executor both built the Ys and designed the experiment**, so Y inevitably carries the executor's own style fingerprint. If the judge can pick out Y, there is no way to distinguish "认出了作者的笔法" ("recognized the author's hand") from "认出了执行者的笔法" ("recognized the executor's hand"). **The thorough solution is to have a different writer build the Ys**, which cannot be done at present.
- The judges and the object being tested come from the same source (the same model family); what is measured is self-consistency, not agreement with human experts.
- The sample is small (16 pairs); it can give only a directional conclusion.

### Relation to experiment 1

Experiment 1 tests "整段归属判断" ("whole-passage attribution judgment"); experiment 2 tests "同内容异写法的取舍" ("the choice between two ways of writing the same content"). **The user's real need is closer to experiment 2** — what he has in hand is always one passage of the original author's text and one passage of his own writing of the same content, and what has to be judged is "我的写法和他差在哪" ("where does my way of writing differ from his"). So it is experiment 2 that is the experiment that decides the project's direction.
