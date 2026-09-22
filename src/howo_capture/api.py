from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .models import ValidationError
from .normalization import normalize_name, normalize_part_number
from .pipeline import process_capture
from .identification import identify_from_payload
from .availability import rank_supplier_reports
from .visual import process_visual_evidence
from .image_pipeline import process_image_identification
from .catalogue import build_catalogue_context
from .review import resolve_review
from .review_commands import resolve_review_command


MAX_REQUEST_BYTES = 5 * 1024 * 1024


class CaptureRequestHandler(BaseHTTPRequestHandler):
    server_version = "HowoCapture/0.1"

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._write_json(
                HTTPStatus.OK,
                {"status": "ok", "service": "howo-capture", "version": "0.1.0"},
            )
            return
        self._write_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_length"})
            return
        if length <= 0 or length > MAX_REQUEST_BYTES:
            self._write_json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                {"error": "request_body_must_be_between_1_byte_and_5_mb"},
            )
            return
        try:
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValidationError("request body must be a JSON object")
            if self.path == "/v1/process":
                result = process_capture(payload)
            elif self.path == "/v1/identify":
                result = identify_from_payload(payload)
            elif self.path == "/v1/supplier-reports":
                result = rank_supplier_reports(payload)
            elif self.path == "/v1/visual-evidence":
                result = process_visual_evidence(payload)
            elif self.path == "/v1/identify-image":
                result = process_image_identification(payload)
            elif self.path == "/v1/catalogue-context":
                result = build_catalogue_context(payload)
            elif self.path == "/v1/resolve-review":
                result = resolve_review(payload)
            elif self.path == "/v1/resolve-review-command":
                result = resolve_review_command(payload)
            elif self.path == "/v1/normalize":
                result = {
                    "part_number": normalize_part_number(payload.get("part_number")),
                    "name": normalize_name(payload.get("name")),
                }
            else:
                self._write_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
        except (json.JSONDecodeError, ValidationError, ValueError, TypeError) as exc:
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "validation_error", "detail": str(exc)},
            )
            return
        self._write_json(HTTPStatus.OK, result)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), CaptureRequestHandler)
    print(f"HOWO capture service listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the HOWO capture HTTP service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    serve(args.host, args.port)


if __name__ == "__main__":
    main()
