"""Registry of every adapter the benchmark knows about."""

from .base import Adapter
from .clitools import ADAPTERS as _CLI
from .jstools import ADAPTERS as _JS
from .pytools import ADAPTERS as _PY

ALL = _JS + _PY + _CLI

RANKED = [a for a in ALL if a.ranked]

BY_NAME = {a.name: a for a in ALL}

__all__ = ["Adapter", "ALL", "RANKED", "BY_NAME"]
