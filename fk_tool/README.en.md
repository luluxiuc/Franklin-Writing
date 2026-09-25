[English](README.en.md) · [中文](README.md)

# fk — Franklin writing method tool (no-judgment edition) · command-line prototype

> **This prototype has been replaced by the web version.** Use `启动.cmd` (or `启动.sh`) in the repository root instead;
> the documentation is at [`docs/design/user-guide.en.md`](../docs/design/user-guide.en.md). This directory is kept for the record only, and is unmaintained:
> the web version's engine `app/fk_core.py` grew out of `fk.py`, and the first version of the constraint self-check is here too.

Making the Franklin writing method easy to keep up with. **The system handles splitting, hinting, hiding, recording; all understanding and all judgment stay with you.**

This tool makes **no judgment about "whether it is written well" or "whether it sounds like the author"**, **calls no model**, and runs fully offline.

---

## Why there is a no-judgment edition

This decision is not a design preference; it is a measured conclusion. We ran an authorship test on 18 anonymized text blocks — 8 real published passages + 10 AI imitations (5 with no injected defect, 5 with one named defect each) — with 5 independent LLM judges:

| Metric | Result |
| --- | --- |
| Real text misjudged as imitation | 0% (all 5 judges got 8/8 right) |
| Imitations with an obvious injected defect, detected | 100% (all 5 judges detected 5/5) |
| **Imitations with no injected defect, detected** | **0%** (3 of the 5 judges scored 0/5) |

Worse is the direction of the errors: the judges' stated reasons were **rejecting the author's own features** — treating "留白收束" ("closing on an unresolved note") and "自我不确定的元陈述" ("meta-statements of self-doubt") as flaws, when those are exactly this author's signature devices. One judge even **fabricated linguistic evidence** (claiming "一个线轴只缠一色线", "a spool holds only one colour of thread") to support a style judgment.

**Conclusion:** what an LLM can do is "defect detection" (against a blacklist), not "style recognition". Passing defect detection off as style judgment in training feedback will reliably push the user away from the target author.

So this tool keeps only the parts that do not depend on judgment. The full research record is in `_capability/实验一最终结果.md` ("Experiment 1 final results").

---

## Install and run

Requires only the Python 3.8+ standard library.

```bash
python fk.py import 范文.txt --title "汪曾祺《端午的鸭蛋》" --size 150
python fk.py status
python fk.py write   <作品id> 1
python fk.py compare <作品id> 1
python fk.py list    <作品id>
```

*In the first command, `范文.txt` is the file being imported and 汪曾祺《端午的鸭蛋》 is that work's title ("Duck Eggs of the Dragon Boat Festival" by Wang Zengqi); `<作品id>` is the work id printed by `status`.*

`--size` is the target character count for each practice unit (default 150). Splitting goes **by size only** and does not judge "expressive moves" — that would be an interpretation.

---

## What one practice round looks like

**1. `write` — imitation**

The original is hidden. The system gives you only a **mechanically extracted list of content fragments**:

```
家乡　端午　多风俗　外地　索子　丝线拧成　小绳　手腕　丝线　掉色　洗脸　印得红
```

*(home town · Dragon Boat Festival · many customs · elsewhere · the cord · twisted from silk thread · small cord · wrist · silk thread · colour runs · washing the face · prints red)*

Every one of these fragments is a contiguous substring that really does occur in the original, extracted by a spanning scan plus an already-covered marker, and it **carries no instruction on how to write and contains no rhetorical terminology**. You do not have to use the hints.

Rewrite that passage from memory below the hints, and end the paste with `END`. If you cannot remember it, leave it blank — **the system will not give you more hints, and it will not hand you a ladder.**

**2. The delay**

After you submit, you **must wait 10 minutes** by default before you can look at the original. This is the single most important step in the Franklin method (it lets the memory leave the short-term buffer). `--skip-delay` skips it, but you should know what you are skipping.

**3. `compare` — side-by-side comparison**

```
原　文                          │你的稿子
==============================================================================
家乡的端午，很多风俗和外地一样。      │家乡的端午，很多风俗和外地一样。
系百索子。                       │因为要系百索子，所以人们把五色的丝线拧成小绳，
五色的丝线拧成小绳，系在手腕上。      │系在手腕上，让我感到非常温暖。
丝线是掉色的，洗脸时沾了水……        │
==============================================================================

【具体名物】以下是机械比对结果，只列事实，不评价。
  出现（9）：家乡、端午、多风俗、外地、索子、丝线拧成、小绳、手腕、丝线
  未出现（5）：掉色、洗脸、印得红、道绿、做香角子

  未出现不等于写得不好——可能是有意省略。判断在你自己。
```

*("原　文" = the original, "你的稿子" = your draft; 【具体名物】 = "concrete named things", followed by a mechanical comparison that lists facts only and evaluates nothing; 出现（9）= present (9); 未出现（5）= absent (5); the closing line says an absent fragment does not mean it was written badly — it may be a deliberate omission, and the judgment is yours.)*

Coverage is a **pure substring comparison**; it is not converted into a score, and it never says "how much of this you remembered".

**4. What I noticed (mandatory)**

```
【我的观察】请写下你自己看到的差异。系统不会替你判断。
看不出差别也可以，但必须写出来。
```

*("What I noticed: write down the differences you see for yourself. The system will not judge in your place. It is fine if you cannot see a difference, but you must write it down.")*

Without a written observation, the unit does not count as complete. **Once the AI judgment is gone, observation is the only learning action left.**

---

## Design constraints (hard, written into the code)

| Constraint | How it is enforced |
| --- | --- |
| No judgment | No code anywhere contains scores, similarity, or better/worse conclusions |
| No model calls | No network dependency at all; runs offline |
| Hints are fragments only | Every extracted item is a contiguous substring of the original, with no instruction on how to write |
| Coverage lists facts only | Reports hit/miss only, never converted into a score |
| Forced separation from the original | After submitting, the draft cannot be overwritten by default (`--force` is required to start over) |
| Enforced delay | `compare` checks the submission timestamp |
| Enforced observation | With no observation, no completion time is written to the store |
| The record does not generalize | Shows raw records only, and draws no "you always..." conclusions |

Constraint self-check: `python selftest.py` · End-to-end test: `python e2e_test.py`

---

## State storage

Everything is in `state/library.json` — purely local, no server. Each unit records: the original, the mechanical hints, your draft, the submission time, the coverage list, your observation, and the comparison time.

---

## Roadmap (not done)

- **Transfer practice**: rewrite in a different subject matter; you compare the two pieces yourself, the system does not judge.
- **Process completeness**: records "did you break away from the original, did you wait, did you write down an observation" — actions only, never good or bad.
- **Export**: export the comparison records as a printable side-by-side document.

**Will never do:** accounts, cloud sync, a model-essay community, model-essay recommendations, or any form of scoring or ranking.
