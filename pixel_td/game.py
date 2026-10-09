"""Main application: input, fixed-timestep loop, glue between sim / renderer / UI."""
import pygame
from .config import *
from .sim import Simulation, PREP, WAVE, LOST
from .sprites import Sprites
from .effects import Effects
from .render import WorldRenderer, MAP_RECT
from .ui import UI
from .towers import TOWER_TYPES


def make_fonts():
    names = "couriernew,consolas,dejavusansmono,liberationmono,monospace"
    path = pygame.font.match_font(names, bold=True)
    fonts = {}
    for sz in (12, 14, 16, 20, 24, 40):
        fonts[sz] = pygame.font.Font(path, sz) if path else pygame.font.Font(None, sz + 6)
    return fonts


class Game:
    def __init__(self, screen):
        self.screen = screen
        self.fonts = make_fonts()
        self.fx = Effects(self.fonts[14])
        self.sim = Simulation(self.fx)
        self.sprites = Sprites(self.sim.path)
        self.world = WorldRenderer(self.sprites, self.fonts)
        self.ui = UI(screen, self.fonts, self.sprites)
        self.running = True
        self.selected = None
        self.placing = None
        self.hover_type = None
        self.speed = 0
        self.paused = False
        self.auto = False
        self.auto_t = 0.0
        self.meteor_armed = False
        self.win_ack = False
        self.acc = 0.0
        self.mouse = (0, 0)
        self.click = False

    # ---- helpers -----------------------------------------------------------------
    @staticmethod
    def snap(x, y):
        return int(round(x / PX)) * PX, int(round(y / PX)) * PX

    def restart(self):
        self.sim.reset()
        self.selected = self.placing = None
        self.meteor_armed = False
        self.win_ack = False
        self.paused = False
        self.acc = 0.0
        self.fx.life[:] = 0
        self.fx.lines.clear(); self.fx.rings.clear(); self.fx.texts.clear()

    def use_skill(self, which):
        if which == "m":
            if self.sim.cd_meteor <= 0:
                self.meteor_armed = not self.meteor_armed
                self.placing = None
        elif self.sim.cast_freeze():
            self.sim.say("Time freeze!", (150, 210, 255))

    def modal(self):
        return self.sim.state == LOST or (self.sim.won and not self.win_ack)

    # ---- input -------------------------------------------------------------------
    def handle_events(self):
        self.click = False
        self.mouse = pygame.mouse.get_pos()
        sim = self.sim
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.MOUSEBUTTONDOWN:
                if e.button == 1:
                    self.click = True
                    self.mouse = e.pos
                elif e.button == 3:
                    self.placing = None
                    self.selected = None
                    self.meteor_armed = False
            elif e.type == pygame.KEYDOWN and not self.modal():
                k = e.key
                if k == pygame.K_ESCAPE:
                    self.placing = self.selected = None
                    self.meteor_armed = False
                elif k == pygame.K_SPACE:
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
                    self.speed = min(len(SPEEDS) - 1, self.speed + 1)
                elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    self.speed = max(0, self.speed - 1)
                elif pygame.K_1 <= k <= pygame.K_6:
                    self.placing = k - pygame.K_1
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
                if sim.gold < sim.build_cost(self.placing):
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
        sim = self.sim
        if self.selected is not None and self.selected not in sim.towers:
            self.selected = None
        if not self.paused and not self.modal():
            self.acc += min(dt, 0.1) * SPEEDS[self.speed]
            n = 0
            while self.acc >= SIM_DT and n < MAX_TICKS_PER_FRAME:
                sim.step(SIM_DT)
                self.acc -= SIM_DT
                n += 1
            if n >= MAX_TICKS_PER_FRAME:
                self.acc = 0.0
            if self.auto and sim.state == PREP:
                self.auto_t += dt
                if self.auto_t > 1.5:
                    sim.start_wave()
                    self.auto_t = 0.0
            else:
                self.auto_t = 0.0
            self.fx.update(dt)

    def draw(self):
        self.screen.fill((20, 18, 30))
        self.world.draw(self.screen, self)
        self.ui.begin(self.mouse, self.click)
        self.ui.draw(self)
        if self.ui.click and not self.modal() and MAP_RECT.collidepoint(self.mouse):
            self.map_click()


def run():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Pixel Tower Defense - Infinite Waves")
    clock = pygame.time.Clock()
    g = Game(screen)
    while g.running:
        dt = clock.tick(FPS) / 1000.0
        g.handle_events()
        g.update(dt)
        g.draw()
        pygame.display.flip()
    pygame.quit()
