from __future__ import annotations

import html
import json
import re
from xml.sax.saxutils import escape

import requests
from flask import current_app


def validate_scan(*, location, barcode: str, mode: str, test_result: str = "good") -> dict:
    api_url = current_app.config.get("SCANNER_API_URL")
    api_timeout = current_app.config.get("SCANNER_API_TIMEOUT", 10)
    testing_mode = current_app.config.get("SCANNER_TESTING", False)

    if testing_mode:
        return _mock_validation(location=location, barcode=barcode, mode=mode, test_result=test_result)

    request_xml = _build_envelope(
        barcode=barcode,
        mode=mode,
        location_id=location.external_location_id,
    )

    if not api_url:
        return {
            "ok": False,
            "status": "not_configured",
            "http_status": None,
            "summary": "CONFIG",
            "payload": {
                "detail": "Set SCANNER_API_URL to enable live validation calls.",
                "location_id": location.external_location_id,
                "request_xml": request_xml,
            },
            "error_detail": "Missing SCANNER_API_URL environment variable.",
        }

    headers = {"Content-Type": 'text/xml;charset="utf-8"'}

    try:
        response = requests.post(
            api_url,
            data=request_xml.encode("utf-8"),
            headers=headers,
            timeout=api_timeout,
        )
    except requests.RequestException as exc:
        return {
            "ok": False,
            "status": "request_error",
            "http_status": None,
            "summary": "REQUEST ERROR",
            "payload": {
                "detail": "API request failed before a response was received.",
                "location_id": location.external_location_id,
                "request_xml": request_xml,
            },
            "error_detail": str(exc),
        }

    raw_response = response.text or ""
    response_headers = dict(response.headers)

    if not response.ok:
        return {
            "ok": False,
            "status": "api_error",
            "http_status": response.status_code,
            "summary": f"HTTP {response.status_code}",
            "payload": {
                "detail": None,
                "location_id": location.external_location_id,
                "msg": None,
                "raw_response": raw_response,
                "request_xml": request_xml,
                "response_headers": response_headers,
                "valid": None,
            },
            "error_detail": raw_response.strip() or f"HTTP {response.status_code} with empty response body.",
        }

    parsed = _parse_response(raw_response)
    msg = parsed["msg"] or ("GOOD" if parsed["valid"] == "1" else "BAD" if parsed["valid"] == "0" else "UNKNOWN")
    is_good = parsed["valid"] == "1"
    has_scan_result = parsed["valid"] in {"0", "1"} or parsed["msg"] in {"GOOD", "BAD"}
    status = "good" if is_good else "bad" if has_scan_result else "unknown"

    return {
        "ok": is_good,
        "status": status,
        "http_status": response.status_code,
        "summary": msg,
        "payload": {
            "detail": parsed["detail"],
            "location_id": location.external_location_id,
            "msg": msg,
            "raw_response": raw_response,
            "request_xml": request_xml,
            "response_headers": response_headers,
            "valid": parsed["valid"],
        },
        "error_detail": parsed["detail"] if not is_good else None,
    }


def dump_payload(value: dict) -> str:
    return json.dumps(value, indent=2, sort_keys=True)


def _mock_validation(*, location, barcode: str, mode: str, test_result: str) -> dict:
    normalized_result = "bad" if test_result == "bad" else "good"
    valid = "1" if normalized_result == "good" else "0"
    msg = "GOOD" if normalized_result == "good" else "BAD"
    action_label = "Inquiry" if mode == "inquiry" else "Execute"
    detail = (
        f"{action_label} Scan: {barcode} 81831009000"
        if normalized_result == "good"
        else (
            f"{action_label} Scan: {barcode} 3109578342809\n"
            f"Error: There Is No Record For PASS_NO A{barcode} In Table ACCESS"
        )
    )

    return {
        "ok": normalized_result == "good",
        "status": normalized_result,
        "http_status": None,
        "summary": msg,
        "payload": {
            "detail": detail,
            "location_id": location.external_location_id,
            "msg": msg,
            "raw_response": _mock_response(detail=detail, msg=msg, valid=valid),
            "test_mode": True,
            "valid": valid,
        },
        "error_detail": None if normalized_result == "good" else detail,
    }


def _build_envelope(*, barcode: str, mode: str, location_id: str) -> str:
    inquiry_value = "1" if mode == "inquiry" else "0"
    escaped_barcode = escape(barcode)
    escaped_location_id = escape(location_id)
    str_args = (
        f"<inquiry>{inquiry_value}</inquiry>"
        f"<scan>{escaped_barcode}</scan>"
        f"<location>{escaped_location_id}</location>"
    )
    escaped_str_args = escape(str_args)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
xmlns:xsd="http://www.w3.org/2001/XMLSchema"
xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <rInvoke xmlns="http://tempuri.org/wwService/wwSales">
      <strFunc>validate</strFunc>
      <strArgs>{escaped_str_args}</strArgs>
    </rInvoke>
  </soap:Body>
</soap:Envelope>"""


def _parse_response(raw_text: str) -> dict:
    normalized = _normalize_response_body(raw_text)
    return {
        "detail": _extract_tag(normalized, "detail"),
        "msg": _extract_tag(normalized, "msg"),
        "valid": _extract_tag(normalized, "valid"),
    }


def _extract_tag(raw_text: str, tag_name: str) -> str | None:
    match = re.search(
        rf"<(?:\w+:)?{tag_name}>(.*?)</(?:\w+:)?{tag_name}>",
        raw_text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if not match:
        return None

    return match.group(1).strip()


def _normalize_response_body(raw_text: str) -> str:
    invoke_result = _extract_tag(raw_text, "rInvokeResult")
    if not invoke_result:
        return html.unescape(raw_text)

    return html.unescape(invoke_result)


def _mock_response(*, detail: str, msg: str, valid: str) -> str:
    return (
        "OK :\n"
        f"<detail>{detail}</detail>\n"
        f"<msg>{msg}</msg>\n"
        f"<valid>{valid}</valid>\n"
    )
