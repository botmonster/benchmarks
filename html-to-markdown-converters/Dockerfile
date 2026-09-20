ARG GO_VERSION=1.25
ARG RUST_VERSION=1.90

FROM golang:${GO_VERSION}-bookworm AS go-builder
ARG HTML_TO_MARKDOWN_GO_VERSION=v2.5.2
RUN GOBIN=/out go install github.com/JohannesKaufmann/html-to-markdown/v2/cli/html2markdown@${HTML_TO_MARKDOWN_GO_VERSION}

FROM rust:${RUST_VERSION}-bookworm AS rust-builder
ARG HTMD_CLI_VERSION=0.5.1
RUN cargo install htmd-cli --version ${HTMD_CLI_VERSION} --root /out --locked

FROM python:3.12-slim-bookworm
ARG NODE_MAJOR=22
ARG PANDOC_VERSION=3.11
ARG TURNDOWN_VERSION=7.2.4
ARG NODE_HTML_MARKDOWN_VERSION=2.0.0
ARG MARKDOWNIFY_VERSION=1.2.3
ARG HTML2TEXT_VERSION=2025.4.15
ARG HTML_TO_MARKDOWN_PY_VERSION=3.14.3
ARG TRAFILATURA_VERSION=2.2.0
ARG MARKITDOWN_VERSION=0.1.7
ARG LXML_VERSION=6.1.3
ARG BEAUTIFULSOUP_VERSION=4.15.0
ARG PYYAML_VERSION=6.0.3
ARG CSSSELECT_VERSION=1.5.0

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NODE_PATH=/bench/node_modules

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl xz-utils \
 && curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && curl -fsSL -o /tmp/pandoc.tar.gz \
      "https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/pandoc-${PANDOC_VERSION}-linux-amd64.tar.gz" \
 && tar -xzf /tmp/pandoc.tar.gz -C /tmp \
 && mv "/tmp/pandoc-${PANDOC_VERSION}/bin/pandoc" /usr/local/bin/pandoc \
 && rm -rf /tmp/pandoc.tar.gz "/tmp/pandoc-${PANDOC_VERSION}" \
 && apt-get purge -y xz-utils \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

COPY --from=go-builder /out/html2markdown /usr/local/bin/html2markdown
COPY --from=rust-builder /out/bin/htmd /usr/local/bin/htmd

RUN pip install --no-cache-dir \
      "markdownify==${MARKDOWNIFY_VERSION}" \
      "html2text==${HTML2TEXT_VERSION}" \
      "html-to-markdown==${HTML_TO_MARKDOWN_PY_VERSION}" \
      "trafilatura==${TRAFILATURA_VERSION}" \
      "markitdown==${MARKITDOWN_VERSION}" \
      "lxml==${LXML_VERSION}" \
      "beautifulsoup4==${BEAUTIFULSOUP_VERSION}" \
      "PyYAML==${PYYAML_VERSION}" \
      "cssselect==${CSSSELECT_VERSION}"

WORKDIR /bench
RUN npm install --no-audit --no-fund --omit=dev \
      "turndown@${TURNDOWN_VERSION}" \
      "turndown-plugin-gfm@1.0.2" \
      "node-html-markdown@${NODE_HTML_MARKDOWN_VERSION}" \
 && npm cache clean --force

COPY harness /bench/harness

ENTRYPOINT ["python3"]
