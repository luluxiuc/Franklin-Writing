[English](README.md) · [中文](../../研究/实验数据/)

# Experiment data and scripts

This directory holds **the raw verdicts, the material parameters, and every analysis script** from Experiment 1. Every figure in the research reports should be traceable to a file here.

---

## What is here

| File | What it is |
| --- | --- |
| `PREREGISTRATION.json` | **The pre-registered decision rule.** Frozen before any judge output was seen: rules D1–D5, the negative results that must be reported, and what this test **cannot** show. |
| `key.json` | The answer key: the shuffled order of the 18 blocks (`order`), which 8 are real (`A_ids`), and the injected defect recorded for each imitation (`B[*].quality` / `.note`). |
| `judge1.json` `judge3.json` `judge5.json` | The per-block verdicts **that were archived**, for 3 judges: verdict and self-reported confidence. |
| `build_material.py` | Material construction: anonymization and fixed-seed shuffling, with every parameter. |
| `score.py` `final_stats.py` `analyze_disagreement.py` | Scoring and statistics. |
| `confidence_stats.py` | Relation between self-reported confidence and correctness. |
| `verify_aggregates.py` | Recomputes the cross-tabs from all 5 judges' verdicts and checks them against the reports. |
| `verify_report.py` | Checks that figures quoted in the reports match the data files. |
| `fingerprint_compare.py` | Normalized feature comparison (pure computation) — used to rule out "the judges just found the passages thin". |
| `analyze_fingerprint.py` | Statistical fingerprint (pure computation, zero model calls). |
| `human_kit.py` | Human annotation kit: **generates annotation material with the answers stripped out**, collects annotations, computes pairwise human agreement, and compares it against the LLM judges. This is the missing link in Experiment 1. |
| `store_judges.py` | Writes the collected verdicts into `judgeN.json`. **Note: the verdict values are hand-transcribed constants in this script** — the original capture channel was not preserved. |

---

## Recomputing

```bash
cd docs/research/experiment-data

python analyze_fingerprint.py     # statistical fingerprint (pure computation, no key)
python fingerprint_compare.py     # normalized feature comparison (pure computation)
python verify_aggregates.py       # 5-judge cross-tabs vs the reports
python confidence_stats.py        # confidence vs correctness
```

---

## Three things that must be stated plainly

### 1. The repository does **not** contain the corpus

The material is **8 real published passages + 10 imitations**, 18 complete texts in total. They are **not in this repository**:

- the 8 real passages are published, copyrighted work and **cannot be redistributed**;
- the imitations were written against those passages and are **meaningless without them**.

So `blocked.json` (all 18 full texts) and the annotation material generated from it **have been excluded**. Obtain the corpus from public sources yourself, then:

```bash
python build_material.py      # rebuilds the anonymized blocks using the pre-registered parameters
```

The **fixed shuffle seed** is recorded in `build_material.py`, so the rebuilt block order matches the original experiment.

### 2. Only 3 of the 5 judges have archived per-block verdicts

Experiment 1 used **5** judges. Per-block files survive for only 3 (`judge1` / `judge3` / `judge5`). **The verdicts of judges 2 and 4 exist only inside the report tables**; the original capture record was not kept.

- `verify_aggregates.py` contains all 5 judges' verdicts and reproduces the report's cross-tabs exactly (judge 2 = 16/18, clean-imitation detection 3/5; judge 4 = 13/18, clean detection 0/5);
- but **confidence is only available for 3 judges**, so the confidence statistics cover only those 3;
- this is a record-keeping defect. It is written here rather than hidden.

### 3. The verdicts were hand-transcribed

The verdicts in `store_judges.py` are **hand-transcribed constants**, not machine-read from a capture log. That means:

- transcription error is a real risk. **What we did about it:** `verify_aggregates.py` recomputes the cross-tabs from the 5 judges' verdicts and matches the reports exactly, and `verify_report.py` separately checks figures quoted in the report body.
- but this only proves **the transcription and the reports agree with each other**; it does not prove **the transcription matches what the models actually output at the time**, because those outputs were not archived.
- The only complete fix is to re-run the experiment with the raw logs retained. **That is one of the items on the [roadmap](../../../ROADMAP.md).**

---

## The finding about confidence

Recomputable with `confidence_stats.py`:

| Group | n | Correct | Mean confidence when correct | Mean confidence when wrong |
| --- | --- | --- | --- | --- |
| A real | 24 | 24/24 | 4.88 | — |
| B clean imitation | 15 | 5/15 | 3.80 | **4.10 (n=10)** |
| B defective imitation | 15 | 15/15 | 4.80 | — |

**All 10 errors were made at self-reported confidence ≥ 4, one of them at the maximum of 5.**

Why this matters: **the errors are not hedged.** If the mistakes clustered at low confidence, one could argue for filtering on confidence. In fact the judges were just as certain when they got it backwards — which, combined with "the errors point systematically one way", explains why this kind of judgment is especially damaging once wired into training feedback: the user sees no warning signal at all.

**But do not over-read this:** confidence is **self-reported by the model** and was never independently calibrated. It is enough to show these were not low-confidence coin flips. It is **not** evidence that the model is well calibrated.
