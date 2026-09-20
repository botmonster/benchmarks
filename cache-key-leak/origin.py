import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("ORIGIN_PORT", "18081"))
PRIVATE = os.environ.get("ORIGIN_PRIVATE") == "1"
HIT_LOG = os.environ.get("ORIGIN_LOG", "origin-hits.log")

NAMED = ["alice", "bob", "carol"]
HOUSEHOLDS = [f"household{n:02d}" for n in range(1, 41)]
ACCOUNTS = {f"token-{name}": name for name in NAMED + HOUSEHOLDS}


def doors_for(account):
    count = 1 + sum(map(ord, account)) % 3
    return [
        {
            "id": f"{account}-door{i}",
            "name": f"{account} garage {i}",
            "status": "closed",
        }
        for i in range(1, count + 1)
    ]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/v1/devices":
            self.send_error(404)
            return
        auth = self.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        account = ACCOUNTS.get(token)
        if account is None:
            self.send_error(401)
            return
        body = json.dumps(
            {
                "account": account,
                "doors": doors_for(account),
                "origin_time": round(time.time(), 3),
            }
        ).encode()
        with open(HIT_LOG, "a") as log:
            log.write(f"{time.strftime('%H:%M:%S')} origin answered for {account}\n")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if PRIVATE:
            self.send_header("Cache-Control", "private")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(
        f"origin listening on 127.0.0.1:{PORT} private={PRIVATE}",
        file=sys.stderr,
        flush=True,
    )
    server.serve_forever()
