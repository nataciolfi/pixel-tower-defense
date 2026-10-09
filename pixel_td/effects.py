"""Particles (numpy ring-buffer), beams, rings, floating text, screen shake. All capped."""
import random
import numpy as np
import pygame


class Effects:
    MAXP = 1500
    MAX_LINES, MAX_RINGS, MAX_TEXTS = 220, 120, 14

    def __init__(self, font):
        n = self.MAXP
        self.px, self.py, self.vx, self.vy = (np.zeros(n) for _ in range(4))
        self.life, self.maxlife = np.zeros(n), np.ones(n)
        self.size = np.full(n, 4, np.int64)
        self.col = np.zeros((n, 3), np.uint8)
        self.ptr = 0
        self.lines, self.rings, self.texts = [], [], []
        self.shake = 0.0
        self.font = font
        self._tcache = {}

    # ---- spawners --------------------------------------------------------------
    def burst(self, x, y, color, n=8, speed=90, life=0.45, size=4):
        n = min(int(n), 60)
        s = (self.ptr + np.arange(n)) % self.MAXP
        self.ptr = (self.ptr + n) % self.MAXP
        ang = np.random.random(n) * 6.2832
        sp = speed * (0.3 + 0.7 * np.random.random(n))
        self.px[s], self.py[s] = x, y
        self.vx[s], self.vy[s] = np.cos(ang) * sp, np.sin(ang) * sp
        self.life[s] = life * (0.6 + 0.4 * np.random.random(n))
        self.maxlife[s] = life
        self.size[s] = size
        self.col[s] = color

    def line(self, pts, color, life=0.1, width=2):
        if len(self.lines) < self.MAX_LINES:
            self.lines.append([pts, color, life, life, width])

    def bolt(self, pts, color):
        """Jagged lightning through pts."""
        out = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            for k in range(1, 4):
                t = k / 4
                out.append((a[0] + (b[0] - a[0]) * t + random.uniform(-6, 6),
                            a[1] + (b[1] - a[1]) * t + random.uniform(-6, 6)))
            out.append(b)
        self.line(out, (240, 225, 255), 0.12, 2)
        self.line(out, color, 0.2, 4)

    def ring(self, x, y, r0, r1, color, life=0.3, width=2):
        if len(self.rings) < self.MAX_RINGS:
            self.rings.append([x, y, r0, r1, color, life, life, width])

    def text(self, x, y, s, color):
        if len(self.texts) < self.MAX_TEXTS:
            self.texts.append([x, y, s, color, 0.8])

    def shake_add(self, v):
        self.shake = min(10.0, max(self.shake, v))

    # ---- update / draw --------------------------------------------------------------
    def update(self, dt):
        a = self.life > 0
        if a.any():
            self.life[a] -= dt
            self.px[a] += self.vx[a] * dt
            self.py[a] += self.vy[a] * dt
            drag = float(np.exp(-3.0 * dt))
            self.vx[a] *= drag
            self.vy[a] *= drag
        for L in self.lines:
            L[2] -= dt
        self.lines = [L for L in self.lines if L[2] > 0]
        for R in self.rings:
            R[5] -= dt
        self.rings = [R for R in self.rings if R[5] > 0]
        for T in self.texts:
            T[4] -= dt
            T[1] -= 24 * dt
        self.texts = [T for T in self.texts if T[4] > 0]
        self.shake = max(0.0, self.shake - 18 * dt)

    def offset(self):
        s = int(self.shake)
        return (random.randint(-s, s), random.randint(-s, s)) if s else (0, 0)

    def draw(self, surf, ox, oy):
        idx = np.flatnonzero(self.life > 0)
        if idx.size:
            xs, ys = self.px[idx].tolist(), self.py[idx].tolist()
            cols = self.col[idx].tolist()
            fade = (self.life[idx] / self.maxlife[idx] > 0.5).tolist()
            sz = self.size[idx].tolist()
            for x, y, c, f, s in zip(xs, ys, cols, fade, sz):
                q = s if f else max(2, s // 2)
                surf.fill(c, (int(x) + ox, int(y) + oy, q, q))
        for pts, color, life, ml, w in self.lines:
            ww = w if life > ml * 0.5 else max(1, w // 2)
            pygame.draw.lines(surf, color, False, [(p[0] + ox, p[1] + oy) for p in pts], ww)
        for x, y, r0, r1, color, life, ml, w in self.rings:
            t = 1.0 - life / ml
            pygame.draw.circle(surf, color, (int(x + ox), int(y + oy)), int(r0 + (r1 - r0) * t), w)
        for x, y, s, color, life in self.texts:
            key = (s, color)
            img = self._tcache.get(key)
            if img is None:
                if len(self._tcache) > 300:
                    self._tcache.clear()
                img = self._tcache[key] = self.font.render(s, False, color)
            surf.blit(img, (int(x + ox) - img.get_width() // 2, int(y + oy)))
