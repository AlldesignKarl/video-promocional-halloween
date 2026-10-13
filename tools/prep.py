"""Prepara el material del anuncio a partir de las fotos de la tienda (assets/img).

    python3 tools/prep.py

Salida en build/prep:
  calavera/off-<color>.jpg   placa 1600×2844 de la calavera con flores con la base LED apagada
  calavera/on-burdeos.jpg    la misma placa con la luz encendida (foto real "con luz")
  calavera/matte.png         R = calavera + base, G = solo calavera, B = sombra suave
  calavera/bloom.jpg         resplandor de la luz (para el efecto de noche)
  calavera/noche.jpg         miniatura de la calavera encendida de noche (cierre)
  calabaza-glow.jpg          velas y purpurina de la calabaza (para el parpadeo)
  colgante-<color>.jpg       placa 2000×3033 del colgante con la puerta extendida hacia abajo
  niebla.png, luna.png       texturas generadas
  meta.json                  colores de las rosas, luces del colgante y medidas
Los recortes de la calavera se hacen con rembg (modelo isnet-general-use) y se guardan en build/matte.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as nd

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "assets" / "img"
OUT = ROOT / "build" / "prep"
MATTE = ROOT / "build" / "matte"
COLORS = ["negro", "burdeos", "azul-oscuro", "morado-oscuro", "rosa-oscuro"]
NIGHT_COLOR = "burdeos"

# placa de la calavera: la foto (1600×2000) con pared añadida arriba y mesa abajo hasta 9:16
PLATE_W, PLATE_H, TOP = 1600, 2844, 270


def load(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255


def save_jpg(a, p, q=93):
    Image.fromarray(np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8)).save(p, quality=q, subsampling=0)


def to_lin(a):
    return np.power(np.clip(a, 0, 1), 2.2)


def to_srgb(a):
    return np.power(np.clip(a, 0, 1), 1 / 2.2)


def blur(a, s):
    if a.ndim == 3:
        return np.stack([nd.gaussian_filter(a[..., c], s) for c in range(a.shape[2])], -1)
    return nd.gaussian_filter(a, s)


def mattes():
    MATTE.mkdir(parents=True, exist_ok=True)
    out = {}
    for kind in ("con-luz", "sin-luz"):
        p = MATTE / f"{kind}-{NIGHT_COLOR}-isnet.png"
        if not p.exists():
            from rembg import new_session, remove
            s = new_session("isnet-general-use")
            remove(Image.open(IMG / "calavera" / f"{kind}-{NIGHT_COLOR}.jpg").convert("RGB"), session=s, only_mask=True).save(p)
        m = np.asarray(Image.open(p)).astype(np.float32) / 255
        # fuera los restos sueltos (los conectores USB): solo las dos piezas grandes
        lab, n = nd.label(m > 0.5)
        sizes = nd.sum(np.ones_like(m), lab, range(1, n + 1))
        keep = np.isin(lab, 1 + np.argsort(sizes)[::-1][:2])
        keep = nd.binary_dilation(keep, iterations=6)
        out[kind] = m * keep
    return out["con-luz"], out["sin-luz"]


def fix_seam(img, matte):
    """Las fotos de la tienda son dos fotos unidas en x ≈ 800: el salto de tono del fondo se
    reparte en un degradado ancho (700–900) que no se nota."""
    left = img[:, 780:795].mean(1)
    right = img[:, 806:821].mean(1)
    d = np.stack([nd.gaussian_filter1d(right[:, c] - left[:, c], 12) for c in range(3)], -1)
    x = np.arange(img.shape[1], dtype=np.float32)
    sm = lambda a, b: np.clip((x - a) / (b - a), 0, 1) ** 2 * (3 - 2 * np.clip((x - a) / (b - a), 0, 1))
    corr = (sm(700, 900) - sm(796, 806))[None, :, None]
    bg = (1 - blur(matte, 2))[..., None]
    out = img + d[:, None, :] * corr * bg
    # la línea fina de la unión: se rellena interpolando entre las columnas de los lados
    a, b = 795, 809
    w = np.linspace(0, 1, b - a + 1)[None, :, None]
    fill = out[:, a:a + 1] * (1 - w) + out[:, b:b + 1] * w
    out[:, a:b + 1] = out[:, a:b + 1] * (1 - bg[:, a:b + 1]) + fill * bg[:, a:b + 1]
    return np.clip(out, 0, 1)


def extend_plate(src):
    """Coloca la foto en la placa 9:16: pared reflejada arriba y mesa limpia abajo."""
    h, w = src.shape[:2]
    plate = np.zeros((PLATE_H, PLATE_W, 3), np.float32)
    plate[TOP:TOP + h] = src
    # arriba: la pared reflejada y muy suavizada (la pared es lisa)
    top = src[1:TOP + 1][::-1]
    plate[:TOP] = blur(top, 6) * 0.5 + blur(top, 30) * 0.5
    # abajo: la mesa sin cables, a partir de las últimas filas (que están limpias)
    band = src[h - 90:h]
    rows = PLATE_H - (TOP + h)
    reps = np.concatenate([band if k % 2 == 0 else band[::-1] for k in range(rows // 90 + 2)], 0)[:rows]
    reps = blur(reps, 3) * 0.6 + blur(reps, 18) * 0.4
    # un poco más oscura hacia abajo, como la luz de estudio que cae
    reps *= (1 - 0.06 * np.linspace(0, 1, rows))[:, None, None]
    # costura suave
    plate[TOP + h:] = reps
    seam = 24
    a = np.linspace(0, 1, seam)[:, None, None]
    plate[TOP + h - seam:TOP + h] = plate[TOP + h - seam:TOP + h] * (1 - a) + reps[:1] * a
    return plate


def extend_mask(m):
    out = np.zeros((PLATE_H, PLATE_W), np.float32)
    out[TOP:TOP + m.shape[0]] = m
    return out


def calavera(meta):
    d = OUT / "calavera"
    d.mkdir(parents=True, exist_ok=True)
    m_on, m_sk = mattes()
    # calavera pegada sobre la base: por debajo del borde delantero de la base manda la base
    sk = blur(m_sk, 1.2)
    yy = np.arange(m_sk.shape[0])[:, None]
    # medida de cada calavera: centro, arriba, borde inferior
    lab, _ = nd.label(m_sk > 0.5)
    objs = [o for o in nd.find_objects(lab) if (o[0].stop - o[0].start) > 400]
    objs.sort(key=lambda o: o[1].start)
    skulls = []
    for o in objs:
        skulls.append({"x0": o[1].start, "x1": o[1].stop, "y0": o[0].start + TOP, "y1": o[0].stop + TOP,
                       "cx": (o[1].start + o[1].stop) / 2, "cy": (o[0].start + o[0].stop) / 2 + TOP})
    lab2, _ = nd.label(m_on > 0.5)
    objs2 = sorted([o for o in nd.find_objects(lab2) if (o[0].stop - o[0].start) > 400], key=lambda o: o[1].start)
    for s, o in zip(skulls, objs2):
        s["base_y1"] = o[0].stop + TOP
    meta["calavera"] = {"plate": [PLATE_W, PLATE_H], "top": TOP, "table_y": 1020 + TOP, "skulls": skulls}

    base = np.clip(m_on - m_sk, 0, 1)
    rose_cols = {}
    stack_on = {c: load(IMG / "calavera" / f"con-luz-{c}.jpg") for c in COLORS}
    mean_on = np.mean([stack_on[c] for c in COLORS], 0)
    for c in COLORS:
        on = fix_seam(stack_on[c], m_on)
        off_src = fix_seam(load(IMG / "calavera" / f"sin-luz-{c}.jpg"), m_sk)
        w = sk[..., None]
        off = on * (1 - w) + off_src * w
        # base de madera sin el brillo de los LED: se comprimen las luces altas de la base
        lum = off.mean(2)
        bmask = blur(base, 2)[..., None]
        ref = np.median(lum[base > 0.8])
        excess = np.clip(lum - ref, 0, None)
        k = np.where(lum > ref, (ref + excess * 0.25) / np.maximum(lum, 1e-3), 1.0)[..., None]
        warm = np.clip((off[..., 0] - off[..., 2]) * 2.5, 0, 1)[..., None]
        off = off * (1 - bmask) + off * k * bmask * (0.92 + 0.08 * (1 - warm))
        save_jpg(extend_plate(off), d / f"off-{c}.jpg")
        # color de las rosas: donde esta versión se separa de la media
        diff = np.abs(on - mean_on).sum(2)
        sel = (diff > 0.12) & (m_sk > 0.8)
        col = on[sel].mean(0) if sel.sum() > 500 else on[m_sk > 0.8].mean(0)
        # muestra algo más rica que la media (que mezcla sombras)
        rose_cols[c] = "#%02x%02x%02x" % tuple(int(v * 255) for v in np.clip(col * 1.08, 0, 1))
        if c == NIGHT_COLOR:
            save_jpg(extend_plate(on), d / f"on-{c}.jpg")
            on_plate = extend_plate(on)
    meta["calavera"]["roses"] = rose_cols

    M_on, M_sk = extend_mask(m_on), extend_mask(m_sk)
    base = np.clip(M_on - M_sk, 0, 1)
    shadow = blur(M_on, 22)
    rgb = np.stack([M_on, M_sk, shadow], -1)
    Image.fromarray(np.clip(rgb * 255 + 0.5, 0, 255).astype(np.uint8)).save(d / "matte.png")

    # resplandor: la luz que sale de la calavera encendida (en lineal), difuminada a varias escalas
    lin = to_lin(on_plate)
    yy = np.arange(PLATE_H)[:, None]
    lowness = np.zeros_like(M_sk)
    for s in skulls:
        t = np.clip((yy - s["y0"]) / (s["y1"] - s["y0"]), 0, 1)
        lowness = np.maximum(lowness, (t ** 1.5) * ((np.arange(PLATE_W)[None, :] >= s["x0"]) & (np.arange(PLATE_W)[None, :] < s["x1"])))
    emit = lin * (M_sk * (0.55 + 0.9 * lowness))[..., None] + lin * blur(base, 3)[..., None] * 0.35
    small = emit[::2, ::2]
    bloom = blur(small, 8) * 0.45 + blur(small, 28) * 0.35 + blur(small, 80) * 0.2
    bloom = bloom / max(bloom.max(), 1e-6)
    save_jpg(to_srgb(bloom), d / "bloom.jpg", 95)
    meta["calavera"]["bloom_max"] = 1.0

    # miniatura de noche (para el cierre): fondo azul noche, la pieza encendida y su halo
    s = skulls[1]
    x0, x1 = int(s["cx"] - 360), int(s["cx"] + 360)
    y0, y1 = int(s["y0"] - 170), int(s["y0"] - 170 + 980)
    amb = np.array([0.035, 0.045, 0.085])
    lit = lin * (M_sk * (1.05 + 0.6 * lowness))[..., None] * np.array([1.0, 0.9, 0.74])
    lit += lin * (M_on - M_sk).clip(0, 1)[..., None] * np.array([0.55, 0.42, 0.3])
    pool = np.exp(-(((np.arange(PLATE_W)[None, :] - s["cx"]) / 520) ** 2 + ((yy - s["cy"] - 120) / 620) ** 2))
    bg = to_lin(on_plate) * (1 - M_on)[..., None] * (amb + pool[..., None] * np.array([0.42, 0.26, 0.12]))
    big = np.repeat(np.repeat(bloom, 2, 0), 2, 1)[:PLATE_H, :PLATE_W]
    night = bg + lit + big * np.array([1.0, 0.75, 0.45]) * 0.55
    night = night[y0:y1, x0:x1]
    night = np.where(night < 0.85, night, 0.85 + 0.15 * (1 - np.exp(-(night - 0.85) / 0.15)))
    save_jpg(to_srgb(night), d / "noche.jpg")


def calabaza(meta):
    im = load(IMG / "calabaza-resina-flores.jpg")
    lum = im.mean(2)
    warm = np.clip((im[..., 0] - im[..., 2]) * 3, 0, 1)
    # velas y luces del fondo (arriba a la derecha) y destellos de la purpurina de cobre
    hi = np.clip((lum - 0.72) / 0.2, 0, 1) * warm
    hi = blur(hi, 3)
    glow = im * hi[..., None]
    glow = blur(glow, 2) * 0.6 + blur(glow, 14) * 0.6
    save_jpg(np.clip(glow * 1.2, 0, 1), OUT / "calabaza-glow.jpg")


def colgante(meta):
    W, H = 2000, 2500
    PH = 3033  # 1920 / 0.633: la foto queda arriba y la puerta sigue hacia abajo
    for c in ("blanco", "negro"):
        im = load(IMG / f"colgante-calavera-{c}.jpg")
        plate = np.zeros((PH, W, 3), np.float32)
        plate[:H] = im
        rows = PH - H
        last = im[H - 40:H].mean(0, keepdims=True)
        ext = np.repeat(last, rows, 0)
        ext = blur(ext, 10)
        ext *= (1 - 0.35 * np.linspace(0, 1, rows) ** 1.2)[:, None, None]
        plate[H:] = ext
        seam = 60
        a = np.linspace(0, 1, seam)[:, None, None]
        plate[H - seam:H] = plate[H - seam:H] * (1 - a) + ext[:1] * a
        save_jpg(plate, OUT / f"colgante-{c}.jpg")
    # lucecitas LED del aro: puntos muy brillantes y cálidos
    im = load(IMG / "colgante-calavera-blanco.jpg")
    lum = im.mean(2)
    warm = im[..., 0] - im[..., 2]
    cand = (lum > 0.8) & (warm > 0.12)
    lab, n = nd.label(cand)
    pts = []
    cx, cy, R = 1000, 1020, 720
    for i, sl in enumerate(nd.find_objects(lab)):
        a = (lab[sl] == i + 1).sum()
        if 30 < a < 4000:
            y = (sl[0].start + sl[0].stop) / 2
            x = (sl[1].start + sl[1].stop) / 2
            r = np.hypot(x - cx, y - cy)
            if 560 < r < 860:
                pts.append([round(x, 1), round(y, 1), int(a)])
    meta["colgante"] = {"plate": [W, PH], "leds": pts}


def ruido_tileable(w, h, beta, seed):
    rng = np.random.default_rng(seed)
    fx = np.fft.fftfreq(w)[None, :]
    fy = np.fft.fftfreq(h)[:, None]
    f = np.sqrt(fx ** 2 + fy ** 2)
    f[0, 0] = 1
    spec = (rng.standard_normal((h, w)) + 1j * rng.standard_normal((h, w))) / f ** beta
    spec[0, 0] = 0
    n = np.real(np.fft.ifft2(spec))
    return (n - n.min()) / (n.max() - n.min())


def niebla():
    # niebla/nubes: ruido 1/f suave y que se repite sin costuras en horizontal
    n = ruido_tileable(1024, 512, 1.75, 7)
    n = np.clip((n - 0.4) / 0.45, 0, 1) ** 1.3
    # se desvanece arriba y abajo (la repetición solo es horizontal)
    v = np.sin(np.linspace(0, np.pi, 512)) ** 1.2
    n = n * v[:, None]
    rgba = np.zeros((512, 1024, 4), np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = 205, 214, 235
    rgba[..., 3] = (n * 255).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(OUT / "niebla.png")


def luna():
    S = 560
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    c = S / 2
    r = np.hypot(xx - c, yy - c) / (S * 0.46)
    disk = np.clip((1 - r) * 140, 0, 1)
    mu = np.sqrt(np.clip(1 - r ** 2, 0, 1))
    limb = 0.62 + 0.38 * mu ** 0.5
    # mares: manchas grandes y suaves
    maria = nd.gaussian_filter(ruido_tileable(S, S, 1.9, 3), 10)
    maria = (maria - maria.min()) / (maria.max() - maria.min())
    tone = 1 - 0.30 * np.clip((maria - 0.52) / 0.18, 0, 1) ** 0.8
    # textura fina y algunos cráteres pequeños muy suaves
    fine = nd.gaussian_filter(ruido_tileable(S, S, 1.0, 5), 1.2)
    fine = (fine - fine.mean()) / fine.std()
    rng = np.random.default_rng(11)
    crat = np.zeros((S, S), np.float32)
    for _ in range(26):
        x, y = rng.uniform(0.2, 0.8, 2) * S
        rr = rng.uniform(2.5, 7)
        d = np.hypot(xx - x, yy - y) / rr
        crat += -0.035 * np.exp(-(d / 0.9) ** 4) + 0.03 * np.exp(-((d - 1.0) / 0.25) ** 2)
    # un cráter brillante con rayos (como Tycho)
    tx, ty = c + 0.18 * S, c + 0.27 * S
    d = np.hypot(xx - tx, yy - ty)
    ang = np.arctan2(yy - ty, xx - tx)
    rays = np.exp(-d / 70) * (0.5 + 0.5 * np.cos(ang * 9 + 1.3)) ** 6 * 0.025
    crat += 0.12 * np.exp(-(d / 6) ** 2) + rays
    lum = np.clip(limb * tone * (1 + crat) * (1 + fine * 0.025), 0, 1.15) * 0.97
    rgb = np.stack([lum * 1.0, lum * 0.975, lum * 0.92], -1)
    rgba = np.concatenate([np.clip(rgb, 0, 1), disk[..., None]], -1)
    Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), "RGBA").save(OUT / "luna.png")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {}
    calavera(meta)
    calabaza(meta)
    colgante(meta)
    niebla()
    luna()
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta)[:1500])
