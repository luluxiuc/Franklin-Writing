[English](README.en.md) · [中文](../设计/)

# Design documents

This directory holds the **design history** of this tool: how it started as a system that judged writing, and converged into a pure tool that does not judge at all.

Read in chronological order and you can see the direction being overturned by measured data:

| Document | What it is | Status |
| --- | --- | --- |
| [`core-method-v0.3.en.md`](core-method-v0.3.en.md) | Methodology v0.3. **The first document to name "proxy drift" as the project's most dangerous failure mode.** | Superseded |
| [`../设计/跑测报告01-指纹与反馈引擎.docx`](../设计/跑测报告01-指纹与反馈引擎.docx) | Run report for the hand-written threshold rules: four structural false positives (flagging the author's own text as "deviating from the author", sampling at the wrong level, treating a low-frequency feature as a per-passage requirement, and scoring a closer imitation no better than a bad one). **The earliest evidence for deleting the judgment.** Chinese only; its findings are restated in full in the [decision report](../research/why-no-llm-judgment.md), section 2. | Record |
| [`no-judgment-design-v1.0.en.md`](no-judgment-design-v1.0.en.md) | The product design after all AI judgment was removed. **The direct source of the shipped tool.** | Current |
| [`user-guide.en.md`](user-guide.en.md) | The user-facing guide: how to import, how to practise, how hints stay cheap, where the data lives. | Current |

The Chinese originals of the methodology, the no-judgment design and the user guide are in [`../设计/`](../设计/). The run report and the Word versions of these documents are Chinese-only for now.

---

## How this relates to the research

**Why the judgment was deleted is not explained here — it is explained in the research.**

- Data and conclusions: [`docs/research/`](../research/) (English) · [`docs/研究/`](../研究/) (中文)
- One line: discriminating power came 100% from "does it contain an obvious defect" and 0% from "does it sound like the author".

---

## Why the deleted design is still in the repository

`core-method-v0.3.en.md` and the engine run report describe **a product that was never built**, including a comparison engine, an author-model judgment layer, gap ranking and convergence trends.

Two reasons to keep them:

1. **They are the basis for the deletion.** Without the four false positives in the run report, "no judgment" is just a stance. With them, it is a decision supported by evidence.
2. **They record the road that failed.** If someone later wants to reintroduce AI judgment — and eventually someone will — reading these two first saves them from repeating the same mistakes.

**But be clear: the design they describe is not the product this project is building.** Do not implement from them.
