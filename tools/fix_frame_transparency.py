"""フォトフレーム素材の透過処理を「外周白＋中央白だけ透過」に修正。

通常の透過処理（白ピクセル全部透過）だと、フレームの白枠も消えてしまう。
このスクリプトは:
- 外周から flood fill で到達できる白（背景） → 透過
- 中央から flood fill で到達できる白（写真エリア） → 透過
- どちらにも属さない白（枠本体） → 不透明のまま残す
"""

import sys
from pathlib import Path
from collections import deque
from PIL import Image
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).parent.parent
ORIGINALS_DIR = BASE / "assets" / "originals" / "frames"
TRANSPARENT_DIR = BASE / "assets" / "transparent" / "frames"

FRAMES = [
    "photo-frame-polaroid",
    "photo-frame-yellow",
    "photo-frame-pink",
    "photo-frame-purple",
]


def flood_fill_from_borders(is_white: np.ndarray) -> np.ndarray:
    """外周から flood fill で到達できる白ピクセルのマスクを返す。"""
    h, w = is_white.shape
    visited = np.zeros((h, w), dtype=bool)
    q = deque()
    for x in range(w):
        if is_white[0, x]:
            q.append((0, x))
        if is_white[h - 1, x]:
            q.append((h - 1, x))
    for y in range(h):
        if is_white[y, 0]:
            q.append((y, 0))
        if is_white[y, w - 1]:
            q.append((y, w - 1))

    while q:
        y, x = q.popleft()
        if visited[y, x]:
            continue
        if not is_white[y, x]:
            continue
        visited[y, x] = True
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_white[ny, nx]:
                q.append((ny, nx))
    return visited


def flood_fill_from_point(is_white: np.ndarray, exclude: np.ndarray, sy: int, sx: int) -> np.ndarray:
    """指定点から flood fill。exclude にあるピクセルは無視。"""
    h, w = is_white.shape
    visited = np.zeros((h, w), dtype=bool)
    if not is_white[sy, sx] or exclude[sy, sx]:
        return visited
    q = deque([(sy, sx)])
    while q:
        y, x = q.popleft()
        if visited[y, x]:
            continue
        if not is_white[y, x] or exclude[y, x]:
            continue
        visited[y, x] = True
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_white[ny, nx] and not exclude[ny, nx]:
                q.append((ny, nx))
    return visited


def process_frame(name: str) -> None:
    src = ORIGINALS_DIR / f"{name}.png"
    dst = TRANSPARENT_DIR / f"{name}.png"
    if not src.exists():
        print(f"  ⚠️  欠落: {src}")
        return

    img = Image.open(src).convert("RGBA")
    arr = np.array(img)
    h, w = arr.shape[:2]
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    # 閾値を厳しく(>250)して、純白だけ判定。
    # 枠は AI生成で微妙にグレーがかってるので、これで枠は残り背景・中央だけ透過になる
    is_white = (r > 250) & (g > 250) & (b > 250)

    # 1. 外周から到達できる白（背景）→ 透過
    outer = flood_fill_from_borders(is_white)
    arr[outer, 3] = 0

    # 2. 中央から到達できる白（写真エリア）→ 透過
    #    外周マスクと重複しないように exclude
    cy, cx = h // 2, w // 2
    center = flood_fill_from_point(is_white, outer, cy, cx)
    arr[center, 3] = 0

    Image.fromarray(arr).save(dst, "PNG")
    n_outer = int(outer.sum())
    n_center = int(center.sum())
    n_frame_kept = int((is_white & ~outer & ~center).sum())
    print(f"  ✅ {name}: 外周透過={n_outer}px, 中央透過={n_center}px, 枠保持={n_frame_kept}px")


def main() -> None:
    print(f"=== フォトフレーム透過修正 ===")
    print(f"入力: {ORIGINALS_DIR}")
    print(f"出力: {TRANSPARENT_DIR}")
    print()
    for name in FRAMES:
        process_frame(name)
    print("\n完了！")


if __name__ == "__main__":
    main()
