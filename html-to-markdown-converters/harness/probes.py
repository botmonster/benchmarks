"""The probe DSL: small, exact assertions about one Markdown output.

A probe names an HTML feature that exists in a specific fixture and states what
correct Markdown for it looks like. Ten tools are checked against the same
probe, so a failure is attributable to a feature rather than to a vague
"quality" score.

Probe fields:
  id          unique within the page
  feature     tables | code | lists | links | images | inline | headings |
              escaping | footnotes | math | entities | boilerplate | structure
  type        one of the PROBE_TYPES below
  weight      default 1
  applies_to  all (default) | converter | extractor
  invert_for  a kind whose expectation is reversed, used by boilerplate probes
  note        free text shown in the report when the probe fails
"""

import re
import unicodedata

FEATURES = [
    "headings",
    "tables",
    "code",
    "lists",
    "links",
    "images",
    "inline",
    "escaping",
    "footnotes",
    "math",
    "entities",
    "structure",
    "boilerplate",
]


def normalize(text):
    """Collapse whitespace and unify unicode so probes compare content, not layout."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace(" ", " ").replace("​", "")
    return re.sub(r"[ \t]+", " ", text)


def _flat(text):
    return re.sub(r"\s+", " ", normalize(text)).strip()


ESCAPED = re.compile(r"\\([\\`*_{}\[\]()#+\-.!|<>~=\"'])")


def _content(text):
    """Text as the reader sees it: whitespace collapsed and backslash escapes undone.

    A tool that writes \\- instead of - produced the same character, so content
    probes must not treat escaping as a difference. Probes that test escaping
    itself (absent, regex, escape) read the raw output instead.
    """
    return _flat(ESCAPED.sub(r"\1", normalize(text)))


def _tables(md):
    """Yield each pipe table in the output as a list of rows of stripped cells."""
    rows, table = [], []
    for line in md.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.count("|") >= 2:
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{1,}:?", c) for c in cells if c):
                continue
            table.append(cells)
        elif table:
            rows.append(table)
            table = []
    if table:
        rows.append(table)
    return rows


def _fences(md):
    """Yield (language, body) for every fenced code block."""
    out = []
    lang = None
    body = []
    inside = False
    fence = None
    for line in md.splitlines():
        match = re.match(r"^(\s*)(`{3,}|~{3,})(.*)$", line)
        if match and not inside:
            inside = True
            fence = match.group(2)[0]
            lang = match.group(3).strip() or None
            body = []
            continue
        if inside and re.match(rf"^\s*{re.escape(fence)}{{3,}}\s*$", line):
            out.append((lang, "\n".join(body)))
            inside = False
            continue
        if inside:
            body.append(line)
    if inside:
        out.append((lang, "\n".join(body)))
    return out


def _indented_code(md):
    """Four-space indented blocks, which html2text and others emit instead of fences."""
    blocks, current = [], []
    for line in md.splitlines():
        if line.startswith("    ") and line.strip():
            current.append(line[4:])
        elif current and not line.strip():
            current.append("")
        elif current:
            blocks.append("\n".join(current).strip("\n"))
            current = []
    if current:
        blocks.append("\n".join(current).strip("\n"))
    return blocks


# --- probe implementations -------------------------------------------------


def p_contains(md, args):
    return _content(args["text"]) in _content(md)


INLINE_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
INLINE_MARKS = re.compile(r"[`*_~]")


def _prose(text):
    """Text with inline markup removed, for asserting prose and code signatures.

    Tools disagree wildly about how to mark up a Python signature: one writes
    _coro_, another `coro`, a third leaves it bare. All three carry the same
    sentence, so prose probes compare what is left once the markup is gone.
    """
    text = ESCAPED.sub(r"\1", normalize(text))
    text = INLINE_LINK.sub(r"\1", text)
    text = INLINE_MARKS.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def p_prose(md, args):
    return _prose(args["text"]) in _prose(md)


def p_absent(md, args):
    return _flat(args["text"]) not in _flat(md)


def p_regex(md, args):
    return re.search(args["pattern"], normalize(md), re.MULTILINE | re.DOTALL) is not None


def p_not_regex(md, args):
    return re.search(args["pattern"], normalize(md), re.MULTILINE | re.DOTALL) is None


HEADING_NOISE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")


def p_heading(md, args):
    """A heading at the right level whose text contains the expected words.

    Containment, not equality: many generators wrap the heading text in a self
    link or append a permalink glyph, and neither changes the heading.
    """
    level = args["level"]
    text = re.sub(r"[`*_]", "", _content(args["text"]))
    for line in normalize(md).splitlines():
        match = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line.strip())
        if not match or len(match.group(1)) != level:
            continue
        found = _content(HEADING_NOISE.sub(r"\1", match.group(2)))
        found = re.sub(r"[`*_]", "", found).strip("¶ \u00b6")
        if text and text in found:
            return True
    return False


def p_table(md, args):
    want_cells = [_content(c) for c in args.get("cells", [])]
    min_rows = args.get("min_rows", 1)
    for table in _tables(md):
        if len(table) < min_rows:
            continue
        flat = {_content(c) for row in table for c in row}
        if all(any(w == c or (w and w in c) for c in flat) for w in want_cells):
            return True
    return False


def p_fence(md, args):
    want = _content(args["body"])
    want_lang = args.get("lang")
    for lang, body in _fences(md):
        if want and want not in _content(body):
            continue
        if want_lang and (lang or "").lower() != want_lang.lower():
            continue
        return True
    return False


def p_code_block(md, args):
    """Code kept as a block, fenced or indented, language ignored."""
    want = _content(args["body"])
    for _, body in _fences(md):
        if want in _content(body):
            return True
    for body in _indented_code(md):
        if want in _content(body):
            return True
    return False


def p_link(md, args):
    text = re.escape(_content(args.get("text", "")).strip()) if args.get("text") else r"[^\]]*"
    href = args["href"]
    pattern = rf"\[{text}\]\(\s*<?[^)\s]*{re.escape(href)}[^)\s]*>?"
    if re.search(pattern, _content(md)):
        return True
    if args.get("allow_reference"):
        return bool(re.search(rf"\]:\s*<?{re.escape(href)}", md))
    return False


def p_image(md, args):
    alt = re.escape(_content(args.get("alt", ""))) if args.get("alt") else r"[^\]]*"
    src = re.escape(args["src"]) if args.get("src") else r"[^)\s]*"
    return bool(re.search(rf"!\[{alt}\]\(\s*<?[^)\s]*{src}", _content(md)))


def p_escape(md, args):
    """A Markdown-special character in body prose must not read as markup."""
    return bool(re.search(args["pattern"], normalize(md)))


def p_order(md, args):
    flat = _content(md)
    first, second = _content(args["first"]), _content(args["second"])
    i, j = flat.find(first), flat.find(second)
    return i != -1 and j != -1 and i < j


def p_list_nesting(md, args):
    """A child bullet must be indented under its parent, not flattened."""
    parent, child = _content(args["parent"]), _content(args["child"])
    lines = normalize(md).splitlines()
    for idx, line in enumerate(lines):
        match = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", line)
        if not match or parent not in _content(match.group(3)):
            continue
        indent = len(match.group(1))
        for nxt in lines[idx + 1 : idx + 12]:
            sub = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", nxt)
            if not sub:
                continue
            if len(sub.group(1)) > indent and child in _content(sub.group(3)):
                return True
            if len(sub.group(1)) <= indent:
                break
    return False


PROBE_TYPES = {
    "contains": p_contains,
    "prose": p_prose,
    "absent": p_absent,
    "regex": p_regex,
    "not_regex": p_not_regex,
    "heading": p_heading,
    "table": p_table,
    "fence": p_fence,
    "code_block": p_code_block,
    "link": p_link,
    "image": p_image,
    "escape": p_escape,
    "order": p_order,
    "list_nesting": p_list_nesting,
}


def applies(probe, kind):
    scope = probe.get("applies_to", "all")
    return scope == "all" or scope == kind


def evaluate(probe, md, kind):
    """Return True/False, honouring invert_for so extractors are not punished
    for dropping the chrome they exist to drop."""
    fn = PROBE_TYPES[probe["type"]]
    result = bool(fn(md, probe.get("args", {})))
    if probe.get("invert_for") == kind:
        return not result
    return result
