"""Pop Bloom-2 LPデザインモック生成スクリプト。

生成→フィードバック→再生成 のループを支援。
- 既存 lp-mock-v2-NN.png の最大番号 +1 を自動採番して保存
- プロンプトは prompts.py から読む（編集して再実行するだけで反映）

使い方:
    python generate_mock.py                # 次の連番で1枚生成
    python generate_mock.py --n 3          # 3枚一気に生成（連番で）
    python generate_mock.py --quality med  # 品質指定（low/medium/high）
"""

import sys
import base64
import argparse
import re
from pathlib import Path

from dotenv import load_dotenv
import os
from openai import OpenAI

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).parent.parent
IMAGES_DIR = BASE / "images"
IMAGES_DIR.mkdir(exist_ok=True)

ENV_PATH = Path(r"C:\Users\eluke\仕事\portfolio\morning-hill\tools\.env")
load_dotenv(ENV_PATH)

# プロンプト本体は別ファイルから読む（編集して再実行→反映）
sys.path.insert(0, str(Path(__file__).parent))
from prompts import build_prompt  # noqa: E402


def next_index(images_dir: Path, prefix: str = "lp-mock-v2-") -> int:
    """既存ファイルの最大番号+1を返す。"""
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)\.png$")
    indices = []
    for p in images_dir.iterdir():
        m = pattern.match(p.name)
        if m:
            indices.append(int(m.group(1)))
    return (max(indices) + 1) if indices else 1


def generate_one(client: OpenAI, prompt: str, out_path: Path, quality: str = "low") -> Path | None:
    print(f"  生成中: {out_path.name} (quality={quality}) ...")
    try:
        result = client.images.generate(
            model="gpt-image-2",
            prompt=prompt,
            size="auto",
            quality=quality,
        )
    except Exception as e:
        print(f"    × 失敗: {e}")
        return None

    data = result.data[0]
    if getattr(data, "b64_json", None):
        image_bytes = base64.b64decode(data.b64_json)
    elif getattr(data, "url", None):
        import urllib.request
        with urllib.request.urlopen(data.url) as resp:
            image_bytes = resp.read()
    else:
        print("    × 失敗: 画像データを取得できません")
        return None

    out_path.write_bytes(image_bytes)
    size_kb = len(image_bytes) / 1024
    print(f"    → 保存: {out_path.name} ({size_kb:.0f} KB)")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=1, help="生成枚数（連番で）")
    parser.add_argument("--quality", choices=["low", "medium", "high"], default="low")
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(f"エラー: OPENAI_API_KEY が見つかりません。{ENV_PATH} を確認してください。")
        sys.exit(1)

    client = OpenAI(api_key=api_key)
    prompt = build_prompt()

    print(f"=== Pop Bloom-2 モック生成 ({args.n}枚, quality={args.quality}) ===")
    print(f"出力先: {IMAGES_DIR}")
    print()

    for _ in range(args.n):
        idx = next_index(IMAGES_DIR)
        out_path = IMAGES_DIR / f"lp-mock-v2-{idx:02d}.png"
        generate_one(client, prompt, out_path, quality=args.quality)

    print("\n完了！")


if __name__ == "__main__":
    main()
