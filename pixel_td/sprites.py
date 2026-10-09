"""Builds all pixel-art surfaces procedurally (nearest-neighbour look, no image files)."""
import random
import pygame
from .config import *
from .sprite_data import *
from .towers import TOWER_TYPES


def build(rows, pal, scale=PX):
    w, h = len(rows[0]), len(rows)
    assert all(len(r) == w for r in rows), "ragged sprite"
    s = pygame.Surface((w * scale, h * scale), pygame.SRCALPHA)
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            c = pal.get(ch)
            if c:
                s.fill(c, (x * scale, y * scale, scale, scale))
    return s


def tint(surf, rgb):
    s = surf.copy()
    s.fill(rgb, special_flags=pygame.BLEND_RGB_ADD)
    return s


class Sprites:
    def __init__(self, path):
        self.enemy = []          # [type][variant] variant: 0 normal, 1 slowed, 2 poisoned
        for k in ENEMY_ORDER:
            base = build(ENEMY_ART[k], ENEMY_PAL[k])
            self.enemy.append([base, tint(base, (20, 60, 110)), tint(base, (0, 70, 10))])
        self.tower = [build(tower_art(tt.key), tower_pal(tt.color)) for tt in TOWER_TYPES]
        self.map = self._make_map(path)

    def _make_map(self, path):
        rng = random.Random(7)
        surf = pygame.Surface((MAP_W, MAP_H))
        surf.fill((70, 118, 58))
        for _ in range(1100):
            x, y = rng.randrange(MAP_W // PX) * PX, rng.randrange(MAP_H // PX) * PX
            d = rng.choice([(62, 108, 52), (78, 128, 64), (66, 112, 56)])
            surf.fill(d, (x, y, PX, PX))
        pts = path.pts
        segs = list(zip(pts[:-1], pts[1:]))

        def seg_rect(a, b, half):
            x1, y1, x2, y2 = a[0], a[1], b[0], b[1]
            return pygame.Rect(int(min(x1, x2) - half), int(min(y1, y2) - half),
                               int(abs(x2 - x1) + 2 * half), int(abs(y2 - y1) + 2 * half))

        for a, b in segs:
            surf.fill((92, 70, 48), seg_rect(a, b, PATH_HALF + 4))
        for a, b in segs:
            surf.fill((158, 120, 80), seg_rect(a, b, PATH_HALF))
        for _ in range(900):
            x, y = rng.randrange(MAP_W // PX) * PX, rng.randrange(MAP_H // PX) * PX
            if path.distance_to(x + 2, y + 2) < PATH_HALF - 2:
                surf.fill(rng.choice([(146, 108, 70), (170, 132, 92), (136, 100, 66)]), (x, y, PX, PX))
        for _ in range(70):                                   # flowers / pebbles
            x, y = rng.randrange(MAP_W // PX) * PX, rng.randrange(MAP_H // PX) * PX
            if path.distance_to(x, y) > PATH_HALF + 10:
                c = rng.choice([(240, 240, 240), (240, 120, 160), (250, 220, 80), (130, 130, 140)])
                surf.fill(c, (x, y, PX, PX))
        for _ in range(14):                                   # bushes
            x, y = rng.randrange(MAP_W // PX) * PX, rng.randrange(MAP_H // PX) * PX
            if path.distance_to(x + 8, y + 4) > PATH_HALF + 24:
                surf.fill((40, 84, 44), (x, y + 4, 16, 8))
                surf.fill((52, 104, 54), (x + 4, y, 8, 8))
        # portal (entrance)
        py = int(pts[0][1])
        surf.fill((60, 40, 90), (0, py - 30, 12, 60))
        surf.fill((150, 90, 230), (0, py - 26, 8, 52))
        surf.fill((230, 190, 255), (0, py - 12, 4, 24))
        # castle (exit / base)
        ey = int(pts[-1][1])
        cx, cy = MAP_W - 56, ey - 30
        surf.fill((40, 40, 56), (cx - 4, cy - 4, 64, 68))
        surf.fill((150, 150, 168), (cx, cy + 12, 56, 48))
        for k in range(0, 56, 16):
            surf.fill((150, 150, 168), (cx + k, cy, 8, 12))
        surf.fill((110, 110, 128), (cx, cy + 44, 56, 16))
        surf.fill((90, 60, 40), (cx + 36, cy + 30, 16, 30))
        surf.fill((200, 60, 60), (cx + 8, cy + 20, 8, 12))
        surf.fill((255, 220, 90), (cx + 24, cy + 20, 4, 4))
        return surf
