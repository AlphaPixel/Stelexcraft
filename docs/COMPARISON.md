# StelexCraft compared with Minecraft

This document puts StelexCraft side by side with the commercial game. "Minecraft" here covers:
- **Java Edition across its history.** It is the original PC version, and its early releases are the fairest comparison for a one-hour build.
- **Modern Minecraft as sold in October 2026.** That is Java Edition 26.3 and Bedrock Edition.

The details behind every StelexCraft entry are in [FEATURES.md](FEATURES.md). Sources for the Minecraft facts are at the end.

![Night in third person with zombies](images/night-zombies-third-person.jpg)

## The short version

**Feel.** StelexCraft looks and moves like Minecraft:
- blocky terrain with smooth lighting;
- the same keys, the same walking, sprinting and jumping speeds, and the same 20-minute day;
- a hotbar, hearts, item drops, a crack animation, F3, F5, and the same screenshot naming.

A Minecraft player will know what to do within seconds.

**Content.** It is a small fraction of the game:
- one dimension, 51 block types against more than a thousand, and 4 mobs against about 87;
- no items besides blocks, no tools, no hunger, no flowing water, no redstone, no structures, no music, no multiplayer.

**Era.** Measured against Minecraft's history, its scope sits around Infdev to early Beta (2010–2011):
- infinite worlds, creative building, a thin survival layer, and weather;
- its world height (128) matches Minecraft before 2012, and its ore depths and lava level match Minecraft before 1.18 (2021);
- its lighting and sky look closer to modern vanilla Minecraft.

## Minecraft today (October 2026)

- **Java Edition.**
  - The current release is **26.3 "Wilderness Bound"** (15 September 2026). It added the dappled forest biome, wool and concrete stairs and slabs, straw beds, and the abandoned camp structure.
  - Since **26.1 "Tiny Takeover"** (24 March 2026), Java uses year-based version numbers (year.drop.hotfix) and requires Java 25.
  - Mojang now ships several smaller "game drops" a year instead of one large annual update.
- **Bedrock Edition** is the C++ version for Windows, consoles and mobile. Its graphics mode **Vibrant Visuals** adds:
  - directional sun and moon shadows;
  - physically based materials;
  - screen-space reflections;
  - volumetric fog and light shafts;
  - water caustics, bloom and tone mapping.

  It is Bedrock-only; Java's renderer is being rebuilt on Vulkan as groundwork for it.
- **Scale of the modern game:**
  - 67 biome types (56 in the Overworld);
  - about 87 mobs;
  - well over a thousand block types (one count of unique block types in 1.21.11 is 1,159);
  - three dimensions and more than 20 kinds of generated structures.

## Where StelexCraft sits on Minecraft's timeline

| Minecraft milestone | What it introduced | StelexCraft |
| --- | --- | --- |
| Classic (2009) | Creative building in a small, fixed-size world | Yes, in an infinite world |
| Survival Test (2009) | Health and hostile mobs | Health and zombies |
| Indev (early 2010) | Inventory and crafting | A block-count inventory and a 14-recipe list |
| Infdev (2010) | Infinite worlds | Yes |
| Alpha (2010) | Survival multiplayer, redstone, biomes, the Nether | None of these; height and temperature zones stand in for biomes |
| Beta 1.5 (2011) | Weather | Rain and snow, without thunderstorms |
| Beta 1.8 (2011) | Hunger, sprinting, villages, the return of creative mode | Sprinting and creative mode; no hunger or villages |
| 1.0 (November 2011) | The End, enchanting, brewing | None |
| 1.2 (2012) | World height raised to 256 | No: 128, as before 1.2 |
| 1.13 Update Aquatic (2018) | Swimming, ocean life and structures | No |
| 1.18 Caves & Cliffs (2021) | Height 384 (y −64 to 319); noise caves ("cheese", "spaghetti", "noodle"); taller mountains; new ore layout | Similar spaghetti and cheese caves, but the pre-1.18 height, lava level and ore depths |
| 2024–2026 game drops | Many new blocks, mobs, biomes and structures each year | None of this content |

## Content by the numbers

| | Minecraft (current Java) | StelexCraft |
| --- | --- | --- |
| Block types | More than 1,000 (about 1,159 unique types in 1.21.11 by one count) | 51 |
| Items that aren't blocks | Hundreds: tools, weapons, armor, food, materials | 0 |
| Biomes | 67 | 6 height and temperature zones |
| Mobs | About 87 | 4 (pig, sheep, cow, zombie) |
| Dimensions | 3 (Overworld, Nether, End) | 1 |
| Generated structures | More than 20 kinds | 0 |
| Crafting recipes | Hundreds, plus smelting, smithing, brewing, stonecutting | 14 |
| World height | 384 blocks (y −64 to 319) | 128 blocks (y 0 to 127) |
| Sea level | y=63 | y=62 |
| Render distance (Java) | 2–32 chunks | 3–16 chunks |
| Sound | Recorded effects for almost everything, plus a full soundtrack | 71 synthesized clips, no music |

## Feel: the numbers that matter for movement and survival

Many of StelexCraft's constants were set to Minecraft's own values, which is why it feels familiar.

| | Minecraft Java | StelexCraft | |
| --- | --- | --- | --- |
| Walking speed | 4.317 blocks/s | 4.317 | Same |
| Sprinting speed | 5.612 blocks/s | 5.612 | Same |
| Sneaking speed | 1.295 blocks/s | 1.3 | Same |
| Creative flying | About 10.8–10.9 blocks/s | 10.9 | Same |
| Sprint flying | About 21.6 blocks/s | 21.6 | Same |
| Jump height | About 1.25 blocks | About 1.27 | Same |
| Player size, eye height | 0.6 × 1.8, eyes at 1.62 | Same | Same |
| Sneaking | Hitbox 1.5 tall, eyes at 1.27 | Hitbox stays 1.8, eyes drop to 1.42 | Close |
| Block reach | 4.5 survival, 5 creative | 5 in both | Close |
| Mob reach | 3 survival, 5 creative | 4 in both | Close |
| Field of view | 70 by default, wider while sprinting | 70 → 80 while sprinting | Same |
| Day length | 20 minutes | 20 minutes | Same |
| Health | 20 (10 hearts) | 20 (10 hearts) | Same |
| Fall damage | 1 per block beyond 3 | 1 per block beyond 3 | Same |
| Air supply, then drowning | 15 s, then 2 per second | 10 s, then 2 per second | Close |
| Lava | 4 per half second, and sets you on fire | 4 per half second, no fire | Close |
| Cactus | 1 per half second | 1 per half second | Same |
| Zombie attack (Normal) | 3 | 3 | Same |
| Zombie health | 20 (20 punches) | 6 punches | Different |
| Pig, cow, sheep health | 10, 10, 8 punches | 4 punches | Different |
| Item pickup delay, despawn | 0.5 s, 5 minutes | 0.4 s, 5 minutes | Same |
| TNT fuse | 4 s; 0.5–1.5 s when set off by another explosion | 3 s; 0.4–1.2 s | Close |
| TNT power | 4 | Radius 4 | Close |
| Light levels | Torch 14; glowstone, jack o'lantern, lava 15 | Same | Same |
| Face shading | Top 100%, N/S 80%, E/W 60%, bottom 50% | 100%, 80%, 62%, 50% | Same |
| Mining crack stages | 10 | 10 | Same |
| Screenshot (F2) | `screenshots/YYYY-MM-DD_HH.MM.SS.png` | Same | Same |

## Side by side

**Match** means a Minecraft player would find it essentially the same. **Partial** means present but simpler or different. **Missing** means absent.

### World generation
| Feature | Minecraft | StelexCraft | |
| --- | --- | --- | --- |
| Infinite world | Yes (to ±30 million blocks) | Yes | Match |
| Seeds | Random or chosen; same seed gives the same world | Random only; same seed gives the same world | Partial |
| Biomes | 67 with their own terrain, plants, colors and mobs | Ocean, beach, desert, grassland and forest, snowy highland, peaks | Partial |
| Terrain shape | 3D noise: cliffs, overhangs, rivers, very tall mountains | Heightmap: rolling hills and terraced mountains; no rivers or overhangs | Partial |
| Caves | Noise caves, ravines, aquifers, lush caves, dripstone, the deep dark | Winding tunnels and large caverns, with lava lakes at the bottom | Partial |
| Ores | 8 Overworld ores, plus deepslate variants | Coal, iron, gold, diamond, at pre-1.18 depths | Partial |
| Trees | About ten kinds (oak, birch, spruce, jungle, acacia, dark oak, mangrove, cherry, pale oak, azalea) | Oak, birch, spruce | Partial |
| Plants | Many flowers, crops, bamboo, kelp, seagrass, mushrooms | Tall grass, 3 flowers, dead bush, sugar cane, cactus, pumpkins | Partial |
| Structures | Villages, mineshafts, strongholds, temples, trial chambers and more | None | Missing |
| Nether and End | Yes | No | Missing |

### Blocks and building
| Feature | Minecraft | StelexCraft | |
| --- | --- | --- | --- |
| Number of blocks | More than 1,000 | 51 | Partial |
| Block shapes | Cubes, slabs, stairs, walls, fences, doors, panes, carpets and more | Cubes, cross-shaped plants, torches | Partial |
| Orientation | Logs rotate, stairs face, wall torches, and so on | None | Missing |
| Water and lava | Flow and spread from sources; buckets; waterlogging | Static; breaking next to water fills the hole | Partial |
| Sand and gravel | Fall as visible entities | Drop instantly | Partial |
| Redstone, fire | Yes | No | Missing |
| Light model | Sky and block light 0–15, smooth lighting | The same model, with smooth lighting and ambient occlusion | Match |
| Creative inventory | Tabbed, searchable, every item | One grid of 50 blocks; hover and press 1–9 to assign | Partial |
| Pick block | Both modes | Creative only | Partial |
| TNT | Lit with flint and steel, redstone or fire; destroyed blocks drop | Lit by right-clicking; destroyed blocks vanish; chain reactions work | Partial |

### Survival
| Feature | Minecraft | StelexCraft | |
| --- | --- | --- | --- |
| Health and damage | Many sources, armor, status effects | Falling, drowning, lava, cactus, zombies, TNT, the void | Partial |
| Hunger and food | Yes | No; health always regenerates | Missing |
| Mining and tools | Tool tiers set speed and whether a block drops (stone needs a pickaxe) | No tools; fixed times per material; everything drops | Partial |
| Inventory | 36 slots, stacks of 64, drag and drop, off-hand | A count per block type with no limits; hotbar fills itself | Partial |
| Crafting | 2×2 and 3×3 grids, crafting table, recipe book; smelting in furnaces | Click a recipe in a list of 14; some recipes invented to stand in for smelting and missing items | Partial |
| Storage | Chests, barrels, shulker boxes, ender chests | None | Missing |
| Beds and respawning | Beds set your spawn and skip the night | Fixed world spawn | Missing |
| Death | Items scatter and can be recovered; most experience is lost | Inventory is wiped | Partial |
| Progression | Experience, enchanting, brewing, armor, advancements | None | Missing |
| Difficulty | Peaceful to Hard, plus Hardcore | None | Missing |

### Mobs and combat
| Feature | Minecraft | StelexCraft | |
| --- | --- | --- | --- |
| Roster | About 87 mobs | Pig, sheep, cow, zombie | Partial |
| Hostile spawning | Light level 0, mob caps, despawning | Surface at night (torches don't prevent it) and dark caves | Partial |
| AI | Pathfinding and special behaviors (creepers explode, skeletons shoot, spiders climb) | Wander, chase in a straight line, jump single blocks | Partial |
| Undead in daylight | Catch fire in direct sunlight; shade, water and helmets protect | Vanish in smoke under open sky after sunrise; shade protects | Partial |
| Combat | Weapons, attack cooldown, critical hits, shields, armor | Punching with knockback and a red flash | Partial |
| Animals | Drop food, leather, wool; breed; can be sheared, tamed, ridden | Wander and make sounds; drop nothing | Partial |

### Graphics
| Feature | Minecraft | StelexCraft | |
| --- | --- | --- | --- |
| Renderer | Java: OpenGL, moving to Vulkan. Bedrock: RenderDragon | OpenGL 3.3 through moderngl, from Python | — |
| Smooth lighting and ambient occlusion | Yes | Yes | Match |
| Day and night, sun, moon, stars | Yes, with moon phases | Yes, no moon phases | Match |
| Sunrise and sunset colors, horizon fog | Yes | Yes | Match |
| Clouds | Flat ("Fast") or 3D ("Fancy") | Flat layer | Partial |
| Weather | Rain, snow, thunderstorms with lightning, splash particles | Rain stopped by roofs, snow on mountains, dry deserts; no thunder | Partial |
| Water | Animated, tinted by biome, underwater fog | Transparent, rippling surface, underwater fog | Partial |
| Grass and leaf colors by biome | Yes | No | Missing |
| Plants sway | Not in vanilla Java (shader packs add it) | Yes | Extra |
| Entity shadows | Small blob shadows | None | Missing |
| Particles | Hundreds of kinds | Block break, smoke, mob poof, rain and snow | Partial |
| Textures | Hand-made 16×16 pixel art | Procedural 16×16 pixel art in a similar style | Partial |
| Modern effects | Vibrant Visuals on Bedrock; shader mods on Java | None | Missing |
| Render distance | Up to 32 chunks (Java) | Up to 16 chunks | Partial |
| Third person | Back and front views | Back view, with a Steve-like model | Partial |

### Sound
| Feature | Minecraft | StelexCraft | |
| --- | --- | --- | --- |
| Music | A full soundtrack (C418, Lena Raine and others) | None | Missing |
| Block sounds | Recorded sets per block type | Synthesized sets for six materials | Partial |
| Mob sounds | Every mob, placed in 3D | Four mobs, quieter with distance, no direction | Partial |
| Ambience and weather | Cave ambience, biome sounds, rain, thunder | Rain only | Partial |
| Subtitles | Yes | No | Missing |

### Interface and controls
| Feature | Minecraft | StelexCraft | |
| --- | --- | --- | --- |
| Default keys | WASD, Space, Shift, Ctrl, E, 1–9, wheel, middle-click, F1, F2, F3, F5, F11, Esc | The same keys, the same jobs | Match |
| Double-tap W to sprint, double-tap Space to fly | Yes | Yes | Match |
| Key rebinding, settings screen | Yes | No; render distance and sensitivity only, by key | Missing |
| Title screen, world list | Yes | No; the game opens straight into the single world | Missing |
| Heads-up display | Hotbar, hearts, hunger, armor, experience bar, air, crosshair, item names | Hotbar, hearts, air, crosshair, item names; an always-visible FPS line | Partial |
| F3 debug screen | Very detailed | Position, chunk, facing, time, seed, target, performance | Partial |
| Pause on focus loss | Yes | Yes | Match |
| Chat and commands | Yes | No | Missing |
| Font | Minecraft's pixel font | The system's default font | Partial |

### Platform
| Feature | Minecraft | StelexCraft | |
| --- | --- | --- | --- |
| Multiplayer | Servers, LAN, Realms; Bedrock cross-play | None | Missing |
| Customization | Java: mods, resource packs, data packs. Bedrock: add-ons, Marketplace | None | Missing |
| Platforms | Java: Windows, macOS, Linux. Bedrock: Windows, consoles, phones, tablets | Tested on Windows only. Python and OpenGL 3.3 should work elsewhere, but that hasn't been tried | Partial |
| Worlds and saves | Many worlds, region files, backups | One world in one file | Partial |
| Installation | A launcher | Python 3 plus `pip install -r requirements.txt` | — |

## Scorecard
This is my own judgment, not a measurement: how close each area is to modern Minecraft on a scale of 0 to 10, where 10 means indistinguishable.

| Area | Score | Why |
| --- | --- | --- |
| Movement and controls | 8 | Same keys and speeds; missing the front F5 view, rebinding and swimming poses |
| Look of the Overworld | 6 | Lighting, sky, fog and texture style land well. Missing biome colors, rivers, cliffs, varied trees and Minecraft's own textures |
| Creative building | 4 | Building works well, but there are only 51 cube blocks with no slabs, stairs or doors and no flowing water |
| Interface | 4 | Familiar hotbar and heads-up display; no title screen, settings or slot-based inventory |
| Survival | 2 | Mining, drops, health and a few recipes. No tools, hunger, storage, beds or progression |
| World variety | 2 | One dimension, six zones, no structures |
| Sound | 2 | Effective effects, but no music and no recorded sounds |
| Mobs and combat | 1 | Four mobs with simple behavior |
| Multiplayer and modding | 0 | None |

## What a Minecraft player will notice first

In roughly the order they'll run into them:
1. **It feels right.** Moving, jumping, sprinting, building, the hotbar, the lighting and the day cycle all behave as expected.
2. **It's quiet and looks a little off.** There is no music, the textures are close in style but not Minecraft's, the font is different, and an FPS line sits in the corner.
3. **There's no title screen.** It opens straight into a creative world.
4. **Survival skips steps.**
   - Logs turn into planks, which is familiar.
   - But there's no crafting table, no sticks and no pickaxe, and stone can be mined by hand.
   - Crafting is a clickable list instead of a grid.
5. **Water doesn't flow,** and there are no buckets.
6. **Nights are tame.** Zombies are the only threat; there are no creepers, skeletons or spiders. Animals drop nothing, and with no hunger there's no reason to hunt.
7. **TNT lights with a right-click,** and explosions leave no drops.
8. **It's single-player only.**

## Closing the gap
The changes that would make the biggest difference to Minecraft players, in order:
1. **Items and tools.** Sticks, coal, ingots, pickaxes, axes and shovels that set mining speed and decide what drops, and a real 36-slot inventory with stacks of 64. This is the largest gameplay gap.
2. **Crafting table and furnace.** A 3×3 crafting grid and smelting, replacing the invented recipes.
3. **Flowing water and lava,** spreading on block updates the way Minecraft's do, with buckets.
4. **More hostile mobs.**
   - Creepers can reuse the TNT explosion; also skeletons with arrows and spiders.
   - Spawning should follow light level, so torches make areas safe.
   - Mobs should drop items.
5. **Hunger and food** from animal drops, which gives animals and farming a purpose.
6. **The most-used building blocks:** doors, slabs, stairs, chests, ladders and beds (which set spawn and skip the night).
7. **Title screen, world list and a settings screen** that remembers options.
8. **Music and ambient sound.**
9. **World variety:** biomes with grass colors, more tree types, rivers, and simple structures such as dungeons and villages.
10. **Engine work.**
    - Draw mobs and particles on the GPU to cut per-frame Python cost.
    - Save in a safe format (JSON or numpy) instead of pickle.

## Sources

Minecraft facts in this document come from these pages, checked on 13 October 2026:
- [Java Edition 26.1](https://minecraft.wiki/w/Java_Edition_26.1): version scheme, Java 25 requirement, release date.
- [Java Edition 26.3](https://minecraft.wiki/w/Java_Edition_26.3): current release, its date and contents.
- [Vibrant Visuals](https://minecraft.wiki/w/Vibrant_Visuals): Bedrock graphics features and Java status.
- [Biome](https://minecraft.wiki/w/Biome): 67 biome types.
- [Mob](https://minecraft.wiki/w/Mob): about 87 mobs (counted from the page's lists).
- [Player](https://minecraft.wiki/w/Player): movement speeds, hitbox, eye heights, reach.
- [Zombie](https://minecraft.wiki/w/Zombie): health, damage, sunlight behavior.
- [TNT](https://minecraft.wiki/w/TNT): fuse times, power, drops.
- [Craftdex: how many blocks in Minecraft](https://craftdex.net/fr/guides/how-many-blocks-in-minecraft): 1,159 unique block types in 1.21.11 (a third-party count).

The version-history milestones and the remaining gameplay values (fall, drowning, lava and cactus damage; item pickup and despawn times; light levels; face shading; crack stages; screenshot names) are long-standing Minecraft Wiki facts that I didn't re-check for this document.
