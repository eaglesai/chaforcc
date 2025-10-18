"""Implementation of the ``ccq crawl`` command."""
from __future__ import annotations

import logging
import mimetypes
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import requests
from requests.adapters import HTTPAdapter, Retry
import typer

from ccq.utils.hash import sha256_bytes
from ccq.utils.io import read_seed_file, write_json
from ccq.utils.text import slugify

LOGGER = logging.getLogger(__name__)


def _build_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=("GET", "HEAD"),
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _derive_extension(content_type: str | None, url: str) -> str:
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if ext:
            return ext
    ext = Path(url).suffix
    if ext:
        return ext
    return ".bin"


def crawl(
    seed_file: Path = typer.Option(..., "--in", help="Seed CSV/XLSX file with agreement URLs"),
    out_dir: Path = typer.Option(Path("data/raw"), "--out", help="Directory where artifacts will be stored"),
    fresh: bool = typer.Option(False, "--fresh", help="Delete existing artifacts before crawling"),
) -> None:
    """Fetch issuer agreements and persist the artifacts on disk."""

    if fresh and out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    session = _build_session()
    rows = read_seed_file(seed_file)

    for row in rows:
        country = row.get("Country", "").strip()
        issuer = row.get("Issuer", "").strip()
        card_program = row.get("Card/Program", "").strip()
        url = row.get("Agreement URL", "").strip()
        if not url:
            LOGGER.warning("Skipping row with missing URL: %s", row)
            continue
        slug = slugify(f"{issuer}-{card_program}")
        artifact_dir = out_dir / slug
        artifact_dir.mkdir(parents=True, exist_ok=True)
        try:
            LOGGER.info("Fetching %s", url)
            response = session.get(url, timeout=30, allow_redirects=True)
        except requests.RequestException as exc:
            LOGGER.error("Failed to fetch %s: %s", url, exc)
            failure_metadata = {
                "country": country,
                "issuer": issuer,
                "card_program": card_program,
                "source_url": url,
                "error": str(exc),
                "retrieved_at": datetime.utcnow().isoformat(),
            }
            write_json(artifact_dir / "metadata.json", failure_metadata)
            continue

        metadata: Dict[str, Optional[str]] = {
            "country": country,
            "issuer": issuer,
            "card_program": card_program,
            "source_url": url,
            "final_url": str(response.url),
            "status_code": str(response.status_code),
            "retrieved_at": datetime.utcnow().isoformat(),
        }
        headers = dict(response.headers)
        write_json(artifact_dir / "headers.json", headers)

        if response.status_code != 200:
            LOGGER.error("Non-200 response for %s: %s", url, response.status_code)
            metadata["error"] = f"HTTP {response.status_code}"
            write_json(artifact_dir / "metadata.json", metadata)
            continue

        extension = _derive_extension(response.headers.get("Content-Type"), response.url)
        filename = artifact_dir / f"artifact{extension}"
        with filename.open("wb") as f:
            f.write(response.content)
        content_hash = sha256_bytes(response.content)
        metadata["content_hash"] = content_hash
        metadata["content_length"] = str(len(response.content))
        write_json(artifact_dir / "metadata.json", metadata)

        LOGGER.info("Saved artifact %s (hash=%s)", filename, content_hash)
