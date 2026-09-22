# Capture v1 Setup

This stage records Telegram messages in the `Capture_Inbox` tab before any AI transformation. It is intentionally useful on its own: every input receives a stable identifier, duplicate delivery updates the same row, and the bot confirms receipt.

## What is already built

- Google Sheets-ready workbook with the complete capture schema;
- deterministic Python core for normalization, matching, validation, and review routing;
- dependency-free local HTTP service and Docker image;
- importable n8n workflow for Telegram raw capture;
- schemas, examples, and unit tests.

## Manual prerequisites

### 1. Start and identify n8n

Start Docker Desktop and the existing n8n container. Record the n8n version shown in the UI or with:

```bash
docker exec <n8n-container-name> n8n --version
```

The workflow was authored against current node definitions for Telegram Trigger 1.2 and Google Sheets 4.7. Import compatibility must be confirmed against the installed version before activation.

### 2. Make the workbook a Google Sheet

Upload `outputs/telegram-capture-v1/howo_parts_capture_template.xlsx` to Google Drive and open it as a Google Sheet. Retain the tab names exactly.

Copy the spreadsheet ID from the URL:

```text
https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
```

### 3. Create the Telegram bot

In Telegram, message the official `@BotFather`, create a bot, and copy its token into an n8n Telegram credential. Do not place the token in this repository or directly in the workflow JSON.

To learn your Telegram numeric user ID, temporarily run the Telegram Trigger in test mode without the user restriction, send the bot a message, and inspect `message.from.id`. Immediately place that number into **Restrict to User IDs** before activation.

### 4. Confirm webhook reachability

n8n's Telegram Trigger registers a webhook. The production webhook URL must be publicly reachable over HTTPS. If the local n8n instance already has a working public `WEBHOOK_URL`, no change is needed.

If it does not, choose one of these before activation:

- expose n8n through an authenticated reverse proxy or tunnel with HTTPS;
- use a polling-based Telegram ingress instead of the trigger.

This decision affects networking and security, so it is not made automatically.

### 5. Configure Google credentials

Create or select a Google Sheets OAuth credential in n8n with edit access to the workbook. The first workflow does not need Google Drive access because media archival is not active yet.

### 6. Import the workflow

Import [the workflow](../workflows/telegram_raw_capture_v1.json), then:

1. select the Telegram credential on both Telegram nodes;
2. put the numeric owner ID in **Restrict to User IDs**;
3. select the Google Sheets credential;
4. replace the spreadsheet ID;
5. select `Capture_Inbox` by name;
6. confirm header row `3` and first data row `4` under the node's data-location options;
7. refresh column mappings if n8n reports that the sheet headers changed;
8. test with one text message before activating the workflow.

## Expected first test

Send:

```text
Test note about front brake chamber WG9000360600.
```

Expected result:

- one row appears in `Capture_Inbox`;
- `capture_id` is `cap_telegram_<chat-id>_<message-id>`;
- `processing_status` is `received`;
- the bot replies with the saved capture ID;
- rerunning the same n8n execution updates the same row rather than creating another.

## Run the deterministic core locally

No package installation is required:

```bash
PYTHONPATH=src python3 -m howo_capture process examples/process-known-part.json
```

Run it as a local HTTP service:

```bash
PYTHONPATH=src python3 -m howo_capture serve --host 127.0.0.1 --port 8765
```

Or build the adjacent Docker service:

```bash
docker compose -f compose.capture.yml up --build -d
```

The n8n container can later call `http://host.docker.internal:8765/v1/process` on Docker Desktop. A shared Docker network is preferable if the existing n8n Compose project can be safely edited.

## Current live stage

The live n8n workflow now covers the capture and human-review loop:

- text, images, and voice notes enter through the restricted Telegram trigger;
- Telegram media is archived in Google Drive and its link is retained in Sheets;
- voice notes are transcribed before structured processing;
- the local decision service writes matched observations or an open
  `Review_Queue` item;
- open review items are sent back to Telegram with their `Review ID` and ranked
  candidates;
- a reply command resolves the review and writes the decision to Sheets.

For an open review notification, reply to that exact Telegram message with one
of:

```text
link PRODUCT_ID
link PRODUCT_ID --accept-image
new "PRODUCT NAME"
reject
```

Use `--accept-image` only after visually confirming that the attached image is
the stated product. Add `--pn=PART_NUMBER` only after checking the number on the
physical label. The longer form `/resolve REVIEW_ID ...` works without replying
to the notification.

The workflow is intentionally left inactive after an import. Before activating
it, confirm that **Restrict to User IDs** on `Telegram Capture` contains the
owner's numeric Telegram ID. Then activate it and run the review-loop test
below.

## Review-loop test

1. Send a photo and description that cannot be matched confidently to an
   existing product.
2. Confirm that the bot sends a `Review needed` message containing a
   `Review ID` and that Sheets contains the same open row in `Review_Queue`.
3. Reply to the bot message with `link PRODUCT_ID` using a real ID from the
   `Products` tab.
4. Confirm that the bot sends `Review resolved`, the review row is closed, and
   `Review_Decisions` contains one audit row.

If the notification does not arrive, inspect the latest n8n execution starting
at `Prepare Review Notification`. If the command is captured as a new product
note, inspect `Is Review Command?`; valid commands must take its true branch.

## Earlier build sequence

Once raw capture is confirmed, extend the workflow in this order:

1. upload downloaded Telegram media to a dedicated Google Drive folder;
2. append an `Attachments` record and update `media_archive_url`;
3. transcribe voice/audio;
4. run schema-constrained extraction;
5. read the `Products` tab;
6. call the local `/v1/process` endpoint;
7. append observations or review items;
8. send the interpretation and any clarification questions to Telegram.

The schema-constrained extraction prompt is versioned at
`prompts/capture-extraction-v1.md`. The AI step must return JSON matching
`schemas/extraction-result.schema.json`; the local `/v1/process` endpoint then
validates that structure and performs conservative matching. A voice-note
example is available at `examples/process-voice-note.json`.

The live workflow now contains the first two nodes for steps 5 and 6:

- `Read Products` reads header row 3 and data from row 4, with empty-list
  output enabled;
- `Prepare Decision Request` builds the service payload using
  `workflows/code/prepare_decision_request.js`;
- `Run Decision Engine` posts that payload to
  `http://howo-capture:8765/v1/process` on the shared Docker network.
- `workflows/code/route_decision_result.js` converts the service response into
  explicit `capture_inbox`, `observation`, `part_number`, and `review_queue`
  routes. Each route carries its stable match key so n8n retries can upsert the
  same logical record instead of creating duplicates.

Keep Google errors fail-closed. Do not treat an authentication failure as an
empty product list.
