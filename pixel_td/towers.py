"""Tower definitions, scaling and hit-scan combat (vectorised target queries)."""
import math
from dataclasses import dataclass
import numpy as np
from .config import *
from .bignum import safe_pow, MAXF, fmt, to_int

MODE_NAMES = ["First", "Last", "Strongest", "Weakest", "Closest"]


@dataclass(frozen=True)
class TowerType:
    key: str
    name: str
    color: tuple
    cost: int
    dmg: float
    range: float
    rate: float
    mode: int
    desc: str


TOWER_TYPES = [
    TowerType("archer", "Archer", (96, 176, 72), 40, 12, 150, 2.0, 0, "Fast & cheap. Crits."),
    TowerType("cannon", "Cannon", (210, 120, 60), 120, 45, 130, 0.7, 0, "Splash damage."),
    TowerType("frost", "Frost", (110, 200, 255), 90, 8, 120, 1.3, 4, "Area slow."),
    TowerType("tesla", "Tesla", (170, 110, 255), 250, 30, 110, 1.0, 0, "Chain lightning."),
    TowerType("sniper", "Sniper", (230, 70, 70), 400, 220, 330, 0.35, 2, "Huge hit, pierces armor."),
    TowerType("toxin", "Toxin", (60, 230, 160), 200, 6, 120, 1.1, 0, "Poison ignores armor."),
]


class Tower:
    def __init__(self, tt, x, y, paid):
        self.tt, self.x, self.y = tt, x, y
        self.level = 1
        self.cd = 0.0
        self.flash = 0.0
        self.mode = tt.mode
        self.invested = int(paid)
        self.recalc()

    # ---- stats ---------------------------------------------------------------
    def recalc(self):
        tt, l = self.tt, self.level
        self.damage = min(MAXF, tt.dmg * safe_pow(DMG_G, l - 1) * safe_pow(MILESTONE, l // 10))
        self.range = tt.range * (1 + min(0.6, 0.006 * (l - 1)))
        self.rate = tt.rate * (1 + min(1.5, 0.01 * (l - 1)))
        self.crit = self.crit_mult = self.splash = self.slow_amt = self.slow_dur = 0.0
        self.chain = 0
        self.pierce = 0.0
        self.poison_dps = self.poison_dur = 0.0
        k = tt.key
        if k == "archer":
            self.crit, self.crit_mult = 0.10 + min(0.40, 0.005 * (l - 1)), 2.5 + 0.02 * (l - 1)
        elif k == "cannon":
            self.splash = 50 * (1 + min(0.8, 0.01 * (l - 1)))
        elif k == "frost":
            self.splash, self.slow_amt, self.slow_dur = 55, 0.35 + min(0.45, 0.01 * (l - 1)), 2.0
        elif k == "tesla":
            self.chain = min(14, 3 + l // 8)
        elif k == "sniper":
            self.pierce = 0.6 + min(0.3, 0.004 * (l - 1))
        elif k == "toxin":
            self.splash, self.poison_dps, self.poison_dur = 45, self.damage * 2.0, 3.0

    def special_text(self):
        k = self.tt.key
        if k == "archer": return f"Crit {self.crit*100:.0f}% x{self.crit_mult:.1f}"
        if k == "cannon": return f"Splash {self.splash:.0f}px"
        if k == "frost":  return f"Slow {self.slow_amt*100:.0f}% / {self.splash:.0f}px"
        if k == "tesla":  return f"Chain {self.chain} targets"
        if k == "sniper": return f"Armor pierce {self.pierce*100:.0f}%"
        return f"Poison {fmt(self.poison_dps)}/s"

    # ---- upgrade economy -----------------------------------------------------
    def _c(self, level):
        return self.tt.cost * UPG_BASE * safe_pow(UPG_G, level - 1)

    def cost_levels(self, n):
        c = self._c(self.level)
        if n == 1:
            return to_int(math.ceil(min(c, MAXF)))
        tot = c * (safe_pow(UPG_G, n) - 1) / (UPG_G - 1)
        return to_int(math.ceil(min(tot, MAXF)))

    def max_levels(self, gold):
        c = self._c(self.level)
        if c >= MAXF or gold <= 0:
            return 0
        gf = float(min(gold, 10 ** 300))
        n = int(math.log(gf * (UPG_G - 1) / c + 1) / math.log(UPG_G))
        while n > 0 and self.cost_levels(n) > gold:
            n -= 1
        return max(0, n)

    def sell_value(self):
        return int(self.invested * SELL_RATIO)

    def set_level(self, lv):
        self.level = lv
        self.recalc()


# ---------------------------------------------------------------------------------
def _pick(pool, cand, d2, mode):
    if mode == 0: return cand[int(np.argmax(pool.dist[cand]))]
    if mode == 1: return cand[int(np.argmin(pool.dist[cand]))]
    if mode == 2: return cand[int(np.argmax(pool.hp[cand]))]
    if mode == 3: return cand[int(np.argmin(pool.hp[cand]))]
    return cand[int(np.argmin(d2))]


def _in_radius(pool, cx, cy, r):
    i = pool.idx
    dx, dy = pool.x[i] - cx, pool.y[i] - cy
    d2 = dx * dx + dy * dy
    m = d2 <= r * r
    return i[m], d2[m]


def tower_fire(sim, t):
    pool, fx, rng = sim.pool, sim.fx, sim.rng
    i = pool.idx
    if i.size == 0:
        return False
    dx, dy = pool.x[i] - t.x, pool.y[i] - t.y
    d2 = dx * dx + dy * dy
    m = d2 <= t.range * t.range
    if not m.any():
        return False
    cand, cd2 = i[m], d2[m]
    tg = _pick(pool, cand, cd2, t.mode)
    tx, ty = float(pool.x[tg]), float(pool.y[tg])
    col = t.tt.color
    k = t.tt.key
    t.flash = 0.1
    one = np.array([tg])
    sy = t.y - 18

    if k == "archer":
        dmg = t.damage
        crit = rng.random() < t.crit
        if crit:
            dmg *= t.crit_mult
            fx.text(tx, ty - 18, fmt(dmg), (255, 230, 80))
        pool.damage(one, dmg)
        fx.line([(t.x, sy), (tx, ty)], col, 0.08, 2)
        fx.burst(tx, ty, col, 3, 60, 0.25, 2)
    elif k == "sniper":
        pool.damage(one, t.damage, t.pierce)
        fx.line([(t.x, sy), (tx, ty)], (255, 255, 255), 0.14, 3)
        fx.line([(t.x, sy), (tx, ty)], col, 0.2, 5)
        fx.burst(tx, ty, (255, 220, 200), 6, 110, 0.3, 4)
    elif k == "cannon":
        ii, d2s = _in_radius(pool, tx, ty, t.splash)
        fall = 1.0 - 0.5 * np.sqrt(d2s) / t.splash
        pool.damage(ii, t.damage * fall)
        fx.line([(t.x, sy), (tx, ty)], (255, 200, 120), 0.07, 3)
        fx.ring(tx, ty, 6, t.splash, (255, 170, 60), 0.28, 3)
        fx.burst(tx, ty, (255, 140, 40), 8, 130, 0.4, 4)
        fx.shake_add(1.5)
    elif k == "frost":
        ii, _ = _in_radius(pool, tx, ty, t.splash)
        pool.damage(ii, t.damage)
        pool.apply_slow(ii, t.slow_amt, t.slow_dur)
        fx.ring(tx, ty, 6, t.splash, col, 0.35, 3)
        fx.burst(tx, ty, (220, 245, 255), 6, 70, 0.4, 2)
        fx.line([(t.x, sy), (tx, ty)], (180, 230, 255), 0.06, 2)
    elif k == "toxin":
        ii, _ = _in_radius(pool, tx, ty, t.splash)
        pool.damage(ii, t.damage)
        pool.apply_poison(ii, t.poison_dps, t.poison_dur)
        fx.ring(tx, ty, 4, t.splash, col, 0.4, 3)
        fx.burst(tx, ty, col, 6, 50, 0.5, 4)
        fx.line([(t.x, sy), (tx, ty)], col, 0.06, 2)
    elif k == "tesla":
        hit = [int(tg)]
        cur = tg
        pts = [(t.x, sy), (tx, ty)]
        for _ in range(t.chain - 1):
            cx, cy = float(pool.x[cur]), float(pool.y[cur])
            ii, d2s = _in_radius(pool, cx, cy, 90.0)
            ok = ~np.isin(ii, hit)
            if not ok.any():
                break
            ii, d2s = ii[ok], d2s[ok]
            cur = ii[int(np.argmin(d2s))]
            hit.append(int(cur))
            pts.append((float(pool.x[cur]), float(pool.y[cur])))
        dm = t.damage * (0.85 ** np.arange(len(hit)))
        pool.damage(np.array(hit), dm)
        fx.bolt(pts, col)
        fx.burst(tx, ty, (230, 200, 255), 4, 80, 0.25, 2)
    return True
