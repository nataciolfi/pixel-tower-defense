"""World rendering: map, enemies (batched blits), towers, effects, overlays."""
import numpy as np
import pygame
from .config import *
from .towers import TOWER_TYPES
from .enemies import T_ISBOSS

MAP_RECT = pygame.Rect(MAP_X, MAP_Y, MAP_W, MAP_H)


class WorldRenderer:
    def __init__(self, sprites, fonts):
        self.sp = sprites
        self.f = fonts
        self.half = [(s[0].get_width() // 2, s[0].get_height() // 2) for s in sprites.enemy]
        self.leak_surf = pygame.Surface((MAP_W, MAP_H), pygame.SRCALPHA)
        self.leak_surf.fill((255, 30, 30, 70))
        self.frz_surf = pygame.Surface((MAP_W, MAP_H), pygame.SRCALPHA)
        self.frz_surf.fill((120, 190, 255, 55))
        self._txt = {}

    def _text(self, s, color, font):
        k = (s, color, id(font))
        img = self._txt.get(k)
        if img is None:
            if len(self._txt) > 400:
                self._txt.clear()
            img = self._txt[k] = font.render(s, False, color)
        return img

    def draw(self, screen, g):
        sim, fx = g.sim, g.fx
        sx, sy = fx.offset()
        ox, oy = MAP_X + sx, MAP_Y + sy
        screen.set_clip(MAP_RECT)
        screen.fill((30, 50, 30), MAP_RECT)
        screen.blit(self.sp.map, (ox, oy))
        self._enemies(screen, sim, ox, oy)
        self._towers(screen, g, ox, oy)
        fx.draw(screen, ox, oy)
        self._overlays(screen, g, ox, oy)
        if sim.freeze_t > 0:
            screen.blit(self.frz_surf, (MAP_X, MAP_Y))
        if sim.leak_flash > 0:
            screen.blit(self.leak_surf, (MAP_X, MAP_Y))
        screen.set_clip(None)

    # -------------------------------------------------------------------------------
    def _enemies(self, screen, sim, ox, oy):
        pool = sim.pool
        i = pool.idx
        if i.size == 0:
            return
        order = i[np.argsort(pool.y[i])]
        xs, ys, ts = pool.x[order], pool.y[order], pool.typ[order]
        var = np.where(pool.slow[order] > 0, 1, np.where(pool.pois_t[order] > 0, 2, 0))
        bob = ((pool.dist[order] / 20.0).astype(np.int64) & 1) * -PX
        spr, half = self.sp.enemy, self.half
        blits = []
        for x, y, t, v, b in zip(xs.tolist(), ys.tolist(), ts.tolist(), var.tolist(), bob.tolist()):
            hw, hh = half[t]
            blits.append((spr[t][v], (int(x) - hw + ox, int(y) - hh + b + oy)))
        screen.blits(blits, False)
        # hp / shield bars (limited for performance, bosses always)
        hp, mx, shd = pool.hp[order], pool.maxhp[order], pool.shield[order]
        want = ((hp < mx) & (hp > 0)) | T_ISBOSS[ts] | (shd > 0)
        for k in np.flatnonzero(want)[-350:].tolist():
            t = int(ts[k])
            w = half[t][0] * 2
            ratio = max(0.0, min(1.0, float(hp[k] / mx[k])))
            bx, by = int(xs[k]) - w // 2 + ox, int(ys[k]) - half[t][1] - 8 + oy
            screen.fill((30, 10, 10), (bx, by, w, 4))
            screen.fill((230, 60, 60) if ratio < 0.35 else (90, 220, 90), (bx, by, max(1, int(w * ratio)), 4))
            if shd[k] > 0:
                sr = max(0.0, min(1.0, float(shd[k] / mx[k])))
                screen.fill((90, 170, 255), (bx, by - 3, max(1, int(w * sr)), 2))

    def _towers(self, screen, g, ox, oy):
        sim = g.sim
        for t in sorted(sim.towers, key=lambda t: t.y):
            x, y = int(t.x) + ox, int(t.y) + oy
            screen.blit(self.sp.tower[TOWER_TYPES.index(t.tt)], (x - 20, y - 28))
            for s in range(min(5, t.level // 10)):
                screen.fill((255, 225, 80), (x - 10 + s * 6, y - 32, 4, 4))
            if t.flash > 0:
                pygame.draw.circle(screen, (255, 255, 230), (x, y - 14), 6)
            if t.buff > 1.0:
                screen.fill((255, 200, 60), (x + 12, y - 28, 4, 4))
            if t.level > 1:
                img = self._text(str(t.level), (255, 255, 255), self.f[12])
                screen.blit(img, (x - img.get_width() // 2, y + 12))
        sel = g.selected
        if sel is not None:
            x, y = int(sel.x) + ox, int(sel.y) + oy
            pygame.draw.circle(screen, (255, 255, 255), (x, y), int(sel.range), 1)
            pygame.draw.rect(screen, (255, 230, 90), (x - 22, y - 30, 44, 46), 2)

    def _overlays(self, screen, g, ox, oy):
        sim = g.sim
        mx, my = g.mouse
        inmap = MAP_RECT.collidepoint(mx, my)
        if g.modal():
            return
        if g.meteor_armed and inmap:
            pygame.draw.circle(screen, (255, 140, 40), (mx, my), 110, 2)
            pygame.draw.circle(screen, (255, 240, 120), (mx, my), 4)
        elif g.placing is not None and inmap:
            tt = TOWER_TYPES[g.placing]
            gx, gy = g.snap(mx - MAP_X, my - MAP_Y)
            ok = sim.can_place(gx, gy)
            col = (120, 255, 120) if ok else (255, 90, 90)
            pygame.draw.circle(screen, col, (gx + ox, gy + oy), int(tt.range), 1)
            ghost = self.sp.tower[g.placing].copy()
            ghost.set_alpha(190 if ok else 90)
            screen.blit(ghost, (gx + ox - 20, gy + oy - 28))
            pygame.draw.circle(screen, col, (gx + ox, gy + oy), 16, 2)
