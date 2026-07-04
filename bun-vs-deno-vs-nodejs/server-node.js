const http = require('http');
http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ hello: 'world', ts: 1234567890, ok: true }));
}).listen(3001, () => console.error('node listening 3001'));
