"""Shared adapter contract.

Every converter is wrapped in an Adapter so run_all.py can treat ten very
different tools identically: give it HTML and a base URL, get Markdown back.

kind is what the project claims to be, not a measured result:
  converter - hands back everything it was given, chrome included
  extractor - finds the article first, then converts only that
The boilerplate-leakage metric checks the claim.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class Adapter:
    name: str
    kind: str
    lang: str
    repo: str
    convert: Callable[[str, str], str]
    version_fn: Callable[[], str]
    ranked: bool = True
    notes: str = ""
    _version: Optional[str] = field(default=None, repr=False)

    def version(self) -> str:
        if self._version is None:
            try:
                self._version = self.version_fn()
            except Exception as exc:  # pragma: no cover
                self._version = f"unknown ({exc})"
        return self._version
