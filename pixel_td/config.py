"""Global constants & balance knobs. Tweak the *_G growth rates to retune the game."""

# ---- window / layout -------------------------------------------------------
SCREEN_W, SCREEN_H = 1280, 720
FPS = 60
SIM_DT = 1.0 / 60.0            # fixed simulation step
MAX_TICKS_PER_FRAME = 16       # guards against spiral-of-death at high game speed
SPEEDS = [1, 2, 4, 8]

TILE = 40
GRID_W, GRID_H = 24, 14
MAP_W, MAP_H = GRID_W * TILE, GRID_H * TILE      # 960 x 560
TOP_H = 56
MAP_X, MAP_Y = 0, TOP_H
PANEL_X = MAP_W
PANEL_W = SCREEN_W - MAP_W                        # 320
BOTTOM_Y = MAP_Y + MAP_H                          # 616
PX = 4                                            # one "art pixel" = 4 screen px

# ---- path (tile coordinates; first/last points are off-screen) -------------
PATH_TILES = [(-1, 1), (20, 1), (20, 4), (3, 4), (3, 7), (20, 7),
              (20, 10), (3, 10), (3, 12), (24, 12)]
PATH_HALF = 22        # half width of the dirt road
PATH_CLEAR = 34       # min distance tower-centre <-> road centre-line
TOWER_SPACING = 30    # min distance between two towers
MAP_MARGIN = 14

# ---- performance -----------------------------------------------------------
MAX_ENEMIES = 1100          # capacity of the numpy enemy pool
MAX_ENT_PER_WAVE = 450      # beyond this, enemies are merged into "bundles"

# ---- progression -----------------------------------------------------------
START_GOLD = 150
WIN_WAVE = 50               # "victory" wave; the game can continue in endless mode

COUNT_G = 1.05    # enemy count growth / wave   (exponential)
HP_G = 1.155      # enemy hp growth / wave
GOLD_G = 1.145    # gold per kill growth / wave
LEAK_G = 1.12     # base damage of a leaking enemy growth / wave
BASE_G = 1.12     # base max-hp growth / wave
BONUS_G = 1.15    # wave-clear bonus growth / wave

DMG_G = 1.12      # tower damage per level
MILESTONE = 1.35   # extra damage multiplier every 10 levels
UPG_G = 1.165     # tower upgrade cost growth per level
UPG_BASE = 0.75   # first upgrade cost = tower cost * UPG_BASE
BUILD_G = 1.2     # build cost growth per tower already standing
SELL_RATIO = 0.7
