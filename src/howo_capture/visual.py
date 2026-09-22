from __future__ import annotations

import json
from typing import Any, Mapping

from .models import ValidationError
from .normalization import stable_id


IMAGE_QUALITIES = {"insufficient", "limited", "usable", "clear"}
VIEW_TYPES = {"full_item", "label", "connector", "mounting_points", "packaging", "unknown"}
FEATURE_TYPES = {
    "shape",
    "mounting",
    "connector",
    "dimension",
    "material",
    "color",
    "marking",
    "fitment",
}


def _required_text(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{key} must be a non-empty string")
    return value.strip()


def _confidence(data: Mapping[str, Any], key: str = "confidence") -> float:
    value = data.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValidationError(f"{key} must be a number")
    confidence = float(value)
    if not 0 <= confidence <= 1:
        raise ValidationError(f"{key} must be between 0 and 1")
    return confidence


def _object_list(data: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise ValidationError(f"{key} must be an array of objects")
    return value


def _feature_term(feature: Mapping[str, Any]) -> str:
    name = _required_text(feature, "feature_name")
    value = _required_text(feature, "feature_value")
    units = feature.get("units")
    if units is not None and (not isinstance(units, str) or not units.strip()):
        raise ValidationError("units must be a non-empty string or null")
    suffix = f" {units.strip()}" if isinstance(units, str) else ""
    return f"{name}: {value}{suffix}"


def process_visual_evidence(payload: Mapping[str, Any]) -> dict[str, Any]:
    capture_id = _required_text(payload, "capture_id")
    attachment_id = _required_text(payload, "attachment_id")
    captured_at = _required_text(payload, "captured_at")
    extraction = payload.get("visual_extraction")
    if not isinstance(extraction, Mapping):
        raise ValidationError("visual_extraction must be an object")

    summary = _required_text(extraction, "summary")
    image_quality = extraction.get("image_quality")
    if image_quality not in IMAGE_QUALITIES:
        raise ValidationError(
            "image_quality must be one of " + ", ".join(sorted(IMAGE_QUALITIES))
        )
    view_type = extraction.get("view_type")
    if view_type not in VIEW_TYPES:
        raise ValidationError("view_type must be one of " + ", ".join(sorted(VIEW_TYPES)))

    observed_numbers = _object_list(extraction, "observed_part_numbers")
    label_texts = _object_list(extraction, "label_texts")
    visual_features = _object_list(extraction, "visual_features")
    fitment_terms = _object_list(extraction, "fitment_terms")
    questions = extraction.get("questions_needed", [])
    if not isinstance(questions, list) or not all(
        isinstance(item, str) and item.strip() for item in questions
    ):
        raise ValidationError("questions_needed must be an array of non-empty strings")

    number_values: list[str] = []
    label_values: list[str] = []
    fitment_values: list[str] = []
    confidences: list[float] = []

    for item in observed_numbers:
        number_values.append(_required_text(item, "raw_text"))
        confidences.append(_confidence(item))
    for item in label_texts:
        label_values.append(_required_text(item, "raw_text"))
        confidences.append(_confidence(item))
    for item in fitment_terms:
        fitment_values.append(_required_text(item, "term"))
        confidences.append(_confidence(item))

    image_evidence_id = stable_id("img", capture_id, attachment_id)
    feature_rows: list[dict[str, Any]] = []
    feature_values: list[str] = []
    for index, feature in enumerate(visual_features):
        feature_type = feature.get("feature_type")
        if feature_type not in FEATURE_TYPES:
            raise ValidationError(
                "feature_type must be one of " + ", ".join(sorted(FEATURE_TYPES))
            )
        term = _feature_term(feature)
        feature_values.append(term)
        confidence = _confidence(feature)
        confidences.append(confidence)
        feature_rows.append(
            {
                "feature_id": stable_id("feat", image_evidence_id, index, term),
                "image_evidence_id": image_evidence_id,
                "product_id": "",
                "variant_id": "",
                "feature_type": feature_type,
                "feature_name": feature["feature_name"].strip(),
                "feature_value": feature["feature_value"].strip(),
                "units": feature.get("units") or "",
                "evidence_class": "inferred",
                "confidence": confidence,
                "observation_id": "",
            }
        )

    if image_quality == "insufficient" and not questions:
        questions = ["Send a clearer full-item and label photograph."]

    overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    image_row = {
        "image_evidence_id": image_evidence_id,
        "attachment_id": attachment_id,
        "capture_id": capture_id,
        "product_id": "",
        "variant_id": "",
        "view_type": view_type,
        "visible_label_text": " | ".join(label_values),
        "ocr_text": json.dumps(
            {
                "observed_part_numbers": observed_numbers,
                "label_texts": label_texts,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        "evidence_class": "inferred",
        "confidence": round(overall_confidence, 4),
        "review_status": "unreviewed",
        "observed_at": captured_at,
        "observation_id": "",
    }

    return {
        "schema_version": "1.0",
        "summary": summary,
        "image_quality": image_quality,
        "identification_query": {
            "mentioned_name": None,
            "confirmed_part_numbers": [],
            "observed_part_numbers": number_values,
            "label_texts": label_values,
            "visual_features": feature_values,
            "fitment_terms": fitment_values,
        },
        "rows": {
            "image_evidence": [image_row],
            "visual_features": feature_rows,
        },
        "questions_needed": [item.strip() for item in questions],
    }
