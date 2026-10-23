"""Tower definitions, scaling and hit-scan combat (vectorised target queries).

18 regular towers in 6 categories + 5 legendary towers (one of each per run, they level up
by killing: XP = gold value of the enemies they kill)."""
import math
from dataclasses import dataclass
import numpy as np
from .config import *
from .bignum import safe_pow, MAXF, fmt, to_int
from .enemies import T_ISBOSS

MODE_NAMES = ["First", "Last", "Strongest", "Weakest", "Closest"]
VOID_BOSS = 0.15          # Void is only 15% as effective against bosses

# (key, short tab label, full name, blurb)
CATEGORIES = [
    ("SHOT", "SHOT", "MARKSMAN", "Single-target damage dealers."),
    ("BLAST", "BLAST", "ARTILLERY", "Explosions and shockwaves. Great vs packs."),
    ("ELEM", "ELEM", "ELEMENTAL", "Chain lightning, poison and fire."),
    ("CTRL", "CTRL", "CONTROL", "Slow, stun and weaken enemies."),
    ("SUPP", "SUPP", "SUPPORT", "Buff other towers and your economy."),
    ("SPEC", "SPEC", "SPECIAL", "Unusual damage rules."),
    ("LEG", "LEG", "LEGENDARY", "One of each per run. They level up by killing."),
]
CAT_KEYS = [c[0] for c in CATEGORIES]


@dataclass(frozen=True)
class TowerType:
    key: str
    name: str
    color: tuple
    cost: int             # regular: base gold price. legendary: FIXED price in Legend Shards (one-time, Vault)
    dmg: float
    range: float
    rate: float
    mode: int
    desc: str
    unlock: int = 0       # regular: best wave (across runs) to unlock. legendary: wave of the current run
    long: str = ""        # multi-line explanation shown in the build panel
    cat: str = "SHOT"
    legendary: bool = False


TOWER_TYPES = [
    # ---- original ten (indices 0-9 never change) -------------------------------------------------
    TowerType("archer", "Archer", (96, 176, 72), 40, 12, 150, 2.0, 0, "Fast & cheap. Crits.", 0,
              "Shoots one target very fast and can crit for big damage. Best value early on.", "SHOT"),
    TowerType("cannon", "Cannon", (210, 120, 60), 120, 45, 130, 0.7, 0, "Splash damage.", 0,
              "Shells explode and hurt every enemy in the blast radius (less at the edge). Great against packs.", "BLAST"),
    TowerType("frost", "Frost", (110, 200, 255), 90, 8, 120, 1.3, 4, "Area slow.", 0,
              "Slows every enemy in a small area. Slowed packs bunch up for your splash towers. Bosses resist slows.", "CTRL"),
    TowerType("tesla", "Tesla", (170, 110, 255), 250, 30, 110, 1.0, 0, "Chain lightning.", 5,
              "Lightning jumps between nearby enemies, 15% weaker per jump. More jumps with levels.", "ELEM"),
    TowerType("sniper", "Sniper", (230, 70, 70), 400, 220, 330, 0.35, 2, "Huge hit, pierces armor.", 8,
              "Slow shots, huge range, huge damage that ignores most armor. Aims at the strongest enemy. Ideal vs bosses.", "SHOT"),
    TowerType("toxin", "Toxin", (60, 230, 160), 200, 6, 120, 1.1, 0, "Poison ignores armor.", 3,
              "Poisons enemies in a small area. Poison damage over time ignores armor. Poison does not stack, it refreshes.", "ELEM"),
    TowerType("laser", "Laser", (255, 120, 170), 300, 4, 140, 8.0, 0, "Beam ramps up on one target.", 12,
              "Rapid beam. Damage grows up to x2.8 while it keeps hitting the same target. Partly ignores armor.", "SHOT"),
    TowerType("mortar", "Mortar", (200, 175, 90), 350, 160, 280, 0.25, 0, "Long-range big splash.", 16,
              "Slow artillery with huge range and a very large blast radius. Brilliant against thick crowds.", "BLAST"),
    TowerType("beacon", "Beacon", (255, 200, 60), 500, 0, 120, 0.0, 0, "Buffs damage of nearby towers.", 20,
              "Never attacks. Every tower inside its aura deals more damage (beacons add up). Upgrade for a stronger aura.", "SUPP"),
    TowerType("void", "Void", (120, 80, 210), 700, 10, 150, 0.8, 2, "Hits % of max HP (true damage).", 30,
              "Each hit removes a % of the target's MAX HP (true damage: ignores armor, shields and dodging) on several of "
              "the strongest enemies in range. It scales with enemy HP so it never falls behind. Bosses take only 15%.", "SPEC"),
    # ---- new regular towers ----------------------------------------------------------------------
    TowerType("ballista", "Ballista", (190, 140, 80), 180, 70, 210, 0.8, 0, "Bolt pierces a whole line.", 6,
              "Fires a heavy bolt that pierces EVERYTHING on the line between the tower and its target. "
              "Place it along a straight road to skewer whole squads.", "SHOT"),
    TowerType("flame", "Flame", (255, 90, 40), 220, 5, 95, 5.0, 0, "Burns everything around it.", 10,
              "Short range, but burns EVERY enemy in range several times a second and sets them on fire "
              "(fire damage ignores armor). Put it right beside the road.", "ELEM"),
    TowerType("shock", "Shockwave", (150, 170, 205), 320, 120, 115, 0.4, 0, "Blast + knockback.", 14,
              "Emits a pulse that damages every enemy in range and PUSHES them back along the road, "
              "buying time for everything else. Bosses are pushed 70% less.", "BLAST"),
    TowerType("stasis", "Stasis", (150, 255, 240), 280, 15, 130, 0.35, 0, "Stuns a whole area.", 18,
              "Freezes enemies in an area in place for a short time. Stunned packs pile up for your splash towers. "
              "Bosses are stunned 80% shorter.", "CTRL"),
    TowerType("hexer", "Hexer", (200, 60, 160), 260, 4, 140, 0.9, 0, "Enemies take more damage.", 22,
              "Curses enemies in an area: for 4 seconds they take extra damage from EVERY tower (and the Void). "
              "Bosses take half the curse.", "CTRL"),
    TowerType("overclock", "Overclock", (200, 255, 80), 450, 0, 130, 0.0, 0, "Towers nearby shoot faster.", 26,
              "Never attacks. Towers inside its aura fire faster (several Overclocks add up). "
              "Stack with Beacons for huge multipliers.", "SUPP"),
    TowerType("mint", "Mint", (255, 235, 140), 550, 0, 0, 0.0, 0, "Global gold bonus.", 12,
              "Never attacks and has no range: every Mint gives a permanent % bonus to ALL gold you earn "
              "(kills and wave bonuses). Upgrade it to raise the bonus.", "SUPP"),
    TowerType("exec", "Executioner", (170, 30, 45), 350, 40, 170, 0.7, 3, "Executes weak enemies.", 24,
              "Hits one enemy and instantly kills it if its HP is below a threshold. Bosses below the threshold "
              "take triple damage instead. Set to Weakest to clean up packs.", "SPEC"),
    # ---- legendary (one per run, level up by killing) --------------------------------------------
    TowerType("phoenix", "Phoenix", (255, 140, 40), 3, 120, 175, 1.2, 0, "Fire nova every 6th shot.", 10,
              "Shells burst into flames (splash + burning). Every 6th shot is a NOVA that hits EVERY enemy in range "
              "for triple damage. Levels up from kills.", "LEG", True),
    TowerType("midas", "Midas", (255, 220, 60), 5, 90, 165, 1.5, 0, "Kills in range pay extra gold.", 15,
              "Golden splash shots. Enemies that die inside its range drop bonus gold. Gains XP from kills, "
              "and the more it kills the more it pays.", "LEG", True),
    TowerType("thunder", "Thunderlord", (120, 200, 255), 8, 80, 190, 1.0, 0, "Mega chain + Smite.", 20,
              "Chain lightning with many jumps. Every 5 seconds SMITE strikes the strongest enemy ANYWHERE on the map "
              "for massive damage. Great against bosses.", "LEG", True),
    TowerType("chronos", "Chronos", (120, 255, 220), 11, 60, 200, 1.0, 0, "Slows all in range, stops time.", 25,
              "A permanent slow aura on every enemy in range, plus TIME STOP: periodically freezes everything in range. "
              "Pair it with splash towers.", "LEG", True),
    TowerType("reaper", "Reaper", (120, 30, 160), 15, 50, 180, 1.4, 2, "Harvests the weak, doubles XP.", 30,
              "Strikes several of the strongest enemies with % max-HP damage and executes anything under a HP "
              "threshold. Earns double XP from kills.", "LEG", True),
]
BY_KEY = {t.key: t for t in TOWER_TYPES}
INDEX = {t.key: i for i, t in enumerate(TOWER_TYPES)}


def cat_indices(cat_key):
    return [i for i, t in enumerate(TOWER_TYPES) if t.cat == cat_key]


# ---- legendary levelling -------------------------------------------------------------------------
def legend_level(xp):
    return 1 + int(math.log(1.0 + xp * (LEG_G - 1.0) / LEG_B) / math.log(LEG_G))


def legend_xp_for(level):
    """XP needed to REACH `level`."""
    return LEG_B * (safe_pow(LEG_G, level - 1) - 1.0) / (LEG_G - 1.0)


class Tower:
    def __init__(self, tt, x, y, paid, meta=None):
        self.tt, self.x, self.y, self.meta = tt, x, y, meta
        self.uid = 0
        self.level = 1
        self.cd = 0.0
        self.flash = 0.0
        self.mode = tt.mode
        self.invested = int(paid)
        self.buff = 1.0           # damage multiplier from Beacons (set by Simulation)
        self.haste = 1.0          # fire-rate multiplier from Overclocks
        self.prio = 0             # auto-upgrade priority: 0 none, 1 highest .. 3
        self.kills = 0.0
        self.xp = 0.0
        self.stacks = 0           # laser ramp
        self.last = -1
        self.shots = 0            # phoenix nova counter
        self.timer = 3.0          # thunderlord smite timer
        self.aura_t = 0.0         # chronos aura tick
        self.stop_t = 8.0         # chronos time-stop timer
        self.recalc()

    # ---- stats ---------------------------------------------------------------
    def recalc(self):
        tt, l, m = self.tt, self.level, self.meta
        dm = m.dmg_mult() if m else 1.0
        rm = m.rate_mult() if m else 1.0
        if tt.legendary:
            base = tt.dmg * safe_pow(LEG_DMG_G, l - 1)
            self.range = tt.range * (1 + min(0.6, 0.005 * (l - 1)))
            self.rate = tt.rate * (1 + min(1.0, 0.005 * (l - 1))) * rm
        else:
            base = tt.dmg * safe_pow(DMG_G, l - 1) * safe_pow(MILESTONE, l // 10)
            self.range = tt.range * (1 + min(0.6, 0.006 * (l - 1)))
            self.rate = tt.rate * (1 + min(1.5, 0.01 * (l - 1))) * rm
        self.damage = min(MAXF, base * dm)
        self.crit = self.crit_mult = self.splash = self.slow_amt = self.slow_dur = 0.0
        self.chain = self.void_n = 0
        self.pierce = self.aura = self.void_pct = 0.0
        self.poison_dur = 0.0
        self.knock = self.stun_dur = self.vuln_amt = self.haste_aura = self.mint_aura = 0.0
        self.exec_frac = self.gold_bonus = self.xp_mult = 0.0
        self.stop_cd = 14.0
        k = tt.key
        if k == "archer":
            self.crit, self.crit_mult = 0.10 + min(0.40, 0.005 * (l - 1)), 2.5 + 0.02 * (l - 1)
        elif k == "cannon":
            self.splash = 60 * (1 + min(0.8, 0.01 * (l - 1)))
        elif k == "frost":
            self.splash, self.slow_amt, self.slow_dur = 65, 0.35 + min(0.45, 0.01 * (l - 1)), 2.0
        elif k == "tesla":
            self.chain = min(14, 3 + l // 8)
        elif k == "sniper":
            self.pierce = 0.6 + min(0.3, 0.004 * (l - 1))
        elif k == "toxin":
            self.splash, self.poison_dur = 55, 3.0
        elif k == "laser":
            self.pierce = 0.3
        elif k == "mortar":
            self.splash = 100 * (1 + min(0.8, 0.01 * (l - 1)))
        elif k == "beacon":
            self.aura = min(1e6, 0.2 * safe_pow(1.03, l - 1))
        elif k == "void":
            self.void_pct = min(0.20, 0.03 + 0.0027 * (l - 1))     # of target MAX HP per hit
            self.void_n = min(12, 2 + l // 10)
        elif k == "ballista":
            self.pierce = 0.2 + min(0.5, 0.004 * (l - 1))
        elif k == "shock":
            self.knock = min(150.0, 35.0 + 0.6 * (l - 1))
        elif k == "stasis":
            self.splash, self.stun_dur = 75, min(3.0, 1.0 + 0.02 * (l - 1))
        elif k == "hexer":
            self.splash, self.vuln_amt = 70, 0.20 + min(1.0, 0.01 * (l - 1))
        elif k == "overclock":
            self.haste_aura = min(3.0, 0.15 * safe_pow(1.025, l - 1))
        elif k == "mint":
            self.mint_aura = min(5.0, 0.05 + 0.004 * (l - 1))
        elif k == "exec":
            self.exec_frac = min(0.5, 0.15 + 0.002 * (l - 1))
        elif k == "phoenix":
            self.splash = 80 * (1 + min(1.0, 0.01 * (l - 1)))
        elif k == "midas":
            self.splash, self.gold_bonus = 55, min(3.0, 0.5 + 0.01 * (l - 1))
        elif k == "thunder":
            self.chain = min(30, 8 + l // 5)
        elif k == "chronos":
            self.slow_amt = min(0.8, 0.5 + 0.003 * (l - 1))
            self.stop_cd = max(6.0, 14.0 / (1 + 0.01 * (l - 1)))
        elif k == "reaper":
            self.void_n = min(15, 3 + l // 10)
            self.void_pct = min(0.05, 0.015 + 0.0003 * (l - 1))
            self.exec_frac = min(0.4, 0.2 + 0.001 * (l - 1))
            self.xp_mult = 2.0
        if not self.xp_mult:
            self.xp_mult = 1.0

    def special_text(self):
        k = self.tt.key
        if k == "archer": return f"Crit {self.crit*100:.0f}% x{self.crit_mult:.1f}"
        if k in ("cannon", "mortar"): return f"Splash {self.splash:.0f}px"
        if k == "frost":  return f"Slow {self.slow_amt*100:.0f}% / {self.splash:.0f}px"
        if k == "tesla":  return f"Chain {self.chain} targets"
        if k == "sniper": return f"Pierce {self.pierce*100:.0f}% armor"
        if k == "laser":  return "Ramp up to x2.8"
        if k == "beacon": return f"+{self.aura*100:.0f}% dmg in range"
        if k == "void":   return f"{self.void_pct*100:.1f}% max HP"
        if k == "ballista": return f"Line pierce, {self.pierce*100:.0f}% armor"
        if k == "flame":  return "Burns all in range"
        if k == "shock":  return f"Knockback {self.knock:.0f}px"
        if k == "stasis": return f"Stun {self.stun_dur:.1f}s / {self.splash:.0f}px"
        if k == "hexer":  return f"+{self.vuln_amt*100:.0f}% dmg taken"
        if k == "overclock": return f"+{self.haste_aura*100:.0f}% fire rate"
        if k == "mint":   return f"+{self.mint_aura*100:.0f}% gold (global)"
        if k == "exec":   return f"Execute < {self.exec_frac*100:.0f}% HP"
        if k == "phoenix": return f"Nova /6th shot, {self.splash:.0f}px"
        if k == "midas":  return f"+{self.gold_bonus*100:.0f}% gold on kills"
        if k == "thunder": return f"Chain {self.chain} + Smite 5s"
        if k == "chronos": return f"Slow {self.slow_amt*100:.0f}% + Time Stop"
        if k == "reaper": return f"Execute < {self.exec_frac*100:.0f}% HP"
        return f"Poison {fmt(self.damage * self.buff * 2)}/s"

    def detail_lines(self):
        """Extra (label, value) rows for the selected-tower panel."""
        k = self.tt.key
        if k == "void":
            return [("Boss hit", f"{self.void_pct*VOID_BOSS*100:.2f}% max HP"),
                    ("Targets", f"{self.void_n} strongest")]
        if k == "flame":
            return [("Burn", f"{fmt(self.damage * self.buff * 1.5)}/s")]
        if k == "reaper":
            return [("Targets", f"{self.void_n}"), ("Hit", f"{self.void_pct*100:.1f}% max HP")]
        if k == "chronos":
            return [("Time Stop", f"every {self.stop_cd:.0f}s")]
        if k == "phoenix":
            return [("Burn", f"{fmt(self.damage * self.buff * 2)}/s")]
        return []

    # ---- legendary XP ---------------------------------------------------------
    def add_xp(self, amount):
        """Returns True if the tower levelled up."""
        self.xp = min(MAXF, self.xp + amount)
        nl = legend_level(self.xp)
        if nl > self.level:
            self.set_level(nl)
            return True
        return False

    def xp_progress(self):
        lo, hi = legend_xp_for(self.level), legend_xp_for(self.level + 1)
        return max(0.0, min(1.0, (self.xp - lo) / (hi - lo))) if hi > lo else 1.0

    # ---- upgrade economy (regular towers) ------------------------------------
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


def _top_n(pool, cand, n):
    if cand.size > n:
        return cand[np.argpartition(-pool.hp[cand], n - 1)[:n]]
    return cand


def _chain(pool, tg, tx, ty, t, jumps, falloff, dmg, fx, col, jump_range=90.0):
    hit = [int(tg)]
    cur = tg
    pts = [(t.x, t.y - 18), (tx, ty)]
    for _ in range(jumps - 1):
        cx, cy = float(pool.x[cur]), float(pool.y[cur])
        ii, d2s = _in_radius(pool, cx, cy, jump_range)
        ok = ~np.isin(ii, hit)
        if not ok.any():
            break
        ii, d2s = ii[ok], d2s[ok]
        cur = ii[int(np.argmin(d2s))]
        hit.append(int(cur))
        pts.append((float(pool.x[cur]), float(pool.y[cur])))
    pool.damage(np.array(hit), dmg * (falloff ** np.arange(len(hit))))
    fx.bolt(pts, col)


def tower_fire(sim, t):
    """Try to shoot. Returns True if a shot was fired."""
    pool, fx, rng = sim.pool, sim.fx, sim.rng
    i = pool.idx
    if i.size == 0:
        return False
    dx, dy = pool.x[i] - t.x, pool.y[i] - t.y
    d2 = dx * dx + dy * dy
    m = d2 <= t.range * t.range
    if not m.any():
        return False
    pool.cur_src = t.uid
    cand, cd2 = i[m], d2[m]
    tg = _pick(pool, cand, cd2, t.mode)
    tx, ty = float(pool.x[tg]), float(pool.y[tg])
    col = t.tt.color
    k = t.tt.key
    D = t.damage * t.buff
    t.flash = 0.1
    one = np.array([tg])
    sy = t.y - 18

    if k == "archer":
        dmg = D
        if rng.random() < t.crit:
            dmg *= t.crit_mult
            fx.text(tx, ty - 18, fmt(dmg), (255, 230, 80))
        pool.damage(one, dmg)
        fx.line([(t.x, sy), (tx, ty)], col, 0.08, 2)
        fx.burst(tx, ty, col, 3, 60, 0.25, 2)
    elif k == "sniper":
        pool.damage(one, D, t.pierce)
        fx.line([(t.x, sy), (tx, ty)], (255, 255, 255), 0.14, 3)
        fx.line([(t.x, sy), (tx, ty)], col, 0.2, 5)
        fx.burst(tx, ty, (255, 220, 200), 6, 110, 0.3, 4)
    elif k == "ballista":
        ux, uy = tx - t.x, ty - t.y
        L = math.hypot(ux, uy) or 1.0
        ux, uy = ux / L, uy / L
        px, py = pool.x[i] - t.x, pool.y[i] - t.y
        proj = px * ux + py * uy
        perp = np.abs(px * uy - py * ux)
        ii = i[(proj >= 0) & (proj <= t.range) & (perp <= 16)]
        pool.damage(ii, D, t.pierce)
        ex, ey = t.x + ux * t.range, t.y + uy * t.range
        fx.line([(t.x, sy), (ex, ey)], (255, 235, 190), 0.12, 3)
        fx.line([(t.x, sy), (ex, ey)], col, 0.2, 5)
        fx.burst(tx, ty, col, 5, 90, 0.3, 4)
    elif k in ("cannon", "mortar"):
        ii, d2s = _in_radius(pool, tx, ty, t.splash)
        fall = 1.0 - (0.4 if k == "mortar" else 0.5) * np.sqrt(d2s) / t.splash
        pool.damage(ii, D * fall)
        fx.line([(t.x, sy), (tx, ty)], (255, 200, 120), 0.07, 3)
        fx.ring(tx, ty, 6, t.splash, (255, 170, 60) if k == "cannon" else (240, 220, 120), 0.28, 3)
        fx.burst(tx, ty, (255, 140, 40), 8 if k == "cannon" else 14, 130, 0.4, 4)
        fx.shake_add(1.5 if k == "cannon" else 3)
    elif k == "shock":
        pool.damage(cand, D)
        pool.knockback(cand, t.knock)
        fx.ring(t.x, t.y, 8, t.range, col, 0.35, 4)
        fx.burst(t.x, t.y, col, 10, 120, 0.4, 4)
        fx.shake_add(2.5)
    elif k == "frost":
        ii, _ = _in_radius(pool, tx, ty, t.splash)
        pool.damage(ii, D)
        pool.apply_slow(ii, t.slow_amt, t.slow_dur)
        fx.ring(tx, ty, 6, t.splash, col, 0.35, 3)
        fx.burst(tx, ty, (220, 245, 255), 6, 70, 0.4, 2)
        fx.line([(t.x, sy), (tx, ty)], (180, 230, 255), 0.06, 2)
    elif k == "stasis":
        ii, _ = _in_radius(pool, tx, ty, t.splash)
        pool.damage(ii, D)
        pool.apply_stun(ii, t.stun_dur)
        fx.ring(tx, ty, 6, t.splash, col, 0.5, 3)
        fx.burst(tx, ty, (220, 255, 250), 8, 60, 0.5, 2)
        fx.line([(t.x, sy), (tx, ty)], col, 0.1, 2)
    elif k == "hexer":
        ii, _ = _in_radius(pool, tx, ty, t.splash)
        pool.damage(ii, D)
        pool.apply_vuln(ii, t.vuln_amt, 4.0)
        fx.ring(tx, ty, 6, t.splash, col, 0.45, 3)
        fx.burst(tx, ty, (255, 140, 220), 6, 60, 0.5, 2)
        fx.line([(t.x, sy), (tx, ty)], col, 0.08, 2)
    elif k == "toxin":
        ii, _ = _in_radius(pool, tx, ty, t.splash)
        pool.damage(ii, D)
        pool.apply_poison(ii, D * 2.0, t.poison_dur)
        fx.ring(tx, ty, 4, t.splash, col, 0.4, 3)
        fx.burst(tx, ty, col, 6, 50, 0.5, 4)
        fx.line([(t.x, sy), (tx, ty)], col, 0.06, 2)
    elif k == "flame":
        pool.damage(cand, D)
        pool.apply_poison(cand, D * 1.5, 2.0)
        fx.ring(t.x, t.y, 10, t.range, (255, 140, 40), 0.16, 2)
        fx.burst(t.x, t.y, (255, 160, 50), 4, 100, 0.3, 4)
    elif k == "tesla":
        _chain(pool, tg, tx, ty, t, t.chain, 0.85, D, fx, col)
        fx.burst(tx, ty, (230, 200, 255), 4, 80, 0.25, 2)
    elif k == "laser":
        t.stacks = min(15, t.stacks + 1) if int(tg) == t.last else 0
        t.last = int(tg)
        pool.damage(one, D * (1.0 + 0.12 * t.stacks), t.pierce)
        fx.line([(t.x, sy), (tx, ty)], (255, 230, 240), 0.05, 1 + t.stacks // 6)
        if t.stacks >= 8:
            fx.burst(tx, ty, col, 1, 40, 0.2, 2)
    elif k == "void":
        sel = _top_n(pool, cand, t.void_n)
        pool.damage(sel, D)
        frac = t.void_pct * np.where(T_ISBOSS[pool.typ[sel]], VOID_BOSS, 1.0)
        pool.true_damage(sel, pool.maxhp[sel] * frac)
        for j in sel:
            jx, jy = float(pool.x[j]), float(pool.y[j])
            fx.line([(t.x, sy), (jx, jy)], col, 0.12, 2)
            fx.ring(jx, jy, 4, 22, col, 0.3, 2)
            fx.burst(jx, jy, (200, 160, 255), 3, 60, 0.3, 2)
    elif k == "exec":
        pool.damage(one, D)
        frac = float(pool.hp[tg] / pool.maxhp[tg])
        if pool.hp[tg] > 0 and frac <= t.exec_frac:
            if T_ISBOSS[pool.typ[tg]]:
                pool.true_damage(one, D * 2.0)
            else:
                pool.hp[tg] = 0.0
                fx.text(tx, ty - 16, "EXECUTE", (255, 80, 80))
        fx.line([(t.x, sy), (tx, ty)], (255, 120, 120), 0.1, 3)
        fx.burst(tx, ty, col, 5, 90, 0.3, 4)
    # ---- legendary ----------------------------------------------------------------------------
    elif k == "phoenix":
        t.shots += 1
        nova = t.shots % 6 == 0
        if nova:
            ii, mult = cand, 3.0
            fx.ring(t.x, t.y, 10, t.range, (255, 200, 80), 0.5, 5)
            fx.burst(t.x, t.y, (255, 180, 60), 24, 200, 0.6, 4)
            fx.shake_add(4)
        else:
            ii, _ = _in_radius(pool, tx, ty, t.splash)
            mult = 1.0
            fx.ring(tx, ty, 6, t.splash, (255, 150, 50), 0.3, 3)
            fx.burst(tx, ty, (255, 120, 40), 8, 120, 0.4, 4)
        pool.damage(ii, D * mult)
        pool.apply_poison(ii, D * 2.0, 3.0)
        fx.line([(t.x, sy), (tx, ty)], (255, 210, 120), 0.1, 4)
    elif k == "midas":
        ii, _ = _in_radius(pool, tx, ty, t.splash)
        pool.damage(ii, D)
        fx.line([(t.x, sy), (tx, ty)], (255, 240, 150), 0.1, 4)
        fx.ring(tx, ty, 5, t.splash, (255, 220, 60), 0.3, 3)
        fx.burst(tx, ty, (255, 230, 90), 8, 100, 0.4, 4)
    elif k == "thunder":
        _chain(pool, tg, tx, ty, t, t.chain, 0.92, D, fx, col, jump_range=110.0)
        fx.burst(tx, ty, (200, 230, 255), 6, 100, 0.3, 4)
    elif k == "chronos":
        pool.damage(one, D, 0.5)
        fx.line([(t.x, sy), (tx, ty)], col, 0.1, 3)
        fx.burst(tx, ty, (200, 255, 245), 5, 70, 0.4, 2)
    elif k == "reaper":
        sel = _top_n(pool, cand, t.void_n)
        pool.damage(sel, D)
        boss = T_ISBOSS[pool.typ[sel]]
        pool.true_damage(sel, pool.maxhp[sel] * t.void_pct * np.where(boss, VOID_BOSS, 1.0))
        weak = sel[(pool.hp[sel] > 0) & (pool.hp[sel] <= pool.maxhp[sel] * t.exec_frac) & ~boss]
        pool.hp[weak] = 0.0
        for j in sel:
            jx, jy = float(pool.x[j]), float(pool.y[j])
            fx.line([(t.x, sy), (jx, jy)], (200, 120, 255), 0.12, 2)
            fx.burst(jx, jy, (170, 90, 220), 3, 60, 0.3, 2)
    else:  # beacon / overclock / mint never fire
        return False
    return True


def legend_tick(sim, t, dt):
    """Per-step logic for legendary towers (timed abilities, auras)."""
    pool, fx = sim.pool, sim.fx
    k = t.tt.key
    if k == "thunder":
        t.timer -= dt
        if t.timer <= 0 and pool.count:
            t.timer = 5.0
            i = pool.idx
            tg = i[int(np.argmax(pool.hp[i]))]
            one = np.array([tg])
            pool.cur_src = t.uid
            pool.damage(one, t.damage * t.buff * 8.0)
            boss = bool(T_ISBOSS[pool.typ[tg]])
            pool.true_damage(one, pool.maxhp[one] * 0.01 * (0.2 if boss else 1.0))
            tx, ty = float(pool.x[tg]), float(pool.y[tg])
            fx.bolt([(tx, -30.0), (tx, ty)], (200, 235, 255))
            fx.ring(tx, ty, 8, 70, (200, 235, 255), 0.4, 4)
            fx.burst(tx, ty, (220, 240, 255), 14, 160, 0.5, 4)
            fx.shake_add(5)
    elif k == "chronos":
        t.aura_t -= dt
        t.stop_t -= dt
        if pool.count and (t.aura_t <= 0 or t.stop_t <= 0):
            ii, _ = _in_radius(pool, t.x, t.y, t.range)
            if t.aura_t <= 0:
                t.aura_t = 0.25
                if ii.size:
                    pool.apply_slow(ii, t.slow_amt, 0.5)
            if t.stop_t <= 0:
                t.stop_t = t.stop_cd
                if ii.size:
                    pool.apply_stun(ii, 2.0)
                fx.ring(t.x, t.y, 10, t.range, (150, 255, 235), 0.8, 5)
                fx.shake_add(3)
