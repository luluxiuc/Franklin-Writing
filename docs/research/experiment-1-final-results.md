[English](experiment-1-final-results.md) · [中文](../研究/实验一最终结果.md)

# Experiment 1 Final Results (4 Judges)

**Language:** English translation of the original Chinese report [`docs/研究/实验一最终结果.md`](../研究/实验一最终结果.md).
**Date:** 2026-09

> *Translator's note: this file is an interim snapshot. Its heading, master table and decisive-metrics table all report **4 judges**, and it is internally consistent at that number. The final report set for Experiment 1 covers **5 judges** (see [llm-authorship-judgment.md](llm-authorship-judgment.md) and [appendix-measured-data.md](appendix-measured-data.md), where judge 3 is the only judge that caught all 5 clean imitations and judges 1, 4 and 5 each caught 0/5). The 4-judge figures reproduced here are the ones the source document states and have not been recalculated. The `2026-01` date carried by the source has been corrected to 2026-09, which is when the repository's file timestamps show this work was actually done.*

## 1. Master table

Material: 8 real original passages + 10 AI imitations (5 with no injected defect, 5 each with one named defect injected), 18 blocks anonymized and shuffled, no author name given.
Judges: 4 independent LLM instances, same protocol.

| Block | Truth | Type | Judge 1 | Judge 2 | Judge 3 | Judge 4 | Agreement | Characters |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | imitation | bad | B | B | B | B | unanimous | 70 |
| 2 | real | — | A | A | A | A | unanimous | 114 |
| 3 | real | — | A | A | A | A | unanimous | 103 |
| 4 | real | — | A | A | A | A | unanimous | 52 |
| 5 | real | — | A | A | A | A | unanimous | 89 |
| 6 | imitation | bad | B | B | B | B | unanimous | 67 |
| **7** | **imitation** | **good** | A | B | B | A | **split** | 67 |
| 8 | imitation | bad | B | B | B | B | unanimous | 73 |
| **9** | **imitation** | **good** | A | A | B | A | **split** | 71 |
| 10 | real | — | A | A | A | A | unanimous | 70 |
| **11** | **imitation** | **good** | A | B | B | A | **split** | 47 |
| 12 | real | — | A | A | A | A | unanimous | 81 |
| **13** | **imitation** | **good** | A | B | B | A | **split** | 61 |
| 14 | imitation | bad | B | B | B | B | unanimous | 74 |
| **15** | **imitation** | **good** | A | A | B | A | **split** | 51 |
| 16 | imitation | bad | B | B | B | B | unanimous | 81 |
| 17 | real | — | A | A | A | A | unanimous | 111 |
| 18 | real | — | A | A | A | A | unanimous | 82 |

## 2. Decisive metrics

| Metric | Result |
| --- | --- |
| **Class A misjudgment rate** (real text judged as imitation) | **0%** — all 4 judges got it right, 8/8 |
| **B-bad detection rate** (obvious defect injected) | **100%** — all 4 judges saw through it, 5/5 |
| **B-good seeing-through rate** (imitation with no injected defect) | **0%** (majority verdict) — the 4 judges together got only 6/20 right |
| Full-unanimity agreement rate across judges | 13/18 = 72% |
| **Distribution of the splits** | **100% concentrated in B-good** (all 5 blocks have splits) |

**Conclusion: 100% of the discriminating power comes from "is there an obvious defect," 0% from "does it resemble the author."**

## 3. What the judges relied on to see through "bad"

The bases the four judges used to see through the bad blocks are highly consistent; all of them are **enumerable surface markers**:

1. Naming emotions directly (惆怅／温暖／幸福／怀念／敬畏 — "melancholy / warm / happy / nostalgia / awe")
2. Spinning phrases that manufacture depth (「仿佛在诉说着什么」("as if telling of something"), 「令人不禁」("one cannot help but"))
3. Explanatory connectives (因为／所以／而且 — "because / so / moreover") — the judges' own words: 「把因果讲透，取消读者发现的空间」("it lays the causation out completely and cancels the reader's space for discovery")
4. An ending that rises into abstraction
5. No concrete physical object landing on the page

**Not one judge saw through a block by "this passage's rhythm is not like his."** That is to say: what they do is **defect detection**, not **style identification**. These two things are entirely different in a training setting — the former needs only a blacklist drawn up, the latter requires actually knowing how the author writes.

## 4. The more serious problem: the direction of the misjudgments is systematic

It is not "random error". List **every misjudgment** of the four judges, and the direction is entirely consistent — **what they reject is precisely the author's own features**:

| Judge | Misjudgment | The reason it gave | The fact |
| --- | --- | --- | --- |
| 3 | block 7 (my imitation) ruled B | "真实写法会让「花纹」本身被描述出来；这里只给出记忆的元陈述" ("real writing would have the 「pattern」 itself described; here only a meta-statement of the memory is given") | **The author himself uses this kind of meta-statement extensively**: 「其余的都记不清，数不出了」("the rest I can't recall, can't count them out"), 「也许十二红只是一个名目」("perhaps 'twelve reds' is only a name"), 「这一点是我没有记错的」("this one I did not misremember"). The judge took the author's core device for a flaw |
| 3 | block 9 (my imitation) ruled B | "节奏由氛围而非信息推进" ("the rhythm advances by atmosphere rather than by information") | the same type of criterion would strike the confirmed real passages 「有的样子蠢，有的秀气」("some look stupid, some elegant") and 「白嘴吃也可以」("eating it plain is fine too") just as hard |
| 2 | block 7 ruled B | 「有缠线的木轴，缠着黑线、白线」("there was a wooden spool wound with black thread and white thread") — **"现实里一个线轴只缠一色线，属对实物无经验造成的漏洞"** ("in reality a spool is wound with only one color of thread; this is a hole caused by no experience of physical objects") | this is a misreading of the text (two spools vs one spool); the judge is **fabricating linguistic evidence** to support a style judgment |
| 2 | block 13 ruled B | "结尾两句排比式的留白，为抒情预留空位，感伤来得过于准时" ("the last two sentences, a parallel-structure blank, reserve an empty slot for lyricism; the sentiment arrives too punctually") | the same class as the author's closures 「我也没问」("I didn't ask either") and 「白嘴吃也可以」("eating it plain is fine too") |
| 2 | block 11 ruled B | "「剩下薄薄一片」省掉「的」，是刻意制造的断裂" ("the 「剩下薄薄一片」 ('only a thin slice is left') drops the 「的」; this is a deliberately manufactured rupture") | judging precise language to be a deliberate rupture |

**This is far more serious than "judging inaccurately".** Judging inaccurately is only noise; systematic misjudgment **actively pushes the user away from the target author** — revising on feedback of this kind, the user will delete 「我也没问」("I didn't ask either") and fill the blank out into an explanation. This is the mechanism of "proxy drift" itself.

## 5. Two methodological problems (must be recorded)

**Problem one: 3 of the 4 judges violated the protocol and checked external sources.** Judges 2, 4 and 5 actively retrieved and verified the provenance of each duck-egg block in their reasoning (citing China Literature and Art Network, The Paper, People's Daily Online and others), confirming it was Wang Zengqi's original text. The protocol explicitly required "do not assume who the author is"; they went around this clause.

Consequence: the 100% correctness on Class A **cannot be credited entirely to style-identification ability** — part of it comes from memory retrieval. And once the corpus is switched to a non-famous piece, that part of the ability disappears. This also explains why the zero Class A misjudgment rate looks too good.

Worth noting is judge 3 — **it is the only one that did not look up external sources, and also the only judge that identified the good blocks**, but the criteria it used when identifying the good blocks ("meta-statement / posturing ending") are precisely wrong (see section 4).

**Problem two: length confounding.** B-good averages 59 characters, Class A averages 88 characters — shorter by one third. So the judges may have been discriminating by "too short, too thin" rather than by style. **This is a design flaw.** A same-length paired test was run separately to isolate this factor.

## 6. The shortcomings of the pre-registered rule (recorded honestly)

The pre-registered trigger condition for D2 was "Class A misjudgment rate ≥ 37.5%"; the measured value was 0%, so it was **not triggered**. D5 was not triggered either.

**But the real failure mode is not "judging the real as fake", it is "judging the competent as real".** I did not foresee this one when I pre-registered. The rule missed it; I supply it now, and write the reasoning process out in full as well, so that it does not turn into post-hoc criterion picking:

> **Corrected decision rule:** if "detection rate on defect imitations = 100%" and "seeing-through rate on defect-free imitations ≈ 0%", then what the model performs is **defect detection**, not style-attribution judgment. This capability is **not sufficient** to support "does it resemble the author" training feedback — because it will only tell the user "do not write those obvious AI accents", and will not tell the user "writing this way is more like him".
>
> **Action: delete the automatic judgment.** The system changes into a tool that does no judging: it only does splitting, mechanical prompting, mechanical comparison, and side-by-side presentation. Understanding and judging are left for the users to complete themselves.

This correction also satisfies the substance of D1 (the judgment is unstable: 100% of the splits concentrate on the only blocks that have any value).
