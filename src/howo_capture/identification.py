from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Mapping

from .models import (
    IdentificationCandidate,
    IdentificationDecision,
    IdentificationQuery,
    ProductEvidenceProfile,
    ProductRecord,
    ValidationError,
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


def _normalized_set(values: tuple[str, ...]) -> set[str]:
    return {value for item in values if (value := normalize_name(item))}


def _coverage(observed: tuple[str, ...], expected: tuple[str, ...]) -> tuple[float, int, int]:
    observed_set = _normalized_set(observed)
    expected_set = _normalized_set(expected)
    if not observed_set or not expected_set:
        return 0.0, 0, len(observed_set)
    matched = len(observed_set & expected_set)
    return matched / len(observed_set), matched, len(observed_set)


def _product_numbers(product: ProductRecord) -> set[str]:
    raw = [product.primary_part_number, *product.additional_part_numbers]
    return {normalized for item in raw if (normalized := normalize_part_number(item))}


def identify_product(
    query: IdentificationQuery,
    products: list[ProductRecord],
    profiles: list[ProductEvidenceProfile],
) -> IdentificationDecision:
    profiles_by_product = {profile.product_id: profile for profile in profiles}
    confirmed_numbers = {
        number
        for item in query.confirmed_part_numbers
        if (number := normalize_part_number(item))
    }
    observed_numbers = {
        number
        for item in query.observed_part_numbers
        if (number := normalize_part_number(item))
    }
    number_matches = [
        product for product in products if confirmed_numbers & _product_numbers(product)
    ]
    if len(number_matches) == 1:
        product = number_matches[0]
        if product.identity_status != "confirmed":
            return IdentificationDecision(
                status="review_required",
                confidence=0.85,
                reason="part_number_matches_provisional_product",
                candidates=(
                    IdentificationCandidate(
                        product_id=product.product_id,
                        canonical_name=product.canonical_name,
                        score=1.0,
                        signals=("exact_part_number", "provisional_product"),
                        observation_ids=profiles_by_product.get(
                            product.product_id,
                            ProductEvidenceProfile(product.product_id),
                        ).observation_ids,
                    ),
                ),
                questions_needed=("Confirm this product record before accepting the part-number match.",),
            )
        profile = profiles_by_product.get(product.product_id)
        candidate = IdentificationCandidate(
            product_id=product.product_id,
            canonical_name=product.canonical_name,
            score=1.0,
            signals=("exact_part_number",),
            observation_ids=profile.observation_ids if profile else (),
        )
        return IdentificationDecision(
            status="matched",
            confidence=1.0,
            reason="exact_part_number",
            product_id=product.product_id,
            candidates=(candidate,),
        )
    if len(number_matches) > 1:
        return IdentificationDecision(
            status="review_required",
            confidence=0.0,
            reason="part_number_matches_multiple_products",
            candidates=tuple(
                IdentificationCandidate(
                    product.product_id,
                    product.canonical_name,
                    1.0,
                    ("exact_part_number",),
                    profiles_by_product.get(
                        product.product_id,
                        ProductEvidenceProfile(product.product_id),
                    ).observation_ids,
                )
                for product in number_matches
            ),
            questions_needed=("Which product record owns the observed part number?",),
        )

    ranked: list[IdentificationCandidate] = []
    for product in products:
        profile = profiles_by_product.get(
            product.product_id, ProductEvidenceProfile(product.product_id)
        )
        signals: list[str] = []
        score = 0.0

        if observed_numbers & _product_numbers(product):
            score += 0.7
            signals.append("exact_observed_part_number")

        if query.mentioned_name:
            name_candidates = (product.canonical_name, *product.aliases)
            best_name = max(_name_score(query.mentioned_name, item) for item in name_candidates)
            if best_name > 0:
                score += 0.35 * best_name
                signals.append(f"name_similarity:{best_name:.2f}")

        if query.label_texts:
            label_candidates = (
                product.canonical_name,
                *product.aliases,
                *profile.label_terms,
            )
            best_label = max(
                (_name_score(observed, expected) for observed in query.label_texts for expected in label_candidates),
                default=0.0,
            )
            if best_label > 0:
                score += 0.25 * best_label
                signals.append(f"label_similarity:{best_label:.2f}")

        visual_score, visual_hits, visual_total = _coverage(
            query.visual_features, profile.visual_features
        )
        if visual_score:
            score += 0.25 * visual_score
            signals.append(f"visual_features:{visual_hits}/{visual_total}")

        fitment_score, fitment_hits, fitment_total = _coverage(
            query.fitment_terms, profile.fitment_terms
        )
        if fitment_score:
            score += 0.15 * fitment_score
            signals.append(f"fitment_terms:{fitment_hits}/{fitment_total}")

        if score >= 0.18:
            ranked.append(
                IdentificationCandidate(
                    product.product_id,
                    product.canonical_name,
                    min(score, 0.89),
                    tuple(signals),
                    profile.observation_ids,
                )
            )

    ranked.sort(key=lambda candidate: (-candidate.score, candidate.product_id))
    ranked = ranked[:5]
    if not ranked:
        return IdentificationDecision(
            status="new_product_candidate",
            confidence=0.0,
            reason="no_internal_evidence_match",
            questions_needed=(
                "Provide a clear label photo, part number, fitment context, or distinguishing measurements.",
            ),
        )

    questions = ["Confirm the intended product from the ranked internal candidates."]
    if observed_numbers:
        questions.append("Confirm the OCR-observed part number against the physical label.")
    elif not confirmed_numbers:
        questions.append("Provide a readable part number or label photo if available.")
    return IdentificationDecision(
        status="review_required",
        confidence=ranked[0].score,
        reason="ranked_internal_evidence",
        candidates=tuple(ranked),
        questions_needed=tuple(questions),
    )


def identify_from_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    query_data = payload.get("query")
    products_data = payload.get("products", [])
    profiles_data = payload.get("evidence_profiles", [])
    if not isinstance(query_data, Mapping):
        raise ValidationError("query must be an object")
    if not isinstance(products_data, list) or not all(
        isinstance(item, Mapping) for item in products_data
    ):
        raise ValidationError("products must be an array of objects")
    if not isinstance(profiles_data, list) or not all(
        isinstance(item, Mapping) for item in profiles_data
    ):
        raise ValidationError("evidence_profiles must be an array of objects")

    products = [ProductRecord.from_mapping(item) for item in products_data]
    profiles = [ProductEvidenceProfile.from_mapping(item) for item in profiles_data]
    product_ids = {product.product_id for product in products}
    unknown_profile_ids = sorted(
        {profile.product_id for profile in profiles} - product_ids
    )
    if unknown_profile_ids:
        raise ValidationError(
            "evidence_profiles reference unknown product_id values: "
            + ", ".join(unknown_profile_ids)
        )
    return identify_product(
        IdentificationQuery.from_mapping(query_data), products, profiles
    ).to_dict()
