"""Prestige ("Ascension") meta-progression. Pure logic, persisted by save.py."""
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Upgrade:
    key: str
    name: str
    desc: str
    base: int
    growth: float
    max_level: int = 0       # 0 = unlimited


UPGRADES = [
    Upgrade("dmg", "Arcane Power", "+12% damage for all towers", 3, 1.55),
    Upgrade("gold", "Greed", "+10% gold from every source", 3, 1.55),
    Upgrade("rate", "Haste", "+3% attack speed", 4, 1.5, 50),
    Upgrade("base", "Fortress", "+15% base HP", 3, 1.5),
    Upgrade("start", "War Chest", "More gold at the start of a run", 5, 1.6),
    Upgrade("disc", "Bargain", "-2% tower build cost (max -40%)", 6, 1.5, 20),
    Upgrade("skill", "Sorcery", "-3% skill cooldowns (max -60%)", 6, 1.5, 20),
]
BY_KEY = {u.key: u for u in UPGRADES}


SHARD_MIN_WAVE = 20      # ending a run below this wave pays no Shards


def ascend_gain(wave, ap_mult=1.0):
    """Ascension Points for ending a run at `wave` (harder maps pay more).

    Polynomial up to wave 100 (about wave^1.8), then it DOUBLES every 100 waves, so very deep
    runs (500, 1000 ...) pay enormously more than shallow ones."""
    if wave < 5:
        return 0
    base = 0.5 * (wave / 5.0) ** 1.8
    boost = 2.0 ** min(max(0.0, wave - 100.0) / 100.0, 900.0)
    return int(base * boost * ap_mult)


def shard_gain(wave, map_level=1):
    """Legend Shards (premium currency): small amounts, slowly growing with depth and map difficulty."""
    if wave < SHARD_MIN_WAVE:
        return 0
    return 1 + int(wave) // 100 + (map_level - 1) // 2


class Meta:
    def __init__(self):
        self.levels = {u.key: 0 for u in UPGRADES}
        self.ap = 0                 # unspent ascension points
        self.total_ap = 0           # lifetime earned (permanent damage bonus, see dmg_mult)
        self.best_wave = 0
        self.ascensions = 0
        self.lifetime_kills = 0.0
        self.map_best = {}          # best wave per map key
        self.shards = 0             # premium currency (Legend Shards)
        self.total_shards = 0
        self.legends = set()        # legendary towers bought in the Vault (permanent)

    # ---- multipliers ---------------------------------------------------------
    def lv(self, k): return self.levels[k]
    def dmg_mult(self):   return (1 + 0.12 * self.lv("dmg")) * self.lifetime_mult()
    def lifetime_mult(self):
        """Permanent bonus from every AP ever earned: +5% x sqrt(lifetime AP) (sub-linear on purpose)."""
        return 1.0 + 0.05 * math.sqrt(float(min(self.total_ap, 10 ** 300)))
    def gold_mult(self):  return 1 + 0.10 * self.lv("gold")
    def rate_mult(self):  return 1 + 0.03 * self.lv("rate")
    def base_mult(self):  return 1 + 0.15 * self.lv("base")
    def build_mult(self): return max(0.6, 1 - 0.02 * self.lv("disc"))
    def skill_mult(self): return max(0.4, 1 - 0.03 * self.lv("skill"))
    def start_bonus(self): return int(100 * (1.6 ** self.lv("start") - 1))

    def effect_text(self, key, level=None):
        l = self.lv(key) if level is None else level
        return {
            "dmg": f"x{(1 + 0.12 * l):.2f}",
            "gold": f"x{(1 + 0.10 * l):.2f}",
            "rate": f"x{(1 + 0.03 * l):.2f}",
            "base": f"x{(1 + 0.15 * l):.2f}",
            "start": f"+{int(100 * (1.6 ** l - 1))}",
            "disc": f"-{min(40, 2 * l)}%",
            "skill": f"-{min(60, 3 * l)}%",
        }[key]

    # ---- shop ----------------------------------------------------------------
    def cost(self, key):
        u = BY_KEY[key]
        return int(math.ceil(u.base * u.growth ** self.levels[key]))

    def at_max(self, key):
        u = BY_KEY[key]
        return bool(u.max_level) and self.levels[key] >= u.max_level

    def can_buy(self, key):
        return not self.at_max(key) and self.ap >= self.cost(key)

    def buy(self, key):
        if not self.can_buy(key):
            return False
        self.ap -= self.cost(key)
        self.levels[key] += 1
        return True

    def buy_max(self, key):
        n = 0
        while n < 1000 and self.buy(key):
            n += 1
        return n

    # ---- legendary vault (premium currency) ---------------------------------------
    def owns_legend(self, key):
        return key in self.legends

    def can_buy_legend(self, key, price):
        return key not in self.legends and self.shards >= price

    def buy_legend(self, key, price):
        if not self.can_buy_legend(key, price):
            return False
        self.shards -= price
        self.legends.add(key)
        return True

    # ---- persistence ---------------------------------------------------------
    def to_dict(self):
        return dict(levels=self.levels, ap=self.ap, total_ap=self.total_ap, best_wave=self.best_wave,
                    ascensions=self.ascensions, lifetime_kills=self.lifetime_kills, map_best=self.map_best,
                    shards=self.shards, total_shards=self.total_shards, legends=sorted(self.legends))

    @classmethod
    def from_dict(cls, d):
        m = cls()
        if not isinstance(d, dict):
            return m
        for k, v in (d.get("levels") or {}).items():
            if k in m.levels:
                m.levels[k] = max(0, int(v))
        m.ap = max(0, int(d.get("ap", 0)))
        m.total_ap = max(0, int(d.get("total_ap", 0)))
        m.best_wave = max(0, int(d.get("best_wave", 0)))
        m.ascensions = max(0, int(d.get("ascensions", 0)))
        m.lifetime_kills = float(d.get("lifetime_kills", 0.0))
        m.shards = max(0, int(d.get("shards", 0)))
        m.total_shards = max(0, int(d.get("total_shards", 0)))
        lg = d.get("legends") or []
        m.legends = {str(k) for k in lg} if isinstance(lg, (list, tuple, set)) else set()
        mb = d.get("map_best") or {}
        m.map_best = {str(k): max(0, int(v)) for k, v in mb.items()} if isinstance(mb, dict) else {}
        return m
