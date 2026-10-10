# Contributing

    git clone <repo> && cd pixel-td
    python3 -m venv .venv && . .venv/bin/activate
    pip install -e . 
    make test        # unit tests (no display needed; the smoke test uses SDL's dummy driver)
    make run

Architecture rule of thumb: everything under `sim.py`, `towers.py`, `enemies.py`, `waves.py`, `meta.py`,
`save.py` is **pygame-free** and unit-testable. Only `render.py`, `ui.py`, `menu.py`, `sprites.py`,
`effects.py` and `game.py` touch pygame. Keep per-enemy work vectorised (numpy), never loop over enemies in Python
in the hot path. Balance knobs live in `config.py`; run the tests after changing them.
