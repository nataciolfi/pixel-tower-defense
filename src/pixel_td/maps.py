"""The five maps. Each map is one difficulty tier: a different road layout (shorter road =
less time under fire), its own visual theme and its own scaling constants.

All maps start alike (see waves.EARLY_WAVES); after wave 10 each map's own growth rates take over.
"""
from dataclasses import dataclass
from .config import PATH_TILES


@dataclass(frozen=True)
class MapDef:
    key: str
    name: str
    difficulty: str
    level: int            # 1..5 (pips shown in the UI)
    desc: str
    tiles: tuple          # road waypoints in tile coordinates (first/last are off-screen)
    theme: str
    hp_mult: float        # multiplies all enemy HP
    hp_g: float           # enemy HP growth per wave (after wave 10)
    count_g: float        # enemy count growth per wave (after wave 10)
    gold_g: float         # gold-per-kill growth per wave (after wave 10)
    gold_mult: float
    leak_mult: float      # damage to the base when an enemy leaks
    regen: float          # fraction of base max HP healed after each cleared wave
    boss_k: float         # boss HP = boss_k * (1 + wave/25) * a grunt's HP
    speed_mult: float
    ap_mult: float        # Ascension Points multiplier
    start_gold: int = 150


MAPS = [
    MapDef("meadow", "Green Meadow", "EASY", 1,
           "A long winding road. Plenty of time to shoot.",
           tuple(PATH_TILES), "meadow",
           hp_mult=1.0, hp_g=1.155, count_g=1.045, gold_g=1.145, gold_mult=1.0,
           leak_mult=0.7, regen=0.06, boss_k=2.5, speed_mult=0.95, ap_mult=1.0, start_gold=150),
    MapDef("canyon", "Dusty Canyon", "NORMAL", 2,
           "Shorter road, tougher enemies.",
           ((-1, 1), (21, 1), (21, 5), (2, 5), (2, 9), (21, 9), (21, 12), (24, 12)), "canyon",
           hp_mult=1.0, hp_g=1.164, count_g=1.048, gold_g=1.145, gold_mult=1.0,
           leak_mult=0.95, regen=0.03, boss_k=3.0, speed_mult=1.0, ap_mult=1.5, start_gold=220),
    MapDef("frozen", "Frozen Pass", "HARD", 3,
           "Three long lanes. Fast, sturdy enemies and little healing.",
           ((-1, 2), (18, 2), (18, 6), (5, 6), (5, 10), (24, 10)), "frozen",
           hp_mult=1.0, hp_g=1.165, count_g=1.048, gold_g=1.147, gold_mult=1.0,
           leak_mult=1.15, regen=0.02, boss_k=3.3, speed_mult=1.05, ap_mult=2.2, start_gold=320),
    MapDef("lava", "Ember Gorge", "EXPERT", 4,
           "A zig-zag through the lava. Every leak hurts.",
           ((-1, 3), (8, 3), (8, 10), (14, 10), (14, 5), (19, 5), (19, 10), (24, 10)), "lava",
           hp_mult=1.0, hp_g=1.166, count_g=1.049, gold_g=1.148, gold_mult=1.0,
           leak_mult=1.3, regen=0.012, boss_k=3.6, speed_mult=1.10, ap_mult=3.2, start_gold=450),
    MapDef("void", "Void Rift", "INSANE", 5,
           "Barely any road and no healing. Good luck.",
           ((-1, 4), (10, 4), (10, 9), (16, 9), (16, 3), (24, 3)), "void",
           hp_mult=1.0, hp_g=1.168, count_g=1.050, gold_g=1.150, gold_mult=1.0,
           leak_mult=1.5, regen=0.0, boss_k=4.0, speed_mult=1.15, ap_mult=5.0, start_gold=600),
]
BY_KEY = {m.key: m for m in MAPS}
DEFAULT_MAP = "meadow"
