[English](core-method-v0.3.en.md) · [中文](../设计/核心方法-v0.3.md)

# AI Franklin Writing Training System: Core Method V0.3

> **Status: superseded — historical design record.** This is the v0.3 design, written while the project still contained AI judgment modules. It is kept as the record of the direction that was abandoned, not as a description of what shipped. Everything here that judges writing — the comparison engine (§15), the author model's judgment layer (§10), gap ranking (§8), convergence trends (§16) — was measured, found unreliable, and deleted in [no-judgment design v1.0](no-judgment-design-v1.0.en.md). Do not implement from this document.

> This version does three things on top of V0.2: it completes the algorithm and acceptance questions V0.2 left open; it rewrites several principles as implementable, testable specifications; and it states that this project is a **local-first, personal-use, open-source** tool, from which hard constraints on data, models and privacy are derived.
>
> **Revision record:** Part 2 (proxy drift), §10 layer 4, the four negative hard criteria in §15, and the sentinel regression and blind test in §21 were all **added after one real probe run**, on the basis of `_probe/跑测报告01-指纹与反馈引擎.md`. These are not precautionary caution clauses — they are repairs for failures that actually occurred during the probe. **When reading this document, Part 2 takes precedence over the rest.**

---

## Part 1: General principles

### 1. The root goal (unchanged)

The system does not help the user "write a good article". It helps the user, through long-term, gradual, high-quality imitation, to **first genuinely write "like" the author and then internalise that ability**, so that in the end they can go beyond imitation and form their own writing ability and taste.

Two stages:

- Stage one: fitting the author — can I write more and more like this author?
- Stage two: surpassing the author — once I have mastered this way of writing, can I use it to write my own things?

Therefore "does it resemble the author" is the core metric of the whole system's early training.

### 2. AI's real task (unchanged)

AI is not responsible for literary appreciation. AI's task is: to turn a good author's way of writing into a training object that the user can repeatedly observe, imitate, compare and correct.

Main loop:

> analyze the author from several works → build the author model → analyze the specific article → split training units sensibly → organize the copy exercise → compare the user's work → find the gaps against the author → explain why the gaps arise → guide the user's correction → judge the degree of closeness → adjust training difficulty dynamically

### 3. Form constraints of this project (new in V0.3, but placed first)

This project is explicitly positioned as: **a single-user local tool + an open-source project**.

This is not a secondary engineering choice; it determines the methodology in reverse. Five hard constraints follow:

**Constraint 1: AI capability is supplied by the user's own key.** The system must be provider-agnostic: the model-calling layer is completely decoupled from the business logic, and any OpenAI-compatible endpoint is supported. An open-source project must never contain a design that "requires a particular service".

**Constraint 2: all data exists only on the user's own disk.** Model texts, copy drafts, training records and user archives are all local files; there is no server side. The side effect is a good one: **the copyright problem for model texts disappears by itself** — the text in the user's hands never leaves his machine, and the open-source repository never contains any copyright-protected corpus either.

**Constraint 3: every comparison must be reproducible and traceable.** After the user upgrades the model or edits the prompt, if "closeness" changes, the system must be able to say whether the model changed or the user genuinely improved. Every training record must therefore write `model_name`, `prompt_version` and `schema_version`.

**Constraint 4: the core engine must be independently testable.** The greatest value of an open-source project is that others can verify whether the methodology works. Feature computation, dimension judgment criteria and the data model must therefore be independent of the UI, able to run and be tested separately from the interface.

**Constraint 5: no dependency on "must be online to work".** Offline, you can at least read model texts, hand-write the copy exercise and view history. The network is used only for analysis, hint generation and comparison.

**Constraint 6 (the most important): the system must be able to prove it has not drifted, rather than assuming by default that it is right.** See Part 2.

---

## Part 2: Proxy drift — this project's most dangerous failure mode (new in V0.3.1)

> This section is written from the measured results in `_probe/跑测报告01-指纹与反馈引擎.md`; it is not a theoretical worry.

### 4. What the danger is

Training can only ever optimise toward a **proxy metric**, and the proxy metric is "the AI's understanding of the author", not the author himself. Once the two separate, the system stably trains the user to be "**like the author as described by the AI**" rather than "like the author". This path happens automatically without any fault:

> the model's understanding of the author is biased → the user revises toward that bias → the AI continues to judge with the same bias → the bias confirms itself

The harder the user tries to satisfy the system, the further they get from the goal. **This is not something a stronger model can fix; only structural constraints can.**

### 5. Measured evidence (summary)

A probe run on Wang Zengqi's 《端午的鸭蛋》 ("Dragon Boat Festival Duck Eggs") produced three conclusions:

1. **The generic conclusion points the wrong way.** Describing this author from impression, the most natural conclusion is "he is good at short sentences". Measured: mean sentence length 17.8 characters, standard deviation 10.0, longest run of consecutive short sentences only 2 — **at the sentence level his rhythm is not at all clipped**. The real feature is at the next unit down: **mean clause length 7.5 characters**, with 179 clauses distributed across 76 sentences, and a run of **8 consecutive clauses of ≤6 characters** did occur. "Short sentences" is a generic label that any model will produce, and it points the wrong way.

2. **The system's actual penalty direction is "generic good prose".** The features judged as deviations in the probe were: clauses on the long side, too many explicit connectives, complete subjects, degree adverbs present, abstract generalization. This author's real practice is the exact opposite (connective density only 0.74 per hundred characters, subjects omitted in large numbers, one concrete object every 8 characters). A real user revising according to this feedback would **become more and more like an ordinary writer of smooth, correct prose**.

3. **Even the author's own original text was judged as deviating from the author.** Feeding the original's own sentences (the opening of paragraph 1) into the judgment engine detected 2 major problems + 2 minor problems. Among them "list-style opening 0/7" is false — **an error in the unit of measurement**: that feature accounts for 20% at clause level and 31% at sentence level, while the sentinel text consists of 8 short clauses, which is precisely the densest form of that feature, yet it was missed because the split was by sentence.

### 6. Structural lines of defence (six, all hard constraints)

**Defence 1: strip layer 1 of the power to judge.** A statistical fingerprint may only **describe**; it may not **judge**. It may output "the original's mean clause length is 7.5±3.8, this paragraph 4.3±1.6", but it **must not** output "the rhythm doesn't match". The only layer entitled to say "resembles / doesn't resemble" is layer 2 (LLM judgment + evidence + confidence). Translating numbers straight into conclusions was the common source of every false positive in this probe.

**Defence 2: features are graded by type, with different permissions.**

| Type | Example | Permitted way of judging |
| --- | --- | --- |
| Distributional | clause length, punctuation density, sentence length distribution | may only be compared **whole text against whole text**; **length normalization is mandatory**; **judging absence paragraph by paragraph is forbidden** |
| Structural | list-style juxtaposition, register drop, a question left unanswered, a colloquial close | high training value; must be judged at the **correct unit of measurement** |
| Rare items | one particular question, one particular modal particle, one particular word | **never used as a criterion of "absent therefore deviating"** |
| Taboo | for example "an emotion word serving as the predicate of the main clause" | the **only** type where "present therefore deviating" is permitted |

In the probe, "no question appeared" and "no modal particle appeared" were treated as deviations: that is misusing rare items as absence criteria; "clause standard deviation 2.4 vs 3.8" is a distributional metric used on a short paragraph without normalization. **Neither class of error can be fixed by tuning thresholds; only grading and disabling can fix them.**

**Defence 3: any rule of the form "the author does not write X" must first search X across the author's complete works.** A rule must not penalise something the author himself used. In the probe, a copy draft I wrote from the measured fingerprint was judged a core problem for "孩子一高兴" — and that is exactly the original sentence 「什么时候孩子一高兴，就把络子里的鸭蛋掏出来，吃了」 ("whenever the child got excited, he would fish the duck egg out of the net bag and eat it"). **Same author, same word, same usage, same syntactic position.** Errors of this kind must be intercepted by the rule-validation step.

**Defence 4: sentinel regression is part of the development process.** Every time the judgment rule set is modified, the **author's own sentences** must be fed into the system, and **zero deviations** required before a commit is allowed. This was the only method that caught four structural false positives in a single pass, at extremely low cost. Sentinel samples should be fixed by selection from the author's calibration samples.

**Defence 5: the unit of measurement must be declared explicitly.** Each metric states its sampling level (clause / sentence / paragraph / whole text), and **the same metric must not be compared across levels**. The missed detection of that feature in the sentinel test was caused entirely by inconsistent units.

**Defence 6: short-text protection.** When the sample is too small (for example fewer than about 15 clauses), outputting any distributional conclusion is forbidden. Standard deviation varies with sample size; this is a mathematical fact, not a tuning problem.

### 7. The development order this establishes

> **Measure first, judge second; fix the unit first, the threshold second; pass the sentinel first, talk about feedback second.**

Before any new metric enters the system, it must answer, in order: what is its sampling unit? what shape does its distribution take across the author's complete works? has the author himself ever violated it? feed the original's sentences in — will it raise a false alarm? If any one of the four answers is unclear, that metric may not take part in judgment.

---

## Part 3: Revisions to V0.2

### 8. Revision one: delete the total score and the fixed weights

Item 8 of V0.2 gave a weight table with seven dimensions totalling 100 points. This version **abolishes that weight table, and also abolishes showing the user any total score**. Three reasons:

1. **The weights have no source.** "Structure and information progression accounts for 20%" cannot be argued for and cannot be verified. A coefficient pulled out of thin air permanently contaminates the credibility of the whole system.
2. **Fixed weights contradict deliberate practice.** Deliberate practice requires setting, one at a time, a task aimed at one specific ability and slightly beyond the current level. If seven dimensions are mixed in fixed proportions, the system can never work out "what exactly should be practised this round".
3. **A total score is useless for training.** What the user needs to know is "what I dropped and what to change next", not "I got 72". V0.2 itself already admitted that "you shouldn't tell the user 72 out of nowhere" — this version carries that judgment through to abolishing scores.

**The replacement: a ranking scheme, not a weighting scheme.**

The system internally maintains gap values for the seven dimensions (algorithm in §9), but **does not multiply or add them**; it does only two things:

- for this round of training, which dimensions have the largest gaps;
- compared with the user's own history, which dimension is regressing.

The top 1–3 ranked dimensions form this round's **focus set**; the remaining dimensions enter the observation area.

This turns "weight" from a constant into a ranking result that varies with the text, with the user and with the round — which both avoids the nuisance of inventing coefficients and naturally fits deliberate practice's "one focus at a time".

### 9. Revision two: split "closeness" into three different quantities

V0.2 used one and the same closeness to measure memory, to measure ability and to draw a trend line; that is the deepest conflict between items 9 and 8. This version splits it into three mutually non-interchangeable quantities: **computed separately, stored separately, never merged**.

| Quantity | Question it answers | Input | Use |
| --- | --- | --- | --- |
| **M: memory fidelity** | what you remembered, what you forgot | original + the user's 1st pass | judge the memorability of the text; identify the user's structural forgetting patterns |
| **G: dimension gaps** | where this pass fails to resemble the author | original + author model + the user's Nth pass | generate this round's feedback and focus set |
| **C: convergence rate** | whether you are absorbing it | G₁ → G₂ → G₃ within the same unit | decide whether to keep practising or move to the next unit |

Three hard rules:

**Rule A: the ability curve uses only data from the 2nd pass onward.** The 1st pass mainly reflects "how easy the original is to remember", not "whether the user can write". If the 1st pass is counted into the growth archive, the archive is contaminated by how salient the text is. M is archived separately and used for its own purpose only.

**Rule B: G must be checked against both the "original" and the "author model".** Against the original alone it degenerates into text comparison; against the author model alone it loses this particular article's specific task. The criterion for whether a gap holds is: **it is both a deviation from the original and a deviation from that author's habits.**

**Rule C: C is used only for trend judgment and takes part in no displayed number.** What the system says to the user is "this is improving / stagnating / regressing", not a line chart plus a slope.

### 10. Revision three: make clear "what can be computed and what must be judged" — the four-layer author model

V0.2 proposed building an author writing model, but did not say what goes into the model or how it is computed. This version divides the author model into four layers, and **each layer has a different credibility and different permissions; conflating them is never allowed**.

#### Layer 1: statistical fingerprint (reliable computation, fully reproducible)

This layer is computed entirely by the program and contains no model judgment, so two runs necessarily produce the same result.

| Feature family | Specific metrics |
| --- | --- |
| Sentence length distribution | mean sentence length, sentence length standard deviation, sentence length histogram (binned by character count) |
| Pause rhythm | comma/period ratio, mean clause length, punctuation density (punctuation marks per hundred characters) |
| Paragraph shape | paragraph length distribution, alternation pattern of long and short paragraphs, frequency of single-sentence paragraphs |
| Dialogue and narration | proportion of quoted content, density of dialogue turns |
| Lexical layer | content-word/function-word ratio, distribution of high-frequency function words, lexical richness (e.g. MATTR, to avoid TTR distortion on long texts) |
| Syntactic layer | proportion of each part of speech, nesting depth of modifiers, frequency of passive and 把-constructions, frequency of fronted adverbials |
| Rhetorical position | simile markers, structural repetition detection for parallelism and repetition, density of exclamations and questions |

This layer directly answers "how does this author usually write", and it **can be computed for any new text** — which is precisely its most important use: testing the model with articles that took no part in building it (see §10).

#### Layer 2: judgment items (LLM judgment + fixed criteria + evidence required)

Some things statistics cannot do; they require understanding the semantics to judge, for example:

- Does the author **avoid stating a character's emotions directly**, substituting action and setting?
- Is the narrative distance close to the character or detached?
- Where does the white space appear, and what is left out?
- Does this simile **replace** direct description, or is it merely decoration?
- Does the order of information progression (setting → character → change → close) hold?

For each judgment item the system must hold three things; none may be missing:

1. **the judgment criterion**: what counts as "yes", what counts as "no", and how boundary cases are handled;
2. **the triggering evidence**: the specific sentence in the original (precise to the sentence);
3. **confidence**: high / medium / low. Any judgment item with low confidence **may not enter user-visible feedback**; it is archived for reference only.

This layer is the only place in the system where errors are possible. Its output is therefore always presented as three items side by side — "original sentence + criterion + judgment" — so that the user can contradict it on the spot. **It is the only layer in the model entitled to say "resembles / doesn't resemble"** (see Defence 1 in Part 2). Items the user marks as "wrong judgment" must be written to the database as the system's calibration set.

#### Layer 3: calibration samples (style anchors)

The author model must store 5–10 **passages from the original that best represent this author**, each labeled with what it represents ("typical of indirect emotional expression", "typical of rhythmic variation").

The use is: when the system says "this paragraph of yours isn't like him", it can pull the calibration sample up for direct comparison, instead of asking the user to believe an abstract description. **Any style conclusion without a calibration sample is treated as unverified.**

#### Layer 4: difference from peers (new in V0.3.1; the filter for training targets)

**This layer decides what is worth training.** The first two layers describe "how this author writes", but most of those features are **shared by comparable authors of the same kind** — training them amounts to training generic prose style. Only the part where "this author differs markedly from comparable authors of the same period" is what constitutes "being like him".

Every group of fingerprints computed in layer 1 must therefore be subtracted against a **peer baseline**:

| | Difference from peers | Training value |
| --- | --- | --- |
| mean clause length 7.5 characters | modern Chinese prose runs generally long, so this is on the low side | medium (directional information) |
| **8 consecutive clauses of ≤6 characters** | very rare in peer texts | **high** |
| **list-style predicate openings (juxtaposed enumeration)** | peer texts habitually use connectives and complete subject–predicate | **high** |
| **register drop (an elegant word immediately undercut)** | peer texts will not undercut themselves | **high** |
| **unrepaired self-doubt ("can't remember clearly", "not necessarily")** | peer texts tend toward certain narration | **high** |
| dense concrete objects | a difference of degree | medium |

**Filter rule:**

> A feature with no difference from peers **can be used only for diagnosis, never as a training target**. Any entry whose "training value" column in the feature table is empty may not enter the user's focus set.

The direct effect of this rule is to block convergence toward "generic good prose" — generic prose is generic precisely because it has no difference from its peers.

**Where does the peer baseline come from?** Three levels of fallback: ① other works by the same author in the user's model-text library (as a contrast); ② a personal baseline made up of works by other authors in the user's library; ③ a corpus baseline built into the system (an open-source project may ship the fingerprints of several public-domain texts). When all three are unavailable, **outputting layer 4 conclusions is forbidden**, and training falls back to work mode.

#### On "author style → writing mechanism → specific sentences" (V0.2 §4)

This principle is retained, and in this version it becomes a hard requirement:

> Every style conclusion must be able to descend to a specific sentence; a style conclusion that cannot descend to a specific sentence may not be written into the author model.

### 11. Revision four: the author model must be validated before it can be used

V0.2 said "import several works → form an author writing model", but gave no acceptance criteria. An unvalidated model puts every subsequent "resembles / doesn't resemble" judgment on top of guesswork.

**Validation method (hold-out):**

1. the user imports N works by that author;
2. the system randomly holds out about 1/3, and builds the model from the remaining works only;
3. the model is used to **predict** layer 1 statistical fingerprints for the held-out articles (for example the interval for mean sentence length, the interval for punctuation density, the interval for dialogue proportion);
4. compute the deviation between predicted and actual values. If most key features fall inside the predicted intervals, the model passes; otherwise the model is judged **underfitted**.

**Confidence and cold start:**

| Condition | Mode | System behavior |
| --- | --- | --- |
| ≥ 3 works and validation passed | **author mode** | all comparison features against the author model are available |
| 1–2 works, or validation failed | **work mode** | comparison against the single original only; the interface clearly states "currently in work mode; no author model has been built" |
| total length under about 3000 characters | **insufficient sample** | training is allowed, but outputting any style-level conclusion is forbidden; only sentence-level and paragraph-level differences |

Pretending to have an author model in work mode is never allowed. **Better to say "I don't yet know how he usually writes" than to make up a style.**

---

## Part 4: Specification of the training loop

### 12. Dynamic splitting of training units

The basic principle is unchanged: neither inside the comfort zone nor straight into the difficult zone, but **slightly above the current stable ability**.

What decides unit size is not character count but **cognitive load**. The system scores the following factors together and then cuts the article into four levels — A (easy) / B (slightly hard) / C (harder) / D (complex):

> text length + structural complexity + syntactic complexity + style complexity (how far it deviates from the features the user has already mastered) + the user's past performance

Character-count ranges serve only as initial defaults (beginner 80–120 characters / intermediate 120–200 / advanced 200–350); once the user has enough history, the weights should give way to actual performance.

**Acceptance criterion for correct splitting:** a training unit must be nameable by one "expressive move" (for example "entering the character from the setting"). If a unit the system cut cannot be named, the cut is wrong — this check can be automated, or handed to the user as a one-click re-split, and re-split results must be written to the database as training data for the splitting algorithm.

### 13. The boundary of hints (reconstruction hints)

V0.2 already decided to delete "get more hints". This version further specifies **what a hint may and may not contain**:

**May contain:** expressive moves, order of information, structural skeleton, viewpoint and distance, how the ending is handled.

**May not contain:** the author's specific wording, the names of rhetorical devices, any phrase that could be lifted straight into the answer.

Format constraints:

- at most 5 per unit;
- no more than 15 characters each;
- describes only "what this paragraph does", never "how well this paragraph is written".

**Acceptance criterion:** give the hints to someone who has not read the original; that person should be able to write a paragraph with **the same structure but completely different wording**. If they cannot, the hints are too few or too vague; if they can write sentences close to the original, the hints leaked the answer.

### 14. The copy stage: the editor is the training ground

In principle the system does not correct in real time while the user copies. V0.2 already explained why (constant reminders from the AI destroy active generation). This version turns that principle into concrete editor specifications:

- **pasting is forbidden** (to prevent falling back to copying the original);
- **no spelling or grammar underlines are shown**;
- **no live suggestions of any kind**;
- the first pass **does not show the original** by default, and after submission no entry point for "take another look at the original and then rewrite" is provided within this unit (the original appears naturally at the comparison stage);
- an "I really can't remember" button is provided, whose behavior is to **honestly accept this incomplete draft** rather than to give hints. If the user can write 30%, they submit 30%.

The idea from V0.2 that "the errors are themselves the learning material" should be saved explicitly: the differences between the first-pass draft and the original must be charted separately (recorded as M, see §9), for long-term observation of **what the user habitually forgets** — for example always dropping scenery description, always compressing the pauses out. Patterns of this kind often have more long-term value than "does this pass resemble the author".

### 15. The comparison engine: a fixed format for feedback

Feedback must answer three questions at once, in an unchangeable order:

1. **Where doesn't it resemble?** — with the original sentence and the user's sentence attached
2. **Why doesn't it resemble?** — explain what reading effect this difference produces
3. **How to make it resemble?** — give an actionable direction for revision, **do not give the revised result**

V0.2 already abolished "give only 1–3 problems at a time" in favour of "report everything found, presented in grades". This version adds a design point to dissolve the contradiction between "report everything" and "focus":

> **Hide none of the findings, but limit "the ones you need to act on now" to 1–3.**

That is, replace the old **filtering** with **counting**:

```
核心问题（2）
  ● 情绪表达方式与作者差异明显        [本次要改]
  ● 句子节奏明显比作者平直            [本次要改]

重要问题（3）
  ○ 原文存在一次明显的语言反复，你没有保留
  ○ 原文由环境进入人物，你直接进入人物
  ○ 段落收束处原文留白，你做了总结     [本次要改]

次要问题（4）
  · 个别词汇选择不同
  · 一个句子的长短与原文不同
  · ……

用户看到全部 9 条；但只有标 [本次要改] 的进入下一轮。
```

```
Core problems (2)
  ● emotional expression differs markedly from the author   [change this round]
  ● sentence rhythm is markedly flatter than the author's   [change this round]

Important problems (3)
  ○ the original has one clear instance of verbal repetition, which you did not keep
  ○ the original enters the character from the setting; you go straight to the character
  ○ the original leaves white space at the paragraph close; you wrote a summary   [change this round]

Minor problems (4)
  · a few word choices differ
  · one sentence differs in length from the original
  · ……

The user sees all 9 items; but only those marked [change this round] carry into the next round.
```

**Four hard criteria for whether a piece of feedback qualifies** (fail any one and it must not be output):

1. **has evidence**: it can point to a specific sentence in the original;
2. **actionable**: after reading it the user knows what the next action is, rather than merely feeling criticised;
3. **no ghost-writing**: it does not give a finished revised sentence;
4. **matches the focus target**: it relates to this unit's training goal, or it can explain why an exception is worth making.

**Four further negative hard criteria** (based on the target practice in Part 2; hit any one and it must not be output):

5. **No judgment may be generated directly from a statistical fingerprint.** Layer 1 may output only descriptions ("the original's mean clause length is 7.5±3.8, this paragraph 4.3±1.6") and must not output conclusions ("the rhythm doesn't match"). The power to judge belongs to layer 2 alone.
6. **Rare items must not be treated as absence criteria.** "no question appears" and "no modal particle appears" are not deviations. Distributional metrics must be whole text against whole text, and length-normalized; when the sample is too small (fewer than about 15 clauses), no distributional conclusion may be output.
7. **No comparing across units of measurement.** Each metric declares its sampling level (clause / sentence / paragraph / whole text), and the same metric must not be judged across levels.
8. **Nothing the author himself used may be penalised.** Any rule of the form "the author does not write X" must first search X across the author's complete works; if it hits, the rule is void.

**Combining rule:** the four positive criteria decide "may it be said", the four negative criteria decide "may it be output as feedback". **Only satisfying all eight at once allows an item to appear on the user's screen; otherwise that item is downgraded to an internal record.**

### 16. Second revision and convergence judgment

When the user revises and submits again, the AI does not re-grade in full; instead it first checks **whether the items marked [change this round] in the previous round improved**, then recomputes the dimension gaps, to see whether a new dimension has jumped to being the largest gap.

Conditions for ending a unit:

- the dimension gaps have converged to a stable value at the user's current level → suggest moving to the next unit;
- or the user has revised 2–3 times and gaps remain → moving to the next unit is allowed.

**Important: do not secretly decide for the user.** The system should show the basis for its judgment and leave the decision to the user. A suggested presentation:

```
当前主要差距：句子节奏（连续 3 次未见改善）
最近三次趋势：改善 → 持平 → 持平
判断：本单元对"节奏"的吸收已接近瓶颈
建议：进入下一单元；或再练一次但换一个聚焦目标
```

```
Current main gap: sentence rhythm (no improvement seen for 3 consecutive rounds)
Trend over the last three: improving → flat → flat
Judgment: absorption of "rhythm" in this unit is approaching its ceiling
Suggestion: move to the next unit; or practise once more but with a different focus target
```

### 17. Difficulty adjustment: use gaps, not scores

Since this version abolishes the total score, difficulty adjustment must change its basis too. The rules:

- 2 consecutive units reach a low gap already on the **2nd pass** → raise the unit level (A→B→C);
- 2 consecutive units still have the same largest gap after the **3rd pass** → do not raise the level; instead **change the focus target** and practise text of the same kind again;
- when the user chooses a difficulty themselves, the system only notes "this is above your current stable level" and does not block it.

---

## Part 5: From copying to internalisation

### 18. The training route (V0.2 §14 retained, with judgment criteria added)

| Stage | Content | Criterion for entering the next stage |
| --- | --- | --- |
| 1. Local copying | one sentence resembles → one paragraph resembles | low gap already on the unit's 2nd pass |
| 2. Complete copying | one whole piece resembles | after reconstructing the whole piece, the structural chain is complete and the language features are consistent |
| 3. Transfer copying | it still resembles on a changed topic | the new-topic article's layer 1 fingerprints against the author model fall inside the intervals |
| 4. Stable copying | the features hold across repeated original writing | 3 consecutive original pieces show no significant deviation |
| 5. Fusion | combine several ways of writing already mastered | the user actively declares a fusion intent, and the system compares against each author model separately |
| 6. Surpassing | form one's own way of expression | no longer takes any single author as reference; comparison switches to the user's own past work |

### 19. Details of judging style transfer

The key to checking that transfer training is valid is that **the content must not overlap the original**. When generating a transfer task, the system must ensure the new topic differs from the original in all three dimensions: setting, characters and events.

What is compared when judging is the **author model**, not the original. The checks are: is the syntax close, is the rhythm close, is the emotional expression close, is the descriptive distance close, is the language density close, do the devices appear in a similar way.

**Reporting format:** no number like "style fit 78"; instead a comparison table — which features have entered the author's interval and which have not. That is far more useful than a number, and far more honest.

### 20. The long-term archive: record ability, not scores

The archive records three kinds of content:

- **relatively stably mastered**: a low gap on one dimension across several consecutive rounds;
- **forming**: the gap keeps shrinking but is not yet stable;
- **recurring problems**: the same dimension's gap recurring across articles and across authors.

**"Habitual forgetting" is recorded at the same time** (from M, not from G): for example persistently losing pauses, persistently compressing scenery description. Information of this kind cannot be seen in single-piece feedback; only the long-term archive can reveal it.

The archive uses **dimension names and evidence**, not scores. A user should be able to read something like this:

> You kept the short-sentence rhythm across 6 articles; but in original writing, you still tend to explain characters' emotions directly (present in all of the last 3 original pieces). You habitually discard the white space at the paragraph close (9 times out of 11 copy exercises).

---

## Part 6: Validating the methodology itself

### 21. The system needs to be validated, not believed

This is the key to whether an open-source project can stand. Four things must be done in the first version:

**(1) Calibration set.** Prepare 20–30 pairs of "original sentence vs user sentence", manually labeled "resembles / doesn't resemble" with reasons. Use it to check whether the AI's judgment agrees with human judgment. When the agreement rate falls below the agreed threshold (80% suggested), the judgment criteria must be revised rather than continuing to ship.

**(2) A recovery entry point for judgment errors.** The user can click "this judgment is wrong" on any feedback item. All marked items enter the calibration-set candidate pool. This is the system's only channel for self-improvement.

**(3) Sentinel regression (must be automated).** Feed the author's calibration sample sentences (and any complete paragraph of the original) into the judgment engine, **requiring zero deviations**. After any judgment rule is modified, it must be re-run and pass before a commit is allowed. The first probe run caught four structural false positives in a single pass precisely through this, at extremely low cost and with the highest payoff — **this is the only mechanism by which this methodology can automatically prove that "the system has not drifted".**

**(4) A real test of whether the methodology works.** What must be answered in the end is not "does the system run" but "after 10 sessions with it, has the writing really changed". A usable test: have the same user do transfer writing on new text that **took no part in training**, and compare the change in author-range hit rate between the 1st time and the 10th. If there is no change over the long run, the methodology or the implementation has a problem, and that should be recorded honestly rather than covered up with a prettier interface.

**One further reverse check that must be done periodically: the blind test.** Mix the author's original sentences together with AI imitation sentences, and have the user judge which sentence the author wrote. **If the user cannot tell them apart, what he learned is the AI's imitation, not the author.** This check does not use the AI itself as referee, and it is the only means of breaking the "AI judging AI" closed loop.

### 22. The first version's minimal closed loop (MVP scope)

So that an open-source project can be reproduced by others, the first version should do only one complete vertical slice and nothing else:

1. import one text (paste or local file);
2. statistical fingerprint computation (layer 1, purely local, no model calls, **describes but does not judge**);
3. author model construction with hold-out validation (with several works) or work mode (with one); layer 4 "difference from peers" **may be left to the second version**, but the filter's principle must be written into the data structure from the first version;
4. splitting training units by cognitive load;
5. generating reconstruction hints (constrained by §13);
6. the copy editor (pasting forbidden, no live intervention);
7. the comparison engine outputting three-layer feedback (where it doesn't resemble / why / how to change) + the graded list, with **all eight hard criteria in force**;
8. improvement checking after a second submission;
9. writing to the database: unit, version, model name, prompt version, evidence items;
10. the **sentinel regression test** (runnable apart from the UI);
11. the dimension view of the growth archive.

**Explicitly not done:** accounts, cloud sync, a model-text community, a model-text recommendation algorithm, multi-user comparison, any form of ranking. These conflict with the "local personal use + open source" positioning, or introduce unnecessary complexity. **Layer 4's peer-baseline comparison and the blind-test tool can be deferred, but sentinel regression cannot be deferred** — it is the only mechanism that can stop systematic drift during development.

### 23. Final principles, consistent with V0.1/V0.2

The four sentences still hold; this version only makes them executable:

- model texts are not for appreciation, they are for learning;
- AI is not for ghost-writing, it is for discovering gaps;
- feedback is not for evaluating the user, it is for guiding the next copy exercise;
- the end goal is not to make the user more and more like some author, but for the user, through long-term imitation, to form his own writing ability and taste.

---

## Appendix: V0.2 → V0.3 revision comparison

| Item | V0.2 | V0.3 | Reason |
| --- | --- | --- | --- |
| Closeness algorithm | seven dimensions with fixed weights, totalling 100 points | weights and total score abolished, replaced by gap ranking | weights have no source; fixed weights conflict with deliberate practice; a total score is useless for training |
| Single closeness | one quantity serving as memory, ability and trend | split into M (memory fidelity) / G (dimension gaps) / C (convergence trend) | one quantity cannot carry three semantics at once |
| First-pass data | counted into the closeness series | counted into M only, not into the ability curve | the first pass mainly reflects the text's memorability |
| Author model | generates a style description | four-layer structure: statistical fingerprint / judgment items + evidence / calibration samples / difference from peers | a description cannot be validated; and only the part that differs from peers is worth training |
| Author model acceptance | unspecified | hold-out validation + three confidence levels (author / work / insufficient sample) | an unvalidated model contaminates all later judgment |
| Amount of feedback | report everything found, presented in grades | show everything, but "change this round" limited to 1–3 items | counting replaces filtering, satisfying full transparency and focus at the same time |
| Basis for difficulty adjustment | the closeness number | gap ranking and rounds of improvement | the total score has been abolished |
| Style transfer report | style fit | an author-range hit comparison table | a number cannot be interpreted |
| Validating the system itself | not addressed | calibration set + judgment-error recovery + **sentinel regression** + effectiveness testing + blind test | an open-source project needs to be verifiable |
| Form and data | unspecified | local-first, provider-agnostic, version-traceable | determines the architecture and how copyright is handled |
| **Proxy drift** | **not recognized** | **its own Part 2, with six hard lines of defence** | measured proof: the system stably trains the user to be "like the author as described by the AI" |
| **Metric permissions** | no distinction | layer 1 describes only, layer 2 judges; features split into four types with different permissions | all four false positives in the probe came from layer 1 overstepping into judgment |
| **Unit of measurement** | unspecified | each metric declares its sampling level, cross-level comparison forbidden | the missed detection of "list-style opening 0/7" was caused entirely by inconsistent units |
