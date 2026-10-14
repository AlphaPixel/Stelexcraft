"""StelexCraft engine: block table, terrain generation, lighting and meshing (numba-accelerated)."""
import numpy as np
from numba import njit

CS = 16      # chunk size (x/z)
H = 128      # world height
SEA = 62

# ---------------------------------------------------------------------------
# Block table
# kinds
K_NONE, K_CUBE, K_CROSS, K_WATER, K_TORCH, K_LAVA = 0, 1, 2, 3, 4, 5

# name, top, bottom, side, front(+z), kind, solid, opaque, light, atten, sound
_B = [
    ("Air", 0, 0, 0, 0, K_NONE, 0, 0, 0, 0, ""),
    ("Grass Block", 0, 2, 1, 1, K_CUBE, 1, 1, 0, 0, "grass"),
    ("Dirt", 2, 2, 2, 2, K_CUBE, 1, 1, 0, 0, "grass"),
    ("Stone", 3, 3, 3, 3, K_CUBE, 1, 1, 0, 0, "stone"),
    ("Cobblestone", 4, 4, 4, 4, K_CUBE, 1, 1, 0, 0, "stone"),
    ("Oak Planks", 5, 5, 5, 5, K_CUBE, 1, 1, 0, 0, "wood"),
    ("Oak Log", 7, 7, 6, 6, K_CUBE, 1, 1, 0, 0, "wood"),
    ("Oak Leaves", 8, 8, 8, 8, K_CUBE, 1, 0, 0, 1, "grass"),
    ("Sand", 9, 9, 9, 9, K_CUBE, 1, 1, 0, 0, "sand"),
    ("Gravel", 10, 10, 10, 10, K_CUBE, 1, 1, 0, 0, "sand"),
    ("Water", 11, 11, 11, 11, K_WATER, 0, 0, 0, 0, ""),
    ("Glass", 12, 12, 12, 12, K_CUBE, 1, 0, 0, 0, "glass"),
    ("Bedrock", 13, 13, 13, 13, K_CUBE, 1, 1, 0, 0, "stone"),
    ("Coal Ore", 14, 14, 14, 14, K_CUBE, 1, 1, 0, 0, "stone"),
    ("Iron Ore", 15, 15, 15, 15, K_CUBE, 1, 1, 0, 0, "stone"),
    ("Gold Ore", 16, 16, 16, 16, K_CUBE, 1, 1, 0, 0, "stone"),
    ("Diamond Ore", 17, 17, 17, 17, K_CUBE, 1, 1, 0, 0, "stone"),
    ("Snowy Grass", 18, 2, 19, 19, K_CUBE, 1, 1, 0, 0, "grass"),
    ("Bricks", 20, 20, 20, 20, K_CUBE, 1, 1, 0, 0, "stone"),
    ("Tall Grass", 21, 21, 21, 21, K_CROSS, 0, 0, 0, 0, "grass"),
    ("Dandelion", 22, 22, 22, 22, K_CROSS, 0, 0, 0, 0, "grass"),
    ("Poppy", 23, 23, 23, 23, K_CROSS, 0, 0, 0, 0, "grass"),
    ("Torch", 24, 24, 24, 24, K_TORCH, 0, 0, 14, 0, "wood"),
    ("Glowstone", 25, 25, 25, 25, K_CUBE, 1, 1, 15, 0, "glass"),
    ("Birch Log", 27, 27, 26, 26, K_CUBE, 1, 1, 0, 0, "wood"),
    ("Birch Leaves", 28, 28, 28, 28, K_CUBE, 1, 0, 0, 1, "grass"),
    ("Cactus", 30, 30, 29, 29, K_CUBE, 1, 1, 0, 0, "wool"),
    ("Sandstone", 32, 32, 31, 31, K_CUBE, 1, 1, 0, 0, "stone"),
    ("White Wool", 33, 33, 33, 33, K_CUBE, 1, 1, 0, 0, "wool"),
    ("Red Wool", 34, 34, 34, 34, K_CUBE, 1, 1, 0, 0, "wool"),
    ("Orange Wool", 35, 35, 35, 35, K_CUBE, 1, 1, 0, 0, "wool"),
    ("Yellow Wool", 36, 36, 36, 36, K_CUBE, 1, 1, 0, 0, "wool"),
    ("Lime Wool", 37, 37, 37, 37, K_CUBE, 1, 1, 0, 0, "wool"),
    ("Cyan Wool", 38, 38, 38, 38, K_CUBE, 1, 1, 0, 0, "wool"),
    ("Blue Wool", 39, 39, 39, 39, K_CUBE, 1, 1, 0, 0, "wool"),
    ("Purple Wool", 40, 40, 40, 40, K_CUBE, 1, 1, 0, 0, "wool"),
    ("Black Wool", 41, 41, 41, 41, K_CUBE, 1, 1, 0, 0, "wool"),
    ("Stone Bricks", 42, 42, 42, 42, K_CUBE, 1, 1, 0, 0, "stone"),
    ("Bookshelf", 5, 5, 43, 43, K_CUBE, 1, 1, 0, 0, "wood"),
    ("Obsidian", 44, 44, 44, 44, K_CUBE, 1, 1, 0, 0, "stone"),
    ("Mossy Cobblestone", 45, 45, 45, 45, K_CUBE, 1, 1, 0, 0, "stone"),
    ("Jack o'Lantern", 46, 46, 48, 47, K_CUBE, 1, 1, 15, 0, "wood"),
    ("TNT", 50, 51, 49, 49, K_CUBE, 1, 1, 0, 0, "grass"),
    ("Snow Block", 18, 18, 18, 18, K_CUBE, 1, 1, 0, 0, "wool"),
    ("Lava", 52, 52, 52, 52, K_LAVA, 0, 0, 15, 0, ""),
    ("Spruce Log", 7, 7, 53, 53, K_CUBE, 1, 1, 0, 0, "wood"),
    ("Spruce Leaves", 54, 54, 54, 54, K_CUBE, 1, 0, 0, 1, "grass"),
    ("Sugar Cane", 55, 55, 55, 55, K_CROSS, 0, 0, 0, 0, "grass"),
    ("Pumpkin", 46, 46, 48, 48, K_CUBE, 1, 1, 0, 0, "wood"),
    ("Spruce Planks", 56, 56, 56, 56, K_CUBE, 1, 1, 0, 0, "wood"),
    ("Dead Bush", 57, 57, 57, 57, K_CROSS, 0, 0, 0, 0, "grass"),
    ("Cornflower", 58, 58, 58, 58, K_CROSS, 0, 0, 0, 0, "grass"),
]
NB = len(_B)
BLOCK_NAMES = [b[0] for b in _B]
BLOCK_SOUND = [b[10] for b in _B]
(AIR, GRASS, DIRT, STONE, COBBLE, PLANKS, LOG, LEAVES, SAND, GRAVEL, WATER, GLASS, BEDROCK,
 COAL, IRON, GOLD, DIAMOND, SNOWGRASS, BRICKS, TALLGRASS, DANDELION, POPPY, TORCH, GLOWSTONE,
 BIRCHLOG, BIRCHLEAVES, CACTUS, SANDSTONE) = range(28)
TNT = BLOCK_NAMES.index("TNT")

TEX = np.zeros((64, 6), np.int64)   # faces: +x -x +y -y +z -z
KIND = np.zeros(64, np.int64)
SOLID = np.zeros(64, np.int64)
OPAQUE = np.zeros(64, np.int64)
LIGHT = np.zeros(64, np.int64)
ATTEN = np.zeros(64, np.int64)
for _i, _b in enumerate(_B):
    _, top, bot, side, front, kind, solid, opaque, light, atten, _s = _b
    TEX[_i] = (side, side, top, bot, front, side)
    KIND[_i], SOLID[_i], OPAQUE[_i], LIGHT[_i], ATTEN[_i] = kind, solid, opaque, light, atten
# blocks that let skylight straight down without loss
LAVA = BLOCK_NAMES.index("Lava")
SPRUCELOG = BLOCK_NAMES.index("Spruce Log")
SPRUCELEAVES = BLOCK_NAMES.index("Spruce Leaves")
SUGARCANE = BLOCK_NAMES.index("Sugar Cane")
PUMPKIN = BLOCK_NAMES.index("Pumpkin")
DEADBUSH = BLOCK_NAMES.index("Dead Bush")
CORNFLOWER = BLOCK_NAMES.index("Cornflower")
FULLPASS = np.zeros(64, np.int64)
for _i in (AIR, GLASS, TALLGRASS, DANDELION, POPPY, TORCH, SUGARCANE, DEADBUSH, CORNFLOWER):
    FULLPASS[_i] = 1

# ---------------------------------------------------------------------------
# Noise


def make_perm(seed):
    rng = np.random.RandomState(seed & 0x7FFFFFFF)
    p = rng.permutation(256).astype(np.int64)
    return np.concatenate([p, p])


@njit(cache=True, fastmath=True, nogil=True)
def _grad(h, x, y, z):
    h &= 15
    u = x if h < 8 else y
    if h < 4:
        v = y
    elif h == 12 or h == 14:
        v = x
    else:
        v = z
    return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)


@njit(cache=True, fastmath=True, nogil=True)
def noise3(perm, x, y, z):
    fx = np.floor(x)
    fy = np.floor(y)
    fz = np.floor(z)
    X = int(fx) & 255
    Y = int(fy) & 255
    Z = int(fz) & 255
    x -= fx
    y -= fy
    z -= fz
    u = x * x * x * (x * (x * 6 - 15) + 10)
    v = y * y * y * (y * (y * 6 - 15) + 10)
    w = z * z * z * (z * (z * 6 - 15) + 10)
    A = perm[X] + Y
    AA = perm[A] + Z
    AB = perm[A + 1] + Z
    B = perm[X + 1] + Y
    BA = perm[B] + Z
    BB = perm[B + 1] + Z
    g1 = _grad(perm[AA], x, y, z)
    g2 = _grad(perm[BA], x - 1, y, z)
    g3 = _grad(perm[AB], x, y - 1, z)
    g4 = _grad(perm[BB], x - 1, y - 1, z)
    g5 = _grad(perm[AA + 1], x, y, z - 1)
    g6 = _grad(perm[BA + 1], x - 1, y, z - 1)
    g7 = _grad(perm[AB + 1], x, y - 1, z - 1)
    g8 = _grad(perm[BB + 1], x - 1, y - 1, z - 1)
    l1 = g1 + u * (g2 - g1)
    l2 = g3 + u * (g4 - g3)
    l3 = g5 + u * (g6 - g5)
    l4 = g7 + u * (g8 - g7)
    m1 = l1 + v * (l2 - l1)
    m2 = l3 + v * (l4 - l3)
    return m1 + w * (m2 - m1)


@njit(cache=True, fastmath=True, nogil=True)
def fbm2(perm, x, z, octaves):
    total = 0.0
    amp = 1.0
    norm = 0.0
    f = 1.0
    for i in range(octaves):
        total += noise3(perm, x * f, 0.31 + i * 7.13, z * f) * amp
        norm += amp
        amp *= 0.5
        f *= 2.0
    return total / norm


@njit(cache=True, nogil=True)
def hash3(x, y, z, seed):
    h = (x * 374761393 + y * 668265263 + z * 1274126177 + seed * 144665) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h = ((h ^ (h >> 16)) * 668265263) & 0xFFFFFFFF
    h = h ^ (h >> 15)
    return (h & 0xFFFFFF) / 16777216.0


@njit(cache=True, fastmath=True, nogil=True)
def terrain_height(perm, x, z):
    c = fbm2(perm, x * 0.0022, z * 0.0022, 4)
    hills = fbm2(perm, x * 0.011 + 100.0, z * 0.011, 4)
    m = fbm2(perm, x * 0.0035 + 300.0, z * 0.0035 - 200.0, 3)
    mask = min(max((m - 0.08) * 3.5, 0.0), 1.0)
    r = 1.0 - abs(fbm2(perm, x * 0.007 - 500.0, z * 0.007 + 50.0, 4))
    h = 64.0 + c * 30.0 + hills * 7.0 * (0.6 + mask) + mask * r * r * 55.0
    return min(max(h, 4.0), H - 14.0)


@njit(cache=True, fastmath=True, nogil=True)
def temperature(perm, x, z):
    return fbm2(perm, x * 0.0016 + 1000.0, z * 0.0016 - 900.0, 3)


@njit(cache=True, nogil=True)
def _put(B, x, y, z, b, only_air):
    if 0 <= x < CS and 0 <= z < CS and 0 <= y < H:
        c = B[x, y, z]
        if (not only_air) or c == AIR or c == TALLGRASS:
            B[x, y, z] = b


ORE_ID = np.array([COAL, IRON, GOLD, DIAMOND, GRAVEL, DIRT], np.int64)
ORE_N = np.array([20, 12, 3, 2, 6, 6], np.int64)
ORE_Y0 = np.array([5, 5, 5, 3, 5, 5], np.int64)
ORE_Y1 = np.array([110, 64, 32, 16, 100, 100], np.int64)
ORE_SZ = np.array([9, 7, 6, 5, 18, 18], np.int64)


@njit(cache=True, fastmath=True, nogil=True)
def gen_chunk(perm, seed, cx, cz):
    B = np.zeros((CS, H, CS), np.uint8)
    PAD = 3
    W = CS + 2 * PAD
    hm = np.empty((W, W), np.int64)
    tm = np.empty((W, W))
    x0 = cx * CS - PAD
    z0 = cz * CS - PAD
    for i in range(W):
        for k in range(W):
            hm[i, k] = int(terrain_height(perm, x0 + i, z0 + k))
            tm[i, k] = temperature(perm, x0 + i, z0 + k)
    bx = cx * CS
    bz = cz * CS
    for i in range(CS):
        for k in range(CS):
            h = hm[i + PAD, k + PAD]
            t = tm[i + PAD, k + PAD]
            wx = bx + i
            wz = bz + k
            desert = t > 0.17
            snowy = h > 88 + int(hash3(wx, 7, wz, seed) * 5)
            for y in range(h + 1):
                B[i, y, k] = STONE
            depth = 3 + int(hash3(wx, 3, wz, seed) * 2)
            if h <= SEA + 1:
                surf = SAND
                fill = SAND
                if h < SEA - 4 and noise3(perm, wx * 0.05, 5.5, wz * 0.05) > 0.1:
                    surf = GRAVEL
                    fill = GRAVEL
            elif desert:
                surf = SAND
                fill = SAND
                depth = 5
            elif snowy:
                surf = SNOWGRASS
                fill = DIRT
                if h > 104:
                    surf = SNOW_BLOCK
                    fill = STONE
            else:
                surf = GRASS
                fill = DIRT
            for y in range(max(h - depth, 1), h):
                B[i, y, k] = fill
            if desert and h > SEA + 1:
                for y in range(max(h - depth - 3, 1), max(h - depth, 1)):
                    B[i, y, k] = SANDSTONE
            B[i, h, k] = surf
            for y in range(h + 1, SEA + 1):
                B[i, y, k] = WATER
            # caves
            ytop = h if h >= SEA + 3 else h - 6
            for y in range(2, ytop + 1):
                n1 = noise3(perm, wx * 0.04, y * 0.065, wz * 0.04)
                n2 = noise3(perm, wx * 0.04 + 50.0, y * 0.065 + 30.0, wz * 0.04 - 70.0)
                carve = n1 * n1 + n2 * n2 < 0.0045
                if not carve and y < 48:
                    n3 = noise3(perm, wx * 0.018 + 9.0, y * 0.035, wz * 0.018 + 3.0)
                    carve = n3 > 0.38
                if carve:
                    B[i, y, k] = AIR
            for y in range(2, 11):
                if B[i, y, k] == AIR:
                    B[i, y, k] = LAVA
            B[i, 0, k] = BEDROCK
            if hash3(wx, 1, wz, seed) < 0.5:
                B[i, 1, k] = BEDROCK
            if hash3(wx, 2, wz, seed) < 0.2:
                B[i, 2, k] = BEDROCK
    # ores
    for o in range(ORE_ID.shape[0]):
        for v in range(ORE_N[o]):
            s = seed + o * 101
            x = int(hash3(cx, v, cz, s) * CS)
            z = int(hash3(cx, v + 1000, cz, s) * CS)
            y = ORE_Y0[o] + int(hash3(cx, v + 2000, cz, s) * (ORE_Y1[o] - ORE_Y0[o]))
            for n in range(ORE_SZ[o]):
                if 0 <= x < CS and 0 <= z < CS and 0 < y < H and B[x, y, z] == STONE:
                    B[x, y, z] = ORE_ID[o]
                r = hash3(cx * 31 + n, v, cz * 17 + o, s + 7)
                if r < 0.33:
                    x += 1 if hash3(n, v, o, s + 1) < 0.5 else -1
                elif r < 0.66:
                    y += 1 if hash3(n, v, o, s + 2) < 0.5 else -1
                else:
                    z += 1 if hash3(n, v, o, s + 3) < 0.5 else -1
    # trees (may spill from neighbouring columns)
    for i in range(W):
        for k in range(W):
            h = hm[i, k]
            wx = x0 + i
            wz = z0 + k
            if h <= SEA + 1 or tm[i, k] > 0.17 or h > 104:
                continue
            snowy = h > 88 + int(hash3(wx, 7, wz, seed) * 5)
            forest = fbm2(perm, wx * 0.006 + 2000.0, wz * 0.006, 2)
            p = 0.003 + max(forest, 0.0) * 0.09
            if hash3(wx, 11, wz, seed) >= p:
                continue
            lx = i - PAD
            lz = k - PAD
            if 0 <= lx < CS and 0 <= lz < CS and B[lx, h, lz] != GRASS and B[lx, h, lz] != SNOWGRASS:
                continue
            if snowy or tm[i, k] < -0.25:
                th = 6 + int(hash3(wx, 13, wz, seed) * 4)
                top = h + 1 + th
                for yy in range(h + 3, top + 1):
                    j = top - yy
                    rad = 0 if j == 0 else (1 if (j % 2 == 1 or j < 3) else 2)
                    for ox in range(-rad, rad + 1):
                        for oz in range(-rad, rad + 1):
                            if rad == 2 and abs(ox) == 2 and abs(oz) == 2:
                                continue
                            _put(B, lx + ox, yy, lz + oz, SPRUCELEAVES, True)
                for y in range(h + 1, top):
                    _put(B, lx, y, lz, SPRUCELOG, False)
                _put(B, lx, h, lz, DIRT, False)
                continue
            birch = hash3(wx, 12, wz, seed) < 0.25
            log = BIRCHLOG if birch else LOG
            leaf = BIRCHLEAVES if birch else LEAVES
            th = 4 + int(hash3(wx, 13, wz, seed) * 3)
            top = h + 1 + th
            for dy in range(-3, 1):
                yy = top + dy
                rad = 2 if dy < -1 else 1
                for ox in range(-rad, rad + 1):
                    for oz in range(-rad, rad + 1):
                        if abs(ox) == rad and abs(oz) == rad:
                            if dy == 0 or hash3(wx + ox, yy, wz + oz, seed) < 0.5:
                                continue
                        _put(B, lx + ox, yy, lz + oz, leaf, True)
            for y in range(h + 1, top):
                _put(B, lx, y, lz, log, False)
            _put(B, lx, h, lz, DIRT, False)
    # plants and cacti
    for i in range(CS):
        for k in range(CS):
            h = hm[i + PAD, k + PAD]
            if h + 4 >= H:
                continue
            wx = bx + i
            wz = bz + k
            s = B[i, h, k]
            if B[i, h + 1, k] != AIR:
                continue
            r = hash3(wx, 21, wz, seed)
            near_water = False
            for dd in range(4):
                ni = i + DX[dd] if dd < 2 else i
                nk = k + DZ[dd + 2] if dd >= 2 else k
                if 0 <= ni < CS and 0 <= nk < CS and B[ni, h, nk] == WATER:
                    near_water = True
            if (s == GRASS or s == SAND) and near_water and h >= SEA - 1:
                if r < 0.25:
                    ch = 1 + int(hash3(wx, 23, wz, seed) * 3)
                    for y in range(h + 1, h + 1 + ch):
                        B[i, y, k] = SUGARCANE
            elif s == GRASS:
                if r < 0.12:
                    B[i, h + 1, k] = TALLGRASS
                elif r < 0.128:
                    B[i, h + 1, k] = DANDELION
                elif r < 0.136:
                    B[i, h + 1, k] = POPPY
                elif r < 0.1375:
                    B[i, h + 1, k] = PUMPKIN
                elif r < 0.144:
                    B[i, h + 1, k] = CORNFLOWER
            elif s == SAND and tm[i + PAD, k + PAD] > 0.17 and h > SEA + 1:
                if r < 0.006 and 0 < i < CS - 1 and 0 < k < CS - 1:
                    ch = 1 + int(hash3(wx, 22, wz, seed) * 3)
                    for y in range(h + 1, h + 1 + ch):
                        B[i, y, k] = CACTUS
                elif 0.006 <= r < 0.016:
                    B[i, h + 1, k] = DEADBUSH
    return B


SNOW_BLOCK = BLOCK_NAMES.index("Snow Block")

# ---------------------------------------------------------------------------
# Lighting

DX = np.array([1, -1, 0, 0, 0, 0], np.int64)
DY = np.array([0, 0, 1, -1, 0, 0], np.int64)
DZ = np.array([0, 0, 0, 0, 1, -1], np.int64)


@njit(cache=True, nogil=True)
def _bfs(P, L, q, head, tail):
    W = P.shape[0]
    D = P.shape[2]
    MASK = q.shape[0] - 1
    while head < tail:
        idx = q[head & MASK]
        head += 1
        z = idx % D
        t = idx // D
        y = t % H
        x = t // H
        l = int(L[x, y, z])
        if l <= 1:
            continue
        for d in range(6):
            nx = x + DX[d]
            ny = y + DY[d]
            nz = z + DZ[d]
            if nx < 0 or nx >= W or ny < 0 or ny >= H or nz < 0 or nz >= D:
                continue
            b = P[nx, ny, nz]
            if OPAQUE[b]:
                continue
            nl = l - 1 - ATTEN[b]
            if nl > int(L[nx, ny, nz]):
                L[nx, ny, nz] = nl
                q[tail & MASK] = (nx * H + ny) * D + nz
                tail += 1
    return tail


@njit(cache=True, nogil=True)
def compute_light(P):
    W = P.shape[0]
    D = P.shape[2]
    sky = np.zeros(P.shape, np.uint8)
    blk = np.zeros(P.shape, np.uint8)
    q = np.empty(1 << 20, np.int32)
    MASK = (1 << 20) - 1
    tail = 0
    for x in range(W):
        for z in range(D):
            for y in range(H - 1, -1, -1):
                b = P[x, y, z]
                if not FULLPASS[b]:
                    break
                sky[x, y, z] = 15
                q[tail & MASK] = (x * H + y) * D + z
                tail += 1
    _bfs(P, sky, q, 0, tail)
    tail = 0
    for x in range(W):
        for y in range(H):
            for z in range(D):
                e = LIGHT[P[x, y, z]]
                if e > 0:
                    blk[x, y, z] = e
                    q[tail & MASK] = (x * H + y) * D + z
                    tail += 1
    _bfs(P, blk, q, 0, tail)
    return sky, blk


# ---------------------------------------------------------------------------
# Meshing

FACE_C = np.array([
    [[1, 0, 0], [1, 1, 0], [1, 1, 1], [1, 0, 1]],   # +x
    [[0, 0, 0], [0, 0, 1], [0, 1, 1], [0, 1, 0]],   # -x
    [[0, 1, 0], [0, 1, 1], [1, 1, 1], [1, 1, 0]],   # +y
    [[0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]],   # -y
    [[0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]],   # +z
    [[0, 0, 0], [0, 1, 0], [1, 1, 0], [1, 0, 0]],   # -z
], np.float64)
FACE_SHADE = np.array([0.62, 0.62, 1.0, 0.5, 0.8, 0.8])
AO_F = np.array([0.42, 0.6, 0.8, 1.0])

CROSS_C = np.array([
    [[0.15, 0, 0.15], [0.85, 0, 0.85], [0.85, 1, 0.85], [0.15, 1, 0.15]],
    [[0.85, 0, 0.85], [0.15, 0, 0.15], [0.15, 1, 0.15], [0.85, 1, 0.85]],
    [[0.85, 0, 0.15], [0.15, 0, 0.85], [0.15, 1, 0.85], [0.85, 1, 0.15]],
    [[0.15, 0, 0.85], [0.85, 0, 0.15], [0.85, 1, 0.15], [0.15, 1, 0.85]],
])
CROSS_UV = np.array([[0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]])


@njit(cache=True, nogil=True)
def _opq(P, x, y, z):
    if y < 0:
        return 1
    if y >= H:
        return 0
    return OPAQUE[P[x, y, z]]


@njit(cache=True, nogil=True)
def _lt(L, x, y, z, top):
    if y >= H:
        return top
    if y < 0:
        return 0
    return int(L[x, y, z])


@njit(cache=True, nogil=True)
def _local_uv(d, px, py, pz):
    if d == 2 or d == 3:
        return px, pz
    if d == 0 or d == 1:
        return pz, 1.0 - py
    return px, 1.0 - py


@njit(cache=True, nogil=True)
def _vert(V, L, n, x, y, z, w, u, v, sk, bl, sh):
    V[n, 0] = x
    V[n, 1] = y
    V[n, 2] = z
    V[n, 3] = w
    V[n, 4] = u
    V[n, 5] = v
    L[n, 0] = min(255, int(sk * 17.0 + 0.5))
    L[n, 1] = min(255, int(bl * 17.0 + 0.5))
    L[n, 2] = min(255, int(sh * 255.0 + 0.5))
    L[n, 3] = 255
    return n + 1


@njit(cache=True, nogil=True)
def mesh_chunk(P):
    """P: padded blocks (48,H,48). Returns opaque verts/lights and water verts/lights."""
    sky, blk = compute_light(P)
    o = CS
    nsolid = 0
    nwater = 0
    for x in range(o, o + CS):
        for y in range(H):
            for z in range(o, o + CS):
                b = P[x, y, z]
                if b == WATER:
                    nwater += 1
                elif b != AIR:
                    nsolid += 1
    cap = min(nsolid * 6, CS * CS * H * 6) * 4 + 4
    wcap = min(nwater * 6, CS * CS * H * 6) * 4 + 4
    V = np.empty((cap, 6), np.float32)
    LL = np.empty((cap, 4), np.uint8)
    WV = np.empty((wcap, 6), np.float32)
    WL = np.empty((wcap, 4), np.uint8)
    n = 0
    wn = 0
    csk = np.zeros(4)
    cbl = np.zeros(4)
    cao = np.zeros(4, np.int64)
    for x in range(o, o + CS):
        for z in range(o, o + CS):
            for y in range(H):
                b = P[x, y, z]
                if b == AIR:
                    continue
                k = KIND[b]
                lx = float(x - o)
                lz = float(z - o)
                fy = float(y)
                if k == K_CUBE:
                    for d in range(6):
                        nx = x + DX[d]
                        ny = y + DY[d]
                        nz = z + DZ[d]
                        if ny < 0:
                            continue
                        if ny < H:
                            nb = P[nx, ny, nz]
                            if OPAQUE[nb] or nb == b:
                                continue
                        t = TEX[b, d]
                        tu = float(t % 16)
                        tv = float(t // 16)
                        for ci in range(4):
                            c0 = FACE_C[d, ci, 0]
                            c1 = FACE_C[d, ci, 1]
                            c2 = FACE_C[d, ci, 2]
                            ox = (2 * int(c0) - 1) if DX[d] == 0 else 0
                            oy = (2 * int(c1) - 1) if DY[d] == 0 else 0
                            oz = (2 * int(c2) - 1) if DZ[d] == 0 else 0
                            if DX[d] != 0:
                                s1x, s1y, s1z = nx, ny + oy, nz
                                s2x, s2y, s2z = nx, ny, nz + oz
                            elif DY[d] != 0:
                                s1x, s1y, s1z = nx + ox, ny, nz
                                s2x, s2y, s2z = nx, ny, nz + oz
                            else:
                                s1x, s1y, s1z = nx + ox, ny, nz
                                s2x, s2y, s2z = nx, ny + oy, nz
                            o1 = _opq(P, s1x, s1y, s1z)
                            o2 = _opq(P, s2x, s2y, s2z)
                            oc = _opq(P, nx + ox, ny + oy, nz + oz)
                            sk = float(_lt(sky, nx, ny, nz, 15))
                            bl = float(_lt(blk, nx, ny, nz, 0))
                            cnt = 1.0
                            if not o1:
                                sk += _lt(sky, s1x, s1y, s1z, 15)
                                bl += _lt(blk, s1x, s1y, s1z, 0)
                                cnt += 1.0
                            if not o2:
                                sk += _lt(sky, s2x, s2y, s2z, 15)
                                bl += _lt(blk, s2x, s2y, s2z, 0)
                                cnt += 1.0
                            if not oc and not (o1 and o2):
                                sk += _lt(sky, nx + ox, ny + oy, nz + oz, 15)
                                bl += _lt(blk, nx + ox, ny + oy, nz + oz, 0)
                                cnt += 1.0
                            csk[ci] = sk / cnt
                            cbl[ci] = bl / cnt
                            cao[ci] = 0 if (o1 and o2) else 3 - (o1 + o2 + oc)
                        start = 0
                        if cao[0] + cao[2] < cao[1] + cao[3]:
                            start = 1
                        for j in range(4):
                            ci = (start + j) & 3
                            c0 = FACE_C[d, ci, 0]
                            c1 = FACE_C[d, ci, 1]
                            c2 = FACE_C[d, ci, 2]
                            lu, lv = _local_uv(d, c0, c1, c2)
                            n = _vert(V, LL, n, lx + c0, fy + c1, lz + c2, 0.0,
                                      (tu + lu) / 16.0, (tv + lv) / 16.0,
                                      csk[ci], cbl[ci], FACE_SHADE[d] * AO_F[cao[ci]])
                elif k == K_CROSS:
                    t = TEX[b, 0]
                    tu = float(t % 16)
                    tv = float(t // 16)
                    sk = float(sky[x, y, z])
                    bl = float(blk[x, y, z])
                    for qd in range(4):
                        for ci in range(4):
                            px = CROSS_C[qd, ci, 0]
                            py = CROSS_C[qd, ci, 1]
                            pz = CROSS_C[qd, ci, 2]
                            n = _vert(V, LL, n, lx + px, fy + py, lz + pz, 2.0 if py > 0.5 else 0.0,
                                      (tu + CROSS_UV[ci, 0]) / 16.0, (tv + CROSS_UV[ci, 1]) / 16.0,
                                      sk, bl, 0.9)
                elif k == K_TORCH:
                    t = TEX[b, 0]
                    tu = float(t % 16)
                    tv = float(t // 16)
                    sk = float(sky[x, y, z])
                    bl = float(blk[x, y, z])
                    for d in range(6):
                        for ci in range(4):
                            px = 7.0 / 16.0 + FACE_C[d, ci, 0] * (2.0 / 16.0)
                            py = FACE_C[d, ci, 1] * (10.0 / 16.0)
                            pz = 7.0 / 16.0 + FACE_C[d, ci, 2] * (2.0 / 16.0)
                            lu, lv = _local_uv(d, px, py, pz)
                            if d == 2:
                                lv = lv - 1.0 / 16.0
                            n = _vert(V, LL, n, lx + px, fy + py, lz + pz, 0.0,
                                      (tu + lu) / 16.0, (tv + lv) / 16.0, sk, bl, FACE_SHADE[d])
                elif k == K_LAVA:
                    above_lava = y + 1 < H and P[x, y + 1, z] == LAVA
                    t = TEX[b, 0]
                    tu = float(t % 16)
                    tv = float(t // 16)
                    for d in range(6):
                        nx = x + DX[d]
                        ny = y + DY[d]
                        nz = z + DZ[d]
                        if ny < 0:
                            continue
                        if ny < H:
                            nb = P[nx, ny, nz]
                            if nb == LAVA or OPAQUE[nb]:
                                continue
                        for ci in range(4):
                            c0 = FACE_C[d, ci, 0]
                            c1 = FACE_C[d, ci, 1]
                            c2 = FACE_C[d, ci, 2]
                            if c1 > 0.5 and not above_lava:
                                c1 = 0.875
                            lu, lv = _local_uv(d, c0, c1, c2)
                            n = _vert(V, LL, n, lx + c0, fy + c1, lz + c2, 3.0,
                                      (tu + lu) / 16.0, (tv + lv) / 16.0, 15.0, 15.0, 1.0)
                elif k == K_WATER:
                    above_water = y + 1 < H and P[x, y + 1, z] == WATER
                    t = TEX[b, 0]
                    tu = float(t % 16)
                    tv = float(t // 16)
                    for d in range(6):
                        nx = x + DX[d]
                        ny = y + DY[d]
                        nz = z + DZ[d]
                        if ny < 0:
                            continue
                        if ny < H:
                            nb = P[nx, ny, nz]
                            if nb == WATER or OPAQUE[nb]:
                                continue
                        sk = float(_lt(sky, nx, ny, nz, 15))
                        bl = float(_lt(blk, nx, ny, nz, 0))
                        for ci in range(4):
                            c0 = FACE_C[d, ci, 0]
                            c1 = FACE_C[d, ci, 1]
                            c2 = FACE_C[d, ci, 2]
                            wflag = 0.0
                            if c1 > 0.5 and not above_water:
                                c1 = 0.875
                                wflag = 1.0
                            lu, lv = _local_uv(d, c0, c1, c2)
                            wn = _vert(WV, WL, wn, lx + c0, fy + c1, lz + c2, wflag,
                                       (tu + lu) / 16.0, (tv + lv) / 16.0, sk, bl, FACE_SHADE[d])
    return V[:n].copy(), LL[:n].copy(), WV[:wn].copy(), WL[:wn].copy()
OBSIDIAN_ID = BLOCK_NAMES.index("Obsidian")
