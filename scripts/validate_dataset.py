#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANNOTATIONS = ROOT / "annotations"
IMAGES = ROOT / "images"
SPLITS = ANNOTATIONS / "splits"
SCHEMA_PATH = ROOT / "schema" / "annotation.schema.json"

GATE_TYPES = {"AND", "OR", "NOT", "NAND", "NOR", "XOR", "XNOR"}
ID_RE = re.compile(r"^lb1k_\d{5}$")
GATE_ID_RE = re.compile(r"^gate_\d+$")
IMAGE_PATH_RE = re.compile(r"^images/lb1k_\d{5}\.jpg$")


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def validate() -> int:
    errors: list[str] = []

    ann_files = sorted(ANNOTATIONS.glob("lb1k_*.json"))
    img_files = sorted(IMAGES.glob("lb1k_*.jpg"))

    if len(ann_files) != 1000:
        errors.append(f"expected 1000 annotations, found {len(ann_files)}")
    if len(img_files) != 1000:
        errors.append(f"expected 1000 images, found {len(img_files)}")

    ann_ids = {p.stem for p in ann_files}
    img_ids = {p.stem for p in img_files}
    if ann_ids != img_ids:
        errors.append(
            f"annotation/image ID mismatch: "
            f"{len(ann_ids - img_ids)} ann-only, {len(img_ids - ann_ids)} img-only"
        )

    split_sets: dict[str, set[str]] = {}
    for split in ("train", "val", "test"):
        split_file = SPLITS / f"{split}.txt"
        if not split_file.exists():
            errors.append(f"missing split file: {split_file}")
            continue
        ids = [line.strip() for line in split_file.read_text().splitlines() if line.strip()]
        split_sets[split] = set(ids)
        if any(not ID_RE.match(i) for i in ids):
            errors.append(f"invalid sample ID format in {split}.txt")

    if split_sets:
        union = set().union(*split_sets.values())
        if union != ann_ids:
            errors.append("splits do not cover exactly all annotation IDs")
        for a, b in (("train", "val"), ("train", "test"), ("val", "test")):
            if a in split_sets and b in split_sets and split_sets[a] & split_sets[b]:
                errors.append(f"overlap between {a} and {b} splits")

    for ann_path in ann_files:
        sample_id = ann_path.stem
        data = load_json(ann_path)

        if not IMAGE_PATH_RE.match(data.get("image_path", "")):
            errors.append(f"{sample_id}: invalid image_path {data.get('image_path')!r}")
        elif data["image_path"] != f"images/{sample_id}.jpg":
            errors.append(f"{sample_id}: image_path does not match sample id")

        img_path = ROOT / data.get("image_path", "")
        if not img_path.is_file():
            errors.append(f"{sample_id}: missing image {img_path}")

        nodes = data.get("nodes")
        edges = data.get("edges")
        if not isinstance(nodes, list) or not nodes:
            errors.append(f"{sample_id}: nodes must be a non-empty list")
            continue
        if not isinstance(edges, list):
            errors.append(f"{sample_id}: edges must be a list")
            continue

        node_ids: list[str] = []
        for node in nodes:
            nid = node.get("id")
            ntype = node.get("type")
            if not GATE_ID_RE.match(nid or ""):
                errors.append(f"{sample_id}: bad node id {nid!r}")
            if ntype not in GATE_TYPES:
                errors.append(f"{sample_id}: bad gate type {ntype!r}")
            node_ids.append(nid)

        if len(node_ids) != len(set(node_ids)):
            errors.append(f"{sample_id}: duplicate node ids")

        node_id_set = set(node_ids)
        for edge in edges:
            src, tgt = edge.get("source"), edge.get("target")
            if src not in node_id_set or tgt not in node_id_set:
                errors.append(f"{sample_id}: edge ({src!r} -> {tgt!r}) references unknown node")

    if errors:
        print("VALIDATION FAILED")
        for err in errors[:50]:
            print(f"  - {err}")
        if len(errors) > 50:
            print(f"  ... and {len(errors) - 50} more")
        return 1

    print("VALIDATION PASSED")
    print(f"  samples: {len(ann_files)}")
    print(f"  splits: train={len(split_sets.get('train', []))} "
          f"val={len(split_sets.get('val', []))} test={len(split_sets.get('test', []))}")
    return 0


if __name__ == "__main__":
    sys.exit(validate())
