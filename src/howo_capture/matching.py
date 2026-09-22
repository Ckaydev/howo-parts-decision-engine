from __future__ import annotations

from difflib import SequenceMatcher

from .models import (
    ExtractionResult,
    MatchCandidate,
    MatchDecision,
    ProductRecord,
)
from .normalization import normalize_name, normalize_part_number


def _name_score(left: str, right: str) -> float:
    left_norm = normalize_name(left)
    right_norm = normalize_name(right)
    if not left_norm or not right_norm:
        return 0.0
    sequence = SequenceMatcher(None, left_norm, right_norm).ratio()
    left_tokens = set(left_norm.split())
    right_tokens = set(right_norm.split())
    union = left_tokens | right_tokens
    token_score = len(left_tokens & right_tokens) / len(union) if union else 0.0
    return 0.7 * sequence + 0.3 * token_score


def _product_numbers(product: ProductRecord) -> set[str]:
    raw = [product.primary_part_number, *product.additional_part_numbers]
    return {normalized for item in raw if (normalized := normalize_part_number(item))}


def match_product(
    extraction: ExtractionResult, products: list[ProductRecord]
) -> MatchDecision:
    reference = extraction.product_reference
    supplied_numbers = {
        normalized
        for value in reference.mentioned_part_numbers
        if (normalized := normalize_part_number(value))
    }

    if supplied_numbers:
        number_matches = [
            product
            for product in products
            if supplied_numbers & _product_numbers(product)
        ]
        if len(number_matches) == 1:
            product = number_matches[0]
            if product.identity_status != "confirmed":
                return MatchDecision(
                    status="review_required",
                    confidence=0.85,
                    reason="part_number_matches_provisional_product",
                    candidates=(
                        MatchCandidate(
                            product.product_id,
                            product.canonical_name,
                            1.0,
                            "exact_part_number_provisional_product",
                        ),
                    ),
                    questions_needed=(
                        "Confirm this product record before accepting the part-number match.",
                    ),
                )
            return MatchDecision(
                status="matched",
                confidence=1.0,
                reason="exact_part_number",
                product_id=product.product_id,
                candidates=(
                    MatchCandidate(
                        product.product_id,
                        product.canonical_name,
                        1.0,
                        "exact_part_number",
                    ),
                ),
            )
        if len(number_matches) > 1:
            return MatchDecision(
                status="review_required",
                confidence=0.0,
                reason="part_number_matches_multiple_products",
                candidates=tuple(
                    MatchCandidate(
                        product.product_id,
                        product.canonical_name,
                        1.0,
                        "exact_part_number",
                    )
                    for product in number_matches
                ),
                questions_needed=("Which product record is the correct identity?",),
            )

    mentioned_name = reference.mentioned_name
    if not mentioned_name:
        return MatchDecision(
            status="review_required",
            confidence=0.0,
            reason="missing_product_identity",
            questions_needed=(
                "What is the product name or confirmed part number?",
            ),
        )

    normalized_mentioned_name = normalize_name(mentioned_name)
    exact_candidates: list[tuple[ProductRecord, str]] = []
    for product in products:
        if normalized_mentioned_name == normalize_name(product.canonical_name):
            exact_candidates.append((product, "exact_canonical_name"))
        elif normalized_mentioned_name in {
            normalize_name(alias) for alias in product.aliases
        }:
            exact_candidates.append((product, "exact_alias"))

    if len(exact_candidates) == 1 and not supplied_numbers:
        product, reason = exact_candidates[0]
        confidence = 0.95 if reason == "exact_canonical_name" else 0.9
        if product.identity_status != "confirmed":
            return MatchDecision(
                status="review_required",
                confidence=confidence,
                reason="name_matches_provisional_product",
                candidates=(
                    MatchCandidate(
                        product.product_id, product.canonical_name, confidence, reason
                    ),
                ),
                questions_needed=("Confirm this provisional product identity.",),
            )
        return MatchDecision(
            status="matched",
            confidence=confidence,
            reason=reason,
            product_id=product.product_id,
            candidates=(
                MatchCandidate(
                    product.product_id, product.canonical_name, confidence, reason
                ),
            ),
        )

    if exact_candidates:
        reason = (
            "unrecognized_part_number_for_known_name"
            if supplied_numbers and len(exact_candidates) == 1
            else "name_matches_multiple_products"
        )
        return MatchDecision(
            status="review_required",
            confidence=0.75,
            reason=reason,
            candidates=tuple(
                MatchCandidate(
                    product.product_id,
                    product.canonical_name,
                    0.95 if match_reason == "exact_canonical_name" else 0.9,
                    match_reason,
                )
                for product, match_reason in exact_candidates
            ),
            questions_needed=(
                "Confirm whether the supplied part number belongs to this product.",
            )
            if supplied_numbers
            else ("Which product record is the intended one?",),
        )

    ranked: list[MatchCandidate] = []
    for product in products:
        scores = [(_name_score(mentioned_name, product.canonical_name), "canonical_name")]
        scores.extend((_name_score(mentioned_name, alias), "alias") for alias in product.aliases)
        best_score, source = max(scores, key=lambda pair: pair[0])
        if best_score >= 0.55:
            ranked.append(
                MatchCandidate(
                    product.product_id,
                    product.canonical_name,
                    best_score,
                    f"fuzzy_{source}",
                )
            )
    ranked.sort(key=lambda candidate: candidate.score, reverse=True)
    ranked = ranked[:3]

    if ranked:
        questions = ["Confirm the intended product from the suggested matches."]
        if supplied_numbers:
            questions.append("Confirm the unrecognized part number from a label or photo.")
        return MatchDecision(
            status="review_required",
            confidence=ranked[0].score,
            reason="fuzzy_name_match",
            candidates=tuple(ranked),
            questions_needed=tuple(questions),
        )

    return MatchDecision(
        status="new_product_candidate",
        confidence=0.0,
        reason="no_existing_product_match",
        questions_needed=(
            "Confirm the product name and provide a part number or identifying photo if available.",
        ),
    )
