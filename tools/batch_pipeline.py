"""モックから全素材を一気通貫で抽出 → 透過処理するパイプライン。

1. ASSETS リストの各素材を images.edit で抽出
2. bg_color に応じて背景透過処理（PIL）
3. 透過済み素材を assets/transparent/ に保存

実行:
    python batch_pipeline.py
    python batch_pipeline.py --skip-existing   # 既存はスキップ（デフォルト）
    python batch_pipeline.py --regenerate      # 全部再生成
    python batch_pipeline.py --transparent-only # 生成スキップ、透過処理だけ
"""

import sys
import base64
import os
import argparse
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).parent.parent
IMAGES_DIR = BASE / "images"
ASSETS_DIR = BASE / "assets"
ORIGINALS_DIR = ASSETS_DIR / "originals"
TRANSPARENT_DIR = ASSETS_DIR / "transparent"
ORIGINALS_DIR.mkdir(exist_ok=True)
TRANSPARENT_DIR.mkdir(exist_ok=True)

MOCK_PATH = IMAGES_DIR / "lp-mock-v2-09.png"

# CATEGORY_MAP を organize_assets から借用（重複定義を避ける）
sys.path.insert(0, str(Path(__file__).parent))
from organize_assets import CATEGORY_MAP  # noqa: E402

# name -> category のルックアップ
CATEGORY_FOR_NAME = {n: c for c, names in CATEGORY_MAP.items() for n in names}


def category_for(name: str) -> str:
    """name からカテゴリを引く。未定義なら空文字（assets直下に保存される）。"""
    return CATEGORY_FOR_NAME.get(name, "")

ENV_PATH = Path(r"C:\Users\eluke\仕事\portfolio\morning-hill\tools\.env")
load_dotenv(ENV_PATH)


# ===== 抽出する素材リスト =====
# bg_color: "white" or "black" (透過処理の対象色)
# what: AIに伝える「これを抽出して」の説明
ASSETS = [
    # ── ロゴ・タイポ ──
    {"name": "hero-logo", "bg_color": "white",
     "what": "モック左上のオレンジ色 'Pop Bloom' ロゴ（Y2K丸文字、花マーク付き）"},
    {"name": "footer-logo", "bg_color": "black",
     "what": "モック左下のフッターセクションにある白色の 'Pop Bloom' ロゴ"},
    {"name": "hero-typo", "bg_color": "white",
     "what": "モックHeroの大きな英字タイポ 'BRIGHT STUFF FOR EVERY DAY!'（カラフルな手描き風）"},
    {"name": "section-title-about", "bg_color": "white",
     "what": "モックの 'ABOUT' セクション見出し文字"},
    {"name": "section-title-products", "bg_color": "white",
     "what": "モックの 'PRODUCTS' セクション見出し文字"},
    {"name": "section-title-lookbook", "bg_color": "white",
     "what": "モックの 'LOOKBOOK / STYLING' セクション見出し文字"},
    {"name": "section-title-drop", "bg_color": "white",
     "what": "モックの 'NEXT DROP / EVENT' セクション見出し文字"},
    {"name": "section-title-community", "bg_color": "white",
     "what": "モックの 'COMMUNITY' セクション見出し文字"},
    {"name": "shop-now-button", "bg_color": "white",
     "what": "モックHeroにあるカラフルな 'SHOP NOW' ボタンのデザイン"},

    # ── 背景・色面 ──
    {"name": "hero-bg-blob-yellow", "bg_color": "white",
     "what": "モックHero背景にある黄色の有機的なブロブ形（不揃いな手描き感のある形）"},
    {"name": "hero-bg-blob-orange", "bg_color": "white",
     "what": "モックHero背景にあるオレンジ色の有機的なブロブ形"},
    {"name": "drop-section-bg", "bg_color": "white",
     "what": "モックのNEXT DROP / EVENTセクションの背景に使われている色面・帯デザイン"},
    {"name": "product-bg-blob-pink", "bg_color": "white",
     "what": "モックのPRODUCTSセクションで商品の裏にあるピンク色の不揃いなブロブ背景"},
    {"name": "product-bg-blob-yellow", "bg_color": "white",
     "what": "モックのPRODUCTSセクションで商品の裏にある黄色の不揃いなブロブ背景"},
    {"name": "product-bg-blob-purple", "bg_color": "white",
     "what": "モックのPRODUCTSセクションで商品の裏にあるパープル色の不揃いなブロブ背景"},
    {"name": "product-bg-blob-lime", "bg_color": "white",
     "what": "モックのPRODUCTSセクションで商品の裏にあるライムグリーン色の不揃いなブロブ背景"},

    # ── 装飾ステッカー ──
    {"name": "sticker-flower-yellow", "bg_color": "white",
     "what": "モックに散らばっている黄色の花ステッカー（笑顔付き、手描き風）"},
    {"name": "sticker-flower-pink", "bg_color": "white",
     "what": "モックに散らばっているピンクの花ステッカー（手描き風）"},
    {"name": "sticker-star-yellow", "bg_color": "white",
     "what": "モックに散らばっている黄色の星型ステッカー（手描き風）"},
    {"name": "sticker-star-pink", "bg_color": "white",
     "what": "モックに散らばっているピンクの星型ステッカー（手描き風）"},
    {"name": "sticker-heart-pink", "bg_color": "white",
     "what": "モックに散らばっているピンクのハート型ステッカー（手描き風）"},
    {"name": "sticker-arrow-curve", "bg_color": "white",
     "what": "モックに使われている手描き風の曲線矢印（カーブしたarrow）"},
    # sticker-squiggle は集約版になってしまったので削除。中身を個別生成する：
    {"name": "sticker-ribbon-lime-check", "bg_color": "white",
     "what": "モックに使われているライムグリーン色のチェッカー柄テープ/リボン装飾"},
    {"name": "line-wavy-lime", "bg_color": "white",
     "what": "モックに使われている太めの波線（ライムグリーン色）の手描き装飾"},
    {"name": "line-thin-pink", "bg_color": "white",
     "what": "モックに使われている薄いピンクの細い直線（手描き装飾）"},
    {"name": "line-wavy-pink", "bg_color": "white",
     "what": "モックに使われている濃いピンクの太めの波線（手描き装飾）"},
    {"name": "line-thin-yellow", "bg_color": "white",
     "what": "モックに使われている細いイエローの曲線（手描き装飾）"},
    {"name": "line-double-orange", "bg_color": "white",
     "what": "モックに使われているオレンジとイエローの二重線（手描き装飾）"},
    {"name": "doodle-star-orange", "bg_color": "white",
     "what": "モックに使われているオレンジ色の手描き星マーク（小ステッカー）"},
    {"name": "doodle-burst-yellow", "bg_color": "white",
     "what": "モックに使われているイエロー色の手描きバースト/雪の結晶風マーク"},
    {"name": "doodle-circle-lime", "bg_color": "white",
     "what": "モックに使われているライムグリーン色の手描きの丸い円マーク"},
    {"name": "doodle-heart-pink", "bg_color": "white",
     "what": "モックに使われている濃いピンクの手描きハート（細い線で描かれた小さなハート）"},
    {"name": "doodle-exclaim-pink", "bg_color": "white",
     "what": "モックに使われているピンクの手描き強調マーク（3本のスラッシュや感嘆符）"},
    {"name": "sticker-sparkle", "bg_color": "white",
     "what": "モックに使われているキラキラ・スパークル装飾"},
    {"name": "sticker-dot-pink", "bg_color": "white",
     "what": "モックに散らばっているピンクのドット・点々の装飾"},
    {"name": "sticker-burst", "bg_color": "white",
     "what": "モックに使われているバースト形（爆発・放射状）の装飾"},

    # ── 写真プレースホルダー ──
    {"name": "hero-model", "bg_color": "white",
     "what": "Z世代女子（10代後半〜20代前半）のかわいい女性モデル（笑顔、頬杖ポーズ、カラフルなY2Kファッション、"
             "オレンジサングラスをかけている）の上半身ポートレート。"
             "**重要: 目を正しく描写してください。左右対称で、瞳の位置・形・サイズが自然な、リアルで違和感のない目に**。"
             "**背景は完全に純白（#FFFFFF）にしてください。色面・ブロブ・装飾・影など一切なし**。"
             "白背景に人物だけが浮いている、商品撮影風の切り抜き済みポートレート画像として出力。"
             "（理由：LP実装時に背景レイヤーを別途配置するため、人物単体の素材が必要）"},
    {"name": "about-product-display", "bg_color": "white",
     "what": "Z世代女子向けの雑貨ショップの商品ディスプレイ写真。"
             "カラフルなぬいぐるみ、文房具、アクセサリーが棚やテーブルに並んでいる、ポップアップショップ風の雰囲気。"
             "ピンク・イエロー・パープルなどビビッドカラー基調"},
    {"name": "about-mascot", "bg_color": "white",
     "what": "Pop Bloomブランドのマスコットキャラクター。"
             "笑顔の花のキャラクター（ピンクやイエローの花にかわいい目と笑顔）。"
             "**目をはっきりかわいらしく描写**。手描きY2K風イラスト"},
    {"name": "product-01", "bg_color": "white",
     "what": "Z世代女子向け雑貨ショップ Pop Bloom の商品写真：1点目。"
             "ピンクのハート型シャイニーバッグ。**背景は純白（#FFFFFF）のみ、装飾・模様・色面・コーナーフレーム一切なし**。"
             "商品単体の物撮り風、商品だけが白背景に浮いている切り抜き済み画像"},
    {"name": "product-02", "bg_color": "white",
     "what": "Z世代女子向け雑貨ショップ Pop Bloom の商品写真：2点目。"
             "ピンクのマグカップ（'GOOD DAYS AHEAD' などのレトロタイポ入りも可）。"
             "**背景は純白（#FFFFFF）のみ、装飾・模様・コーナー装飾一切なし**。商品単体の物撮り風"},
    {"name": "product-03", "bg_color": "white",
     "what": "Z世代女子向け雑貨ショップ Pop Bloom の商品写真：3点目。"
             "パステルカラーのビーズと笑顔フラワーモチーフのキーホルダーまたはチャーム。"
             "**背景は純白（#FFFFFF）のみ、装飾・模様・コーナー装飾一切なし**。商品単体の物撮り風"},
    {"name": "product-04", "bg_color": "white",
     "what": "Z世代女子向け雑貨ショップ Pop Bloom の商品写真：4点目。"
             "ピンクのハート型ポーチ＋ヘアアクセサリーセット（シュシュ、ヘアクリップ）。"
             "**背景は純白（#FFFFFF）のみ、装飾・模様・コーナー装飾一切なし**。商品単体の物撮り風"},
    {"name": "product-05", "bg_color": "white",
     "what": "Z世代女子向け雑貨ショップ Pop Bloom の商品写真：5点目。"
             "他の商品（バッグ・マグ・キーホルダー・ポーチ）と被らない雑貨。"
             "たとえばカラフルなステッカーセット、ノート、スマホケース、ヘッドホンなど。"
             "**背景は純白（#FFFFFF）のみ、装飾・模様・コーナー装飾一切なし**。商品単体の物撮り風"},
    {"name": "lookbook-model-01", "bg_color": "white",
     "what": "Z世代女子（10代後半〜20代前半）のスタイリング全身写真。カラフルなY2Kファッション。"
             "**目を正しく描写、左右対称で自然な瞳**。明るい背景、ファッション雑誌風のポップな構図"},
    {"name": "lookbook-model-02", "bg_color": "white",
     "what": "Z世代女子の別のスタイリング全身写真。パステルカラーまたはビビッドな配色のかわいいコーデ。"
             "**目を正しく描写**。背景はシンプル、モデルの服装が引き立つ構図"},
    {"name": "lookbook-model-03", "bg_color": "white",
     "what": "Z世代女子の3つ目のスタイリング写真。アクセサリーや雑貨を身につけた個性的なコーデ。"
             "**目を正しく描写**。雰囲気のあるポートレート"},
    {"name": "drop-storefront", "bg_color": "white",
     "what": "Pop Bloomのポップアップストアの店頭風景写真。カラフルでビビッドな店構え、"
             "ピンク・オレンジ基調の壁、商品が並ぶ什器、ガラスショーケース。"
             "Z世代女子向けのインスタ映えするかわいい店内・店頭のイメージ。"
             "（モックNEXT DROP/EVENTセクションの左側に置く大きめの店頭イメージ画像）"},
    {"name": "drop-product-01", "bg_color": "white",
     "what": "モックNEXT DROP / EVENTセクションの1番目の商品写真"},
    {"name": "drop-product-02", "bg_color": "white",
     "what": "モックNEXT DROP / EVENTセクションの2番目の商品写真"},
    {"name": "ugc-01", "bg_color": "white",
     "what": "Z世代女子のInstagram投稿風写真。Pop Bloomの雑貨（ぬいぐるみやステッカー）を使った"
             "推し活デコの様子。スマホで撮ったような明るくカジュアルな雰囲気"},
    {"name": "ugc-02", "bg_color": "white",
     "what": "Z世代女子のInstagram投稿風写真。カラフルな雑貨を並べたフラットレイ。"
             "ピンク・イエロー基調でかわいいテーブルセッティング"},
    {"name": "ugc-03", "bg_color": "white",
     "what": "Z世代女子のInstagram投稿風写真。**人物は写さない**、商品中心。"
             "お部屋やデスクの上でPop Bloom雑貨を飾った様子（ぬいぐるみ・ステッカーで彩られた机、"
             "ベッドサイドのかわいいディスプレイなど）。カラフルでSNS映えする構図"},
    {"name": "ugc-04", "bg_color": "white",
     "what": "Z世代女子のInstagram投稿風写真。ポップアップストアでの買い物の様子、"
             "またはお気に入りのPop Bloomグッズの紹介。**人物が写る場合は目を正しく**"},

    # ── 機能パーツ ──
    # nav-icons / sns-icons はLP実装で個別リンクにするため、ばらして抽出
    {"name": "nav-icon-search", "bg_color": "white",
     "what": "モック右上ナビゲーションの「検索」アイコン（虫眼鏡）を単体で抽出"},
    {"name": "nav-icon-heart", "bg_color": "white",
     "what": "モック右上ナビゲーションの「お気に入り」アイコン（ハート）を単体で抽出"},
    {"name": "nav-icon-cart", "bg_color": "white",
     "what": "モック右上ナビゲーションの「カート」アイコン（買い物袋またはバッグ）を単体で抽出"},
    {"name": "sns-icon-instagram", "bg_color": "white",
     "what": "モックフッターのInstagram丸アイコンを単体で抽出"},
    {"name": "sns-icon-tiktok", "bg_color": "white",
     "what": "モックフッターのTikTok丸アイコンを単体で抽出"},
    {"name": "sns-icon-x", "bg_color": "white",
     "what": "モックフッターのX(Twitter)丸アイコンを単体で抽出"},
    {"name": "newsletter-input", "bg_color": "white",
     "what": "モックフッターにあるニュースレターのメールアドレス入力欄＋登録ボタン"},

    # ── マスキングテープ素材（カラフルな単色長方形、貼り絵感を出すための装飾）──
    {"name": "tape-orange", "bg_color": "white",
     "what": "マスキングテープ風の長方形ステッカー。ビビッドオレンジ色の単色。"
             "横長の長方形（およそ4:1の比率）、エッジは自然な手切り感がある、わずかに半透明感、影は控えめ。"
             "貼り絵やスクラップブッキングに使うマスキングテープのような見た目"},
    {"name": "tape-pink", "bg_color": "white",
     "what": "マスキングテープ風の長方形ステッカー。ホットピンク色の単色。"
             "横長の長方形、エッジは自然な手切り感、わずかに半透明、影は控えめ。マスキングテープ風"},
    {"name": "tape-purple", "bg_color": "white",
     "what": "マスキングテープ風の長方形ステッカー。ビビッドパープル色の単色。"
             "横長の長方形、エッジは自然な手切り感、わずかに半透明、影は控えめ。マスキングテープ風"},
    {"name": "tape-yellow", "bg_color": "white",
     "what": "マスキングテープ風の長方形ステッカー。サニーイエロー色の単色。"
             "横長の長方形、エッジは自然な手切り感、わずかに半透明、影は控えめ。マスキングテープ風"},
    {"name": "tape-lime", "bg_color": "white",
     "what": "マスキングテープ風の長方形ステッカー。ライムグリーン色の単色。"
             "横長の長方形、エッジは自然な手切り感、わずかに半透明、影は控えめ。マスキングテープ風"},

    # ── フォトフレーム素材（写真を入れるための長方形の枠）──
    {"name": "photo-frame-polaroid", "bg_color": "black",
     "what": "**黒い背景の上に、白く塗りつぶされたポラロイド型のフォトフレーム。中央に黒い長方形（写真を入れるエリア）**。"
             "上の枠は細め、下の枠は広め（ポラロイドのキャプションエリア）、ポラロイドの本体は全面白で塗りつぶされている。"
             "中央の黒長方形が写真エリア。背景は完全に黒。**白と黒だけのシンプルな構造**で、グレーや中間色は使わない。"
             "わずかにラフな手作り感あり"},
    {"name": "photo-frame-yellow", "bg_color": "white",
     "what": "黄色いポップなフォトフレーム。中央に写真を入れるための透明な四角い空間、周りはサニーイエローの太めの枠、"
             "わずかに手作り感、シンプル。中央の透明部分は完全に透過"},
    {"name": "photo-frame-pink", "bg_color": "white",
     "what": "ピンクのポップなフォトフレーム。中央に写真を入れるための透明な四角い空間、周りはホットピンクの太めの枠、"
             "わずかに手作り感、シンプル。中央の透明部分は完全に透過"},
    {"name": "photo-frame-purple", "bg_color": "white",
     "what": "パープルのポップなフォトフレーム。中央に写真を入れるための透明な四角い空間、周りはビビッドパープルの太めの枠、"
             "わずかに手作り感、シンプル。中央の透明部分は完全に透過"},

    # ── Hero バッジ置換（紫バッジ「かわいいを世界中へ！」のユニーク版）──
    {"name": "hero-badge-cute", "bg_color": "white",
     "what": "Pop Bloomブランド用のかわいい円形バッジ。テキスト『かわいいを世界中へ！』入り。"
             "Y2K風の手描きユニークフォント、紫やピンクや黄色のカラフル配色、回転して斜めに配置されている雰囲気。"
             "シンプルな円形ベース、テキストがメイン。装飾的なバッジ風デザイン"},
]


PROMPT_TEMPLATE = """\
このモック画像をもとに、LPページをコーディングで再現したいです。
そのために使えるクリーンな単体パーツが欲しいので、抽出してください。

【今回欲しいパーツ】
{what}

【条件】
- モックのパーツの色・形・テイストを、そのまま再現してください
- 他の要素（モデル、商品、ステッカー、背景など）がパーツに重なっている場合は、
  パーツの該当部分を背景として補完して、単体できれいに使える状態にしてください
- 出力背景は「{bg_color}色」にしてください
  （理由: 後で背景透過処理をするため、パーツ本体と背景色が被らないようにする）
- 出力は、パーツだけが中央に大きく配置された画像
- LP実装にそのまま貼り付けて使える、クリーンな単体素材として出力
"""


def generate(client: OpenAI, asset: dict, skip_existing: bool = True) -> Path | None:
    name = asset["name"]
    category = category_for(name)
    # 元画像は originals/{category}/{name}.png に直接保存
    out_dir = ORIGINALS_DIR / category if category else ASSETS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{name}.png"

    if skip_existing and out_path.exists():
        print(f"  ⏭  スキップ: {name} (既存)")
        return out_path

    prompt = PROMPT_TEMPLATE.format(**asset)
    print(f"  ⚙️  生成中: {name} (bg={asset['bg_color']})")

    try:
        with open(MOCK_PATH, "rb") as f:
            result = client.images.edit(
                model="gpt-image-2",
                image=f,
                prompt=prompt,
                size="1024x1024",
                quality="low",
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
    print(f"    → 保存 ({len(image_bytes) / 1024:.0f} KB)")
    return out_path


def make_transparent(in_path: Path, out_path: Path, bg_color: str) -> None:
    """背景色を透過にする処理。chroma-aware: 色のあるピクセルは保護。"""
    img = Image.open(in_path).convert("RGBA")
    arr = np.array(img)

    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    if bg_color == "white":
        # 白に近い & 彩度低い ピクセルを透過
        is_bg = (r > 235) & (g > 235) & (b > 235)
    elif bg_color == "black":
        # 黒に近い & 彩度低い ピクセルを透過
        is_bg = (r < 25) & (g < 25) & (b < 25)
    else:
        print(f"    × 不明な bg_color: {bg_color}")
        return

    arr[is_bg, 3] = 0  # アルファ0で透過
    Image.fromarray(arr).save(out_path, "PNG")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--regenerate", action="store_true", help="既存ファイルも再生成")
    parser.add_argument("--transparent-only", action="store_true", help="生成スキップ、透過処理だけ")
    args = parser.parse_args()

    if not MOCK_PATH.exists():
        print(f"エラー: モック画像が見つかりません: {MOCK_PATH}")
        sys.exit(1)

    skip_existing = not args.regenerate

    # === Step 1: 素材生成 ===
    if not args.transparent_only:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print(f"エラー: OPENAI_API_KEY が見つかりません。{ENV_PATH} を確認してください。")
            sys.exit(1)

        client = OpenAI(api_key=api_key)

        print(f"=== Step 1: 素材生成 ({len(ASSETS)} 点) ===")
        print(f"入力モック: {MOCK_PATH.name}")
        print(f"出力先: {ASSETS_DIR}")
        print()

        for i, asset in enumerate(ASSETS, 1):
            print(f"[{i}/{len(ASSETS)}]", end=" ")
            generate(client, asset, skip_existing=skip_existing)

    # === Step 2: 透過処理 ===
    print("\n=== Step 2: 透過処理 ===")
    print(f"出力先: {TRANSPARENT_DIR}")
    print()

    transparent_count = 0
    for asset in ASSETS:
        name = asset["name"]
        category = category_for(name)

        # 元画像は originals/{category}/{name}.png にあるはず
        in_path = (ORIGINALS_DIR / category / f"{name}.png") if category else (ASSETS_DIR / f"{name}.png")
        # 透過先も transparent/{category}/{name}.png に直接保存
        out_dir = TRANSPARENT_DIR / category if category else TRANSPARENT_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{name}.png"

        if not in_path.exists():
            print(f"  ⚠️  スキップ: {name} (元ファイルなし: {in_path})")
            continue
        try:
            make_transparent(in_path, out_path, asset["bg_color"])
            print(f"  ✅ 透過: {category}/{name} (bg={asset['bg_color']})")
            transparent_count += 1
        except Exception as e:
            print(f"  × 失敗: {name} — {e}")

    print(f"\n完了！ 透過処理: {transparent_count}/{len(ASSETS)} 点")


if __name__ == "__main__":
    main()
