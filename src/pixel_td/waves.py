"""Wave generation. All growth is exponential (see config). When the real enemy count
exceeds MAX_ENT_PER_WAVE, enemies are merged into *bundles*: one on-screen enemy then
stands for `bundle` real ones (hp, gold and leak damage are multiplied accordingly), so
the CPU cost stays flat while the displayed numbers keep exploding."""
import numpy as np
from .config import *
from .bignum import safe_pow, MAXF
from . import enemies as E


def hp_base(w):      return 20.0 * safe_pow(HP_G, w - 1)
def gold_base(w):    return 3.0 * safe_pow(GOLD_G, w - 1)
def leak_base(w):    return 4.0 * safe_pow(LEAK_G, w - 1)
def base_hp_max(w):  return 100.0 * safe_pow(BASE_G, w - 1)
def enemy_count(w):  return 6.0 * safe_pow(COUNT_G, w - 1)
def wave_bonus(w):   return int(40 * safe_pow(BONUS_G, w - 1))
def speed_scale(w):  return min(1.6, 1.0 + 0.004 * (w - 1))
def is_boss_wave(w): return w % 10 == 0
def boss_count(w):   return 1 + w // 40
def boss_type(w):    return E.TITAN if w % 20 == 0 else E.OVERLORD


class WaveSpec:
    pass


def make_wave(w, rng):
    boss = is_boss_wave(w)
    total = enemy_count(w) * (0.6 if boss else 1.0)
    n = int(max(1, min(MAX_ENT_PER_WAVE, round(total))))
    bundle = max(1.0, total / n)

    avail = [t for t in E.NORMAL_TYPES if E.ETYPES[t].first_wave <= w]
    wts = np.array([E.ETYPES[t].weight for t in avail], float)
    if len(avail) > 1 and w >= 3 and rng.random() < 0.35:       # "rush" waves
        wts[rng.integers(len(avail))] *= 3.0
    wts /= wts.sum()
    typ = rng.choice(avail, size=n, p=wts).astype(np.int64)

    s = WaveSpec()
    s.w, s.boss = w, boss
    hp = hp_base(w) * E.T_HPM[typ] * bundle
    armor = np.minimum(E.T_ARM_C[typ], E.T_ARM_B[typ] + E.T_ARM_P[typ] * w)
    dmg = leak_base(w) * E.T_DMGM[typ] * bundle
    gold = gold_base(w) * E.T_GOLDM[typ] * bundle
    spd = E.T_SPEED[typ] * speed_scale(w)
    bun = np.full(n, bundle)

    if boss:
        nb = boss_count(w)
        b = boss_type(w)
        budget = enemy_count(w) * hp_base(w)
        typ = np.concatenate([typ, np.full(nb, b)])
        hp = np.concatenate([hp, np.full(nb, 0.8 * budget / nb)])
        armor = np.concatenate([armor, np.full(nb, min(E.T_ARM_C[b], E.T_ARM_B[b] + E.T_ARM_P[b] * w))])
        dmg = np.concatenate([dmg, np.full(nb, 0.5 * base_hp_max(w) / nb)])
        gold = np.concatenate([gold, np.full(nb, 0.6 * enemy_count(w) * gold_base(w) / nb)])
        spd = np.concatenate([spd, np.full(nb, E.T_SPEED[b] * speed_scale(w))])
        bun = np.concatenate([bun, np.ones(nb)])

    s.n = int(typ.size)
    s.typ = typ
    s.hp = np.minimum(hp, MAXF)
    s.armor, s.dmg = armor, np.minimum(dmg, MAXF)
    s.gold = np.minimum(gold, MAXF)
    s.speed, s.bundle = spd, bun
    s.evade, s.regen, s.sres = E.T_EVADE[typ], E.T_REGEN[typ], E.T_SRES[typ]
    s.shield = np.minimum(E.T_SHIELD[typ] * s.hp, MAXF)
    s.interval = float(np.clip(24.0 / s.n, 0.04, 0.9))
    s.suffix = np.concatenate([np.cumsum(bun[::-1])[::-1], [0.0]])
    s.total_real = float(s.suffix[0])
    return s


def wave_preview(w):
    boss = is_boss_wave(w)
    total = enemy_count(w) * (0.6 if boss else 1.0) + (boss_count(w) if boss else 0)
    names = [E.ETYPES[t].name for t in E.NORMAL_TYPES if E.ETYPES[t].first_wave <= w]
    return dict(total=total, hp=hp_base(w), boss=boss, names=names, bundled=total > MAX_ENT_PER_WAVE,
                boss_name=E.ETYPES[boss_type(w)].name if boss else "")
