[English](README.en.md) · [中文](README.md)

# Experiment material and scripts

This directory holds **every piece of raw material, the judge verdicts, and the analysis scripts** from Experiment 1.

> **These files are also part of the research report; there is an explanation and a copy under [`docs/research/experiment-data/`](../docs/research/experiment-data/).**
> That one is in English; the Chinese version is under [`docs/研究/实验数据/`](../docs/研究/实验数据/).

---

## What is here

| File | What it is |
| --- | --- |
| `PREREGISTRATION.json` | The pre-registered decision rule, frozen before any result was seen |
| `key.json` | The answer key for the material: the shuffled order, which 8 blocks are real, the defect injected into each imitation |
| `build_material.py` | Material construction (anonymization + fixed-seed shuffling) |
| `judge1.json` `judge3.json` `judge5.json` | The per-block verdicts and self-reported confidence archived for 3 judges |
| `store_judges.py` | Writes the verdicts into `judgeN.json` (**the verdict values are hand-transcribed constants**) |
| `score.py` `final_stats.py` `analyze_disagreement.py` | Scoring and statistics |
| `fingerprint_compare.py` | Normalized feature comparison (pure computation) |
| `human_kit.py` | Human annotation kit (generates blank material **with the answers stripped out**, computes human agreement) |
| `verify_report.py` | Checks the figures quoted in the reports |
| `实验一最终结果.md` `实验一结果与实验二设计.md` | Report text — "Experiment 1 final results" and "Experiment 1 results and Experiment 2 design" (the same files as under `docs/研究/`) |

---

## The two files that are not here, and why

**`blocked.json`** (all 18 complete texts) and the **`人工标注材料.md`** generated from it (the human-annotation material) are deliberately excluded — they are **not in this repository**:

- 8 of those blocks are **published work under copyright** (the essay 汪曾祺《端午的鸭蛋》 by Wang Zengqi, "Duck Eggs of the Dragon Boat Festival") and cannot be distributed with the repository;
- the other 10 blocks are imitations written against those 8, and **without the originals they mean nothing**.

**This is not an oversight. It is a decision.** To reproduce the experiment, obtain the corpus from public sources yourself, then:

```bash
python build_material.py      # rebuilds the anonymized blocks from the PREREGISTRATION parameters
```

The **fixed shuffle seed** is recorded in `build_material.py`, so the blocks you rebuild come out in the same order as in the original experiment.
`human_kit.py materials` also regenerates the annotation material **with the answers stripped out** from those same parameters.

See [`docs/research/experiment-data/README.md`](../docs/research/experiment-data/README.md), which also spells out the other two things you must know:
**per-block verdicts were archived for only 3 judges**, and **the verdict values were hand-transcribed**.
