# Benchmark tasks and metrics

LogicBench-1K supports evaluation aligned with *Stroke-Level Connectivity Verification* (reference paper §4.1, ICDAR 2026).

Dataset composition and topology statistics: [`../metadata/STATISTICS.md`](../metadata/STATISTICS.md) · [`../metadata/statistics.json`](../metadata/statistics.json).

## Task 1: Symbol detection

**Goal:** Detect and classify all logic gates in each diagram.

**Ground truth:** `nodes[].type` with implicit localisation via full-image context; for bbox-level evaluation, systems must produce bounding boxes matched to nodes via bipartite assignment (paper uses IoU ≥ 0.5).

**Metric:** **Gate accuracy**: classification accuracy over correctly localised components.

## Task 2: Graph recovery (connectivity)

**Goal:** Predict the directed connectivity graph between gates.

**Ground truth:** `edges` (and `nodes` for endpoint identity).

**Metrics:**

| Metric | Definition |
|--------|------------|
| **Connectivity F1** | Edge-level F1 over directed edges; endpoints must match the same symbol instances (bipartite bbox matching) with correct direction |
| **NED** | Netlist Edit Distance: minimum-cost graph edit distance with node insert/delete cost 1, edge insert/delete cost 1, node substitution cost 0.5 |

Connectivity F1 is the primary metric for topology hallucination studies.

## Task 3: Functional equivalence

**Goal:** Verify logical equivalence of extracted circuits.

**Status:** Defined in the paper but **not included** in this v1.0.1 release’s evaluation protocol; reserved for future work.

## Recommended evaluation protocol

1. Report results on **`test`** split only (`annotations/splits/test.txt`, 200 samples).
2. Do not tune on test; use **train** for model fitting and **val** for hyperparameters.
3. When comparing to published baselines, note whether methods are **zero-shot VLMs**, **fine-tuned VLMs**, or **supervised pipelines** (PaRCO).

## Reference results (paper)

| Setting | Connectivity F1 |
|---------|-------------------|
| Moondream2 (zero-shot) | 0.05 |
| LLaVA 7B (zero-shot) | 0.22 |
| Qwen3-VL (zero-shot) | 0.45 |
| LLaMA 3.2 Vision (zero-shot) | 0.58 |
| Gemini 1.5 Pro (zero-shot) | 0.76 |
| GPT-4o (zero-shot) | 0.78 |
| Claude 3.5 Sonnet (zero-shot) | 0.81 |
| LLaVA-1.5 fine-tuned | 0.87 |
| Claude 3.5 Sonnet + SLCV (hybrid) | 0.89 |
| PaRCO (supervised) | 0.98 |

## Clean vs. noisy subsets

The paper stratifies performance on **digital-native** (*D*<sub>clean</sub>) and **scanned-legacy** (*D*<sub>noisy</sub>) subsets. Subset membership labels are not shipped separately in v1.0.1; contact the author if you require the official subset manifest for exact reproduction.
