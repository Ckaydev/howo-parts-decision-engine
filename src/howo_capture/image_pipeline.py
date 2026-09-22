from __future__ import annotations

import json
from typing import Any, Mapping

from .identification import identify_from_payload
from .models import ValidationError
from .normalization import stable_id
from .visual import process_visual_evidence


def _string_values(value: Any, key: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ValidationError(f"{key} must be an array of non-empty strings")
    return [item.strip() for item in value]


def process_image_identification(payload: Mapping[str, Any]) -> dict[str, Any]:
    visual_result = process_visual_evidence(payload)
    text_reference = payload.get("text_reference", {})
    if not isinstance(text_reference, Mapping):
        raise ValidationError("text_reference must be an object")

    mentioned_name = text_reference.get("mentioned_name")
    if mentioned_name is not None and (
        not isinstance(mentioned_name, str) or not mentioned_name.strip()
    ):
        raise ValidationError("text_reference.mentioned_name must be a non-empty string or null")
    confirmed_numbers = _string_values(
        text_reference.get("confirmed_part_numbers"),
        "text_reference.confirmed_part_numbers",
    )

    query = dict(visual_result["identification_query"])
    query["mentioned_name"] = mentioned_name.strip() if isinstance(mentioned_name, str) else None
    query["confirmed_part_numbers"] = confirmed_numbers
    decision = identify_from_payload(
        {
            "query": query,
            "products": payload.get("products", []),
            "evidence_profiles": payload.get("evidence_profiles", []),
        }
    )

    image_rows = visual_result["rows"]["image_evidence"]
    feature_rows = visual_result["rows"]["visual_features"]
    if decision["status"] == "matched" and decision.get("product_id"):
        for row in (*image_rows, *feature_rows):
            row["product_id"] = decision["product_id"]

    questions: list[str] = []
    for question in [
        *visual_result.get("questions_needed", []),
        *decision.get("questions_needed", []),
    ]:
        if question not in questions:
            questions.append(question)

    review_rows: list[dict[str, Any]] = []
    if decision["status"] != "matched":
        candidates = decision.get("candidates", [])
        review_rows.append(
            {
                "review_id": stable_id(
                    "rev", str(payload.get("capture_id", "")), "image_identification"
                ),
                "capture_id": payload.get("capture_id"),
                "proposed_product_id": candidates[0]["product_id"] if candidates else "",
                "candidate_matches": json.dumps(
                    candidates, ensure_ascii=False, sort_keys=True
                ),
                "reason": decision["reason"],
                "questions_needed": json.dumps(questions, ensure_ascii=False),
                "status": "open",
                "reviewed_at": "",
            }
        )

    return {
        "schema_version": "1.0",
        "capture_id": payload.get("capture_id"),
        "visual_summary": visual_result["summary"],
        "image_quality": visual_result["image_quality"],
        "identification_query": query,
        "match": decision,
        "rows": {
            "image_evidence": image_rows,
            "visual_features": feature_rows,
            "review_queue": review_rows,
        },
        "questions_needed": questions,
    }
