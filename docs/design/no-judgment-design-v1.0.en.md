[English](no-judgment-design-v1.0.en.md) · [中文](../设计/无判断版设计-v1.0.md)

# Franklin Writing Tool (No-Judgment Edition): Design v1.0 Draft

> Trigger condition: if the conclusion of the LLM style-judgment capability test is D1/D2/D5 (judgment unreliable), the project switches to this design.
> Relation to v0.3: it keeps **all of v0.3's training structure** and deletes **all AI judgment**.

---

## 1. One-sentence positioning

**Turn the Franklin writing method into a handy, sustainable process tool. The system handles splitting, hints, hiding and recording; understanding and judging are done entirely by the user.**

It is not "AI helps you write", and it is not "AI rates your writing". It is:

> **AI puts the actions you are supposed to perform in the right order; you do the rest.**

## 2. What was deleted

| Module in v0.3 | Disposition | Reason |
| --- | --- | --- |
| Comparison engine (where it doesn't resemble / why / how to change) | **Deleted** | Judgment is unreliable; and the user sees the original themselves anyway |
| Author model layer 2 (LLM judgment items) | **Deleted** | Same as above |
| Author model layer 4 (difference from peers) | **Deleted** | Depends on judgment |
| Style transfer's "author-range hit rate" | **Deleted** | Depends on judgment |
| Focus set, gap ranking, convergence trend | **Deleted** | All depend on judgment |
| Capability conclusions in the long-term archive | **Deleted** | Same as above |

**Key realisation: every one of these deleted things was the only part of v0.3 capable of drifting.** Delete them and proxy-drift risk goes to zero; sentinel regression, calibration sets and blind tests are no longer needed — because the system no longer makes any assertion about "resembling".

## 3. What remains (this is the entire product)

### 3.1 Splitting (program + user confirmation)

- Split the article into training units by cognitive load (by default by length and structural complexity; one-click re-splitting is allowed).
- **No naming of expressive moves** (that is an interpretation). Report scale only: how many characters, how many sentences, how many clauses.
- Split results are saved, and re-split history is saved.

### 3.2 Reconstruction hints (the only module involving generation, and tightly restricted)

- A hint **describes the content skeleton only**; it describes no rhetoric, no technique, no effect.
- Format: **mechanically extracted** from the original by the program — the concrete objects, actions and order that appear.
  - Example: `丝线／手腕／香角子／帐钩／五毒／门槛／符／城隍庙` (silk thread / wrist / incense sachet / curtain hook / the five poisons / doorstep / charm / City God temple)
- **Make the "hint" a keyword list rather than a sentence description.** That way it cannot carry any interpretation, and it leaks almost no wording.
- The user can turn hints off. The history marks "this round used hints", for their own reference.

### 3.3 Forced reconstruction (the editor is the training ground)

- Pasting is forbidden; no live correction; no spelling underlines; no suggestions of any kind.
- After submission, no further entry point for re-viewing the original is provided within this unit (the original appears naturally at the comparison stage).
- An "I can't remember" button is provided: it honestly accepts the incomplete draft, giving no hints and no ladder.
- **Delay mechanism:** a forced wait after submission (10 minutes by default, configurable), during which the original cannot be viewed. This is the core action of the Franklin method and is worth making an unskippable constraint.

### 3.4 Side-by-side comparison (the real body of the product)

With AI judgment removed, this screen goes from a supporting feature to the core feature. Requirements:

- **Original and user draft aligned sentence by sentence, side by side**, on the same screen, at the same font size, in the same layout.
- **Concrete objects from the original that are not hit in the user's draft are marked automatically** (mechanical comparison, not judgment).
- The user looks at the differences and says them, themselves.
- **A "my observations" input box is provided**: the user writes down the differences they see. This is the only "judgment" that is saved, and it is the user's own.
- Optional: compare "my observations" against the previous round's, to see how your attention has changed.

### 3.5 Memory coverage M (mechanically computed; the only quantitative measure retained)

- Compute the **hit rate** in the user's draft of the concrete objects, proper nouns and key verbs from the original.
- This is a **pure string/vocabulary comparison**, not judgment, so it is reproducible and cannot drift.
- **The reporting format is strictly limited to facts:** "12 concrete objects appear in the original; 5 appear in your draft", together with a list of which 7 are missing.
- It is **forbidden** to convert this into a score, **forbidden** to say "how much you remembered", **forbidden** to give it a name like "fidelity". List only.

### 3.6 History and archive (record facts only, draw no conclusions)

- Each round records: unit, time, whether hints were used, M's hit list, the verbatim text of "my observations", time taken.
- The archive **does not generalize**. The system does not tell you "you habitually forget scenery description" — that too is a judgment.
- Instead: **lay out the raw data that might show a pattern**, and let the user look at it themselves.
  - Example: list the missing-objects list for each of the last 10 sessions. Whether the user notices "I always drop environment-type objects" is for them to judge.

## 4. One risk that still exists, and how it is handled

**Risk:** the user may not do the comparison either, submitting hastily and going straight into the next unit — the tool has no judgment, so there is no pressure of "being caught".

**Handling:** no forced scoring, but **process constraints**:
- After submission you must enter the side-by-side comparison screen, and you **must write at least one "my observations"** entry before that unit can be ended (you may write "I can't see a difference", but you must write it explicitly).
- Scoring is not about good or bad; it **records whether the actions were completed**: whether this round left the original behind, whether the wait happened, whether the comparison was completed, whether observations were written. This is **process completion**, not writing quality.

## 5. Trade-offs compared with v0.3 (stated plainly)

| | v0.3 (with judgment) | This design (no judgment) |
| --- | --- | --- |
| What can be learned | Possibly more (there is signposting) | Depends on the user's own powers of observation |
| Drift risk | High, and already measured | **Zero** |
| Cost | Several model calls per round | Near zero (hints are mechanically extracted) |
| Privacy | Requires network | Can be completely offline |
| Open-source value | Needs calibration sets and sentinel maintenance | Light, easy to reproduce, easy for others to verify |
| Honesty | The system must constantly prove it has not drifted | The system never claims to be judging |

**Core judgment:** the driving force of the Franklin method is "active reconstruction + delay + self-comparison", not "being told the gap". The research that the study report itself cites also points out that the quantity of feedback does not guarantee an effect, and that **the learner's actual participation is the key**. Deleting judgment puts all the learning pressure back where it originally belonged — on the user.

## 6. What this design can still be tested on

Deleting judgment does not mean it cannot be verified. You can still test:

1. **Whether the process is stuck to**: completion rate, average number of rounds, where people give up.
2. **Whether self-observation changes**: whether the user's "my observations" go from "the words are different" to "the structure is different" around round 10.
3. **Whether transfer writing changes**: using new text that took no part in training, compare the 1st time with the 10th. **The user judges** the difference between them; the system is responsible only for laying the two drafts side by side.

None of these three requires the system to make any style judgment, so none of them can lead the user astray.
