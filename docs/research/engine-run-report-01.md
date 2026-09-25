[English](engine-run-report-01.md) · [中文](../../_probe/跑测报告01-指纹与反馈引擎.md)

# Run Report 01: the v0.3 layer-1 fingerprint and the section 11 feedback engine

**Purpose:** to run one real text end to end through the v0.3 statistical fingerprint and feedback decision, focusing on one specific risk —
**will the system train the user into "像 AI 所描述的作者" ("like the author as the AI describes him") rather than "像作者本人" ("like the author himself")?**

**Corpus:** Wang Zengqi, 《端午的鸭蛋》("Duck Eggs of the Dragon Boat Festival") ([full text at China Literature and Art Network](https://www.cflac.org.cn/wywzt/2014/DuanWu/yuedu/201405/t20140529_257288.html)). 6 passages of the author's own prose + 1 passage quoted from Yuan Mei's 《随园食单》("Recipes from the Suiyuan Garden") (the quoted passage has already been excluded from the author fingerprint). 1351 characters (punctuation removed).
**Note:** the corpus source text has one truncation (at the end of paragraph 2, 「但是《腌蛋》这一条我看后却」("but this entry on 《腌蛋》 ('Salted Eggs'), after reading it I…") is missing a closing such as 「很感兴趣」("was very interested")); it does not affect this run's conclusion.

**Tools:** `_probe/analyze_fingerprint.py`, `_probe/engine_probe.py`, `_probe/verify_details.py` (purely local computation, no model is called)

---

## 1. The measured fingerprint: one thing I got wrong first

Before the run, if I had written this author's style from impression, I would have written "善用短句、节奏短促" ("favors short sentences, rhythm clipped and brief"). **The measured data does not support that description.**

| Metric | Measured value |
| --- | --- |
| Sentences / clauses | 76 / 179 |
| **Sentence length** | mean 17.8 characters, median 16.5, **SD 10.0** |
| **Clause length** | **mean 7.5 characters**, median 7, SD 3.8 |
| Sentence-length distribution | 0-6 chars: 8, 7-10 chars: 14, 11-15 chars: 13, 16-20 chars: 14, 21-30 chars: 18, 31+ chars: 9 |
| Commas / periods (per 100 characters) | 6.9 / 4.7 (ratio 1.48) |
| Longest run of consecutive short sentences (≤8 characters) | **2** |
| Words that name an emotion directly | **2 occurrences** (only "高兴" ("happy"), see section 2) |
| Explicit connective density | 0.74 per 100 characters |
| Personal-pronoun density | 2.07 per 100 characters, of which "我" ("I") accounts for 60.7% |
| Concrete objects | 47 kinds, 165 occurrences in total (roughly one physical object every 8 characters) |
| Questions | 4 occurrences, all self-asked and none answered |
| Expressions of uncertainty | 不知 / 记不清 / 数不出 / 也许 / 不一定 / 大概 / 好像 / 说是 ("don't know / can't recall / can't count them out / perhaps / not necessarily / probably / seems / they say"), 1 occurrence each |

### Conclusion 1: this author is not a "short-sentence author", he is a "clause author"

Sentence length mean 17.8 characters, SD 10.0, longest run of consecutive short sentences only 2 — **at the sentence level his rhythm is not the least bit clipped; on the contrary it alternates sharply between tight and loose** (shortest 1 character, longest 43 characters).

The real feature is at the next unit down: **mean clause length 7.5 characters, and the SD is not small (3.8)**. 179 clauses are distributed over 76 sentences, 2.4 clauses per sentence on average. What he is actually doing is:

> **Splitting long sentences into clauses of 3-10 characters and linking them quickly with commas.**

The clause-length sequence of paragraph 1 (the first 32):

```
5, 9, 4, 9, 5, 6, 6, 13, 4, 7, 6, 7, 5, 3, 6, 5,
2, 9, 15, 15, 7, 4, 9, 7, 5, 14, 6, 4, 18, 9, 11, 4
```

This sequence is itself the rhythm. And it contains a run of **8 consecutive clauses of ≤6 characters**. That structure is completely invisible in sentence-level metrics.

**"短句" ("short sentences") is a generic conclusion any model will hand out off the cuff, and it points in the wrong direction.** If the system feeds this impression to the user as a training target, the user will go and write line after line of short sentences — which is precisely not this author. This is the first empirical instance of proxy drift.

### Conclusion 2: emotion is not "不写" ("not writing it"), it is not "陈述" ("stating it")

The whole text has only 2 direct emotion words, both of them "高兴" ("happy"):

- 「我对异乡人称道高邮鸭蛋，是**不大高兴**的」("when I praise Gaoyou duck eggs to people from other places, I am **not altogether happy**") — negated, and it is a judgment of attitude
- 「什么时候孩子**一高兴**，就把络子里的鸭蛋掏出来，吃了」("whenever the child **was happy**, he took the duck egg out of the net bag and ate it") — used as an adverbial of condition (一……就……, "as soon as … then …")

Neither occurrence "states an emotion": not one is a sentence of the "他很高兴" ("he was very happy") kind, with an emotion as the predicate. **What really has to be judged is not "有没有情绪词" ("is there an emotion word") but "情绪词有没有作为谓语出现在主句里" ("has the emotion word appeared as the predicate of a main clause").**

### Conclusion 3: the remaining stable features

- **List-style predicate openings**: no connectives are used; things are displayed by juxtaposition. 「系百索子。五色的丝线拧成小绳，系在手腕上。做香角子。……贴五毒。……贴符。……喝雄黄酒。」("Tie on the hundred-cord. The five-color silk threads are twisted into a small cord and tied on the wrist. Make fragrant corner-bags. … Paste up the five poisons. … Paste up the charms. … Drink realgar wine.") Subjects are heavily omitted, and each action takes a sentence or a clause of its own.
- **Concrete objects carry the emotion**: 47 kinds of physical object, 165 occurrences; almost no abstract feeling is written anywhere in the piece. Objects like 「鸭蛋、络子、丝线、萤火虫、薄罗」("duck eggs, net bag, silk thread, fireflies, thin gauze") do the lyricism themselves.
- **Elegant-plain register drop**: right after an elegant phrase he immediately undercuts himself. 「曾经沧海难为水」("having seen the great ocean, no other water is water") → 「他乡咸鸭蛋，我实在瞧不上」("salted duck eggs from other parts, I really turn up my nose at them"); 「所食鸭蛋多矣」("as for duck eggs eaten, many indeed") → 「还不就是个鸭蛋！」("and it is still just a duck egg!"); 「肃然起敬」("awe rising in me") → 「哦！你们那里出咸鸭蛋！」("oh! your parts produce salted duck eggs!")
- **The weight given to uncertainty**: 「记不清」「数不出了」「不一定真凑足十二样」("can't recall", "can't count them out", "not necessarily really made up the full twelve items") — 「我记不清」("I can't recall") is written into the body of the text itself, not repaired into a definite account.
- **Colloquial closings**: ending on 「吗／呢／罢了／极了」("ma / ne / bale / jile" — colloquial sentence-final particles and intensifiers), with a tone that is "speaking", not "writing an essay".

---

## 2. Live-fire results: the sentinel test failed

Three test texts were set up and scored with the same set of decision rules:

1. **User's imitation draft** — I deliberately wrote it in "AI generalized style": smooth, well supplied with connectives, every sentence complete, everything fully explained.
2. **Sentinel text** — **a sentence of the original itself** (the opening sentence of paragraph 1). This is the most "author" text there is. **Any "deviation" is a false positive.**
3. **An imitation draft built to the measured fingerprint** — I deliberately wrote to the 7.5-character clause, the list-style openings and the colloquial closings.

### Defect one: the system judged the author himself as deviating from the author

The sentinel text (a sentence from the original) was detected as having **2 important issues + 2 minor issues**:

```
【原文原句（哨兵）】("the original's own sentence (sentinel)")
  [重要问题] ("important issues")
    - 节奏起伏 ("rhythm fluctuation")：小句长标准差 2.4 vs 作者 3.8 ("clause-length SD 2.4 vs the author's 3.8")
    - 句法骨架 ("syntactic skeleton")：清单式起句 0/7 句（0%）vs 作者约 30~40% ("list-style openings 0/7 sentences (0%) vs the author's about 30~40%")
  [次要问题] ("minor issues")
    - 口语性 ("colloquiality")：未出现「罢了／吗／呢／极了」一类口语收束 ("no colloquial closing of the 罢了／吗／呢／极了 kind appeared")
    - 疑而未答 ("doubt left unanswered")：未出现问句；原文 76 句中有 4 处自问 ("no question appeared; the original has 4 self-asked questions in its 76 sentences")
```

Of these, "清单式起句 0/7" ("list-style opening 0/7") is **obviously false**. Checking item by item confirmed it was a **unit-of-measurement error**:

| Unit of measurement | Proportion of predicate / attributive openings (paragraph 1) |
| --- | --- |
| Clause level | 13/65 = 20% |
| Sentence level | 8/26 = 31% |

The sentinel text is made of 8 clauses of ≤6 characters, **which is precisely the densest form of this feature**, yet it was missed in full because the text was split by sentence (its first clause is 「五色的丝线拧成小绳」("the five-color silk threads are twisted into a small cord"), which does not begin with a predicate). **When a metric is sampled at the wrong level, it judges the target's typical form as a deviation.**

### Defect two: the false positives of three metrics are structural, not a parameter-tuning problem

| Metric | Sentinel result | Real cause |
| --- | --- | --- |
| Rhythm fluctuation (clause SD) | judged "过于均匀" ("too uniform") | **SD varies with sample size.** The 2.4 computed from 7 clauses and the 3.8 computed from 179 clauses are not comparable. The metric itself was not normalized, so a short passage is bound to be judged monotonous |
| Syntactic skeleton (list-style openings) | judged 0% | unit-of-measurement error (see above) |
| Doubt left unanswered (question count = 0) | judged a deviation | **treating "没有出现" ("did not appear") as a defect.** The original's 4 questions are distributed over 76 sentences; the great majority of passages have no question to begin with. This is pure noise |
| Colloquiality (modal particles) | judged a deviation | same as above: a low-frequency feature treated as a mandatory feature |

**Not one of the four can be repaired by tuning the threshold**, because they are not threshold problems but one class of modeling error: "把全体统计分布里的稀有项当成逐段必备项" ("treating a rare item in the overall statistical distribution as a per-passage mandatory item").

### Defect three: the most ironic one — the correct imitation was scored more severely than the wrong one

The imitation draft built to the measured fingerprint (mean clause length 4.3 characters, closer to "clipped" than the author's 7.5 characters):

```
【临摹稿（按实测指纹构造）】 ("imitation draft (built to the measured fingerprint)")
  指纹 ("fingerprint"): 86字 11句 句长7.8±3.5 小句4.3±1.6 逗10.5 句12.8 ("86 characters, 11 sentences, sentence length 7.8±3.5, clauses 4.3±1.6, commas 10.5, periods 12.8")
  [核心问题] ("core issue")
    - 情绪表达：出现直接情绪词 [('高兴', 1)] ("emotion expression: a direct emotion word appears [('高兴' ("happy"), 1)]")
```

That "高兴" ("happy") judged a core issue comes from a line I wrote, "孩子一高兴，掏出来，吃了" ("the child, happy, took it out and ate it") — **and this is exactly the original's own sentence** 「什么时候孩子一高兴，就把络子里的鸭蛋掏出来，吃了」("whenever the child was happy, he took the duck egg out of the net bag and ate it"). Same author, same word, same usage, same syntactic position — judged a serious deviation of "直接命名情绪" ("naming an emotion directly").

And the genuinely wrong user draft (35.9-character long sentences, connective density 3.2 times the author's) received only 1 core issue; the two were **comparable in severity**.

### Summary: the direction of the errors is consistent

| Feature punished by the system | In the real author |
| --- | --- |
| Smooth long sentences, explicit connectives, "因为/所以/因此" ("because / so / therefore") | the author very rarely uses them (0.74 per 100 characters) |
| Complete subjects, every sentence spelled out clearly | the author omits subjects heavily |
| Degree adverbs, explanatory phrasing | the author exclaims outright in only a very few places |
| Abstract generalization | the author lands on concrete physical objects |

That is to say, **this decision set is in effect rewarding the generic good prose style — "通顺、完整、有逻辑、有解释" ("fluent, complete, logical, explanatory") — and punishing this author's real features.** What a real user will do in the face of this feedback is clear: add connectives, write the sentences out in full, pile up fewer physical objects, state the emotions out loud — **he will become more and more like "一个文从字顺的普通写作者" ("an ordinary writer whose prose is smooth and correct"), and less and less like Wang Zengqi.**

This is exactly what is meant by "被带偏到 AI 评判解读作者的方向" ("being dragged off toward the direction of an AI judging and interpreting the author"). And it needs no malice at all: **as long as the metrics are sensitive to "通用规范" ("generic norms") and insensitive to "作者特征" ("the author's features"), the training pressure points automatically at the generic norms.**

---

## 3. Root cause: the three-layer structure and judging authority

This failure is not a matter of insufficient modeling quality; **the authority was allocated wrongly**.

v0.3 §5 already laid down that layer 1 is "可靠计算、完全可复现" ("reliable computation, fully reproducible") and that only layer 2 is "LLM 判定 + 证据" ("LLM judgment + evidence"). But **what was actually doing the judging in this run was the numbers of layer 1** — "小句标准差 2.4 vs 3.8" ("clause SD 2.4 vs 3.8") turned directly into an "重要问题" ("important issue"). Layer 1 has no judging authority, yet it was exercising it.

The correct division of labor:

| Layer | Authority |
| --- | --- |
| Layer 1, statistical fingerprint | **may only describe, it may not judge.** It outputs "原文小句均长 7.5±3.8，本段 4.3±1.6" ("the original's mean clause length is 7.5±3.8, this passage's is 4.3±1.6"), and it does not output "节奏不像" ("the rhythm is not like his") |
| Layer 2, LLM judgment | the only layer with the authority to say "像/不像" ("like / not like"), and it must carry original-sentence evidence and a confidence value |
| Sentinel regression | **must be re-run after every change to the decision rules**: feed the original's sentences into the system and there must be zero deviations. A deviation means the rules are wrong, not that the author is wrong |

---

## 4. Necessary revisions to v0.3

The conclusions from this run land directly in document revisions:

1. **Add a 4th layer to the author model: difference from others of the same kind.** Only the part where "这位作者与同时代同类作者不同" ("this author differs from comparable authors of his time") has training value. "短句" ("short sentences") is not a difference; "小句均长 7.5 字 + 连续 8 个 ≤6 字小句" ("mean clause length 7.5 characters + 8 consecutive clauses of ≤6 characters") is.
2. **Distinguish four feature types, with different authority for each**:
   - Distributional (clause length, punctuation density) — may only be compared over a whole piece; judging a passage to be missing something is forbidden; length normalization is mandatory
   - Structural (list-style juxtaposition, elegant-plain register drop, questions left unanswered) — high value, but it must be judged at the correct unit of measurement
   - Rare items (questions, modal particles, specific words) — **never to be used as a criterion of "缺失即偏离" ("missing means deviating")**
   - Taboo type (the only type where "出现即偏离" ("appearing means deviating") may be judged, for example "情绪词作谓语出现在主句" ("an emotion word appearing as the predicate of a main clause"))
3. **A prohibition must be checked against the author's own usage.** For any rule of the form "作者不写 X" ("the author does not write X"), first search X in the author's full text. That is how "高兴" ("happy") was caught in this run — **a rule must not punish something the author himself has used.**
4. **Sentinel regression goes into the development flow.** Every time the decision-rule set is changed, the original's sentences must be run; only zero false positives is allowed to be committed.
5. **The unit of measurement must be declared explicitly.** Every metric must state its sampling level (clause / sentence / paragraph / whole text), and **the same metric must not be compared across levels**.
6. **Short-text protection.** When the sample size is insufficient, distributional conclusions are forbidden.

---

## 5. Methodological gains from this run

1. **The "先测量、再判断" ("measure first, then judge") layered architecture is necessary, but not sufficient** — layer 1 must also be stripped of its judging authority.
2. **The sentinel test is effective and cheap**: hitting the system with the original's own sentences caught four structural false positives in one go. This test should be frozen into the development flow, not treated as a one-off verification.
3. **"模仿得越努力越偏离" ("the harder you imitate, the further you deviate") is a failure mode that really happens**, and its direction is predictable: convergence toward the generic prose style. This has to be fought at the product level, not by swapping in a stronger model.
4. **Proxy drift cannot be solved by "更准的模型" ("a more accurate model")**, only constrained by **structure**: where judging authority sits, feature grading, sentinel regression, and checking rules against the author's own usage.
