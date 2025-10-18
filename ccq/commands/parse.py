"""Implementation of the ``ccq parse`` command."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Set

import typer
from bs4 import BeautifulSoup
import pdfplumber

from ccq.models import CardSchema
from ccq.parsers import registry
from ccq.parsers.base import ParseContext
from ccq.utils.io import iter_artifact_directories, read_json, write_json
from ccq.utils.text import detect_keywords

LOGGER = logging.getLogger(__name__)


def _extract_keywords(path: Path, source_type: str, issuer: str) -> Set[str]:
    issuer_keyword = issuer.lower()
    if source_type == "pdf":
        text_fragments = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                if text:
                    text_fragments.append(text)
        text = "\n".join(text_fragments)
    else:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
    keywords = detect_keywords(text, {"apr", "fees", "foreign transaction", issuer_keyword})
    return keywords


def parse(
    raw_dir: Path = typer.Option(Path("data/raw"), "--raw", help="Directory with crawled artifacts"),
    out_dir: Path = typer.Option(Path("data/parsed"), "--out", help="Directory to write parsed JSON files"),
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest: List[Dict] = []

    for artifact_dir in iter_artifact_directories(raw_dir):
        metadata_path = artifact_dir / "metadata.json"
        if not metadata_path.exists():
            LOGGER.warning("Skipping %s without metadata", artifact_dir)
            continue
        metadata = dict(read_json(metadata_path))
        if metadata.get("error"):
            LOGGER.warning("Skipping failed artifact %s: %s", artifact_dir, metadata["error"])
            continue
        source_url = metadata.get("final_url") or metadata.get("source_url")
        artifact_file = None
        for candidate in artifact_dir.iterdir():
            if candidate.name.startswith("artifact") and candidate.is_file():
                artifact_file = candidate
                break
        if artifact_file is None:
            LOGGER.warning("No artifact file found for %s", artifact_dir)
            continue
        source_type = "pdf" if artifact_file.suffix.lower() == ".pdf" else "html"
        parser = registry.get(metadata.get("issuer", ""), source_type)
        context = ParseContext(metadata=metadata, raw_path=artifact_file)
        try:
            card_schema = parser.parse(context)
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.exception("Parser failed for %s: %s", artifact_dir, exc)
            failure = {
                "slug": artifact_dir.name,
                "source_url": source_url,
                "status": "failed",
                "error": str(exc),
            }
            manifest.append(failure)
            continue

        card_schema = CardSchema.parse_obj(card_schema.dict())
        keywords = sorted(_extract_keywords(artifact_file, source_type, card_schema.issuer))

        output_path = out_dir / f"{artifact_dir.name}.json"
        write_json(output_path, card_schema.dict())

        manifest.append(
            {
                "slug": artifact_dir.name,
                "issuer": card_schema.issuer,
                "card_name": card_schema.card_name,
                "country": card_schema.country,
                "source_url": card_schema.source_url,
                "content_hash": card_schema.content_hash,
                "source_type": card_schema.source_type,
                "keywords": keywords,
                "raw_relative_path": str(artifact_file.relative_to(raw_dir)),
                "status": "parsed",
            }
        )
        LOGGER.info("Parsed %s -> %s", artifact_dir.name, output_path)

    write_json(out_dir / "manifest.json", {"items": manifest})
    LOGGER.info("Wrote manifest with %d entries", len(manifest))
