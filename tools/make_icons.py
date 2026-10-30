"""Draws the Voice Studio icon (rounded square with waveform bars) at every size
and writes assets/voice-studio.png and assets/voice-studio.ico. Needs only numpy."""
import struct
import zlib
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent.parent / "assets"
BG = np.array([0x24, 0x47, 0xE8], dtype=np.float64)
FG = np.array([255, 255, 255], dtype=np.float64)
BARS = [0.26, 0.50, 0.78, 0.42, 0.30]  # bar heights as a fraction of the icon


def render(size, ss=4):
    n = size * ss
    y, x = (np.mgrid[0:n, 0:n] + 0.5) / n  # 0..1 coordinates
    # rounded square
    r = 0.22
    dx = np.maximum(np.abs(x - 0.5) - (0.5 - r), 0)
    dy = np.maximum(np.abs(y - 0.5) - (0.5 - r), 0)
    alpha = (np.hypot(dx, dy) <= r).astype(np.float64)
    # bars (capsules)
    w, gap = 0.085, 0.058
    total = len(BARS) * w + (len(BARS) - 1) * gap
    left = 0.5 - total / 2
    bar = np.zeros_like(alpha)
    for i, h in enumerate(BARS):
        cx = left + i * (w + gap) + w / 2
        half = h / 2 - w / 2
        d = np.hypot(x - cx, np.maximum(np.abs(y - 0.5) - half, 0))
        bar = np.maximum(bar, (d <= w / 2).astype(np.float64))
    color = BG[None, None, :] * (1 - bar[..., None]) + FG[None, None, :] * bar[..., None]
    pre = color * alpha[..., None]
    pre = pre.reshape(size, ss, size, ss, 3).mean(axis=(1, 3))
    a = alpha.reshape(size, ss, size, ss).mean(axis=(1, 3))
    rgb = np.where(a[..., None] > 0, pre / np.maximum(a[..., None], 1e-9), 0)
    return np.dstack([rgb, a * 255]).round().clip(0, 255).astype(np.uint8)


def png_bytes(arr):
    h, w, _ = arr.shape
    raw = b"".join(b"\x00" + arr[row].tobytes() for row in range(h))

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def ico_bytes(sizes):
    images = [png_bytes(render(s)) for s in sizes]
    header = struct.pack("<HHH", 0, 1, len(sizes))
    offset = 6 + 16 * len(sizes)
    entries, blobs = b"", b""
    for s, data in zip(sizes, images):
        entries += struct.pack("<BBBBHHII", 0 if s >= 256 else s, 0 if s >= 256 else s, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
        blobs += data
    return header + entries + blobs


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    (OUT / "voice-studio.png").write_bytes(png_bytes(render(1024, ss=2)))
    (OUT / "voice-studio.ico").write_bytes(ico_bytes([16, 24, 32, 48, 64, 128, 256]))
    print("icons written to", OUT)
