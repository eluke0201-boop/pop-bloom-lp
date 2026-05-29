"""sticker-squiggle.png に集約された11パーツを個別に切り出すスクリプト。

入力: assets/sticker-squiggle.png (1024x1024)
出力: assets/{各パーツ名}.png + assets/transparent/{各パーツ名}.png

- 大まかな領域を Y で区切る
- 各領域内で前景の bbox を自動検出してタイトに切り抜き
- 白背景を透過処理
"""

import sys
from pathlib import Path
from PIL import Image
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).parent.parent
ASSETS_DIR = BASE / "assets"
TRANSPARENT_DIR = ASSETS_DIR / "transparent"

SRC = ASSETS_DIR / "sticker-squiggle.png"

# 各領域: name → (x1, y1, x2, y2) を画像比率で
LINE_REGIONS = [
    ("sticker-ribbon-lime-check", 0.00, 0.00, 1.00, 0.27),
    ("line-wavy-lime",            0.00, 0.27, 1.00, 0.36),
    ("line-thin-pink",            0.00, 0.36, 1.00, 0.46),
    ("line-wavy-pink",            0.00, 0.46, 1.00, 0.56),
    ("line-thin-yellow",          0.00, 0.56, 1.00, 0.66),
    ("line-double-orange",        0.00, 0.66, 1.00, 0.77),
]

STICKER_NAMES = [
    "doodle-star-orange",
    "doodle-burst-yellow",
    "doodle-circle-lime",
    "doodle-heart-pink",
    "doodle-exclaim-pink",
]
STICKER_Y_START = 0.78
STICKER_Y_END = 1.00


def detect_fg_bbox(region: np.ndarray) -> tuple[int, int, int, int] | None:
    """白に近いピクセルを除外して前景の bbox を返す。"""
    r, g, b = region[:, :, 0], region[:, :, 1], region[:, :, 2]
    is_fg = ~((r > 235) & (g > 235) & (b > 235))
    rows = np.any(is_fg, axis=1)
    cols = np.any(is_fg, axis=0)
    if not rows.any() or not cols.any():
        return None
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    return int(rmin), int(rmax), int(cmin), int(cmax)


def make_transparent(arr: np.ndarray) -> np.ndarray:
    """白に近いピクセルのアルファを 0 にする。"""
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    is_bg = (r > 235) & (g > 235) & (b > 235)
    arr[is_bg, 3] = 0
    return arr


def save_part(name: str, region: np.ndarray, pad: int = 20) -> bool:
    bbox = detect_fg_bbox(region)
    if bbox is None:
        print(f"  ⚠️  スキップ: {name} (前景なし)")
        return False
    rmin, rmax, cmin, cmax = bbox
    h, w = region.shape[:2]
    rmin = max(0, rmin - pad)
    rmax = min(h, rmax + pad + 1)
    cmin = max(0, cmin - pad)
    cmax = min(w, cmax + pad + 1)

    cropped = region[rmin:rmax, cmin:cmax].copy()

    # 元画像（白背景版）
    rgb_out = cropped.copy()
    rgb_out[:, :, 3] = 255  # 不透明
    Image.fromarray(rgb_out).save(ASSETS_DIR / f"{name}.png")

    # 透過版
    transparent = make_transparent(cropped.copy())
    Image.fromarray(transparent).save(TRANSPARENT_DIR / f"{name}.png")

    print(f"  ✅ {name}.png ({cmax-cmin}x{rmax-rmin})")
    return True


def main() -> None:
    if not SRC.exists():
        print(f"エラー: {SRC} が見つかりません")
        sys.exit(1)

    src = Image.open(SRC).convert("RGBA")
    arr = np.array(src)
    h, w = arr.shape[:2]
    print(f"入力: {SRC.name} ({w}x{h})")
    print(f"出力: assets/{{name}}.png + assets/transparent/{{name}}.png")
    print()

    # 横長領域（リボン・線）
    for name, x1r, y1r, x2r, y2r in LINE_REGIONS:
        x1, y1 = int(x1r * w), int(y1r * h)
        x2, y2 = int(x2r * w), int(y2r * h)
        region = arr[y1:y2, x1:x2]
        save_part(name, region)

    # 小ステッカー5個（横5分割）
    sticker_y1 = int(STICKER_Y_START * h)
    sticker_y2 = int(STICKER_Y_END * h)
    sticker_w = w // 5
    for i, name in enumerate(STICKER_NAMES):
        x1 = i * sticker_w
        x2 = (i + 1) * sticker_w
        region = arr[sticker_y1:sticker_y2, x1:x2]
        save_part(name, region)

    print("\n完了！")


if __name__ == "__main__":
    main()
