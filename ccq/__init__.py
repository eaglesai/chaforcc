"""ccq package entry point."""
from __future__ import annotations

from typer import Typer

from ccq.commands import crawl, diff, parse, publish, verify
from ccq.logging import configure_logging

configure_logging()

app = Typer(add_completion=False)
app.command()(crawl)
app.command()(parse)
app.command()(verify)
app.command()(diff)
app.command()(publish)

__all__ = ["app"]
