#!/usr/bin/env python3
"""Generate the app icons (pure Python PNG writer, no Pillow needed)."""
import os, struct, sys, zlib
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
from pixel_td.sprite_data import tower_art, tower_pal, ENEMY_ART, ENEMY_PAL  # noqa: E402


def write_png(path, w, h, rows):
    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def render(size):
    scale = max(1, size // 14)
    px = [[(0, 0, 0, 0)] * size for _ in range(size)]
    r = size // 8
    for y in range(size):                                   # rounded dark-purple tile + gold frame
        for x in range(size):
            dx, dy = max(r - x, x - (size - 1 - r), 0), max(r - y, y - (size - 1 - r), 0)
            if dx * dx + dy * dy <= r * r:
                edge = min(x, y, size - 1 - x, size - 1 - y) < max(2, size // 40)
                px[y][x] = (255, 215, 80, 255) if edge else (34, 30, 50, 255)

    def blit(rows, pal, ox, oy, s):
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                c = pal.get(ch)
                if c:
                    for yy in range(s):
                        for xx in range(s):
                            X, Y = ox + i * s + xx, oy + j * s + yy
                            if 0 <= X < size and 0 <= Y < size:
                                px[Y][X] = (*c, 255)
    tw = tower_art("tesla")
    blit(tw, tower_pal((170, 110, 255)), (size - 10 * scale) // 2, int(size * 0.14), scale)
    g = ENEMY_ART["grunt"]
    es = max(1, scale // 2)
    blit(g, ENEMY_PAL["grunt"], int(size * 0.14), int(size * 0.66), es)
    blit(ENEMY_ART["brute"], ENEMY_PAL["brute"], int(size * 0.62), int(size * 0.66), es)
    return [[v for p in row for v in p] for row in px]


if __name__ == "__main__":
    out = os.path.join(ROOT, "packaging", "icons")
    os.makedirs(out, exist_ok=True)
    for s in (48, 128, 256):
        write_png(os.path.join(out, f"pixel-td-{s}.png"), s, s, render(s))
        print("wrote", s)
