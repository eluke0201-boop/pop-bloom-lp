# Pop Bloom — Bright Stuff for Every Day

架空のZ世代女子向けカラフル雑貨ショップ **Pop Bloom** のランディングページ。  
ポートフォリオ作品として、AI画像生成（gpt-image-2）+ HTML/CSS素のままで実装。

## 🌐 Live Demo

**👉 https://pop-bloom-2.vercel.app**

## 🎨 デザイン方向性

- **Y2K Pop Maximalism** — カラフル、コラージュ感、ハンドメイド風
- **配色**: クリーム白 + ビビッドオレンジ / ピンク / パープル / ライム / イエロー
- **ターゲット**: 10代後半〜20代前半の女子

## 🛠 技術スタック

- HTML / CSS / 一部 JavaScript（素のまま、フレームワーク非依存）
- gpt-image-2 で全イラスト・装飾・写真を生成
- Python + PIL で素材のクロップ・透過処理
- レスポンシブ対応（1440 / 1280 / 1024 / 768 / 480 の5段階）

## 📁 ディレクトリ構成

```
pop-bloom-2/
├── site-design/         # メインのLP HTML/CSS
├── assets/
│   ├── transparent/     # 透過処理済みPNG素材（60点超）
│   └── preview.html     # 素材一覧プレビュー
├── images/              # LPデザインモック
├── tools/               # 素材生成・整理スクリプト
└── README.md
```

## 🌟 特徴

- **26種類の装飾ステッカー** をすべて使用（バリエーション豊富）
- **CSS-only アニメーション** 5種（float / spin / twinkle / drift / wiggle）
- **viewport全幅の背景グラデーション** でセクション境界をまたぐY2Kな世界観
- **ホバーインタラクション** 全要素（NAV / CTA / カード / SNS / 写真）
- **SEO/OGP/a11y** 完備（h1+h2, aria-disabled, demo-banner, OGP, favicon）

## 🚀 ローカル起動

```bash
python -m http.server 8776 --directory .
# → http://localhost:8776/site-design/index.html
```

## 📝 ライセンス

このプロジェクトはデザインモックです。リンク先・購入機能・SNSアカウントはすべてダミー。  
ステッカー素材・写真素材は AI 生成、商業利用は不可。

---

**🎨 Made with Claude Code + gpt-image-2**
