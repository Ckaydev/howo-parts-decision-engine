from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from .models import ValidationError


AVAILABILITY_STATUSES = {
    "reported_available",
    "reported_low_stock",
    "reported_unavailable",
    "unknown",
}


def _parse_datetime(value: Any, key: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{key} must be a non-empty ISO 8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{key} must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValidationError(f"{key} must include a timezone")
    return parsed.astimezone(timezone.utc)


def rank_supplier_reports(payload: Mapping[str, Any]) -> dict[str, Any]:
    product_id = payload.get("product_id")
    if not isinstance(product_id, str) or not product_id.strip():
        raise ValidationError("product_id must be a non-empty string")
    as_of = _parse_datetime(payload.get("as_of"), "as_of")
    fresh_for_days = payload.get("fresh_for_days", 30)
    if not isinstance(fresh_for_days, int) or fresh_for_days < 1:
        raise ValidationError("fresh_for_days must be a positive integer")
    reports = payload.get("supplier_reports", [])
    if not isinstance(reports, list) or not all(
        isinstance(report, Mapping) for report in reports
    ):
        raise ValidationError("supplier_reports must be an array of objects")

    ranked: list[dict[str, Any]] = []
    for report in reports:
        if report.get("product_id") != product_id:
            continue
        status = report.get("availability_status")
        if status not in AVAILABILITY_STATUSES:
            raise ValidationError(
                "availability_status must be one of "
                + ", ".join(sorted(AVAILABILITY_STATUSES))
            )
        observed_at = _parse_datetime(report.get("observed_at"), "observed_at")
        age_days = (as_of - observed_at).total_seconds() / 86400
        if age_days < 0:
            freshness = "future_dated_invalid"
        elif age_days <= fresh_for_days:
            freshness = "recent_report"
        else:
            freshness = "stale_report"
        ranked.append(
            {
                "report_id": str(report.get("report_id", "")),
                "supplier_id": str(report.get("supplier_id", "")),
                "supplier_name": str(report.get("supplier_name", "")),
                "product_id": product_id,
                "availability_status": status,
                "observed_at": report.get("observed_at"),
                "age_days": round(age_days, 1),
                "freshness": freshness,
                "source_capture_id": str(report.get("source_capture_id", "")),
                "requires_reconfirmation": True,
            }
        )

    status_order = {
        "reported_available": 0,
        "reported_low_stock": 1,
        "unknown": 2,
        "reported_unavailable": 3,
    }
    freshness_order = {
        "recent_report": 0,
        "stale_report": 1,
        "future_dated_invalid": 2,
    }
    ranked.sort(
        key=lambda item: (
            freshness_order[item["freshness"]],
            status_order[item["availability_status"]],
            item["age_days"] if item["age_days"] >= 0 else float("inf"),
            item["supplier_id"],
        )
    )
    return {
        "product_id": product_id,
        "as_of": payload.get("as_of"),
        "fresh_for_days": fresh_for_days,
        "results": ranked,
        "notice": "Supplier reports are historical observations, not current-stock guarantees. Reconfirm before quoting or purchasing.",
    }
