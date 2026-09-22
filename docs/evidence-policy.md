# Evidence Policy

## Purpose

This policy governs information captured from quick notes, voice messages, images, supplier pages, marketplaces, internal enquiries, and later research. The system may influence real purchasing decisions, so traceability is more important than filling every field.

## 1. Preserve the original input

Every captured item must retain an immutable reference to its original form where practical:

- original text or transcript;
- image, document, or audio attachment reference;
- capture channel and message identifier;
- sender or source identity when relevant;
- original timestamp and ingestion timestamp;
- language and transcription method, when applicable.

Structured extraction supplements the original input; it does not replace it.

## 2. Label the nature of every claim

Use one of these evidence classes:

- `observed`: directly visible in a cited source, image, document, listing, or business record;
- `user_reported`: supplied from personal experience, a conversation, or an informal note;
- `calculated`: produced deterministically from recorded inputs and a named formula or configuration version;
- `inferred`: interpreted or classified from evidence but not directly established;
- `unresolved`: ambiguous, disputed, or lacking enough support.

Do not present `user_reported` or `inferred` information as independently verified fact.

## 3. Record provenance

Each atomic observation should carry as many of these fields as apply:

- source type, title, URL, or internal reference;
- source publication date, if known;
- date observed;
- quoted or transcribed evidence snippet;
- currency, units, quantity, MOQ, and quality grade;
- relevant truck, engine, transmission, or axle context;
- extractor type and version;
- confidence and the reason for that confidence.

A URL alone is not sufficient provenance for a value that may later change.

## 4. Separate identity from notes

Do not merge a captured note into a part record until a match is supported by a confirmed part number or sufficient identifying context. When several records may match:

- retain all candidates;
- record the evidence for and against each candidate;
- assign a match status and confidence;
- route low-confidence matches for human review.

Never invent or silently repair a part number. Preserve the entered value and store normalized forms separately.

## 5. Preserve contradictions and history

New information must not silently overwrite older evidence. Append a new observation, link it to the affected part or candidate, and mark whether it confirms, updates, or conflicts with earlier information.

Corrections should record who or what made the correction, when it was made, and why. Derived summaries may change; raw observations should remain recoverable.

## 6. Represent confidence and missing information

Confidence should reflect evidence quality, agreement between independent sources, specificity of fitment, source freshness, and extraction certainty. It must not be used to disguise missing data.

When evidence is insufficient, return the missing verification information, such as a photograph, chassis/VIN, engine model, dimensions, teeth count, connector layout, mounting points, or original part number.

## 7. Price and market observations

Every price observation must distinguish, where known:

- listing price from confirmed transaction price;
- unit price from package or MOQ price;
- product cost from freight, duty, and landed cost;
- OEM, premium aftermarket, standard aftermarket, and unknown quality;
- currency and exchange-rate date;
- Nigerian retail, wholesale, and asking prices.

Online availability is only a market signal. It is not proof of Nigerian demand or actual turnover.

Supplier availability reports are also time-sensitive market signals. Store
each report as a dated observation rather than overwriting an earlier one.
Results shown to a user must state their age or freshness and require direct
reconfirmation before quoting, promising stock, or purchasing.

## 8. AI-generated structure

AI extraction may propose:

- a possible part-record match;
- names, variants, attributes, and relationships;
- an attachment transcription or visual description;
- confidence and follow-up questions.

Deterministic validation must check field formats, allowed values, identifiers, calculations, and duplicates. Material low-confidence identity or fitment claims require human review before they influence purchasing recommendations.

## 9. Minimum acceptance rule

A structured observation is acceptable only when it can be traced back to an original input and clearly identifies what was observed, when, from whom or where, and with what certainty. If this minimum cannot be met, retain it as an unstructured inbox item rather than forcing it into a trusted part record.
