"""Command line entry point for the ccq tool."""
from __future__ import annotations

from ccq import app as core_app


def main() -> None:
    core_app()


if __name__ == "__main__":  # pragma: no cover
    main()
