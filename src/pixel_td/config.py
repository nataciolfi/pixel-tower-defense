"""Global constants & balance knobs. Tweak the *_G growth rates to retune the game."""

APP_NAME = "Pixel Tower Defense"
APP_ID = "pixel-td"

# ---- window / layout -------------------------------------------------------
SCREEN_W, SCREEN_H = 1280, 720
FPS = 60
SIM_DT = 1.0 / 60.0            # fixed simulation step
MAX_TICKS_PER_FRAME = 512      # hard cap; the real limit is TICK_BUDGET (wall-clock seconds per frame)
TICK_BUDGET = 0.010            # max seconds per frame spent simulating (keeps the UI responsive at x64)
SPEEDS = [1, 2, 4, 8, 16, 32, 64]
FX_MAX_SPEED_INDEX = 2         # effects are disabled above this speed (x4) to save CPU

TILE = 40
GRID_W, GRID_H = 24, 14
MAP_W, MAP_H = GRID_W * TILE, GRID_H * TILE      # 960 x 560
TOP_H = 56
MAP_X, MAP_Y = 0, TOP_H
PANEL_X = MAP_W
PANEL_W = SCREEN_W - MAP_W                        # 320
BOTTOM_Y = MAP_Y + MAP_H                          # 616
PX = 4                                            # one "art pixel" = 4 screen px

# ---- default path (Green Meadow). Every map defines its own, see maps.py -----
PATH_TILES = [(-1, 1), (20, 1), (20, 4), (3, 4), (3, 7), (20, 7),
              (20, 10), (3, 10), (3, 12), (24, 12)]
PATH_HALF = 22        # half width of the dirt road
PATH_CLEAR = 34       # min distance tower-centre <-> road centre-line
TOWER_SPACING = 30    # min distance between two towers
REPAIR_FRACTION = 0.25  # base HP restored by one Repair
MAP_MARGIN = 14

# ---- performance -----------------------------------------------------------
MAX_ENEMIES = 1100          # capacity of the numpy enemy pool
MAX_ENT_PER_WAVE = 450      # beyond this, enemies are merged into "bundles"

# ---- progression -----------------------------------------------------------
START_GOLD = 150
WIN_WAVE = 50               # "victory" wave; the game can continue in endless mode

# Enemy scaling (HP, count, gold, leak damage, regen ...) now lives per map in maps.py.
BASE_G = 1.12     # base max-hp growth / wave (display + Fortress upgrade; leaks are a *fraction* of it)
BONUS_G = 1.15    # wave-clear bonus growth / wave

DMG_G = 1.12      # tower damage per level
MILESTONE = 1.35  # extra damage multiplier every 10 levels
UPG_G = 1.165     # tower upgrade cost growth per level
UPG_BASE = 0.75   # first upgrade cost = tower cost * UPG_BASE
BUILD_G = 1.2     # build cost growth per tower already standing
SELL_RATIO = 0.7
AUTO_INTERVAL = 0.25       # seconds (sim time) between auto-upgrade passes

# Legendary towers: level from the gold value of enemies they kill (XP)
LEG_B = 30.0               # XP needed for level 2
LEG_G = 1.3                # XP growth per level
LEG_DMG_G = 1.25           # legendary damage growth per level (keeps pace with enemy HP growth)

SAVE_VERSION = 1
