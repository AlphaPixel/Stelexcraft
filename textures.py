"""Procedurally generated 16x16 pixel-art texture atlas (256x256, 16x16 tiles)."""
import numpy as np

T = 16
rng = np.random.RandomState(1337)


def noise(rgb, var=0.2, alpha=255):
    n = rng.random_sample((T, T, 1))
    c = np.array(rgb, float)[None, None, :] * (1.0 + (n - 0.5) * 2 * var)
    a = np.full((T, T, 1), float(alpha))
    return np.concatenate([c, a], -1)


def speckle(img, rgb, prob, var=0.1):
    m = rng.random_sample((T, T)) < prob
    img[m, :3] = noise(rgb, var)[m, :3]
    return img


def dirt():
    img = noise((134, 96, 67), 0.18)
    speckle(img, (100, 70, 48), 0.15)
    speckle(img, (160, 120, 86), 0.08)
    return img


def grass_top():
    img = noise((96, 158, 56), 0.2)
    speckle(img, (70, 125, 40), 0.15)
    speckle(img, (120, 180, 70), 0.08)
    return img


def grass_side(top_rgb=(96, 158, 56)):
    img = dirt()
    g = noise(top_rgb, 0.15)
    for x in range(T):
        d = 3 + (rng.random_sample() < 0.5) + (rng.random_sample() < 0.25)
        img[:d, x] = g[:d, x]
    return img


def stone(base=(125, 125, 125)):
    img = noise(base, 0.12)
    speckle(img, tuple(c * 0.8 for c in base), 0.12)
    speckle(img, tuple(min(255, c * 1.12) for c in base), 0.06)
    return img


def voronoi(npts=10, seed_pts=None):
    pts = rng.random_sample((npts, 2)) * T
    yy, xx = np.mgrid[0:T, 0:T]
    ds = []
    for px, py in pts:
        dx = np.abs(xx - px)
        dx = np.minimum(dx, T - dx)
        dy = np.abs(yy - py)
        dy = np.minimum(dy, T - dy)
        ds.append(np.sqrt(dx * dx + dy * dy))
    ds = np.stack(ds)
    order = np.sort(ds, 0)
    cell = np.argmin(ds, 0)
    border = (order[1] - order[0]) < 1.3
    return cell, border


def cobble(base=(122, 122, 122)):
    cell, border = voronoi(9)
    shade = rng.random_sample(16) * 0.35 + 0.8
    img = noise(base, 0.12)
    img[..., :3] *= shade[cell][..., None]
    img[border, :3] = noise((70, 70, 70), 0.15)[border, :3]
    return img


def planks():
    img = noise((160, 128, 78), 0.06)
    for r in range(T):
        img[r, :, :3] *= 0.92 + 0.12 * rng.random_sample()
    for band in range(4):
        y0 = band * 4
        img[y0 + 3, :, :3] *= 0.65
        sx = (band * 7 + 3) % T
        img[y0:y0 + 3, sx, :3] *= 0.7
    return img


def log_side(base=(104, 82, 50)):
    img = noise(base, 0.08)
    for x in range(T):
        img[:, x, :3] *= 0.75 + 0.4 * rng.random_sample()
    return img


def log_top(inner=(176, 142, 88), bark=(104, 82, 50)):
    yy, xx = np.mgrid[0:T, 0:T]
    r = np.maximum(np.abs(xx - 7.5), np.abs(yy - 7.5))
    img = noise(inner, 0.06)
    ring = (r.astype(int) % 2 == 0)
    img[ring, :3] *= 0.85
    edge = r > 6.6
    img[edge, :3] = noise(bark, 0.1)[edge, :3]
    return img


def leaves(base=(58, 125, 38)):
    img = noise(base, 0.3)
    speckle(img, tuple(c * 0.7 for c in base), 0.2)
    holes = rng.random_sample((T, T)) < 0.18
    img[holes, 3] = 0
    return img


def gravel():
    img = noise((130, 125, 120), 0.1)
    cell, border = voronoi(14)
    cols = np.array([(150, 140, 135), (110, 105, 100), (90, 85, 82), (165, 155, 150), (125, 110, 100)], float)
    pick = rng.randint(0, 5, 16)
    img[..., :3] = cols[pick[cell]] * (0.9 + 0.2 * rng.random_sample((T, T, 1)))
    img[border, :3] *= 0.7
    return img


def glass():
    img = np.zeros((T, T, 4))
    img[..., :3] = 220
    img[[0, -1], :, :] = (200, 225, 235, 255)
    img[:, [0, -1], :] = (200, 225, 235, 255)
    for (x, y) in [(3, 5), (4, 4), (5, 3), (6, 2), (9, 12), (10, 11), (11, 10), (12, 9), (11, 12), (12, 11)]:
        img[y, x] = (245, 252, 255, 255)
    return img


def ore(color, n=5):
    img = stone()
    for _ in range(n):
        cx, cy = rng.randint(1, T - 2, 2)
        for dx, dy in [(0, 0), (1, 0), (0, 1), (1, 1), (-1, 0), (0, -1)]:
            if rng.random_sample() < 0.75:
                img[(cy + dy) % T, (cx + dx) % T, :3] = np.array(color) * (0.8 + 0.4 * rng.random_sample())
    return img


def bricks(brick=(150, 72, 58), mortar=(185, 178, 168), bw=8, bh=4):
    img = noise(brick, 0.12)
    m = noise(mortar, 0.05)
    for y in range(T):
        band = y // bh
        for x in range(T):
            if y % bh == bh - 1 or (x + (band % 2) * (bw // 2)) % bw == bw - 1:
                img[y, x] = m[y, x]
    return img


def tallgrass():
    img = np.zeros((T, T, 4))
    for _ in range(9):
        x = rng.randint(1, T - 1)
        h = rng.randint(5, 14)
        lean = rng.choice([-1, 0, 1])
        c = np.array((70, 140, 45)) * (0.75 + 0.5 * rng.random_sample())
        for i in range(h):
            xx = int(x + lean * (i / 6.0))
            if 0 <= xx < T:
                img[T - 1 - i, xx] = (*c, 255)
    return img


def flower(petal, center):
    img = np.zeros((T, T, 4))
    img[9:, 7] = (60, 130, 40, 255)
    img[11, 8] = (60, 130, 40, 255)
    img[12, 6] = (60, 130, 40, 255)
    for y in range(4, 9):
        for x in range(5, 10):
            if (y in (4, 8)) and (x in (5, 9)):
                continue
            img[y, x] = (*np.array(petal) * (0.85 + 0.3 * rng.random_sample()), 255)
    img[6, 7] = (*center, 255)
    return img


def torch():
    img = np.zeros((T, T, 4))
    for y in range(9, 16):
        img[y, 7] = (140, 105, 60, 255)
        img[y, 8] = (110, 82, 48, 255)
    img[6, 7:9] = (255, 255, 210, 255)
    img[7, 7:9] = (255, 225, 90, 255)
    img[8, 7:9] = (255, 160, 40, 255)
    return img


def glowstone():
    img = noise((190, 140, 70), 0.15)
    speckle(img, (255, 230, 150), 0.3)
    speckle(img, (140, 95, 45), 0.12)
    return img


def birch_side():
    img = noise((216, 214, 204), 0.04)
    for _ in range(9):
        y = rng.randint(0, T)
        x = rng.randint(0, T)
        w = rng.randint(2, 5)
        img[y, x:x + w, :3] = (50, 48, 44)
    return img


def cactus_side():
    img = noise((76, 138, 48), 0.08)
    for x in (0, 4, 8, 12):
        img[:, x, :3] *= 0.75
    for y in range(1, T, 4):
        for x in (2, 6, 10, 14):
            img[(y + x) % T, x, :3] = (200, 220, 170)
    return img


def cactus_top():
    img = log_top((90, 150, 60), (60, 115, 40))
    return img


def sandstone_side():
    img = noise((216, 203, 155), 0.05)
    for y in (3, 4, 9, 13):
        img[y, :, :3] *= 0.9
    img[0:2, :, :3] *= 1.05
    return img


def wool(rgb):
    img = noise(rgb, 0.06)
    for y in range(T):
        for x in range(T):
            if (x + y) % 4 == 0:
                img[y, x, :3] *= 0.92
    return img


def stonebricks():
    img = noise((122, 122, 122), 0.08)
    for y in range(T):
        for x in range(T):
            band = y // 8
            if y % 8 == 7 or (x + band * 8) % 16 == 15:
                img[y, x, :3] = (80, 80, 80)
            elif y % 8 == 0 or (x + band * 8) % 16 == 0:
                img[y, x, :3] *= 1.15
    return img


def bookshelf():
    img = planks()
    cols = [(150, 40, 40), (40, 70, 150), (50, 120, 50), (150, 120, 40), (90, 50, 120), (60, 60, 60)]
    for y0 in (2, 9):
        x = 1
        while x < T - 1:
            w = rng.randint(1, 3)
            h = rng.randint(4, 6)
            c = np.array(cols[rng.randint(len(cols))]) * (0.8 + 0.4 * rng.random_sample())
            img[y0:y0 + 6, x:x + w, :3] = (40, 30, 20)
            img[y0 + 6 - h:y0 + 6, x:x + w, :3] = c
            x += w
            if rng.random_sample() < 0.2:
                x += 1
    return img


def obsidian():
    img = noise((22, 16, 34), 0.25)
    speckle(img, (60, 40, 95), 0.12)
    return img


def mossy():
    img = cobble()
    m = rng.random_sample((T, T)) < 0.3
    img[m, :3] = noise((80, 120, 60), 0.2)[m, :3]
    return img


def pumpkin_side():
    img = noise((215, 125, 30), 0.08)
    for x in (2, 6, 10, 13):
        img[:, x, :3] *= 0.82
    return img


def pumpkin_top():
    img = pumpkin_side()
    img[6:10, 6:10, :3] = (90, 70, 30)
    return img


def jack_face():
    img = pumpkin_side()
    glow = (255, 225, 90)
    for (x0, y0) in [(3, 4), (10, 4)]:
        img[y0:y0 + 3, x0:x0 + 3, :3] = glow
    img[10:12, 3:13, :3] = glow
    img[9, 4:6, :3] = glow
    img[9, 10:12, :3] = glow
    img[12, 5:7, :3] = glow
    img[12, 9:11, :3] = glow
    return img


FONT3x5 = {
    "T": ["111", "010", "010", "010", "010"],
    "N": ["101", "111", "111", "111", "101"],
}


def tnt_side():
    img = noise((200, 50, 40), 0.1)
    for x in range(0, T, 4):
        img[:, x, :3] *= 0.8
    img[5:11, :, :3] = noise((230, 230, 225), 0.03)[5:11, :, :3]
    x = 2
    for ch in "TNT":
        g = FONT3x5[ch]
        for yy in range(5):
            for xx in range(3):
                if g[yy][xx] == "1":
                    img[5 + 0 + yy if yy < 5 else 0, x + xx, :3] = (20, 20, 20)
        x += 4
    img[10, :, :3] = (230, 230, 225)
    return img


def tnt_top():
    img = noise((170, 165, 160), 0.06)
    img[6:10, 6:10, :3] = (200, 50, 40)
    img[7:9, 7:9, :3] = (60, 60, 60)
    return img


def lava():
    img = noise((215, 85, 15), 0.15)
    speckle(img, (255, 170, 40), 0.25)
    speckle(img, (160, 40, 10), 0.12)
    return img


def sugarcane():
    img = np.zeros((T, T, 4))
    for x in (3, 8, 12):
        for y in range(T):
            c = (140, 190, 90) if y % 5 != 0 else (100, 150, 60)
            img[y, x:x + 2] = (*c, 255)
    return img


def deadbush():
    img = np.zeros((T, T, 4))
    for x0, lean in ((7, 0), (5, -1), (10, 1), (8, 1), (4, -1)):
        x = float(x0)
        for y in range(15, 15 - rng.randint(6, 12), -1):
            if 0 <= int(x) < T:
                img[y, int(x)] = (*np.array((125, 85, 40)) * (0.8 + 0.4 * rng.random_sample()), 255)
            x += lean * 0.35
    return img


def spruce_planks():
    img = planks()
    img[..., :3] *= np.array([0.62, 0.55, 0.5])
    return img


HEART = ["..XX...XX..", ".XXXX.XXXX.", "XXXXXXXXXXX", "XXXXXXXXXXX", "XXXXXXXXXXX",
         ".XXXXXXXXX.", "..XXXXXXX..", "...XXXXX...", "....XXX....", ".....X....."]


def extra_tiles():
    out = {}
    r = np.random.RandomState(77)
    path = []
    for _ in range(5):
        x, y = 7.5, 7.5
        ang = r.uniform(0, 2 * np.pi)
        for _ in range(14):
            ang += r.uniform(-0.6, 0.6)
            x += np.cos(ang)
            y += np.sin(ang)
            if 0 <= x < T and 0 <= y < T:
                path.append((int(y), int(x)))
    order = sorted(range(len(path)), key=lambda i: (i % 14, i))
    for st in range(10):
        img = np.zeros((T, T, 4))
        n = int(len(order) * (st + 1) / 10)
        for i in order[:n]:
            img[path[i]] = (25, 25, 25, 230)
        out[208 + st] = img
    for idx, mode in ((218, "full"), (219, "half"), (220, "empty")):
        img = np.zeros((T, T, 4))
        for yy, row in enumerate(HEART):
            for xx, ch in enumerate(row):
                if ch != "X":
                    continue
                py, px = yy + 3, xx + 2
                edge = (yy == 0 or xx == 0 or xx == len(row) - 1 or row[xx - 1] != "X" or row[xx + 1] != "X"
                        or yy == len(HEART) - 1 or HEART[yy + 1][xx] != "X" or HEART[yy - 1][xx] != "X")
                if edge:
                    img[py, px] = (20, 0, 0, 255)
                elif mode == "full" or (mode == "half" and xx < 6):
                    img[py, px] = (215, 25, 25, 255) if yy > 1 else (255, 140, 140, 255)
                else:
                    img[py, px] = (60, 10, 10, 255)
        out[idx] = img
    img = np.zeros((T, T, 4))
    yy, xx = np.mgrid[0:T, 0:T]
    d = np.sqrt((yy - 8) ** 2 + (xx - 8) ** 2)
    img[(d < 5.5)] = (40, 90, 220, 255)
    img[(d < 4.3)] = (120, 180, 255, 255)
    img[5:7, 5:7] = (255, 255, 255, 255)
    out[221] = img
    return out


def build_atlas():
    tiles = {
        0: grass_top(), 1: grass_side(), 2: dirt(), 3: stone(), 4: cobble(), 5: planks(),
        6: log_side(), 7: log_top(), 8: leaves(), 9: noise((219, 207, 160), 0.06), 10: gravel(),
        11: noise((48, 92, 200), 0.08), 12: glass(), 13: stone((60, 60, 60)), 14: ore((30, 30, 30)),
        15: ore((214, 175, 145)), 16: ore((250, 222, 60)), 17: ore((95, 230, 225)),
        18: noise((240, 245, 250), 0.03), 19: grass_side((238, 243, 248)), 20: bricks(),
        21: tallgrass(), 22: flower((245, 215, 40), (220, 160, 20)), 23: flower((210, 30, 30), (40, 30, 10)),
        24: torch(), 25: glowstone(), 26: birch_side(), 27: log_top((200, 180, 130), (216, 214, 204)),
        28: leaves((100, 150, 62)), 29: cactus_side(), 30: cactus_top(), 31: sandstone_side(),
        32: noise((218, 205, 158), 0.04),
        33: wool((235, 235, 235)), 34: wool((165, 40, 38)), 35: wool((235, 125, 40)), 36: wool((245, 210, 50)),
        37: wool((120, 195, 40)), 38: wool((30, 140, 150)), 39: wool((50, 60, 160)), 40: wool((125, 50, 170)),
        41: wool((25, 25, 30)), 42: stonebricks(), 43: bookshelf(), 44: obsidian(), 45: mossy(),
        46: pumpkin_top(), 47: jack_face(), 48: pumpkin_side(), 49: tnt_side(), 50: tnt_top(),
        51: noise((150, 145, 140), 0.06), 52: lava(), 53: log_side((70, 50, 30)),
        54: leaves((50, 92, 60)), 55: sugarcane(), 56: spruce_planks(), 57: deadbush(),
        58: flower((80, 110, 235), (40, 50, 140)),
    }
    # bedrock: harsh contrast
    b = noise((90, 90, 90), 0.5)
    tiles[13] = b
    atlas = np.zeros((256, 256, 4), np.float64)
    for idx, img in tiles.items():
        r, c = divmod(idx, 16)
        atlas[r * T:(r + 1) * T, c * T:(c + 1) * T] = img
    for idx, img in extra_tiles().items():
        r, c = divmod(idx, 16)
        atlas[r * T:(r + 1) * T, c * T:(c + 1) * T] = img
    atlas[15 * T:, 15 * T:] = 255  # white tile (255) for UI
    return np.clip(atlas, 0, 255).astype(np.uint8)


def cloud_texture(size=64, seed=5):
    r = np.random.RandomState(seed)
    base = r.random_sample((size // 8, size // 8))
    big = np.kron(base, np.ones((8, 8)))
    fine = r.random_sample((size, size))
    # smooth by rolling average
    v = big * 0.7 + fine * 0.3
    for _ in range(2):
        v = (v + np.roll(v, 1, 0) + np.roll(v, -1, 0) + np.roll(v, 1, 1) + np.roll(v, -1, 1)) / 5
    m = v > 0.55
    img = np.zeros((size, size, 4), np.uint8)
    img[m] = (255, 255, 255, 200)
    return img
