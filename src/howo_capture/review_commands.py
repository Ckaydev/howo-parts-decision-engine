from __future__ import annotations

import re
import shlex
from datetime import datetime, timezone
from typing import Any, Mapping

from .models import ValidationError
from .review import resolve_review


_REVIEW_ID_FROM_REPLY = re.compile(
    r"(?:^|\n)\s*Review ID:\s*([A-Za-z0-9_-]+)\s*(?:\n|$)",
    re.IGNORECASE,
)
_COMMAND_NAMES = {"/resolve", "/review"}
_ACTIONS = {"link", "new", "reject"}


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


def _reviewed_at(value: Any) -> str:
    rendered = _text(value)
    if not rendered:
        return datetime.now(timezone.utc).isoformat()
    candidate = rendered[:-1] + "+00:00" if rendered.endswith("Z") else rendered
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError("message.sent_at must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValidationError("message.sent_at must include a timezone")
    return rendered


def _parse_command(text: str, reply_text: str) -> dict[str, Any]:
    try:
        tokens = shlex.split(text)
    except ValueError as exc:
        raise ValidationError(f"review command has invalid quoting: {exc}") from exc
    if not tokens:
        raise ValidationError("message.text must contain a review command")

    first = tokens[0].lower().split("@", 1)[0]
    if first in _COMMAND_NAMES:
        if len(tokens) < 3:
            raise ValidationError(
                "use /resolve REVIEW_ID link PRODUCT_ID, new NAME, or reject"
            )
        review_id = tokens[1]
        action = tokens[2].lower()
        remainder = tokens[3:]
    else:
        match = _REVIEW_ID_FROM_REPLY.search(reply_text)
        if match is None:
            raise ValidationError(
                "reply to a review notification or include /resolve REVIEW_ID"
            )
        review_id = match.group(1)
        action = first
        remainder = tokens[1:]

    if action not in _ACTIONS:
        raise ValidationError("review action must be link, new, or reject")

    accept_images = False
    part_numbers: list[str] = []
    positional: list[str] = []
    for token in remainder:
        lowered = token.lower()
        if lowered == "--accept-image":
            accept_images = True
        elif lowered.startswith("--pn="):
            number = token.split("=", 1)[1].strip()
            if not number:
                raise ValidationError("--pn requires a part number")
            if number not in part_numbers:
                part_numbers.append(number)
        elif lowered.startswith("--"):
            raise ValidationError(f"unknown review option: {token}")
        else:
            positional.append(token)

    parsed: dict[str, Any] = {
        "review_id": review_id,
        "action": action,
        "accept_images": accept_images,
        "part_numbers": part_numbers,
    }
    if action == "link":
        if len(positional) != 1:
            raise ValidationError("link requires exactly one product_id")
        parsed["product_id"] = positional[0]
    elif action == "new":
        canonical_name = " ".join(positional).strip()
        if not canonical_name:
            raise ValidationError("new requires a product name")
        parsed["canonical_name"] = canonical_name
    elif positional or accept_images or part_numbers:
        raise ValidationError("reject does not accept product, image, or part-number options")
    return parsed


def resolve_review_command(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve a strict Telegram review command against current Sheet rows."""
    message = payload.get("message")
    if not isinstance(message, Mapping):
        raise ValidationError("message must be an object")

    text = _required(message.get("text"), "message.text")
    parsed = _parse_command(text, _text(message.get("reply_text")))
    sender_id = _required(message.get("sender_id"), "message.sender_id")
    chat_id = _required(message.get("chat_id"), "message.chat_id")
    message_id = _required(message.get("message_id"), "message.message_id")
    reviewed_at = _reviewed_at(message.get("sent_at"))

    review_rows = _rows(payload, "review_queue")
    matching_reviews = [
        row for row in review_rows if _text(row.get("review_id")) == parsed["review_id"]
    ]
    if len(matching_reviews) != 1:
        raise ValidationError("review_id must identify exactly one review row")
    review_item = matching_reviews[0]
    capture_id = _required(review_item.get("capture_id"), "review_item.capture_id")

    image_rows = _rows(payload, "image_evidence")
    capture_images = [
        row
        for row in image_rows
        if _text(row.get("capture_id")) == capture_id
        and _text(row.get("image_evidence_id"))
    ]
    image_ids = [_text(row.get("image_evidence_id")) for row in capture_images]

    source_reference = f"telegram:{chat_id}:{message_id}"
    action = parsed["action"]
    decision: dict[str, Any] = {
        "review_id": parsed["review_id"],
        "capture_id": capture_id,
        "reviewer": f"telegram:{sender_id}",
        "reviewed_at": reviewed_at,
        "notes": f"Telegram review command {source_reference}",
        "confirmed_part_numbers": [
            {
                "raw_part_number": number,
                "number_type": "reviewed",
                "verified_by_human": True,
                "source_reference": source_reference,
            }
            for number in parsed["part_numbers"]
        ],
    }
    if action == "link":
        decision.update(
            {
                "action": "link_existing",
                "product_id": parsed["product_id"],
                "identity_confidence": 1.0,
                "accept_image_evidence_ids": image_ids
                if parsed["accept_images"]
                else [],
                "reject_image_evidence_ids": [],
            }
        )
    elif action == "new":
        decision.update(
            {
                "action": "create_provisional",
                "canonical_name": parsed["canonical_name"],
                "identity_confidence": 0.6,
                "accept_image_evidence_ids": image_ids
                if parsed["accept_images"]
                else [],
                "reject_image_evidence_ids": [],
            }
        )
    else:
        decision.update(
            {
                "action": "reject",
                "accept_image_evidence_ids": [],
                "reject_image_evidence_ids": image_ids,
            }
        )

    result = resolve_review(
        {
            "decision": decision,
            "review_item": review_item,
            "products": _rows(payload, "products"),
            "part_numbers": _rows(payload, "part_numbers"),
            "image_evidence": image_rows,
        }
    )
    decision_row = result["decision"]
    if action == "reject":
        confirmation = (
            f"Review rejected\nReview ID: {parsed['review_id']}\n"
            f"Rejected images: {len(image_ids)}"
        )
    else:
        confirmation = (
            f"Review resolved\nReview ID: {parsed['review_id']}\n"
            f"Product: {decision_row['canonical_name']} ({decision_row['product_id']})\n"
            f"Images accepted: {len(decision['accept_image_evidence_ids'])}\n"
            f"Part numbers confirmed: {len(parsed['part_numbers'])}"
        )
    result["command"] = {
        "review_id": parsed["review_id"],
        "action": action,
        "source_reference": source_reference,
    }
    result["confirmation_text"] = confirmation
    return result
