"""素材をジャンル別サブフォルダに整理。

両方とも整理する:
- assets/ 直下の元画像 → assets/originals/{category}/
- assets/transparent/ 直下の透過画像 → assets/transparent/{category}/

カテゴリ:
- logos        - Pop Bloom ロゴ各種
- typography   - セクション見出し、ヘッダー文字
- backgrounds  - ブロブ、色面
- stickers     - 装飾ステッカー
- photos       - 写真プレースホルダー
- ui           - ナビアイコン、SNSアイコン、UIパーツ
"""

import sys
import shutil
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).parent.parent
ASSETS_DIR = BASE / "assets"
ORIGINALS_DIR = ASSETS_DIR / "originals"
TRANSPARENT_DIR = ASSETS_DIR / "transparent"


CATEGORY_MAP = {
    "logos": [
        "hero-logo", "footer-logo",
    ],
    "typography": [
        "hero-typo",
        "section-title-about",
        "section-title-products",
        "section-title-lookbook",
        "section-title-drop",
        "section-title-community",
        "shop-now-button",
    ],
    "backgrounds": [
        "hero-bg-blob-yellow",
        "hero-bg-blob-orange",
        "drop-section-bg",
        "product-bg-blob-pink",
        "product-bg-blob-yellow",
        "product-bg-blob-purple",
        "product-bg-blob-lime",
    ],
    "stickers": [
        "sticker-flower-yellow",
        "sticker-flower-pink",
        "sticker-star-yellow",
        "sticker-star-pink",
        "sticker-heart-pink",
        "sticker-arrow-curve",
        "sticker-sparkle",
        "sticker-dot-pink",
        "sticker-burst",
        "sticker-ribbon-lime-check",
        "line-wavy-lime",
        "line-thin-pink",
        "line-wavy-pink",
        "line-thin-yellow",
        "line-double-orange",
        "doodle-star-orange",
        "doodle-burst-yellow",
        "doodle-circle-lime",
        "doodle-heart-pink",
        "doodle-exclaim-pink",
        # マスキングテープ色違い
        "tape-orange", "tape-pink", "tape-purple", "tape-yellow", "tape-lime",
    ],
    "frames": [
        "photo-frame-polaroid",
        "photo-frame-yellow",
        "photo-frame-pink",
        "photo-frame-purple",
    ],
    "photos": [
        "hero-model",
        "about-product-display",
        "about-mascot",
        "product-01", "product-02", "product-03", "product-04", "product-05",
        "lookbook-model-01", "lookbook-model-02", "lookbook-model-03",
        "drop-storefront", "drop-product-01", "drop-product-02",
        "ugc-01", "ugc-02", "ugc-03", "ugc-04",
    ],
    "ui": [
        "nav-icon-search", "nav-icon-heart", "nav-icon-cart",
        "sns-icon-instagram", "sns-icon-tiktok", "sns-icon-x",
        "newsletter-input",
        "hero-badge-cute",  # 紫バッジ置換用
    ],
}


def organize_dir(src_dir: Path, dst_parent_dir: Path, label: str) -> None:
    """src_dir 直下のファイルを dst_parent_dir/{category}/ に移動。
    dst が既存で src も残っている場合は重複扱いで src を削除する。"""
    print(f"\n=== {label} 整理 ===")
    print(f"  source: {src_dir}")
    print(f"  dest:   {dst_parent_dir}")
    dst_parent_dir.mkdir(exist_ok=True)
    moved = 0
    skipped = 0
    deleted = 0
    missing = 0

    for category, names in CATEGORY_MAP.items():
        cat_dir = dst_parent_dir / category
        cat_dir.mkdir(exist_ok=True)
        for name in names:
            src = src_dir / f"{name}.png"
            dst = cat_dir / f"{name}.png"

            if dst.exists():
                # 整理先に既存。src が直下に残っていれば重複なので削除。
                # ただし src と dst が同じ実体（assets/transparent/transparent/）の
                # ような自己参照状態は触らない。
                if src.exists() and src.resolve() != dst.resolve():
                    src.unlink()
                    print(f"  🗑  重複削除: {src.relative_to(BASE)}")
                    deleted += 1
                else:
                    skipped += 1
                continue

            if not src.exists():
                missing += 1
                continue

            shutil.move(str(src), str(dst))
            print(f"  ✅ {category}/{name}.png")
            moved += 1

    print(f"  → 移動: {moved}, 重複削除: {deleted}, 整理済み: {skipped}, 欠落: {missing}")


def main() -> None:
    # 元画像: assets/ 直下 → assets/originals/{category}/
    organize_dir(ASSETS_DIR, ORIGINALS_DIR, "元画像")
    # 透過画像: assets/transparent/ 直下 → assets/transparent/{category}/
    organize_dir(TRANSPARENT_DIR, TRANSPARENT_DIR, "透過画像")
    print("\n完了！")


if __name__ == "__main__":
    main()
