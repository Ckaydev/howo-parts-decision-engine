#!/usr/bin/env python3
"""Sync versioned n8n Code-node sources into a workflow export."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


CODE_NODES = {
    "Normalize Telegram Capture": "normalize_telegram_capture.js",
    "Prepare Archived Capture": "prepare_archived_capture.js",
    "Validate Extraction Evidence": "validate_extraction_evidence.js",
    "Prepare Text Catalogue Context": "prepare_text_catalogue_context.js",
    "Prepare Decision Request": "prepare_decision_request.js",
    "Route Decision Result": "route_decision_result.js",
    "Validate Visual Extraction": "validate_visual_extraction.js",
    "Prepare Image Catalogue Context": "prepare_image_catalogue_context.js",
    "Prepare Image Decision Request": "prepare_image_decision_request.js",
    "Route Image Result": "route_image_result.js",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    raw = json.loads(args.input.read_text(encoding="utf-8"))
    workflow = raw[0] if isinstance(raw, list) else raw
    if not isinstance(workflow, dict):
        raise ValueError("workflow export must contain an object")

    nodes = {node.get("name"): node for node in workflow.get("nodes", [])}
    code_dir = Path(__file__).parents[1] / "workflows" / "code"
    for node_name, filename in CODE_NODES.items():
        if node_name not in nodes:
            raise ValueError(f"required Code node is missing: {node_name}")
        nodes[node_name]["parameters"]["jsCode"] = (code_dir / filename).read_text(
            encoding="utf-8"
        ).rstrip()

    args.output.write_text(
        json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
