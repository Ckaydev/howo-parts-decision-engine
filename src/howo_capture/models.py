from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


EVIDENCE_CLASSES = {
    "observed",
    "user_reported",
    "calculated",
    "inferred",
    "unresolved",
}

MEDIA_TYPES = {"none", "image", "voice", "audio", "document", "video"}

PROCESSING_STATUSES = {
    "received",
    "extracting",
    "needs_review",
    "structured",
    "failed",
}


class ValidationError(ValueError):
    """Raised when data would violate the capture contract."""


def _require_text(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{key} must be a non-empty string")
    return value.strip()


def _optional_text(data: Mapping[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{key} must be a string or null")
    return value.strip() or None


def _string_list(value: Any, key: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValidationError(f"{key} must be an array of strings")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(f"{key} must contain only non-empty strings")
        result.append(item.strip())
    return tuple(result)


def _pipe_or_string_list(value: Any, key: str) -> tuple[str, ...]:
    if isinstance(value, str):
        value = [item for item in value.split("|") if item.strip()]
    return _string_list(value, key)


@dataclass(frozen=True)
class CaptureEnvelope:
    capture_id: str
    channel: str
    channel_message_id: str
    captured_at: str
    ingested_at: str
    sender_id: str
    raw_text: str | None = None
    media_type: str = "none"
    media_original_ref: str | None = None
    media_archive_url: str | None = None
    transcript: str | None = None
    processing_status: str = "received"
    processing_error: str | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "CaptureEnvelope":
        channel = _require_text(data, "channel").lower()
        media_type = str(data.get("media_type", "none")).lower()
        if media_type not in MEDIA_TYPES:
            raise ValidationError(f"media_type must be one of {sorted(MEDIA_TYPES)}")
        processing_status = str(data.get("processing_status", "received")).lower()
        if processing_status not in PROCESSING_STATUSES:
            raise ValidationError(
                f"processing_status must be one of {sorted(PROCESSING_STATUSES)}"
            )

        envelope = cls(
            capture_id=_require_text(data, "capture_id"),
            channel=channel,
            channel_message_id=_require_text(data, "channel_message_id"),
            captured_at=_require_text(data, "captured_at"),
            ingested_at=_require_text(data, "ingested_at"),
            sender_id=_require_text(data, "sender_id"),
            raw_text=_optional_text(data, "raw_text"),
            media_type=media_type,
            media_original_ref=_optional_text(data, "media_original_ref"),
            media_archive_url=_optional_text(data, "media_archive_url"),
            transcript=_optional_text(data, "transcript"),
            processing_status=processing_status,
            processing_error=_optional_text(data, "processing_error"),
        )
        if not envelope.raw_text and not envelope.transcript and envelope.media_type == "none":
            raise ValidationError(
                "capture must contain raw_text, transcript, or a media attachment"
            )
        return envelope

    def to_dict(self) -> dict[str, Any]:
        return {
            "capture_id": self.capture_id,
            "channel": self.channel,
            "channel_message_id": self.channel_message_id,
            "captured_at": self.captured_at,
            "ingested_at": self.ingested_at,
            "sender_id": self.sender_id,
            "raw_text": self.raw_text,
            "media_type": self.media_type,
            "media_original_ref": self.media_original_ref,
            "media_archive_url": self.media_archive_url,
            "transcript": self.transcript,
            "processing_status": self.processing_status,
            "processing_error": self.processing_error,
        }


@dataclass(frozen=True)
class ProductRecord:
    product_id: str
    canonical_name: str
    primary_part_number: str | None = None
    aliases: tuple[str, ...] = ()
    additional_part_numbers: tuple[str, ...] = ()
    identity_status: str = "provisional"

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ProductRecord":
        return cls(
            product_id=_require_text(data, "product_id"),
            canonical_name=_require_text(data, "canonical_name"),
            primary_part_number=_optional_text(data, "primary_part_number"),
            aliases=_pipe_or_string_list(data.get("aliases", ()), "aliases"),
            additional_part_numbers=_pipe_or_string_list(
                data.get("additional_part_numbers", ()),
                "additional_part_numbers",
            ),
            identity_status=str(data.get("identity_status", "provisional")),
        )


@dataclass(frozen=True)
class ProductEvidenceProfile:
    product_id: str
    label_terms: tuple[str, ...] = ()
    visual_features: tuple[str, ...] = ()
    fitment_terms: tuple[str, ...] = ()
    observation_ids: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ProductEvidenceProfile":
        return cls(
            product_id=_require_text(data, "product_id"),
            label_terms=_pipe_or_string_list(data.get("label_terms", ()), "label_terms"),
            visual_features=_pipe_or_string_list(
                data.get("visual_features", ()), "visual_features"
            ),
            fitment_terms=_pipe_or_string_list(
                data.get("fitment_terms", ()), "fitment_terms"
            ),
            observation_ids=_pipe_or_string_list(
                data.get("observation_ids", ()), "observation_ids"
            ),
        )


@dataclass(frozen=True)
class IdentificationQuery:
    mentioned_name: str | None = None
    confirmed_part_numbers: tuple[str, ...] = ()
    observed_part_numbers: tuple[str, ...] = ()
    label_texts: tuple[str, ...] = ()
    visual_features: tuple[str, ...] = ()
    fitment_terms: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "IdentificationQuery":
        query = cls(
            mentioned_name=_optional_text(data, "mentioned_name"),
            confirmed_part_numbers=_pipe_or_string_list(
                data.get("confirmed_part_numbers", ()), "confirmed_part_numbers"
            ),
            observed_part_numbers=_pipe_or_string_list(
                data.get("observed_part_numbers", ()), "observed_part_numbers"
            ),
            label_texts=_pipe_or_string_list(data.get("label_texts", ()), "label_texts"),
            visual_features=_pipe_or_string_list(
                data.get("visual_features", ()), "visual_features"
            ),
            fitment_terms=_pipe_or_string_list(
                data.get("fitment_terms", ()), "fitment_terms"
            ),
        )
        if not any(
            (
                query.mentioned_name,
                query.confirmed_part_numbers,
                query.observed_part_numbers,
                query.label_texts,
                query.visual_features,
                query.fitment_terms,
            )
        ):
            raise ValidationError("identification query must contain at least one signal")
        return query


@dataclass(frozen=True)
class IdentificationCandidate:
    product_id: str
    canonical_name: str
    score: float
    signals: tuple[str, ...]
    observation_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "canonical_name": self.canonical_name,
            "score": round(self.score, 4),
            "signals": list(self.signals),
            "observation_ids": list(self.observation_ids),
        }


@dataclass(frozen=True)
class IdentificationDecision:
    status: str
    confidence: float
    reason: str
    product_id: str | None = None
    candidates: tuple[IdentificationCandidate, ...] = ()
    questions_needed: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "confidence": round(self.confidence, 4),
            "reason": self.reason,
            "product_id": self.product_id,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "questions_needed": list(self.questions_needed),
        }


@dataclass(frozen=True)
class ProductReference:
    mentioned_name: str | None = None
    mentioned_part_numbers: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> "ProductReference":
        data = data or {}
        if not isinstance(data, Mapping):
            raise ValidationError("product_reference must be an object")
        return cls(
            mentioned_name=_optional_text(data, "mentioned_name"),
            mentioned_part_numbers=_string_list(
                data.get("mentioned_part_numbers"), "mentioned_part_numbers"
            ),
        )


@dataclass(frozen=True)
class ExtractedClaim:
    claim_type: str
    claim_text: str
    structured_value: Any = None
    evidence_class: str = "user_reported"
    confidence: float = 0.5
    variant_name: str | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ExtractedClaim":
        evidence_class = str(data.get("evidence_class", "user_reported"))
        if evidence_class not in EVIDENCE_CLASSES:
            raise ValidationError(
                f"evidence_class must be one of {sorted(EVIDENCE_CLASSES)}"
            )
        raw_confidence = data.get("confidence", 0.5)
        if not isinstance(raw_confidence, (int, float)):
            raise ValidationError("confidence must be a number")
        confidence = float(raw_confidence)
        if not 0 <= confidence <= 1:
            raise ValidationError("confidence must be between 0 and 1")
        return cls(
            claim_type=_require_text(data, "claim_type"),
            claim_text=_require_text(data, "claim_text"),
            structured_value=data.get("structured_value"),
            evidence_class=evidence_class,
            confidence=confidence,
            variant_name=_optional_text(data, "variant_name"),
        )


@dataclass(frozen=True)
class ExtractionResult:
    summary: str
    product_reference: ProductReference
    claims: tuple[ExtractedClaim, ...] = ()
    follow_up_questions: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ExtractionResult":
        raw_claims = data.get("claims", [])
        if not isinstance(raw_claims, list):
            raise ValidationError("claims must be an array")
        if not all(isinstance(item, Mapping) for item in raw_claims):
            raise ValidationError("claims must contain only objects")
        return cls(
            summary=_require_text(data, "summary"),
            product_reference=ProductReference.from_mapping(
                data.get("product_reference")
            ),
            claims=tuple(ExtractedClaim.from_mapping(item) for item in raw_claims),
            follow_up_questions=_string_list(
                data.get("follow_up_questions"), "follow_up_questions"
            ),
        )


@dataclass(frozen=True)
class MatchCandidate:
    product_id: str
    canonical_name: str
    score: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "canonical_name": self.canonical_name,
            "score": round(self.score, 4),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class MatchDecision:
    status: str
    confidence: float
    reason: str
    product_id: str | None = None
    candidates: tuple[MatchCandidate, ...] = field(default_factory=tuple)
    questions_needed: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "confidence": round(self.confidence, 4),
            "reason": self.reason,
            "product_id": self.product_id,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "questions_needed": list(self.questions_needed),
        }
