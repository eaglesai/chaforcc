"""Configuration helpers for the ccq CLI."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@lru_cache(maxsize=1)
def load_env(dotenv_path: Optional[Path] = None) -> None:
    """Load environment variables from a .env file if present.

    Parameters
    ----------
    dotenv_path:
        Optional override path to the .env file. When omitted the standard
        search chain used by :func:`python-dotenv.load_dotenv` is used.
    """

    if dotenv_path:
        load_dotenv(dotenv_path=dotenv_path)
    else:
        load_dotenv()


@lru_cache(maxsize=1)
def get_supabase_credentials() -> dict[str, str]:
    """Return the Supabase credentials required by the CLI.

    The values are fetched from environment variables. The method raises a
    :class:`RuntimeError` when a required variable is missing to ensure that the
    caller fails fast and the run stays auditable.
    """

    load_env()

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        missing = [name for name, value in {"SUPABASE_URL": url, "SUPABASE_SERVICE_ROLE_KEY": key}.items() if not value]
        raise RuntimeError(
            "Missing Supabase credentials. Ensure the following environment "
            f"variables are set: {', '.join(missing)}"
        )

    return {"url": url.rstrip("/"), "key": key}
