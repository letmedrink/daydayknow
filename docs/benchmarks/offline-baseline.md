# llmwiki 离线 Benchmark 基线

- 模式：`offline`
- Dataset：`1.0.0`（CC0 合成数据）
- 基线 Git SHA：`11713985fa0527455a33a78d1f8e2a0b9b944162`
- Pipeline / Parser：`3` / `1`
- Provider：`fake` / `deterministic-fixture`
- 运行时间：`2026-08-24T05:10:13.929Z`
- 进程模型：单机、单进程

## 结果

| 指标 | 结果 |
| --- | ---: |
| 总分 | 100.00 |
| 摄入 | 100.00 |
| 问答 | 100.00 |
| Lint | 100.00 |
| 安全硬门禁 | PASS |
| 场景 | 10 / 10 |
| 必须事实召回率 | 1.0000 |
| 旧事实保留率 | 1.0000 |
| 禁止断言规避率 | 1.0000 |
| create/update 准确率 | 1.0000 |
| 来源绑定率 | 1.0000 |
| Schema 合规率 | 1.0000 |
| Recall@1 | 1.0000 |
| Recall@3 | 1.0000 |
| MRR | 1.0000 |
| 检索 P50 | 2.124 ms |
| 检索 P95 | 2.322 ms |

| 场景 | 分组 | 分数 | 硬门禁 | Fake LLM 调用 |
| --- | --- | ---: | --- | ---: |
| `ingest-create` | ingest | 100.00 | PASS | 2 |
| `ingest-update-preserve` | ingest | 100.00 | PASS | 2 |
| `ingest-revise-claim` | ingest | 100.00 | PASS | 2 |
| `ingest-contradiction` | ingest | 100.00 | PASS | 2 |
| `ingest-source-idempotency` | ingest | 100.00 | PASS | 4 |
| `ingest-long-tail` | ingest | 100.00 | PASS | 3 |
| `ingest-schema-injection` | ingest | 100.00 | PASS | 2 |
| `query-grounded-answer` | query | 100.00 | PASS | 1 |
| `query-backfill` | query | 100.00 | PASS | 2 |
| `lint-mixed-findings` | lint | 100.00 | PASS | 1 |

## 口径

该结果证明固定输入和固定模型输出下的 Pipeline、评分器与安全约束可重复通过，不代表真实模型能够获得 100 分。真实生成质量必须使用 `live` 模式单独测量。延迟来自当前开发机上的短合成页面，只用于本次运行记录，不是生产 SLA，也不应与不同硬件上的结果直接比较。
