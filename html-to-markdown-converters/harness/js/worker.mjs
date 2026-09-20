// Persistent converter worker. Reads newline-delimited JSON requests on stdin,
// writes newline-delimited JSON responses on stdout. Kept alive for the whole
// run so Node startup is not charged to every page.
import { createInterface } from 'node:readline';
import TurndownService from 'turndown';
import { gfm } from 'turndown-plugin-gfm';
import { NodeHtmlMarkdown } from 'node-html-markdown';

const turndownGfm = new TurndownService({
  headingStyle: 'atx',
  codeBlockStyle: 'fenced',
  bulletListMarker: '-',
});
turndownGfm.use(gfm);

const turndownBare = new TurndownService({
  headingStyle: 'atx',
  codeBlockStyle: 'fenced',
  bulletListMarker: '-',
});

const nhm = new NodeHtmlMarkdown({ bulletMarker: '-', codeBlockStyle: 'fenced' });

const { createRequire } = await import('node:module');
const require = createRequire(import.meta.url);
const pkgVersion = (name) => {
  try {
    return require(`${name}/package.json`).version;
  } catch {
    return 'unknown';
  }
};
const versions = {
  turndown: pkgVersion('turndown'),
  'turndown-bare': pkgVersion('turndown'),
  'node-html-markdown': pkgVersion('node-html-markdown'),
  node: process.versions.node,
};

const converters = {
  turndown: (html) => turndownGfm.turndown(html),
  'turndown-bare': (html) => turndownBare.turndown(html),
  'node-html-markdown': (html) => nhm.translate(html),
};

const rl = createInterface({ input: process.stdin, crlfDelay: Infinity });

for await (const line of rl) {
  if (!line.trim()) continue;
  const req = JSON.parse(line);
  if (req.op === 'versions') {
    process.stdout.write(JSON.stringify({ id: req.id, ok: true, versions }) + '\n');
    continue;
  }
  if (req.op === 'quit') break;
  const fn = converters[req.tool];
  if (!fn) {
    process.stdout.write(JSON.stringify({ id: req.id, ok: false, error: `unknown tool ${req.tool}` }) + '\n');
    continue;
  }
  try {
    const t0 = process.hrtime.bigint();
    const md = fn(req.html);
    const t1 = process.hrtime.bigint();
    process.stdout.write(
      JSON.stringify({ id: req.id, ok: true, ms: Number(t1 - t0) / 1e6, markdown: md }) + '\n'
    );
  } catch (err) {
    process.stdout.write(JSON.stringify({ id: req.id, ok: false, error: String(err && err.stack || err) }) + '\n');
  }
}
