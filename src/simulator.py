"""Spiral ring breaker: renders one vertical short (video + synthesized sound).

Every run picks a new seed, mode, palette, ring count and spiral shape.
Environment (optional): SEED, MODE=solo|duel, OUT_W (default 1080).
"""
import json, math, os, random, subprocess, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W = int(os.getenv("OUT_W") or 1080)
H = W * 16 // 9
FPS = 30
K = W / 1080  # every size below is designed for a 1080px wide frame

SEED = int(os.getenv("SEED") or random.SystemRandom().randrange(1, 2**31))
rng = random.Random(SEED)
nrng = np.random.default_rng(SEED)

MODE = os.getenv("MODE") or rng.choice(["solo", "duel"])
N = rng.randrange(260, 421, 10)
LIMIT = rng.choice([35, 40, 45])
TARGET = LIMIT * rng.uniform(0.74, 1.07)  # above 1.0 means the clock may win
TWIST = rng.choice([-1, 1]) * math.tau * rng.uniform(0.7, 2.2) / N
GAP = math.radians(rng.uniform(105, 145))
SPIN = rng.choice([-1, 1]) * rng.uniform(0.018, 0.032)

PALETTES = [
    # background centre, background edge, ring gradient
    ((22, 30, 66), (5, 6, 18), [(70, 230, 255), (150, 110, 255), (255, 90, 190)]),
    ((10, 46, 44), (2, 12, 16), [(190, 255, 110), (40, 230, 180), (60, 150, 255)]),
    ((58, 20, 44), (14, 4, 16), [(255, 214, 90), (255, 112, 80), (230, 60, 150)]),
    ((36, 24, 70), (8, 4, 22), [(255, 150, 220), (130, 140, 255), (90, 250, 220)]),
    ((16, 18, 24), (2, 2, 4), [(255, 255, 255), (130, 200, 255), (60, 90, 255)]),
]
BG_IN, BG_OUT, STOPS = rng.choice(PALETTES)
NAMES_COLORS = rng.choice([
    [("GOLD", (255, 200, 40)), ("CYAN", (40, 220, 255))],
    [("RED", (255, 70, 80)), ("GREEN", (60, 230, 110))],
    [("PINK", (255, 90, 200)), ("LIME", (180, 240, 50))],
])

CX, CY = W / 2, H / 2
SPACING = 11 * K
HALF_LINE = 3.0 * K
R_MIN = 170 * K
BALL_R = 26 * K
GRAVITY = 0.55 * K

# ---------------------------------------------------------------- static layers
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
RAD = np.hypot(xx - CX, yy - CY)
THETA = np.arctan2(yy - CY, xx - CX)
glow = np.clip(1 - RAD / (H * 0.55), 0, 1)[..., None] ** 1.4
BG = (np.array(BG_OUT, np.float32) + (np.array(BG_IN, np.float32) - BG_OUT) * glow)
for _ in range(220):  # faint star field
    x, y = rng.randrange(1, W - 1), rng.randrange(1, H - 1)
    BG[y - 1:y + 1, x - 1:x + 1] += rng.uniform(15, 70)
BG = np.clip(BG, 0, 255).astype(np.float32)

t = np.linspace(0, 1, N)
RING_COL = np.stack([np.interp(t, np.linspace(0, 1, len(STOPS)), [c[i] for c in STOPS])
                     for i in range(3)], axis=1).astype(np.float32)


def font(size):
    for p in ("/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, max(8, int(size * K)))
    raise RuntimeError("No usable font found; install fonts-dejavu-core.")


F_HOOK, F_TIME, F_COUNT, F_SCORE, F_END = (font(s) for s in (58, 78, 44, 46, 104))


# ---------------------------------------------------------------- simulation
class Ball:
    def __init__(self, i, name, color):
        a = rng.uniform(0, math.tau)
        side = (i - 0.5) * 2 * BALL_R * 1.3 if MODE == "duel" else 0.0
        self.p = np.array([CX + side, CY - 20 * K])
        self.v = np.array([math.cos(a), math.sin(a)]) * 12 * K
        self.name, self.color = name, color
        self.score, self.cool, self.trail = 0, 0, []


balls = ([Ball(0, *NAMES_COLORS[0]), Ball(1, *NAMES_COLORS[1])] if MODE == "duel"
         else [Ball(0, "BALL", (255, 255, 255))])

first = 0           # innermost ring still alive
r_in = R_MIN        # its radius
rot = rng.uniform(0, math.tau)
debris = np.zeros((0, 8), np.float32)  # x, y, vx, vy, life, r, g, b
sounds = []         # (time, kind, value)
finished_at = timed_out_at = None


def wrap(a):
    return (a + math.pi) % math.tau - math.pi


def shatter(start, count):
    """Turn rings [start, start+count) into dust that keeps their shape."""
    global debris
    per = max(40, min(260, 3200 // count))
    parts = []
    for k in range(start, start + count):
        radius = r_in + (k - start) * SPACING
        centre = rot + k * TWIST
        ang = centre + GAP / 2 + nrng.random(per) * (math.tau - GAP)
        x, y = CX + radius * np.cos(ang), CY + radius * np.sin(ang)
        push = nrng.uniform(0.5, 5.0, per) * K
        vx = np.cos(ang) * push + nrng.normal(0, 1.2 * K, per)
        vy = np.sin(ang) * push + nrng.normal(0, 1.2 * K, per) - 1.5 * K
        life = nrng.uniform(25, 75, per)
        col = np.tile(RING_COL[k], (per, 1))
        parts.append(np.column_stack([x, y, vx, vy, life, col]))
    debris = np.vstack([debris, *parts]).astype(np.float32)[-14000:]


def step(now):
    global first, r_in, rot, debris, finished_at
    rot += SPIN
    sub = 5
    for b in balls:
        b.cool = max(0, b.cool - 1)
    for _ in range(sub):
        for b in balls:
            b.v[1] += GRAVITY / sub
            b.p += b.v / sub
            if first >= N:
                continue
            d = b.p - (CX, CY)
            dist = float(np.hypot(*d))
            if dist + BALL_R < r_in - HALF_LINE or dist == 0:
                continue
            n = d / dist
            outward = float(b.v @ n)
            ang = math.atan2(d[1], d[0])
            in_gap = abs(wrap(ang - rot - first * TWIST)) < GAP / 2
            if in_gap and b.cool == 0 and outward > 0:
                # Pace the run: break more rings when behind the target time.
                left = max(TARGET - now, 1.5)
                hits_left = max(left * 1.15, 1)
                burst = (N - first) / hits_left * rng.uniform(0.55, 1.6)
                burst = int(min(max(burst, 3), 48, N - first))
                if now > TARGET - 1.5 and TARGET <= LIMIT:
                    burst = N - first if N - first < 60 else max(burst, 30)
                shatter(first, burst)
                first += burst
                r_in += burst * SPACING
                b.score += burst
                b.cool = 9
                sounds.append((now, "break", burst))
                if first >= N:
                    finished_at = now
                    continue
            # bounce back inside, with a little chaos so paths never repeat
            if outward > 0:
                b.v -= 2 * outward * n
                jitter = rng.uniform(-0.45, 0.45)
                c, s = math.cos(jitter), math.sin(jitter)
                b.v = np.array([c * b.v[0] - s * b.v[1], s * b.v[0] + c * b.v[1]])
                if float(b.v @ n) > 0:
                    b.v -= 2 * float(b.v @ n) * n
                speed = rng.uniform(15, 25) * K
                b.v *= speed / max(float(np.hypot(*b.v)), 1e-6)
                if not sounds or now - sounds[-1][0] > 0.07:
                    sounds.append((now, "bounce", first / N))
            b.p = np.array([CX, CY]) + n * (r_in - HALF_LINE - BALL_R - 0.5)
        if len(balls) == 2:
            a, b = balls
            d = b.p - a.p
            dist = float(np.hypot(*d))
            if 0 < dist < 2 * BALL_R:
                n = d / dist
                rel = float((b.v - a.v) @ n)
                if rel < 0:
                    a.v += rel * n
                    b.v -= rel * n
                push = (2 * BALL_R - dist) / 2
                a.p -= n * push
                b.p += n * push
    # the whole spiral keeps closing in around the balls
    r_in += (R_MIN - r_in) * 0.022
    for b in balls:
        b.trail = (b.trail + [tuple(b.p)])[-14:]
    if len(debris):
        debris[:, 0:2] += debris[:, 2:4]
        debris[:, 2] *= 0.975
        debris[:, 3] = debris[:, 3] * 0.975 + 0.35 * K
        debris[:, 4] -= 1
        debris = debris[debris[:, 4] > 0]


# ---------------------------------------------------------------- drawing
def draw_rings(img):
    if first >= N:
        return
    u = (RAD - r_in) / SPACING
    near = np.rint(u)
    mask = (near >= 0) & (near < N - first)
    dist = np.abs(u[mask] - near[mask]) * SPACING
    cover = np.clip(HALF_LINE + 0.5 - dist, 0, 1)
    k = near[mask].astype(np.int32) + first
    off = np.abs(wrap(THETA[mask] - np.float32(rot % math.tau) - k * np.float32(TWIST)))
    cover *= np.clip((off - np.float32(GAP / 2)) * RAD[mask] + 0.5, 0, 1)
    under = img[mask]
    img[mask] = under + (RING_COL[k] - under) * cover[:, None]


def stamp(img, x, y, radius, color, alpha=1.0, soft=1.0):
    x0, x1 = max(int(x - radius - soft), 0), min(int(x + radius + soft) + 2, W)
    y0, y1 = max(int(y - radius - soft), 0), min(int(y + radius + soft) + 2, H)
    if x0 >= x1 or y0 >= y1:
        return
    d = np.hypot(xx[y0:y1, x0:x1] - x, yy[y0:y1, x0:x1] - y)
    a = np.clip((radius + soft - d) / soft, 0, 1)[..., None] * alpha
    region = img[y0:y1, x0:x1]
    region += (np.array(color, np.float32) - region) * a


def draw_debris(img):
    if not len(debris):
        return
    x = debris[:, 0].astype(np.int32)
    y = debris[:, 1].astype(np.int32)
    size = max(2, int(4 * K))
    ok = (x >= 0) & (x < W - size) & (y >= 0) & (y < H - size)
    x, y, col = x[ok], y[ok], debris[ok, 5:8]
    for dx in range(size):
        for dy in range(size):
            img[y + dy, x + dx] = col


def label(d, xy, text, f, fill=(255, 255, 255)):
    d.text(xy, text, font=f, fill=fill, anchor="mm",
           stroke_width=max(2, int(7 * K)), stroke_fill=(0, 0, 0))


def render(now):
    img = BG.copy()
    draw_rings(img)
    draw_debris(img)
    for b in balls:
        for i, (x, y) in enumerate(b.trail[:-1]):
            f = (i + 1) / len(b.trail)
            stamp(img, x, y, BALL_R * f * 0.85, b.color, alpha=0.45 * f)
        x, y = b.p
        stamp(img, x, y, BALL_R, b.color, alpha=0.35, soft=22 * K)
        stamp(img, x, y, BALL_R, (10, 10, 18))
        stamp(img, x, y, BALL_R - 5 * K, b.color)
        stamp(img, x - 7 * K, y - 8 * K, 6 * K, (255, 255, 255), alpha=0.9)
    frame = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    # dark plate keeps the headline readable on top of the rings
    d = ImageDraw.Draw(frame, "RGBA")
    d.rounded_rectangle((70 * K, 180 * K, W - 70 * K, (380 if MODE == "duel" else 280) * K),
                        radius=36 * K, fill=(0, 0, 0, 175))
    clock = LIMIT - min(now, finished_at if finished_at is not None else now)
    label(d, (CX, CY - 24 * K), f"{max(0, math.ceil(clock))}s", F_TIME)
    label(d, (CX, CY + 48 * K), str(N - first), F_COUNT, (225, 225, 235))
    hook = "WHICH BALL BREAKS MORE?" if MODE == "duel" else f"CAN IT BREAK {N} RINGS?"
    label(d, (CX, 230 * K), hook, F_HOOK)
    if MODE == "duel":
        for i, b in enumerate(balls):
            label(d, (W * (0.28 if i == 0 else 0.72), 330 * K),
                  f"{b.name} {b.score}", F_SCORE, b.color)
    end = finished_at if finished_at is not None else timed_out_at
    if end is not None and now - end > 0.5:
        text, color = result()
        label(d, (CX, CY + 430 * K), text, F_END, color)
    return frame


def result():
    if MODE == "duel":
        a, b = balls
        if a.score == b.score:
            return "IT'S A TIE!", (255, 255, 255)
        w = a if a.score > b.score else b
        return f"{w.name} WINS!", w.color
    if finished_at is not None:
        return "ESCAPED!", (120, 255, 160)
    return "TIME'S UP!", (255, 100, 100)


# ---------------------------------------------------------------- audio
def synth(total):
    sr = 44100
    out = np.zeros(int(total * sr) + sr, np.float32)
    scale = [0, 2, 4, 7, 9]
    root = rng.choice([196.0, 220.0, 246.94, 261.63])

    def tone(at, freq, length, vol, decay):
        i = int(at * sr)
        x = np.arange(int(length * sr)) / sr
        w = np.sin(math.tau * freq * x) + 0.3 * np.sin(math.tau * 2.01 * freq * x)
        env = np.exp(-x * decay) * np.minimum(1, x * 400)
        out[i:i + len(x)] += (w * env * vol).astype(np.float32)[: len(out) - i]

    note = 0
    for at, kind, value in sounds:
        if kind == "bounce":
            step_ = scale[note % 5] + 12 * ((note // 5) % 2)
            tone(at, root * 2 ** (step_ / 12), 0.35, 0.22, 11)
            note += 1
        else:
            for j in range(min(7, 2 + value // 7)):
                st = scale[j % 5] + 12 * (1 + j // 5)
                tone(at + j * 0.028, root * 2 ** (st / 12), 0.28, 0.13, 14)
            i = int(at * sr)
            n = int(0.18 * sr)
            noise = np.diff(nrng.random(n + 1) - 0.5) * np.exp(-np.arange(n) / sr * 24)
            out[i:i + n] += (noise * 0.18).astype(np.float32)[: len(out) - i]
    end = finished_at if finished_at is not None else timed_out_at
    for j, st in enumerate([0, 4, 7, 12]):
        tone(end + 0.5 + j * 0.09, root * 2 ** (st / 12), 1.4, 0.2, 2.8)
    out = out[: int(total * sr)]
    peak = float(np.max(np.abs(out))) or 1.0
    return (out / peak * 0.85 * 32767).astype("<i2"), sr


# ---------------------------------------------------------------- main
def metadata(seconds):
    if MODE == "duel":
        a, b = balls[0].name.title(), balls[1].name.title()
        titles = [f"{a} vs {b}: who breaks more of {N} rings? 👀",
                  f"{N} rings, 2 balls. Pick {a} or {b}!",
                  f"{a} or {b}? {LIMIT} seconds to decide 🔥"]
        ask = f"Comment {a} or {b} before the end!"
    else:
        titles = [f"Can the ball break {N} rings in {LIMIT}s? 👀",
                  f"{N} spiral rings vs 1 ball 🔥",
                  f"{LIMIT} seconds. {N} rings. Will it escape?"]
        ask = "Will it make it? Guess before the end!"
    return {
        "title": f"{rng.choice(titles)} #shorts",
        "description": f"{ask}\n\nAn original physics simulation.\n#shorts #satisfying #physics #simulation",
        "tags": ["satisfying", "physics", "simulation", "bouncing ball", "shorts"],
        "mode": MODE, "rings": N, "limit": LIMIT, "seed": SEED,
        "duration_seconds": round(seconds, 2), "width": W, "height": H, "fps": FPS,
    }


def main():
    global timed_out_at
    raw = "raw_video.mp4"
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264",
         "-preset", "veryfast", "-crf", "21", "-maxrate", "14M", "-bufsize", "28M",
         "-pix_fmt", "yuv420p", raw], stdin=subprocess.PIPE)
    frame = 0
    while True:
        now = frame / FPS
        end = finished_at if finished_at is not None else timed_out_at
        if end is not None and now - end >= 3.0:
            break
        if timed_out_at is None:
            step(now)
        if finished_at is None and timed_out_at is None and now >= LIMIT:
            timed_out_at = now
        proc.stdin.write(render(now).tobytes())
        frame += 1
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("FFmpeg encoding failed")
    seconds = frame / FPS
    pcm, sr = synth(seconds)
    with wave.open("audio.wav", "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-i", "audio.wav",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", "output.mp4"], check=True)
    Path(raw).unlink(missing_ok=True)
    meta = metadata(seconds)
    Path("metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated output.mp4 seed={SEED} mode={MODE} rings={N} left={N - first} "
          f"seconds={seconds:.1f} result={result()[0]}")


if __name__ == "__main__":
    main()
