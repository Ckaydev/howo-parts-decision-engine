from __future__ import annotations

from dataclasses import replace
from typing import Any

from .models import CaptureEnvelope, ExtractionResult


def validate_extraction_evidence(
    capture: CaptureEnvelope, extraction: ExtractionResult
) -> tuple[ExtractionResult, tuple[dict[str, Any], ...]]:
    """Remove unsupported identity values and report material AI drift.

    This deliberately uses literal source-text checks. Fuzzy repair belongs in
    human review, not in the trusted capture path.
    """

    source_text = "\n".join(
        value for value in (capture.raw_text, capture.transcript) if value
    )
    source_casefold = source_text.casefold()
    issues: list[dict[str, Any]] = []

    reference = extraction.product_reference
    mentioned_name = reference.mentioned_name
    if mentioned_name and mentioned_name.casefold() not in source_casefold:
        issues.append(
            {
                "code": "unsupported_product_name",
                "value": mentioned_name,
                "message": "Product name was not stated in the source text",
            }
        )
        mentioned_name = None

    supported_numbers: list[str] = []
    for number in reference.mentioned_part_numbers:
        if number in source_text:
            supported_numbers.append(number)
        else:
            issues.append(
                {
                    "code": "unsupported_part_number",
                    "value": number,
                    "message": "Part number was not present exactly in the source text",
                }
            )

    claims = []
    for claim in extraction.claims:
        updated_claim = claim
        if claim.claim_type.casefold() == "part_number":
            value = claim.structured_value
            if value is None and len(supported_numbers) == 1:
                updated_claim = replace(claim, structured_value=supported_numbers[0])
            elif value is not None and (
                not isinstance(value, str) or value not in source_text
            ):
                issues.append(
                    {
                        "code": "unsupported_claim_part_number",
                        "value": value,
                        "message": "Part-number claim was not supported by the source text",
                    }
                )
                updated_claim = replace(
                    claim, structured_value=None, evidence_class="unresolved"
                )
        claims.append(updated_claim)

    validated = replace(
        extraction,
        product_reference=replace(
            reference,
            mentioned_name=mentioned_name,
            mentioned_part_numbers=tuple(supported_numbers),
        ),
        claims=tuple(claims),
    )
    return validated, tuple(issues)
