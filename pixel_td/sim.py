"""Headless simulation core (no pygame): economy, waves, towers, skills."""
import math
import numpy as np
from .config import *
from .bignum import to_int, MAXF, fmt
from .pathing import Path
from .enemies import EnemyPool, ETYPES, BOSS
from .waves import make_wave, base_hp_max, wave_bonus
from .towers import TOWER_TYPES, Tower, tower_fire

PREP, WAVE, LOST = "prep", "wave", "lost"


class NullFx:
    def __getattr__(self, name):
        return lambda *a, **k: None


class Simulation:
    def __init__(self, fx=None, seed=None):
        self.fx = fx or NullFx()
        self.rng = np.random.default_rng(seed)
        self.path = Path(PATH_TILES)
        self.reset()

    def reset(self):
        self.pool = EnemyPool(MAX_ENEMIES, self.path, self.rng)
        self.towers = []
        self.gold = START_GOLD
        self.wave = 0
        self.state = PREP
        self.base_max = base_hp_max(1)
        self.base_hp = self.base_max
        self.spec = None
        self.sq_pos = 0
        self.spawn_timer = 0.0
        self.time = 0.0
        self.kills = 0.0
        self.best_wave = 0
        self.won = False
        self.leak_flash = 0.0
        self.cd_meteor = self.cd_freeze = 0.0
        self.freeze_t = 0.0
        self.last_bonus = 0
        self.log = []
        self.say("Build towers, then start wave 1!", (200, 220, 255))

    def say(self, text, color=(230, 230, 230)):
        self.log.append((text, color))
        del self.log[:-3]

    # ---- economy / placement ---------------------------------------------------
    def build_cost(self, ti):
        c = TOWER_TYPES[ti].cost * (BUILD_G ** min(len(self.towers), 200))
        return to_int(math.ceil(min(c, MAXF)))

    def can_place(self, x, y):
        m = MAP_MARGIN
        if not (m <= x <= MAP_W - m and m <= y <= MAP_H - m):
            return False
        if self.path.distance_to(x, y) < PATH_CLEAR:
            return False
        s2 = TOWER_SPACING ** 2
        for t in self.towers:
            if (t.x - x) ** 2 + (t.y - y) ** 2 < s2:
                return False
        return True

    def place(self, ti, x, y):
        cost = self.build_cost(ti)
        if self.gold < cost or not self.can_place(x, y):
            return None
        self.gold -= cost
        t = Tower(TOWER_TYPES[ti], x, y, cost)
        self.towers.append(t)
        self.fx.ring(x, y, 4, 26, t.tt.color, 0.3, 2)
        self.fx.burst(x, y, t.tt.color, 8, 80, 0.4, 4)
        return t

    def sell(self, t):
        if t in self.towers:
            self.towers.remove(t)
            self.gold += t.sell_value()
            self.fx.burst(t.x, t.y, (255, 220, 80), 10, 90, 0.5, 4)

    def upgrade(self, t, n):
        """n>0: that many levels; n<0: as many as affordable. Returns levels bought."""
        if n < 0:
            n = t.max_levels(self.gold)
        if n <= 0:
            return 0
        cost = t.cost_levels(n)
        if self.gold < cost:
            return 0
        self.gold -= cost
        t.invested += cost
        t.set_level(t.level + n)
        self.fx.ring(t.x, t.y, 6, 34, (255, 230, 90), 0.4, 3)
        self.fx.burst(t.x, t.y - 10, (255, 230, 90), 12, 100, 0.6, 4)
        self.fx.text(t.x, t.y - 34, f"LV {t.level}", (255, 240, 120))
        return n

    # ---- waves -------------------------------------------------------------------
    def start_wave(self):
        if self.state != PREP:
            return False
        self.wave += 1
        w = self.wave
        self.best_wave = max(self.best_wave, w)
        new_max = base_hp_max(w)
        self.base_hp = min(new_max, self.base_hp * new_max / self.base_max)
        self.base_max = new_max
        self.spec = make_wave(w, self.rng)
        self.sq_pos = 0
        self.spawn_timer = 0.0
        self.state = WAVE
        return True

    def remaining(self):
        r = self.pool.remaining_real()
        if self.state == WAVE and self.spec is not None:
            r += float(self.spec.suffix[self.sq_pos])
        return r

    def _finish_wave(self):
        w = self.wave
        self.last_bonus = wave_bonus(w)
        self.gold += self.last_bonus
        self.base_hp = min(self.base_max, self.base_hp + 0.3 * self.base_max)
        self.state = PREP
        self.say(f"Wave {w} cleared!  +{fmt(self.last_bonus)} gold", (255, 230, 120))
        if w >= WIN_WAVE and not self.won:
            self.won = True

    # ---- skills --------------------------------------------------------------------
    def cast_meteor(self, x, y):
        if self.cd_meteor > 0:
            return False
        self.cd_meteor = 20.0
        pool = self.pool
        i = pool.idx
        if i.size:
            d2 = (pool.x[i] - x) ** 2 + (pool.y[i] - y) ** 2
            ii = i[d2 <= 110 ** 2]
            frac = np.where(pool.typ[ii] == BOSS, 0.04, 0.20)
            pool.hp[ii] -= pool.maxhp[ii] * frac
        self.fx.ring(x, y, 10, 110, (255, 150, 40), 0.5, 5)
        self.fx.ring(x, y, 4, 70, (255, 240, 120), 0.4, 3)
        self.fx.burst(x, y, (255, 120, 30), 40, 220, 0.7, 4)
        self.fx.shake_add(8)
        return True

    def cast_freeze(self):
        if self.cd_freeze > 0:
            return False
        self.cd_freeze = 35.0
        self.freeze_t = 4.0
        return True

    # ---- main tick ---------------------------------------------------------------
    def step(self, dt):
        if self.state == LOST:
            return
        self.time += dt
        self.cd_meteor = max(0.0, self.cd_meteor - dt)
        self.cd_freeze = max(0.0, self.cd_freeze - dt)
        self.freeze_t = max(0.0, self.freeze_t - dt)
        self.leak_flash = max(0.0, self.leak_flash - dt)
        pool, spec = self.pool, self.spec

        if self.state == WAVE and self.sq_pos < spec.n:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                nb = 1 + int(-self.spawn_timer / spec.interval)
                self.spawn_timer += nb * spec.interval
                b = min(nb, spec.n - self.sq_pos)
                got = pool.spawn(spec, self.sq_pos, self.sq_pos + b)
                if (spec.typ[self.sq_pos:self.sq_pos + got] == BOSS).any():
                    self.say(f"BOSS incoming! (wave {self.wave})", (255, 100, 100))
                    self.fx.shake_add(6)
                self.sq_pos += got
                if got < b:
                    self.spawn_timer = 0.05

        leak = pool.move(dt, 0.85 if self.freeze_t > 0 else 0.0)
        if leak > 0:
            self.base_hp -= leak
            self.leak_flash = 0.35
            self.fx.shake_add(4)

        for t in self.towers:
            if t.flash > 0:
                t.flash -= dt
            t.cd -= dt
            if t.cd <= 0:
                if pool.count and tower_fire(self, t):
                    t.cd += 1.0 / t.rate
                else:
                    t.cd = 0.06

        gold, real, xs, ys, ts = pool.reap()
        if real > 0:
            self.gold += to_int(gold)
            self.kills += real
            n = len(xs)
            sel = range(n) if n <= 12 else self.rng.choice(n, 12, replace=False)
            for j in sel:
                c = ETYPES[int(ts[j])].color
                big = int(ts[j]) == BOSS
                self.fx.burst(float(xs[j]), float(ys[j]), c, 24 if big else 7, 150 if big else 90,
                              0.7 if big else 0.4, 4)
                if big:
                    self.fx.ring(float(xs[j]), float(ys[j]), 8, 90, c, 0.5, 4)
                    self.fx.shake_add(8)

        if self.base_hp <= 0:
            self.base_hp = 0.0
            self.state = LOST
            self.say("The base has fallen...", (255, 90, 90))
            return
        if self.state == WAVE and self.sq_pos >= spec.n and pool.count == 0:
            self._finish_wave()
