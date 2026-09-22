# HOWO Parts Decision Engine

## Purpose

Build an internal, evidence-based system for identifying HOWO/SINOTRUK parts and deciding whether they deserve inventory capital in Nigeria. The product direction and phased scope live in [docs/north-star.md](docs/north-star.md).

## Working rules

- Start with the smallest usable stage; do not introduce a database, dashboard, or production infrastructure before it is needed.
- Preserve raw inputs and source evidence. Never invent suppliers, prices, demand, fitment, or part numbers.
- Keep observed facts, user-provided claims, calculations, and AI inferences distinguishable.
- Store research dates, source references, confidence, and unresolved contradictions with derived records.
- Use AI for extraction, normalization, classification, and explanation. Use deterministic code for validation, deduplication, currency arithmetic, scoring, and thresholds.
- Treat part-number and fitment ambiguity as a purchasing risk. Ask for identifying evidence rather than silently choosing a variant.
- Keep weights and business thresholds in versioned configuration rather than scattering them through code.
- Follow [docs/evidence-policy.md](docs/evidence-policy.md) whenever capturing or transforming business information.

## Project state and validation

The capture foundation is a dependency-free Python package under `src/howo_capture`, with schemas in `schemas`, n8n exports in `workflows`, and a Google Sheets-ready workbook under `outputs/telegram-capture-v1`. The local service also exposes conservative internal-evidence identification and freshness-aware supplier-report endpoints; OCR and image-only matches remain review candidates, and supplier reports always require reconfirmation.

Verified commands from the repository root:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m howo_capture process examples/process-known-part.json
PYTHONPATH=src python3 -m howo_capture visual-evidence examples/process-visual-evidence.json
PYTHONPATH=src python3 -m howo_capture identify-image examples/identify-image.json
PYTHONPATH=src python3 -m howo_capture identify examples/identify-part.json
PYTHONPATH=src python3 -m howo_capture catalogue-context examples/catalogue-context.json
PYTHONPATH=src python3 -m howo_capture resolve-review examples/resolve-review.json
PYTHONPATH=src python3 -m howo_capture resolve-review-command examples/resolve-review-command.json
PYTHONPATH=src python3 -m howo_capture supplier-reports examples/supplier-reports.json
PYTHONPATH=src python3 -m howo_capture serve --host 127.0.0.1 --port 8765
```

The HTTP service must remain local or network-restricted unless authentication is added. Never commit Telegram, Google, or AI credentials. The n8n workflow must remain inactive until its Telegram user-ID restriction is configured.

For each implementation change, run the smallest meaningful validation available and report anything that could not be checked. Never claim a purchasing workflow is reliable solely because its code executes.
