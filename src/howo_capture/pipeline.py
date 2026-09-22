from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Mapping

from .matching import match_product
from .models import (
    CaptureEnvelope,
    ExtractionResult,
    MatchDecision,
    ProductRecord,
    ValidationError,
)
from .normalization import normalize_part_number, stable_id
from .validation import validate_extraction_evidence


def _json_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def process_capture(payload: Mapping[str, Any]) -> dict[str, Any]:
    capture_data = payload.get("capture", {})
    extraction_data = payload.get("extraction", {})
    if not isinstance(capture_data, Mapping):
        raise ValidationError("capture must be an object")
    if not isinstance(extraction_data, Mapping):
        raise ValidationError("extraction must be an object")
    capture = CaptureEnvelope.from_mapping(capture_data)
    raw_extraction = ExtractionResult.from_mapping(extraction_data)
    extraction, validation_issues = validate_extraction_evidence(
        capture, raw_extraction
    )
    raw_products = payload.get("products", [])
    if not isinstance(raw_products, list):
        raise ValidationError("products must be an array")
    if not all(isinstance(product, Mapping) for product in raw_products):
        raise ValidationError("products must contain only objects")
    products = [ProductRecord.from_mapping(product) for product in raw_products]

    decision = match_product(extraction, products)
    if validation_issues:
        validation_questions = tuple(
            issue["message"] for issue in validation_issues
        )
        decision = MatchDecision(
            status="review_required",
            confidence=0.0,
            reason="extraction_evidence_failed",
            candidates=decision.candidates,
            questions_needed=validation_questions,
        )
    observation_rows: list[dict[str, Any]] = []
    if decision.status == "matched" and decision.product_id:
        for index, claim in enumerate(extraction.claims):
            observation_rows.append(
                {
                    "observation_id": stable_id(
                        "obs", capture.capture_id, index, claim.claim_text
                    ),
                    "capture_id": capture.capture_id,
                    "product_id": decision.product_id,
                    "variant_id": "",
                    "claim_type": claim.claim_type,
                    "claim_text": claim.claim_text,
                    "structured_value": _json_cell(claim.structured_value),
                    "evidence_class": claim.evidence_class,
                    "confidence": claim.confidence,
                    "relationship": "new",
                    "review_status": "unreviewed",
                    "observed_at": capture.captured_at,
                }
            )

    review_rows: list[dict[str, Any]] = []
    if decision.status != "matched":
        questions = list(decision.questions_needed)
        questions.extend(
            question
            for question in extraction.follow_up_questions
            if question not in questions
        )
        review_rows.append(
            {
                "review_id": stable_id("rev", capture.capture_id),
                "capture_id": capture.capture_id,
                "proposed_product_id": "",
                "candidate_matches": json.dumps(
                    [candidate.to_dict() for candidate in decision.candidates],
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "reason": decision.reason,
                "questions_needed": json.dumps(questions, ensure_ascii=False),
                "status": "open",
                "reviewed_at": "",
            }
        )

    part_number_rows: list[dict[str, Any]] = []
    if decision.status == "matched" and decision.product_id:
        for raw_number in extraction.product_reference.mentioned_part_numbers:
            normalized = normalize_part_number(raw_number)
            if not normalized:
                continue
            part_number_rows.append(
                {
                    "part_number_id": stable_id(
                        "pn", decision.product_id, normalized
                    ),
                    "product_id": decision.product_id,
                    "raw_part_number": raw_number,
                    "normalized_part_number": normalized,
                    "number_type": "captured",
                    "status": "unreviewed",
                    "confidence": decision.confidence,
                    "observation_id": observation_rows[0]["observation_id"]
                    if observation_rows
                    else "",
                }
            )

    capture_row = capture.to_dict()
    capture_row["processing_status"] = (
        "structured" if decision.status == "matched" else "needs_review"
    )

    return {
        "schema_version": "1.0",
        "capture": capture_row,
        "extraction_summary": extraction.summary,
        "extraction_validation": {
            "status": "needs_review" if validation_issues else "passed",
            "issues": list(validation_issues),
        },
        "match": decision.to_dict(),
        "rows": {
            "observations": observation_rows,
            "part_numbers": part_number_rows,
            "review_queue": review_rows,
        },
    }
