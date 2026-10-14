"""StelexCraft - a Minecraft-style voxel sandbox.  Run:  python stelexcraft.py"""
import math
import os
import pickle
import random
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pygame
import moderngl

import engine as E
import textures
from engine import CS, H

HERE = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.path.join(HERE, "world.sav")
AUTOTEST = os.environ.get("STELEX_AUTOTEST")
if AUTOTEST:
    SAVE_PATH = os.path.join(AUTOTEST, "test.sav")
DAY_LENGTH = 1200.0  # seconds per full day, like Minecraft

VTX = np.dtype([("p", "<f2", (6,)), ("l", "u1", (4,))])
VFMT = "4f2 2f2 4f1"

CHUNK_VS = """
#version 330
uniform mat4 m_vp;
uniform vec3 u_off;
uniform vec3 u_cam;
uniform float u_time;
in vec4 in_pos;
in vec2 in_uv;
in vec4 in_light;
out vec2 v_uv;
out vec3 v_light;
out vec3 v_rel;
out float v_glow;
void main() {
    vec3 rel = in_pos.xyz + u_off;
    vec3 w = rel + u_cam;
    v_glow = 0.0;
    if (in_pos.w > 2.5) {
        v_glow = 1.0;
    } else if (in_pos.w > 1.5) {
        rel.x += sin(u_time * 1.6 + w.x * 0.7 + w.z * 0.4) * 0.05;
        rel.z += cos(u_time * 1.3 + w.x * 0.3 + w.z * 0.8) * 0.05;
    } else if (in_pos.w > 0.5) {
        rel.y += (sin(u_time * 1.8 + w.x * 0.9 + w.z * 0.6) * 0.5 - 0.5) * 0.06;
    }
    v_rel = rel;
    v_uv = in_uv;
    v_light = in_light.xyz;
    gl_Position = m_vp * vec4(rel, 1.0);
}
"""

CHUNK_FS = """
#version 330
uniform sampler2D u_tex;
uniform float u_daylight;
uniform vec3 u_fog_color;
uniform float u_fog_start;
uniform float u_fog_end;
uniform int u_water;
uniform float u_time;
in vec2 v_uv;
in vec3 v_light;
in vec3 v_rel;
in float v_glow;
out vec4 frag;
void main() {
    vec4 c = texture(u_tex, v_uv);
    if (u_water == 0 && c.a < 0.5) discard;
    if (v_glow > 0.5) {
        vec3 wp = v_rel;
        c.rgb *= 0.8 + 0.25 * sin(u_time * 1.7 + (wp.x + wp.z) * 0.9) * sin(u_time * 1.1 - wp.x * 0.6 + wp.z * 0.4);
        c.rgb += vec3(0.08, 0.03, 0.0) * sin(u_time * 2.3 + wp.z);
    }
    float s = v_light.x * u_daylight;
    float b = v_light.y;
    float l = max(s, b);
    float br = 0.035 + 0.965 * pow(0.8, (1.0 - l) * 15.0);
    vec3 tint = mix(vec3(1.0), vec3(1.18, 1.0, 0.78), clamp((b - s) * 1.4, 0.0, 1.0));
    vec3 col = c.rgb * br * v_light.z * tint;
    float a = 1.0;
    if (u_water == 1) {
        col *= 0.92 + 0.08 * sin(u_time * 2.0 + (v_rel.x + v_rel.z) * 1.3);
        a = 0.72;
    }
    float d = length(v_rel.xz);
    float f = clamp((d - u_fog_start) / (u_fog_end - u_fog_start), 0.0, 1.0);
    col = mix(col, u_fog_color, f);
    frag = vec4(col, a);
}
"""

SIMPLE_VS = """
#version 330
uniform mat4 m_vp;
in vec3 in_pos;
in vec2 in_uv;
in vec4 in_color;
out vec2 v_uv;
out vec4 v_color;
out vec3 v_rel;
void main() {
    v_uv = in_uv;
    v_color = in_color;
    v_rel = in_pos;
    gl_Position = m_vp * vec4(in_pos, 1.0);
}
"""

SIMPLE_FS = """
#version 330
uniform sampler2D u_tex;
uniform int u_use_tex;
uniform vec3 u_fog_color;
uniform float u_fog_end;
uniform int u_fog;
in vec2 v_uv;
in vec4 v_color;
in vec3 v_rel;
out vec4 frag;
void main() {
    vec4 c = v_color;
    if (u_use_tex == 1) c *= texture(u_tex, v_uv);
    if (c.a < 0.02) discard;
    if (u_fog == 1) {
        float f = clamp(length(v_rel.xz) / u_fog_end, 0.0, 1.0);
        c.rgb = mix(c.rgb, u_fog_color, f * f);
        c.a *= 1.0 - f * f;
    }
    frag = c;
}
"""

GUI_VS = """
#version 330
uniform vec2 u_screen;
in vec2 in_pos;
in vec2 in_uv;
in vec4 in_color;
out vec2 v_uv;
out vec4 v_color;
void main() {
    v_uv = in_uv;
    v_color = in_color;
    gl_Position = vec4(in_pos.x / u_screen.x * 2.0 - 1.0, 1.0 - in_pos.y / u_screen.y * 2.0, 0.0, 1.0);
}
"""

GUI_FS = """
#version 330
uniform sampler2D u_tex;
in vec2 v_uv;
in vec4 v_color;
out vec4 frag;
void main() {
    vec4 c = texture(u_tex, v_uv) * v_color;
    if (c.a < 0.01) discard;
    frag = c;
}
"""


# ---------------------------------------------------------------------------
# math helpers

def perspective(fovy, aspect, near, far):
    f = 1.0 / math.tan(math.radians(fovy) / 2)
    return np.array([[f / aspect, 0, 0, 0], [0, f, 0, 0],
                     [0, 0, (far + near) / (near - far), 2 * far * near / (near - far)],
                     [0, 0, -1, 0]], np.float64)


def view_rot(fwd):
    f = fwd / np.linalg.norm(fwd)
    s = np.cross(f, (0.0, 1.0, 0.0))
    s /= np.linalg.norm(s)
    u = np.cross(s, f)
    m = np.identity(4)
    m[0, :3] = s
    m[1, :3] = u
    m[2, :3] = -f
    return m


def mat_bytes(m):
    return m.T.astype("f4").tobytes()


# ---------------------------------------------------------------------------
# world / chunk streaming

def _mesh_job(P):
    v, l, wv, wl = E.mesh_chunk(P)
    a = np.empty(len(v), VTX)
    a["p"] = v
    a["l"] = l
    b = np.empty(len(wv), VTX)
    b["p"] = wv
    b["l"] = wl
    return a.tobytes(), len(v) // 4, b.tobytes(), len(wv) // 4


class World:
    def __init__(self, ctx, prog, seed, edits):
        self.ctx = ctx
        self.prog = prog
        self.seed = seed
        self.perm = E.make_perm(seed)
        self.edits = edits
        self.chunks = {}
        self.torches = {}
        self.meshes = {}
        self.dirty = set()
        self.ver = {}
        self.applied = {}
        self.gen_f = {}
        self.mesh_f = {}
        self.workers = max(2, min(8, (os.cpu_count() or 4) - 2))
        self.pool = ThreadPoolExecutor(self.workers)
        self.radius = 10
        self.center = None
        self.wanted = []
        self.wanted_set = set()
        maxq = CS * CS * H * 6
        idx = np.array([0, 1, 2, 0, 2, 3], np.uint32)
        allidx = (np.arange(maxq, dtype=np.uint32)[:, None] * 4 + idx[None, :]).ravel()
        self.ibo = ctx.buffer(allidx.tobytes())

    # -- block access
    def get(self, x, y, z):
        if y < 0:
            return E.BEDROCK
        if y >= H:
            return E.AIR
        c = self.chunks.get((x >> 4, z >> 4))
        if c is None:
            return None
        return int(c[x & 15, y, z & 15])

    def set(self, x, y, z, b, sync=True):
        if not 0 <= y < H:
            return set()
        key = (x >> 4, z >> 4)
        arr = self.chunks.get(key)
        if arr is None:
            return set()
        lx, lz = x & 15, z & 15
        old = arr[lx, y, lz]
        arr[lx, y, lz] = b
        if b == E.TORCH or old == E.TORCH:
            self.index_torches(key, arr)
        self.edits.setdefault(key, {})[(lx, y, lz)] = b
        touched = set()
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                k2 = (key[0] + dx, key[1] + dz)
                if k2 in self.chunks:
                    self.ver[k2] = self.ver.get(k2, 0) + 1
                    touched.add(k2)
        if sync:
            near = {key}
            if lx == 0:
                near.add((key[0] - 1, key[1]))
            if lx == 15:
                near.add((key[0] + 1, key[1]))
            if lz == 0:
                near.add((key[0], key[1] - 1))
            if lz == 15:
                near.add((key[0], key[1] + 1))
            self.remesh(touched, near)
        return touched

    def remesh(self, touched, now):
        for k in touched:
            if k in now and self.ready(k):
                self.upload(k, _mesh_job(self.padded(k)))
                self.applied[k] = self.ver.get(k, 0)
                self.dirty.discard(k)
            elif k in self.meshes or self.ready(k):
                self.dirty.add(k)

    def index_torches(self, key, arr):
        t = np.argwhere(arr == E.TORCH)
        if len(t):
            self.torches[key] = t + (key[0] * 16, 0, key[1] * 16)
        else:
            self.torches.pop(key, None)

    def ready(self, key):
        cx, cz = key
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                if (cx + dx, cz + dz) not in self.chunks:
                    return False
        return True

    def padded(self, key):
        cx, cz = key
        P = np.empty((48, H, 48), np.uint8)
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                P[(i + 1) * 16:(i + 2) * 16, :, (j + 1) * 16:(j + 2) * 16] = self.chunks[(cx + i, cz + j)]
        return P

    def upload(self, key, res):
        ob, nq, wb, wq = res
        self.release(key)
        m = [None, None, 0, None, None, 0]
        if nq:
            m[0] = self.ctx.buffer(ob)
            m[1] = self.ctx.vertex_array(self.prog, [(m[0], VFMT, "in_pos", "in_uv", "in_light")],
                                         index_buffer=self.ibo, index_element_size=4)
            m[2] = nq * 6
        if wq:
            m[3] = self.ctx.buffer(wb)
            m[4] = self.ctx.vertex_array(self.prog, [(m[3], VFMT, "in_pos", "in_uv", "in_light")],
                                         index_buffer=self.ibo, index_element_size=4)
            m[5] = wq * 6
        self.meshes[key] = m

    def release(self, key):
        m = self.meshes.pop(key, None)
        if m:
            for o in m:
                if o is not None and not isinstance(o, int):
                    o.release()

    def set_center(self, pc):
        self.center = pc
        R = self.radius + 1
        cx, cz = pc
        lst = []
        for dx in range(-R, R + 1):
            for dz in range(-R, R + 1):
                d = dx * dx + dz * dz
                if d <= R * R + 1:
                    lst.append((d, (cx + dx, cz + dz)))
        lst.sort()
        self.wanted = [k for _, k in lst]
        self.wanted_set = set(self.wanted)
        far = self.radius + 4
        for k in list(self.chunks):
            if max(abs(k[0] - cx), abs(k[1] - cz)) > far:
                del self.chunks[k]
                self.torches.pop(k, None)
                self.release(k)
                self.dirty.discard(k)
                self.applied.pop(k, None)
        for k in list(self.meshes):
            if (k[0] - cx) ** 2 + (k[1] - cz) ** 2 > (self.radius + 2) ** 2:
                self.release(k)

    def in_mesh_range(self, k):
        cx, cz = self.center
        return (k[0] - cx) ** 2 + (k[1] - cz) ** 2 <= self.radius * self.radius + 1

    def update(self, px, pz, budget_s=0.006):
        pc = (math.floor(px / 16), math.floor(pz / 16))
        if pc != self.center:
            self.set_center(pc)
        t0 = time.perf_counter()
        for key, f in list(self.gen_f.items()):
            if not f.done():
                continue
            del self.gen_f[key]
            if key not in self.wanted_set:
                continue
            arr = f.result()
            e = self.edits.get(key)
            if e:
                for (lx, y, lz), b in e.items():
                    arr[lx, y, lz] = b
            self.chunks[key] = arr
            self.index_torches(key, arr)
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    k2 = (key[0] + dx, key[1] + dz)
                    if k2 in self.chunks and k2 not in self.meshes and self.in_mesh_range(k2) and self.ready(k2):
                        self.dirty.add(k2)
        for key, (f, ver) in list(self.mesh_f.items()):
            if not f.done():
                continue
            del self.mesh_f[key]
            if key in self.chunks and ver >= self.applied.get(key, -1) and self.in_mesh_range(key):
                self.upload(key, f.result())
                self.applied[key] = ver
            if time.perf_counter() - t0 > budget_s:
                break
        limit = self.workers * 2
        if len(self.gen_f) < limit:
            for key in self.wanted:
                if key not in self.chunks and key not in self.gen_f:
                    self.gen_f[key] = self.pool.submit(E.gen_chunk, self.perm, self.seed, key[0], key[1])
                    if len(self.gen_f) >= limit:
                        break
        if self.dirty and len(self.mesh_f) < limit:
            cx, cz = self.center
            for key in sorted(self.dirty, key=lambda k: (k[0] - cx) ** 2 + (k[1] - cz) ** 2):
                if len(self.mesh_f) >= limit:
                    break
                if key in self.mesh_f:
                    continue
                if not self.in_mesh_range(key) or key not in self.chunks:
                    self.dirty.discard(key)
                    continue
                if not self.ready(key):
                    continue
                self.mesh_f[key] = (self.pool.submit(_mesh_job, self.padded(key)), self.ver.get(key, 0))
                self.dirty.discard(key)
        # make sure missing meshes in range get scheduled (e.g. after radius change)
        if not self.dirty and not self.mesh_f and not self.gen_f:
            for key in self.wanted:
                if key not in self.meshes and key in self.chunks and self.in_mesh_range(key) and self.ready(key):
                    self.dirty.add(key)

    def pending(self):
        return len(self.gen_f) + len(self.mesh_f) + len(self.dirty)

    def draw(self, vp, cam, water):
        keys = [k for k, m in self.meshes.items() if (m[5] if water else m[2])]
        if not keys:
            return
        ka = np.array(keys, np.float64)
        centers = np.stack([ka[:, 0] * 16 + 8 - cam[0], np.full(len(ka), 64 - cam[1]), ka[:, 1] * 16 + 8 - cam[2]], 1)
        planes = np.array([vp[3] + vp[0], vp[3] - vp[0], vp[3] + vp[1], vp[3] - vp[1], vp[3] + vp[2], vp[3] - vp[2]])
        d = centers @ planes[:, :3].T + planes[:, 3]
        r = np.abs(planes[:, :3]) @ np.array([8.0, 64.0, 8.0])
        vis = np.all(d + r >= 0, axis=1)
        order = np.nonzero(vis)[0]
        if water:
            dist = (centers[order, 0] ** 2 + centers[order, 2] ** 2)
            order = order[np.argsort(-dist)]
        u_off = self.prog["u_off"]
        for i in order:
            k = keys[i]
            m = self.meshes[k]
            u_off.value = (k[0] * 16 - cam[0], -cam[1], k[1] * 16 - cam[2])
            if water:
                m[4].render(moderngl.TRIANGLES, vertices=m[5])
            else:
                m[1].render(moderngl.TRIANGLES, vertices=m[2])
        return len(order)


# ---------------------------------------------------------------------------
# sound

class Sounds:
    def __init__(self):
        self.ok = False
        try:
            pygame.mixer.init(44100, -16, 2, 512)
            pygame.mixer.set_num_channels(24)
            self.ok = True
        except Exception:
            return
        r = np.random.RandomState(3)
        sr = 44100

        def mk(dur, k, decay, vol, tone=0.0, tone_f=0.0, hp=False):
            n = int(sr * dur)
            x = r.uniform(-1, 1, n)
            if k > 1:
                x = np.convolve(x, np.ones(k) / k, "same")
                x /= max(1e-6, np.abs(x).max())
            if hp:
                x = np.diff(x, prepend=0)
                x /= max(1e-6, np.abs(x).max())
            t = np.arange(n) / sr
            if tone:
                x = x * (1 - tone) + tone * np.sin(2 * np.pi * tone_f * t * (1 - t / dur * 0.4))
            env = np.exp(-t / decay) * np.minimum(1, t / 0.003)
            y = (x * env * vol * 32767).astype(np.int16)
            return pygame.sndarray.make_sound(np.ascontiguousarray(np.stack([y, y], 1)))

        self.s = {}
        for kind, (k, dec, tone, tf, hp) in {
            "stone": (2, 0.05, 0.0, 0, True), "grass": (6, 0.07, 0.0, 0, False),
            "wood": (4, 0.06, 0.45, 140, False), "sand": (3, 0.08, 0.0, 0, False),
            "glass": (1, 0.08, 0.5, 2600, True), "wool": (14, 0.06, 0.0, 0, False),
        }.items():
            self.s["break_" + kind] = [mk(0.25, k, dec, 0.55, tone, tf * (0.9 + 0.2 * i), hp) for i in range(3)]
            self.s["place_" + kind] = [mk(0.15, k, dec * 0.7, 0.45, tone, tf * 1.1, hp) for i in range(2)]
            self.s["step_" + kind] = [mk(0.12, k, dec * 0.6, 0.18, tone, tf, hp) for i in range(4)]
        self.s["explode"] = [mk(2.0, 40, 0.45, 0.95, 0.35, 45)]
        self.s["fuse"] = [mk(1.2, 1, 0.8, 0.12, 0.0, 0, True)]
        self.s["splash"] = [mk(0.4, 8, 0.12, 0.3)]
        self.s["hurt"] = [mk(0.25, 3, 0.08, 0.5, 0.7, 420 + 60 * i) for i in range(3)]
        self.s["pop"] = [mk(0.3, 2, 0.1, 0.5, 0.6, 900)]
        def voice(dur, f0, f1, vol, buzz):
            n = int(sr * dur)
            t = np.arange(n) / sr
            f = f0 + (f1 - f0) * t / dur
            ph = 2 * np.pi * np.cumsum(f) / sr
            x = np.sin(ph) + buzz * np.sign(np.sin(ph * 2))
            x += r.uniform(-0.15, 0.15, n)
            env = np.minimum(1, t / 0.03) * np.minimum(1, (dur - t) / 0.08)
            y = (x / (1 + buzz) * env * vol * 32767).astype(np.int16)
            return pygame.sndarray.make_sound(np.ascontiguousarray(np.stack([y, y], 1)))

        self.s["pig"] = [voice(0.25, 260, 200, 0.35, 0.6), voice(0.2, 300, 230, 0.35, 0.6)]
        self.s["cow"] = [voice(0.9, 130, 105, 0.4, 0.4)]
        self.s["sheep"] = [voice(0.6, 420, 380, 0.25, 0.3)]
        self.s["rain"] = [mk(3.0, 3, 1e9, 0.25)]
        self.s["pickup"] = [mk(0.12, 1, 0.04, 0.35, 0.8, 1400 + 300 * i) for i in range(3)]
        self.s["groan"] = [mk(0.8, 4, 0.35, 0.5, 0.85, 95 + 15 * i) for i in range(2)]

    def play(self, name, vol=1.0):
        if not self.ok:
            return
        lst = self.s.get(name)
        if lst:
            snd = random.choice(lst)
            ch = snd.play()
            if ch:
                ch.set_volume(vol)

    def block(self, action, b):
        kind = E.BLOCK_SOUND[b] if 0 <= b < len(E.BLOCK_SOUND) else ""
        if kind:
            self.play(action + "_" + kind)


# ---------------------------------------------------------------------------
# player

class Player:
    HW = 0.3
    HEIGHT = 1.8
    EYE = 1.62

    def __init__(self, pos):
        self.pos = np.array(pos, np.float64)
        self.vel = np.zeros(3)
        self.yaw = 0.0
        self.pitch = 0.0
        self.on_ground = False
        self.flying = False
        self.sprint = False
        self.walk = 0.0
        self.step_acc = 0.0
        self.fall_start = None
        self.crouch = 0.0

    def eye(self, bob=True):
        e = self.pos + (0, self.EYE - getattr(self, "crouch", 0.0), 0)
        if bob and self.on_ground and not self.flying:
            e = e + (0, abs(math.sin(self.walk * math.pi)) * 0.06, 0)
        return e

    def forward(self):
        cp = math.cos(self.pitch)
        return np.array([math.sin(self.yaw) * cp, math.sin(self.pitch), -math.cos(self.yaw) * cp])

    def hits(self, world, p):
        x0 = math.floor(p[0] - self.HW)
        x1 = math.floor(p[0] + self.HW - 1e-7)
        y0 = math.floor(p[1])
        y1 = math.floor(p[1] + self.HEIGHT - 1e-7)
        z0 = math.floor(p[2] - self.HW)
        z1 = math.floor(p[2] + self.HW - 1e-7)
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    b = world.get(x, y, z)
                    if b is None or E.SOLID[b]:
                        return True
        return False

    def move(self, world, dt, sneak):
        sp = float(np.max(np.abs(self.vel))) * dt
        steps = max(1, int(sp / 0.35) + 1)
        sdt = dt / steps
        was_ground = self.on_ground
        self.on_ground = False
        p = self.pos
        for _ in range(steps):
            for ax in (1, 0, 2):
                d = self.vel[ax] * sdt
                if d == 0.0:
                    continue
                old = p[ax]
                p[ax] += d
                if self.hits(world, p):
                    if ax == 1:
                        if d < 0:
                            p[1] = math.floor(p[1]) + 1.0
                            self.on_ground = True
                        else:
                            p[1] = math.floor(p[1] + self.HEIGHT) - self.HEIGHT - 1e-4
                    else:
                        if d > 0:
                            p[ax] = math.floor(p[ax] + self.HW) - self.HW - 1e-4
                        else:
                            p[ax] = math.floor(p[ax] - self.HW) + 1 + self.HW + 1e-4
                    if self.hits(world, p):
                        p[ax] = old
                    self.vel[ax] = 0.0
                elif ax != 1 and sneak and was_ground and not self.flying:
                    q = p.copy()
                    q[1] -= 0.6
                    if not self.hits(world, q):
                        p[ax] = old
                        self.vel[ax] = 0.0
        # ground probe (for standing still)
        if not self.on_ground and self.vel[1] <= 0:
            q = p.copy()
            q[1] -= 0.02
            if self.hits(world, q):
                self.on_ground = True


MOB_KINDS = {
    #        body colour            head colour           (w, h, l) body      leg h  head size
    "pig": ((0.94, 0.64, 0.64), (0.94, 0.64, 0.64), (0.62, 0.5, 0.9), 0.36, 0.5),
    "sheep": ((0.93, 0.93, 0.9), (0.78, 0.72, 0.66), (0.75, 0.62, 1.0), 0.5, 0.42),
    "cow": ((0.36, 0.25, 0.17), (0.36, 0.25, 0.17), (0.75, 0.62, 1.1), 0.6, 0.5),
}


FC = E.FACE_C.reshape(24, 3)
QI = np.array([0, 1, 2, 0, 2, 3])


class Mob(Player):
    HW = 0.4
    HEIGHT = 1.0

    def __init__(self, kind, pos):
        super().__init__(pos)
        self.kind = kind
        self.timer = 0.0
        self.speed = 0.0
        self.health = 4
        self.hurt = 0.0
        self.yaw = random.uniform(0, 2 * math.pi)
        self.attack_cd = 0.0
        if kind == "zombie":
            self.HW = 0.3
            self.HEIGHT = 1.9
            self.health = 6

    def update(self, world, dt, chase=None):
        self.timer -= dt
        self.attack_cd -= dt
        if chase is not None:
            d = chase - self.pos
            self.yaw = math.atan2(d[0], -d[2])
            self.speed = 2.3 if self.hurt <= 0 else 0.0
            self.timer = 1.0
        elif self.timer <= 0:
            self.timer = random.uniform(1.5, 5.0)
            if random.random() < 0.55:
                self.yaw = random.uniform(0, 2 * math.pi)
                self.speed = 1.3
            else:
                self.speed = 0.0
        self.hurt = max(0.0, self.hurt - dt)
        fx, fz = math.sin(self.yaw), -math.cos(self.yaw)
        rate = 8.0 if self.on_ground else 1.0
        self.vel[0] += (fx * self.speed - self.vel[0]) * min(1, rate * dt)
        self.vel[2] += (fz * self.speed - self.vel[2]) * min(1, rate * dt)
        feet = world.get(math.floor(self.pos[0]), math.floor(self.pos[1] + 0.3), math.floor(self.pos[2]))
        if feet == E.WATER:
            self.vel[1] = min(self.vel[1] + 20 * dt, 2.0)
        else:
            self.vel[1] = max(self.vel[1] - 32 * dt, -40)
        wanted = abs(self.vel[0]) + abs(self.vel[2])
        self.move(world, dt, False)
        if self.speed > 0 and self.on_ground and abs(self.vel[0]) + abs(self.vel[2]) < 0.5 * wanted:
            self.vel[1] = 8.5
        hs = math.hypot(self.vel[0], self.vel[2])
        self.walk += hs * dt * 1.5

    def ray_hit(self, o, d, maxd):
        lo = self.pos - (self.HW, 0, self.HW)
        hi = self.pos + (self.HW, self.HEIGHT + 0.2, self.HW)
        t0, t1 = 0.0, maxd
        for i in range(3):
            if abs(d[i]) < 1e-9:
                if o[i] < lo[i] or o[i] > hi[i]:
                    return None
                continue
            a = (lo[i] - o[i]) / d[i]
            b = (hi[i] - o[i]) / d[i]
            if a > b:
                a, b = b, a
            t0, t1 = max(t0, a), min(t1, b)
            if t0 > t1:
                return None
        return t0

    def tris(self, cam, br):
        if self.kind in ("zombie", "steve"):
            return self.zombie_tris(cam, br)
        bc, hc, (w, h, l), lh, hs = MOB_KINDS[self.kind]
        if self.hurt > 0:
            bc = hc = (1.0, 0.35, 0.35)
        cy, sy = math.cos(self.yaw), math.sin(self.yaw)
        # local -z is forward; world = R * local + pos
        R = np.array([[cy, 0, -sy], [0, 1, 0], [sy, 0, cy]])
        base = self.pos - cam
        swing = math.sin(self.walk * 3.0) * 0.6
        boxes = []

        def box(c, size, col, pivot=None, ang=0.0):
            pts = np.asarray(c, float) + (FC - 0.5) * np.asarray(size, float)   # (24,3)
            if pivot is not None:
                py, pz = pts[:, 1] - pivot[1], pts[:, 2] - pivot[2]
                ca, sa = math.cos(ang), math.sin(ang)
                pts = np.stack([pts[:, 0], pivot[1] + py * ca - pz * sa, pivot[2] + py * sa + pz * ca], 1)
            boxes.append((pts, col))

        legc = hc if self.kind != "cow" else (0.3, 0.22, 0.15)
        box((0, lh + h / 2, 0), (w, h, l), bc)
        hy = lh + h * 0.85
        hz = -l / 2 - hs * 0.35
        box((0, hy, hz), (hs, hs, hs), hc)
        for ex in (-hs * 0.25, hs * 0.25):
            box((ex, hy + hs * 0.1, hz - hs / 2 - 0.01), (0.08, 0.08, 0.02), (0.05, 0.05, 0.05))
        if self.kind == "pig":
            box((0, hy - hs * 0.15, hz - hs / 2 - 0.04), (0.24, 0.16, 0.08), (0.88, 0.5, 0.52))
        if self.kind == "cow":
            box((0, lh + h / 2 + 0.01, l * 0.15), (w + 0.02, h * 0.6, l * 0.3), (0.95, 0.95, 0.92))
            for hx in (-hs * 0.45, hs * 0.45):
                box((hx, hy + hs * 0.55, hz), (0.08, 0.14, 0.08), (0.85, 0.85, 0.8))
        for i, (lx, lz) in enumerate(((-w / 2 + 0.13, -l / 2 + 0.15), (w / 2 - 0.13, -l / 2 + 0.15),
                                      (-w / 2 + 0.13, l / 2 - 0.15), (w / 2 - 0.13, l / 2 - 0.15))):
            a = swing if i in (0, 3) else -swing
            box((lx, lh / 2, lz), (0.22, lh, 0.22), legc, pivot=(lx, lh, lz), ang=a)
        n = len(boxes)
        pts = np.concatenate([bx[0] for bx in boxes]) @ R.T + base          # (n*24,3)
        pts = pts.reshape(n, 6, 4, 3)[:, :, QI, :].reshape(-1, 3)          # (n*36,3)
        cols = np.array([bx[1] for bx in boxes])                            # (n,3)
        shade = np.repeat(E.FACE_SHADE, 6) * br                              # (36,)
        out = np.zeros((n, 36, 9), np.float32)
        out[:, :, :3] = pts.reshape(n, 36, 3)
        out[:, :, 5:8] = cols[:, None, :] * shade[None, :, None]
        out[:, :, 8] = 1.0
        return out.reshape(-1, 9)


def _zombie_tris(self, cam, br):
    skin, shirt, pants = (0.33, 0.58, 0.3), (0.12, 0.55, 0.62), (0.26, 0.2, 0.55)
    steve = self.kind == "steve"
    if steve:
        skin, shirt, pants = (0.85, 0.65, 0.5), (0.0, 0.65, 0.7), (0.25, 0.25, 0.6)
    if self.hurt > 0:
        skin = shirt = pants = (1.0, 0.35, 0.35)
    cy, sy = math.cos(self.yaw), math.sin(self.yaw)
    R = np.array([[cy, 0, -sy], [0, 1, 0], [sy, 0, cy]])
    base = self.pos - cam
    swing = math.sin(self.walk * 3.0) * 0.7
    boxes = []

    def box(c, size, col, pivot=None, ang=0.0):
        pts = np.asarray(c, float) + (FC - 0.5) * np.asarray(size, float)
        if pivot is not None:
            py, pz = pts[:, 1] - pivot[1], pts[:, 2] - pivot[2]
            ca, sa = math.cos(ang), math.sin(ang)
            pts = np.stack([pts[:, 0], pivot[1] + py * ca - pz * sa, pivot[2] + py * sa + pz * ca], 1)
        boxes.append((pts, col))

    for i, lx in enumerate((-0.125, 0.125)):
        box((lx, 0.375, 0), (0.25, 0.75, 0.25), pants, pivot=(lx, 0.75, 0), ang=swing if i == 0 else -swing)
    box((0, 1.125, 0), (0.5, 0.75, 0.25), shirt)
    box((0, 1.75, 0), (0.5, 0.5, 0.5), skin)
    for ex in (-0.12, 0.12):
        box((ex, 1.8, -0.255), (0.1, 0.07, 0.02), (0.05, 0.05, 0.05) if not steve else (0.3, 0.2, 0.6))
    if steve:
        box((0, 1.98, 0.02), (0.52, 0.06, 0.52), (0.3, 0.2, 0.1))
        box((0, 1.75, 0.2), (0.52, 0.5, 0.12), (0.3, 0.2, 0.1))
    for i, ax in enumerate((-0.375, 0.375)):
        a = math.pi / 2 + (swing * 0.15 if i == 0 else -swing * 0.15)
        if steve:
            a = -swing if i == 0 else swing
        box((ax, 1.5 - 0.375, 0), (0.25, 0.75, 0.25), skin, pivot=(ax, 1.4, 0), ang=a)
    n = len(boxes)
    pts = np.concatenate([bx[0] for bx in boxes]) @ R.T + base
    pts = pts.reshape(n, 6, 4, 3)[:, :, QI, :].reshape(-1, 3)
    cols = np.array([bx[1] for bx in boxes])
    shade = np.repeat(E.FACE_SHADE, 6) * br
    out = np.zeros((n, 36, 9), np.float32)
    out[:, :, :3] = pts.reshape(n, 36, 3)
    out[:, :, 5:8] = cols[:, None, :] * shade[None, :, None]
    out[:, :, 8] = 1.0
    return out.reshape(-1, 9)


Mob.zombie_tris = _zombie_tris


def raycast(world, origin, d, maxd=6.0):
    x, y, z = (math.floor(origin[0]), math.floor(origin[1]), math.floor(origin[2]))
    step = [1 if d[i] > 0 else -1 for i in range(3)]
    tmax = []
    tdelta = []
    cell = [x, y, z]
    for i in range(3):
        if abs(d[i]) < 1e-9:
            tmax.append(float("inf"))
            tdelta.append(float("inf"))
        else:
            nb = cell[i] + (1 if d[i] > 0 else 0)
            tmax.append((nb - origin[i]) / d[i])
            tdelta.append(abs(1.0 / d[i]))
    prev = None
    t = 0.0
    while t <= maxd:
        b = world.get(cell[0], cell[1], cell[2])
        if b is not None and b != E.AIR and b != E.WATER and b != E.LAVA:
            return tuple(cell), prev
        prev = tuple(cell)
        ax = 0 if tmax[0] < tmax[1] and tmax[0] < tmax[2] else (1 if tmax[1] < tmax[2] else 2)
        t = tmax[ax]
        cell[ax] += step[ax]
        tmax[ax] += tdelta[ax]
    return None, None


# ---------------------------------------------------------------------------
# GUI batching

WHITE_UV = (15.5 / 16, 15.5 / 16)


class Gui:
    def __init__(self, ctx, prog):
        self.ctx = ctx
        self.prog = prog
        self.buf = ctx.buffer(reserve=1 << 20, dynamic=True)
        self.vao = ctx.vertex_array(prog, [(self.buf, "2f 2f 4f", "in_pos", "in_uv", "in_color")])
        self.v = []
        self.fonts = {}
        self.text_cache = {}

    def tri(self, pts, uvs, col):
        for (x, y), (u, v) in zip(pts, uvs):
            self.v.extend((x, y, u, v, *col))

    def quad(self, x, y, w, h, uv0=WHITE_UV, uv1=WHITE_UV, col=(1, 1, 1, 1)):
        p = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
        u = [(uv0[0], uv0[1]), (uv1[0], uv0[1]), (uv1[0], uv1[1]), (uv0[0], uv1[1])]
        self.tri([p[0], p[1], p[2], p[0], p[2], p[3]], [u[0], u[1], u[2], u[0], u[2], u[3]], col)

    def rect(self, x, y, w, h, col):
        self.quad(x, y, w, h, col=col)

    def frame(self, x, y, w, h, t, col):
        self.rect(x, y, w, t, col)
        self.rect(x, y + h - t, w, t, col)
        self.rect(x, y, t, h, col)
        self.rect(x + w - t, y, t, h, col)

    def tile_uv(self, t):
        r, c = divmod(int(t), 16)
        return (c / 16, r / 16), ((c + 1) / 16, (r + 1) / 16)

    def poly(self, pts, t, col):
        (u0, v0), (u1, v1) = self.tile_uv(t)
        uv = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        self.tri([pts[0], pts[1], pts[2], pts[0], pts[2], pts[3]], [uv[0], uv[1], uv[2], uv[0], uv[2], uv[3]], col)

    def icon(self, b, cx, cy, s, bright=1.0):
        if E.KIND[b] in (E.K_CROSS, E.K_TORCH, E.K_WATER):
            uv0, uv1 = self.tile_uv(E.TEX[b, 0])
            self.quad(cx - s * 0.45, cy - s * 0.45, s * 0.9, s * 0.9, uv0, uv1, (bright, bright, bright, 1))
            return
        w = s * 0.43
        top = [(cx, cy - s * 0.48), (cx + w, cy - s * 0.24), (cx, cy), (cx - w, cy - s * 0.24)]
        left = [(cx - w, cy - s * 0.24), (cx, cy), (cx, cy + s * 0.48), (cx - w, cy + s * 0.24)]
        right = [(cx, cy), (cx + w, cy - s * 0.24), (cx + w, cy + s * 0.24), (cx, cy + s * 0.48)]
        f = bright
        self.poly(top, E.TEX[b, 2], (f, f, f, 1))
        self.poly(left, E.TEX[b, 4], (0.8 * f, 0.8 * f, 0.8 * f, 1))
        self.poly(right, E.TEX[b, 0], (0.6 * f, 0.6 * f, 0.6 * f, 1))

    def flush(self, tex):
        if not self.v:
            return
        data = np.array(self.v, "f4").tobytes()
        if len(data) > self.buf.size:
            self.buf.orphan(len(data) * 2)
        self.buf.write(data)
        tex.use(0)
        self.vao.render(moderngl.TRIANGLES, vertices=len(self.v) // 8)
        self.v = []

    def text(self, s, x, y, size=20, col=(255, 255, 255), shadow=True, center=False, alpha=1.0):
        key = (s, size, col)
        ent = self.text_cache.get(key)
        if ent is None:
            if len(self.text_cache) > 400:
                for e in self.text_cache.values():
                    e[0].release()
                self.text_cache.clear()
            font = self.fonts.get(size)
            if font is None:
                font = self.fonts[size] = pygame.font.Font(None, size)
            surf = font.render(s, True, col)
            sh = font.render(s, True, (40, 40, 40))
            w, h = surf.get_size()
            full = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
            if shadow:
                full.blit(sh, (2, 2))
            full.blit(surf, (0, 0))
            tex = self.ctx.texture(full.get_size(), 4, pygame.image.tobytes(full, "RGBA", False))
            tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
            ent = (tex, w + 2, h + 2)
            self.text_cache[key] = ent
        tex, w, h = ent
        if center:
            x -= w / 2
        saved = self.v
        self.v = []
        self.quad(x, y, w, h, (0, 0), (1, 1), (1, 1, 1, alpha))
        self.flush(tex)
        self.v = saved
        return w, h


# ---------------------------------------------------------------------------
# game

HOTBAR_DEFAULT = [E.GRASS, E.DIRT, E.COBBLE, E.PLANKS, E.LOG, E.GLASS, E.BRICKS, E.TORCH, E.TNT]
INVENTORY = [b for b in range(1, E.NB) if b != E.WATER]
FALLING = (E.SAND, E.GRAVEL)
REPLACEABLE = (E.AIR, E.WATER, E.TALLGRASS, E.LAVA)
_N = E.BLOCK_NAMES.index
RECIPES = [  # (output, count, [(ingredient, count), ...])
    (E.PLANKS, 4, [(E.LOG, 1)]),
    (E.PLANKS, 4, [(E.BIRCHLOG, 1)]),
    (_N("Spruce Planks"), 4, [(E.SPRUCELOG, 1)]),
    (E.TORCH, 4, [(E.COAL, 1), (E.PLANKS, 1)]),
    (E.GLASS, 1, [(E.SAND, 1)]),
    (E.STONE, 1, [(E.COBBLE, 1)]),
    (_N("Stone Bricks"), 4, [(E.STONE, 4)]),
    (E.SANDSTONE, 1, [(E.SAND, 4)]),
    (E.BRICKS, 1, [(E.DIRT, 2), (E.GRAVEL, 2)]),
    (_N("Bookshelf"), 1, [(E.PLANKS, 6)]),
    (_N("Jack o'Lantern"), 1, [(E.PUMPKIN, 1), (E.TORCH, 1)]),
    (E.GLOWSTONE, 1, [(E.GOLD, 1), (E.TORCH, 1)]),
    (E.TNT, 1, [(E.SAND, 4), (E.GRAVEL, 4)]),
    (_N("White Wool"), 1, [(E.TALLGRASS, 4)]),
]
HARD = np.ones(64)
for _b in range(E.NB):
    _k = E.BLOCK_SOUND[_b]
    HARD[_b] = {"grass": 0.6, "sand": 0.6, "wood": 1.3, "stone": 1.6, "glass": 0.4, "wool": 0.8}.get(_k, 1.0)
    if E.KIND[_b] in (E.K_CROSS, E.K_TORCH):
        HARD[_b] = 0.05
for _b, _h in ((E.LEAVES, 0.25), (E.BIRCHLEAVES, 0.25), (E.SPRUCELEAVES, 0.25), (E.OBSIDIAN_ID, 6.0),
               (E.BEDROCK, 1e9), (E.COAL, 2.2), (E.IRON, 2.4), (E.GOLD, 2.4), (E.DIAMOND, 2.8), (E.TNT, 0.05)):
    HARD[_b] = _h
DROP = {E.GRASS: E.DIRT, E.SNOWGRASS: E.DIRT, E.STONE: E.COBBLE, E.LEAVES: None, E.BIRCHLEAVES: None,
        E.SPRUCELEAVES: None, E.GLASS: None, E.BEDROCK: None, E.LAVA: None, E.WATER: None}


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("StelexCraft")
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
        pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
        try:
            dw, dh = pygame.display.get_desktop_sizes()[0]
        except Exception:
            dw, dh = 1600, 900
        w, h = int(dw * 0.8), int(dh * 0.8)
        flags = pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE
        pygame.display.set_mode((w, h), flags, vsync=0)
        self.ctx = moderngl.create_context()
        self.size = pygame.display.get_window_size()
        ctx = self.ctx
        self.chunk_prog = ctx.program(vertex_shader=CHUNK_VS, fragment_shader=CHUNK_FS)
        self.simple_prog = ctx.program(vertex_shader=SIMPLE_VS, fragment_shader=SIMPLE_FS)
        self.gui_prog = ctx.program(vertex_shader=GUI_VS, fragment_shader=GUI_FS)
        atlas = textures.build_atlas()
        self.atlas = ctx.texture((256, 256), 4, atlas.tobytes())
        self.atlas.build_mipmaps(0, 4)
        self.atlas.filter = (moderngl.NEAREST_MIPMAP_LINEAR, moderngl.NEAREST)
        self.clouds = ctx.texture((64, 64), 4, textures.cloud_texture().tobytes())
        self.clouds.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self.clouds.repeat_x = self.clouds.repeat_y = True
        self.gui = Gui(ctx, self.gui_prog)
        yy, xx = np.mgrid[0:128, 0:128]
        d = np.sqrt(((xx - 63.5) / 63.5) ** 2 + ((yy - 63.5) / 63.5) ** 2)
        vig = np.zeros((128, 128, 4), np.uint8)
        vig[..., 3] = (np.clip((d - 0.55) / 0.9, 0, 1) ** 1.6 * 150).astype(np.uint8)
        self.vignette = ctx.texture((128, 128), 4, vig.tobytes())
        self.vignette.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.sbuf = ctx.buffer(reserve=1 << 20, dynamic=True)
        self.svao = ctx.vertex_array(self.simple_prog, [(self.sbuf, "3f 2f 4f", "in_pos", "in_uv", "in_color")])
        self.sounds = Sounds()
        sr = np.random.RandomState(9)
        st = sr.normal(size=(700, 3))
        self.stars = st / np.linalg.norm(st, axis=1)[:, None]
        self.star_sz = sr.uniform(0.5, 1.4, 700)

        data = None
        if os.path.exists(SAVE_PATH):
            try:
                with open(SAVE_PATH, "rb") as f:
                    data = pickle.load(f)
            except Exception:
                data = None
        if data:
            seed = data["seed"]
            edits = data["edits"]
        else:
            seed = random.randint(1, 10 ** 9)
            edits = {}
        self.world = World(ctx, self.chunk_prog, seed, edits)
        self.player = Player((0.5, 100, 0.5))
        self.tod = 0.03
        self.hotbar = list(HOTBAR_DEFAULT)
        self.sel = 0
        if data:
            self.player.pos[:] = data["pos"]
            self.player.yaw = data["yaw"]
            self.player.pitch = data["pitch"]
            self.player.flying = data.get("flying", False)
            self.tod = data.get("tod", 0.03)
            self.hotbar = data.get("hotbar", self.hotbar)
            self.survival = data.get("survival", False)
            self.counts = data.get("counts", {})
            self.health = data.get("health", 20) or 20
            self.spawn_pos = data.get("spawn_pos", tuple(self.player.pos))
            self.spawned = True
        else:
            sx, sz = self.find_spawn()
            self.player.pos[:] = (sx, 100, sz)
            self.spawned = False
        if not data:
            self.survival = False
            self.counts = {}
            self.health = 20
            self.spawn_pos = None
        self.air = 10.0
        self.hurt_t = 0.0
        self.dmg_cd = 0.0
        self.regen = 0.0
        self.dead = False
        self.fall_y = None
        self.mine_pos = None
        self.mine_prog = 0.0
        self.mine_snd = 0.0
        self.msg = "Survival" if self.survival else "Creative mode - press G for Survival"
        self.msg_t = 5.0
        self.swing = 0.0
        self.rain = 0.0
        self.raining = False
        self.weather_t = random.uniform(90, 180)
        self.rpos = np.zeros((900, 3))
        self.rkill = np.full(900, 1e9)
        self.rsnow = np.zeros(900, bool)
        self.rain_ch = None
        self.t = 0.0
        self.paused = False
        self.inventory = False
        self.show_debug = False
        self.third = False
        self.sens = 0.0025
        self.hide_hud = False
        self.last_space = -1.0
        self.break_cd = 0.0
        self.place_cd = 0.0
        self.name_timer = 0.0
        self.particles = []
        self.mobs = []
        self.drops = []
        self.mob_timer = 0.0
        self.mob_target = None
        self.tnt = {}
        self.fps = 0.0
        self.fov = 70.0
        self.target = None
        self.mouse_grab(True)
        self.last_save = time.time()

    # -- helpers
    def mouse_grab(self, on):
        pygame.event.set_grab(on)
        pygame.mouse.set_visible(not on)
        if on:
            pygame.mouse.get_rel()

    def new_world(self):
        old = self.world
        for k in list(old.meshes):
            old.release(k)
        old.pool.shutdown(wait=False, cancel_futures=True)
        old.ibo.release()
        self.world = World(self.ctx, self.chunk_prog, random.randint(1, 10 ** 9), {})
        sx, sz = self.find_spawn()
        self.player = Player((sx, 100, sz))
        self.spawned = False
        self.mobs = []
        self.drops = []
        self.tnt = {}
        self.particles = []
        self.counts = {}
        self.health = 20
        self.dead = False
        self.tod = 0.03
        self.paused = False
        self.inventory = False
        self.mouse_grab(True)
        self.msg = "New world generated"
        self.msg_t = 2.5

    def find_spawn(self):
        perm = self.world.perm
        for r in range(0, 4000, 24):
            for a in range(max(1, r // 12)):
                ang = a / max(1, r // 12) * 2 * math.pi
                x, z = int(math.cos(ang) * r), int(math.sin(ang) * r)
                h = E.terrain_height(perm, x, z)
                if E.SEA + 3 < h < 85 and E.temperature(perm, x, z) < 0.17:
                    return x + 0.5, z + 0.5
        return 0.5, 0.5

    def save(self):
        p = self.player
        data = {"seed": self.world.seed, "edits": self.world.edits, "pos": tuple(p.pos), "yaw": p.yaw,
                "pitch": p.pitch, "flying": p.flying, "tod": self.tod, "hotbar": self.hotbar,
                "survival": self.survival, "counts": self.counts, "health": self.health, "spawn_pos": self.spawn_pos}
        tmp = SAVE_PATH + ".tmp"
        with open(tmp, "wb") as f:
            pickle.dump(data, f)
        os.replace(tmp, SAVE_PATH)
        self.last_save = time.time()

    def sdraw(self, verts, mode, tex=None, fog=False):
        if len(verts) == 0:
            return
        data = np.asarray(verts, "f4").tobytes()
        if len(data) > self.sbuf.size:
            self.sbuf.orphan(len(data) * 2)
        self.sbuf.write(data)
        sp = self.simple_prog
        sp["u_use_tex"].value = 1 if tex is not None else 0
        sp["u_fog"].value = 1 if fog else 0
        if tex is not None:
            tex.use(0)
        self.svao.render(mode, vertices=len(data) // 36)

    # -- world interaction
    def spawn_particles(self, x, y, z, b, n=14):
        t = E.TEX[b, 0]
        r, c = divmod(int(t), 16)
        for _ in range(n):
            pu = (c + random.randint(0, 12) / 16) / 16
            pv = (r + random.randint(0, 12) / 16) / 16
            self.particles.append([np.array([x + random.random(), y + random.random(), z + random.random()]),
                                   np.array([random.uniform(-2, 2), random.uniform(1, 4), random.uniform(-2, 2)]),
                                   random.uniform(0.5, 1.1), pu, pv])

    def drop_column(self, x, y, z, touched):
        """Let sand/gravel at or above y fall down."""
        w = self.world
        yy = y
        while yy < H:
            b = w.get(x, yy, z)
            if b not in FALLING:
                break
            ly = yy
            while ly - 1 >= 0 and w.get(x, ly - 1, z) in REPLACEABLE + (E.DANDELION, E.POPPY):
                ly -= 1
            if ly != yy:
                touched |= w.set(x, yy, z, E.AIR, sync=False)
                touched |= w.set(x, ly, z, b, sync=False)
            yy += 1

    def break_block(self, pos):
        w = self.world
        x, y, z = pos
        b = w.get(x, y, z)
        if b is None or b == E.AIR:
            return
        fill = E.AIR
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0)):
            if w.get(x + dx, y + dy, z + dz) == E.WATER:
                fill = E.WATER
        touched = w.set(x, y, z, fill, sync=False)
        above = w.get(x, y + 1, z)
        if b in (E.SUGARCANE, E.CACTUS):
            yy = y + 1
            while w.get(x, yy, z) == b:
                touched |= w.set(x, yy, z, E.AIR, sync=False)
                if self.survival:
                    self.drops.append([np.array([x + 0.5, yy + 0.3, z + 0.5]), np.array([0.0, 2.0, 0.0]), b, 0.0])
                yy += 1
        elif above is not None and E.KIND[above] in (E.K_CROSS, E.K_TORCH):
            touched |= w.set(x, y + 1, z, E.AIR, sync=False)
        self.drop_column(x, y + 1, z, touched)
        w.remesh(touched, {(x >> 4, z >> 4)} | self.border_keys(x, z))
        self.spawn_particles(x, y, z, b)
        self.sounds.block("break", b)
        if self.survival:
            d = DROP.get(b, b)
            if d:
                self.drops.append([np.array([x + 0.5, y + 0.3, z + 0.5]),
                                   np.array([random.uniform(-1, 1), 3.0, random.uniform(-1, 1)]), d, 0.0])

    def border_keys(self, x, z):
        k = set()
        lx, lz = x & 15, z & 15
        cx, cz = x >> 4, z >> 4
        if lx == 0:
            k.add((cx - 1, cz))
        if lx == 15:
            k.add((cx + 1, cz))
        if lz == 0:
            k.add((cx, cz - 1))
        if lz == 15:
            k.add((cx, cz + 1))
        return k

    def place_block(self, hit, prev):
        w = self.world
        b = self.hotbar[self.sel]
        tb = w.get(*hit)
        if tb == E.TNT:
            self.ignite(hit)
            return
        if tb in (E.TALLGRASS,):
            prev = hit
        if prev is None:
            return
        if self.survival and self.counts.get(b, 0) <= 0:
            return
        x, y, z = prev
        cur = w.get(x, y, z)
        if cur is None or cur not in REPLACEABLE or not 0 <= y < H:
            return
        if E.SOLID[b]:
            p = self.player
            if (x < p.pos[0] + p.HW and x + 1 > p.pos[0] - p.HW and z < p.pos[2] + p.HW and z + 1 > p.pos[2] - p.HW
                    and y < p.pos[1] + p.HEIGHT and y + 1 > p.pos[1]):
                return
        if E.KIND[b] in (E.K_CROSS,) and w.get(x, y - 1, z) not in (E.GRASS, E.DIRT, E.SNOWGRASS, E.SAND):
            return
        touched = w.set(x, y, z, b, sync=False)
        if self.survival:
            self.counts[b] -= 1
        if b in FALLING:
            self.drop_column(x, y, z, touched)
        w.remesh(touched, {(x >> 4, z >> 4)} | self.border_keys(x, z))
        self.sounds.block("place", b)

    def ignite(self, pos):
        if pos not in self.tnt:
            self.tnt[pos] = 3.0
            self.sounds.play("fuse", 0.8)

    def explode(self, pos):
        w = self.world
        cx, cy, cz = pos
        R = 4
        touched = set()
        touched |= w.set(cx, cy, cz, E.AIR, sync=False)
        for dx in range(-R, R + 1):
            for dy in range(-R, R + 1):
                for dz in range(-R, R + 1):
                    d2 = dx * dx + dy * dy + dz * dz
                    if d2 > (R - random.random() * 1.2) ** 2:
                        continue
                    x, y, z = cx + dx, cy + dy, cz + dz
                    b = w.get(x, y, z)
                    if b is None or b in (E.AIR, E.BEDROCK, E.WATER, E.OBSIDIAN_ID):
                        continue
                    if b == E.TNT:
                        if (x, y, z) not in self.tnt:
                            self.tnt[(x, y, z)] = random.uniform(0.4, 1.2)
                        continue
                    touched |= w.set(x, y, z, E.AIR, sync=False)
                    if random.random() < 0.08:
                        self.spawn_particles(x, y, z, b, 3)
        now = set()
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                now.add(((cx >> 4) + dx, (cz >> 4) + dz))
        w.remesh(touched, now)
        p = self.player
        c = np.array([cx + 0.5, cy + 0.5, cz + 0.5])
        d = (p.pos + (0, 0.9, 0)) - c
        dist = float(np.linalg.norm(d))
        if dist < 8:
            p.vel += d / max(dist, 0.5) * (8 - dist) * 3.0
            p.flying = False
            self.damage(int((8 - dist) * 2.5))
        for m in list(self.mobs):
            md = float(np.linalg.norm(m.pos - c))
            if md < 5:
                m.health = 1
                self.hit_mob(m)
            elif md < 8:
                m.vel += (m.pos - c) / md * (8 - md) * 2.5
        self.sounds.play("explode", max(0.15, 1.0 - dist / 60))
        self.shake = 0.6

    # -- per-frame
    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return False
            if ev.type == pygame.MOUSEBUTTONDOWN and self.dead:
                if self.respawn_hover():
                    self.respawn()
                continue
            if ev.type == pygame.KEYDOWN:
                k = ev.key
                if self.dead:
                    continue
                if k == pygame.K_ESCAPE:
                    if self.inventory:
                        self.inventory = False
                        self.mouse_grab(True)
                    else:
                        self.paused = not self.paused
                        self.mouse_grab(not self.paused)
                elif self.paused:
                    if k == pygame.K_q:
                        return False
                elif k == pygame.K_e:
                    self.inventory = not self.inventory
                    self.mouse_grab(not self.inventory)
                elif pygame.K_1 <= k <= pygame.K_9:
                    if self.inventory:
                        hov = self.inv_hover()
                        if hov is not None:
                            self.hotbar[k - pygame.K_1] = hov
                    else:
                        self.sel = k - pygame.K_1
                        self.name_timer = 2.0
                elif k == pygame.K_w:
                    if self.t - getattr(self, "last_w", -1.0) < 0.3:
                        self.player.sprint = True
                    self.last_w = self.t
                elif k == pygame.K_F3:
                    self.show_debug = not self.show_debug
                elif k == pygame.K_g:
                    self.survival = not self.survival
                    self.player.flying = False
                    self.health = 20
                    self.fall_y = None
                    self.msg = "Survival Mode" if self.survival else "Creative Mode"
                    self.msg_t = 2.5
                elif k in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
                    self.sens *= 0.8 if k == pygame.K_LEFTBRACKET else 1.25
                    self.sens = max(0.0005, min(0.012, self.sens))
                    self.msg = f"Mouse sensitivity {self.sens / 0.0025 * 100:.0f}%"
                    self.msg_t = 1.5
                elif k == pygame.K_F2:
                    self.want_shot = True
                elif k == pygame.K_F7:
                    self.raining = not self.raining
                    self.weather_t = random.uniform(60, 160) if self.raining else random.uniform(180, 420)
                elif k == pygame.K_F5:
                    self.third = not self.third
                elif k == pygame.K_F11:
                    try:
                        pygame.display.toggle_fullscreen()
                    except Exception:
                        pass
                elif k == pygame.K_F1:
                    self.hide_hud = not self.hide_hud
                elif k == pygame.K_SPACE:
                    if self.t - self.last_space < 0.3 and not self.survival:
                        self.player.flying = not self.player.flying
                        self.player.vel[1] = 0
                        self.last_space = -1
                    else:
                        self.last_space = self.t
                elif k in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS) and self.world.center:
                    self.world.radius = min(16, self.world.radius + 1)
                    self.world.set_center(self.world.center)
                elif k in (pygame.K_MINUS, pygame.K_KP_MINUS) and self.world.center:
                    self.world.radius = max(3, self.world.radius - 1)
                    self.world.set_center(self.world.center)
            elif ev.type == pygame.MOUSEMOTION and not self.paused and not self.inventory:
                dx, dy = ev.rel
                p = self.player
                p.yaw += dx * self.sens
                p.pitch = max(-1.5607, min(1.5607, p.pitch - dy * self.sens))
            elif ev.type == pygame.MOUSEWHEEL and not self.paused and not self.inventory:
                self.sel = (self.sel - ev.y) % 9
                self.name_timer = 2.0
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                if self.paused:
                    act = self.pause_hover()
                    if act == 0:
                        self.paused = False
                        self.mouse_grab(True)
                    elif act == 1:
                        return False
                    elif act == 2:
                        self.new_world()
                elif self.inventory:
                    rh = self.recipe_hover()
                    if ev.button == 1 and rh is not None:
                        self.craft(rh)
                    elif ev.button == 1:
                        hov = self.inv_hover()
                        if hov is not None:
                            self.hotbar[self.sel] = hov
                            self.name_timer = 2.0
                            self.inventory = False
                            self.mouse_grab(True)
                else:
                    self.swing = 1.0
                    if ev.button == 1 and self.mob_target is not None:
                        self.hit_mob(self.mob_target)
                        self.break_cd = 0.5
                    elif ev.button == 1 and self.target and not self.survival:
                        self.break_block(self.target[0])
                        self.break_cd = 0.3
                    elif ev.button == 3 and self.target:
                        self.place_block(*self.target)
                        self.place_cd = 0.3
                    elif ev.button == 2 and self.target and not self.survival:
                        b = self.world.get(*self.target[0])
                        if b:
                            if b in self.hotbar:
                                self.sel = self.hotbar.index(b)
                            else:
                                self.hotbar[self.sel] = b
                            self.name_timer = 2.0
            elif ev.type in (pygame.WINDOWFOCUSLOST,) and not self.paused:
                self.paused = True
                self.inventory = False
                self.mouse_grab(False)
        return True

    def inv_items(self):
        if not self.survival:
            return INVENTORY
        return sorted(b for b, c in self.counts.items() if c > 0)

    def give(self, b):
        self.counts[b] = self.counts.get(b, 0) + 1
        if b not in self.hotbar:
            for i, hb in enumerate(self.hotbar):
                if self.counts.get(hb, 0) <= 0:
                    self.hotbar[i] = b
                    break

    def damage(self, n):
        if not self.survival or self.dead or n <= 0:
            return
        self.health -= n
        self.hurt_t = 0.45
        self.sounds.play("hurt")
        if self.health <= 0:
            self.health = 0
            self.dead = True
            self.counts = {}
            self.inventory = False
            self.mouse_grab(False)

    def respawn_rect(self):
        W, Hh = self.size
        return (W / 2 - 200, Hh / 2 + 10, 400, 48)

    def respawn_hover(self):
        x, y, w, h = self.respawn_rect()
        mx, my = pygame.mouse.get_pos()
        return x <= mx <= x + w and y <= my <= y + h

    def respawn(self):
        p = self.player
        if self.spawn_pos:
            p.pos[:] = self.spawn_pos
        p.vel[:] = 0
        self.health = 20
        self.air = 10.0
        self.dead = False
        self.paused = False
        self.inventory = False
        self.fall_y = None
        self.mouse_grab(True)

    def survival_tick(self, dt, prev_ground, in_water):
        p = self.player
        w = self.world
        self.dmg_cd -= dt
        if p.on_ground or in_water or p.flying:
            if p.on_ground and not prev_ground and self.fall_y is not None and not in_water:
                dist = self.fall_y - p.pos[1]
                if dist > 3.5:
                    self.damage(int(dist - 3))
            self.fall_y = None
        elif p.vel[1] < 0 and self.fall_y is None:
            self.fall_y = p.pos[1]
        eye = p.eye(False)
        head = w.get(math.floor(eye[0]), math.floor(eye[1]), math.floor(eye[2]))
        if head == E.WATER:
            self.air -= dt
            if self.air < 0:
                self.air = 0
                if self.dmg_cd <= 0:
                    self.damage(2)
                    self.dmg_cd = 1.0
        else:
            self.air = min(10.0, self.air + dt * 4)
        feet = w.get(math.floor(p.pos[0]), math.floor(p.pos[1] + 0.3), math.floor(p.pos[2]))
        if (feet == E.LAVA or head == E.LAVA) and self.dmg_cd <= 0:
            self.damage(4)
            self.dmg_cd = 0.5
        if self.dmg_cd <= 0:
            cact = False
            for cx in (math.floor(p.pos[0] - 0.36), math.floor(p.pos[0] + 0.36)):
                for cz in (math.floor(p.pos[2] - 0.36), math.floor(p.pos[2] + 0.36)):
                    for cy in (math.floor(p.pos[1] - 0.05), math.floor(p.pos[1] + 0.9)):
                        if w.get(cx, cy, cz) == E.CACTUS:
                            cact = True
            if cact:
                self.damage(1)
                self.dmg_cd = 0.5
        if self.health < 20 and not self.dead:
            self.regen += dt
            if self.regen > 3.0:
                self.regen = 0
                self.health += 1

    def inv_layout(self):
        W, Hh = self.size
        s = max(40, min(64, int(Hh / 12)))
        cols = 9
        rows = max(1, (len(self.inv_items()) + cols - 1) // cols)
        pw, ph = cols * s + 40, rows * s + 90
        x0, y0 = (W - pw) / 2, (Hh - ph) / 2 - s
        if self.survival:
            x0 = max(10, (W - pw - 400) / 2)
            y0 = max(10, (Hh - 56 - len(RECIPES) * 40) / 2 - 20)
        return s, cols, x0, y0, pw, ph

    def recipe_rects(self):
        s, cols, x0, y0, pw, ph = self.inv_layout()
        rx = x0 + pw + 14
        rh = 40
        return [(rx, y0 + 50 + i * rh, 380, rh - 4, r) for i, r in enumerate(RECIPES)]

    def recipe_hover(self):
        if not self.survival:
            return None
        mx, my = pygame.mouse.get_pos()
        for x, y, w, h, r in self.recipe_rects():
            if x <= mx <= x + w and y <= my <= y + h:
                return r
        return None

    def can_craft(self, r):
        return all(self.counts.get(b, 0) >= n for b, n in r[2])

    def craft(self, r):
        if not self.can_craft(r):
            return
        for b, n in r[2]:
            self.counts[b] -= n
        for _ in range(r[1]):
            self.give(r[0])
        self.sounds.play("pickup", 0.6)

    def inv_hover(self):
        s, cols, x0, y0, pw, ph = self.inv_layout()
        mx, my = pygame.mouse.get_pos()
        i = int((mx - x0 - 20) // s)
        j = int((my - y0 - 60) // s)
        if 0 <= i < cols and j >= 0 and mx >= x0 + 20 and my >= y0 + 60:
            n = j * cols + i
            items = self.inv_items()
            if n < len(items):
                return items[n]
        return None

    def pause_buttons(self):
        W, Hh = self.size
        bw, bh = 400, 48
        return [(W / 2 - bw / 2, Hh / 2 - 40, bw, bh, "Back to Game"),
                (W / 2 - bw / 2, Hh / 2 + 24, bw, bh, "Save and Quit"),
                (W / 2 - bw / 2, Hh / 2 + 88, bw, bh, "New World (replaces this one)")]

    def pause_hover(self):
        mx, my = pygame.mouse.get_pos()
        for i, (x, y, w, h, _) in enumerate(self.pause_buttons()):
            if x <= mx <= x + w and y <= my <= y + h:
                return i
        return None

    def update_player(self, dt):
        p = self.player
        w = self.world
        keys = pygame.key.get_pressed()
        active = not self.paused and not self.inventory
        fwd = (keys[pygame.K_w] - keys[pygame.K_s]) if active else 0
        strafe = (keys[pygame.K_d] - keys[pygame.K_a]) if active else 0
        jump = keys[pygame.K_SPACE] and active
        sneak = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and active
        if active and (keys[pygame.K_LCTRL] or keys[pygame.K_r]) and fwd > 0:
            p.sprint = True
        if fwd <= 0 or sneak:
            p.sprint = False
        p.crouch += ((0.2 if sneak and not p.flying else 0.0) - p.crouch) * min(1, dt * 12)
        fx, fz = math.sin(p.yaw), -math.cos(p.yaw)
        rx, rz = math.cos(p.yaw), math.sin(p.yaw)
        wish = np.array([fx * fwd + rx * strafe, 0.0, fz * fwd + rz * strafe])
        n = np.linalg.norm(wish)
        if n > 0:
            wish /= n
        feet = w.get(math.floor(p.pos[0]), math.floor(p.pos[1] + 0.4), math.floor(p.pos[2]))
        in_water = feet == E.WATER or feet == E.LAVA
        if p.flying:
            speed = 21.6 if p.sprint else 10.9
            rate = 8.0
            p.vel[0] += (wish[0] * speed - p.vel[0]) * min(1, rate * dt)
            p.vel[2] += (wish[2] * speed - p.vel[2]) * min(1, rate * dt)
            vy = (jump - sneak) * 8.0
            p.vel[1] += (vy - p.vel[1]) * min(1, 10 * dt)
        elif in_water:
            speed = 3.0 if not p.sprint else 4.5
            p.vel[0] += (wish[0] * speed - p.vel[0]) * min(1, 6 * dt)
            p.vel[2] += (wish[2] * speed - p.vel[2]) * min(1, 6 * dt)
            p.vel[1] -= 10.0 * dt
            if jump:
                p.vel[1] = min(p.vel[1] + 28 * dt, 3.2)
            p.vel[1] = max(p.vel[1], -3.5)
        else:
            speed = 1.3 if sneak else (5.612 if p.sprint else 4.317)
            rate = 14.0 if p.on_ground else 2.5
            p.vel[0] += (wish[0] * speed - p.vel[0]) * min(1, rate * dt)
            p.vel[2] += (wish[2] * speed - p.vel[2]) * min(1, rate * dt)
            p.vel[1] = max(p.vel[1] - 32.0 * dt, -60.0)
            if jump and p.on_ground:
                p.vel[1] = 9.0
                if p.sprint:
                    p.vel[0] += wish[0] * 2.0
                    p.vel[2] += wish[2] * 2.0
        prev_ground = p.on_ground
        if in_water and not getattr(self, "was_in_water", True) and p.vel[1] < -4:
            self.sounds.play("splash", 0.8)
        self.was_in_water = in_water
        p.move(w, dt, sneak)
        if p.flying and p.on_ground and not jump:
            p.flying = False
        if p.on_ground and not prev_ground:
            b = w.get(math.floor(p.pos[0]), math.floor(p.pos[1] - 0.5), math.floor(p.pos[2]))
            if b:
                self.sounds.block("step", b)
        hspeed = math.hypot(p.vel[0], p.vel[2])
        if p.on_ground and hspeed > 0.5:
            p.walk += hspeed * dt / 1.6
            p.step_acc += hspeed * dt
            if p.step_acc > 1.9:
                p.step_acc = 0
                b = w.get(math.floor(p.pos[0]), math.floor(p.pos[1] - 0.5), math.floor(p.pos[2]))
                if b:
                    self.sounds.block("step", b)
        if self.survival:
            self.survival_tick(dt, prev_ground, in_water)
            if p.pos[1] < -30:
                self.damage(100)
        if p.pos[1] < -30:
            p.pos[1] = 120
            p.vel[:] = 0

    def update(self, dt):
        self.t += dt
        self.tod = (self.tod + dt / DAY_LENGTH) % 1.0
        p = self.player
        w = self.world
        w.update(p.pos[0], p.pos[2])
        if not self.spawned:
            x, z = math.floor(p.pos[0]), math.floor(p.pos[2])
            if all(((x + dx) >> 4, (z + dz) >> 4) in w.chunks for dx in (-6, 6) for dz in (-6, 6)):
                trees = (E.LEAVES, E.BIRCHLEAVES, E.SPRUCELEAVES, E.LOG, E.BIRCHLOG, E.SPRUCELOG, E.CACTUS)
                best = None
                for r in range(0, 6):
                    for dx in range(-r, r + 1):
                        for dz in range(-r, r + 1):
                            if best is not None or max(abs(dx), abs(dz)) != r:
                                continue
                            y = H - 1
                            while y > 0 and not E.SOLID[w.get(x + dx, y, z + dz)]:
                                y -= 1
                            if w.get(x + dx, y, z + dz) not in trees:
                                best = (x + dx, y, z + dz)
                if best is None:
                    y = H - 1
                    while y > 0 and not E.SOLID[w.get(x, y, z)]:
                        y -= 1
                    best = (x, y, z)
                p.pos[:] = (best[0] + 0.5, best[1] + 1, best[2] + 0.5)
                self.spawned = True
                self.spawn_pos = tuple(p.pos)
            else:
                return
        self.hurt_t = max(0.0, self.hurt_t - dt)
        self.msg_t -= dt
        if not self.dead:
            self.update_player(dt)
        # targeting & held mouse buttons
        eye = p.eye(False)
        self.target = None
        if not self.paused and not self.inventory and not self.dead:
            hit, prev = raycast(w, eye, p.forward(), 5.0)
            if hit:
                self.target = (hit, prev)
            self.mob_target = None
            best = math.dist(eye, np.array(hit) + 0.5) if hit else 4.0
            for m in self.mobs:
                t = m.ray_hit(eye, p.forward(), 4.0)
                if t is not None and t < best:
                    best = t
                    self.mob_target = m
            if self.mob_target is not None:
                self.target = None
            btn = pygame.mouse.get_pressed()
            self.break_cd -= dt
            self.place_cd -= dt
            if self.survival:
                if btn[0] and self.target:
                    if self.target[0] != self.mine_pos:
                        self.mine_pos = self.target[0]
                        self.mine_prog = 0.0
                    self.mine_prog += dt
                    if self.swing <= 0.05:
                        self.swing = 1.0
                    self.mine_snd -= dt
                    b = w.get(*self.mine_pos)
                    if self.mine_snd <= 0 and b:
                        self.sounds.block("step", b)
                        self.mine_snd = 0.25
                    if b and self.mine_prog >= HARD[b]:
                        self.break_block(self.mine_pos)
                        self.mine_pos = None
                        self.mine_prog = 0.0
                else:
                    self.mine_pos = None
                    self.mine_prog = 0.0
            elif btn[0] and self.target and self.break_cd <= 0:
                self.break_block(self.target[0])
                self.break_cd = 0.25
                self.swing = 1.0
            if btn[2] and self.target and self.place_cd <= 0:
                self.place_block(*self.target)
                self.place_cd = 0.25
                self.swing = 1.0
        self.update_mobs(dt)
        self.update_drops(dt)
        self.update_weather(dt)
        pcx, pcz = math.floor(p.pos[0]) >> 4, math.floor(p.pos[2]) >> 4
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                tl = w.torches.get((pcx + dx, pcz + dz))
                if tl is None:
                    continue
                for tx, ty, tz in tl:
                    if random.random() < dt * 1.2:
                        self.particles.append([np.array([tx + 0.5 + random.uniform(-0.03, 0.03), ty + 0.72, tz + 0.5]),
                                               np.array([random.uniform(-0.05, 0.05), 0.6, random.uniform(-0.05, 0.05)]),
                                               random.uniform(0.8, 1.4), 3.4 / 16, 0.4 / 16, -0.2])
        # tnt
        for pos in list(self.tnt):
            self.tnt[pos] -= dt
            if self.tnt[pos] <= 0:
                del self.tnt[pos]
                if w.get(*pos) == E.TNT:
                    self.explode(pos)
        # particles
        alive = []
        for pt in self.particles:
            pt[1][1] -= (pt[5] if len(pt) > 5 else 16) * dt
            np_ = pt[0] + pt[1] * dt
            b = w.get(math.floor(np_[0]), math.floor(np_[1]), math.floor(np_[2]))
            if b is not None and E.SOLID[b]:
                pt[1] *= 0.3
            else:
                pt[0] = np_
            pt[2] -= dt
            if pt[2] > 0:
                alive.append(pt)
        self.particles = alive[-600:]
        self.name_timer -= dt
        self.swing = max(0.0, getattr(self, "swing", 0.0) - dt * 4.0)
        target_fov = 80.0 if p.sprint else 70.0
        self.fov += (target_fov - self.fov) * min(1, dt * 8)
        if time.time() - self.last_save > 120:
            self.save()

    def update_mobs(self, dt):
        p = self.player
        w = self.world
        self.mob_timer -= dt
        if self.mob_timer <= 0 and len(self.mobs) < 14:
            self.mob_timer = 0.7
            ang = random.uniform(0, 2 * math.pi)
            r = random.uniform(18, 56)
            x, z = math.floor(p.pos[0] + math.cos(ang) * r), math.floor(p.pos[2] + math.sin(ang) * r)
            if (x >> 4, z >> 4) in w.chunks:
                y = H - 1
                while y > 0 and not E.SOLID[w.get(x, y, z)] and w.get(x, y, z) != E.WATER:
                    y -= 1
                if w.get(x, y, z) == E.GRASS:
                    kind = random.choice(list(MOB_KINDS))
                    for _ in range(random.randint(1, 3)):
                        self.mobs.append(Mob(kind, (x + 0.5 + random.uniform(-1, 1), y + 1.05, z + 0.5 + random.uniform(-1, 1))))
        daylight = self.sky()[1]
        nz = sum(1 for m in self.mobs if m.kind == "zombie")
        self.zombie_timer = getattr(self, "zombie_timer", 0.0) - dt
        if daylight < 0.5 and nz < 8 and self.zombie_timer <= 0:
            self.zombie_timer = 2.0
            ang = random.uniform(0, 2 * math.pi)
            r = random.uniform(16, 40)
            x, z = math.floor(p.pos[0] + math.cos(ang) * r), math.floor(p.pos[2] + math.sin(ang) * r)
            if (x >> 4, z >> 4) in w.chunks:
                y = H - 1
                while y > 0 and not E.SOLID[w.get(x, y, z)] and w.get(x, y, z) not in (E.WATER, E.LAVA):
                    y -= 1
                if E.SOLID[w.get(x, y, z)] and E.OPAQUE[w.get(x, y, z)]:
                    self.mobs.append(Mob("zombie", (x + 0.5, y + 1.05, z + 0.5)))
        if nz < 6 and self.zombie_timer <= 0 and self.exposure(p.pos) < 0.5:
            self.zombie_timer = 4.0
            x = math.floor(p.pos[0] + random.uniform(-16, 16))
            z = math.floor(p.pos[2] + random.uniform(-16, 16))
            if abs(x - p.pos[0]) + abs(z - p.pos[2]) > 8 and (x >> 4, z >> 4) in w.chunks:
                for y in range(math.floor(p.pos[1]) + 6, math.floor(p.pos[1]) - 8, -1):
                    if (E.SOLID[w.get(x, y - 1, z)] and w.get(x, y, z) == E.AIR and w.get(x, y + 1, z) == E.AIR
                            and self.exposure((x + 0.5, y, z + 0.5)) < 0.5):
                        self.mobs.append(Mob("zombie", (x + 0.5, y + 0.05, z + 0.5)))
                        break
        keep = []
        for m in self.mobs:
            if np.linalg.norm(m.pos[[0, 2]] - p.pos[[0, 2]]) > 110 or m.pos[1] < -10:
                continue
            if (m.kind == "zombie" and daylight > 0.75 and random.random() < dt * 0.5
                    and self.exposure(m.pos) >= 1.0):
                for _ in range(10):
                    self.particles.append([m.pos + (random.uniform(-0.3, 0.3), random.uniform(0.5, 1.9), random.uniform(-0.3, 0.3)),
                                           np.array([random.uniform(-0.5, 0.5), random.uniform(1, 2), random.uniform(-0.5, 0.5)]),
                                           random.uniform(0.4, 0.9), 15.2 / 16, 15.2 / 16])
                continue
            if (math.floor(m.pos[0]) >> 4, math.floor(m.pos[2]) >> 4) in w.meshes:
                chase = None
                if m.kind == "zombie" and self.survival and not self.dead:
                    d = np.linalg.norm(m.pos - p.pos)
                    if d < 24:
                        chase = p.pos
                    if d < 1.4 and m.attack_cd <= 0:
                        m.attack_cd = 1.0
                        self.damage(3)
                        kb = p.pos - m.pos
                        kb[1] = 0
                        nn = np.linalg.norm(kb)
                        if nn > 0:
                            p.vel += kb / nn * 6
                        p.vel[1] = 5.0
                    if d < 12 and random.random() < dt * 0.15:
                        self.sounds.play("groan", max(0.2, 1 - d / 16))
                m.update(w, dt, chase)
                if m.kind in ("pig", "cow", "sheep") and random.random() < dt * 0.05:
                    dd = float(np.linalg.norm(m.pos - p.pos))
                    if dd < 20:
                        self.sounds.play(m.kind, max(0.1, 1 - dd / 20))
            keep.append(m)
        self.mobs = keep

    def update_weather(self, dt):
        self.weather_t -= dt
        if self.weather_t <= 0:
            self.raining = not self.raining
            self.weather_t = random.uniform(60, 160) if self.raining else random.uniform(180, 420)
        target = 1.0 if self.raining else 0.0
        self.rain += max(-dt / 6, min(dt / 6, target - self.rain))
        snd = self.sounds
        if snd.ok:
            if self.rain_ch is None and self.rain > 0.01:
                self.rain_ch = snd.s["rain"][0].play(loops=-1)
            if self.rain_ch is not None:
                self.rain_ch.set_volume(self.rain * 0.5)
                if self.rain <= 0.0:
                    self.rain_ch.stop()
                    self.rain_ch = None
        if self.rain <= 0.01:
            return
        p = self.player
        rp = self.rpos
        rp[:, 1] -= np.where(self.rsnow, 3.0, 24.0) * dt
        if self.rsnow.any():
            rp[self.rsnow, 0] += np.sin(self.t * 1.5 + np.nonzero(self.rsnow)[0]) * dt * 0.6
        off = rp[:, [0, 2]] - p.pos[[0, 2]]
        dead = np.nonzero((rp[:, 1] < self.rkill) | (np.abs(off).max(axis=1) > 22))[0]
        w = self.world
        for i in dead[:150]:
            x = p.pos[0] + random.uniform(-20, 20)
            z = p.pos[2] + random.uniform(-20, 20)
            rp[i] = (x, p.pos[1] + random.uniform(6, 24), z)
            ix, iz = math.floor(x), math.floor(z)
            c = w.chunks.get((ix >> 4, iz >> 4))
            if c is None:
                self.rkill[i] = 1e9
                continue
            col = c[ix & 15, :, iz & 15]
            nz = np.nonzero(col)[0]
            top = (nz[-1] + 1) if len(nz) else 0
            self.rkill[i] = top
            self.rsnow[i] = top > 88
            if not self.rsnow[i] and E.temperature(w.perm, ix, iz) > 0.17:
                self.rkill[i] = 1e9

    def update_drops(self, dt):
        p = self.player
        w = self.world
        keep = []
        target = p.pos + (0, 0.8, 0)
        for dr in self.drops:
            pos, vel = dr[0], dr[1]
            dr[3] += dt
            to = target - pos
            dist = float(np.linalg.norm(to))
            if dr[3] > 0.4 and not self.dead:
                if dist < 1.0:
                    self.give(dr[2])
                    self.sounds.play("pickup", 0.5)
                    continue
                if dist < 2.5:
                    vel[:] = to / max(dist, 0.1) * 8.0
            vel[1] -= 16 * dt
            npos = pos + vel * dt
            b = w.get(math.floor(npos[0]), math.floor(npos[1] - 0.12), math.floor(npos[2]))
            if b is None or E.SOLID[b]:
                if vel[1] < 0:
                    npos[1] = math.floor(npos[1] - 0.12) + 1.12
                vel[0] *= 0.5
                vel[2] *= 0.5
                vel[1] = 0.0
            dr[0] = npos
            if dr[3] < 300 and dist < 120:
                keep.append(dr)
        self.drops = keep[-300:]

    def drop_tris(self, cam, br):
        out = []
        for pos, vel, b, age in self.drops:
            ang = age * 2.0
            ca, sa = math.cos(ang), math.sin(ang)
            R = np.array([[ca, 0, sa], [0, 1, 0], [-sa, 0, ca]])
            c = pos - cam + (0, 0.08 + math.sin(age * 3) * 0.06, 0)
            sz = 0.25
            if E.KIND[b] in (E.K_CROSS, E.K_TORCH):
                t = E.TEX[b, 0]
                r, cc = divmod(int(t), 16)
                quad = [(-0.5, -0.5, (cc / 16, (r + 1) / 16)), (0.5, -0.5, ((cc + 1) / 16, (r + 1) / 16)),
                        (0.5, 0.5, ((cc + 1) / 16, r / 16)), (-0.5, 0.5, (cc / 16, r / 16))]
                pts = [(R @ np.array([qx * sz * 1.4, qy * sz * 1.4, 0.0]) + c, uv) for qx, qy, uv in quad]
                for k in (0, 1, 2, 0, 2, 3, 0, 2, 1, 0, 3, 2):
                    out.extend([*pts[k][0], *pts[k][1], br, br, br, 1])
                continue
            for d in range(6):
                t = E.TEX[b, d]
                r, cc = divmod(int(t), 16)
                sh = E.FACE_SHADE[d] * br
                fc = E.FACE_C[d]
                pts = []
                for k in range(4):
                    lu, lv = E._local_uv(d, fc[k][0], fc[k][1], fc[k][2])
                    pts.append((R @ ((fc[k] - 0.5) * sz) + c, ((cc + lu) / 16, (r + lv) / 16)))
                for k in (0, 1, 2, 0, 2, 3):
                    out.extend([*pts[k][0], *pts[k][1], sh, sh, sh, 1])
        return out

    def hit_mob(self, m):
        p = self.player
        d = m.pos - p.pos
        d[1] = 0
        n = np.linalg.norm(d)
        if n > 0:
            m.vel += d / n * 6.0
        m.vel[1] = 6.0
        m.hurt = 0.35
        m.health -= 1
        m.speed = 2.6
        m.timer = 3.0
        m.yaw = math.atan2(d[0], -d[2]) if n > 0 else m.yaw
        self.sounds.play("hurt")
        if m.health <= 0:
            self.mobs.remove(m)
            self.sounds.play("pop")
            for _ in range(16):
                self.particles.append([m.pos + (random.uniform(-0.4, 0.4), random.uniform(0.2, 1.0), random.uniform(-0.4, 0.4)),
                                       np.array([random.uniform(-1, 1), random.uniform(1, 3), random.uniform(-1, 1)]),
                                       random.uniform(0.4, 0.8), 15.2 / 16, 15.2 / 16])

    # -- rendering
    def sky(self):
        a = self.tod * 2 * math.pi
        sun_h = math.sin(a)
        day = min(1.0, max(0.0, (sun_h + 0.15) / 0.4))
        daylight = 0.3 + 0.7 * day
        day_c = np.array([0.53, 0.72, 1.0])
        night_c = np.array([0.02, 0.03, 0.08])
        c = night_c + (day_c - night_c) * day
        dusk = max(0.0, 1.0 - abs(sun_h) / 0.25) * (1 if math.cos(a) != 0 else 0)
        c = c * (1 - dusk * 0.5) + np.array([1.0, 0.5, 0.25]) * dusk * 0.5
        r = getattr(self, "rain", 0.0)
        if r > 0:
            daylight *= 1.0 - 0.2 * r
            c = c * (1 - 0.65 * r) + np.array([0.48, 0.5, 0.55]) * (0.15 + 0.85 * day) * 0.65 * r
        return a, daylight, c

    def render(self):
        ctx = self.ctx
        W, Hh = self.size
        p = self.player
        a, daylight, sky_c = self.sky()
        eye = p.eye()
        if self.third:
            back = p.forward()
            dist = 0.0
            while dist < 4.0:
                q = eye - back * (dist + 0.3)
                b = self.world.get(math.floor(q[0]), math.floor(q[1]), math.floor(q[2]))
                if b is None or E.OPAQUE[b]:
                    break
                dist += 0.1
            eye = eye - back * dist
        cam = eye
        head = self.world.get(math.floor(eye[0]), math.floor(eye[1] + 0.05), math.floor(eye[2]))
        underwater = head == E.WATER
        fog_end = self.world.radius * 16 - 6
        fog_start = fog_end * 0.55
        dayf = (daylight - 0.3) / 0.7
        fog_c = sky_c + (np.array([0.86, 0.9, 1.0]) - sky_c) * 0.42 * dayf
        zen_c = sky_c * np.array([0.72, 0.84, 1.0])
        if underwater:
            fog_c = np.array([0.08, 0.2, 0.5]) * daylight
            fog_start, fog_end = 0.0, 22.0
        ctx.clear(*fog_c, 1.0)
        ctx.viewport = (0, 0, W, Hh)
        fwd = p.forward()
        shake = getattr(self, "shake", 0.0)
        if shake > 0:
            self.shake = max(0.0, shake - 1 / 60)
            fwd = fwd + np.random.uniform(-1, 1, 3) * shake * 0.03
        proj = perspective(self.fov, W / max(1, Hh), 0.05, 1000.0)
        view = view_rot(fwd)
        if self.hurt_t > 0:
            ang = math.sin(self.hurt_t / 0.45 * math.pi) * 0.12
            ca, sa = math.cos(ang), math.sin(ang)
            roll = np.identity(4)
            roll[0, 0], roll[0, 1], roll[1, 0], roll[1, 1] = ca, -sa, sa, ca
            view = roll @ view
        vp = proj @ view
        vpb = mat_bytes(vp)

        # sun & moon
        ctx.disable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
        ctx.enable(moderngl.BLEND)
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        sp = self.simple_prog
        sp["m_vp"].write(vpb)
        sp["u_fog_color"].value = tuple(fog_c)
        sp["u_fog_end"].value = 900.0
        verts = []
        if not underwater:
            hc = (*fog_c, 1.0)
            zc = (*zen_c, 1.0)
            for i in range(32):
                a0, a1 = i / 32 * 2 * math.pi, (i + 1) / 32 * 2 * math.pi
                p0 = (math.cos(a0) * 500, 0.0, math.sin(a0) * 500)
                p1 = (math.cos(a1) * 500, 0.0, math.sin(a1) * 500)
                m0 = (p0[0] * 0.8, 160.0, p0[2] * 0.8)
                m1 = (p1[0] * 0.8, 160.0, p1[2] * 0.8)
                mc = tuple(np.array(hc) * 0.35 + np.array(zc) * 0.65)
                for pt, col in ((m0, mc), (p0, hc), (p1, hc), (m0, mc), (p1, hc), (m1, mc),
                                ((0.0, 500.0, 0.0), zc), (m0, mc), (m1, mc)):
                    verts.extend([*pt, 0, 0, *col])
            sd = np.array([math.cos(a), math.sin(a), 0.25])
            sd /= np.linalg.norm(sd)
            sa = 1.0 - 0.85 * self.rain
            for d, size, col in ((sd, 40, (1.0, 0.97, 0.75, sa)), (-sd, 28, (0.85, 0.88, 1.0, sa))):
                c = d * 400
                t1 = np.cross(d, (0, 0, 1.0))
                t1 /= np.linalg.norm(t1)
                t2 = np.cross(d, t1)
                pts = [c + (t1 * i + t2 * j) * size for i, j in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
                for k in (0, 1, 2, 0, 2, 3):
                    verts.extend([*pts[k], 0, 0, *col])
        night = 1.0 - min(1.0, max(0.0, (math.sin(a) + 0.3) / 0.35))
        if night > 0.01 and not underwater:
            ca, sa = math.cos(a), math.sin(a)
            S = self.stars @ np.array([[ca, sa, 0], [-sa, ca, 0], [0, 0, 1.0]])
            t1 = np.cross(S, (0, 0, 1.0))
            t1 /= np.linalg.norm(t1, axis=1)[:, None]
            t2 = np.cross(S, t1)
            c = S * 400
            sz = self.star_sz[:, None]
            corners = [c + (-t1 - t2) * sz, c + (t1 - t2) * sz, c + (t1 + t2) * sz, c + (-t1 + t2) * sz]
            pos = np.stack([corners[k] for k in (0, 1, 2, 0, 2, 3)], 1).reshape(-1, 3)
            sv = np.zeros((len(pos), 9), np.float32)
            sv[:, :3] = pos
            sv[:, 5:8] = 1.0
            sv[:, 8] = night * 0.9
            verts.extend(sv.ravel().tolist())
        self.sdraw(verts, moderngl.TRIANGLES)

        # terrain
        ctx.enable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
        ctx.disable(moderngl.BLEND)
        cp = self.chunk_prog
        cp["m_vp"].write(vpb)
        cp["u_cam"].value = tuple(cam)
        cp["u_time"].value = self.t
        cp["u_daylight"].value = daylight
        cp["u_fog_color"].value = tuple(fog_c)
        cp["u_fog_start"].value = fog_start
        cp["u_fog_end"].value = fog_end
        cp["u_water"].value = 0
        self.atlas.use(0)
        self.drawn = self.world.draw(vp, cam, False) or 0

        draw_mobs = list(self.mobs)
        if self.third:
            me = Mob("steve", tuple(p.pos))
            me.yaw = p.yaw
            me.walk = p.walk / 1.5
            me.hurt = self.hurt_t
            draw_mobs.append(me)
        if draw_mobs:
            mv = []
            br = 0.25 + 0.75 * daylight
            for m in draw_mobs:
                d = m.pos - cam
                dist = np.linalg.norm(d)
                if dist < fog_end and (dist < 3 or d @ fwd > -1.5):
                    mv.append(m.tris(cam, br * self.exposure(m.pos)))
            if mv:
                sp["u_fog_end"].value = fog_end
                self.sdraw(np.concatenate(mv), moderngl.TRIANGLES, fog=True)
        if self.drops:
            self.sdraw(self.drop_tris(cam, 0.3 + 0.7 * daylight), moderngl.TRIANGLES, tex=self.atlas)
        ctx.enable(moderngl.BLEND)
        ctx.disable(moderngl.CULL_FACE)
        # block outline
        if self.target and not self.hide_hud:
            x, y, z = self.target[0]
            o = np.array([x, y, z], float) - cam
            e = 0.003
            lo, hi = o - e, o + 1 + e
            cs = [np.array([lo[0] if i & 1 == 0 else hi[0], lo[1] if i & 2 == 0 else hi[1], lo[2] if i & 4 == 0 else hi[2]]) for i in range(8)]
            edges = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]
            lv = []
            for i, j in edges:
                lv.extend([*cs[i], 0, 0, 0, 0, 0, 0.7])
                lv.extend([*cs[j], 0, 0, 0, 0, 0, 0.7])
            self.sdraw(lv, moderngl.LINES)
        # mining cracks
        if self.survival and self.mine_pos and self.mine_prog > 0:
            b = self.world.get(*self.mine_pos)
            if b:
                stage = min(9, int(self.mine_prog / HARD[b] * 10))
                o = np.array(self.mine_pos, float) - cam - 0.003
                self.sdraw(self.cube_tris_uv(o, 1.006, 208 + stage), moderngl.TRIANGLES, tex=self.atlas)
        # lit tnt flash
        if self.tnt:
            tv = []
            for (x, y, z), tleft in self.tnt.items():
                if int(tleft * 5) % 2 == 0:
                    continue
                o = np.array([x, y, z], float) - cam - 0.01
                tv.extend(self.cube_tris(o, 1.02, (1, 1, 1, 0.55)))
            self.sdraw(tv, moderngl.TRIANGLES)
        # particles
        if self.particles:
            right = np.cross(fwd, (0, 1, 0))
            right /= max(1e-6, np.linalg.norm(right))
            up = np.cross(right, fwd)
            pv = []
            s = 0.07
            br = 0.3 + 0.7 * daylight
            for pt in self.particles:
                pos, u, v = pt[0], pt[3], pt[4]
                smoke = len(pt) > 5
                ps = s * (0.4 + pt[2] * 0.35) if smoke else s
                pa = min(0.6, pt[2]) if smoke else 1.0
                c = pos - cam
                pts = [c + (-right - up) * ps, c + (right - up) * ps, c + (right + up) * ps, c + (-right + up) * ps]
                uv = [(u, v + 0.25 / 16), (u + 0.25 / 16, v + 0.25 / 16), (u + 0.25 / 16, v), (u, v)]
                for k in (0, 1, 2, 0, 2, 3):
                    pv.extend([*pts[k], *uv[k], br, br, br, pa])
            self.sdraw(pv, moderngl.TRIANGLES, tex=self.atlas)
        # clouds
        cy = 118 - cam[1]
        span = 900.0
        scale = 1.0 / (12 * 64)
        ox = (cam[0] + self.t * 1.2) * scale
        oz = cam[2] * scale
        cb = (0.25 + 0.75 * daylight) * (1 - 0.45 * self.rain)
        ccol = (cb, cb, cb, 0.85)
        cl = []
        for (i, j) in ((-1, -1), (1, -1), (1, 1), (-1, -1), (1, 1), (-1, 1)):
            cl.extend([i * span, cy, j * span, ox + i * span * scale, oz + j * span * scale, *ccol])
        sp["u_fog_end"].value = span
        self.sdraw(cl, moderngl.TRIANGLES, tex=self.clouds, fog=True)
        # water
        self.atlas.use(0)
        cp["u_water"].value = 1
        self.world.draw(vp, cam, True)
        if self.rain > 0.01:
            n = int(len(self.rpos) * self.rain)
            pts = self.rpos[:n] - cam
            alive = self.rpos[:n, 1] >= self.rkill[:n]
            snow = self.rsnow[:n][alive]
            pts = pts[alive]
            if len(pts):
                rv = np.zeros((len(pts), 2, 9), np.float32)
                rv[:, 0, :3] = pts
                rv[:, 1, :3] = pts + (0.06, 1.3, 0.0)
                rv[snow, 1, :3] = pts[snow] + (0.12, 0.12, 0.0)
                bri = 0.45 + 0.55 * daylight
                rv[:, :, 5:8] = (0.7 * bri, 0.78 * bri, 0.95 * bri)
                rv[snow, :, 5:8] = bri
                rv[:, 0, 8] = 0.8
                rv[:, 1, 8] = 0.15
                rv[snow, 1, 8] = 0.9
                self.sdraw(rv.reshape(-1, 9), moderngl.LINES)

        # GUI
        ctx.disable(moderngl.DEPTH_TEST)
        if not self.hide_hud and not self.third and not self.dead:
            self.draw_hand(W, Hh, daylight)
        gp = self.gui_prog
        gp["u_screen"].value = (W, Hh)
        g = self.gui
        if underwater:
            g.rect(0, 0, W, Hh, (0.1, 0.25, 0.7, 0.35))
            g.flush(self.atlas)
        g.quad(0, 0, W, Hh, (0, 0), (1, 1), (1, 1, 1, 1))
        g.flush(self.vignette)
        if not self.hide_hud:
            self.draw_hud(W, Hh)
        if self.hurt_t > 0:
            g.rect(0, 0, W, Hh, (0.8, 0.0, 0.0, self.hurt_t * 0.5))
            g.flush(self.atlas)
        if self.inventory:
            self.draw_inventory(W, Hh)
        if self.dead:
            g.rect(0, 0, W, Hh, (0.45, 0.0, 0.0, 0.6))
            x, y, bw, bh = self.respawn_rect()
            hov = self.respawn_hover()
            g.rect(x, y, bw, bh, (0.45, 0.45, 0.5, 1) if hov else (0.3, 0.3, 0.32, 1))
            g.frame(x, y, bw, bh, 2, (1, 1, 1, 1) if hov else (0, 0, 0, 1))
            g.flush(self.atlas)
            g.text("You died!", W / 2, Hh / 2 - 90, 64, center=True)
            g.text("Respawn", W / 2, y + 12, 30, center=True)
        if self.paused:
            self.draw_pause(W, Hh)
        if not self.spawned:
            g.rect(0, 0, W, Hh, (0.25, 0.18, 0.12, 1))
            g.flush(self.atlas)
            g.text("Generating terrain...", W / 2, Hh / 2 - 20, 40, center=True)

    def draw_hand(self, W, Hh, daylight):
        b = self.hotbar[self.sel]
        p = self.player
        sw = getattr(self, "swing", 0.0)
        sws = math.sin(sw * math.pi)
        bob = math.sin(p.walk * math.pi) * 0.03 if p.on_ground else 0.0
        proj = perspective(70.0, W / max(1, Hh), 0.01, 10.0)
        ry = 0.75 + sws * 0.3
        rx = -sws * 0.9
        cy, sy = math.cos(ry), math.sin(ry)
        cx, sx = math.cos(rx), math.sin(rx)
        R = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
        T = np.array([0.62 + bob - sws * 0.25, -0.58 - abs(bob) - sws * 0.1, -1.05 - sws * 0.1])
        br = (0.35 + 0.65 * daylight) * self.exposure(p.eye(False))
        verts = []
        if self.survival and self.counts.get(b, 0) <= 0:
            skin = np.array((0.85, 0.65, 0.5))
            ax, ay = 0.45 - sws * 0.8, 0.35
            ca_, sa_ = math.cos(ax), math.sin(ax)
            cb_, sb_ = math.cos(ay), math.sin(ay)
            R2 = np.array([[1, 0, 0], [0, ca_, -sa_], [0, sa_, ca_]]) @ np.array([[cb_, 0, sb_], [0, 1, 0], [-sb_, 0, cb_]])
            T2 = np.array([0.55 + bob, -0.62 - abs(bob), -0.85 - sws * 0.15])
            for d in range(6):
                sh = E.FACE_SHADE[d] * br
                pts = [R2 @ ((E.FACE_C[d, ci] - 0.5) * (0.17, 0.17, 0.6) + (0, 0, 0.15)) + T2 for ci in range(4)]
                for k in (0, 1, 2, 0, 2, 3):
                    verts.extend([*pts[k], 0, 0, *(skin * sh), 1])
            self.simple_prog["m_vp"].write(mat_bytes(proj))
            self.ctx.enable(moderngl.CULL_FACE)
            self.sdraw(verts, moderngl.TRIANGLES)
            self.ctx.disable(moderngl.CULL_FACE)
            return
        if E.KIND[b] in (E.K_CROSS, E.K_TORCH):
            ry = 0.2 + sws * 0.3
            cy, sy = math.cos(ry), math.sin(ry)
            R = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
            t = E.TEX[b, 0]
            r, c = divmod(int(t), 16)
            quad = [(-0.5, -0.5, 0, c / 16, (r + 1) / 16), (0.5, -0.5, 0, (c + 1) / 16, (r + 1) / 16),
                    (0.5, 0.5, 0, (c + 1) / 16, r / 16), (-0.5, 0.5, 0, c / 16, r / 16)]
            for k in (0, 1, 2, 0, 2, 3, 0, 2, 1, 0, 3, 2):
                x, y, z, u, v = quad[k]
                q = R @ (np.array([x, y, z]) * 0.55) + T
                verts.extend([*q, u, v, br, br, br, 1])
        else:
            for d in range(6):
                t = E.TEX[b, d]
                r, c = divmod(int(t), 16)
                sh = E.FACE_SHADE[d] * br
                pts = []
                for ci in range(4):
                    cc = E.FACE_C[d, ci]
                    lu, lv = E._local_uv(d, cc[0], cc[1], cc[2])
                    q = R @ ((cc - 0.5) * 0.4) + T
                    pts.append((*q, (c + lu) / 16, (r + lv) / 16))
                for k in (0, 1, 2, 0, 2, 3):
                    verts.extend([*pts[k], sh, sh, sh, 1])
        self.simple_prog["m_vp"].write(mat_bytes(proj))
        self.ctx.enable(moderngl.CULL_FACE)
        self.sdraw(verts, moderngl.TRIANGLES, tex=self.atlas)
        self.ctx.disable(moderngl.CULL_FACE)

    def exposure(self, pos):
        """Rough light factor for entities: 1 under open sky, dimmer under cover, lit near torches."""
        x, y, z = math.floor(pos[0]), math.floor(pos[1] + 0.5), math.floor(pos[2])
        c = self.world.chunks.get((x >> 4, z >> 4))
        if c is None:
            return 1.0
        col = c[x & 15, :, z & 15]
        solid = np.nonzero(E.OPAQUE[col])[0]
        if len(solid) == 0 or solid[-1] < y:
            return 1.0
        f = 0.35
        lo = max(0, y - 3)
        for dx in (-3, 0, 3):
            for dz in (-3, 0, 3):
                cc = self.world.chunks.get(((x + dx) >> 4, (z + dz) >> 4))
                if cc is not None and np.any(E.LIGHT[cc[(x + dx) & 15, lo:y + 4, (z + dz) & 15]] > 0):
                    f = 0.9
        return f

    def cube_tris_uv(self, o, s, tile):
        r, c = divmod(int(tile), 16)
        out = []
        for d in range(6):
            fc = E.FACE_C[d]
            for k in (0, 1, 2, 0, 2, 3):
                lu, lv = E._local_uv(d, fc[k][0], fc[k][1], fc[k][2])
                out.extend([o[0] + fc[k][0] * s, o[1] + fc[k][1] * s, o[2] + fc[k][2] * s,
                            (c + lu) / 16, (r + lv) / 16, 1, 1, 1, 1])
        return out

    def cube_tris(self, o, s, col):
        out = []
        for d in range(6):
            c = E.FACE_C[d]
            for k in (0, 1, 2, 0, 2, 3):
                out.extend([o[0] + c[k][0] * s, o[1] + c[k][1] * s, o[2] + c[k][2] * s, 0, 0, *col])
        return out

    def draw_hud(self, W, Hh):
        g = self.gui
        ctx = self.ctx
        # crosshair (inverted colours)
        if not self.paused and not self.inventory and not self.dead:
            ctx.blend_func = moderngl.ONE_MINUS_DST_COLOR, moderngl.ZERO
            g.rect(W / 2 - 10, Hh / 2 - 1, 20, 2, (1, 1, 1, 1))
            g.rect(W / 2 - 1, Hh / 2 - 10, 2, 8, (1, 1, 1, 1))
            g.rect(W / 2 - 1, Hh / 2 + 2, 2, 8, (1, 1, 1, 1))
            g.flush(self.atlas)
            ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        # hotbar
        s = max(40, min(64, int(Hh / 14)))
        x0 = W / 2 - s * 4.5
        y0 = Hh - s - 8
        g.rect(x0 - 3, y0 - 3, s * 9 + 6, s + 6, (0.0, 0.0, 0.0, 0.45))
        for i in range(9):
            g.frame(x0 + i * s, y0, s, s, 2, (0.55, 0.55, 0.55, 0.9))
        g.frame(x0 + self.sel * s - 3, y0 - 3, s + 6, s + 6, 3, (1, 1, 1, 1))
        for i, b in enumerate(self.hotbar):
            have = not self.survival or self.counts.get(b, 0) > 0
            g.icon(b, x0 + i * s + s / 2, y0 + s / 2, s * 0.72, 1.0 if have else 0.3)
        if self.survival:
            hs = int(s * 0.42)
            for i in range(10):
                hp = self.health - i * 2
                tile = 218 if hp >= 2 else (219 if hp == 1 else 220)
                (u0, v0), (u1, v1) = g.tile_uv(tile)
                jit = random.uniform(-1.5, 1.5) if self.health <= 4 else 0
                g.quad(x0 + i * (hs + 1), y0 - hs - 8 + jit, hs, hs, (u0, v0), (u1, v1))
            if self.air < 10:
                for i in range(10):
                    if self.air > i:
                        (u0, v0), (u1, v1) = g.tile_uv(221)
                        g.quad(x0 + s * 9 - (i + 1) * (hs + 1), y0 - hs - 8, hs, hs, (u0, v0), (u1, v1))
        g.flush(self.atlas)
        if self.survival:
            for i, b in enumerate(self.hotbar):
                c = self.counts.get(b, 0)
                if c > 0:
                    g.text(str(c), x0 + i * s + s - 22, y0 + s - 20, 20)
        for i in range(9):
            g.text(str(i + 1), x0 + i * s + 4, y0 + 2, 16, (220, 220, 220))
        if self.msg_t > 0:
            g.text(self.msg, W / 2, Hh * 0.3, 40, center=True, alpha=min(1.0, self.msg_t))
        if self.name_timer > 0:
            g.text(E.BLOCK_NAMES[self.hotbar[self.sel]], W / 2, y0 - 36, 28, center=True,
                   alpha=min(1.0, self.name_timer))
        p = self.player
        if p.flying:
            g.text("Flying", 10, Hh - 30, 22, (200, 230, 255))
        if self.show_debug:
            lines = [
                f"StelexCraft  {self.fps:.0f} fps",
                f"XYZ: {p.pos[0]:.2f} / {p.pos[1]:.2f} / {p.pos[2]:.2f}",
                f"Chunk: {math.floor(p.pos[0]) >> 4}, {math.floor(p.pos[2]) >> 4}   loaded {len(self.world.chunks)}  meshes {len(self.world.meshes)}  drawn {self.drawn}",
                f"Render distance: {self.world.radius} chunks (+/-)   pending {self.world.pending()}",
                f"Facing: {['north', 'east', 'south', 'west'][int(((p.yaw % (2 * math.pi)) / (math.pi / 2)) + 0.5) % 4]}  yaw {math.degrees(p.yaw) % 360:.0f} pitch {math.degrees(p.pitch):.0f}",
                f"Time of day: {int((self.tod * 24 + 6) % 24):02d}:{int(((self.tod * 24 + 6) % 1) * 60):02d}   weather {'rain' if self.raining else 'clear'}   seed {self.world.seed}",
            ]
            if self.target:
                b = self.world.get(*self.target[0])
                lines.append(f"Looking at: {E.BLOCK_NAMES[b] if b is not None else '?'} {self.target[0]}")
            for i, ln in enumerate(lines):
                g.text(ln, 8, 8 + i * 22, 22)
        else:
            mode = "Survival" if self.survival else "Creative"
            g.text(f"StelexCraft   {self.fps:.0f} fps   {mode} (G to switch)   F3 debug, E blocks, ESC menu", 8, 8, 20, (230, 230, 230))

    def draw_inventory(self, W, Hh):
        g = self.gui
        s, cols, x0, y0, pw, ph = self.inv_layout()
        g.rect(0, 0, W, Hh, (0, 0, 0, 0.5))
        g.rect(x0, y0, pw, ph, (0.78, 0.78, 0.78, 0.97))
        g.frame(x0, y0, pw, ph, 3, (0.3, 0.3, 0.3, 1))
        hov = self.inv_hover()
        items = self.inv_items()
        if not items:
            g.flush(self.atlas)
            g.text("Your inventory is empty - mine some blocks!", W / 2, y0 + 64, 24, (40, 40, 40), shadow=False, center=True)
        for n, b in enumerate(items):
            i, j = n % cols, n // cols
            x, y = x0 + 20 + i * s, y0 + 60 + j * s
            g.rect(x + 1, y + 1, s - 2, s - 2, (0.55, 0.55, 0.55, 1) if b != hov else (0.85, 0.85, 1.0, 1))
            g.icon(b, x + s / 2, y + s / 2, s * 0.7)
        g.flush(self.atlas)
        if self.survival:
            for n, b in enumerate(items):
                i, j = n % cols, n // cols
                g.text(str(self.counts.get(b, 0)), x0 + 20 + i * s + s - 22, y0 + 60 + j * s + s - 20, 20)
        g.text("Blocks  (click to put in selected slot, or hover + 1-9)", x0 + 20, y0 + 18, 26, (40, 40, 40), shadow=False)
        if self.survival:
            rects = self.recipe_rects()
            rhov = self.recipe_hover()
            px = rects[0][0] - 6
            g.rect(px, y0, 392, 56 + len(rects) * 40, (0.78, 0.78, 0.78, 0.97))
            g.frame(px, y0, 392, 56 + len(rects) * 40, 3, (0.3, 0.3, 0.3, 1))
            for x, y, w, h, r in rects:
                ok = self.can_craft(r)
                col = (0.62, 0.8, 0.62, 1) if ok else (0.6, 0.6, 0.6, 1)
                if r is rhov and ok:
                    col = (0.75, 0.95, 0.75, 1)
                g.rect(x, y, w, h, col)
                g.icon(r[0], x + 20, y + h / 2, 30, 1.0 if ok else 0.45)
                ix = x + 150
                for b, n in r[2]:
                    g.icon(b, ix, y + h / 2, 26, 1.0 if self.counts.get(b, 0) >= n else 0.45)
                    ix += 58
            g.flush(self.atlas)
            g.text("Crafting (click a recipe)", px + 12, y0 + 16, 24, (40, 40, 40), shadow=False)
            for x, y, w, h, r in rects:
                g.text(f"x{r[1]}", x + 40, y + 9, 22, (30, 30, 30), shadow=False)
                g.text("<=", x + 100, y + 9, 22, (30, 30, 30), shadow=False)
                ix = x + 150
                for b, n in r[2]:
                    g.text(str(n), ix + 14, y + 14, 18)
                    ix += 58
            if rhov is not None:
                mx, my = pygame.mouse.get_pos()
                label = E.BLOCK_NAMES[rhov[0]] + "  <=  " + " + ".join(f"{n} {E.BLOCK_NAMES[b]}" for b, n in rhov[2])
                g.rect(mx + 12, my - 4, len(label) * 10 + 16, 30, (0.1, 0.0, 0.15, 0.92))
                g.flush(self.atlas)
                g.text(label, mx + 20, my + 2, 24)
        if hov is not None:
            mx, my = pygame.mouse.get_pos()
            g.rect(mx + 12, my - 4, len(E.BLOCK_NAMES[hov]) * 11 + 16, 30, (0.1, 0.0, 0.15, 0.92))
            g.flush(self.atlas)
            g.text(E.BLOCK_NAMES[hov], mx + 20, my + 2, 24)

    def draw_pause(self, W, Hh):
        g = self.gui
        g.rect(0, 0, W, Hh, (0, 0, 0, 0.55))
        hov = self.pause_hover()
        for i, (x, y, w, h, label) in enumerate(self.pause_buttons()):
            g.rect(x, y, w, h, (0.45, 0.45, 0.5, 1) if hov == i else (0.3, 0.3, 0.32, 1))
            g.frame(x, y, w, h, 2, (0, 0, 0, 1) if hov != i else (1, 1, 1, 1))
        g.flush(self.atlas)
        g.text("Game Menu", W / 2, Hh / 2 - 130, 48, center=True)
        for i, (x, y, w, h, label) in enumerate(self.pause_buttons()):
            g.text(label, x + w / 2, y + 12, 30, center=True)
        help_lines = [
            "WASD move   Space jump (double-tap: fly)   Shift sneak / fly down   Ctrl or double-tap W sprint",
            "Left click break / hit animals   Right click place (right click TNT to ignite)   Middle click pick block",
            "1-9 / wheel select   E block picker   G survival/creative   +/- render distance   [ ] mouse sensitivity",
            "F2 screenshot   F5 third person   F7 toggle rain   F11 fullscreen   F3 debug   F1 hide HUD",
            "Q: quit (world is saved automatically)",
        ]
        for i, ln in enumerate(help_lines):
            g.text(ln, W / 2, Hh / 2 + 165 + i * 26, 22, (210, 210, 210), center=True)

    def autotest(self, dt):
        self.at = getattr(self, "at", 0.0) + dt
        shots = getattr(self, "shots", 0)
        marks = [6.0, 9.0, 13.0, 15.5]
        if self.at > 4.5 and not getattr(self, "tt", False):
            self.tt = True
            pp = self.player
            f = pp.forward()
            tx, tz = math.floor(pp.pos[0] + f[0] * 2), math.floor(pp.pos[2] + f[2] * 2)
            ty = math.floor(pp.pos[1])
            if self.world.get(tx, ty, tz) in (E.AIR, E.TALLGRASS):
                self.world.set(tx, ty, tz, E.TORCH)
        if self.at > 4.0 and self.at < 4.1:
            self.player.pitch = -0.35
        if self.at > 6.5 and shots == 1 and not getattr(self, "boom", False):
            self.boom = True
            self.raining = True
            self.rain = 1.0
            p = self.player
            x, y, z = math.floor(p.pos[0]) + 6, math.floor(p.pos[1]), math.floor(p.pos[2])
            self.world.set(x, y, z, E.TNT)
            self.explode((x, y, z))
            self.player.yaw = math.pi / 2
            self.player.pitch = -0.4
            self.sel = 7
        if self.at > 9.5 and shots == 2 and not getattr(self, "moved", False):
            self.moved = True
            pp = self.player
            pp.pitch = -0.1
            self.raining = False
            self.rain = 0.0
            for key, arr in self.world.chunks.items():
                hits = np.argwhere(arr == E.LAVA)
                if len(hits) > 20 and key in self.world.meshes:
                    lx, ly, lz = hits[len(hits) // 2]
                    pp.pos[:] = (key[0] * 16 + lx + 0.5, ly + 2.2, key[1] * 16 + lz + 3.5)
                    pp.flying = True
                    pp.pitch = -0.6
                    pp.yaw = 0.0
                    for dy in range(0, 4):
                        for dz in range(-1, 4):
                            self.world.set(math.floor(pp.pos[0]), ly + 1 + dy, key[1] * 16 + lz + dz, E.AIR)
                    break
        if self.at > 13.5 and shots == 3 and not getattr(self, "nw", False):
            self.nw = True
            self.new_world()
            self.tod = 0.25
        if self.at > 13.5 and shots == 3:
            self.third = False
            if self.mobs and not self.nw:
                m = self.mobs[0]
                p = self.player
                p.flying = True
                p.pos[:] = m.pos + (2.5, 1.0, 2.5)
                d = m.pos - p.eye(False)
                p.yaw = math.atan2(d[0], -d[2])
                p.pitch = math.atan2(d[1] + 0.5, math.hypot(d[0], d[2]))
                for dx in (-2, 2):
                    x, z = math.floor(p.pos[0]) + dx, math.floor(p.pos[2])
                    y = H - 1
                    while y > 0 and not E.SOLID[self.world.get(x, y, z)]:
                        y -= 1
                    self.world.set(x, y + 1, z, E.TORCH)
        if self.at > 14.8 and not getattr(self, "acted", False):
            self.acted = True
            self.survival = True
            self.give(E.DIRT)
            self.damage(5)
            self.mine_pos = None
            for m in list(self.mobs[:1]):
                for _ in range(4):
                    if m in self.mobs:
                        self.hit_mob(m)
            hit, prev = raycast(self.world, self.player.eye(False), self.player.forward(), 8.0)
            if hit:
                self.break_block(hit)
                hit, prev = raycast(self.world, self.player.eye(False), self.player.forward(), 8.0)
                self.sel = 0
                if hit:
                    self.place_block(hit, prev)
            pp = self.player
            f = pp.forward()
            for k in range(4):
                self.drops.append([pp.pos + np.array([f[0] * 2.5 + k * 0.4 - 0.6, 1.0, f[2] * 2.5]),
                                   np.array([0.0, 2.0, 0.0]), [E.DIRT, E.COBBLE, E.LOG, E.POPPY][k], 0.0])
            if self.target:
                self.mine_pos = self.target[0]
                self.mine_prog = 0.5
            pp = self.player
            tx, ty, tz = math.floor(pp.pos[0]) + 2, math.floor(pp.pos[1]), math.floor(pp.pos[2])
            self.world.set(tx, ty, tz, E.TNT)
            self.explode((tx, ty, tz))
            print("actions ok, mobs", len(self.mobs), "counts", self.counts, "health", self.health, flush=True)
        if self.at > 15.0 and not getattr(self, "inv_shown", False):
            self.inv_shown = True
            self.health = 20
            for b, n in ((E.LOG, 3), (E.COAL, 2), (E.SAND, 6), (E.COBBLE, 9), (E.PUMPKIN, 1)):
                for _ in range(n):
                    self.give(b)
            self.craft(RECIPES[0])
            self.craft(RECIPES[3])
            self.inventory = True
        if shots < len(marks) and self.at > marks[shots]:
            W, Hh = self.size
            data = self.ctx.screen.read(components=3)
            surf = pygame.image.frombytes(data, (W, Hh), "RGB", True)
            pygame.image.save(surf, os.path.join(AUTOTEST, f"shot{shots}.png"))
            self.shots = shots + 1
            print("shot", shots, "fps", self.fps, "pending", self.world.pending(), "meshes", len(self.world.meshes), flush=True)
        return self.at < 16.0

    def run(self):
        clock = pygame.time.Clock()
        # loading screen while numba compiles / caches
        self.render()
        pygame.display.flip()
        running = True
        fps_acc, fps_n = 0.0, 0
        while running:
            dt = min(clock.tick(144) / 1000.0, 0.05)
            fps_acc += dt
            fps_n += 1
            if fps_acc > 0.5:
                self.fps = fps_n / fps_acc
                fps_acc, fps_n = 0.0, 0
            running = self.handle_events()
            sz = pygame.display.get_window_size()
            if sz != self.size and sz[0] > 0 and sz[1] > 0:
                self.size = sz
            self.update(dt)
            self.render()
            if getattr(self, "want_shot", False):
                self.want_shot = False
                try:
                    W, Hh = self.size
                    folder = os.path.join(HERE, "screenshots")
                    os.makedirs(folder, exist_ok=True)
                    surf = pygame.image.frombytes(self.ctx.screen.read(components=3), (W, Hh), "RGB", True)
                    name = time.strftime("%Y-%m-%d_%H.%M.%S") + ".png"
                    pygame.image.save(surf, os.path.join(folder, name))
                    self.msg = "Saved screenshot " + name
                    self.msg_t = 2.5
                except Exception:
                    pass
            if AUTOTEST:
                running = self.autotest(dt) and running
            pygame.display.flip()
        self.save()
        self.world.pool.shutdown(wait=False, cancel_futures=True)
        pygame.quit()


def main():
    # warm up / compile the numba kernels before opening the window
    print("StelexCraft: preparing engine (first run compiles, ~30s)...", flush=True)
    perm = E.make_perm(1)
    c = E.gen_chunk(perm, 1, 0, 0)
    P = np.zeros((48, H, 48), np.uint8)
    P[16:32, :, 16:32] = c
    E.mesh_chunk(P)
    Game().run()


if __name__ == "__main__":
    main()
