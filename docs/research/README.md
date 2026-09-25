[English](README.md) · [中文](../研究/)

# Research: can an LLM judge whether writing "sounds like the author"?

This directory holds the **evidence behind this project's central decision**. It is not promotional material.

The tool does not score, does not evaluate, and never says whether your writing "sounds like the author" — not because that was too hard, but because **we built it, measured it, and deliberately deleted it.** Everything here is the material behind that: the design, the raw numbers, and the parts that are unfavourable to us.

---

## The conclusion, in one line

> **Discriminating power came 100% from "does it contain an obvious defect" and 0% from "does it sound like the author".**

5 independent LLM judges / 18 anonymized text blocks / pre-registered decision rule:

| Metric | Result |
| --- | --- |
| Real text misjudged as imitation | **0%** |
| Imitations with an injected defect, detected | **100%** |
| **Imitations with no injected defect, detected** | **0%** |

And **the errors are systematic**: the judges rejected the author's own signature devices. Wire that into a training loop and the user drifts toward being a competent, ordinary writer — away from the author they set out to learn from.

---

## Which document to read

| What you want | Read this | 中文 |
| --- | --- | --- |
| **Why the decision is correct** (full reasoning, costs, follow-ups) | [`why-no-llm-judgment.md`](why-no-llm-judgment.md) | [`为什么不做LLM判断评分.md`](../研究/为什么不做LLM判断评分.md) |
| **The whole research conclusion** (three layers of judgment, measured) | [`llm-authorship-judgment.md`](llm-authorship-judgment.md) | [`LLM能否判断像不像作者.md`](../研究/LLM能否判断像不像作者.md) |
| **Experiment 1: per-block votes and per-judge cross-tabs** | [`experiment-1-final-results.md`](experiment-1-final-results.md) | [`实验一最终结果.md`](../研究/实验一最终结果.md) |
| **Where every number comes from** (recomputable) | [`appendix-measured-data.md`](appendix-measured-data.md) | [`附录-实测数据汇总.md`](../研究/附录-实测数据汇总.md) |
| **Experiment 2 design** (single-sentence discrimination, not run) | [`experiment-2-design.md`](experiment-2-design.md) | [`实验一结果与实验二设计.md`](../研究/实验一结果与实验二设计.md) |
| **Raw material and scripts** | [`experiment-data/`](experiment-data/) | [`实验数据/`](../研究/实验数据/) |

### One easily-missed figure

All 10 of the judges' errors were made at **self-reported confidence ≥ 4**, one at the maximum of 5. **The errors are not hedged.** If they clustered at low confidence one could argue for filtering on confidence; in fact the judges were just as certain when they got it backwards. Recompute with `python docs/research/experiment-data/confidence_stats.py`.

---

## Reproducing it

**Everything in sections A, B and C is pure local computation with zero model calls.** Sections D and E are the controlled judge experiments.

```bash
# Statistical fingerprint (pure computation, no API key needed)
python _probe/analyze_fingerprint.py

# Normalized feature comparison (pure computation)
python _capability/fingerprint_compare.py

# Re-run scoring and statistics over the collected judge outputs
python _capability/score.py
python _capability/final_stats.py
python _capability/analyze_disagreement.py
python _capability/verify_report.py
```

**The corpus is not distributed with this repository.** It is a published work; obtain it from public sources yourself. The material-construction script `_capability/build_material.py` records every parameter, including the fixed shuffle seed, so the anonymized blocks can be rebuilt from it.

---

## Problems in our own study

**A project that claims to be honest cannot report only the favourable data.** These are the defects in this research, all on the record:

| Limitation | Detail | Status |
| --- | --- | --- |
| **Human agreement was never measured** | All judges are LLMs — circular. This measures self-consistency, not agreement with human experts. Tooling exists (`_capability/human_kit.py`); **needs 3+ qualified readers to each annotate once.** | Open |
| **The retrieval channel was not removed** | 3 of 5 judges violated the protocol and looked up the source, despite an explicit instruction not to speculate about authorship. **So "0% misjudgment on real text" cannot be credited purely to style recognition.** | Open |
| **The same-length paired test failed** | With lengths strictly matched, the judge's reason was "verbatim identical to the original, i.e. an excerpt", with a citation link — it bypassed style comparison. | Recorded |
| **Experiment 2 is designed but not run** | Single-sentence discrimination is the design that would truly separate style judgment from length judgment. | Open |
| **The experimenter built the materials *and* designed the study** | The imitations carry the experimenter's own fingerprint; there is no way to separate "recognised the author's hand" from "recognised the experimenter's hand". | Structural |
| **Small sample** | 18 blocks, 5 judges — directional only. | Recorded |
| **The pre-registered rule missed the real failure mode** | Its trigger was "flagging real text as imitation"; the actual failure was accepting competent imitations. The corrected rule is recorded together with its reasoning, so it does not become post-hoc criterion picking. | Recorded |

**But these limitations can only strengthen the conclusion, not overturn it**: the judgment is unstable between humans too, and the disagreement concentrates on exactly the kind of text a learner produces.

---

## Citing this

Use [`CITATION.cff`](../../CITATION.cff) at the repository root. **If you reproduce or refute these results, please open an issue** — a refutation backed by data is a valuable contribution.
