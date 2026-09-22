from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Iterable, Mapping

from .models import ProductRecord, ValidationError


TRUSTED_NUMBER_STATUSES = {"confirmed", "accepted", "verified"}


def _rows(payload: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = payload.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise ValidationError(f"{key} must be an array of objects")
    return value


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _terms(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_text(item) for item in value if _text(item)]
    if not isinstance(value, str):
        return []
    return [item.strip() for item in value.split("|") if item.strip()]


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = _text(value)
        folded = cleaned.casefold()
        if cleaned and folded not in seen:
            seen.add(folded)
            result.append(cleaned)
    return result


def build_catalogue_context(payload: Mapping[str, Any]) -> dict[str, Any]:
    product_rows = _rows(payload, "products")
    number_rows = _rows(payload, "part_numbers")
    image_rows = _rows(payload, "image_evidence")
    feature_rows = _rows(payload, "visual_features")

    products: dict[str, ProductRecord] = {}
    issues: list[dict[str, str]] = []
    for row in product_rows:
        if _text(row.get("identity_status")).lower() == "rejected":
            continue
        try:
            product = ProductRecord.from_mapping(row)
        except ValidationError as exc:
            issues.append({"table": "Products", "id": _text(row.get("product_id")), "reason": str(exc)})
            continue
        if product.product_id in products:
            issues.append({"table": "Products", "id": product.product_id, "reason": "duplicate_product_id"})
            continue
        products[product.product_id] = product

    accepted_numbers: dict[str, list[str]] = defaultdict(list)
    for row in number_rows:
        row_id = _text(row.get("part_number_id"))
        product_id = _text(row.get("product_id"))
        status = _text(row.get("status")).lower()
        raw_number = _text(row.get("raw_part_number"))
        if status not in TRUSTED_NUMBER_STATUSES:
            continue
        if product_id not in products:
            issues.append({"table": "Part_Numbers", "id": row_id, "reason": "unknown_product_id"})
            continue
        if not raw_number:
            issues.append({"table": "Part_Numbers", "id": row_id, "reason": "missing_raw_part_number"})
            continue
        accepted_numbers[product_id].append(raw_number)

    accepted_images: dict[str, Mapping[str, Any]] = {}
    for row in image_rows:
        image_id = _text(row.get("image_evidence_id"))
        product_id = _text(row.get("product_id"))
        if _text(row.get("review_status")).lower() != "accepted":
            continue
        if product_id not in products:
            issues.append({"table": "Image_Evidence", "id": image_id, "reason": "unknown_product_id"})
            continue
        if not image_id:
            issues.append({"table": "Image_Evidence", "id": "", "reason": "missing_image_evidence_id"})
            continue
        accepted_images[image_id] = row

    labels: dict[str, list[str]] = defaultdict(list)
    visual_terms: dict[str, list[str]] = defaultdict(list)
    fitment_terms: dict[str, list[str]] = defaultdict(list)
    observation_ids: dict[str, list[str]] = defaultdict(list)
    for row in accepted_images.values():
        product_id = _text(row.get("product_id"))
        labels[product_id].extend(_terms(row.get("visible_label_text")))
        observation_ids[product_id].extend(_terms(row.get("observation_id")))

    for row in feature_rows:
        feature_id = _text(row.get("feature_id"))
        image_id = _text(row.get("image_evidence_id"))
        accepted_image = accepted_images.get(image_id)
        if accepted_image is None:
            continue
        product_id = _text(row.get("product_id")) or _text(accepted_image.get("product_id"))
        if product_id != _text(accepted_image.get("product_id")):
            issues.append({"table": "Visual_Features", "id": feature_id, "reason": "product_id_conflicts_with_image"})
            continue
        name = _text(row.get("feature_name"))
        value = _text(row.get("feature_value"))
        units = _text(row.get("units"))
        if not name or not value:
            issues.append({"table": "Visual_Features", "id": feature_id, "reason": "missing_feature_name_or_value"})
            continue
        term = f"{name}: {value}{f' {units}' if units else ''}"
        if _text(row.get("feature_type")).lower() == "fitment":
            fitment_terms[product_id].append(term)
        else:
            visual_terms[product_id].append(term)
        observation_ids[product_id].extend(_terms(row.get("observation_id")))

    context_products: list[dict[str, Any]] = []
    profiles: list[dict[str, Any]] = []
    for product_id in sorted(products):
        product = products[product_id]
        context_products.append(
            {
                "product_id": product.product_id,
                "canonical_name": product.canonical_name,
                "primary_part_number": product.primary_part_number,
                "aliases": list(product.aliases),
                "additional_part_numbers": _unique(
                    [*product.additional_part_numbers, *accepted_numbers[product_id]]
                ),
                "identity_status": product.identity_status,
            }
        )
        if labels[product_id] or visual_terms[product_id] or fitment_terms[product_id]:
            profiles.append(
                {
                    "product_id": product_id,
                    "label_terms": _unique(labels[product_id]),
                    "visual_features": _unique(visual_terms[product_id]),
                    "fitment_terms": _unique(fitment_terms[product_id]),
                    "observation_ids": _unique(observation_ids[product_id]),
                }
            )

    return {
        "schema_version": "1.0",
        "products": context_products,
        "evidence_profiles": profiles,
        "diagnostics": {
            "input_products": len(product_rows),
            "usable_products": len(context_products),
            "trusted_part_numbers": sum(len(values) for values in accepted_numbers.values()),
            "accepted_images": len(accepted_images),
            "profiled_products": len(profiles),
            "issues": issues,
        },
    }
