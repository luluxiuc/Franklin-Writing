[English](appendix-measured-data.md) · [中文](../研究/附录-实测数据汇总.md)

# Appendix: All measured data cited in this report

**Language:** English translation of the original Chinese data appendix [`docs/研究/附录-实测数据汇总.md`](../研究/附录-实测数据汇总.md).
**Purpose:** auditability. Every figure in the research reports traces to a row here.

This file is the data source. Every number in the body of the report comes from here, and every one of them can be recomputed.

---

## A. Corpus and tools

| Item | Content |
| --- | --- |
| Corpus | Wang Zengqi, 《端午的鸭蛋》("Duck Eggs of the Dragon Boat Festival") |
| Source | China Federation of Literary and Art Circles (中国文艺网) https://www.cflac.org.cn/wywzt/2014/DuanWu/yuedu/201405/t20140529_257288.html |
| Extent | 6 body paragraphs written by the author + 1 paragraph quoting Yuan Mei's 《随园食单》("Menu of the Suiyuan Garden") (the quoted paragraph is excluded from the author fingerprint) |
| Character count | 1351 characters (punctuation removed, quoted paragraph excluded) |
| Note | The source text has one truncation (at the end of paragraph 2, "但是《腌蛋》这一条我看后却" ("but after reading this entry on 《腌蛋》 (Salted Eggs), I…") is missing its ending); this does not affect the present conclusions |
| Computation scripts | `_probe/analyze_fingerprint.py`, `_probe/engine_probe.py`, `_probe/verify_details.py`, `_capability/*.py` |
| Model calls | **Sections A and B are entirely local computation, zero model calls. Sections C and D use LLM judges.** |

The corpus is a published essay, attributed above with its public source URL. This repository does not redistribute the copyrighted source text; the short source fragments quoted in B3 are the minimum needed to document that measurement.

---

## B. Layer-1 statistical fingerprint measurements (pure computation, reproducible)

### B1. Sentences and clauses

| Metric | Measured value |
| --- | --- |
| Sentence count | 76 |
| Clause count | 179 |
| **Sentence length** | mean **17.8** characters, median 16.5, SD 10.0, min 1, max 43 |
| **Clause length** | mean **7.5** characters, median 7, SD 3.8, min 1, max 18 |
| Sentence-length distribution | 0-6 chars: 8, 7-10 chars: 14, 11-15 chars: 13, 16-20 chars: 14, 21-30 chars: 18, 31+ chars: 9 |
| **Longest run of consecutive short sentences (≤8 chars)** | **2 sentences** |
| Longest run of consecutive short sentences (≤10 chars) | 3 sentences |
| Paragraph length | mean 225.2 characters, median 182.5, min 81, max 487 |

### B2. Punctuation and vocabulary

| Metric | Measured value |
| --- | --- |
| Comma density | 6.9 per 100 characters |
| Period density | 4.7 per 100 characters |
| Comma-to-period ratio | 1.48 |
| Exclamation marks | 8 occurrences |
| Question marks | 4 occurrences (all self-asked, none answered) |
| Enumeration comma (顿号) | 7 occurrences; semicolon (分号) 0 occurrences |
| Dash (破折号) | 1 occurrence |
| Explicit connectives | 所以 (so) 1, 但是 (but) 1, 然而 (however) 1, 不过 (though) 3, 而且 (moreover) 2, 于是 (thereupon) 1, 而是 (but rather) 1 |
| **Connective density** | **0.74 per 100 characters** |
| Personal pronoun density | 2.07 per 100 characters ("我" ("I") accounts for 60.7%) |
| Concrete named objects | 47 kinds, 165 occurrences in total (roughly one physical object every 8 characters) |
| Expressions of uncertainty | 不知 (don't know), 记不清 (can't recall), 数不出 (can't count them out), 也许 (perhaps), 不一定 (not necessarily), 大概 (probably), 好像 (seems), 说是 (it is said), 1 occurrence each |

### B3. Two general claims overturned by measurement

**Claim one: "skilled use of short sentences" is wrong.**

- If one described this author from impression, the most natural phrasing would be "善用短句" ("skilled use of short sentences").
- Measured: mean sentence length **17.8 characters**, longest run of consecutive short sentences only **2 sentences**. At the sentence level, the rhythm is not at all brisk.
- The real feature lies at the next unit down: **mean clause length 7.5 characters**, with 179 clauses distributed over 76 sentences (2.4 clauses per sentence on average).
- Paragraph 1 contains a run of **8 consecutive clauses of ≤6 characters**. The length sequence of the first 32 clauses in that paragraph:
  `5, 9, 4, 9, 5, 6, 6, 13, 4, 7, 6, 7, 5, 3, 6, 5, 2, 9, 15, 15, 7, 4, 9, 7, 5, 14, 6, 4, 18, 9, 11, 4`

**Claim two: "doesn't write emotion" is inaccurate.**

- The whole text contains only **2** direct emotion words, both of them "高兴" ("happy/glad"), and **neither of the two states an emotion**:
  - 「我对异乡人称道高邮鸭蛋，是**不大高兴**的」("When people from elsewhere praise Gaoyou duck eggs, I am **not too pleased**") — negative form, an attitude judgement
  - 「什么时候孩子**一高兴**，就把络子里的鸭蛋掏出来，吃了」("whenever a child **took a fancy**, he would pull the duck egg out of the net bag and eat it") — used as an adverbial of condition (一……就…… "as soon as… then…")
- Nowhere is there a sentence of the "他很高兴" ("he was very happy") type, with emotion as the predicate.
- The correct formulation is therefore: **emotion words are not used as main-clause predicates**, not "emotion words are not written".

---

## C. Failure caused by layer-1 over-reach judging (run report 01)

### C1. Sentinel test: the author's own text judged as deviating from the author

The opening sentence of paragraph 1 (8 short clauses, the densest form of this feature) was fed into the judging engine. Result: **2 major problems + 2 minor problems**.

| Metric | Sentinel result | Real cause |
| --- | --- | --- |
| List-style opening | judged 0/7 sentences | **Unit-of-measurement error**: at clause level this feature runs at 20% (13/65), at sentence level 31% (8/26); the sentinel is made of 8 short clauses, and because it was segmented by sentence they were all missed |
| Rhythm variation | judged "too uniform" (clause-length SD 2.4 vs 3.8) | **SD varies with sample size**: 2.4 from 7 clauses and 3.8 from 179 clauses are not comparable; the metric was not normalised |
| No question appeared | judged as deviation | The original's 4 questions are spread over 76 sentences, and most paragraphs simply contain no question; **"did not appear" was treated as a defect** |
| No modal particle appeared | judged as deviation | Same as above; a low-frequency feature was treated as mandatory |

**All four are structural false positives; not one of them can be fixed by tuning a threshold.**

### C2. The rules penalised a word the author himself used

A pastiche deliberately constructed to match the measured fingerprint (mean clause length 4.3 characters, brisker than the author's 7.5) was judged a **core problem**:

> 情绪表达：出现直接情绪词 [('高兴', 1)]
> ("Emotion expression: a direct emotion word appears [('高兴' ("happy"), 1)]")

That sentence is "孩子一高兴，掏出来，吃了" ("the child took a fancy, pulled it out, ate it") — **this is exactly the original sentence** 「什么时候孩子一高兴，就把络子里的鸭蛋掏出来，吃了」("whenever a child took a fancy, he would pull the duck egg out of the net bag and eat it"). Same author, same word, same usage, same syntactic position.

### C3. A badly written draft was judged more leniently

| Draft | Fingerprint | Judgement |
| --- | --- | --- |
| User's pastiche (AI-generalised style) | 251 characters, 7 sentences, **sentence length 35.9 characters**, connective density **2.39 per 100 characters** (author 0.74) | 1 core + 2 major + 3 minor |
| Pastiche (constructed to the measured fingerprint, clauses 4.3 characters) | 86 characters, 11 sentences, sentence length 7.8 characters | **1 core** + 2 major + 2 minor |

**The draft closer to the author received a severity count comparable to the badly written one.**

### C4. The penalised features point in exactly one direction

| Penalised by the system | The author's own measured value |
| --- | --- |
| Smooth long sentences, explicit connectives (因为／所以／因此 — because／so／therefore) | connective density only **0.74 per 100 characters** |
| Complete subjects, every sentence spelled out | heavy subject ellipsis ("系百索子" ("tie on the five-coloured silk cords"), "出鸭" ("the ducks come out"), "鸭多，鸭蛋也多" ("there are many ducks, and many duck eggs too")) |
| Degree adverbs, explanatory phrasing | almost never stacked |
| Abstract generalisation | 47 kinds of concrete named objects, 165 occurrences |

**This judging scheme is in effect rewarding the generic good prose style of "fluent, complete, logical, explained".**

> **Caveat: the four false positives in section C were produced by hand-written heuristic rules; the LLM was not involved in that judging.** What they demonstrate is that passing a threshold off as judgement goes off track; they must not be used to assess LLM capability. For the LLM measurements, see section D.

---

## D. Experiment 1: measured LLM attribution ability

### D1. Materials

| Item | Content |
| --- | --- |
| Class A | 8 real published prose paragraphs |
| Class B | 10 AI imitations (5 with **no implanted defect**, 5 each with 1 named defect implanted) |
| Presentation | 18 blocks, anonymised and shuffled (fixed seed 20260101), author name not given |
| Protocol | Explicitly requires "do not assume who the author is"; the basis for a judgement must point to concrete linguistic facts; a verdict of B must quote the most suspicious passage |
| Judges | 5 independent LLM instances, same protocol |
| Material script | `_capability/build_material.py`; pre-registered criteria `_capability/PREREGISTRATION.json` |

**The 5 implanted defects (B-bad):** explicit connectives + abstract evaluation; direct statement of emotion + "温暖/幸福/怀念" ("warmth/happiness/longing") + degree adverbs; smooth long sentences + metaphor substitution + elevated conclusion ("仿佛在诉说着什么" ("as if telling of something")); direct entry into emotion ("说不出的惆怅" ("an indescribable melancholy") + "眼角有些湿润" ("the corners of the eyes grew a little moist")); explanatory causality ("因为年代久远" ("because of the great age")) + "令人不禁" ("one cannot help but") + "仿佛藏着另一个世界" ("as if hiding another world").

### D2. Block-by-block votes

| Block | Ground truth | Type | Judge 1 | Judge 2 | Judge 3 | Judge 4 | Judge 5 | Agreement |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | imitation | bad | B | B | B | B | B | unanimous |
| 2 | real | — | A | A | A | A | A | unanimous |
| 3 | real | — | A | A | A | A | A | unanimous |
| 4 | real | — | A | A | A | A | A | unanimous |
| 5 | real | — | A | A | A | A | A | unanimous |
| 6 | imitation | bad | B | B | B | B | B | unanimous |
| **7** | **imitation** | **good** | A | **B** | **B** | A | A | **split** |
| 8 | imitation | bad | B | B | B | B | B | unanimous |
| **9** | **imitation** | **good** | A | A | **B** | A | A | **split** |
| 10 | real | — | A | A | A | A | A | unanimous |
| **11** | **imitation** | **good** | A | **B** | **B** | A | A | **split** |
| 12 | real | — | A | A | A | A | A | unanimous |
| **13** | **imitation** | **good** | A | **B** | **B** | A | A | **split** |
| 14 | imitation | bad | B | B | B | B | B | unanimous |
| **15** | **imitation** | **good** | A | A | **B** | A | A | **split** |
| 16 | imitation | bad | B | B | B | B | B | unanimous |
| 17 | real | — | A | A | A | A | A | unanimous |
| 18 | real | — | A | A | A | A | A | unanimous |

### D3. Decisive metrics

| Metric | Result |
| --- | --- |
| **Class A error rate** (real judged as imitation) | **0%** — all 5 judges correct 8/8 |
| **B-bad detection rate** (implanted obvious defects) | **100%** — all 5 judges saw through 5/5 |
| **B-good seeing-through rate** (no implanted defect) | **0%** (majority verdict 0/5) |
| Full-unanimity agreement rate across judges | 13/18 = 72%; splits fall **100% on B-good** (all 5 blocks had a split) |
| Overall accuracy per judge | Judge 1: 13/18; Judge 2: 16/18; Judge 3: 18/18; Judge 4: 13/18; Judge 5: 13/18 |

**Per-judge cross-tab:**

| Judge | True A judged A | True A judged B | True B judged B | True B judged A | good seen through | Overall correct |
| --- | --- | --- | --- | --- | --- | --- |
| Judge 1 | 8/8 | 0/8 | 5/10 | 5/10 | **0/5** | 13/18 |
| Judge 2 | 8/8 | 0/8 | 8/10 | 2/10 | 3/5 | 16/18 |
| Judge 3 | 8/8 | 0/8 | 10/10 | 0/10 | 5/5 | 18/18 |
| Judge 4 | 8/8 | 0/8 | 5/10 | 5/10 | **0/5** | 13/18 |
| Judge 5 | 8/8 | 0/8 | 5/10 | 5/10 | **0/5** | 13/18 |

**Conclusion: 100% of the discriminative power comes from "is there an obvious defect", 0% from "does it read like the author".**

### D4. The evidence judges used to see through defects (all of it enumerable surface markers)

1. Naming emotion directly (惆怅／温暖／幸福／怀念／敬畏 — melancholy／warmth／happiness／longing／awe)
2. Empty phrases manufacturing depth ("仿佛在诉说着什么" ("as if telling of something"), "令人不禁" ("one cannot help but"))
3. Explanatory connectives (因为／所以／而且 — because／so／moreover) — a judge's own words: "把因果讲透，取消读者发现的空间" ("spelling the causality out completely cancels the space for the reader to discover")
4. Endings rising to abstraction
5. No concrete named object grounded

**Not one judge saw through a block by saying "the rhythm of this passage doesn't sound like him".**

### D5. The direction of misjudgement is systematic (key finding)

Listing all misjudgements made by the 5 judges, the direction is entirely consistent: **what they rejected was precisely the author's own features.**

| Judge | Reason for misjudgement | Fact |
| --- | --- | --- |
| 3 | Judged "a meta-statement that only gives memory" to be a flaw: "真实写法会让「花纹」本身被描述出来" ("real writing would have the 「花纹」 (pattern) itself described") | The author uses meta-statements heavily: 「其余的都记不清，数不出了」("the rest I can't recall, can't count them out"), 「也许十二红只是一个名目」("perhaps Shi'erhong is just a name"), 「这一点是我没有记错的」("this is one point I have not misremembered") |
| 3 | Judged "the rhythm is advanced by atmosphere rather than by information" | The same criterion would equally strike confirmed real paragraphs: 「有的样子蠢，有的秀气」("some look stupid, some elegant"), 「白嘴吃也可以」("eating it plain is fine too") |
| 2 | 「有缠线的木轴，缠着黑线、白线」("there is a wooden spool for winding thread, wound with black thread, white thread") — called it "in reality one spool holds only one colour of thread, a flaw caused by inexperience with real objects" | **A misreading of the text** (two spools vs one), **fabricating linguistic evidence** to prop up a style judgement |
| 2 | Judged "the parallel-structure blank space of the closing two sentences; the sentiment arrives too punctually" | Of the same kind as the author's closings 「我也没问」("I didn't ask either"), 「白嘴吃也可以」("eating it plain is fine too") |
| 2 | Judged "omitting 「的」 is a deliberately manufactured rupture" | Reading precise language as deliberate rupture |

**Inference:** if training feedback were wired in, the result of the user following the corrections would be to delete "我也没问" ("I didn't ask either"), pad the blank space out into explanation, and add subjects and connectives to the sentences — **looking more and more like an ordinary writer who is merely fluent.**

### D6. Judge self-reported confidence against correctness (supplementary statistics)

The 3 judges whose per-block verdicts were archived (Judges 1, 3, 5) produced **45 verdicts in total, 10 of them wrong**:

| Group | Verdicts | Correct | Mean confidence when correct | Mean confidence when wrong |
| --- | --- | --- | --- | --- |
| A real | 24 | 24/24 | 4.88 | — |
| B clean imitation | 15 | 5/15 | 3.80 | **4.10 (n=10)** |
| B defective imitation | 15 | 15/15 | 4.80 | — |

**All 10 errors were made at self-reported confidence ≥ 4, one of them at the maximum of 5.**

Recompute with [`experiment-data/confidence_stats.py`](experiment-data/confidence_stats.py).

**Why this matters: the errors are not hedged.** If the mistakes clustered at low confidence, one could argue for filtering on confidence. In fact the judges were just as certain when they got it backwards — which, combined with D5, explains why this kind of judgment is especially damaging once wired into training feedback: the user sees no warning signal at all.

**But do not over-read this:** confidence is **self-reported by the model** and was never independently calibrated. It is enough to show these were not low-confidence coin flips. It is **not** evidence that the model is well calibrated.

### D7. Methodological problems

**Problem one: illicit retrieval.** 3 of the 5 judges (Judges 2, 4, 5) actively searched for and verified the provenance in their reasoning, citing 中国文艺网, 澎湃 (The Paper) and other links to confirm it was Wang Zengqi's original text; Judge A in the same-length paired test did the same, and cited 文汇网 (Wenhui) for the next sentence of the original. The protocol explicitly required "do not assume who the author is".

Consequence: **the 0% Class A error rate cannot be credited entirely to style-recognition ability**; part of it comes from memory retrieval. Once the corpus is switched to a non-famous text, that part of the ability disappears.

**Problem two: length confounding (ruled out).** In the first version of the materials, B-good averaged 59 characters vs Class A 88 characters. Normalised feature comparison:

| Group | Concrete-item density | Verb density | Connectives | Emotion words | Characters |
| --- | --- | --- | --- | --- | --- |
| A real (8 paragraphs) | 4.7 | 4.1 | 0.39 | 0.25 | 87.8 |
| B-good (5 paragraphs) | **9.2** | **6.2** | 0.00 | 0.00 | 59.4 |
| B-bad (5 paragraphs) | 2.4 | 1.1 | **4.38** | **1.40** | 73.0 |

**The imitation drafts have a higher concrete-object density than the original** (9.2 vs 4.7), so the alternative explanation "the judges merely disliked it for being short and thin" is ruled out. What is genuinely mechanically separable is **connectives and emotion words**: high in the bad group, zero in the good group, and zero in the original as well.

**Problem three: the pre-registered rule missed the real failure mode (recorded honestly).** The pre-registered D2 trigger condition was "Class A error rate ≥ 37.5%"; measured 0%, so it **did not trigger**. The real failure mode is "judging a competent imitation as real" (a miss), which was not foreseen at pre-registration time. The revised judgement and the full reasoning are in [experiment-1-final-results.md](experiment-1-final-results.md).

---

## E. Same-length paired test (supplementary experiment)

### E1. Materials (strictly balanced to equal character count)

**Group 1**
- 甲 (my imitation, 47 characters): `母亲的针线笸箩。/ 里头有顶针。有缠线的木轴，缠着黑线、白线。有一把张小泉的剪子，剪子尖有点豁。还有几颗纽扣，玻璃的，扣子上有细小花纹。`
  English: "My mother's sewing basket. / In it is a thimble. There is a wooden spool for winding thread, wound with black thread, white thread. There is a pair of Zhang Xiaoquan scissors, the tip of the scissors a little chipped. And a few buttons, glass ones, with a tiny pattern on them."
- 乙 (original text, 47 characters): `挑好了，装在络子里，挂在大襟的纽扣上。这有什么好看呢？`
  English: "Once chosen, they were put in the net bag and hung on the button of the jacket front. What is there to look at?"
- Ground truth: **甲 = imitation, 乙 = original**

**Group 2**
- 甲 (my imitation, 51 characters): `父亲的自行车。/ 二八的。链条盒是铁皮的，锈了。骑起来哗啦哗啦响。他从来不擦。`
  English: "My father's bicycle. / A 28-inch one. The chain guard is tin, rusted. Riding it, it clatters. He never wiped it."
- 乙 (original text, 51 characters): `有一年，那棉垫丢了。他没有再绑。我也没问。`
  English: "One year, that cotton pad was lost. He did not tie another one on. I didn't ask either."
- Ground truth: **甲 = imitation, 乙 = original**

### E2. Results and reasons

Judge A returned **2/2 correct** (it chose 甲 in both groups). But look at the reasons it gave:

> 第一组："乙 的两句与汪曾祺《端午的鸭蛋》原文**逐字一致**（引文汇网、中国文艺网链接），属原文截取。"
> ("Group 1: the two sentences of 乙 are **word-for-word identical** to the original text of Wang Zengqi's 《端午的鸭蛋》 (citing the Wenhui and 中国文艺网 links); this is an excerpt from the original.")

> 第二组："**本组无逐字可核出处**，判断依据是写法……乙2 有事件、有否定、有留白……**这是人类作者常用的收束方式**，也是仿写最不容易做对的地方。"
> ("Group 2: **no word-for-word source can be verified for this group**; the basis for the judgement is the writing… 乙2 has an event, a negation, a blank space… **this is a closing method human authors commonly use**, and also the place where imitation is hardest to get right.")

**Two key points:**

1. **Group 1's "correct" comes from hitting the original text through retrieval, not from style judgement.** The strict balancing (47 vs 47 characters) therefore fails completely as a design — the judge bypassed the style comparison and looked the source up directly.
2. **In group 2 it had no source to look up, and the reasoning immediately turned to "blank space / negative closing"** — and that is precisely a device the author himself uses repeatedly (「我也没问」("I didn't ask either"), 「白嘴吃也可以」("eating it plain is fine too"), 「这有什么好看呢？」("what is there to look at?")). That is, **within a single judgement it treated the author's device as "a closing method human authors commonly use" while counting it as a flaw in 甲.**

**Conclusion: the paired test cannot shut the retrieval channel down, so it cannot be used to measure pure within-text style-judgement ability.**

---

## F. Unfinished work

1. **"Agreement rate with a qualified human consensus" has not been measured.** The objective pre-registered this metric, but in actual execution the judges were all LLMs, which is circular. The tooling is ready: `_capability/human_kit.py` can generate annotation materials containing no answers (the `materials` subcommand; `人工标注材料.md` has been generated), collect human annotations, and compute pairwise human agreement and compare it with the LLM judges (the `score` subcommand). **At least 3 qualified readers are needed, each annotating once.**
2. **Re-testing on a non-famous corpus has not been done.** Switch to a contemporary author's corpus that the model has no memory of, stripping out the retrieval channel. Pure judgement ability is expected to be lower.
3. **Experiment 2 (single-sentence discrimination) is designed but not executed.** Pair the author's original sentences against rewrites that keep "the same content, the same character count, the same named objects, with only the phrasing changed" in a two-choice test. Design in [experiment-2-design.md](experiment-2-design.md).
