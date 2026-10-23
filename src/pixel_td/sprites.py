"""Builds all pixel-art surfaces procedurally (nearest-neighbour look, no image files)."""
import random
import pygame
from .config import *
from .sprite_data import *
from .towers import TOWER_TYPES
from .pathing import Path

THEMES = {
    "meadow": dict(ground=[(70, 118, 58), (62, 108, 52), (78, 128, 64), (66, 112, 56)], edge=(92, 70, 48),
                   road=(158, 120, 80), dots=[(146, 108, 70), (170, 132, 92), (136, 100, 66)],
                   deco=[(240, 240, 240), (240, 120, 160), (250, 220, 80), (130, 130, 140)],
                   bush=[(40, 84, 44), (52, 104, 54)]),
    "canyon": dict(ground=[(205, 175, 115), (196, 166, 106), (214, 186, 128), (200, 170, 110)], edge=(120, 80, 50),
                   road=(172, 122, 88), dots=[(158, 108, 74), (184, 134, 98), (146, 100, 68)],
                   deco=[(150, 110, 70), (120, 100, 80), (230, 210, 160), (110, 90, 70)],
                   bush=[(70, 130, 70), (90, 150, 80)]),
    "frozen": dict(ground=[(214, 230, 242), (204, 222, 238), (224, 238, 248), (208, 226, 240)], edge=(100, 130, 170),
                   road=(150, 178, 208), dots=[(138, 166, 198), (164, 190, 218), (128, 156, 190)],
                   deco=[(255, 255, 255), (180, 220, 255), (150, 190, 230)],
                   bush=[(130, 170, 200), (160, 200, 225)]),
    "lava": dict(ground=[(52, 36, 36), (46, 30, 30), (60, 42, 40), (50, 34, 34)], edge=(255, 110, 30),
                 road=(104, 58, 50), dots=[(90, 48, 42), (120, 66, 56), (255, 140, 40)],
                 deco=[(255, 120, 30), (255, 200, 60), (90, 70, 70)],
                 bush=[(70, 50, 50), (90, 64, 62)]),
    "void": dict(ground=[(24, 18, 42), (20, 14, 38), (30, 22, 50), (26, 18, 46)], edge=(190, 80, 230),
                 road=(66, 48, 110), dots=[(58, 40, 98), (80, 60, 130), (150, 100, 220)],
                 deco=[(255, 255, 255), (200, 160, 255), (120, 200, 255)],
                 bush=[(44, 30, 80), (60, 44, 100)]),
}
PREVIEW_SIZE = (216, 126)


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
    def __init__(self, maps):
        self.enemy = []          # [type][variant] variant: 0 normal, 1 slowed, 2 poisoned
        for art, pal in ENEMY_SPRITES:
            base = build(ENEMY_ART[art], ENEMY_PAL[pal])
            self.enemy.append([base, tint(base, (20, 60, 110)), tint(base, (0, 70, 10))])
        self.tower = [build(tower_art(tt.key), tower_pal(tt.color)) for tt in TOWER_TYPES]
        self.maps, self.previews = {}, {}
        for i, m in enumerate(maps):
            surf = self._make_map(Path(m.tiles), THEMES[m.theme], i)
            self.maps[m.key] = surf
            self.previews[m.key] = pygame.transform.scale(surf, PREVIEW_SIZE)

    def app_icon(self):
        """40x40 window icon built from the Tesla tower sprite (no image files needed)."""
        icon = pygame.Surface((40, 40), pygame.SRCALPHA)
        icon.blit(self.tower[3], (0, 0))
        return icon

    def _make_map(self, path, th, seed):
        rng = random.Random(7 + seed)
        surf = pygame.Surface((MAP_W, MAP_H))
        surf.fill(th["ground"][0])
        for _ in range(1100):
            x, y = rng.randrange(MAP_W // PX) * PX, rng.randrange(MAP_H // PX) * PX
            surf.fill(rng.choice(th["ground"][1:]), (x, y, PX, PX))
        pts = path.pts
        segs = list(zip(pts[:-1], pts[1:]))

        def seg_rect(a, b, half):
            x1, y1, x2, y2 = a[0], a[1], b[0], b[1]
            return pygame.Rect(int(min(x1, x2) - half), int(min(y1, y2) - half),
                               int(abs(x2 - x1) + 2 * half), int(abs(y2 - y1) + 2 * half))

        for a, b in segs:
            surf.fill(th["edge"], seg_rect(a, b, PATH_HALF + 4))
        for a, b in segs:
            surf.fill(th["road"], seg_rect(a, b, PATH_HALF))
        for _ in range(900):
            x, y = rng.randrange(MAP_W // PX) * PX, rng.randrange(MAP_H // PX) * PX
            if path.distance_to(x + 2, y + 2) < PATH_HALF - 2:
                surf.fill(rng.choice(th["dots"]), (x, y, PX, PX))
        for _ in range(70):                                   # flowers / pebbles / stars / embers
            x, y = rng.randrange(MAP_W // PX) * PX, rng.randrange(MAP_H // PX) * PX
            if path.distance_to(x, y) > PATH_HALF + 10:
                surf.fill(rng.choice(th["deco"]), (x, y, PX, PX))
        for _ in range(14):                                   # bushes / rocks / ice blocks
            x, y = rng.randrange(MAP_W // PX) * PX, rng.randrange(MAP_H // PX) * PX
            if path.distance_to(x + 8, y + 4) > PATH_HALF + 24:
                surf.fill(th["bush"][0], (x, y + 4, 16, 8))
                surf.fill(th["bush"][1], (x + 4, y, 8, 8))
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
