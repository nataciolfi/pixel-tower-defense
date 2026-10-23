"""Wave generation. Everything scales exponentially per map (see maps.py).

* Enemies of the same type spawn together as a tight *squad* (small spacing + a random
  sideways offset), so crowds are dense and area damage is effective.
* When the real enemy count exceeds MAX_ENT_PER_WAVE, enemies are merged into *bundles*: one
  on-screen enemy then stands for `bundle` real ones (HP, gold and leak damage multiplied).
* Boss HP grows only polynomially in the wave number (see boss_hp_units), far slower than
  normal enemies, so bosses stay beatable while ordinary waves keep getting heavier.
"""
import numpy as np
from .config import *
from .bignum import safe_pow, MAXF
from . import enemies as E

SPACING_PX = 10.0        # distance between enemies of a squad along the road
LATERAL = 14.0           # random sideways offset (px) -> thick crowds
SQUAD_GAP = 1.0          # seconds between squads of different types
MAX_SPAWN_TIME = 40.0    # a wave never takes longer than this to spawn


EARLY_WAVES = 10         # every map starts alike; the map's own growth rates take over after this
EARLY_HP_G, EARLY_COUNT_G, EARLY_GOLD_G = 1.15, 1.05, 1.145


def _grow(early_g, late_g, w):
    return safe_pow(early_g, min(w, EARLY_WAVES) - 1) * safe_pow(late_g, max(0, w - EARLY_WAVES))


def hp_base(w, m):        return 20.0 * m.hp_mult * _grow(EARLY_HP_G, m.hp_g, w)
def gold_base(w, m):      return 3.0 * m.gold_mult * _grow(EARLY_GOLD_G, m.gold_g, w)
def enemy_count(w, m):    return 6.0 * _grow(EARLY_COUNT_G, m.count_g, w)
def leak_grace(w):        return min(1.0, 0.4 + 0.1 * w)     # early waves hurt the base less
def base_hp_nominal(w):   return 100.0 * safe_pow(BASE_G, w - 1)
def wave_bonus(w, m):     return int(40 * m.gold_mult * safe_pow(BONUS_G, w - 1))
def speed_scale(w, m):    return min(1.6, 1.0 + 0.004 * (w - 1)) * m.speed_mult
def is_boss_wave(w):      return w % 10 == 0
def boss_count(w):        return 1 + w // 50
def boss_type(w):         return E.TITAN if w % 20 == 0 else E.OVERLORD
def boss_hp_units(w, m):  return m.boss_k * (1.0 + w / 25.0)   # in multiples of a grunt's HP
def income_est(w, m):     return gold_base(w, m) * enemy_count(w, m) * 2.4 + wave_bonus(w, m)
def repair_cost(w, m):    return int(1.2 * gold_base(w, m) * enemy_count(w, m)) + 1


class WaveSpec:
    pass


def make_wave(w, rng, m):
    boss = is_boss_wave(w)
    total = enemy_count(w, m) * (0.6 if boss else 1.0)
    n = int(max(1, min(MAX_ENT_PER_WAVE, round(total))))
    bundle = max(1.0, total / n)

    avail = [t for t in E.NORMAL_TYPES if E.ETYPES[t].first_wave <= w]
    wts = np.array([E.ETYPES[t].weight for t in avail], float)
    if len(avail) > 1 and w >= 3 and rng.random() < 0.35:       # "rush" waves
        wts[rng.integers(len(avail))] *= 2.0
    wts /= wts.sum()
    typ = rng.choice(avail, size=n, p=wts).astype(np.int64)
    kinds = [t for t in avail if (typ == t).any()]
    rng.shuffle(kinds)
    typ = np.concatenate([typ[typ == t] for t in kinds])          # squads: one type after another

    s = WaveSpec()
    s.w, s.boss = w, boss
    hp1 = hp_base(w, m)
    hp = hp1 * E.T_HPM[typ] * bundle
    armor = np.minimum(E.T_ARM_C[typ], E.T_ARM_B[typ] + E.T_ARM_P[typ] * w)
    lm = m.leak_mult * leak_grace(w)
    leak = base_hp_nominal(w) * E.T_LEAK[typ] * lm * bundle
    gold = gold_base(w, m) * E.T_GOLDM[typ] * bundle
    spd = E.T_SPEED[typ] * speed_scale(w, m)
    bun = np.full(n, bundle)
    lat = rng.uniform(-LATERAL, LATERAL, n)

    # spawn schedule: tight inside a squad, a gap between squads
    step = SPACING_PX / spd
    gap = np.zeros(n)
    gap[1:] = np.where(typ[1:] != typ[:-1], SQUAD_GAP, 0.0)
    times = np.cumsum(step + gap) - step[0]
    if times[-1] > MAX_SPAWN_TIME:
        times *= MAX_SPAWN_TIME / times[-1]

    if boss:
        nb = boss_count(w)
        b = boss_type(w)
        bspd = E.T_SPEED[b] * speed_scale(w, m)
        typ = np.concatenate([typ, np.full(nb, b)])
        hp = np.concatenate([hp, np.full(nb, hp1 * boss_hp_units(w, m))])
        armor = np.concatenate([armor, np.full(nb, min(E.T_ARM_C[b], E.T_ARM_B[b] + E.T_ARM_P[b] * w))])
        leak = np.concatenate([leak, np.full(nb, base_hp_nominal(w) * E.T_LEAK[b] * lm)])
        gold = np.concatenate([gold, np.full(nb, 0.6 * enemy_count(w, m) * gold_base(w, m) / nb)])
        spd = np.concatenate([spd, np.full(nb, bspd)])
        bun = np.concatenate([bun, np.ones(nb)])
        lat = np.concatenate([lat, np.zeros(nb)])
        times = np.concatenate([times, times[-1] + 2.5 + 3.0 * np.arange(nb)])

    s.n = int(typ.size)
    s.typ = typ
    s.hp = np.minimum(hp, MAXF)
    s.armor, s.dmg = armor, np.minimum(leak, MAXF)
    s.gold = np.minimum(gold, MAXF)
    s.speed, s.bundle, s.lat = spd, bun, lat
    s.evade, s.regen, s.sres = E.T_EVADE[typ], E.T_REGEN[typ], E.T_SRES[typ]
    s.shield = np.minimum(E.T_SHIELD[typ] * s.hp, MAXF)
    s.times = times
    s.suffix = np.concatenate([np.cumsum(bun[::-1])[::-1], [0.0]])
    s.total_real = float(s.suffix[0])
    return s


def wave_preview(w, m):
    boss = is_boss_wave(w)
    total = enemy_count(w, m) * (0.6 if boss else 1.0) + (boss_count(w) if boss else 0)
    names = [E.ETYPES[t].name for t in E.NORMAL_TYPES if E.ETYPES[t].first_wave <= w]
    return dict(total=total, hp=hp_base(w, m), boss=boss, names=names, bundled=total > MAX_ENT_PER_WAVE,
                boss_name=E.ETYPES[boss_type(w)].name if boss else "",
                boss_hp=hp_base(w, m) * boss_hp_units(w, m) if boss else 0.0)
