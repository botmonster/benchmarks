Bun.serve({
  port: 3002,
  fetch() {
    return new Response(JSON.stringify({ hello: 'world', ts: 1234567890, ok: true }), {
      headers: { 'Content-Type': 'application/json' },
    });
  },
});
console.error('bun listening 3002');
