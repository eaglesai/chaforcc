"""Parser registry."""
from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Dict, Type

from ccq.parsers.base import BaseParser, GenericHTMLParser, GenericPDFParser
from ccq.utils.text import slugify

LOGGER = logging.getLogger(__name__)


class ParserRegistry:
    def __init__(self) -> None:
        self._registry: Dict[str, Type[BaseParser]] = {}
        self.register(GenericHTMLParser)
        self.register(GenericPDFParser)

    def register(self, parser_cls: Type[BaseParser]) -> None:
        self._registry[parser_cls.issuer_key] = parser_cls

    def get(self, issuer_name: str, source_type: str) -> BaseParser:
        issuer_key = slugify(issuer_name)
        module_name = f"ccq.parsers.issuers.{issuer_key}"
        if issuer_key not in self._registry:
            try:
                importlib.import_module(module_name)
            except ModuleNotFoundError:
                LOGGER.debug("No custom parser found for issuer %s", issuer_name)
        parser_cls = self._registry.get(issuer_key)
        if parser_cls is None:
            parser_cls = GenericHTMLParser if source_type == "html" else GenericPDFParser
        return parser_cls()


registry = ParserRegistry()
