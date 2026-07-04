// Builds a ~3.3 MB JSON payload, then measures JSON.parse and JSON.stringify
// averaged over 30 iterations after a warmup. Runs unchanged on Node, Bun, Deno.
const rows = [];
for (let i = 0; i < 20000; i++) {
  rows.push({ id: i, name: 'user_' + i, email: 'u' + i + '@example.com',
    tags: ['a', 'b', 'c'], score: i * 0.7, active: i % 2 === 0,
    nested: { a: 1, b: [1, 2, 3], c: 'text text text text' } });
}
const str = JSON.stringify({ rows });
for (let i = 0; i < 5; i++) { JSON.parse(str); JSON.stringify(JSON.parse(str)); }
const N = 30;
let t0 = performance.now();
for (let i = 0; i < N; i++) JSON.parse(str);
const parseMs = (performance.now() - t0) / N;
const obj = JSON.parse(str);
t0 = performance.now();
for (let i = 0; i < N; i++) JSON.stringify(obj);
const strMs = (performance.now() - t0) / N;
console.log(`payload=${(str.length / 1048576).toFixed(1)}MB parse=${parseMs.toFixed(2)}ms stringify=${strMs.toFixed(2)}ms`);
