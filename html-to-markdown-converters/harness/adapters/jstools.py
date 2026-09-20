"""turndown and node-html-markdown, driven through one long-lived Node worker.

The worker stays up for the whole run, so Node startup is paid once instead of
once per page. Timings reported for these two are the worker's own hrtime
around the convert call.
"""

import atexit
import itertools
import json
import os
import subprocess

from .base import Adapter

_WORKER_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "js", "worker.mjs")
_ids = itertools.count(1)
_proc = None
_versions = {}


def _worker():
    global _proc, _versions
    if _proc is not None and _proc.poll() is None:
        return _proc
    _proc = subprocess.Popen(
        ["node", _WORKER_PATH],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=None,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )
    atexit.register(_shutdown)
    _versions = _call({"op": "versions"}).get("versions", {})
    return _proc


def _shutdown():
    if _proc is not None and _proc.poll() is None:
        try:
            _proc.stdin.write(json.dumps({"op": "quit", "id": 0}) + "\n")
            _proc.stdin.flush()
            _proc.wait(timeout=5)
        except Exception:
            _proc.kill()


def _call(payload):
    proc = _proc if payload.get("op") == "versions" else _worker()
    payload = dict(payload)
    payload["id"] = next(_ids)
    proc.stdin.write(json.dumps(payload) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError("node worker died")
    resp = json.loads(line)
    if not resp.get("ok"):
        raise RuntimeError(resp.get("error", "node worker error"))
    return resp


def _convert(tool):
    def run(html, base_url):
        return _call({"op": "convert", "tool": tool, "html": html})["markdown"]

    return run


def _version(tool):
    def get():
        _worker()
        return _versions.get(tool, "unknown")

    return get


ADAPTERS = [
    Adapter(
        name="turndown",
        kind="converter",
        lang="JavaScript",
        repo="https://github.com/mixmark-io/turndown",
        convert=_convert("turndown"),
        version_fn=_version("turndown"),
        notes="turndown-plugin-gfm enabled, which is what its own docs point you at for tables",
    ),
    Adapter(
        name="turndown (no gfm plugin)",
        kind="converter",
        lang="JavaScript",
        repo="https://github.com/mixmark-io/turndown",
        convert=_convert("turndown-bare"),
        version_fn=_version("turndown-bare"),
        ranked=False,
        notes="stock turndown with no plugins, scored to show what the plugin buys you",
    ),
    Adapter(
        name="node-html-markdown",
        kind="converter",
        lang="JavaScript",
        repo="https://github.com/crosstype/node-html-markdown",
        convert=_convert("node-html-markdown"),
        version_fn=_version("node-html-markdown"),
    ),
]
