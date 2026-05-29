"""モックから個別素材を抽出するスクリプト。

イメージは「モック画像を見せて、その中のロゴ/タイポ/装飾を抽出して」と指示する。
gpt-image-2 の images.edit API を使う。

中の NAME / PROMPT / SIZE を毎回編集して実行する。
出力先: pop-bloom-2/assets/{NAME}.png

使い方:
    1. 下の「ここを毎回編集」セクションを書き換える
    2. python generate_asset.py で実行
    3. 結果を確認して、OK なら次の素材へ、NG ならプロンプト調整して再実行
"""

import sys
import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).parent.parent
ASSETS_DIR = BASE / "assets"
ASSETS_DIR.mkdir(exist_ok=True)
IMAGES_DIR = BASE / "images"

ENV_PATH = Path(r"C:\Users\eluke\仕事\portfolio\morning-hill\tools\.env")
load_dotenv(ENV_PATH)


# ===== ここを毎回編集 =====

# 参照するモック画像（v2-09 が確定モック）
MOCK_PATH = IMAGES_DIR / "lp-mock-v2-09.png"

# 抽出する素材の名前（出力ファイル名）
NAME = "footer-logo"

# 抽出指示プロンプト
PROMPT = """\
このモック画像をもとに、LPページをコーディングで再現したいです。
そのために使えるクリーンな単体パーツが欲しいので、抽出してください。

【今回欲しいパーツ】
モック左下のフッターセクションにある "Pop Bloom" ロゴ。
（ピンク背景の上に白色で書かれているロゴ）

【条件】
- ロゴの色（白色）・形・タイポグラフィは、モックのものをそのまま再現してください
- 他の要素が重なっている場合は背景として補完して、ロゴが単体できれいに
  使える状態にしてください
- 出力背景は「黒色」にしてください
  （理由：ロゴが白色なので、白背景だと透過処理時にロゴまで消えてしまう。
   黒背景にしておけば、後で黒を透過にしてもロゴだけ残せる）
- 出力は、白色のロゴだけが中央に大きく配置された、黒背景の正方形画像
- LP実装にそのまま貼り付けて使える、クリーンな単体素材として出力
"""

SIZE = "1024x1024"  # "1024x1024" / "1024x1536"(縦長) / "1536x1024"(横長) / "auto"
QUALITY = "low"     # ユーザー指示で low 固定
# ========================


def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(f"エラー: OPENAI_API_KEY が見つかりません。{ENV_PATH} を確認してください。")
        sys.exit(1)

    if not MOCK_PATH.exists():
        print(f"エラー: モック画像が見つかりません: {MOCK_PATH}")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    out_path = ASSETS_DIR / f"{NAME}.png"
    print(f"抽出中: {NAME}")
    print(f"  入力モック: {MOCK_PATH.name}")
    print(f"  出力先: {out_path}")
    print(f"  サイズ/品質: {SIZE} / {QUALITY}")

    try:
        with open(MOCK_PATH, "rb") as mock_file:
            result = client.images.edit(
                model="gpt-image-2",
                image=mock_file,
                prompt=PROMPT,
                size=SIZE,
                quality=QUALITY,
            )
    except Exception as e:
        print(f"× 失敗: {e}")
        sys.exit(1)

    data = result.data[0]
    if getattr(data, "b64_json", None):
        image_bytes = base64.b64decode(data.b64_json)
    elif getattr(data, "url", None):
        import urllib.request
        with urllib.request.urlopen(data.url) as resp:
            image_bytes = resp.read()
    else:
        print("× 失敗: 画像データを取得できません")
        sys.exit(1)

    out_path.write_bytes(image_bytes)
    print(f"→ 保存: {out_path.name} ({len(image_bytes) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
