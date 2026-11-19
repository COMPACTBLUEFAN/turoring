"""Лаборатория 0.SND.01: от сэмпла и классического DSP к AI в звуке.

Только стандартная библиотека Python (без numpy/scipy).
Запуск: python snd_lab.py
Создаёт WAV-файлы в папке out/ рядом со скриптом (можно послушать в плеере или DAW).
"""

from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent / "out"


def save_wav(path: Path, samples: list[float], sr: int) -> None:
    """Сохраняет моно-сигнал float [-1.0, 1.0] в 16-bit PCM WAV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    peak = max((abs(x) for x in samples), default=1.0)
    scale = 0.9 / peak if peak > 0 else 1.0
    pcm = bytearray()
    for x in samples:
        val = max(-1.0, min(1.0, x * scale))
        pcm += struct.pack("<h", int(round(val * 32767)))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm)


def dft_magnitude(samples: list[float], sr: int, freqs: list[float]) -> dict[float, float]:
    """Считает амплитуду на заданных частотах (прямое ДПФ с окном Ханна)."""
    n = len(samples)
    if n == 0:
        return {f: 0.0 for f in freqs}
    windowed = [
        samples[i] * 0.5 * (1.0 - math.cos(2.0 * math.pi * i / (n - 1)))
        for i in range(n)
    ]
    result: dict[float, float] = {}
    for f in freqs:
        re = 0.0
        im = 0.0
        step = 2.0 * math.pi * f / sr
        for i, s in enumerate(windowed):
            angle = step * i
            re += s * math.cos(angle)
            im -= s * math.sin(angle)
        result[f] = (2.0 / n) * math.hypot(re, im)
    return result


def rms_db(samples: list[float]) -> float:
    """Уровень RMS в dBFS (для тишины — -96.0)."""
    if not samples:
        return -96.0
    mean_sq = sum(x * x for x in samples) / len(samples)
    if mean_sq <= 1e-12:
        return -96.0
    return 20.0 * math.log10(math.sqrt(mean_sq))


def spectral_centroid_hz(samples: list[float], sr: int) -> float:
    """Оценка спектрального центроида («яркости», Гц) по сетке гармоник 110..4400 Гц."""
    probe_freqs = [110.0 * k for k in range(1, 41)]
    mags = dft_magnitude(samples, sr, probe_freqs)
    total = sum(mags.values())
    if total <= 1e-9:
        return 0.0
    return sum(f * m for f, m in mags.items()) / total


def karplus_strong(
    freq: float = 110.0,
    duration: float = 1.5,
    sr: int = 44100,
    decay: float = 0.996,
    seed: int = 42,
) -> list[float]:
    """Синтез щипка струны алгоритмом Karplus-Strong (~12 строк ядра)."""
    rng = random.Random(seed)
    period = max(2, round(sr / freq))
    # 1. «Щипок» — заполняем короткий буфер задержки белым шумом
    buf = [rng.uniform(-1.0, 1.0) for _ in range(period)]
    out: list[float] = []
    n_samples = int(sr * duration)
    for i in range(n_samples):
        idx = i % period
        nxt = (idx + 1) % period
        sample = buf[idx]
        out.append(sample)
        # 2. Простейший ФНЧ (среднее 2 соседних сэмплов) + затухание
        buf[idx] = 0.5 * (buf[idx] + buf[nxt]) * decay
    return out


def exp1_aliasing() -> None:
    print("=" * 68)
    print("ОПЫТ 1. Найквист и алиасинг при ресэмплинге 48 кГц -> 8 кГц без LPF")
    print("=" * 68)
    sr_hi = 48000
    dur = 1.0
    # Два чистых тона: 1000 Гц и 6000 Гц
    sig_48k = [
        0.45 * math.sin(2.0 * math.pi * 1000.0 * i / sr_hi)
        + 0.45 * math.sin(2.0 * math.pi * 6000.0 * i / sr_hi)
        for i in range(int(sr_hi * dur))
    ]
    # Наивный ресэмплинг в 8 кГц (просто каждый 6-й сэмпл, без фильтра)
    sr_lo = 8000
    sig_8k_naive = sig_48k[::6]

    save_wav(OUT_DIR / "exp1_tone_48k.wav", sig_48k, sr_hi)
    save_wav(OUT_DIR / "exp1_tone_8k_naive.wav", sig_8k_naive, sr_lo)

    check_48k = [1000.0, 2000.0, 3000.0, 4000.0, 6000.0]
    check_8k = [1000.0, 2000.0, 3000.0, 3500.0]

    # Берём короткий срез 20 мс — достаточно для точной оценки чистых тонов
    mags_48k = dft_magnitude(sig_48k[:960], sr_hi, check_48k)
    mags_8k = dft_magnitude(sig_8k_naive[:160], sr_lo, check_8k)

    print("Спектр оригинала (48 кГц, Найквист = 24 000 Гц):")
    for f, m in mags_48k.items():
        bar = "#" * int(m * 60)
        print(f"  {f:6.0f} Гц : {m:.3f}  {bar}")

    print("\nСпектр после наивного прореживания (8 кГц, Найквист = 4 000 Гц):")
    for f, m in mags_8k.items():
        bar = "#" * int(m * 60)
        print(f"  {f:6.0f} Гц : {m:.3f}  {bar}")
    print(f"\nФайлы сохранены: {OUT_DIR / 'exp1_tone_48k.wav'} и exp1_tone_8k_naive.wav\n")


def exp2_and_3_karplus_and_timbre() -> None:
    print("=" * 68)
    print("ОПЫТ 2 и 3. Karplus-Strong и «одинаковая АЧХ vs разный тембр»")
    print("=" * 68)
    sr = 44100
    # Попробуй в задании 3 поменять decay (например, 0.996 -> 0.95) или freq
    pluck = karplus_strong(freq=110.0, duration=1.2, sr=sr, decay=0.996)
    pluck_rev = list(reversed(pluck))

    save_wav(OUT_DIR / "exp2_karplus_A2.wav", pluck, sr)
    save_wav(OUT_DIR / "exp3_karplus_A2_reversed.wav", pluck_rev, sr)

    # Сравним глобальную АЧХ (магнитудный спектр на 8 гармониках по всему файлу)
    probe = [110.0 * k for k in (1, 2, 3, 4, 6, 8, 12, 16)]
    # Для скорости возьмём равномерную подвыборку целого файла (каждый 4-й сэмпл -> 11025 Гц,
    # все 8 пробных частот <= 1760 Гц, сильно ниже Найквиста 5512 Гц)
    sub_sr = sr // 4
    sub_fwd = pluck[::4]
    sub_rev = list(reversed(sub_fwd))
    g_fwd = dft_magnitude(sub_fwd, sub_sr, probe)
    g_rev = dft_magnitude(sub_rev, sub_sr, probe)

    max_diff = max(abs(g_fwd[f] - g_rev[f]) for f in probe)
    print("Глобальная АЧХ (амплитуда по всему файлу, прямой vs reverse):")
    for f in probe:
        print(f"  {f:6.0f} Гц | прямой: {g_fwd[f]:.5f} | reverse: {g_rev[f]:.5f}")
    print(f"Максимальная разница глобальной АЧХ: {max_diff:.6f}\n")

    # Теперь сравним по времени (4 окна по 30 мс — аналог кадров STFT)
    windows_ms = [(0, 30), (200, 230), (600, 630), (1100, 1130)]
    print("Покадровый разрез во времени (RMS и спектральный центроид «яркости»):")
    print(f"  {'Окно (мс)':<12} | {'Прямой RMS / центроид':<26} | {'Reverse RMS / центроид':<26}")
    print("  " + "-" * 70)
    for start_ms, end_ms in windows_ms:
        i0 = int(sr * start_ms / 1000)
        i1 = int(sr * end_ms / 1000)
        f_rms = rms_db(pluck[i0:i1])
        f_cen = spectral_centroid_hz(pluck[i0:i1], sr)
        r_rms = rms_db(pluck_rev[i0:i1])
        r_cen = spectral_centroid_hz(pluck_rev[i0:i1], sr)
        print(
            f"  {start_ms:4d}–{end_ms:4d} мс | "
            f"{f_rms:6.1f} дБ / {f_cen:6.0f} Гц      | "
            f"{r_rms:6.1f} дБ / {r_cen:6.0f} Гц"
        )
    print(
        f"\nФайлы сохранены: {OUT_DIR / 'exp2_karplus_A2.wav'} "
        f"и exp3_karplus_A2_reversed.wav"
    )


if __name__ == "__main__":
    exp1_aliasing()
    exp2_and_3_karplus_and_timbre()
