"""Enemy definitions + a struct-of-arrays pool. Every per-frame operation on enemies
(movement, poison, regen, healing, slow, shields, damage, death) is a numpy vector op."""
from dataclasses import dataclass
import numpy as np

(GRUNT, RUNNER, BRUTE, KNIGHT, WRAITH, SWARM, SHAMAN, SPLITTER, AEGIS, GOLEM,
 SPLITLING, OVERLORD, TITAN) = range(13)
NORMAL_TYPES = [GRUNT, RUNNER, BRUTE, KNIGHT, WRAITH, SWARM, SHAMAN, SPLITTER, AEGIS, GOLEM]
BOSS_TYPES = [OVERLORD, TITAN]
BOSS = OVERLORD            # backwards-compatible alias
HEAL_RADIUS = 80.0
HEAL_RATE = 0.015          # fraction of max HP / s


@dataclass(frozen=True)
class EType:
    name: str
    speed: float
    hp_mult: float
    gold_mult: float
    leak: float               # fraction of the base's max HP removed when it leaks
    first_wave: int
    weight: float
    armor: tuple              # (base, per_wave, cap) -> damage reduction fraction
    regen: float = 0.0        # fraction of max hp / second
    evade: float = 0.0        # chance to dodge a hit
    slow_res: float = 0.0
    color: tuple = (255, 255, 255)
    shield: float = 0.0       # shield = shield * hp, absorbs damage first
    heal: float = 0.0         # fraction of max hp / s healed to allies in HEAL_RADIUS
    note: str = ""


ETYPES = [
    EType("Grunt",  95, 1.0, 1.0, 0.08, 1, 1.0, (0.00, 0.0015, 0.50), color=(110, 190, 80), note="Basic infantry."),
    EType("Runner", 175, 0.45, 0.8, 0.08, 2, 0.7, (0.00, 0.0010, 0.40), color=(240, 190, 70), note="Very fast."),
    EType("Brute",  65, 5.0, 3.5, 0.15, 4, 0.5, (0.10, 0.0020, 0.70), color=(190, 100, 80), note="Lots of HP."),
    EType("Knight", 80, 2.0, 3.0, 0.12, 6, 0.5, (0.35, 0.0040, 0.88), color=(170, 180, 200), note="Heavy armor."),
    EType("Wraith", 115, 1.6, 3.0, 0.15, 9, 0.45, (0.10, 0.0020, 0.70), regen=0.03, evade=0.30,
          color=(170, 120, 240), note="Dodges & regenerates."),
    EType("Swarm",  150, 0.12, 0.22, 0.02, 3, 1.4, (0.00, 0.0008, 0.30), color=(240, 140, 60), note="Tiny, numerous."),
    EType("Shaman", 80, 1.5, 3.0, 0.12, 8, 0.25, (0.05, 0.0015, 0.50), color=(70, 190, 210),
          heal=0.015, note="Heals nearby enemies."),
    EType("Splitter", 75, 3.0, 3.0, 0.12, 12, 0.25, (0.10, 0.0020, 0.60), color=(230, 100, 180),
          note="Splits in two on death."),
    EType("Aegis",  80, 1.0, 4.0, 0.12, 15, 0.35, (0.20, 0.0020, 0.70), color=(110, 140, 230),
          shield=1.5, note="Shield soaks damage."),
    EType("Golem",  45, 6.0, 6.0, 0.25, 20, 0.15, (0.30, 0.0030, 0.80), slow_res=1.0, color=(150, 145, 140),
          note="Huge HP, immune to slow."),
    EType("Splitling", 110, 1.0, 1.0, 0.04, 999, 0.0, (0.0, 0.0, 0.0), color=(230, 100, 180), note="Spawned by Splitters."),
    EType("OVERLORD", 55, 1.0, 1.0, 0.60, 10, 0.0, (0.25, 0.0020, 0.70), slow_res=0.4, color=(230, 70, 80),
          note="Boss."),
    EType("TITAN", 45, 1.0, 1.0, 0.50, 20, 0.0, (0.30, 0.0020, 0.75), slow_res=0.75, color=(120, 150, 255),
          shield=0.2, note="Armored, shielded boss."),
]
NT = len(ETYPES)
T_SPEED = np.array([t.speed for t in ETYPES])
T_HPM = np.array([t.hp_mult for t in ETYPES])
T_GOLDM = np.array([t.gold_mult for t in ETYPES])
T_LEAK = np.array([t.leak for t in ETYPES])
T_ARM_B = np.array([t.armor[0] for t in ETYPES])
T_ARM_P = np.array([t.armor[1] for t in ETYPES])
T_ARM_C = np.array([t.armor[2] for t in ETYPES])
T_REGEN = np.array([t.regen for t in ETYPES])
T_EVADE = np.array([t.evade for t in ETYPES])
T_SRES = np.array([t.slow_res for t in ETYPES])
T_SHIELD = np.array([t.shield for t in ETYPES])
T_ISBOSS = np.array([i in BOSS_TYPES for i in range(NT)])

_FIELDS = ("hp", "speed", "armor", "dmg", "gold", "bundle", "evade", "regen", "sres", "shield", "lat")


class EnemyPool:
    def __init__(self, cap, path, rng):
        self.cap, self.path, self.rng = cap, path, rng
        f = lambda: np.zeros(cap, np.float64)
        self.alive = np.zeros(cap, bool)
        self.typ = np.zeros(cap, np.int64)
        self.dist, self.x, self.y, self.lat = f(), f(), f(), f()
        self.hp, self.maxhp, self.shield = f(), f(), f()
        self.speed, self.armor, self.dmg, self.gold, self.bundle = f(), f(), f(), f(), f()
        self.slow, self.slow_t, self.pois, self.pois_t = f(), f(), f(), f()
        self.stun_t, self.vuln, self.vuln_t = f(), f(), f()
        self.src = np.full(cap, -1, np.int64)       # uid of the tower that last hurt this enemy
        self.cur_src = -1
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
        self.stun_t[free] = self.vuln[free] = self.vuln_t[free] = 0.0
        self.src[free] = -1
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
        stn = self.stun_t[i]
        if stn.any():
            self.stun_t[i] = np.maximum(0.0, stn - dt)
            sp = np.where(stn > 0, 0.0, sp)
        vt = self.vuln_t[i]
        if vt.any():
            vt = vt - dt
            self.vuln_t[i] = vt
            gone = i[vt <= 0]
            self.vuln[gone] = 0.0
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

        x, y = self.path.positions(self.dist[i], self.lat[i])
        self.x[i], self.y[i] = x, y

        # shamans heal everything around them; coverage does NOT stack (one heal per enemy / tick)
        sh = i[(self.typ[i] == SHAMAN) & (self.hp[i] > 0)]
        if sh.size:
            xs, ys = self.x[i], self.y[i]
            covered = np.zeros(i.size, bool)
            for s in sh[:24]:
                covered |= (xs - self.x[s]) ** 2 + (ys - self.y[s]) ** 2 <= HEAL_RADIUS ** 2
            covered &= self.hp[i] > 0
            ii = i[covered]
            self.hp[ii] = np.minimum(self.maxhp[ii], self.hp[ii] + self.maxhp[ii] * HEAL_RATE * dt)

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
            d = dmg * (1.0 - self.armor[idx] * (1.0 - pierce)) * (1.0 + self.vuln[idx])
            self.src[idx] = self.cur_src
            ev = self.evade[idx]
            if ev.any():
                miss = (ev > 0) & (self.rng.random(idx.size) < ev)
                d = np.where(miss, 0.0, d)
            sh = self.shield[idx]
            if sh.any():
                ab = np.minimum(sh, d)
                self.shield[idx] = sh - ab
                d = d - ab
            self.hp[idx] -= d

    def true_damage(self, idx, dmg):
        """Ignores armor, evasion and shields (but not Hexer's vulnerability)."""
        self.src[idx] = self.cur_src
        self.hp[idx] -= dmg * (1.0 + self.vuln[idx])

    def apply_stun(self, idx, dur):
        d = dur * (1.0 - 0.8 * T_ISBOSS[self.typ[idx]])         # bosses are stunned 80% shorter
        self.stun_t[idx] = np.maximum(self.stun_t[idx], d)

    def apply_vuln(self, idx, amount, dur):
        a = amount * (1.0 - 0.5 * T_ISBOSS[self.typ[idx]])      # bosses take half the vulnerability
        self.vuln[idx] = np.maximum(self.vuln[idx], a)
        self.vuln_t[idx] = np.maximum(self.vuln_t[idx], dur)

    def knockback(self, idx, px):
        k = px * (1.0 - 0.7 * T_ISBOSS[self.typ[idx]])
        self.dist[idx] = np.maximum(0.0, self.dist[idx] - k)

    def apply_slow(self, idx, amount, dur):
        amt = amount * (1.0 - self.sres[idx])
        self.slow[idx] = np.maximum(self.slow[idx], amt)
        self.slow_t[idx] = np.maximum(self.slow_t[idx], dur)

    def apply_poison(self, idx, dps, dur):
        self.src[idx] = self.cur_src
        self.pois[idx] = np.maximum(self.pois[idx], dps)
        self.pois_t[idx] = dur

    def reap(self):
        """Remove dead enemies.
        Returns (gold, real_kills, xs, ys, types, srcs, bundles, golds); the last four are per-kill
        arrays (killer tower uid, real enemies represented, unmultiplied gold)."""
        i = self.idx
        if i.size == 0:
            return (0.0, 0.0) + (None,) * 6
        dead = i[(self.hp[i] <= 0) & self.alive[i]]
        if dead.size:
            gold = float(self.gold[dead].sum())
            real = float(self.bundle[dead].sum())
            xs, ys, ts = self.x[dead].copy(), self.y[dead].copy(), self.typ[dead].copy()
            srcs, buns, golds = self.src[dead].copy(), self.bundle[dead].copy(), self.gold[dead].copy()
            kids = dead[self.typ[dead] == SPLITTER]
            parent = None
            if kids.size:
                parent = {n: getattr(self, n)[kids].copy()
                          for n in ("dist", "maxhp", "armor", "dmg", "gold", "bundle", "speed", "x", "y", "lat")}
                parent["src"] = self.src[kids].copy()
            self.alive[dead] = False
            self.refresh()
            if parent is not None:
                self._spawn_children(parent)
            return gold, real, xs, ys, ts, srcs, buns, golds
        self.refresh()
        return (0.0, 0.0) + (None,) * 6

    def _spawn_children(self, p):
        n = 2 * len(p["dist"])
        free = np.flatnonzero(~self.alive)[:n]
        k = int(free.size)
        if k == 0:
            return
        rep = np.repeat(np.arange(len(p["dist"])), 2)[:k]
        self.alive[free] = True
        self.typ[free] = SPLITLING
        self.hp[free] = self.maxhp[free] = 0.25 * p["maxhp"][rep]
        self.speed[free] = T_SPEED[SPLITLING] * (p["speed"][rep] / T_SPEED[SPLITTER])
        self.armor[free] = p["armor"][rep] * 0.5
        self.dmg[free] = p["dmg"][rep] * 0.25
        self.gold[free] = p["gold"][rep] * 0.25
        self.bundle[free] = p["bundle"][rep]
        self.evade[free] = self.regen[free] = self.sres[free] = self.shield[free] = 0.0
        self.dist[free] = p["dist"][rep]
        self.x[free], self.y[free] = p["x"][rep], p["y"][rep]
        self.lat[free] = p["lat"][rep]
        self.stun_t[free] = self.vuln[free] = self.vuln_t[free] = 0.0
        self.src[free] = p["src"][rep]
        self.slow[free] = self.slow_t[free] = self.pois[free] = self.pois_t[free] = 0.0
        self.refresh()

    def remaining_real(self):
        return float(self.bundle[self.idx].sum()) if self.idx.size else 0.0
