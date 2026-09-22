# Proposed Capture System

Status: capture foundation implemented; account-dependent activation pending

## Decision

Use a private Telegram bot as the first mobile capture channel, n8n as the workflow orchestrator, Google Drive for original media, and Google Sheets as the human-readable working database.

Keep the capture-channel contract generic so WhatsApp or Notion can be added later without changing the extraction or storage model.

## Why Telegram first

Telegram best matches the immediate need:

- message-style capture is quick on a phone;
- a bot can receive text, captions, photos, documents, and voice notes;
- bot creation and authentication are comparatively light;
- n8n has built-in Telegram trigger and file operations;
- it does not require a Meta business portfolio or WhatsApp Business Platform phone-number onboarding;
- the bot can immediately acknowledge what it extracted and request clarification.

The default Telegram Bot API can download incoming files up to 20 MB. That is sufficient for ordinary product photos and short voice notes, but the workflow must detect and report oversized attachments rather than dropping them.

Descriptions should normally be entered as the photo caption so the text and
image arrive as one capture. The workflow also supports an explicit text reply
to a photo: when the reply contains no new media, it reuses the replied-to
photo and records the relationship in the normalized execution data. It never
joins consecutive messages merely because they arrived close together.

Official references:

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [n8n Telegram integration](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.telegram/)

## Why not WhatsApp first

WhatsApp is probably the most familiar daily interface, but official programmable message capture uses the WhatsApp Business Platform. Its setup involves Meta developer and business assets, including a business portfolio, WhatsApp Business Account, and registered business phone number. Even if full business verification is not required for every initial test, it does not meet the goal of avoiding Meta onboarding friction.

Unofficial personal-WhatsApp automation should not be used for this project. It creates account, reliability, and maintainability risk at the point where original business evidence enters the system.

WhatsApp remains a later channel if the convenience benefit becomes worth official onboarding. It should then emit the same normalized capture envelope as Telegram.

Official references:

- [WhatsApp Business developer hub](https://whatsappbusiness.com/developers/developer-hub/)
- [Meta WhatsApp Cloud API collection](https://www.postman.com/meta/whatsapp-business-platform/collection/wlk6lh4/whatsapp-cloud-api)

## Why not Notion first

Notion is strong for reviewing and organizing knowledge. Its API supports pages, structured data sources, images, documents, and audio attachments. An internal connection can also be created without implementing OAuth.

It is less natural than chat for repeated one-handed capture of short voice notes and spontaneous observations. Using Notion as the capture surface while Google Sheets remains the working database also creates two overlapping data interfaces and synchronization questions before they are necessary.

Notion can be added later as a curated knowledge and review interface if Google Sheets becomes uncomfortable for reading long part histories.

Official references:

- [Notion developer quickstart](https://developers.notion.com/guides/get-started/quick-start)
- [Notion files and media](https://developers.notion.com/guides/data-apis/working-with-files-and-media)

## Proposed flow

```text
Private Telegram chat
        |
        v
Telegram trigger in n8n
        |
        +--> preserve message metadata
        +--> download photo/audio/document
        +--> save original media to Google Drive
        +--> transcribe voice note
        +--> extract structured claims
        +--> normalize names and part numbers
        +--> find possible product matches
        |
        v
Validation and confidence rules
        |
        +--> confident match: append observations
        +--> ambiguous match: add to Review Queue
        +--> no match: create proposed product candidate
        |
        v
Google Sheets
        |
        v
Telegram acknowledgement and clarification prompt
```

## Capture envelope

Every input channel should produce the same envelope before extraction:

| Field | Purpose |
| --- | --- |
| `capture_id` | Stable internal identifier for idempotency |
| `channel` | `telegram`, later `whatsapp`, `notion`, or manual |
| `channel_message_id` | Original platform message identifier |
| `captured_at` | Original message timestamp |
| `ingested_at` | Workflow receipt timestamp |
| `sender_id` | Allowed sender identifier |
| `raw_text` | Exact typed text or caption |
| `media_type` | Voice, image, document, video, or none |
| `media_original_ref` | Platform file identifier |
| `media_archive_url` | Durable Google Drive link |
| `transcript` | Voice transcription, if applicable |
| `processing_status` | Current workflow state |
| `processing_error` | Recoverable error detail |

The `capture_id` must be unique so an n8n retry cannot create duplicate observations.

## Google Sheets workbook

Do not store the entire knowledge base in one ever-widening product row. Use related tabs with stable identifiers.

### `Products`

One row per canonical or provisional product:

- `product_id`
- `canonical_name`
- `primary_part_number`
- `category`
- `system`
- `summary`
- `identity_status`
- `identity_confidence`
- `created_at`
- `updated_at`

### `Part_Numbers`

One row per observed part number or cross-reference:

- `part_number_id`
- `product_id`
- `raw_part_number`
- `normalized_part_number`
- `number_type`
- `status`
- `confidence`
- `observation_id`

### `Variants`

One row per distinguishable variant:

- `variant_id`
- `product_id`
- `variant_name`
- `distinguishing_attribute`
- `attribute_value`
- `application_notes`
- `status`
- `confidence`
- `observation_id`

### `Observations`

Append-only record of extracted claims:

- `observation_id`
- `capture_id`
- `product_id`
- `variant_id`
- `claim_type`
- `claim_text`
- `structured_value`
- `evidence_class`
- `confidence`
- `relationship`
- `review_status`
- `observed_at`

`relationship` records whether the observation confirms, updates, or conflicts with existing information.

### `Attachments`

- `attachment_id`
- `capture_id`
- `media_type`
- `drive_url`
- `original_filename`
- `mime_type`
- `transcript`
- `transcription_confidence`

### `Image_Evidence`

One row per reviewed interpretation of an archived product image:

- `image_evidence_id`
- `attachment_id`
- `capture_id`
- `product_id`
- `variant_id`
- `view_type`
- `visible_label_text`
- `ocr_text`
- `evidence_class`
- `confidence`
- `review_status`
- `observed_at`
- `observation_id`

The archived file remains in `Attachments`. This tab records what was visibly
read or inferred from that file and whether a person accepted it.

### `Visual_Features`

One row per distinguishing feature, such as a mounting count, connector layout,
dimension, marking, or fitment clue. Each row links back to image and observation
evidence so candidate ranking remains auditable.

### `Suppliers` and `Supplier_Reports`

`Suppliers` stores stable market-contact identities. `Supplier_Reports` stores
append-only, dated claims about a product's availability, quantity, or asking
price. A report is never treated as guaranteed current stock and must be
reconfirmed before the system recommends contacting, quoting, or purchasing.

### `Review_Queue`

- `review_id`
- `capture_id`
- `proposed_product_id`
- `candidate_matches`
- `reason`
- `questions_needed`
- `status`
- `reviewed_at`

This layout lets a product accumulate knowledge without losing the messages that produced it.

## Internal identification service

For photographs, the OpenAI Responses API supplies the image to the versioned
prompt in `prompts/image-evidence-extraction-v1.md`. The structured result is
sent to `POST /v1/visual-evidence`, which validates allowed fields, preserves
raw OCR readings, creates replay-safe provisional image/feature rows, and emits
an identification query. It never promotes an OCR reading into a confirmed part
number or assigns an unmatched image directly to a product.

OpenAI reference: [Images and vision](https://developers.openai.com/api/docs/guides/images-vision)

`POST /v1/identify-image` performs the visual validation and internal ranking in
one operation for n8n. It merges only separately validated caption evidence,
assigns image rows to a product only after a valid match, and otherwise emits a
replay-safe `Review_Queue` row with ranked candidates and clarification questions.

`POST /v1/identify` accepts an identification query, the current product list,
and evidence profiles derived from reviewed image/feature rows. Deterministic
ranking uses these signals in order of authority:

1. exact normalized part number confirmed by a person;
2. reviewed names and label terms;
3. reviewed visual features;
4. fitment clues.

A person-confirmed exact part number can identify one unique product. A number
observed by OCR ranks a matching product strongly but still needs confirmation
against the physical label. All other image-only, OCR-only, fuzzy-name, and
multi-signal results also remain ranked candidates. Candidate responses include
the supporting observation IDs.

`POST /v1/catalogue-context` joins the normalized Sheet tabs before matching.
It excludes rejected products, ignores unreviewed part numbers and images, and
builds reusable label, visual-feature, fitment, and observation profiles only
from human-accepted image evidence. A product/feature linkage conflict is
reported in diagnostics and excluded instead of being silently merged.

`POST /v1/resolve-review` turns an explicit human decision into replay-safe
Sheet rows. A reviewer may link an existing product, create a provisional
product, reject the capture, and accept or reject image evidence. New products
cannot be created as confirmed by this endpoint. A part number becomes
confirmed only when the request states that a person checked it and includes
the source reference used for that check. Every decision produces an immutable
`Review_Decisions` audit row; the raw capture remains unchanged.

`POST /v1/resolve-review-command` provides the strict Telegram-facing layer.
It accepts either a complete command such as
`/resolve REVIEW_ID link PRODUCT_ID` or a shorter reply such as
`link PRODUCT_ID` when the quoted bot message contains `Review ID:`. The
optional `--accept-image` flag is required before captured images become
accepted catalogue evidence. The optional `--pn=NUMBER` flag is treated as an
explicit human verification and records the Telegram message as its source.
Use `/resolve REVIEW_ID new "PRODUCT NAME"` to create a provisional product,
or `/resolve REVIEW_ID reject` to reject the review and its pending images.
Unknown options, missing review IDs, closed reviews, conflicting part numbers,
and cross-capture image references fail closed.

`POST /v1/supplier-reports` ranks historical supplier reports by product and
freshness as of an explicit timestamp. It labels stale and future-dated records
and always returns `requires_reconfirmation: true`.

## Example behavior

Input:

> Rotarito has an 11-teeth and a 12-teeth variant. I think their part numbers end differently. See the attached photos.

The system should:

1. preserve the exact message and photographs;
2. extract two proposed variants and the teeth-count distinction;
3. search the current product list for possible matches;
4. avoid inventing either part number;
5. append user-reported observations if the product match is reliable;
6. otherwise place the input in `Review_Queue` with candidate matches;
7. reply in Telegram with its interpretation and ask for the missing markings or confirmed product identity.

## First-version boundary

The first working version should support only:

- one authorized Telegram user;
- text, one or more photos, and short voice notes;
- English transcription, while retaining the original audio;
- matching against an existing product list by exact/normalized part number and name similarity;
- structured extraction into the tabs above;
- a review queue for ambiguous matches;
- a Telegram confirmation containing what was stored;
- replay-safe processing using `capture_id`.

It should not yet:

- conduct external supplier or Nigerian-market research;
- automatically declare a new part number correct;
- merge low-confidence product identities;
- calculate stock-opportunity scores;
- support multiple users or public bot access;
- use Notion as a second database;
- depend on WhatsApp.

## Implementation stages

1. Define the workbook columns and load the existing product list.
2. Create the private Telegram bot and restrict it to the owner's Telegram user ID.
3. Build an n8n flow that records the raw capture before doing any AI work.
4. Add media archival and voice transcription.
5. Add schema-constrained extraction and deterministic validation.
6. Add exact part-number matching, then cautious name matching.
7. Append observations or route uncertainty to `Review_Queue`.
8. Send a compact confirmation or clarification request back to Telegram.
9. Test with representative text, photo, voice, duplicate, ambiguous, and failure cases.

The live n8n extraction branch uses the versioned prompt in
`prompts/capture-extraction-v1.md`, followed by the deterministic Code node in
`workflows/code/validate_extraction_evidence.js`. The validator retains the raw
AI result, removes unsupported product names or part numbers from the trusted
copy, and marks material drift for review.

The photo branch runs separately from ordinary text extraction. It analyzes the
archived binary image, validates the visual result, sends it to
`POST /v1/identify-image`, and writes replay-safe rows to `Image_Evidence`,
`Visual_Features`, `Review_Queue`, and `Capture_Inbox`. The first live stage uses
the current `Products` rows and intentionally leaves reviewed evidence profiles
empty; building those profiles from accepted visual evidence is the next
catalogue-learning stage.

## Acceptance criteria

The first version is useful when:

- a capture takes no more effort than messaging a contact;
- the original input and attachments remain retrievable;
- repeated processing does not duplicate rows;
- known products receive append-only observations;
- uncertain product matches require review;
- a user can see what the system understood immediately;
- no unconfirmed part number or fitment becomes a trusted fact.
