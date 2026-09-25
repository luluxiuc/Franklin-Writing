# Why This Project Does No LLM Judgment Scoring

**A decision report based on measured data**

> *Translator's note: 句 is rendered "sentence" and 小句 "clause" (the comma-delimited unit), because sections 2 and 3 turn on that distinction. Where the original uses the first-person singular, the singular is kept.*

**Language:** English translation of the original Chinese report [`docs/研究/为什么不做LLM判断评分.md`](../研究/为什么不做LLM判断评分.md).
**Date:** 2026-09
**Status:** Decision report — this decision is in force, and is the reason the shipped tool does no judging.

---

## Abstract

The original design at the core of this project was a "作者近似度" ("author similarity") scoring and gap-diagnosis engine: the user copies a model passage, and the AI judges where it does not resemble the author, why it does not, and what to change next. This document reports why that design was abandoned.

The conclusion is: **abandon it, and not because it does not do the job well enough, but because we measured it doing something different from what it claims to be doing.**

An experiment with 5 independent LLM judges, 18 anonymous text blocks, and pre-registered decision criteria showed:

| Metric | Result |
| --- | --- |
| Real text misjudged as imitation | **0%** (all 5 judges got 8/8 right) |
| Imitations with an obvious injected defect seen through | **100%** (all 5 judges saw through 5/5) |
| **Imitations with no injected defect seen through** | **0%** (majority verdict; 3 of the 5 were 0/5) |

The first three rows look like "能力很强" ("very capable"). The third row shows that it is not doing style judgment but **defect detection** — relying on an enumerable blacklist (naming emotions directly, spinning phrases, explanatory connectives, abstract endings), not on "像不像这位作者" ("whether this resembles this author").

More critical is the direction of the misjudgment: what the judges rejected is precisely **the author's own signature devices**. Some judges ruled "留白收束" ("closure by leaving a blank") and "自我不确定的元陈述" ("meta-statements of self-doubt") to be flaws, and those are exactly this author's core traits; another judge **fabricated linguistic evidence** (claiming "一个线轴只缠一色线" ("a spool is wound with only one color of thread")) to support a style judgment.

Therefore the direction of this project was fixed as: **build a pure tool only, to help users use the Franklin writing method more conveniently. The system handles splitting, prompting, hiding, delaying, and recording; understanding and judging are left entirely to the users themselves.**

Every number in this document comes from this round of measurement; the data sources and the recomputable scripts are in [appendix-measured-data.md](appendix-measured-data.md).

---

## 1. Where the problem is: a self-reinforcing loop

The core loop of the Franklin writing method is: **model passage input → reconstruct away from the original → compare with the original → find the gap → correct**.

The original AI-ified design had the model take over the "比较" ("compare") and "发现差距" ("find the gap") steps in it. Structurally this introduces a danger:

```
the model's understanding of the author (proxy metric)
        ↓  the user edits toward it
    the user's actual writing
        ↓  the model keeps judging with the same understanding
    the deviation is self-confirmed
```

**The harder the user tries to satisfy the system, the further he moves from the author.** This process needs no fault at all — as long as a difference exists between the "代理指标" ("proxy metric") and "作者本人" ("the author himself"), the training pressure steadily pushes the user toward the proxy metric.

We initially treated it as a theoretical risk. The measurements show that it does happen, and that its direction is predictable.

---

## 2. Measurement: what the purely computational part exposed

One boundary first: **all four failures in this section are produced by hand-written threshold rules; no LLM took part in the judging at the time.** What it proves is that "用阈值冒充判断会跑偏" ("passing thresholds off as judgment goes off course"); it cannot be used to assess LLM capability. The measurement of LLMs is in section 3.

To avoid dispute, we first did something that needs no model at all: computed every feature of one real prose piece. The corpus is Wang Zengqi's 《端午的鸭蛋》("Duck Eggs of the Dragon Boat Festival"), 1351 characters, purely local computation, zero model calls.

### 2.1 First finding: even "这位作者善用短句" ("this author favors short sentences") is wrong

If you describe this author from impression, the most natural thing to say is "善用短句、节奏短促" ("favors short sentences, rhythm clipped and brief"). The measurements do not support it:

| Metric | Measured value |
| --- | --- |
| Sentence length | mean **17.8** characters, SD 10.0, shortest 1 character, longest 43 characters |
| **Longest run of consecutive short sentences (≤8 characters)** | **2 sentences** |
| **Clause length** | mean **7.5** characters |
| Total clauses / total sentences | 179 / 76 (2.4 clauses per sentence on average) |

**At the sentence level, his rhythm is not the least bit clipped.** The real feature is at the next level down: he splits sentences into clauses of 3–10 characters and strings them together quickly with commas. Paragraph 1 even contains **8 consecutive clauses of ≤6 characters**.

This distinction is substantive. "短句" ("short sentences") is a generic label that any model will hand out off the cuff, and its **direction is wrong**. If you make it the training target, the user will go and write line after line of short sentences — which is exactly not this author.

**This is the first empirical instance of proxy drift, and it appears in the most basic step: describing the author.**

### 2.2 Second finding: the system judged the author's own text as "偏离作者" ("deviating from the author")

We ran a sentinel test: we fed **the original's own sentence** (the opening of paragraph 1, 8 short clauses, precisely the densest form of that feature) into the decision engine.

Result: **2 important issues + 2 minor issues.**

| Metric | Sentinel result | Real cause |
| --- | --- | --- |
| List-style opening | judged 0/7 sentences | **Wrong unit of measurement**: at the clause level this feature accounts for 20% (13/65), at the sentence level for 31% (8/26); the sentinel consists of 8 short clauses and was missed in full because it was split by sentence |
| Rhythm fluctuation | judged "过于均匀" ("too uniform") | **SD changes with sample size**: the 2.4 over 7 clauses and the 3.8 over 179 clauses are not comparable; the metric was not normalized |
| No question appeared | judged a deviation | the original's 4 questions are distributed across 76 sentences; most paragraphs have no question to begin with; **treating "没有出现" ("did not appear") as a defect** |
| No modal particle appeared | judged a deviation | same as above; a low-frequency feature treated as a mandatory item |

**All four are structural false positives; not one of them can be fixed by tuning thresholds.** They are not parameter problems but modeling errors of the kind "把全体统计分布里的稀有项当成逐段必备项" ("treating a rare item in the overall statistical distribution as a per-paragraph mandatory item") and "在错误的层级上取样" ("sampling at the wrong level").

### 2.3 Third finding: the rules punished a word the author himself used

Following the measured fingerprint, we deliberately built a "更像" ("more similar") imitation (mean clause length 4.3 characters, more clipped than the author's 7.5). It was judged a **核心问题** ("core issue"):

> 情绪表达：出现直接情绪词 [('高兴', 1)] ("Emotional expression: a direct emotion word appears [('高兴', 1)]")

That sentence was "孩子一高兴，掏出来，吃了" ("the child, happy, took it out and ate it") — **this is the original's own sentence** 「什么时候孩子一高兴，就把络子里的鸭蛋掏出来，吃了」("whenever the child was happy, he took the duck egg out of the net and ate it"). Same author, same word, same usage, same syntactic position.

Incidentally, the criterion itself does not hold either. The whole text has only 2 instances of "高兴" ("happy"), and neither states an emotion:

- 「我对异乡人称道高邮鸭蛋，是**不大高兴**的」("when I praise Gaoyou duck eggs to people from other places, I am **not altogether happy**") — negated, a judgment of attitude
- 「什么时候孩子**一高兴**……」("whenever the child **was happy**…") — used as an adverbial of condition (一……就……, "as soon as … then …")

**The correct formulation is "不把情绪词用作主句谓语" ("do not use an emotion word as the predicate of a main clause"), not "不写情绪词" ("do not write emotion words").** Judging with a word list is bound to hit the wrong targets.

### 2.4 Fourth finding: the badly written draft was judged more leniently

| Draft | Fingerprint | Verdict |
| --- | --- | --- |
| User's imitation (AI-generalized style) | 251 characters, **sentence length 35.9 characters**, connective density **2.39 per 100 characters** (author 0.74) | 1 core + 2 important + 3 minor |
| Imitation (built to the measured fingerprint) | 86 characters, clauses 4.3 characters, sentence length 7.8 characters | **1 core** + 2 important + 2 minor |

**The one closer to the author received about the same number of severe issues as the badly written one.**

### 2.5 Summary: the direction of punishment is one-sided

| Feature punished by the system | The author's own measured value |
| --- | --- |
| Smooth long sentences, explicit connectives (因为／所以／因此 — "because / so / therefore") | connective density only **0.74 per 100 characters** |
| Complete subjects, everything spelled out sentence by sentence | heavy subject omission ("系百索子" ("tie on the hundred-cord"), "出鸭" ("the ducks come out"), "鸭多，鸭蛋也多" ("many ducks, and many duck eggs too")) |
| Degree adverbs, explanatory phrasing | almost never stacked |
| Abstract generalization | 47 kinds of concrete object, 165 occurrences (about one physical object every 8 characters) |

**This decision set is in effect rewarding the generic good style — "通顺、完整、有逻辑、有解释" ("fluent, complete, logical, explanatory") — and punishing this author's real features.**

What a real user will do in the face of this feedback is predictable: add connectives, write the sentences out in full, pile up fewer physical objects, state the emotions outright. **He will become more and more like an ordinary writer whose prose is smooth and correct.**

---

## 3. Measurement: how good LLM judgment actually is

The previous section was all hand-written rules. **How capable LLMs are has to be measured separately.**

### 3.1 Experimental design

| Item | Content |
| --- | --- |
| Material | 8 real passages from the original + 10 AI imitations (5 with **no injected defect**, 5 each with 1 named defect injected) |
| Presentation | 18 blocks, anonymized and shuffled (fixed seed); no author name, no reference text |
| Protocol | explicitly required "不要假设作者是谁" ("do not assume who the author is"); the basis must point to a concrete linguistic fact; a verdict of imitation must quote the most suspicious fragment |
| Judges | 5 independent LLM instances, same protocol |
| Decision criteria | frozen before seeing any result ([experiment-data/PREREGISTRATION.json](experiment-data/PREREGISTRATION.json)) |

**The 5 injected defects** are respectively: explicit connectives + abstract evaluation; direct statement of emotion + "温暖/幸福/怀念" ("warmth / happiness / nostalgia") + degree adverbs; smooth long sentences + metaphor substitution + a raised conclusion ("仿佛在诉说着什么" ("as if telling of something")); direct entry into emotion ("说不出的惆怅" ("an indescribable melancholy") + "眼角有些湿润" ("the corners of the eyes a little moist")); explanatory causation ("因为年代久远" ("because of the great age")) + "令人不禁" ("one cannot help but") + "仿佛藏着另一个世界" ("as if hiding another world").

### 3.2 Results

| Block | Truth | Type | J1 | J2 | J3 | J4 | J5 | Agreement |
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

**Decisive metrics:**

| Metric | Result |
| --- | --- |
| Class A misjudgment rate (real judged as imitation) | **0%** — all 5 judges got 8/8 right |
| B-bad detection rate (obvious defects injected) | **100%** — all 5 judges saw through 5/5 |
| **B-good seeing-through rate (no injected defect)** | **0%** (majority verdict; 3 of the 5 were 0/5) |
| Full-unanimity agreement rate across judges | 13/18 = 72% |

**The distribution of the splits is too precise to be a coincidence: the 5 judges agree closely on "什么是明显的 AI 腔" ("what counts as an obvious AI accent"), and 100% of the disagreements fall on text that is "写得不错但不确定是不是本人" ("written well, but I am not sure whether it is him") — the only class that has any value.**

### 3.3 Defect one: it does defect detection, not style identification

The bases the judges used to see through the bad blocks are highly consistent, and all of them are **enumerable surface markers**:

1. Naming emotions directly (惆怅／温暖／幸福／怀念／敬畏 — "melancholy / warmth / happiness / nostalgia / awe")
2. Spinning phrases that manufacture depth ("仿佛在诉说着什么" ("as if telling of something"), "令人不禁" ("one cannot help but"))
3. Explanatory connectives (因为／所以／而且 — "because / so / moreover") — the judge's own words: "把因果讲透，取消读者发现的空间" ("laying out the causation completely, canceling the space for the reader to discover")
4. An ending that rises into abstraction
5. No concrete object landing on the page

**Not one judge saw through a block by "这段的节奏不像他" ("this passage's rhythm is not like his").**

These are two different things. Defect detection needs only a blacklist; style identification requires actually knowing how the author writes. **In a training setting, a blacklist can tell the user "不要写那些明显的 AI 腔" ("do not write those obvious AI accents"), and it can never say "这样写更像他" ("writing this way is more like him").**

**The alternative explanation has been ruled out.** We worried that "裁判只是嫌我的模仿稿太短太薄" ("the judges just find my imitations too short and too thin"). A comparison of normalized features shows:

| Group | Concrete-item density | Verb density | Connectives | Emotion words | Characters |
| --- | --- | --- | --- | --- | --- |
| A real (8 passages) | 4.7 | 4.1 | 0.39 | 0.25 | 87.8 |
| B-good (5 passages) | **9.2** | **6.2** | 0.00 | 0.00 | 59.4 |
| B-bad (5 passages) | 2.4 | 1.1 | **4.38** | **1.40** | 73.0 |

**My imitation's concrete-object density is higher than the original's** (9.2 vs 4.7), so the "信息量薄厚" ("how thin or thick the information is") explanation does not stand. What is genuinely mechanically separable is **connectives and emotion words**: high in the bad group, zero in the good group — zero, same as the original.

**The conclusion tightens to: the only thing the judges can reliably detect is explicitly injected defect markers; once an imitation draws level with the original on those two items, the verdict drops to random.**

### 3.4 Defect two: the direction of the misjudgment is systematic

This one is far more serious than "判不准" ("judging inaccurately"). Inaccuracy is only noise; what the measurements show is a **consistent bias** — what the judges rejected is precisely the author's own features:

| Judge | Reason given for the misjudgment | The fact |
| --- | --- | --- |
| 3 | ruled "只给记忆的元陈述" ("a meta-statement that gives only the memory") a flaw: "真实写法会让「花纹」本身被描述出来" ("real writing would have the 花纹 ("pattern") itself described") | the author uses meta-statements extensively: 「其余的都记不清，数不出了」("the rest I can't recall, can't count them out"), 「也许十二红只是一个名目」("perhaps 'twelve reds' is only a name"), 「这一点是我没有记错的」("this one I have not misremembered") |
| 3 | ruled "节奏由氛围而非信息推进" ("the rhythm advances by atmosphere rather than by information") | the same criterion would hit the confirmed real passage just as hard: 「有的样子蠢，有的秀气」("some look stupid, some look elegant"), 「白嘴吃也可以」("eating it plain is fine too") |
| 2 | 「有缠线的木轴，缠着黑线、白线」("there was a wooden spool wound with black thread and white thread") — called it "现实里一个线轴只缠一色线，属对实物无经验造成的漏洞" ("in reality a spool is wound with only one color of thread; this is a hole caused by no experience of physical objects") | **a misreading of the text** (two spools vs one), **fabricating linguistic evidence** to support a style judgment |
| 2 | ruled "结尾两句排比式的留白，感伤来得过于准时" ("the last two sentences, a parallel-structure blank; the sentiment arrives too punctually") | the same class as the author's closures 「我也没问」("I didn't ask either"), 「白嘴吃也可以」("eating it plain is fine too") |
| 2 | ruled "省掉「的」，是刻意制造的断裂" ("omitting 的 is a deliberately manufactured rupture") | judging precise language to be a deliberate rupture |

**A user who revises on feedback of this kind will delete "我也没问" ("I didn't ask either"), fill the blank out into an explanation, and add subjects and connectives to the sentences.** This is exactly the path predicted in section 2, except that this time the agent is the model's style judgment rather than a hand-written threshold.

### 3.5 Defect three: fluency makes the problem harder to notice

All the judges wrote very persuasive reasons. "取消读者自己发现的空间" ("canceling the space for the reader to discover"), "把精确的语言判断为刻意的断裂" ("judging precise language to be a deliberate rupture") — these sentences read like something an expert would say.

**But this fluency is exactly where the danger lies.** The user has no ability to tell which judgment is the right one. An unreliable judgment that stammers will put the user on guard; if it is professionally worded, clearly organized, and quotes sentences from the original, the user will accept it.

**Fluency is not reliability, and an unreliable judgment wearing the coat of fluency is more harmful than obvious nonsense.**

### 3.6 Defect four: with a famous-piece corpus there is one more shortcut

3 of the 5 judges actively searched for and verified the source in their reasoning, citing links from China Literature and Art Network, The Paper, and others to confirm it was the original; the judges of the supplementary experiment did the same, citing Wenhui and giving the original's next sentence. The protocol explicitly required "不要假设作者是谁" ("do not assume who the author is"); they went around it.

The consequences are twofold:

1. **The 0% Class A misjudgment rate cannot be credited entirely to style-identification ability**; part of it comes from memory retrieval.
2. **The supplementary "同长度配对检验" ("same-length paired test") therefore fails.** We strictly balanced the original and the imitation to the same character count (47 vs 47, 51 vs 51 characters), and the judge got it right 2/2 — but the reason it gave was "乙的两句与原文**逐字一致**，属原文截取" ("B's two sentences are **word-for-word identical** to the original, so this is an excerpt from the original"), with a search link attached. It bypassed the style comparison and looked the source up directly.

Worth noting: in the second pair that judge admitted "检索不到可核原文……只能靠写法判断" ("I cannot retrieve a verifiable original … I can only judge by the writing"), and in that pair its reasoning immediately turned to "留白／否定收束" ("a blank / closure by negation") — and it called that "人类作者常用的收束方式" ("a way of closing that human authors commonly use"). **Within one and the same judgment, it treated the author's device as normal writing for a human author, and at the same time counted it as a flaw in an imitation.**

**And what the user actually needs is precisely non-famous corpora.** If it is like this with a famous piece, it will only be weaker with a non-famous one.

---

## 4. Why "换个更强的模型" ("switching to a stronger model") does not solve it

This is the point that most needs to be made clear. The failures above look like insufficient capability, and the conclusion "等模型变强就好了" ("it will be fine once the model gets stronger") comes easily. We do not think so, for four reasons.

### 4.1 Training can only optimize toward the proxy metric; this is structural

A model never directly compares "你的文本" ("your text") with "作者本人" ("the author himself"); what it compares is "你的文本" ("your text") with "它对作者的理解" ("its understanding of the author"). The gap between those two does not disappear because the model gets stronger — a stronger model only produces a finer proxy metric, **and a finer proxy metric is still a proxy metric**.

Section 2.1 already demonstrated this: even the most basic description, "这位作者善用短句" ("this author favors short sentences"), is wrong. This is not the model being insufficiently strong; it is that **the description itself may point at the wrong level**.

### 4.2 The objective function itself is flawed

We easily take "训练用户像作者" ("training the user to be like the author") to be a well-defined optimization problem. It is not. **A reader who has only a single text (whether a model or a real person) cannot see a large part of the information that decides "像不像" ("whether it resembles him"):** the choices the author did not make, whom else he was in dialogue with, what he deliberately avoided.

**So some disagreements are not a defect of the model but a defect of the task.** Automating this kind of thing amounts to passing "我对作者的解读" ("my reading of the author") off as "作者本人" ("the author himself").

### 4.3 The remaining subjective layer is inconsistent even between real people

This point deserves separate emphasiz: **even two trained human readers are often inconsistent about "这一处是否捕捉到了作者的笔法" ("whether this spot has captured the author's handling").** More precisely, the disagreements concentrate on one class of text — **text that is competently written, but that you are not sure is his** — which is to say, all the text a user will meet in training.

If humans are inconsistent among themselves, then:

- aligning the model with a "人类共识" ("human consensus") — that consensus does not exist;
- having the model output a judgment amounts to giving an authoritative-sounding answer to a question that has no standard answer.

**We do not even need to wait for human annotation data to confirm this** — the performance of the executor of this report throughout the experiment is the example: I built those imitations (so I knew the answers), yet on reading them back I could not point out where they differ from the original. Out of three people, I got 0/5 right.

### 4.4 The cost of the misjudgment direction is asymmetric

Suppose a future model's accuracy rises to 85%. That looks good enough. But look at the cost distribution:

- **Judged right**: the user gets one useful hint.
- **Judged wrong**: the user deletes a piece of writing that was **correct to begin with** (say, a blank like "我也没问" ("I didn't ask either")), or adds an explanatory sentence.

The second kind of loss is irreversible, and the user has no way to notice it — he has no reason to doubt a judgment that is professionally worded, quotes the original, and is clearly organized.

**In the matter of "帮助用户学会写作" ("helping the user learn to write"), one piece of wrong guidance is worse than no guidance.** This is the decisive reason we ultimately abandoned scoring: not that it is not accurate enough, but that its errors, in a way the user cannot identify, point steadily in the same wrong direction.

### 4.5 And the tool approach costs zero

Abandoning judgment costs the user nothing, because the driving force of the Franklin method was never in the judgment to begin with.

The research conclusion the research report itself cites is: **AI 提供更多反馈并不必然带来更好的修改，反馈的有效利用与学习者参与程度密切相关。** ("more feedback from AI does not necessarily lead to better revision; how effectively the feedback is used is closely tied to the learner's degree of engagement"). In other words, the main source of learning is the **actions themselves** — "阅读—脱离原文重构—延迟—修改" ("read — reconstruct away from the original — delay — revise") — and AI judgment is only seasoning.

And Franklin himself practiced exactly this way — **his "评判" ("judging") was done by himself**: leave the outline for a few days, rewrite from memory, then compare side by side with the original.

So the tool approach:

| | With AI judgment | Pure tool |
| --- | --- | --- |
| Core mechanism (away from the original, delay, side-by-side comparison) | retained | **retained** |
| Drift risk | high, and measured | **zero** |
| Cost | several model calls per round | **near zero (the prompt is mechanical extraction)** |
| Privacy | requires a network connection | **can be fully offline** |
| The user's responsibility for judgment | replaced by the system | **returns to himself** |
| Honesty | the system must keep proving it has not gone off course | **the system never claims to be judging** |

**Conclusion: delete the judgment; the gains (risk to zero, cost to zero, better privacy, honesty) far outweigh the loss (losing an unreliable piece of guidance).**

---

## 5. The final decision

### 5.1 What we will not do

| Module in the v0.3 design | Disposition | Reason |
| --- | --- | --- |
| Comparison engine (where it does not resemble / why / how to change) | **deleted** | measured to be defect detection, and its misjudgment direction systematically favors a generic prose style |
| Author model layer 2 (the LLM-judged items) | **deleted** | same as above |
| Author model layer 4 (difference from others of the same kind) | **deleted** | depends on judgment |
| The "作者区间命中率" ("author-range hit rate") of style transfer | **deleted** | depends on judgment |
| Focus items, gap ranking, convergence trend | **deleted** | all depend on judgment |
| Capability conclusions in the long-term archive | **deleted** | same as above |

**These deleted parts happen to be the only part of the original design that could go off course.**

### 5.2 What we will do

**Build a pure tool only, to help users use the Franklin writing method more conveniently.**

The system handles: **splitting, prompting, hiding, delaying, recording.**

**Understanding and judging are left entirely to the users themselves.**

Key design points:

- **The prompt becomes a list of mechanically extracted content fragments** (e.g. `家乡 / 端午 / 多风俗 / 索子 / 丝线拧成 / 小绳 / 手腕` — "hometown / Dragon Boat Festival / many customs / cord / twisted from silk thread / small rope / wrist"). These fragments are all contiguous substrings that genuinely exist in the original; they contain no statement about how to write and no name of any rhetorical device. This way it cannot carry any interpretation, and it barely leaks any wording.
- **Side-by-side comparison goes from an auxiliary feature to the main body of the product.** Original and user draft aligned sentence by sentence, on the same screen and at the same width, with the fragments not hit marked automatically. **The user sees the differences and says them himself.**
- **Mandatory "我的观察" ("my observations")**: not writing them does not count as complete. With AI judgment deleted, observation is the only learning action.
- **Mandatory delay**: after submitting, the default wait is 10 minutes before the original can be seen. This is the core action of the Franklin method.
- **The archive does not generalize**: it does not tell the user "你习惯性遗忘环境描写" ("you habitually forget to describe the setting") — that too is a judgment. Instead it lays out the raw data and lets the user see the pattern himself.

The prototype is implemented and verified: `fk_tool/fk.py`. Zero model calls, works offline, single file, depends only on the Python standard library.

### 5.3 This decision does not depend on any unfinished experiment

The measurement in section 3.2 is already sufficient to decide: **100% of the discriminating power comes from "有没有明显缺陷" ("is there an obvious defect"), 0% from "像不像作者" ("does it resemble the author").** That layer of capability is not enough to support training feedback.

One metric was prepared but never collected: **"与合格人类共识的一致率" ("agreement rate with a qualified human consensus").** The plan was to measure it, but in execution all the judges were LLMs, which is circular. The tooling is ready ([experiment-data/human_kit.py](experiment-data/human_kit.py), which can generate annotation material containing no answers, compute pairwise human agreement rates, and compare them against the LLM judges); it needs 3 or more qualified readers to annotate once each.

**But section 4.3 has already explained that this data can only strengthen the conclusion, not overturn it**: because that judgment is itself unstable between humans, and the disagreements concentrate precisely on the class of text the user will meet.

---

## 6. What this decision loses

For honesty's sake, the cost has to be written down.

**What is lost:**

1. **One possible shortcut.** With judgment, the user might be told outright "这里你写成了直接说明情绪" ("here you have written it as a direct statement of emotion"); without judgment, he has to see it himself. For a beginner whose observation is not yet formed, this is indeed a loss.
2. **A feeling of "被陪伴" ("being accompanied").** Feedback brings an immediate response. In the tool approach, the response comes from the original text itself.
3. **An automatically generated training plan.** What to practice next round is now for the user to decide.

**What is kept:**

1. **Not one learning mechanism is lost.** Active reconstruction, delay, side-by-side comparison, repetition — all retained.
2. **The training pressure returns to where it should have been.** Franklin had no AI, and his method still holds up.
3. **A system that will not lie to you.** It never claims to be judging, and therefore will not quietly shape the user in a wrong direction.

**We judge this trade to be worth it**: an unreliable piece of guidance exchanged for a system that will not lead people astray.

---

## 7. Follow-ups

**Done:**

- Research conclusion and all data: [llm-authorship-judgment.md](llm-authorship-judgment.md), [appendix-measured-data.md](appendix-measured-data.md)
- The no-judgment design: [docs/设计/无判断版设计-v1.0.md](../设计/无判断版设计-v1.0.md)
- Runnable prototype: `fk_tool/fk.py` (including `README.md`, `smoke_test.py` with 11 assertions, `selftest.py` with 7 constraint self-checks, all passing)
- **Web version of the tool**: `app/` (runs locally, zero dependencies, works offline, all data stays local)

**To do:**

1. Send the human annotation material to 3 or more qualified readers, to close the human-agreement loop.
2. Retest on a contemporary author's corpus that the model has no memory of, to strip out the retrieval channel (expected: pure judgment ability is even lower).
3. Experiment 2 (single-sentence discrimination) has been designed but has not been run.

See [ROADMAP.md](../../ROADMAP.md).

---

**One-sentence summary:**

> The problem is not whether an LLM can read literature, but that **the judgment it gives will, exactly where the user cannot notice, steadily push the user toward "通用的通顺文风" ("a generic fluent prose style"), away from the author he wants to learn.** Therefore this project should not have AI judge writing.
