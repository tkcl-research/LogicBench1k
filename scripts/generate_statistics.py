#!/usr/bin/env python3

from __future__ import annotations

import json
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANNOTATIONS = ROOT / "annotations"
SPLITS_DIR = ANNOTATIONS / "splits"
OUT_JSON = ROOT / "metadata" / "statistics.json"
OUT_MD = ROOT / "metadata" / "STATISTICS.md"

GATE_VOCAB = ["AND", "NAND", "NOR", "NOT", "OR", "XNOR", "XOR"]
SPLITS = ("train", "val", "test")
NODE_HIST_BINS = [(1, 5), (6, 10), (11, 15), (16, 20), (21, 31)]
EDGE_HIST_BINS = [(0, 0), (1, 5), (6, 10), (11, 20), (21, 57)]


def load_ids(split: str) -> list[str]:
    return [
        line.strip()
        for line in (SPLITS_DIR / f"{split}.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def distribution_summary(values: list[int | float]) -> dict:
    if not values:
        return {"min": 0, "max": 0, "mean": 0.0, "median": 0.0, "std": 0.0, "q1": 0.0, "q3": 0.0}
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    q1 = statistics.median(sorted_vals[: n // 2]) if n > 1 else sorted_vals[0]
    q3 = statistics.median(sorted_vals[(n + 1) // 2 :]) if n > 1 else sorted_vals[0]
    return {
        "min": min(values),
        "max": max(values),
        "mean": round(statistics.mean(values), 3),
        "median": round(statistics.median(values), 3),
        "std": round(statistics.pstdev(values), 3) if len(values) > 1 else 0.0,
        "q1": round(q1, 3),
        "q3": round(q3, 3),
    }


def histogram(values: list[int], bins: list[tuple[int, int]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for lo, hi in bins:
        label = f"{lo}" if lo == hi else f"{lo}-{hi}"
        counts[label] = sum(1 for v in values if lo <= v <= hi)
    return counts


def gate_frequencies(gate_counts: Counter[str], total_gates: int) -> dict[str, dict]:
    return {
        gate: {
            "count": gate_counts.get(gate, 0),
            "proportion": round(gate_counts.get(gate, 0) / total_gates, 4) if total_gates else 0.0,
        }
        for gate in GATE_VOCAB
    }


def analyze(ids: list[str]) -> dict:
    gate_types: Counter[str] = Counter()
    gate_mix: Counter[tuple] = Counter()
    node_counts: list[int] = []
    edge_counts: list[int] = []
    in_degrees: Counter[int] = Counter()
    out_degrees: Counter[int] = Counter()
    isolated_nodes = 0
    empty_edge_graphs = 0

    for sample_id in ids:
        data = json.loads((ANNOTATIONS / f"{sample_id}.json").read_text(encoding="utf-8"))
        type_counts = Counter(node["type"] for node in data["nodes"])
        gate_mix[tuple(sorted(type_counts.items()))] += 1
        gate_types.update(type_counts)

        n = len(data["nodes"])
        e = len(data["edges"])
        node_counts.append(n)
        edge_counts.append(e)
        if e == 0:
            empty_edge_graphs += 1

        indeg: Counter[str] = Counter()
        outdeg: Counter[str] = Counter()
        for edge in data["edges"]:
            outdeg[edge["source"]] += 1
            indeg[edge["target"]] += 1
        for node in data["nodes"]:
            nid = node["id"]
            in_d, out_d = indeg[nid], outdeg[nid]
            in_degrees[in_d] += 1
            out_degrees[out_d] += 1
            if in_d == 0 and out_d == 0:
                isolated_nodes += 1

    total_gates = sum(gate_types.values())
    total_edges = sum(edge_counts)
    densities = [e / (n * (n - 1)) if n > 1 else 0.0 for n, e in zip(node_counts, edge_counts)]

    return {
        "num_samples": len(ids),
        "totals": {
            "gates": total_gates,
            "edges": total_edges,
            "avg_gates_per_sample": round(total_gates / len(ids), 3) if ids else 0.0,
            "avg_edges_per_sample": round(total_edges / len(ids), 3) if ids else 0.0,
        },
        "sample_diversity": {
            "unique_gate_mixtures": len(gate_mix),
            "mixture_coverage": round(len(gate_mix) / len(ids), 4) if ids else 0.0,
            "graphs_with_no_edges": empty_edge_graphs,
            "isolated_gate_instances": isolated_nodes,
        },
        "graph_size": {
            "nodes_per_graph": distribution_summary(node_counts),
            "edges_per_graph": distribution_summary(edge_counts),
            "node_count_histogram": histogram(node_counts, NODE_HIST_BINS),
            "edge_count_histogram": histogram(edge_counts, EDGE_HIST_BINS),
        },
        "topology": {
            "avg_directed_density": round(statistics.mean(densities), 4) if densities else 0.0,
            "gate_type_frequencies": gate_frequencies(gate_types, total_gates),
            "terminal_degree_histogram": {
                "in_degree": {str(k): v for k, v in sorted(in_degrees.items())},
                "out_degree": {str(k): v for k, v in sorted(out_degrees.items())},
            },
        },
    }


def render_markdown(stats: dict) -> str:
    g = stats["topology_distribution"]["global"]
    splits = stats["topology_distribution"]["by_split"]
    ps = stats["paper_summary"]

    lines = [
        "# LogicBench-1K Dataset Statistics (camera-ready)",
        "",
        f"**Version:** {stats['version']}  ",
        f"**Generated:** {stats['generated_at']}  ",
        f"**Samples:** {stats['num_samples']:,} ({stats['splits']['train']}/{stats['splits']['val']}/{stats['splits']['test']} train/val/test)",
        "",
        "## Sample diversity",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Unique gate mixtures | {g['sample_diversity']['unique_gate_mixtures']} |",
        f"| Mixture coverage (unique / samples) | {g['sample_diversity']['mixture_coverage']:.1%} |",
        f"| Gates per diagram (mean ± std) | {g['graph_size']['nodes_per_graph']['mean']} ± {g['graph_size']['nodes_per_graph']['std']} |",
        f"| Gates per diagram (median [Q1, Q3]) | {g['graph_size']['nodes_per_graph']['median']} [{g['graph_size']['nodes_per_graph']['q1']}, {g['graph_size']['nodes_per_graph']['q3']}] |",
        f"| Gates per diagram (range) | {g['graph_size']['nodes_per_graph']['min']}-{g['graph_size']['nodes_per_graph']['max']} |",
        f"| Diagrams with no edges | {g['sample_diversity']['graphs_with_no_edges']} |",
        "",
        "### Node-count histogram",
        "",
        "| Bin (gates) | Count |",
        "|-------------|------:|",
    ]
    for label, count in g["graph_size"]["node_count_histogram"].items():
        lines.append(f"| {label} | {count} |")

    lines += [
        "",
        "## Topology distribution",
        "",
        "### Gate-type frequencies (global)",
        "",
        "| Gate | Count | Share |",
        "|------|------:|------:|",
    ]
    for gate in GATE_VOCAB:
        freq = g["topology"]["gate_type_frequencies"][gate]
        lines.append(f"| {gate} | {freq['count']:,} | {freq['proportion']:.1%} |")

    lines += [
        "",
        "### Edge-count summary",
        "",
        "| Statistic | Value |",
        "|-----------|------:|",
        f"| Total directed edges | {g['totals']['edges']:,} |",
        f"| Edges per diagram (mean ± std) | {g['graph_size']['edges_per_graph']['mean']} ± {g['graph_size']['edges_per_graph']['std']} |",
        f"| Edges per diagram (median) | {g['graph_size']['edges_per_graph']['median']} |",
        f"| Edges per diagram (range) | {g['graph_size']['edges_per_graph']['min']}-{g['graph_size']['edges_per_graph']['max']} |",
        f"| Mean directed density | {g['topology']['avg_directed_density']:.4f} |",
        "",
        "### Edge-count histogram",
        "",
        "| Bin (edges) | Count |",
        "|-------------|------:|",
    ]
    for label, count in g["graph_size"]["edge_count_histogram"].items():
        lines.append(f"| {label} | {count} |")

    lines += [
        "",
        "### Split-stratified summary",
        "",
        "| Split | *n* | Unique mixtures | Gates (mean) | Edges (mean) | Density |",
        "|-------|----:|----------------:|-------------:|-------------:|--------:|",
    ]
    for split in SPLITS:
        s = splits[split]
        lines.append(
            f"| {split.capitalize()} | {s['num_samples']} | "
            f"{s['sample_diversity']['unique_gate_mixtures']} | "
            f"{s['graph_size']['nodes_per_graph']['mean']} | "
            f"{s['graph_size']['edges_per_graph']['mean']} | "
            f"{s['topology']['avg_directed_density']:.4f} |"
        )

    lines += [
        "",
        "## Paper-ready summary",
        "",
        ps["data_availability_paragraph"],
        "",
        "---",
        "",
        "*Auto-generated by `scripts/generate_statistics.py`. Machine-readable source: [`statistics.json`](statistics.json).*",
        "",
    ]
    return "\n".join(lines)


def build_paper_summary(global_stats: dict) -> dict:
    sd = global_stats["sample_diversity"]
    nodes = global_stats["graph_size"]["nodes_per_graph"]
    edges = global_stats["graph_size"]["edges_per_graph"]
    mixtures = sd["unique_gate_mixtures"]
    n = global_stats["num_samples"]

    paragraph = (
        f"The corpus comprises {n:,} annotated diagrams with {global_stats['totals']['gates']:,} gates and "
        f"{global_stats['totals']['edges']:,} directed edges. Sample diversity spans {mixtures} unique gate "
        f"mixtures ({sd['mixture_coverage']:.1%} coverage). Diagrams contain {nodes['min']}-{nodes['max']} gates "
        f"(mean {nodes['mean']}, median {nodes['median']}) and {edges['min']}-{edges['max']} edges "
        f"(mean {edges['mean']}, median {edges['median']}). Gate-type and topology statistics are stratified "
        f"by the official 700/100/200 train/validation/test split in `metadata/statistics.json`."
    )

    return {
        "unique_gate_mixtures": mixtures,
        "gates_per_diagram": {
            "range": [nodes["min"], nodes["max"]],
            "mean": nodes["mean"],
            "median": nodes["median"],
            "std": nodes["std"],
        },
        "edges_per_diagram": {
            "range": [edges["min"], edges["max"]],
            "mean": edges["mean"],
            "median": edges["median"],
            "std": edges["std"],
        },
        "total_gates": global_stats["totals"]["gates"],
        "total_edges": global_stats["totals"]["edges"],
        "mean_directed_density": global_stats["topology"]["avg_directed_density"],
        "data_availability_paragraph": paragraph,
    }


def main() -> None:
    all_ids = sorted(p.stem for p in ANNOTATIONS.glob("lb1k_*.json"))
    split_ids = {name: load_ids(name) for name in SPLITS}
    global_stats = analyze(all_ids)

    stats = {
        "schema_version": "1.1",
        "dataset": "LogicBench-1K",
        "version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "release": "camera-ready",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_by": "scripts/generate_statistics.py",
        "num_samples": len(all_ids),
        "num_images": len(list((ROOT / "images").glob("lb1k_*.jpg"))),
        "image_format": "JPEG",
        "image_resolution": [512, 512],
        "splits": {name: len(split_ids[name]) for name in SPLITS},
        "gate_vocabulary": GATE_VOCAB,
        "definitions": {
            "gate_mixture": "Sorted multiset of gate types present in one diagram; unique mixtures measure combinatorial diversity.",
            "directed_density": "edges / (nodes * (nodes - 1)) for n > 1; proportion of possible directed pairs that are annotated edges.",
            "terminal_degree": "Per-gate in-degree (incoming edges) and out-degree (outgoing edges) aggregated across all diagrams.",
        },
        "sample_diversity": global_stats["sample_diversity"] | {
            "graph_size": global_stats["graph_size"],
        },
        "topology_distribution": {
            "global": global_stats,
            "by_split": {name: analyze(split_ids[name]) for name in SPLITS},
        },
        "paper_summary": build_paper_summary(global_stats),
    }

    OUT_JSON.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(stats), encoding="utf-8")
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")


if __name__ == "__main__":
    main()
