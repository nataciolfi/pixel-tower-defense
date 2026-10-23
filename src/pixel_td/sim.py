"""Headless simulation core (no pygame): economy, waves, towers, skills, prestige hooks."""
import math
import numpy as np
from .config import *
from .bignum import to_int, MAXF, fmt
from .pathing import Path
from .enemies import EnemyPool, ETYPES, T_ISBOSS
from .waves import make_wave, base_hp_nominal, wave_bonus, repair_cost
from .towers import TOWER_TYPES, BY_KEY, Tower, tower_fire, legend_tick
from .meta import Meta, ascend_gain, shard_gain
from .maps import BY_KEY as MAP_BY_KEY, DEFAULT_MAP

PREP, WAVE, LOST = "prep", "wave", "lost"
METEOR_CD, FREEZE_CD = 20.0, 35.0


class NullFx:
    def __getattr__(self, name):
        return lambda *a, **k: None


class Simulation:
    def __init__(self, fx=None, seed=None, meta=None, map_key=DEFAULT_MAP):
        self.fx = fx or NullFx()
        self.rng = np.random.default_rng(seed)
        self.meta = meta or Meta()
        self.set_map(map_key)

    def set_map(self, key, reset=True):
        self.map = MAP_BY_KEY.get(key) or MAP_BY_KEY[DEFAULT_MAP]
        self.path = Path(self.map.tiles)
        if reset:
            self.reset()

    def reset(self):
        self.pool = EnemyPool(MAX_ENEMIES, self.path, self.rng)
        self.towers = []
        self.by_uid = {}
        self._uid = 0
        self.auto_mode = 0          # auto-upgrade: 0 off, 1 priority towers only, 2 priority first, then everything
        self.auto_t = 0.0
        self.mint_bonus = 0.0
        self.gold = self.map.start_gold + self.meta.start_bonus()
        self.wave = 0
        self.state = PREP
        self.base_max = base_hp_nominal(1) * self.meta.base_mult()
        self.base_hp = self.base_max
        self.spec = None
        self.sq_pos = 0
        self.wave_t = 0.0
        self.time = 0.0
        self.kills = 0.0
        self.won = False
        self.waves_cleared = 0
        self.leak_flash = 0.0
        self.cd_meteor = self.cd_freeze = 0.0
        self.freeze_t = 0.0
        self.last_bonus = 0
        self.log = []
        self.say("Build towers, then start wave 1!", (200, 220, 255))
        self.checkpoint = self.snapshot()

    def say(self, text, color=(230, 230, 230)):
        self.log.append((text, color))
        del self.log[:-3]

    # ---- meta helpers ----------------------------------------------------------
    @property
    def meteor_total(self): return METEOR_CD * self.meta.skill_mult()
    @property
    def freeze_total(self): return FREEZE_CD * self.meta.skill_mult()

    def ascend_gain(self):
        return ascend_gain(self.wave, self.map.ap_mult)

    def shard_gain(self):
        return shard_gain(self.wave, self.map.level)

    def legend_state(self, ti):
        """For legendary towers: 'vault' (not bought), 'wave' (bought, run not far enough), 'built' or 'ready'."""
        tt = TOWER_TYPES[ti]
        if not self.meta.owns_legend(tt.key):
            return "vault"
        if self.has_legend(tt.key):
            return "built"
        if self.wave < tt.unlock:
            return "wave"
        return "ready"

    def unlocked(self, ti):
        tt = TOWER_TYPES[ti]
        if tt.legendary:
            return self.legend_state(ti) in ("ready", "built")
        return self.meta.best_wave >= tt.unlock

    def recalc_all(self):
        for t in self.towers:
            t.recalc()
        self.recompute_buffs()

    def recompute_buffs(self):
        """Beacon damage auras, Overclock speed auras and the global Mint gold bonus."""
        tw = self.towers
        for t in tw:
            t.buff = 1.0
            t.haste = 1.0
        self.mint_bonus = 0.0
        for b in tw:
            k = b.tt.key
            if k == "mint":
                self.mint_bonus += b.mint_aura
            elif k in ("beacon", "overclock"):
                r2 = b.range * b.range
                for t in tw:
                    if t.rate > 0 and (t.x - b.x) ** 2 + (t.y - b.y) ** 2 <= r2:
                        if k == "beacon":
                            t.buff += b.aura
                        else:
                            t.haste += b.haste_aura

    def gold_mult(self):
        return self.meta.gold_mult() * (1.0 + self.mint_bonus)

    # ---- save / load -------------------------------------------------------------
    def snapshot(self):
        return {"map": self.map.key, "wave": self.wave, "gold": int(self.gold),
                "base_hp": float(self.base_hp), "kills": float(self.kills), "won": bool(self.won),
                "auto": int(self.auto_mode),
                "towers": [{"k": t.tt.key, "x": t.x, "y": t.y, "l": t.level, "m": t.mode,
                            "i": int(t.invested), "p": t.prio, "xp": float(t.xp), "kl": float(t.kills)}
                           for t in self.towers]}

    def save_snapshot(self):
        """State to persist: live while building, otherwise the start-of-wave checkpoint."""
        return self.snapshot() if self.state == PREP else self.checkpoint

    def restore(self, d):
        self.set_map(d.get("map") or DEFAULT_MAP, reset=False)
        self.reset()
        self.wave = max(0, int(d["wave"]))
        self.gold = max(0, int(d["gold"]))
        self.kills = float(d.get("kills", 0.0))
        self.won = bool(d.get("won", False))
        self.auto_mode = max(0, min(2, int(d.get("auto", 0))))
        for td in d.get("towers", []):
            tt = BY_KEY[td["k"]]
            t = Tower(tt, float(td["x"]), float(td["y"]), int(td["i"]), self.meta)
            t.set_level(max(1, int(td["l"])))
            t.mode = int(td["m"]) % 5
            t.prio = max(0, min(3, int(td.get("p", 0))))
            t.xp = float(td.get("xp", 0.0))
            t.kills = float(td.get("kl", 0.0))
            if tt.legendary:
                t.add_xp(0.0)
                self.meta.legends.add(tt.key)          # a restored legend is always owned
            self._register(t)
        self.base_max = base_hp_nominal(max(1, self.wave)) * self.meta.base_mult()
        self.base_hp = max(1.0, min(self.base_max, float(d.get("base_hp", self.base_max))))
        self.recompute_buffs()
        self.say(f"Run restored at wave {self.wave}.", (200, 220, 255))
        self.checkpoint = self.snapshot()

    # ---- economy / placement ---------------------------------------------------
    def _register(self, t):
        self._uid += 1
        t.uid = self._uid
        self.towers.append(t)
        self.by_uid[t.uid] = t

    def has_legend(self, key):
        return any(t.tt.key == key for t in self.towers)

    def build_cost(self, ti):
        tt = TOWER_TYPES[ti]
        if tt.legendary:
            return 0          # legends are paid once, in Legend Shards (Vault); placing them costs no gold
        n = sum(1 for t in self.towers if not t.tt.legendary)
        c = tt.cost * (BUILD_G ** min(n, 200)) * self.meta.build_mult()
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
        tt = TOWER_TYPES[ti]
        cost = self.build_cost(ti)
        if not self.unlocked(ti) or self.gold < cost or not self.can_place(x, y):
            return None
        if tt.legendary and self.has_legend(tt.key):
            return None                                   # only one of each legend per run
        self.gold -= cost
        t = Tower(tt, x, y, cost, self.meta)
        self._register(t)
        self.recompute_buffs()
        self.fx.ring(x, y, 4, 26, t.tt.color, 0.3, 2)
        self.fx.burst(x, y, t.tt.color, 8, 80, 0.4, 4)
        if tt.legendary:
            self.say(f"LEGENDARY {tt.name} awakens! It levels up by killing.", (255, 220, 100))
            self.fx.ring(x, y, 10, 120, (255, 215, 80), 0.8, 5)
            self.fx.shake_add(6)
        return t

    def sell(self, t):
        if t in self.towers and not t.tt.legendary:         # legends are permanent
            self.towers.remove(t)
            self.by_uid.pop(t.uid, None)
            self.gold += t.sell_value()
            self.recompute_buffs()
            self.fx.burst(t.x, t.y, (255, 220, 80), 10, 90, 0.5, 4)

    def upgrade(self, t, n, silent=False):
        """n>0: that many levels; n<0: as many as affordable. Returns levels bought.
        Legendary towers cannot be bought up: they level from kills."""
        if t.tt.legendary:
            return 0
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
        if t.tt.key in ("beacon", "overclock", "mint"):
            self.recompute_buffs()
        if not silent:
            self.fx.ring(t.x, t.y, 6, 34, (255, 230, 90), 0.4, 3)
            self.fx.burst(t.x, t.y - 10, (255, 230, 90), 12, 100, 0.6, 4)
            self.fx.text(t.x, t.y - 34, f"LV {t.level}", (255, 240, 120))
        return n

    # ---- auto upgrade (priority ranks first, then optionally everything else) -------------
    def _spend_group(self, group, cap=300):
        if not group:
            return 0
        n = 0
        if len(group) == 1:
            n = self.upgrade(group[0], -1, silent=True)
            return n
        costs = {t.uid: t.cost_levels(1) for t in group}
        while n < cap:
            t = min(group, key=lambda g: costs[g.uid])
            if self.gold < costs[t.uid]:
                break
            self.upgrade(t, 1, silent=True)
            costs[t.uid] = t.cost_levels(1)
            n += 1
        return n

    def auto_upgrade(self):
        if self.auto_mode == 0:
            return
        up = [t for t in self.towers if not t.tt.legendary]
        for rank in (1, 2, 3):
            self._spend_group([t for t in up if t.prio == rank])
        if self.auto_mode == 2:
            self._spend_group([t for t in up if t.prio == 0])

    # ---- base repair (the base only heals a little between waves) ------------------
    def repair_price(self):
        return repair_cost(max(1, self.wave), self.map)

    def can_repair(self):
        return self.state == PREP and self.base_hp < self.base_max and self.gold >= self.repair_price()

    def repair(self):
        if not self.can_repair():
            return False
        self.gold -= self.repair_price()
        self.base_hp = min(self.base_max, self.base_hp + REPAIR_FRACTION * self.base_max)
        self.say(f"Base repaired (+{int(REPAIR_FRACTION * 100)}%).", (120, 255, 150))
        return True

    # ---- waves -------------------------------------------------------------------
    def start_wave(self):
        if self.state != PREP:
            return False
        self.checkpoint = self.snapshot()
        self.wave += 1
        w = self.wave
        self.meta.best_wave = max(self.meta.best_wave, w)
        self.meta.map_best[self.map.key] = max(self.meta.map_best.get(self.map.key, 0), w)
        new_max = base_hp_nominal(w) * self.meta.base_mult()
        self.base_hp = min(new_max, self.base_hp * new_max / self.base_max)
        self.base_max = new_max
        self.spec = make_wave(w, self.rng, self.map)
        self.sq_pos = 0
        self.wave_t = 0.0
        self.state = WAVE
        return True

    def remaining(self):
        r = self.pool.remaining_real()
        if self.state == WAVE and self.spec is not None:
            r += float(self.spec.suffix[self.sq_pos])
        return r

    def _finish_wave(self):
        w = self.wave
        self.last_bonus = to_int(wave_bonus(w, self.map) * self.gold_mult())
        self.gold += self.last_bonus
        heal = self.map.regen * self.base_max
        self.base_hp = min(self.base_max, self.base_hp + heal)
        self.state = PREP
        self.waves_cleared += 1
        self.say(f"Wave {w} cleared!  +{fmt(self.last_bonus)} gold", (255, 230, 120))
        if w >= WIN_WAVE and not self.won:
            self.won = True

    # ---- skills --------------------------------------------------------------------
    def cast_meteor(self, x, y):
        if self.cd_meteor > 0:
            return False
        self.cd_meteor = self.meteor_total
        pool = self.pool
        i = pool.idx
        if i.size:
            d2 = (pool.x[i] - x) ** 2 + (pool.y[i] - y) ** 2
            ii = i[d2 <= 110 ** 2]
            frac = np.where(T_ISBOSS[pool.typ[ii]], 0.08, 0.20)
            pool.hp[ii] -= pool.maxhp[ii] * frac
        self.fx.ring(x, y, 10, 110, (255, 150, 40), 0.5, 5)
        self.fx.ring(x, y, 4, 70, (255, 240, 120), 0.4, 3)
        self.fx.burst(x, y, (255, 120, 30), 40, 220, 0.7, 4)
        self.fx.shake_add(8)
        return True

    def cast_freeze(self):
        if self.cd_freeze > 0:
            return False
        self.cd_freeze = self.freeze_total
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
            self.wave_t += dt
            k = int(np.searchsorted(spec.times, self.wave_t, side="right"))
            if k > self.sq_pos:
                got = pool.spawn(spec, self.sq_pos, k)
                if got and T_ISBOSS[spec.typ[self.sq_pos:self.sq_pos + got]].any():
                    self.say(f"BOSS incoming! (wave {self.wave})", (255, 100, 100))
                    self.fx.shake_add(6)
                self.sq_pos += got

        leak = pool.move(dt, 0.85 if self.freeze_t > 0 else 0.0)
        if leak > 0:
            self.base_hp -= leak
            self.leak_flash = 0.35
            self.fx.shake_add(4)

        for t in self.towers:
            if t.flash > 0:
                t.flash -= dt
            if t.rate <= 0:           # beacon / overclock / mint only buff
                continue
            if t.tt.legendary:
                legend_tick(self, t, dt)
            t.cd -= dt
            if t.cd <= 0:
                if pool.count and tower_fire(self, t):
                    t.cd += 1.0 / (t.rate * t.haste)
                else:
                    t.cd = 0.06
                    t.stacks = 0

        gold, real, xs, ys, ts, srcs, buns, golds = pool.reap()
        if real > 0:
            gm = self.gold_mult()
            self.gold += to_int(gold * gm)
            self.kills += real
            self.meta.lifetime_kills += real
            ok = srcs >= 0
            if ok.any():                                       # credit kills / legendary XP
                su = srcs[ok]
                kills = np.bincount(su, weights=buns[ok])
                xps = np.bincount(su, weights=golds[ok])
                for uid in np.flatnonzero(kills).tolist():
                    t = self.by_uid.get(uid)
                    if t is None:
                        continue
                    t.kills += float(kills[uid])
                    if t.tt.legendary and t.add_xp(float(xps[uid]) * t.xp_mult):
                        self.fx.ring(t.x, t.y, 8, 60, (255, 215, 80), 0.6, 4)
                        self.fx.text(t.x, t.y - 40, f"LV {t.level}", (255, 230, 120))
                        self.say(f"{t.tt.name} reached level {t.level}!", (255, 220, 120))
            for t in self.towers:                               # Midas: kills in range pay extra
                if t.tt.key == "midas":
                    inr = (xs - t.x) ** 2 + (ys - t.y) ** 2 <= t.range ** 2
                    if inr.any():
                        self.gold += to_int(float(golds[inr].sum()) * t.gold_bonus * gm)
            n = len(xs)
            sel = range(n) if n <= 12 else self.rng.choice(n, 12, replace=False)
            for j in sel:
                c = ETYPES[int(ts[j])].color
                big = bool(T_ISBOSS[int(ts[j])])
                self.fx.burst(float(xs[j]), float(ys[j]), c, 24 if big else 7, 150 if big else 90,
                              0.7 if big else 0.4, 4)
                if big:
                    self.fx.ring(float(xs[j]), float(ys[j]), 8, 90, c, 0.5, 4)
                    self.fx.shake_add(8)

        if self.auto_mode:
            self.auto_t += dt
            if self.auto_t >= AUTO_INTERVAL:
                self.auto_t = 0.0
                self.auto_upgrade()

        if self.base_hp <= 0:
            self.base_hp = 0.0
            self.state = LOST
            self.say("The base has fallen...", (255, 90, 90))
            return
        if self.state == WAVE and self.sq_pos >= spec.n and pool.count == 0:
            self._finish_wave()
