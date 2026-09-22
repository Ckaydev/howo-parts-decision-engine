#!/usr/bin/env python3
"""Add deterministic decision-result persistence nodes to an n8n workflow export.

The script accepts either a single workflow object or n8n's one-item export list.
It preserves credentials present in a live export and leaves a repository export
credential-free.
"""

from __future__ import annotations

import argparse
import copy
import json
import uuid
from pathlib import Path
from typing import Any


ROUTE_NODE_NAMES = {
    "switch": "Switch Decision Route",
    "capture_inbox": "Persist Capture Decision",
    "observation": "Upsert Observation",
    "part_number": "Upsert Part Number",
    "review_queue": "Upsert Review Item",
    "image_evidence": "Upsert Image Evidence",
    "visual_feature": "Upsert Visual Feature",
    "fallback": "Reject Unknown Decision Route",
}

TEXT_CONTEXT_NAMES = {
    "Read Confirmed Part Numbers for Text",
    "Prepare Text Catalogue Context",
    "Build Text Catalogue Context",
}

SHEET_COLUMNS = {
    "capture_inbox": (
        "Capture_Inbox",
        "capture_id",
        (
            "capture_id",
            "channel",
            "channel_message_id",
            "captured_at",
            "ingested_at",
            "sender_id",
            "raw_text",
            "media_type",
            "media_original_ref",
            "media_archive_url",
            "transcript",
            "processing_status",
            "processing_error",
            "extraction_summary",
            "match_status",
            "matched_product_id",
            "match_confidence",
        ),
    ),
    "observation": (
        "Observations",
        "observation_id",
        (
            "observation_id",
            "capture_id",
            "product_id",
            "variant_id",
            "claim_type",
            "claim_text",
            "structured_value",
            "evidence_class",
            "confidence",
            "relationship",
            "review_status",
            "observed_at",
        ),
    ),
    "part_number": (
        "Part_Numbers",
        "part_number_id",
        (
            "part_number_id",
            "product_id",
            "raw_part_number",
            "normalized_part_number",
            "number_type",
            "status",
            "confidence",
            "observation_id",
        ),
    ),
    "review_queue": (
        "Review_Queue",
        "review_id",
        (
            "review_id",
            "capture_id",
            "proposed_product_id",
            "candidate_matches",
            "reason",
            "questions_needed",
            "status",
            "reviewed_at",
        ),
    ),
    "image_evidence": (
        "Image_Evidence",
        "image_evidence_id",
        (
            "image_evidence_id",
            "attachment_id",
            "capture_id",
            "product_id",
            "variant_id",
            "view_type",
            "visible_label_text",
            "ocr_text",
            "evidence_class",
            "confidence",
            "review_status",
            "observed_at",
            "observation_id",
        ),
    ),
    "visual_feature": (
        "Visual_Features",
        "feature_id",
        (
            "feature_id",
            "image_evidence_id",
            "product_id",
            "variant_id",
            "feature_type",
            "feature_name",
            "feature_value",
            "units",
            "evidence_class",
            "confidence",
            "observation_id",
        ),
    ),
}


def stable_node_id(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"howo-capture/n8n/{name}"))


def schema(columns: tuple[str, ...]) -> list[dict[str, Any]]:
    return [
        {
            "id": column,
            "displayName": column,
            "required": False,
            "defaultMatch": False,
            "display": True,
            "type": "string",
            "canBeUsedToMatch": True,
        }
        for column in columns
    ]


def sheet_node(
    route: str,
    *,
    base_node: dict[str, Any],
    position: list[int],
) -> dict[str, Any]:
    sheet_name, match_key, columns = SHEET_COLUMNS[route]
    document_id = copy.deepcopy(base_node["parameters"]["documentId"])
    node: dict[str, Any] = {
        "parameters": {
            "operation": "appendOrUpdate",
            "documentId": document_id,
            "sheetName": {"__rl": True, "value": sheet_name, "mode": "name"},
            "columns": {
                "mappingMode": "defineBelow",
                "value": {
                    column: f"={{{{ $json.row.{column} }}}}" for column in columns
                },
                "matchingColumns": [match_key],
                "schema": schema(columns),
                "attemptToConvertTypes": False,
                "convertFieldsToString": False,
            },
            "options": {
                "locationDefine": {
                    "values": {"headerRow": 3, "firstDataRow": 4}
                }
            },
        },
        "type": "n8n-nodes-base.googleSheets",
        "typeVersion": base_node.get("typeVersion", 4.7),
        "position": position,
        "id": stable_node_id(ROUTE_NODE_NAMES[route]),
        "name": ROUTE_NODE_NAMES[route],
    }
    if base_node.get("credentials"):
        node["credentials"] = copy.deepcopy(base_node["credentials"])
    return node


def switch_node() -> dict[str, Any]:
    rules = []
    for route in SHEET_COLUMNS:
        rules.append(
            {
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "leftValue": "",
                        "typeValidation": "strict",
                        "version": 2,
                    },
                    "conditions": [
                        {
                            "id": stable_node_id(f"route-condition/{route}"),
                            "leftValue": "={{ $json.route }}",
                            "rightValue": route,
                            "operator": {"type": "string", "operation": "equals"},
                        }
                    ],
                    "combinator": "and",
                },
                "renameOutput": True,
                "outputKey": route,
            }
        )
    return {
        "parameters": {
            "mode": "rules",
            "rules": {"values": rules},
            "options": {
                "fallbackOutput": "extra",
                "renameFallbackOutput": "unknown_route",
            },
        },
        "type": "n8n-nodes-base.switch",
        "typeVersion": 3.3,
        "position": [4960, -384],
        "id": stable_node_id(ROUTE_NODE_NAMES["switch"]),
        "name": ROUTE_NODE_NAMES["switch"],
    }


def fallback_node() -> dict[str, Any]:
    return {
        "parameters": {
            "jsCode": (
                "const route = String($json.route || 'missing');\n"
                "throw new Error(`Unsupported decision route: ${route}`);"
            )
        },
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [5200, 336],
        "id": stable_node_id(ROUTE_NODE_NAMES["fallback"]),
        "name": ROUTE_NODE_NAMES["fallback"],
    }


def extend(workflow: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(workflow)
    nodes = result.get("nodes")
    if not isinstance(nodes, list):
        raise ValueError("workflow must contain a nodes array")
    by_name = {node.get("name"): node for node in nodes}
    try:
        base_sheet = by_name["Upsert Raw Capture"]
        route_node = by_name["Route Decision Result"]
    except KeyError as exc:
        raise ValueError(f"required workflow node is missing: {exc.args[0]}") from exc

    # The catalogue read and all persistence writes must use the same working
    # Sheets connection. A stale second OAuth credential previously allowed raw
    # capture to succeed but made matching fail at `Read Products`.
    read_products = by_name.get("Read Products")
    if read_products is not None and base_sheet.get("credentials"):
        read_products["credentials"] = copy.deepcopy(base_sheet["credentials"])

    try:
        read_products = by_name["Read Products"]
        decision_engine = by_name["Run Decision Engine"]
    except KeyError as exc:
        raise ValueError(f"required workflow node is missing: {exc.args[0]}") from exc

    read_part_numbers = copy.deepcopy(read_products)
    read_part_numbers.update(
        {
            "position": [4288, -640],
            "id": stable_node_id("Read Confirmed Part Numbers for Text"),
            "name": "Read Confirmed Part Numbers for Text",
            "alwaysOutputData": True,
        }
    )
    read_part_numbers["parameters"]["sheetName"] = {
        "__rl": True,
        "value": "Part_Numbers",
        "mode": "name",
    }
    if base_sheet.get("credentials"):
        read_part_numbers["credentials"] = copy.deepcopy(base_sheet["credentials"])

    prepare_context = {
        "parameters": {
            "jsCode": "// Synced from workflows/code for Prepare Text Catalogue Context"
        },
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [4512, -640],
        "id": stable_node_id("Prepare Text Catalogue Context"),
        "name": "Prepare Text Catalogue Context",
    }
    build_context = copy.deepcopy(decision_engine)
    build_context.update(
        {
            "position": [4736, -640],
            "id": stable_node_id("Build Text Catalogue Context"),
            "name": "Build Text Catalogue Context",
        }
    )
    build_context["parameters"]["url"] = (
        "http://howo-capture:8765/v1/catalogue-context"
    )

    managed_names = set(ROUTE_NODE_NAMES.values()) | TEXT_CONTEXT_NAMES
    result["nodes"] = [
        node for node in nodes if node.get("name") not in managed_names
    ]
    result["nodes"].extend(
        [
            switch_node(),
            sheet_node("capture_inbox", base_node=base_sheet, position=[5200, -720]),
            sheet_node("observation", base_node=base_sheet, position=[5200, -544]),
            sheet_node("part_number", base_node=base_sheet, position=[5200, -368]),
            sheet_node("review_queue", base_node=base_sheet, position=[5200, -192]),
            sheet_node("image_evidence", base_node=base_sheet, position=[5200, -16]),
            sheet_node("visual_feature", base_node=base_sheet, position=[5200, 160]),
            fallback_node(),
            read_part_numbers,
            prepare_context,
            build_context,
        ]
    )

    connections = copy.deepcopy(result.get("connections", {}))
    for name in managed_names:
        connections.pop(name, None)
    connections[route_node["name"]] = {
        "main": [
            [{"node": ROUTE_NODE_NAMES["switch"], "type": "main", "index": 0}]
        ]
    }
    connections[ROUTE_NODE_NAMES["switch"]] = {
        "main": [
            [
                {
                    "node": ROUTE_NODE_NAMES[route],
                    "type": "main",
                    "index": 0,
                }
            ]
            for route in SHEET_COLUMNS
        ]
        + [
            [
                {
                    "node": ROUTE_NODE_NAMES["fallback"],
                    "type": "main",
                    "index": 0,
                }
            ]
        ]
    }
    connections["Read Products"] = {
        "main": [
            [
                {
                    "node": "Read Confirmed Part Numbers for Text",
                    "type": "main",
                    "index": 0,
                }
            ]
        ]
    }
    connections["Read Confirmed Part Numbers for Text"] = {
        "main": [
            [
                {
                    "node": "Prepare Text Catalogue Context",
                    "type": "main",
                    "index": 0,
                }
            ]
        ]
    }
    connections["Prepare Text Catalogue Context"] = {
        "main": [
            [
                {
                    "node": "Build Text Catalogue Context",
                    "type": "main",
                    "index": 0,
                }
            ]
        ]
    }
    connections["Build Text Catalogue Context"] = {
        "main": [
            [
                {
                    "node": "Prepare Decision Request",
                    "type": "main",
                    "index": 0,
                }
            ]
        ]
    }
    result["connections"] = connections
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    raw = json.loads(args.input.read_text(encoding="utf-8"))
    is_list = isinstance(raw, list)
    if is_list:
        if len(raw) != 1 or not isinstance(raw[0], dict):
            raise ValueError("expected a one-workflow n8n export")
        workflow = raw[0]
    elif isinstance(raw, dict):
        workflow = raw
    else:
        raise ValueError("workflow export must be an object or one-item array")

    updated = extend(workflow)
    payload: Any = [updated] if is_list else updated
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
