from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Mapping

from .models import ProductRecord, ValidationError
from .normalization import normalize_name, normalize_part_number, stable_id


ALLOWED_ACTIONS = {"link_existing", "create_provisional", "reject"}


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _required(value: Any, field: str) -> str:
    rendered = _text(value)
    if not rendered:
        raise ValidationError(f"{field} is required")
    return rendered


def _rows(payload: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = payload.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise ValidationError(f"{key} must be an array of objects")
    return value


def _string_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError(f"{field} must be an array of strings")
    result: list[str] = []
    for item in value:
        rendered = _required(item, field)
        if rendered not in result:
            result.append(rendered)
    return result


def _timestamp(value: Any, field: str) -> str:
    rendered = _required(value, field)
    candidate = rendered[:-1] + "+00:00" if rendered.endswith("Z") else rendered
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError(f"{field} must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValidationError(f"{field} must include a timezone")
    return rendered


def _confidence(value: Any) -> float:
    if isinstance(value, bool):
        raise ValidationError("decision.identity_confidence must be between 0 and 1")
    try:
        rendered = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            "decision.identity_confidence must be between 0 and 1"
        ) from exc
    if not 0 <= rendered <= 1:
        raise ValidationError("decision.identity_confidence must be between 0 and 1")
    return rendered


def _number_owners(
    products: list[ProductRecord], part_numbers: list[Mapping[str, Any]]
) -> dict[str, set[str]]:
    owners: dict[str, set[str]] = {}
    for product in products:
        numbers = [product.primary_part_number, *product.additional_part_numbers]
        for value in numbers:
            normalized = normalize_part_number(value)
            if normalized:
                owners.setdefault(normalized, set()).add(product.product_id)
    for row in part_numbers:
        if _text(row.get("status")).lower() == "rejected":
            continue
        normalized = normalize_part_number(
            _text(row.get("normalized_part_number"))
            or _text(row.get("raw_part_number"))
        )
        product_id = _text(row.get("product_id"))
        if normalized and product_id:
            owners.setdefault(normalized, set()).add(product_id)
    return owners


def resolve_review(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Turn an explicit human decision into replay-safe catalogue upserts."""
    decision = payload.get("decision")
    review_item = payload.get("review_item")
    if not isinstance(decision, Mapping):
        raise ValidationError("decision must be an object")
    if not isinstance(review_item, Mapping):
        raise ValidationError("review_item must be an object")

    review_id = _required(decision.get("review_id"), "decision.review_id")
    capture_id = _required(decision.get("capture_id"), "decision.capture_id")
    if review_id != _text(review_item.get("review_id")):
        raise ValidationError("decision.review_id does not match review_item")
    if capture_id != _text(review_item.get("capture_id")):
        raise ValidationError("decision.capture_id does not match review_item")
    if _text(review_item.get("status")).lower() != "open":
        raise ValidationError("review_item must have status open")

    action = _required(decision.get("action"), "decision.action").lower()
    if action not in ALLOWED_ACTIONS:
        raise ValidationError(
            "decision.action must be link_existing, create_provisional, or reject"
        )
    reviewer = _required(decision.get("reviewer"), "decision.reviewer")
    reviewed_at = _timestamp(decision.get("reviewed_at"), "decision.reviewed_at")
    notes = _text(decision.get("notes"))

    product_rows = _rows(payload, "products")
    part_number_rows = _rows(payload, "part_numbers")
    image_rows = _rows(payload, "image_evidence")
    products: dict[str, ProductRecord] = {}
    for row in product_rows:
        product = ProductRecord.from_mapping(row)
        if product.product_id in products:
            raise ValidationError(f"duplicate product_id: {product.product_id}")
        products[product.product_id] = product

    product_id = ""
    canonical_name = ""
    identity_confidence: float | None = None
    output_products: list[dict[str, Any]] = []
    if action == "link_existing":
        product_id = _required(decision.get("product_id"), "decision.product_id")
        product = products.get(product_id)
        if product is None or product.identity_status.lower() == "rejected":
            raise ValidationError("decision.product_id must identify a usable product")
        canonical_name = product.canonical_name
        identity_confidence = _confidence(decision.get("identity_confidence"))
    elif action == "create_provisional":
        canonical_name = _required(
            decision.get("canonical_name"), "decision.canonical_name"
        )
        if not normalize_name(canonical_name):
            raise ValidationError("decision.canonical_name is not usable")
        identity_confidence = _confidence(decision.get("identity_confidence"))
        product_id = _text(decision.get("product_id")) or stable_id(
            "prd", review_id, canonical_name
        )
        if product_id in products:
            raise ValidationError("new provisional product_id already exists")
        output_products.append(
            {
                "product_id": product_id,
                "canonical_name": canonical_name,
                "primary_part_number": "",
                "aliases": "",
                "additional_part_numbers": "",
                "category": _text(decision.get("category")),
                "system": _text(decision.get("system")),
                "summary": notes,
                "identity_status": "provisional",
                "identity_confidence": identity_confidence,
                "created_at": reviewed_at,
                "updated_at": reviewed_at,
            }
        )
    else:
        forbidden = (
            decision.get("product_id"),
            decision.get("canonical_name"),
            decision.get("confirmed_part_numbers"),
            decision.get("accept_image_evidence_ids"),
        )
        if any(forbidden):
            raise ValidationError("reject decisions cannot link or create trusted evidence")

    accepted_ids = _string_list(
        decision.get("accept_image_evidence_ids"),
        "decision.accept_image_evidence_ids",
    )
    rejected_ids = _string_list(
        decision.get("reject_image_evidence_ids"),
        "decision.reject_image_evidence_ids",
    )
    if set(accepted_ids) & set(rejected_ids):
        raise ValidationError("the same image evidence cannot be accepted and rejected")
    if action == "reject" and accepted_ids:
        raise ValidationError("reject decisions cannot accept image evidence")

    images_by_id = {
        _text(row.get("image_evidence_id")): row
        for row in image_rows
        if _text(row.get("image_evidence_id"))
    }
    output_images: list[dict[str, Any]] = []
    for image_id, review_status in [
        *((value, "accepted") for value in accepted_ids),
        *((value, "rejected") for value in rejected_ids),
    ]:
        row = images_by_id.get(image_id)
        if row is None:
            raise ValidationError(f"unknown image_evidence_id: {image_id}")
        if _text(row.get("capture_id")) != capture_id:
            raise ValidationError(
                f"image evidence {image_id} does not belong to this capture"
            )
        updated = dict(row)
        updated["review_status"] = review_status
        if review_status == "accepted":
            updated["product_id"] = product_id
        output_images.append(updated)

    confirmed_numbers = decision.get("confirmed_part_numbers", [])
    if not isinstance(confirmed_numbers, list) or not all(
        isinstance(item, Mapping) for item in confirmed_numbers
    ):
        raise ValidationError("decision.confirmed_part_numbers must be an array of objects")

    all_products = list(products.values())
    if output_products:
        all_products.append(ProductRecord.from_mapping(output_products[0]))
    owners = _number_owners(all_products, part_number_rows)
    existing_rows = {
        (
            _text(row.get("product_id")),
            normalize_part_number(
                _text(row.get("normalized_part_number"))
                or _text(row.get("raw_part_number"))
            ),
        ): row
        for row in part_number_rows
    }
    output_numbers: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    audited_numbers: list[str] = []
    for index, item in enumerate(confirmed_numbers):
        raw_number = _required(
            item.get("raw_part_number"),
            f"decision.confirmed_part_numbers[{index}].raw_part_number",
        )
        normalized = normalize_part_number(raw_number)
        if not normalized:
            raise ValidationError("confirmed part number is not usable")
        if item.get("verified_by_human") is not True:
            raise ValidationError("confirmed part numbers require verified_by_human=true")
        source_reference = _required(
            item.get("source_reference"),
            f"decision.confirmed_part_numbers[{index}].source_reference",
        )
        if owners.get(normalized, set()) - {product_id}:
            raise ValidationError(
                f"part number {raw_number} is already linked to another product"
            )
        observation_id = stable_id(
            "obs", review_id, "confirmed_part_number", normalized
        )
        prior = existing_rows.get((product_id, normalized), {})
        output_numbers.append(
            {
                "part_number_id": _text(prior.get("part_number_id"))
                or stable_id("pn", product_id, normalized),
                "product_id": product_id,
                "raw_part_number": raw_number,
                "normalized_part_number": normalized,
                "number_type": _text(item.get("number_type")) or "reviewed",
                "status": "confirmed",
                "confidence": 1.0,
                "observation_id": observation_id,
            }
        )
        observations.append(
            {
                "observation_id": observation_id,
                "capture_id": capture_id,
                "product_id": product_id,
                "variant_id": "",
                "claim_type": "part_number_verification",
                "claim_text": f"Human verified part number {raw_number}",
                "structured_value": json.dumps(
                    {
                        "raw_part_number": raw_number,
                        "normalized_part_number": normalized,
                        "source_reference": source_reference,
                        "reviewer": reviewer,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "evidence_class": "observed",
                "confidence": 1.0,
                "relationship": "new",
                "review_status": "accepted",
                "observed_at": reviewed_at,
            }
        )
        audited_numbers.append(raw_number)

    updated_review = dict(review_item)
    updated_review["status"] = "rejected" if action == "reject" else "resolved"
    updated_review["reviewed_at"] = reviewed_at
    decision_id = stable_id("rdec", review_id, action, product_id)
    audit_row = {
        "decision_id": decision_id,
        "review_id": review_id,
        "capture_id": capture_id,
        "action": action,
        "product_id": product_id,
        "canonical_name": canonical_name,
        "identity_confidence": identity_confidence if identity_confidence is not None else "",
        "accepted_image_evidence_ids": " | ".join(accepted_ids),
        "rejected_image_evidence_ids": " | ".join(rejected_ids),
        "confirmed_part_numbers": " | ".join(audited_numbers),
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "notes": notes,
    }
    return {
        "schema_version": "1.0",
        "decision": audit_row,
        "rows": {
            "review_queue": [updated_review],
            "review_decisions": [audit_row],
            "products": output_products,
            "part_numbers": output_numbers,
            "observations": observations,
            "image_evidence": output_images,
        },
        "safeguards": {
            "product_created_as_provisional": action == "create_provisional",
            "confirmed_part_numbers_require_human_verification": True,
            "accepted_images_linked_to_resolved_product": bool(accepted_ids),
        },
    }
