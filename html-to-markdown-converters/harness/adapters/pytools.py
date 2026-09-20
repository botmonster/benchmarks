"""The five Python tools, called in-process with their documented defaults."""

import importlib.metadata as md

from .base import Adapter


def _dist_version(dist):
    try:
        return md.version(dist)
    except md.PackageNotFoundError:
        return "unknown"


def _markdownify(html, base_url):
    from markdownify import markdownify

    return markdownify(html, heading_style="ATX", bullets="-")


def _html2text(html, base_url):
    """Library defaults, except body_width.

    html2text hard-wraps at 78 columns out of the box, which rewraps every
    paragraph and breaks tables. Setting body_width to 0 turns wrapping off;
    everything else is left as shipped.
    """
    import html2text

    h = html2text.HTML2Text(baseurl=base_url)
    h.body_width = 0
    return h.handle(html)


def _html_to_markdown(html, base_url):
    from html_to_markdown import ConversionOptions, convert

    options = ConversionOptions(heading_style="atx", bullets="-", extract_metadata=False)
    return convert(html, options).content


def _trafilatura(html, base_url):
    import trafilatura

    out = trafilatura.extract(
        html,
        output_format="markdown",
        include_tables=True,
        include_links=True,
        include_images=True,
        include_formatting=True,
        include_comments=False,
        url=base_url,
    )
    return out or ""


def _markitdown(html, base_url):
    import io

    from markitdown import MarkItDown, StreamInfo

    converter = MarkItDown(enable_plugins=False)
    stream = io.BytesIO(html.encode("utf-8"))
    info = StreamInfo(extension=".html", mimetype="text/html", charset="utf-8", url=base_url)
    return converter.convert_stream(stream, stream_info=info).markdown


ADAPTERS = [
    Adapter(
        name="markdownify",
        kind="converter",
        lang="Python",
        repo="https://github.com/matthewwithanm/python-markdownify",
        convert=_markdownify,
        version_fn=lambda: _dist_version("markdownify"),
    ),
    Adapter(
        name="html2text",
        kind="converter",
        lang="Python",
        repo="https://github.com/Alir3z4/html2text",
        convert=_html2text,
        version_fn=lambda: _dist_version("html2text"),
    ),
    Adapter(
        name="html-to-markdown (py)",
        kind="converter",
        lang="Python",
        repo="https://github.com/xberg-io/html-to-markdown",
        convert=_html_to_markdown,
        version_fn=lambda: _dist_version("html-to-markdown"),
    ),
    Adapter(
        name="trafilatura",
        kind="extractor",
        lang="Python",
        repo="https://github.com/adbar/trafilatura",
        convert=_trafilatura,
        version_fn=lambda: _dist_version("trafilatura"),
    ),
    Adapter(
        name="markitdown",
        kind="extractor",
        lang="Python",
        repo="https://github.com/microsoft/markitdown",
        convert=_markitdown,
        version_fn=lambda: _dist_version("markitdown"),
    ),
]
