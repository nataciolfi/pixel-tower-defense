# Pixel Tower Defense

A pixel-art **tower defense with infinite waves and absurd numbers**. Build towers *anywhere* off the road,
watch enemy count, HP, damage and gold grow exponentially (millions → billions → trillions → beyond),
then **Ascend** for permanent power and do it all again.

> Add a screenshot at `docs/screenshot.png` and reference it here.

## Features

- **Free placement** – no preset slots; the only rule is "not on the road" (and not on top of another tower).
- **10 towers**, each with damage / range / rate / targeting / special effect, upgradable without limit.
- **12 enemy types + 2 bosses**, introduced progressively; a boss every 10 waves.
- **Exponential difficulty** with a number system that never breaks (gold is an arbitrary-precision integer; combat values go to 1e300; display K, M, B, T, Qa … Vg, then scientific notation).
- **Performance by design** – all enemies live in numpy arrays; every update is a vector operation. Huge waves are merged into *bundles* so thousands of "real" enemies cost the same CPU as a few hundred.
- **Ascension (prestige)**, permanent upgrades, tower unlocks by best wave.
- **Autosave** (every wave + on exit), atomic JSON with automatic backup, main menu, pause menu, fullscreen (F11).

## Install

### Debian / Ubuntu (recommended)

Needs Debian 12+ / Ubuntu 22.04+ (python3-pygame ≥ 2.0).

```bash
# build the package from source (needs only dpkg-deb)
./packaging/debian/build-deb.sh
sudo apt install ./dist/pixel-td_1.0.0_all.deb     # pulls python3-pygame + python3-numpy
pixel-td                                           # or launch "Pixel Tower Defense" from your app menu
```

Or grab the `.deb` from the project's *Releases* page. Uninstall: `sudo apt remove pixel-td`.

### pip / pipx

```bash
pipx install .            # or: pip install .
pixel-td
```

### From source

```bash
pip install -r requirements.txt
PYTHONPATH=src python3 -m pixel_td
```

## Controls

| Key / mouse | Action |
|---|---|
| `1`-`9`, `0` | pick tower to build |
| Left click | place tower / select tower / press buttons |
| Right click, `Esc` | cancel (Esc with nothing to cancel opens the menu) |
| `Space` | start next wave |
| `P` | pause |
| `+` / `-` | game speed (x1, x2, x4, x8) |
| `U` | upgrade selected tower once |
| `Q` | **Meteor** – then click the map (damages % of max HP) |
| `W` | **Time freeze** |
| `F11` | fullscreen |

Selected tower: `UP x1 / x10 / MAX`, cycle targeting (First / Last / Strongest / Weakest / Closest), sell (70 %).
Every 10 levels a tower receives a large damage bonus.

## Towers

| Tower | Unlock (best wave) | Role |
|---|---|---|
| Archer | 0 | cheap, fast, crits |
| Cannon | 0 | splash |
| Frost | 0 | area slow |
| Toxin | 3 | poison (ignores armor) |
| Tesla | 5 | chain lightning |
| Sniper | 8 | huge single hit, pierces armor, long range |
| Laser | 12 | beam ramps up on a single target |
| Mortar | 16 | very long range, big splash |
| Beacon | 20 | no attack – buffs damage of nearby towers |
| Void | 30 | % of max HP as true damage (strong vs. late waves) |

## Enemies

Grunt · Runner (fast) · Brute (HP) · Knight (armor) · Wraith (dodge + regen) · Swarm (tiny, numerous) ·
Shaman (heals allies) · Splitter (splits on death) · Aegis (shield) · Golem (huge HP, slow-immune) ·
**Overlord** (boss) · **Titan** (armored, shielded boss, every 20 waves).

## Ascension (prestige)

Choose **Ascend** from the pause menu (or after defeat / victory). Your run resets and you gain
`floor(0.5 · (wave/5)^1.8)` **Ascension Points** (e.g. wave 20 → 6, wave 50 → 31, wave 100 → 110).
Spend AP on permanent upgrades (damage, gold, attack speed, base HP, starting gold, cheaper towers, shorter
skill cooldowns). Every AP ever earned also gives **+1 % damage**. Reaching **wave 50** shows *Victory*, but the
game continues in endless mode.

## Saves

`~/.local/share/pixel-td/save.json` (honours `$XDG_DATA_HOME`; override with `--save-dir` or `$PIXEL_TD_HOME`).
The game autosaves after every cleared wave and when you leave. Quitting mid-wave resumes at the *start* of that wave.
A `.bak` copy of the previous save is kept. `pixel-td --reset-save` wipes everything.

## Command line

```
pixel-td [--fullscreen] [--save-dir DIR] [--reset-save] [--seed N] [--version]
```

## Project layout

```
src/pixel_td/
  config.py   balance knobs        sim.py     headless simulation core
  bignum.py   big-number helpers   towers.py  tower stats + combat
  enemies.py  numpy enemy pool     waves.py   exponential wave generator
  meta.py     prestige             save.py    JSON saves
  sprite_data.py / sprites.py      ASCII → pixel-art surfaces (no image files)
  effects.py  particles & beams    render.py  world drawing
  ui.py       HUD                  menu.py    menu / ascension / help
  game.py     main loop & scenes   __main__.py CLI
tests/        unit tests (+ headless pygame smoke test)
packaging/    Debian package builder, desktop file, man page, icons
```

Only `render/ui/menu/sprites/effects/game` import pygame; the rest is unit-tested without a display.

## Development

```bash
make test          # unittest suite
make deb           # build the Debian package into dist/
python3 tools/make_icon.py   # regenerate icons
```

Tuning the difficulty: edit the `*_G` growth constants in `src/pixel_td/config.py`
(`HP_G`, `COUNT_G`, `GOLD_G`, `DMG_G`, `UPG_G` …). A naive "build and upgrade the cheapest tower" bot reaches
roughly wave 150+ before losing, so there's room for smarter play.

## License

MIT – see [LICENSE](LICENSE).
