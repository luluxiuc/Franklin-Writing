# Research Conclusion: Can an LLM Judge "Does It Sound Like the Author"?

**Language:** English translation of the original Chinese report [`docs/研究/LLM能否判断像不像作者.md`](../研究/LLM能否判断像不像作者.md).
**Date:** 2026-09
**What this is:** the project's research conclusion. It is the basis for the shipped tool doing no scoring and no judgment of writing.

**Date:** 2026-09
**Research objective:** measure empirically how far LLMs agree with qualified readers across three kinds of judgment, and decide the project's direction on that basis.
**Conclusion:** an LLM can reliably detect **explicit defects**, and cannot reliably judge **style attribution**. The project moves to a pure-tool direction that does no judging.
**Main output:** `fk_tool/fk.py` (runnable prototype), [`docs/设计/无判断版设计-v1.0.md`](../设计/无判断版设计-v1.0.md) (design)

---

## 一、The three kinds of judgment, decomposed and measured

The original objective required breaking 「像不像作者」("does it sound like the author") into three layers and measuring each separately. What was actually measured is as follows.

### Layer 1: Verifiable features — the program is reliable, and it has to be done by the program

No LLM is needed. Everything here is deterministic computation:

| Feature | Wang Zengqi, 《端午的鸭蛋》("Duck Eggs of the Dragon Boat Festival"), measured |
| --- | --- |
| Sentence length | mean 17.8 characters, SD 10.0 |
| **Clause length** | **mean 7.5 characters** |
| Longest run of consecutive short sentences (≤8 characters) | **2 sentences** |
| Commas / periods (per 100 characters) | 6.9 / 4.7 |
| Explicit connective density | 0.74 per 100 characters |
| Words that name an emotion directly | 2 occurrences (neither a "stating an emotion" usage) |

**This layer also overturned a general conclusion.** If you describe this author from impression, the most natural thing to say is 「善用短句」("skilled use of short sentences") — the measurements do not support it: mean sentence length 17.8 characters, longest run of consecutive short sentences only 2. The real feature is at the next unit down: **mean clause length 7.5 characters, and a run of 8 consecutive clauses of ≤6 characters occurs.** 「短句」("short sentences") is a label any model will hand out, and its **direction is wrong**.

**Conclusion: Layer 1 has to be executed by a program, and it can only describe, not judge.**

### Layer 2: Intersubjective judgment — the measurements do not support automatic judgment

18 anonymized text blocks (8 real original passages + 10 AI imitations, of which 5 have no injected defect and 5 each have one named defect injected) were given to 5 independent LLM judges to decide attribution.

| Judge | Real judged A | Clean imitation caught | Total correct |
| --- | --- | --- | --- |
| Judge 1 | 8/8 | **0/5** | 13/18 |
| Judge 2 | 8/8 | 3/5 | 16/18 |
| Judge 3 | 8/8 | 5/5 | 18/18 |
| Judge 4 | 8/8 | **0/5** | 13/18 |
| Judge 5 | 8/8 | **0/5** | 13/18 |

**Decisive metrics:**

- Real text misjudged as imitation: **0%** (all 5 judges, 8/8)
- Imitations with an obvious injected defect caught: **100%** (all 5 judges, 5/5)
- **Clean imitations caught: 0%** (majority verdict 0/5; 3 of the 5 judges scored 0/5)

**The distribution of the splits is too precise to be coincidence:** the 5 judges agree closely on 「什么是明显的 AI 腔」("what is an obvious AI accent"), and 100% of the splits fall on text that is "written decently, but I am not sure whether it is him" — the only class that has any value.

**Mechanism:** what the judges rely on to catch the defects is an **enumerable set of surface markers** —

1. Naming emotions directly (惆怅／温暖／怀念／敬畏 — "melancholy / warm / nostalgia / awe")
2. Spinning phrases that manufacture depth (「仿佛在诉说着什么」("as if telling of something"), 「令人不禁」("one cannot help but"))
3. Explanatory connectives (因为／所以／而且 — "because / so / moreover")
4. An ending that rises into abstraction
5. No concrete object landing on the page

**Not one judge caught a block by "this passage's rhythm is not like him."** What they do is **defect detection**, not **style identification**.

### Layer 3: The remaining subjective part — not measured, and now shown not to be worth automating

**The "agreement rate with a qualified human consensus" required by the objective was not completed.** The pre-registered plan stated this metric, but in execution every judge was an LLM — that is circular. The tooling is ready (`_capability/human_kit.py`, which can generate annotation material containing no answers, collect human annotations, and compute pairwise human agreement rates for comparison against the LLMs), but no human data has been collected yet.

**Nevertheless the evidence the decision rests on is already sufficient, for the following reasons:**

1. The failure of Layer 2 can be determined without Layer 3 — the model has no discriminating power at all on "a competent alternative way of writing."
2. The person who ran the experiment is himself one sample of a "qualified reader": **I could not reliably distinguish those 5 imitations of mine from the original text.** I got 0/5 (when building the material I of course knew the answers, but on reading it back I could not point out where the differences lay).
3. More decisive: **once the model starts to misjudge, the direction of its misjudgments is systematic** (see section 二). This point alone, without any human baseline, is enough to rule out automatic judgment.

---

## 二、A more serious problem than "judging inaccurately": the direction of the misjudgments is systematic

Judging inaccurately is only noise. What the measurements show is a **consistent bias** — what the judges reject is precisely **the author's own features**:

| Judge | Stated reason for the misjudgment | The fact |
| --- | --- | --- |
| 3 | ruled "a meta-statement that gives only the memory" a flaw | **the author uses them extensively**: 「其余的都记不清，数不出了」("the rest I can't recall, can't count them out"), 「也许十二红只是一个名目」("perhaps 'twelve reds' is only a name"), 「这一点是我没有记错的」("this one I have not misremembered") |
| 3 | ruled "the rhythm advances by atmosphere rather than by information" | the same criterion would strike the confirmed real passages just as hard: 「有的样子蠢，有的秀气」("some look stupid, some elegant"), 「白嘴吃也可以」("eating it plain is fine too") |
| 2 | 「有缠线的木轴，缠着黑线、白线」("there was a wooden spool wound with black thread and white thread") — called it "in reality a spool is wound with only one color of thread, a flaw caused by no experience of physical objects" | **this is a misreading of the text** (two spools vs one). The judge **fabricates linguistic evidence** to support a style judgment |
| 2 | ruled "the last two sentences, a parallel-structure blank, the sentiment arrives too punctually" | the same class as the author's closures 「我也没问」("I did not ask either") and 「白嘴吃也可以」("eating it plain is fine too") |
| 2 | ruled "dropping the 「的」 is a deliberately manufactured rupture" | judging precise language to be a deliberate rupture |

**This explains an intuition every qualified reader has: the reasons the judges give read as highly persuasive.** "Cancels the reader's own space for discovery," "judging precise language to be a deliberate rupture" — these sentences sound like something an expert would say. **But that fluency is exactly where the danger lies:** the user has no ability to tell which judgment is the right one, and an unreliable judgment wearing the coat of fluency is more harmful than obvious nonsense.

**Corollary:** if judgments of this kind were wired into training feedback, the result of the user revising accordingly would be **deleting 「我也没问」("I did not ask either"), filling the blank out into an explanation, and adding subjects and connectives to the sentences** — becoming more and more like an ordinary writer whose prose is smooth and correct. This is the mechanism of "proxy drift" itself.

---

## 三、Methodological problems (must be recorded)

**Problem 1: 4 of the 5 judges violated the protocol and checked external sources.**

Judges 2, 4 and 5 (and judge A in the same-length paired test) actively searched for and verified the provenance of each duck-egg block in their reasoning, citing links from China Literature and Art Network, The Paper, Wenhui, People's Daily Online and others, and confirming it was Wang Zengqi's original text.

The consequences are twofold:

1. **The 100% correctness on Class A cannot be credited entirely to style-identification ability** — part of it comes from memory retrieval. Switch to a non-famous corpus and that part of the ability disappears.
2. **The "correct" result of the same-length paired test is fake.** That test balanced the two passages strictly (47 characters vs 47 characters, 51 characters vs 51 characters), and judge A got it right 2/2 — but the reason it gave was "B's two sentences are **word-for-word identical** to the original, so this is an excerpt from the original," with a search link attached. It admitted itself that for the second pair "I cannot retrieve a verifiable original … I can only judge by the writing," and in that pair it ruled **a blank / closing by negation** to be an imitation feature — and that is the author's own device.

**The only judge that did not look up external sources (judge 3) is the only one that identified the clean blocks — but the criterion it used was wrong** (see the first row of section 二).

**Problem 2: length confounding (corrected).** In the first version of the material, B-good averaged 59 characters vs 88 characters for Class A — shorter by one third. To rule out "the judges merely disliked the shortness," two supplements were run: the same-length paired test (strictly balanced to the same character count) and a normalized feature comparison.

| Group | Concrete-object density | Verb density | Connectives | Emotion words |
| --- | --- | --- | --- | --- |
| A real | 4.7 | 4.1 | 0.39 | 0.25 |
| B-good, clean imitation | **9.2** | **6.2** | 0.00 | 0.00 |
| B-bad, injected defect | 2.4 | 1.1 | **4.38** | **1.40** |

**My imitations have a denser concrete-object count than the original** (9.2 vs 4.7), so the alternative explanation "the judges discriminate by how thin or thick the information is" is ruled out. What is genuinely mechanically separable is **connectives and emotion words**: high in the bad group, zero in the good group — zero, just as in the original.

**The conclusion tightens to: the only thing the judges can reliably detect is explicitly injected defect markers; once an imitation draws level with the original on those two items, the verdict drops to random.**

**Problem 3: the pre-registered rule missed the real failure mode (recorded honestly).**

The pre-registered D2 trigger condition was "Class A misjudgment rate ≥ 37.5%"; the measured value was 0%, so it was **not triggered**. The real failure mode is "**judging a competent imitation to be real**" (a miss), and I did not foresee it when pre-registering. The corrected decision has been written into `_capability/实验一最终结果.md` together with the reasoning, so that it does not become post-hoc criterion picking.

---

## 四、Final direction

**Move to a pure tool that does no judging.** Grounds:

1. 100% of the discriminating power comes from "is there an explicit defect," 0% from "does it sound like the author" — **this layer of capability is not enough to support training feedback**, because it can only tell the user "do not write those obvious AI accents," and can never say "writing this way is more like him."
2. The direction of the misjudgments is systematically biased toward "a generic good prose style"; wired into feedback it would actively push the user away from the target author.
3. With a famous-piece corpus there is still the shortcut of memory retrieval; **with a non-famous corpus the ability can only be weaker** — and what users actually need is precisely a non-famous one.

**What was deleted** (the only part of v0.3 that could go off course): the comparison engine, the author-model judgment layer, gap ranking, convergence trend, capability conclusions. With those gone, the drift risk is zero, and sentinel regression and calibration sets are no longer needed either.

**What was kept and has been implemented:** splitting, mechanical prompting, forced departure from the original, mandatory delay, side-by-side comparison, a coverage checklist, history records. See `fk_tool/README.md`.

---

## 五、What has not been done yet

1. **Human annotation.** `_capability/human_kit.py` can already generate annotation material and compute human agreement rates. It now has two uses: (a) supplying the "human consensus" denominator missing from the objective; (b) if the human agreement rate is itself low, further proof that this layer of judgment cannot be automated in principle. **The recommendation is to find at least 3 qualified readers and have each annotate once.**
2. **Retest on a non-famous corpus.** Re-run with a contemporary author's corpus that the model has no memory of, stripping out the retrieval channel, to measure pure in-text judgment ability. The expectation is that it will be lower.
3. **Experiment 2 (single-sentence discrimination)** is designed but not run: pair the author's original sentences with rewrites that have "the same content, the same character count, the same concrete objects, with only the writing changed," and make it a two-way choice. This is the test closest to what users actually need.
