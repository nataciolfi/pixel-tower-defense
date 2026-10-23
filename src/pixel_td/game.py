"""Main application: scenes, input, fixed-timestep loop, save/load glue."""
import time
import pygame
from .config import *
from .sim import Simulation, PREP, WAVE, LOST, NullFx
from .meta import Meta
from .save import SaveStore
from .sprites import Sprites
from .effects import Effects
from .render import WorldRenderer, MAP_RECT
from .ui import UI
from .menu import Menu, MapSelect, MetaScreen, HelpScreen
from .maps import MAPS, BY_KEY as MAP_BY_KEY, DEFAULT_MAP
from .pathing import Path
from .bignum import fmt
from .towers import TOWER_TYPES, CATEGORIES, cat_indices


def make_fonts():
    names = "dejavusansmono,couriernew,consolas,liberationmono,freemono,monospace"
    path = pygame.font.match_font(names, bold=True)
    fonts = {}
    for sz in (12, 14, 16, 20, 24, 40):
        fonts[sz] = pygame.font.Font(path, sz) if path else pygame.font.Font(None, sz + 6)
    return fonts


class Game:
    def __init__(self, screen, store=None, seed=None, fullscreen=False):
        self.screen = screen
        self.store = store or SaveStore()
        data = self.store.load()
        self.meta = Meta.from_dict(data.get("meta"))
        self.run_data = data.get("run") if isinstance((data.get("run")), dict) else None
        self.fullscreen = bool((data.get("settings") or {}).get("fullscreen", False)) or fullscreen
        self.fonts = make_fonts()
        self.fx = Effects(self.fonts[14])
        self.sim = Simulation(self.fx, seed=seed, meta=self.meta)
        self.sprites = Sprites(MAPS)
        self.map_paths = {m.key: Path(m.tiles).total for m in MAPS}
        try:
            pygame.display.set_icon(self.sprites.app_icon())
        except Exception:
            pass
        self.world = WorldRenderer(self.sprites, self.fonts)
        self.ui = UI(screen, self.fonts, self.sprites)
        self.screens = {"menu": Menu(self), "maps": MapSelect(self), "meta": MetaScreen(self), "help": HelpScreen(self)}
        self.scene = "menu"
        self.running = True
        self.banner = ""
        self.meta_tab = 0
        self._reset_play_state()
        self.mouse = (0, 0)
        self.click = False
        self._seen_cleared = 0

    def _reset_play_state(self):
        self.selected = None
        self.placing = None
        self.hover_type = None
        self.cat = 0
        self.speed = 0
        self.eff_speed = 1.0
        self.set_speed(0)
        self.paused = False
        self.pause_menu = False
        self.auto = False
        self.auto_t = 0.0
        self.meteor_armed = False
        self.win_ack = False
        self.acc = 0.0

    # ---- helpers -----------------------------------------------------------------
    def set_speed(self, i):
        """Select a speed. Above x4 the visual effects are switched off to save CPU."""
        self.speed = max(0, min(len(SPEEDS) - 1, i))
        self.sim.fx = self.fx if self.speed <= FX_MAX_SPEED_INDEX else NullFx()

    @staticmethod
    def snap(x, y):
        return int(round(x / PX)) * PX, int(round(y / PX)) * PX

    def modal(self):
        s = self.sim
        return s.state == LOST or (s.won and not self.win_ack) or self.pause_menu

    def ascend_gain(self):
        return self.sim.ascend_gain()

    # ---- save / load ---------------------------------------------------------------
    def save(self):
        run = None
        if self.scene == "play" and self.sim.state != LOST:
            run = self.run_data = self.sim.save_snapshot()
        elif self.run_data is not None and self.sim.state != LOST:
            run = self.run_data
        data = {"meta": self.meta.to_dict(), "run": run, "settings": {"fullscreen": self.fullscreen}}
        self.store.write(data)

    def set_fullscreen(self, on):
        self.fullscreen = bool(on)
        try:
            if bool(pygame.display.get_surface().get_flags() & pygame.FULLSCREEN) != self.fullscreen:
                pygame.display.toggle_fullscreen()
        except Exception:
            pass
        self.save()

    # ---- scene transitions ------------------------------------------------------------
    def _enter_play(self):
        self._reset_play_state()
        if self.sim.won:
            self.win_ack = True
        self.sim.recalc_all()
        self._seen_cleared = self.sim.waves_cleared
        self.scene = "play"

    def new_run(self, map_key=None):
        if map_key is None:
            map_key = self.sim.map.key
        self.sim.set_map(map_key)
        self.run_data = None
        self._enter_play()
        self.save()

    def continue_run(self):
        if not self.run_data:
            return
        try:
            self.sim.restore(self.run_data)
        except Exception:
            self.run_data = None
            self.sim.reset()
        self._enter_play()

    def restart(self):
        self.new_run(self.sim.map.key)

    def to_menu(self):
        self.save()
        self.pause_menu = False
        self.banner = ""
        self.scene = "menu"
        if self.sim.state == LOST:
            self.run_data = None

    def open_meta(self):
        self.banner = ""
        self.meta_tab = 0
        self.scene = "meta"

    def close_meta(self):
        if self.banner:
            self.banner = ""
            self.scene = "maps"          # pick the map for the next run
        else:
            self.scene = "menu"

    def ascend(self):
        wave = self.sim.wave
        gain = self.sim.ascend_gain()
        shards = self.sim.shard_gain()
        m = self.meta
        m.ap += gain
        m.total_ap += gain
        m.shards += shards
        m.total_shards += shards
        m.ascensions += 1
        self.sim.reset()
        self.run_data = None
        self.pause_menu = False
        self._reset_play_state()
        extra = f" and +{shards} Shards" if shards else ""
        self.banner = (f"Ascended from wave {wave} on {self.sim.map.name}:  +{fmt(gain)} AP{extra}!   "
                       "Spend them, then start a new run.")
        self.meta_tab = 0
        self.scene = "meta"
        self.save()

    def quit(self):
        self.save()
        self.running = False

    def use_skill(self, which):
        if which == "m":
            if self.sim.cd_meteor <= 0:
                self.meteor_armed = not self.meteor_armed
                self.placing = None
        elif self.sim.cast_freeze():
            self.sim.say("Time freeze!", (150, 210, 255))

    # ---- input -------------------------------------------------------------------
    def handle_events(self):
        self.click = False
        self.mouse = pygame.mouse.get_pos()
        sim = self.sim
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.quit()
            elif e.type == pygame.MOUSEBUTTONDOWN:
                if e.button == 1:
                    self.click = True
                    self.mouse = e.pos
                elif e.button == 3 and self.scene == "play":
                    self.placing = self.selected = None
                    self.meteor_armed = False
            elif e.type == pygame.KEYDOWN:
                k = e.key
                if k == pygame.K_F11:
                    self.set_fullscreen(not self.fullscreen)
                elif self.scene in ("meta", "help", "maps"):
                    if k == pygame.K_ESCAPE:
                        self.scene = "menu" if not self.banner else self.scene
                elif self.scene == "play":
                    self._play_key(k)

    def _play_key(self, k):
        sim = self.sim
        if k == pygame.K_ESCAPE:
            if self.pause_menu:
                self.pause_menu = False
            elif self.placing is not None or self.selected is not None or self.meteor_armed:
                self.placing = self.selected = None
                self.meteor_armed = False
            elif not self.modal():
                self.pause_menu = True
            return
        if self.modal():
            return
        if k == pygame.K_SPACE:
            sim.start_wave()
        elif k == pygame.K_p:
            self.paused = not self.paused
        elif k == pygame.K_q:
            self.use_skill("m")
        elif k == pygame.K_w:
            self.use_skill("f")
        elif k == pygame.K_u and self.selected:
            sim.upgrade(self.selected, 1)
        elif k in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
            self.set_speed(self.speed + 1)
        elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.set_speed(self.speed - 1)
        elif k == pygame.K_g:
            sim.auto_mode = (sim.auto_mode + 1) % 3
        elif pygame.K_1 <= k <= pygame.K_7:
            self.cat = k - pygame.K_1
        elif k in (pygame.K_z, pygame.K_x, pygame.K_c, pygame.K_v, pygame.K_b):
            slot = (pygame.K_z, pygame.K_x, pygame.K_c, pygame.K_v, pygame.K_b).index(k)
            items = cat_indices(CATEGORIES[self.cat][0])
            if slot < len(items):
                ti = items[slot]
                tt = TOWER_TYPES[ti]
                if sim.unlocked(ti) and not (tt.legendary and sim.has_legend(tt.key)):
                    self.placing = ti
                    self.selected = None
                    self.meteor_armed = False

    def map_click(self):
        sim = self.sim
        mx, my = self.mouse[0] - MAP_X, self.mouse[1] - MAP_Y
        if self.meteor_armed:
            if sim.cast_meteor(mx, my):
                self.meteor_armed = False
        elif self.placing is not None:
            gx, gy = self.snap(mx, my)
            if sim.place(self.placing, gx, gy) is not None:
                if TOWER_TYPES[self.placing].legendary or sim.gold < sim.build_cost(self.placing):
                    self.placing = None
        else:
            best, bd = None, 22 * 22
            for t in sim.towers:
                d = (t.x - mx) ** 2 + (t.y - 8 - my) ** 2
                if d < bd:
                    best, bd = t, d
            self.selected = best

    # ---- update / draw ---------------------------------------------------------------
    def update(self, dt):
        if self.scene != "play":
            self.screens[self.scene].update(dt)
            return
        sim = self.sim
        if self.selected is not None and self.selected not in sim.towers:
            self.selected = None
        if not self.paused and not self.modal():
            self.acc += min(dt, 0.1) * SPEEDS[self.speed]
            n, t0 = 0, time.perf_counter()
            while self.acc >= SIM_DT and n < MAX_TICKS_PER_FRAME and time.perf_counter() - t0 < TICK_BUDGET:
                sim.step(SIM_DT)
                self.acc -= SIM_DT
                n += 1
            if self.acc >= SIM_DT:                     # can't keep up: drop the backlog instead of spiralling
                self.acc = SIM_DT
            self.eff_speed = 0.9 * self.eff_speed + 0.1 * (n * SIM_DT / max(dt, 1e-3))
            if self.auto and sim.state == PREP:
                self.auto_t += dt
                if self.auto_t > 1.5:
                    sim.start_wave()
                    self.auto_t = 0.0
            else:
                self.auto_t = 0.0
            self.fx.update(dt)
        if sim.waves_cleared != self._seen_cleared:       # autosave after each cleared wave
            self._seen_cleared = sim.waves_cleared
            self.save()
        if sim.state == LOST and self.run_data is not None:
            self.run_data = None                          # a dead run can't be continued
            self.save()

    def draw(self):
        self.ui.begin(self.mouse, self.click)
        if self.scene != "play":
            self.screens[self.scene].draw()
            return
        self.screen.fill((20, 18, 30))
        self.world.draw(self.screen, self)
        self.ui.draw(self)
        if self.ui.click and not self.modal() and MAP_RECT.collidepoint(self.mouse):
            self.map_click()


def run(fullscreen=False, save_dir=None, seed=None, reset_save=False):
    pygame.init()
    flags = getattr(pygame, "SCALED", 0) | getattr(pygame, "RESIZABLE", 0)
    try:
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags)
    except pygame.error:
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption(APP_NAME)
    store = SaveStore(save_dir)
    if reset_save:
        store.wipe()
    clock = pygame.time.Clock()
    g = Game(screen, store, seed=seed, fullscreen=fullscreen)
    if g.fullscreen:
        g.set_fullscreen(True)
    while g.running:
        dt = clock.tick(FPS) / 1000.0
        g.handle_events()
        g.update(dt)
        g.draw()
        pygame.display.flip()
    pygame.quit()
