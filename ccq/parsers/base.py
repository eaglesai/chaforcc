"""Base parsing infrastructure."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

from bs4 import BeautifulSoup
import pdfplumber

from ccq.models import CardSchema
from ccq.utils.hash import sha256_file
from ccq.utils.text import detect_keywords

LOGGER = logging.getLogger(__name__)


class ParseContext:
    def __init__(self, metadata: Dict, raw_path: Path, *, text_preview: Optional[str] = None):
        self.metadata = metadata
        self.raw_path = raw_path
        self.text_preview = text_preview


class BaseParser:
    issuer_key = "generic"

    def parse(self, context: ParseContext) -> CardSchema:
        raise NotImplementedError


class GenericHTMLParser(BaseParser):
    issuer_key = "generic_html"

    def parse(self, context: ParseContext) -> CardSchema:
        with context.raw_path.open("r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        keywords = detect_keywords(text, {"apr", "fee", "foreign transaction", context.metadata.get("issuer", "").lower()})
        extraction_notes = (
            "Generic HTML parser used. Manual review required. "
            f"Keywords detected: {', '.join(sorted(keywords)) if keywords else 'none'}."
        )

        content_hash = sha256_file(context.raw_path)
        metadata = context.metadata
        return CardSchema(
            issuer=metadata.get("issuer", ""),
            card_name=metadata.get("card_program", ""),
            country=metadata.get("country", ""),
            network=None,
            card_type=None,
            annual_fee=None,
            purchase_apr=None,
            cash_advance_apr=None,
            fx_fee_percent=None,
            grace_period_days=None,
            signup_bonus=None,
            earn_rates=[],
            insurance=[],
            eligibility=[],
            other_fees=[],
            source_url=metadata.get("final_url") or metadata.get("source_url", ""),
            source_type="html",
            content_hash=content_hash,
            extraction_notes=extraction_notes,
        )


class GenericPDFParser(BaseParser):
    issuer_key = "generic_pdf"

    def parse(self, context: ParseContext) -> CardSchema:
        text_fragments = []
        with pdfplumber.open(context.raw_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                if text:
                    text_fragments.append(text)
        text = "\n".join(text_fragments)
        keywords = detect_keywords(text, {"apr", "fee", "foreign transaction", context.metadata.get("issuer", "").lower()})
        extraction_notes = (
            "Generic PDF parser used. Manual review required. "
            f"Keywords detected: {', '.join(sorted(keywords)) if keywords else 'none'}."
        )
        content_hash = sha256_file(context.raw_path)
        metadata = context.metadata
        return CardSchema(
            issuer=metadata.get("issuer", ""),
            card_name=metadata.get("card_program", ""),
            country=metadata.get("country", ""),
            network=None,
            card_type=None,
            annual_fee=None,
            purchase_apr=None,
            cash_advance_apr=None,
            fx_fee_percent=None,
            grace_period_days=None,
            signup_bonus=None,
            earn_rates=[],
            insurance=[],
            eligibility=[],
            other_fees=[],
            source_url=metadata.get("final_url") or metadata.get("source_url", ""),
            source_type="pdf",
            content_hash=content_hash,
            extraction_notes=extraction_notes,
        )
