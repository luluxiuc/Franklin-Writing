# 实验材料与脚本

这里放实验一的**全部原始材料、裁判判定和分析脚本**。

> **这些文件同时也是研究报告的一部分,在 [`docs/研究/实验数据/`](../docs/研究/实验数据/) 有一份说明与副本。**
> 那边有中文说明,英文说明在 [`docs/research/experiment-data/`](../docs/research/experiment-data/)。

---

## 有什么

| 文件 | 是什么 |
| --- | --- |
| `PREREGISTRATION.json` | 预注册的判定规则,在看到任何结果之前冻结 |
| `key.json` | 材料答案:打乱顺序、哪 8 块真实、各模仿稿植入的缺陷 |
| `build_material.py` | 材料构造(匿名化 + 固定种子打乱) |
| `judge1.json` `judge3.json` `judge5.json` | 3 位裁判逐块留存的判定与自报置信度 |
| `store_judges.py` | 把裁决写入 `judgeN.json`(**裁决值是人工转录的常量**) |
| `score.py` `final_stats.py` `analyze_disagreement.py` | 打分与统计 |
| `fingerprint_compare.py` | 归一化特征对比(纯计算) |
| `human_kit.py` | 真人标注工具(生成**不含答案**的空白材料、算人类一致率) |
| `verify_report.py` | 核对报告引用的数字 |
| `实验一最终结果.md` `实验一结果与实验二设计.md` | 报告文本(与 `docs/研究/` 下同) |

---

## 没有的两个文件,以及为什么

**`blocked.json`**(18 块完整文本)与由它生成的 **`人工标注材料.md`** 被有意排除,**不在仓库里**:

- 其中 8 块是**受版权保护的已发表作品**(汪曾祺《端午的鸭蛋》),不能随仓库分发;
- 另外 10 块模仿稿是照着那 8 块写的,**脱离原文也就没有意义**。

**这不是遗漏,是决定。** 想复现实验,请自己从公开来源取得语料,然后:

```bash
python build_material.py      # 按 PREREGISTRATION 的参数重建匿名块
```

打乱用的**固定种子**记录在 `build_material.py` 里,所以重建出来的块序与当年的实验一致。
`human_kit.py materials` 也能据此重新生成**不含答案**的标注材料。

详见 [`docs/研究/实验数据/README.md`](../docs/研究/实验数据/README.md),那里还写明了另外两件必须知道的事:
**只有 3 位裁判的逐块判定有留档**、**裁决值是人工转录的**。
