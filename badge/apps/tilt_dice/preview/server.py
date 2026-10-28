"""Loopback-only preview using the badge app's actual physics and face assets."""

import argparse
import base64
import binascii
import importlib.util
import json
import math
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import struct
from urllib.parse import urlsplit

PREVIEW = Path(__file__).resolve().parent
APP = PREVIEW.parent
spec = importlib.util.spec_from_file_location("dice_physics", APP / "physics.py")
physics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(physics)


def number(data, key, default):
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("%s must be a finite number" % key)
    return value


def decode_face(value):
    prefix = "data:image/png;base64,"
    if not isinstance(value, str) or not value.startswith(prefix):
        raise ValueError("Faces must be PNG data URLs")
    data = base64.b64decode(value[len(prefix):], validate=True)
    if len(data) > 20000 or data[:16] != b"\x89PNG\r\n\x1a\n\0\0\0\rIHDR":
        raise ValueError("Invalid or oversized PNG")
    if struct.unpack(">II", data[16:24]) != (48, 48):
        raise ValueError("Faces must be 48x48 pixels")
    offset = 8
    ended = False
    while offset + 12 <= len(data):
        size = struct.unpack(">I", data[offset:offset + 4])[0]
        end = offset + size + 12
        if end > len(data):
            raise ValueError("Truncated PNG")
        payload = data[offset + 4:end - 4]
        crc = struct.unpack(">I", data[end - 4:end])[0]
        if binascii.crc32(payload) & 0xFFFFFFFF != crc:
            raise ValueError("Corrupt PNG")
        offset = end
        if payload[:4] == b"IEND":
            ended = offset == len(data)
            break
    if not ended:
        raise ValueError("Incomplete PNG")
    return data


class Handler(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass

    def reply(self, status, data, content_type="application/json"):
        if content_type == "application/json":
            data = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.headers.get("Host") != "127.0.0.1:%d" % self.server.server_port:
            self.reply(403, {"error": "Use the loopback preview URL"})
            return
        path = urlsplit(self.path).path
        if path == "/":
            self.reply(200, (PREVIEW / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif path in ["/assets/%d.png" % i for i in range(1, 7)]:
            self.reply(200, (APP / path.lstrip("/")).read_bytes(), "image/png")
        else:
            self.reply(404, {"error": "Not found"})

    def do_POST(self):
        expected = "127.0.0.1:%d" % self.server.server_port
        if self.headers.get("Host") != expected or self.headers.get("Origin") != "http://" + expected:
            self.reply(403, {"error": "Only this local preview can change the app"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 180000:
                raise ValueError("Request size must be between 1 and 180000 bytes")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Expected a JSON object")
            if self.path == "/step":
                dt = number(data, "dt", 0)
                gx, gy = number(data, "gx", 0), number(data, "gy", 1)
                action = data.get("action")
                if action not in (None, "roll", "add", "remove"):
                    raise ValueError("Unknown dice action")
                if action == "roll":
                    self.server.tray.roll()
                elif action == "add":
                    self.server.tray.add()
                elif action == "remove":
                    self.server.tray.remove()
                self.server.tray.step(dt, gx, gy)
                self.reply(200, {"faces": self.server.tray.faces(),
                                 "count": len(self.server.tray.dice)})
            elif self.path == "/faces":
                faces = data.get("faces")
                if not isinstance(faces, list) or not 1 <= len(faces) <= 6:
                    raise ValueError("Choose between one and six photos")
                decoded = [decode_face(value) for value in faces]
                for i in range(6):
                    target = APP / "assets" / ("%d.png" % (i + 1))
                    temporary = target.with_suffix(".png.tmp")
                    try:
                        temporary.write_bytes(decoded[i % len(decoded)])
                        temporary.replace(target)
                    finally:
                        temporary.unlink(missing_ok=True)
                self.reply(200, {"saved": 6})
            else:
                self.reply(404, {"error": "Not found"})
        except (ValueError, binascii.Error, UnicodeError) as error:
            self.reply(400, {"error": str(error)})
        except OSError as error:
            print("Preview file error: %s" % error, flush=True)
            self.reply(500, {"error": "Could not save face images: %s" % error})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = HTTPServer(("127.0.0.1", args.port), Handler)
    server.tray = physics.DiceTray()
    print("Tilt Dice preview: http://127.0.0.1:%d" % server.server_port, flush=True)
    print("Local only. No badge access. Photos stay in this project.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
