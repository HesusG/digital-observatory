"""Tiny WOL broadcaster.

Runs as a sidecar with host networking so it can actually emit a magic packet
on the LAN (192.168.1.0/24 in our setup). Exposes:

  POST /wake          → wake the MAC in WOL_MAC env var
  POST /wake/<MAC>    → wake the MAC in the URL (override)
  GET  /healthz       → liveness

stdlib only; no third-party deps. ~50 lines.
"""
import json
import os
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer

DEFAULT_MAC = os.environ.get("WOL_MAC", "")
BROADCAST = os.environ.get("WOL_BROADCAST", "255.255.255.255")
PORT = int(os.environ.get("WOL_PORT", "9999"))


def magic_packet(mac: str) -> bytes:
    clean = mac.replace(":", "").replace("-", "").strip()
    if len(clean) != 12:
        raise ValueError(f"invalid MAC: {mac!r}")
    raw = bytes.fromhex(clean)
    return b"\xff" * 6 + raw * 16


def send_wol(mac: str) -> None:
    packet = magic_packet(mac)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # Magic packets are conventionally sent to UDP/9 (or UDP/7).
        sock.sendto(packet, (BROADCAST, 9))
    finally:
        sock.close()


class Handler(BaseHTTPRequestHandler):
    def _json(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/healthz":
            self._json(200, {"status": "ok", "default_mac": DEFAULT_MAC, "broadcast": BROADCAST})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/wake":
            mac = DEFAULT_MAC
        elif self.path.startswith("/wake/"):
            mac = self.path[len("/wake/"):]
        else:
            self._json(404, {"error": "not found"})
            return

        if not mac:
            self._json(400, {"error": "no MAC configured (set WOL_MAC env or POST /wake/<MAC>)"})
            return

        try:
            send_wol(mac)
        except ValueError as e:
            self._json(400, {"error": str(e)})
            return
        except OSError as e:
            self._json(500, {"error": f"socket error: {e}"})
            return

        self._json(200, {"status": "sent", "mac": mac, "broadcast": BROADCAST})

    def log_message(self, format, *args):  # noqa: A002
        # Cleaner default-stderr line; keep it for ops debugging.
        print(f"wol {self.address_string()} - {format % args}", flush=True)


def main():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"wol-service listening on 0.0.0.0:{PORT}, default_mac={DEFAULT_MAC!r}, broadcast={BROADCAST}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
