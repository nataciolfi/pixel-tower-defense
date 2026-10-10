"""Runs the real pygame front-end headless (SDL dummy driver). Skipped if pygame is missing."""
import os, tempfile, unittest
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import _path  # noqa

try:
    import pygame
except ImportError:                                       # pragma: no cover
    pygame = None


@unittest.skipIf(pygame is None, "pygame not installed")
class Smoke(unittest.TestCase):
    def test_play_frames(self):
        from pixel_td.game import Game
        from pixel_td.save import SaveStore
        from pixel_td.config import SCREEN_W, SCREEN_H
        pygame.init()
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        g = Game(screen, SaveStore(tempfile.mkdtemp()), seed=1)
        for _ in range(10):                               # main menu
            g.handle_events(); g.update(1 / 60); g.draw()
        g.new_run()
        g.sim.gold = 10 ** 6
        for x in (100, 160, 220):
            g.sim.place(0, x, 120)
        g.selected = g.sim.towers[0]
        g.sim.start_wave()
        g.speed = 3
        for _ in range(600):
            g.handle_events(); g.update(1 / 60); g.draw()
        for scene in ("meta", "help", "menu"):
            g.scene = scene
            g.update(1 / 60); g.draw()
        g.pause_menu = True
        g.scene = "play"
        g.draw()
        pygame.quit()


if __name__ == "__main__":
    unittest.main()
