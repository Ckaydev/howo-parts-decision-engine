from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .api import serve
from .availability import rank_supplier_reports
from .identification import identify_from_payload
from .models import ValidationError
from .normalization import normalize_name, normalize_part_number
from .pipeline import process_capture
from .visual import process_visual_evidence
from .image_pipeline import process_image_identification
from .catalogue import build_catalogue_context
from .review import resolve_review
from .review_commands import resolve_review_command


def _load_json(path: str) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError("input JSON must contain an object")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(prog="howo-capture")
    subparsers = parser.add_subparsers(dest="command", required=True)

    process_parser = subparsers.add_parser("process")
    process_parser.add_argument("input", help="Path to a process payload JSON file")
    process_parser.add_argument("--output", help="Optional output JSON path")

    identify_parser = subparsers.add_parser("identify")
    identify_parser.add_argument("input", help="Path to an identification payload JSON file")

    supplier_parser = subparsers.add_parser("supplier-reports")
    supplier_parser.add_argument("input", help="Path to a supplier report lookup JSON file")

    visual_parser = subparsers.add_parser("visual-evidence")
    visual_parser.add_argument("input", help="Path to a visual extraction payload JSON file")

    image_parser = subparsers.add_parser("identify-image")
    image_parser.add_argument("input", help="Path to an image identification payload JSON file")

    catalogue_parser = subparsers.add_parser("catalogue-context")
    catalogue_parser.add_argument("input", help="Path to a catalogue rows payload JSON file")

    review_parser = subparsers.add_parser("resolve-review")
    review_parser.add_argument("input", help="Path to a human review resolution JSON file")

    review_command_parser = subparsers.add_parser("resolve-review-command")
    review_command_parser.add_argument(
        "input", help="Path to a Telegram review command payload JSON file"
    )

    normalize_parser = subparsers.add_parser("normalize")
    normalize_parser.add_argument("--part-number")
    normalize_parser.add_argument("--name")

    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)

    args = parser.parse_args()
    try:
        if args.command == "process":
            result = process_capture(_load_json(args.input))
            rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
            if args.output:
                Path(args.output).write_text(rendered, encoding="utf-8")
            else:
                sys.stdout.write(rendered)
        elif args.command == "identify":
            result = identify_from_payload(_load_json(args.input))
            sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        elif args.command == "supplier-reports":
            result = rank_supplier_reports(_load_json(args.input))
            sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        elif args.command == "visual-evidence":
            result = process_visual_evidence(_load_json(args.input))
            sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        elif args.command == "identify-image":
            result = process_image_identification(_load_json(args.input))
            sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        elif args.command == "catalogue-context":
            result = build_catalogue_context(_load_json(args.input))
            sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        elif args.command == "resolve-review":
            result = resolve_review(_load_json(args.input))
            sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        elif args.command == "resolve-review-command":
            result = resolve_review_command(_load_json(args.input))
            sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        elif args.command == "normalize":
            print(
                json.dumps(
                    {
                        "part_number": normalize_part_number(args.part_number),
                        "name": normalize_name(args.name),
                    },
                    ensure_ascii=False,
                )
            )
        elif args.command == "serve":
            serve(args.host, args.port)
    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
