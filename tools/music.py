"""Banda sonora original del anuncio de Halloween (sintetizada desde cero, sin derechos de terceros).

Re menor, 100 BPM (1 pulso = 0,6 s; compás de 2,4 s). Caja de música al empezar, una campanita por
cada color de las rosas, un reloj que se acelera mientras cae la noche, el clic del interruptor y el
golpe cálido cuando se enciende la calavera, aleteo de murciélagos, el golpe del 10 %, la tienda que
se dibuja y enciende sus luces (mayoristas) y el cierre.

Uso: python3 tools/music.py build/audio/musica.f32   (float32 estéreo intercalado, 48 kHz)
"""
import sys
import numpy as np

try:
    from scipy.signal import lfilter
except ImportError:  # sin scipy funciona igual, solo más lento
    lfilter = None

SR = 48000
T_SHOP = 15.35  # se encienden las luces de la tienda
DUR = 20.0
BEAT = 0.6
N = int(SR * (DUR + 0.2))
rng = np.random.default_rng(1031)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def t_axis(n):
    return np.arange(n) / SR


def place(buf, sig, t0, gain=1.0, pan=0.0):
    """Suma una señal mono o estéreo en el instante t0 (s) con panorama -1..1."""
    i = int(round(t0 * SR))
    if sig.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        sig = np.stack([sig * l * 1.4142, sig * r * 1.4142], 1)
    if i < 0:
        sig, i = sig[-i:], 0
    j = min(len(buf), i + len(sig))
    if j > i:
        buf[i:j] += sig[: j - i] * gain


def env_adsr(n, a, d, s, r, hold):
    t = t_axis(n)
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    rel = np.clip((t - hold) / max(r, 1e-4), 0, 1)
    return e * (1 - rel) ** 2


def onepole_lp(x, fc):
    """Paso bajo de un polo (fc puede variar en el tiempo)."""
    if np.isscalar(fc) and lfilter is not None:
        a = np.exp(-2 * np.pi * fc / SR)
        return lfilter([1 - a], [1, -a], x, axis=0)
    fc = np.broadcast_to(np.asarray(fc, dtype=float), x.shape[:1])
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    z = np.zeros(x.shape[1:]) if x.ndim > 1 else 0.0
    for i in range(len(x)):
        z = (1 - a[i]) * x[i] + a[i] * z
        y[i] = z
    return y


def stft_filter(x, gain_fn, nfft=2048, hop=512):
    """Filtra ruido con una ganancia que depende del tiempo y la frecuencia (para barridos)."""
    win = np.hanning(nfft)
    out = np.zeros(len(x) + nfft)
    norm = np.zeros(len(x) + nfft)
    freqs = np.fft.rfftfreq(nfft, 1 / SR)
    for start in range(0, len(x) - 1, hop):
        seg = x[start:start + nfft]
        if len(seg) < nfft:
            seg = np.pad(seg, (0, nfft - len(seg)))
        spec = np.fft.rfft(seg * win) * gain_fn((start + nfft / 2) / SR, freqs)
        out[start:start + nfft] += np.fft.irfft(spec) * win
        norm[start:start + nfft] += win ** 2
    return (out / np.maximum(norm, 1e-3))[: len(x)]


# ---------------------------------------------------------------- instrumentos
def bell(f, dur=1.6, bright=1.0):
    """Campanita FM (celesta) para las notas de los colores."""
    n = int(dur * SR)
    t = t_axis(n)
    idx = (2.2 * bright) * np.exp(-t / 0.18) + 0.25
    mod = np.sin(2 * np.pi * f * 3.5 * t) * idx
    car = np.sin(2 * np.pi * f * t + mod)
    car += 0.35 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t / 0.25)
    e = (1 - np.exp(-t / 0.002)) * np.exp(-t / 0.55)
    return car * e


def epiano(f, dur=0.9, vel=1.0):
    n = int(dur * SR)
    t = t_axis(n)
    idx = 1.6 * vel * np.exp(-t / 0.12) + 0.35
    car = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t))
    car += 0.2 * np.sin(2 * np.pi * f * 4.0 * t) * np.exp(-t / 0.05) * vel
    e = (1 - np.exp(-t / 0.003)) * np.exp(-t / 0.42)
    return car * e * vel


def pad(notes, t0, t1, bright, attack=0.5, release=0.9):
    """Colchón de cuerdas sintéticas: dientes de sierra desafinados con filtro que varía."""
    n = int((t1 - t0 + release) * SR)
    t = t_axis(n)
    out = np.zeros((n, 2))
    fc = bright(t + t0) if callable(bright) else np.full(n, bright)
    e = env_adsr(n, attack, 1.0, 1.0, release, t1 - t0)
    for m in notes:
        f0 = mtof(m)
        for det, pan in ((-0.09, -0.7), (0.0, 0.0), (0.085, 0.7)):
            f = f0 * 2 ** (det / 12)
            ph = rng.random() * 6.28
            sig = np.zeros(n)
            for k in range(1, 40):
                if k * f > 9000:
                    break
                amp = (1 / k) / np.sqrt(1 + (k * f / fc) ** 4)
                sig += amp * np.sin(2 * np.pi * k * f * t + ph * k)
            l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
            out[:, 0] += sig * l
            out[:, 1] += sig * r
    return out * e[:, None] / (len(notes) * 2.2)


def bass(f, dur, vel=1.0):
    n = int(dur * SR)
    t = t_axis(n)
    sig = np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * 2 * f * t) + 0.18 * np.sin(2 * np.pi * 3 * f * t)
    e = (1 - np.exp(-t / 0.004)) * np.exp(-t / 0.9) * np.clip((dur - t) / 0.05, 0, 1)
    return np.tanh(sig * 1.3) * e * vel


def kick(vel=1.0):
    n = int(0.5 * SR)
    t = t_axis(n)
    f = 52 + 120 * np.exp(-t / 0.03)
    ph = 2 * np.pi * np.cumsum(f) / SR
    sig = np.sin(ph) * np.exp(-t / 0.24)
    click = rng.standard_normal(n) * np.exp(-t / 0.002) * 0.25
    return np.tanh((sig + click) * 1.5) * vel


def snap(vel=1.0):
    n = int(0.35 * SR)
    t = t_axis(n)
    noise = rng.standard_normal(n)
    bp = onepole_lp(noise, 4200) - onepole_lp(noise, 900)
    e = np.zeros(n)
    for d in (0.0, 0.011, 0.022):
        e += np.where(t >= d, np.exp(-(t - d) / (0.012 if d < 0.02 else 0.11)), 0)
    return bp * e * 2.2 * vel


def hat(vel=1.0, dec=0.035):
    n = int(0.2 * SR)
    t = t_axis(n)
    noise = rng.standard_normal(n)
    hp = noise - onepole_lp(noise, 7000)
    return hp * np.exp(-t / dec) * vel


def tick(f=2200, vel=1.0):
    n = int(0.08 * SR)
    t = t_axis(n)
    return (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.012) + 0.3 * rng.standard_normal(n) * np.exp(-t / 0.003)) * vel


def whoosh(dur, f0, f1, peak=0.6, width=0.6):
    """Ráfaga de aire con un filtro de banda que barre de f0 a f1."""
    n = int(dur * SR)
    noise = rng.standard_normal(n)

    def g(tt, fr):
        x = np.clip(tt / dur, 0, 1)
        fc = f0 * (f1 / f0) ** x
        return np.exp(-0.5 * (np.log2(np.maximum(fr, 20) / fc) / width) ** 2)

    sig = stft_filter(noise, g)
    t = t_axis(n)
    x = t / dur
    e = np.where(x < peak, (x / peak) ** 2, np.exp(-(x - peak) / (1 - peak) * 4))
    pan = np.sin(np.pi * (x - 0.5)) * 0.8
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    return np.stack([sig * e * l, sig * e * r], 1) * 1.4


def boom(dur=2.4, vel=1.0):
    n = int(dur * SR)
    t = t_axis(n)
    f = 34 + 60 * np.exp(-t / 0.08)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.55)
    noise = rng.standard_normal(n)
    thump = onepole_lp(noise, 300) * np.exp(-t / 0.18) * 3
    air = (noise - onepole_lp(noise, 3000)) * np.exp(-t / 0.5) * 0.25
    return np.tanh((sub * 1.2 + thump + air) * 1.2) * vel


def riser(dur):
    n = int(dur * SR)
    t = t_axis(n)
    x = t / dur
    noise = rng.standard_normal(n)
    sig = stft_filter(noise, lambda tt, fr: np.exp(-0.5 * (np.log2(np.maximum(fr, 20) / (400 * 20 ** np.clip(tt / dur, 0, 1))) / 0.9) ** 2))
    tone = np.sin(2 * np.pi * np.cumsum(220 * 4 ** x) / SR) * 0.25
    return (sig * 0.9 + tone) * x ** 2.2


def reverb_ir(seconds=2.6, predelay=0.02):
    n = int(seconds * SR)
    t = t_axis(n)
    ir = np.zeros((n, 2))
    for c in range(2):
        noise = rng.standard_normal(n)
        # más oscuro cuanto más tarde (como una sala real)
        dark = onepole_lp(noise, 2500)
        bright_mix = np.exp(-t / 0.35)
        ir[:, c] = (noise * bright_mix + dark * (1 - bright_mix) * 1.6) * np.exp(-t / (seconds / 6.2))
    ir[: int(predelay * SR)] = 0
    return ir / np.sqrt((ir ** 2).sum(0, keepdims=True)) * 0.9


def convolve(x, ir):
    n = len(x) + len(ir)
    size = 1 << (n - 1).bit_length()
    out = np.zeros((len(x), 2))
    for c in range(2):
        X = np.fft.rfft(x[:, c], size)
        H = np.fft.rfft(ir[:, c], size)
        out[:, c] = np.fft.irfft(X * H, size)[: len(x)]
    return out


def musicbox(f, dur=2.2, vel=1.0):
    """Caja de música: parciales inarmónicos de una púa metálica, ataque seco y cola larga."""
    n = int(dur * SR)
    t = t_axis(n)
    sig = np.zeros(n)
    for ratio, amp, dec in ((1.0, 1.0, 0.9), (2.0, 0.28, 0.35), (3.01, 0.12, 0.18), (4.17, 0.16, 0.12), (6.3, 0.06, 0.06)):
        if f * ratio < 16000:
            sig += amp * np.sin(2 * np.pi * f * ratio * t + rng.random() * 6.28) * np.exp(-t / dec)
    click = rng.standard_normal(n) * np.exp(-t / 0.0015) * 0.15
    e = 1 - np.exp(-t / 0.0015)
    return (sig * e + click) * vel


def pluck(f, dur=0.8, vel=1.0, bright=0.6):
    """Pizzicato de cuerda (Karplus-Strong sencillo)."""
    n = int(dur * SR)
    period = max(2, int(SR / f))
    buf = rng.uniform(-1, 1, period)
    buf = onepole_lp(buf, 1500 + 5000 * bright)
    out = np.zeros(n)
    for i in range(n):
        j = i % period
        out[i] = buf[j]
        buf[j] = 0.497 * (buf[j] + buf[(j + 1) % period])
    return out * vel * np.clip((dur - t_axis(n)) / 0.05, 0, 1)


def choir(notes, t0, t1, attack=0.6, release=1.2, vowel=(700, 1150, 2600)):
    """Coro sintético: dientes de sierra con vibrato filtrados por formantes (vocal "a")."""
    n = int((t1 - t0 + release) * SR)
    t = t_axis(n)
    out = np.zeros((n, 2))
    e = env_adsr(n, attack, 1.0, 1.0, release, t1 - t0)
    for m in notes:
        f0 = mtof(m)
        for det, pan in ((-0.07, -0.6), (0.06, 0.6)):
            vib = 1 + 0.004 * np.sin(2 * np.pi * (5.1 + det * 4) * t + rng.random() * 6)
            ph = 2 * np.pi * np.cumsum(f0 * 2 ** (det / 12) * vib) / SR
            sig = np.zeros(n)
            for k in range(1, 28):
                fk = k * f0
                if fk > 7000:
                    break
                g = sum(a * np.exp(-0.5 * ((fk - fc) / bw) ** 2) for fc, bw, a in zip(vowel, (110, 140, 220), (1.0, 0.55, 0.25)))
                sig += (g + 0.02) / k ** 0.5 * np.sin(k * ph)
            l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
            out[:, 0] += sig * l
            out[:, 1] += sig * r
    return out * e[:, None] / (len(notes) * 3)


def drone(f, dur, vel=1.0):
    n = int(dur * SR)
    t = t_axis(n)
    sig = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.501 * t) + 0.3 * np.sin(2 * np.pi * f * 2.003 * t)
    e = np.clip(t / 0.8, 0, 1) * np.clip((dur - t) / 0.6, 0, 1)
    return sig * e * vel * (0.8 + 0.2 * np.sin(2 * np.pi * 0.35 * t))


def wind(dur, vel=1.0):
    n = int(dur * SR)
    out = np.zeros((n, 2))
    for c in range(2):
        noise = rng.standard_normal(n)
        sig = stft_filter(noise, lambda tt, fr: np.exp(-0.5 * (np.log2(np.maximum(fr, 20) / (500 * 2 ** (0.9 * np.sin(tt * 1.3 + c)))) / 0.5) ** 2))
        out[:, c] = sig
    t = t_axis(n)
    e = np.clip(t / (dur * 0.4), 0, 1) ** 1.5 * np.clip((dur - t) / 0.4, 0, 1)
    return out * e[:, None] * vel


def switch_click(vel=1.0):
    n = int(0.12 * SR)
    t = t_axis(n)
    hi = rng.standard_normal(n)
    hi = hi - onepole_lp(hi, 3000)
    body = np.sin(2 * np.pi * 1100 * t) * np.exp(-t / 0.006) + 0.6 * np.sin(2 * np.pi * 180 * t) * np.exp(-t / 0.012)
    return (hi * np.exp(-t / 0.0025) * 0.9 + body * 0.6) * vel


def flutter(dur, rate, vel=1.0):
    """Aleteo de un murciélago: ráfagas cortas de aire a 'rate' aletazos por segundo."""
    n = int(dur * SR)
    t = t_axis(n)
    noise = rng.standard_normal(n)
    bp = onepole_lp(noise, 1400) - onepole_lp(noise, 250)
    ph = (t * rate) % 1.0
    flap = np.exp(-ph / 0.09) * (1 + 0.3 * rng.random())
    e = np.sin(np.pi * np.clip(t / dur, 0, 1))
    return bp * flap * e * vel * 2.0


# ---------------------------------------------------------------- partitura
def compose():
    dry = np.zeros((N, 2))      # percusión y efectos secos
    send = np.zeros((N, 2))     # lo que pasa por la reverb
    pads = np.zeros((N, 2))
    bassb = np.zeros((N, 2))
    kicks = []

    # --- armonía (re menor) ---------------------------------------------------
    # (inicio, fin, voicing del colchón, bajo)
    CH = [
        (0.0, 2.4, [50, 57, 62, 64, 65], 38),     # Dm(add9)
        (2.4, 4.8, [46, 53, 57, 62, 65], 34),     # Bbmaj7
        (4.8, 5.95, [43, 50, 55, 58, 62], 31),    # Gm9
        (5.95, 8.4, [45, 52, 55, 61, 62], 33),    # A7sus → la noche
        (8.4, 10.5, [46, 53, 60, 62, 65, 69], 34),  # Bbmaj9: se enciende
        (10.5, 12.15, [43, 50, 57, 58, 62], 31),  # Gm9: colgante
        (12.15, 12.6, [45, 52, 55, 61, 64], 33),  # A7: murciélagos
        (12.6, 13.8, [50, 57, 60, 64, 65], 38),   # Dm9: 10 %
        (13.8, 14.4, [46, 53, 57, 62, 65], 34),   # Bbmaj7
        (14.4, 15.35, [43, 50, 55, 58, 62], 31),  # Gm9: ¿tienes una tienda?
        (15.35, 16.5, [46, 53, 60, 62, 65, 69], 34),  # Bbmaj9: se encienden las luces de la tienda
        (16.5, 17.4, [43, 50, 55, 58, 62], 31),   # Gm9: cierre
        (17.4, 18.0, [45, 52, 57, 61, 64], 33),   # A7
        (18.0, DUR - 0.2, [50, 57, 62, 65, 69, 64], 38),  # Dm(add9) final
    ]

    def bright_curve(tt):
        fc = 1200 + 2400 * np.clip(tt / 2.4, 0, 1)
        fc = np.where((tt > 5.95) & (tt < 8.4), 3600 * np.clip(1 - (tt - 5.95) / 1.6, 0.14, 1), fc)
        fc = np.where(tt >= 8.4, 4200 + 2000 * np.exp(-(tt - 8.4) / 0.8), fc)
        fc = np.where(tt >= 10.5, 3400, fc)
        return fc

    for i, (t0, t1, v, _) in enumerate(CH):
        p = pad(v, t0, t1, bright_curve, attack=1.0 if i == 0 else 0.2, release=1.8 if i == len(CH) - 1 else 0.5)
        place(pads, p, t0, gain=0.42)

    # --- intro: caja de música (motivo en re menor) -----------------------------
    intro = [69, 74, 77, 76, 74, 73, 74, 69]
    for k, m in enumerate(intro):
        tt = 0.3 + k * BEAT / 2
        place(send, musicbox(mtof(m + 12), 2.4, 0.9), tt, gain=0.17, pan=-0.3 + 0.08 * k)
    for k, m in enumerate([62, 57]):                       # pizzicatos graves
        place(send, pluck(mtof(m - 12), 0.9, 0.9), 0.3 + k * BEAT * 2, gain=0.22)
    place(send, pluck(mtof(58 - 12), 0.9, 0.9), 2.4, gain=0.22)
    place(send, whoosh(1.2, 300, 3000, 0.8, 0.8), 0.0, gain=0.05)       # aire al abrir
    place(send, bell(mtof(86), 2.0, 0.5), 0.75, gain=0.07)               # "Halloween" se escribe

    # --- barrido a la calavera ------------------------------------------------
    place(dry, whoosh(0.7, 400, 4500, 0.55, 0.7), 2.66, gain=0.22)
    place(send, whoosh(0.5, 3000, 600, 0.3, 0.8), 3.0, gain=0.08)

    # --- ritmo suave (100 BPM) --------------------------------------------------
    def groove(t_from, t_to, half=False, vel=1.0, off=0.0):
        k0, k1 = int(round((t_from - off) / BEAT)), int(round((t_to - off) / BEAT))
        for k in range(k0, k1):
            tb = off + k * BEAT
            bb = k % 4
            if bb == 0 or (bb == 2 and not half):
                place(dry, kick(0.9 * vel if bb == 0 else 0.75 * vel), tb, gain=0.55)
                kicks.append(tb)
            if (bb in (1, 3) and not half) or (half and bb == 2):
                place(send, snap(0.7 * vel), tb, gain=0.3, pan=0.05)
                place(dry, snap(0.7 * vel), tb, gain=0.22)
            place(dry, hat(0.45 * vel), tb + BEAT / 2, gain=0.12, pan=0.35)
            place(dry, hat(0.2 * vel, 0.02), tb + BEAT * 0.75, gain=0.07, pan=-0.3)

    groove(3.0, 5.95)
    groove(9.0, 10.2, half=True, vel=0.8)
    groove(10.8, 12.0, half=True, vel=0.8)
    groove(12.6, 14.4)
    groove(15.35, 16.2, half=True, vel=0.7, off=0.35)
    groove(16.5, 18.0, half=True, vel=0.8, off=0.3)

    # --- bajo -------------------------------------------------------------------
    for t0, t1, _, root in CH:
        if t0 < 2.4 or 5.95 <= t0 < 8.4 or t0 >= 18.0:
            continue
        k = 0
        tt = t0
        while tt < t1 - 0.05:
            ln = min(BEAT * (1.5 if k % 3 == 0 else 1.0), t1 - tt)
            place(bassb, bass(mtof(root + (12 if k % 3 == 2 else 0)), ln, 0.8), tt, gain=0.5)
            tt += ln
            k += 1
    place(bassb, bass(mtof(38), 1.8, 0.85), 18.0, gain=0.55)

    # --- colores de las rosas: un toque y una campanita por cambio ---------------
    place(send, bell(mtof(77), 1.6, 0.8), 3.0, gain=0.16)
    for k, (tt, m) in enumerate(zip([3.6, 4.2, 4.8, 5.4], [81, 84, 86, 89])):
        place(dry, tick(2300, 0.7), tt - 0.12, gain=0.1)                      # toque en la muestra
        place(send, bell(mtof(m), 1.8, 1.0), tt, gain=0.34, pan=(-0.3 + 0.2 * k))
        place(send, musicbox(mtof(m + 12), 1.2, 0.5), tt + 0.003, gain=0.06)
        for j in range(3):                                                    # destellos en las rosas
            place(send, bell(mtof(m + 7 + 5 * j), 0.9, 0.5), tt + 0.06 + 0.05 * j, gain=0.035, pan=(j - 1) * 0.6)

    # --- cae la noche: reloj que se acelera, viento y dron grave ------------------
    tt, gap, k = 5.95, 0.3, 0
    while tt < 8.0:
        place(dry, tick(2600 if k % 2 == 0 else 1900, 0.8), tt, gain=0.11 * (0.6 + 0.4 * (tt - 5.95) / 2.05), pan=0.15 if k % 2 else -0.15)
        tt += gap
        gap = max(0.045, gap * 0.86)
        k += 1
    place(send, wind(3.2, 1.0), 6.1, gain=0.16)
    place(pads, np.stack([drone(mtof(26), 3.0, 1.0)] * 2, 1), 6.0, gain=0.18)
    place(send, riser(1.4), 7.0, gain=0.22)
    place(dry, whoosh(1.2, 2500, 220, 0.25, 0.9), 6.0, gain=0.12)

    # --- se enciende: clic del interruptor, golpe cálido y destellos --------------
    place(dry, switch_click(1.0), 8.38, gain=0.5)
    place(dry, switch_click(0.6), 8.52, gain=0.25)
    place(dry, boom(2.8, 1.0), 8.4, gain=0.5)
    place(send, boom(2.8, 1.0), 8.4, gain=0.22)
    place(pads, choir([58, 62, 65, 69], 8.4, 10.4, attack=0.35, release=1.0), 8.4, gain=1.1)
    sp = np.random.default_rng(8)
    pent = [74, 77, 79, 81, 84, 86, 89, 91, 93]
    for k in range(24):
        tt = 8.45 + sp.random() ** 1.5 * 1.3
        place(send, bell(mtof(pent[sp.integers(len(pent))]), 1.4, 0.8), tt, gain=0.07 * (1 - (tt - 8.45) / 1.6), pan=sp.uniform(-0.8, 0.8))
    for k, m in enumerate([70, 74, 77, 81, 79, 77]):                         # melodía cálida
        place(send, musicbox(mtof(m + 12), 2.0, 0.7), 9.0 + k * BEAT / 2, gain=0.1, pan=-0.2 + 0.08 * k)

    # --- atraviesa la luz hacia el colgante ----------------------------------------
    place(send, riser(0.9), 9.6, gain=0.2)
    place(dry, whoosh(0.6, 300, 6000, 0.7, 0.7), 9.95, gain=0.2)
    place(dry, boom(2.0, 0.7), 10.5, gain=0.35)
    place(send, bell(mtof(86), 2.2, 0.7), 10.5, gain=0.12)
    for k in range(16):                                                      # lucecitas que titilan
        tt = 10.7 + sp.random() * 1.4
        place(send, musicbox(mtof([86, 89, 93, 98, 101][sp.integers(5)]), 1.0, 0.5), tt, gain=0.045, pan=sp.uniform(-0.7, 0.7))
    for k, m in enumerate([67, 70, 74, 77, 74, 70]):
        place(send, musicbox(mtof(m + 12), 2.0, 0.7), 10.8 + k * BEAT / 2, gain=0.1, pan=0.2 - 0.08 * k)
    for k in range(9):                                                       # de blanco a negro: glissando
        place(send, bell(mtof(81 + k * 2), 1.0, 0.6), 11.55 + k * 0.05, gain=0.05, pan=-0.8 + 0.2 * k)

    # --- murciélagos ------------------------------------------------------------------
    for k in range(26):
        tt = 12.0 + sp.random() * 0.55
        place(dry, flutter(0.35 + sp.random() * 0.35, 8 + sp.random() * 4, 1.0), tt, gain=0.07 + 0.05 * sp.random(), pan=sp.uniform(-0.9, 0.9))
    place(dry, whoosh(0.8, 500, 3500, 0.55, 0.8), 12.0, gain=0.2)

    # --- 10 % de descuento ----------------------------------------------------------------
    place(dry, boom(2.6, 1.0), 12.6, gain=0.48)
    place(send, boom(2.6, 1.0), 12.6, gain=0.2)
    for k in range(11):                                                      # cuenta 0 → 10
        tt = 12.85 + (1 - (1 - k / 10) ** (1 / 3)) * 0.4
        place(dry, tick(3000 + 80 * k, 0.6), tt, gain=0.06)
    for m in (74, 81, 86, 89):
        place(send, bell(mtof(m), 2.4, 1.0), 13.27, gain=0.14)
    place(dry, kick(1.0), 13.27, gain=0.4)
    mel = [81, 79, 77, 76, 77, 74]
    for k, m in enumerate(mel):
        place(send, musicbox(mtof(m + 12), 1.6, 0.8), 13.65 + k * BEAT / 2, gain=0.09, pan=-0.3 + 0.08 * k)

    # --- ¿tienes una tienda? colabora con nosotros ---------------------------------------
    place(dry, whoosh(0.7, 3500, 500, 0.35, 0.8), 14.3, gain=0.14)
    place(dry, boom(2.0, 0.6), 14.4, gain=0.3)
    for k, m in enumerate([67, 70, 74, 79, 82, 86]):                         # la tienda se dibuja
        place(send, musicbox(mtof(m + 12), 1.6, 0.6), 14.6 + k * 0.12, gain=0.07, pan=-0.6 + 0.24 * k)
    place(dry, switch_click(0.8), T_SHOP - 0.02, gain=0.35)                    # se encienden las luces
    for m in (70, 74, 77, 81):
        place(send, bell(mtof(m + 12), 2.2, 0.9), T_SHOP, gain=0.09)
    place(pads, choir([58, 62, 65, 69], T_SHOP, 16.4, attack=0.25, release=0.8), T_SHOP, gain=0.8)
    for k, m in enumerate([86, 89, 93]):                                      # las piezas en el escaparate
        place(send, bell(mtof(m), 1.2, 0.7), T_SHOP + 0.15 + k * 0.12, gain=0.09, pan=(-0.4 + 0.4 * k))
        place(dry, tick(2800, 0.5), T_SHOP + 0.15 + k * 0.12, gain=0.05)
    for k in range(10):
        tt = T_SHOP + 0.5 + sp.random() * 0.6
        place(send, musicbox(mtof([93, 98, 101, 105][sp.integers(4)]), 0.9, 0.4), tt, gain=0.035, pan=sp.uniform(-0.7, 0.7))

    # --- cierre ------------------------------------------------------------------------------
    E0 = 16.5
    place(send, riser(0.5), E0 - 0.5, gain=0.18)
    place(dry, whoosh(0.7, 4500, 500, 0.35, 0.8), E0 - 0.05, gain=0.14)
    place(dry, boom(2.4, 0.8), E0, gain=0.38)
    place(dry, kick(1.0), E0, gain=0.5)
    kicks.append(E0)
    for m in (62, 69, 74, 77):
        place(send, epiano(mtof(m), 2.2, 0.8), E0 + 0.01, gain=0.1)
    for k in range(6):                                                       # se escribe la web
        place(dry, tick(2600, 0.6), E0 + 0.7 + k * 0.1, gain=0.045)
    for k, m in enumerate([86, 89, 93]):                                     # miniaturas
        place(send, bell(mtof(m), 1.4, 0.6), E0 + 1.3 + k * 0.1, gain=0.08, pan=(-0.5 + 0.5 * k))
    outro = [74, 77, 81, 79, 77, 76, 74]
    for k, m in enumerate(outro):
        place(send, musicbox(mtof(m + 12), 2.6, 0.85), 18.0 + k * BEAT / 2, gain=0.13, pan=0.3 - 0.08 * k)
    for m in (74, 81, 86):
        place(send, bell(mtof(m), 3.0, 0.6), 18.0, gain=0.08)
    place(send, choir([50, 57, 62, 65], 18.0, DUR - 0.3, attack=0.5, release=1.0), 18.0, gain=0.7)

    # --- compresión lateral: colchón y bajo respiran con el bombo --------------------------
    duck = np.ones(N)
    tt = t_axis(N)
    for kt in kicks:
        i = int(kt * SR)
        seg = tt[: int(0.45 * SR)]
        g = 1 - 0.4 * np.exp(-seg / 0.12)
        j = min(N, i + len(seg))
        duck[i:j] = np.minimum(duck[i:j], g[: j - i])
    pads *= duck[:, None]
    bassb *= duck[:, None]

    ir = reverb_ir(3.0)
    wet = convolve(send + pads * 0.6, ir)
    mixb = dry + send * 0.95 + pads * 0.8 + bassb * 0.7 + wet * 0.62
    mixb = mixb - onepole_lp(mixb, 40)
    mixb = mixb - onepole_lp(mixb, 40)
    mixb = mixb - 0.35 * (mixb - onepole_lp(mixb, 7000))
    # graves algo más contenidos (en el móvil no se oyen y le quitan volumen a lo demás)
    mixb = mixb - 0.3 * onepole_lp(onepole_lp(mixb, 110), 110)
    fade = np.clip((DUR + 0.05 - tt) / 1.4, 0, 1) ** 1.5
    mixb *= fade[:, None]
    mixb[: int(0.01 * SR)] *= np.linspace(0, 1, int(0.01 * SR))[:, None]
    peak = np.max(np.abs(mixb))
    mixb = np.tanh(mixb / peak * 1.6) / np.tanh(1.6) * 0.89
    return mixb[: int(DUR * SR)].astype(np.float32)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "build/audio/musica.f32"
    compose().tofile(out)
    print("música:", out, DUR, "s")
