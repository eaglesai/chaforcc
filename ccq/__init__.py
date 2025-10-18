"""ccq package entry point."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from typer import Option, Typer

from ccq.logging import configure_logging

if TYPE_CHECKING:  # pragma: no cover - imported for static analysis only
    from ccq.commands import crawl as _crawl
    from ccq.commands import diff as _diff
    from ccq.commands import parse as _parse
    from ccq.commands import publish as _publish
    from ccq.commands import verify as _verify


configure_logging()

app = Typer(add_completion=False)


@app.command()
def crawl(
    seed_file: Path = Option(..., "--in", help="Seed CSV/XLSX file with agreement URLs"),
    out_dir: Path = Option(Path("data/raw"), "--out", help="Directory where artifacts will be stored"),
    fresh: bool = Option(False, "--fresh", help="Delete existing artifacts before crawling"),
) -> None:
    """Fetch issuer agreements and persist the artifacts on disk."""

    from ccq.commands.crawl import crawl as _crawl_command

    _crawl_command(seed_file=seed_file, out_dir=out_dir, fresh=fresh)


@app.command()
def parse(
    raw_dir: Path = Option(Path("data/raw"), "--raw", help="Directory with crawled artifacts"),
    out_dir: Path = Option(Path("data/parsed"), "--out", help="Directory to write parsed JSON files"),
) -> None:
    """Parse crawled artifacts into normalized card schemas."""

    from ccq.commands.parse import parse as _parse_command

    _parse_command(raw_dir=raw_dir, out_dir=out_dir)


@app.command()
def verify(
    parsed_dir: Path = Option(Path("data/parsed"), "--in", help="Directory containing parsed JSON files"),
    report_path: Path = Option(
        Path("data/parsed/verification_report.html"),
        "--report",
        help="HTML report destination",
    ),
) -> None:
    """Verify parsed card schemas and produce a QA report."""

    from ccq.commands.verify import verify as _verify_command

    _verify_command(parsed_dir=parsed_dir, report_path=report_path)


@app.command()
def diff(
    parsed_dir: Path = Option(Path("data/parsed"), "--in", help="Directory containing parsed JSON files"),
    report_path: Path = Option(
        Path("data/parsed/diff_report.html"),
        "--report",
        help="HTML report destination",
    ),
    against: str = Option("supabase", "--against", help="Datasource to diff against"),
) -> None:
    """Compare parsed cards against an external datasource."""

    from ccq.commands.diff import diff as _diff_command

    _diff_command(parsed_dir=parsed_dir, report_path=report_path, against=against)


@app.command()
def publish(
    parsed_dir: Path = Option(Path("data/parsed"), "--in", help="Directory containing parsed JSON files"),
    only_changed: bool = Option(False, "--only-changed", help="Publish only new or changed cards"),
    promote: bool = Option(False, "--promote", help="Mark published cards as approved and promote to production"),
) -> None:
    """Publish verified cards to Supabase staging (and optionally production)."""

    from ccq.commands.publish import publish as _publish_command

    _publish_command(parsed_dir=parsed_dir, only_changed=only_changed, promote=promote)


__all__ = ["app"]
