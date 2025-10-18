"""Implementation of the ``ccq publish`` command."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import typer

from ccq.models import CardSchema
from ccq.supabase import SupabaseRepository
from ccq.utils.io import iter_json_files, read_json

LOGGER = logging.getLogger(__name__)


def _card_key(card: CardSchema) -> str:
    return "::".join(part.lower() for part in [card.issuer, card.card_name, card.country] if part)


def publish(
    parsed_dir: Path = typer.Option(Path("data/parsed"), "--in", help="Directory containing parsed JSON files"),
    only_changed: bool = typer.Option(False, "--only-changed", help="Publish only new or changed cards"),
    promote: bool = typer.Option(False, "--promote", help="Mark published cards as approved and promote to production"),
) -> None:
    verification_summary = parsed_dir / "verification_report.json"
    if not verification_summary.exists():
        raise typer.BadParameter("Verification summary not found. Run 'ccq verify' first.")

    summary_data = read_json(verification_summary)
    results = summary_data.get("results", [])
    passed_keys = {entry["card_key"] for entry in results if entry.get("status") == "PASS"}
    failed_keys = {entry["card_key"] for entry in results if entry.get("status") != "PASS"}

    if not passed_keys:
        raise typer.Exit(code=1)

    repository = SupabaseRepository()
    supabase_index = repository.fetch_card_index() if only_changed else {}

    cards_to_publish: List[Dict] = []
    total_cards = 0
    for json_file in iter_json_files(parsed_dir):
        card = CardSchema.parse_obj(read_json(json_file))
        key = _card_key(card)
        total_cards += 1
        if key not in passed_keys:
            LOGGER.info("Skipping %s due to failed verification", key)
            continue
        if only_changed:
            supabase_card = supabase_index.get(key)
            if supabase_card and supabase_card.get("content_hash") == card.content_hash:
                LOGGER.debug("Skipping unchanged card %s", key)
                continue
        payload = card.dict()
        payload["verified_at"] = datetime.utcnow().isoformat()
        payload["approved"] = False
        cards_to_publish.append(payload)

    if not cards_to_publish:
        LOGGER.warning("No cards to publish after filtering")
        return

    repository.upsert_cards(cards_to_publish)
    LOGGER.info("Upserted %d cards into staging", len(cards_to_publish))

    if promote:
        repository.promote_cards(cards_to_publish)
        LOGGER.info("Promoted %d cards to production", len(cards_to_publish))

    counts = {
        "total_cards": total_cards,
        "published_cards": len(cards_to_publish),
        "skipped_cards": total_cards - len(cards_to_publish),
        "failed_cards": len(failed_keys),
    }
    repository.record_run(str(verification_summary), counts)
    LOGGER.info("Recorded publish run with counts %s", counts)
