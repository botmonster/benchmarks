Deno.serve({ port: 3003 }, () =>
  new Response(JSON.stringify({ hello: 'world', ts: 1234567890, ok: true }), {
    headers: { 'Content-Type': 'application/json' },
  }),
);
console.error('deno listening 3003');
