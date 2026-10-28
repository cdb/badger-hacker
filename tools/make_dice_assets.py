"""Generate original pip textures and a cube icon without imaging dependencies."""

import math
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "badge" / "apps" / "tilt_dice"
COLORS = ((222, 243, 152), (116, 212, 236), (247, 159, 189),
          (250, 198, 113), (183, 166, 244), (117, 218, 179))
PIPS = (
    ((24, 24),),
    ((13, 13), (35, 35)),
    ((13, 13), (24, 24), (35, 35)),
    ((13, 13), (35, 13), (13, 35), (35, 35)),
    ((13, 13), (35, 13), (24, 24), (13, 35), (35, 35)),
    ((13, 12), (35, 12), (13, 24), (35, 24), (13, 36), (35, 36)),
)


def chunk(kind, data):
    return (struct.pack(">I", len(data)) + kind + data +
            struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))


def png(pixels, palette):
    size = len(pixels)
    raw = b"".join(b"\0" + bytes(row) for row in pixels)
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 3, 0, 0, 0)) +
            chunk(b"PLTE", bytes(channel for rgb in palette for channel in rgb)) +
            chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def make_assets():
    assets = APP / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for i, pips in enumerate(PIPS):
        pixels = [[0] * 48 for _ in range(48)]
        for y in range(48):
            for x in range(48):
                if x < 3 or x >= 45 or y < 3 or y >= 45:
                    pixels[y][x] = 2
                if any((x - px) ** 2 + (y - py) ** 2 <= 16 for px, py in pips):
                    pixels[y][x] = 1
        path = assets / ("%d.png" % (i + 1))
        if path.exists():
            raise FileExistsError("Refusing to overwrite %s" % path)
        path.write_bytes(png(pixels, (COLORS[i], (25, 35, 53), (244, 246, 232))))

    pixels = [[0] * 48 for _ in range(48)]
    for y in range(6, 43):
        for x in range(5, 43):
            dx = x - 24
            if 6 <= y <= 24 and abs(dx) <= (y - 6) * 2:
                pixels[y][x] = 1
            if 18 <= y <= 33 and abs(dx) <= 18:
                pixels[y][x] = 2 if dx < 0 else 3
            if 33 < y <= 43 and abs(dx) <= (43 - y) * 1.8:
                pixels[y][x] = 2 if dx < 0 else 3
    for px, py in ((24, 15), (14, 26), (14, 32), (32, 25), (32, 31), (32, 37)):
        for y in range(py - 2, py + 3):
            for x in range(px - 2, px + 3):
                if math.hypot(x - px, y - py) <= 1.8:
                    pixels[y][x] = 0
    (APP / "icon.png").write_bytes(png(
        pixels, ((13, 18, 30), (222, 243, 152), (116, 212, 236), (183, 166, 244))))


if __name__ == "__main__":
    make_assets()
