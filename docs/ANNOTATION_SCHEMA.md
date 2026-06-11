# Annotation schema

Each sample in LogicBench-1K is a pair:

- **Image:** `images/lb1k_{id}.jpg` where `{id}` is a zero-padded five-digit index (`00000`-`00999`).
- **Annotation:** `annotations/lb1k_{id}.json`

Corpus-level statistics (gate mix, graph size, topology): [`../metadata/STATISTICS.md`](../metadata/STATISTICS.md).

## Graph semantics

Annotations encode a **directed graph** \(G = (V, E)\):

- **Vertices** (`nodes`) are logic gates. Node IDs are local strings `gate_0`, `gate_1`, ... assigned per diagram.
- **Edges** (`edges`) are directed connections from an output terminal of `source` to an input of `target`.
- Edges represent **logical connectivity** (netlist topology), not pixel polylines or geometric wire segments.

Downstream systems (e.g. SLCV in the reference paper) may derive pixel-level stroke evidence separately; this release stores **symbol-level topology** only.

## Fields

### `nodes` (required)

Array of gate objects.

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | string | Must match `^gate_[0-9]+$` and be unique within the file |
| `type` | string | One of: `AND`, `OR`, `NOT`, `NAND`, `NOR`, `XOR`, `XNOR` |

### `edges` (required)

Array of directed edges. May be empty for degenerate circuits.

| Field | Type | Constraints |
|-------|------|-------------|
| `source` | string | Must reference an existing `nodes[].id` |
| `target` | string | Must reference an existing `nodes[].id` |

Self-loops and duplicate edges are discouraged but not enforced by the schema validator; researchers should treat the provided graphs as authoritative ground truth.

### `image_path` (required)

Relative path from the repository root to the paired image, e.g. `images/lb1k_00042.jpg`.

## JSON Schema

Machine validation: [`../schema/annotation.schema.json`](../schema/annotation.schema.json)

## Integrity checks

```bash
python3 scripts/validate_dataset.py
python3 scripts/generate_statistics.py
```

Checks include: file pairing, split disjointness, schema conformance, unique node IDs, and valid edge endpoints.
