"""Implementation of the ``ccq verify`` command."""
from __future__ import annotations

import html
import json
import logging
from pathlib import Path
from typing import Dict, List

import requests
import typer

from ccq.models import CardSchema, VerificationResult
from ccq.utils.io import iter_json_files, read_json, write_json

LOGGER = logging.getLogger(__name__)

REQUIRED_KEYWORDS = {"apr", "fees", "foreign transaction"}


def _card_key(card: CardSchema) -> str:
    return "::".join(part.lower() for part in [card.issuer, card.card_name, card.country] if part)


def _url_check(url: str) -> Dict[str, str]:
    try:
        response = requests.head(url, allow_redirects=True, timeout=15)
        if response.status_code == 405:  # method not allowed
            response = requests.get(url, allow_redirects=True, timeout=15)
        ok = response.status_code == 200
        return {"passed": ok, "status_code": str(response.status_code)}
    except requests.RequestException as exc:
        return {"passed": False, "error": str(exc)}


def _semantic_check(keywords: List[str], issuer: str) -> Dict[str, str]:
    detected = set(keyword.lower() for keyword in keywords)
    required = set(REQUIRED_KEYWORDS)
    if issuer:
        required.add(issuer.lower())
    missing = sorted(required - detected)
    return {"passed": not missing, "missing": ", ".join(missing)}


def _schema_check(card: CardSchema) -> Dict[str, str]:
    issues: List[str] = []
    if card.annual_fee is not None and card.annual_fee < 0:
        issues.append("annual_fee negative")
    if card.purchase_apr is not None and not (0 <= card.purchase_apr <= 99):
        issues.append("purchase_apr out of range")
    if card.cash_advance_apr is not None and not (0 <= card.cash_advance_apr <= 99):
        issues.append("cash_advance_apr out of range")
    if card.fx_fee_percent is not None and not (0 <= card.fx_fee_percent <= 50):
        issues.append("fx_fee_percent out of range")
    return {"passed": not issues, "issues": ", ".join(issues)}


def _build_html_report(results: List[VerificationResult]) -> str:
    rows = []
    for result in results:
        details = ", ".join(f"{key}={html.escape(str(value))}" for key, value in result.details.items())
        rows.append(
            f"<tr><td>{html.escape(result.issuer)}</td><td>{html.escape(result.card_name)}</td>"
            f"<td>{html.escape(result.status)}</td><td>{details}</td></tr>"
        )
    body = "\n".join(rows)
    return (
        "<html><head><title>Verification Report</title></head><body>"
        "<h1>Verification Report</h1>"
        "<table border='1' cellspacing='0' cellpadding='4'>"
        "<tr><th>Issuer</th><th>Card</th><th>Status</th><th>Details</th></tr>"
        f"{body}</table></body></html>"
    )


def verify(
    parsed_dir: Path = typer.Option(Path("data/parsed"), "--in", help="Directory containing parsed JSON files"),
    report_path: Path = typer.Option(Path("data/parsed/verification_report.html"), "--report", help="HTML report destination"),
) -> None:
    manifest_path = parsed_dir / "manifest.json"
    manifest = {item["slug"]: item for item in read_json(manifest_path).get("items", [])} if manifest_path.exists() else {}

    results: List[VerificationResult] = []

    for json_file in iter_json_files(parsed_dir):
        slug = json_file.stem
        manifest_entry = manifest.get(slug, {})
        card = CardSchema.parse_obj(read_json(json_file))
        url_result = _url_check(card.source_url)
        semantic_result = _semantic_check(manifest_entry.get("keywords", []), card.issuer)
        schema_result = _schema_check(card)
        passed = all(
            (
                url_result.get("passed"),
                semantic_result.get("passed"),
                schema_result.get("passed"),
            )
        )
        status = "PASS" if passed else "FAIL"
        details = {
            "url_check": url_result,
            "semantic_check": semantic_result,
            "schema_check": schema_result,
        }
        results.append(
            VerificationResult(
                card_key=_card_key(card),
                issuer=card.issuer,
                card_name=card.card_name,
                status=status,
                details=details,
                source_path=manifest_entry.get("raw_relative_path"),
            )
        )
        LOGGER.info("Verification %s for %s", status, slug)

    html_report = _build_html_report(results)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(html_report, encoding="utf-8")
    LOGGER.info("Wrote verification report to %s", report_path)

    summary_path = report_path.with_suffix(".json")
    write_json(summary_path, {"results": [result.dict() for result in results]})
    LOGGER.info("Wrote verification summary to %s", summary_path)
