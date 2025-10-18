"""Implementation of the ``ccq diff`` command."""
from __future__ import annotations

import html
import logging
from pathlib import Path
from typing import Dict, List

import typer

from ccq.models import CardSchema, DiffResult
from ccq.supabase import SupabaseRepository
from ccq.utils.io import iter_json_files, read_json, write_json

LOGGER = logging.getLogger(__name__)

CARD_FIELDS = [
    "issuer",
    "card_name",
    "country",
    "network",
    "card_type",
    "annual_fee",
    "purchase_apr",
    "cash_advance_apr",
    "fx_fee_percent",
    "grace_period_days",
    "signup_bonus",
    "earn_rates",
    "insurance",
    "eligibility",
    "other_fees",
    "source_url",
    "source_type",
    "content_hash",
]


def _card_key(card: CardSchema) -> str:
    return "::".join(part.lower() for part in [card.issuer, card.card_name, card.country] if part)


def diff(
    parsed_dir: Path = typer.Option(Path("data/parsed"), "--in", help="Directory containing parsed JSON files"),
    report_path: Path = typer.Option(Path("data/parsed/diff_report.html"), "--report", help="HTML report destination"),
    against: str = typer.Option("supabase", "--against", help="Datasource to diff against"),
) -> None:
    if against != "supabase":
        raise typer.BadParameter("Only Supabase diffing is currently supported")

    repository = SupabaseRepository()
    supabase_index = repository.fetch_card_index()

    manifest_path = parsed_dir / "manifest.json"
    manifest = {item["slug"]: item for item in read_json(manifest_path).get("items", [])} if manifest_path.exists() else {}

    new_cards: List[DiffResult] = []
    changed_cards: List[DiffResult] = []
    unchanged_cards: List[DiffResult] = []
    failed_cards: List[DiffResult] = []

    for slug, entry in manifest.items():
        if entry.get("status") != "parsed":
            failed_cards.append(
                DiffResult(
                    card_key=slug,
                    issuer=entry.get("issuer", ""),
                    card_name=entry.get("card_name", ""),
                    change_type="failed",
                    current_hash=None,
                    supabase_hash=None,
                    changes={"error": {"current": entry.get("error", "parse failure"), "supabase": None}},
                )
            )

    for json_file in iter_json_files(parsed_dir):
        card = CardSchema.parse_obj(read_json(json_file))
        key = _card_key(card)
        supabase_card = supabase_index.get(key)
        if not supabase_card:
            new_cards.append(
                DiffResult(
                    card_key=key,
                    issuer=card.issuer,
                    card_name=card.card_name,
                    change_type="new",
                    current_hash=card.content_hash,
                    supabase_hash=None,
                )
            )
            continue
        changes: Dict[str, Dict[str, object]] = {}
        for field in CARD_FIELDS:
            current_value = getattr(card, field)
            supabase_value = supabase_card.get(field)
            if isinstance(current_value, list):
                if current_value != supabase_value:
                    changes[field] = {"current": current_value, "supabase": supabase_value}
            else:
                if current_value != supabase_value:
                    changes[field] = {"current": current_value, "supabase": supabase_value}
        if not changes:
            unchanged_cards.append(
                DiffResult(
                    card_key=key,
                    issuer=card.issuer,
                    card_name=card.card_name,
                    change_type="unchanged",
                    current_hash=card.content_hash,
                    supabase_hash=supabase_card.get("content_hash"),
                )
            )
        else:
            changed_cards.append(
                DiffResult(
                    card_key=key,
                    issuer=card.issuer,
                    card_name=card.card_name,
                    change_type="changed",
                    current_hash=card.content_hash,
                    supabase_hash=supabase_card.get("content_hash"),
                    changes=changes,
                )
            )

    def _render_section(title: str, items: List[DiffResult]) -> str:
        rows = []
        for item in items:
            change_details = html.escape(str(item.changes)) if item.changes else ""
            rows.append(
                f"<tr><td>{html.escape(item.issuer)}</td><td>{html.escape(item.card_name)}</td>"
                f"<td>{html.escape(item.change_type)}</td><td>{html.escape(item.card_key)}</td>"
                f"<td>{html.escape(str(item.current_hash or ''))}</td>"
                f"<td>{html.escape(str(item.supabase_hash or ''))}</td>"
                f"<td>{change_details}</td></tr>"
            )
        body = "\n".join(rows)
        return (
            f"<h2>{html.escape(title)}</h2>"
            "<table border='1' cellspacing='0' cellpadding='4'>"
            "<tr><th>Issuer</th><th>Card</th><th>Type</th><th>Key</th><th>Current Hash</th>"
            "<th>Supabase Hash</th><th>Changes</th></tr>"
            f"{body}</table>"
        )

    html_sections = [
        _render_section("New", new_cards),
        _render_section("Changed", changed_cards),
        _render_section("Unchanged", unchanged_cards),
        _render_section("Failed", failed_cards),
    ]
    html_report = (
        "<html><head><title>Diff Report</title></head><body>"
        "<h1>Diff Report</h1>"
        + "".join(html_sections)
        + "</body></html>"
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(html_report, encoding="utf-8")
    LOGGER.info("Wrote diff report to %s", report_path)

    summary = {
        "new": [item.dict() for item in new_cards],
        "changed": [item.dict() for item in changed_cards],
        "unchanged": [item.dict() for item in unchanged_cards],
        "failed": [item.dict() for item in failed_cards],
    }
    write_json(report_path.with_suffix(".json"), summary)
