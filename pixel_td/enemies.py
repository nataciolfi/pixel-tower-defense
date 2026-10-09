"""Enemy definitions + a struct-of-arrays pool. Every per-frame operation on enemies
(movement, poison, regen, slow, damage, death) is a numpy vector operation."""
from dataclasses import dataclass
import numpy as np

GRUNT, RUNNER, BRUTE, KNIGHT, WRAITH, BOSS = range(6)
NORMAL_TYPES = [GRUNT, RUNNER, BRUTE, KNIGHT, WRAITH]


@dataclass(frozen=True)
class EType:
    name: str
    speed: float
    hp_mult: float
    gold_mult: float
    dmg_mult: float
    first_wave: int
    weight: float
    armor: tuple          # (base, per_wave, cap)  -> damage reduction fraction
    regen: float = 0.0    # fraction of max hp / second
    evade: float = 0.0    # chance to dodge a hit
    slow_res: float = 0.0
    color: tuple = (255, 255, 255)


ETYPES = [
    EType("Grunt",  95, 1.0, 1.0, 1.0, 1, 1.0, (0.00, 0.0015, 0.50), color=(110, 190, 80)),
    EType("Runner", 175, 0.45, 0.8, 1.0, 2, 0.7, (0.00, 0.0010, 0.40), color=(240, 190, 70)),
    EType("Brute",  65, 5.0, 3.5, 3.0, 4, 0.5, (0.10, 0.0020, 0.70), color=(190, 100, 80)),
    EType("Knight", 80, 2.0, 3.0, 2.0, 6, 0.5, (0.35, 0.0040, 0.88), color=(170, 180, 200)),
    EType("Wraith", 115, 1.6, 3.0, 2.0, 9, 0.45, (0.10, 0.0020, 0.70), regen=0.03, evade=0.30,
          color=(170, 120, 240)),
    EType("BOSS",   55, 1.0, 1.0, 1.0, 10, 0.0, (0.40, 0.0030, 0.90), slow_res=0.5, color=(230, 70, 80)),
]
NT = len(ETYPES)
T_SPEED = np.array([t.speed for t in ETYPES])
T_HPM = np.array([t.hp_mult for t in ETYPES])
T_GOLDM = np.array([t.gold_mult for t in ETYPES])
T_DMGM = np.array([t.dmg_mult for t in ETYPES])
T_ARM_B = np.array([t.armor[0] for t in ETYPES])
T_ARM_P = np.array([t.armor[1] for t in ETYPES])
T_ARM_C = np.array([t.armor[2] for t in ETYPES])
T_REGEN = np.array([t.regen for t in ETYPES])
T_EVADE = np.array([t.evade for t in ETYPES])
T_SRES = np.array([t.slow_res for t in ETYPES])

_FIELDS = ("hp", "speed", "armor", "dmg", "gold", "bundle", "evade", "regen", "sres")


class EnemyPool:
    def __init__(self, cap, path, rng):
        self.cap, self.path, self.rng = cap, path, rng
        f = lambda: np.zeros(cap, np.float64)
        self.alive = np.zeros(cap, bool)
        self.typ = np.zeros(cap, np.int64)
        self.dist, self.x, self.y = f(), f(), f()
        self.hp, self.maxhp = f(), f()
        self.speed, self.armor, self.dmg, self.gold, self.bundle = f(), f(), f(), f(), f()
        self.slow, self.slow_t, self.pois, self.pois_t = f(), f(), f(), f()
        self.evade, self.regen, self.sres = f(), f(), f()
        self.idx = np.zeros(0, np.int64)
        self.count = 0

    def refresh(self):
        self.idx = np.flatnonzero(self.alive)
        self.count = int(self.idx.size)

    def spawn(self, spec, a, b):
        free = np.flatnonzero(~self.alive)[:b - a]
        k = int(free.size)
        if k == 0:
            return 0
        sl = slice(a, a + k)
        self.alive[free] = True
        self.typ[free] = spec.typ[sl]
        for name in _FIELDS:
            getattr(self, name)[free] = getattr(spec, name)[sl]
        self.maxhp[free] = spec.hp[sl]
        self.dist[free] = 0.0
        self.x[free], self.y[free] = self.path.start
        self.slow[free] = self.slow_t[free] = self.pois[free] = self.pois_t[free] = 0.0
        self.refresh()
        return k

    def clear(self):
        self.alive[:] = False
        self.refresh()

    # -- per-tick movement / status effects (all vectorised) ------------------
    def move(self, dt, freeze=0.0):
        i = self.idx
        if i.size == 0:
            return 0.0
        st = self.slow_t[i] - dt
        self.slow_t[i] = st
        ex = st <= 0
        if ex.any():
            self.slow[i[ex]] = 0.0
        sp = 1.0 - np.minimum(self.slow[i], 0.92)
        if freeze > 0:
            sp = sp * (1.0 - freeze)
        self.dist[i] += self.speed[i] * sp * dt

        pm = self.pois_t[i] > 0
        if pm.any():
            ii = i[pm]
            self.hp[ii] -= self.pois[ii] * dt
            self.pois_t[ii] -= dt
            done = ii[self.pois_t[ii] <= 0]
            self.pois[done] = 0.0
        rm = (self.regen[i] > 0) & (self.hp[i] > 0)
        if rm.any():
            ii = i[rm]
            self.hp[ii] = np.minimum(self.maxhp[ii], self.hp[ii] + self.maxhp[ii] * self.regen[ii] * dt)

        x, y = self.path.positions(self.dist[i])
        self.x[i], self.y[i] = x, y

        lk = (self.dist[i] >= self.path.total) & (self.hp[i] > 0)
        if lk.any():
            li = i[lk]
            dmg = float(self.dmg[li].sum())
            self.alive[li] = False
            return dmg
        return 0.0

    # -- damage helpers --------------------------------------------------------
    def damage(self, idx, dmg, pierce=0.0):
        with np.errstate(all="ignore"):
            d = dmg * (1.0 - self.armor[idx] * (1.0 - pierce))
            ev = self.evade[idx]
            if ev.any():
                miss = (ev > 0) & (self.rng.random(idx.size) < ev)
                d = np.where(miss, 0.0, d)
            self.hp[idx] -= d

    def true_damage(self, idx, dmg):
        self.hp[idx] -= dmg

    def apply_slow(self, idx, amount, dur):
        amt = amount * (1.0 - self.sres[idx])
        self.slow[idx] = np.maximum(self.slow[idx], amt)
        self.slow_t[idx] = np.maximum(self.slow_t[idx], dur)

    def apply_poison(self, idx, dps, dur):
        self.pois[idx] = np.maximum(self.pois[idx], dps)
        self.pois_t[idx] = dur

    def reap(self):
        """Remove dead enemies. Returns (gold, real_kills, xs, ys, types)."""
        i = self.idx
        if i.size == 0:
            return 0.0, 0.0, None, None, None
        dead = i[(self.hp[i] <= 0) & self.alive[i]]
        if dead.size:
            gold = float(self.gold[dead].sum())
            real = float(self.bundle[dead].sum())
            xs, ys, ts = self.x[dead].copy(), self.y[dead].copy(), self.typ[dead].copy()
            self.alive[dead] = False
            self.refresh()
            return gold, real, xs, ys, ts
        self.refresh()
        return 0.0, 0.0, None, None, None

    def remaining_real(self):
        return float(self.bundle[self.idx].sum()) if self.idx.size else 0.0
