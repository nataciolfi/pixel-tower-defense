"""Command line entry point: `pixel-td` or `python -m pixel_td`."""
import argparse
from . import __version__


def main(argv=None):
    p = argparse.ArgumentParser(prog="pixel-td", description="Pixel Tower Defense - infinite waves, absurd numbers.")
    p.add_argument("--version", action="version", version=f"pixel-td {__version__}")
    p.add_argument("--fullscreen", action="store_true", help="start in fullscreen (F11 toggles in game)")
    p.add_argument("--save-dir", metavar="DIR", help="use DIR for the save file (default: XDG data dir)")
    p.add_argument("--reset-save", action="store_true", help="delete the existing save file and start fresh")
    p.add_argument("--seed", type=int, help="seed the random number generator")
    a = p.parse_args(argv)
    from .game import run          # imported late so --help/--version work without pygame
    run(fullscreen=a.fullscreen, save_dir=a.save_dir, seed=a.seed, reset_save=a.reset_save)


if __name__ == "__main__":
    main()
