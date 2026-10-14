# StelexCraft
An example of one-shotting a Minecraft-clone in one hour, as an example of LLM coding.

![StelexCraft landscape](docs/images/landscape-f3.jpg)

## Documentation
- [Build report](docs/BUILD_REPORT.md): how it was built in about 55 minutes, with the decisions, timeline, testing and fixes
- [Features](docs/FEATURES.md): everything it has, what it doesn't have, and known issues, with screenshots
- [Comparison with Minecraft](docs/COMPARISON.md): side by side with Minecraft Java Edition (past and current) and Bedrock

## Run
```
pip install -r requirements.txt
python stelexcraft.py
```
The first launch compiles the numba kernels (~15 s); later launches start in a couple of seconds.
The world is saved to `world.sav` on quit and every 2 minutes. Use **New World** in the Esc menu (or delete the file) to start over with a new random world.

## Features
- Infinite procedural terrain: oceans, beaches, plains, forests (oak and birch), deserts with cacti, snowy mountains, caves and caverns, ores (coal, iron, gold, diamond), and bedrock
- Multithreaded chunk generation and meshing (numba, `nogil`), 10-chunk render distance by default, frustum culling, and distance fog
- Minecraft-style sky and block lighting: flood-fill light, smooth lighting with ambient occlusion, torches, glowstone, and jack o'lanterns
- Day/night cycle (20 min) with sun, moon, stars, a gradient sky, and drifting clouds
- Weather: rain showers come and go, darken the sky, and stop at roofs; it snows on mountains and stays dry in deserts (F7 toggles rain)
- Transparent animated water (swim in it), swaying grass and flowers, alpha-cut leaves, and glass
- Creative-style building with 50 block types, a hotbar, and a block picker (E)
- Physics: gravity, jumping, sprinting (FOV kick), sneaking (no falling off edges), flying (double-tap Space), and falling sand and gravel
- Wandering pigs, sheep and cows that you can punch; zombies come out at night and lurk in dark caves; those caught in the open burn up at sunrise
- Third-person view (F5) with a player model
- Survival mode (G): hold-to-mine with crack animation, spinning item drops you pick up, stack counts, crafting (planks, torches, glass, stone bricks, TNT and more), health, fall damage, drowning, lava, death and respawn
- Lava lakes in deep caves, spruce forests on snowy mountains, sugar cane along shores, pumpkins, cornflowers, and dead bushes in deserts
- TNT (right-click it to light) with chain reactions, block-break particles, and procedural sound effects
- Little touches: animal sounds, torch smoke, crouching lowers the camera, a hurt camera tilt, an edge vignette, F2 screenshots, and sugar cane and cacti that break as a whole stalk (cacti also hurt in survival)
- All textures are generated procedurally; there are no asset files

## Controls
| Key | Action |
| --- | --- |
| WASD | Move |
| Space | Jump / swim up (double-tap to toggle flying) |
| Shift | Sneak / fly down |
| Ctrl, R, or double-tap W | Sprint |
| Left mouse | Break block / hit animal |
| Right mouse | Place block / light TNT |
| Middle mouse | Pick block |
| 1-9, mouse wheel | Select hotbar slot |
| E | Block picker (inventory in survival) |
| G | Toggle Creative / Survival |
| + / - | Render distance |
| [ / ] | Mouse sensitivity |
| F2 | Screenshot (saved to `screenshots/`) |
| F5 | Third-person view |
| F7 | Toggle rain |
| F11 | Fullscreen |
| F3 | Debug info |
| F1 | Hide HUD |
| Esc | Menu (Q quits) |
