# 大喜利けいこ場

`odai.json`（過去の大喜利ファイルから抽出したお題 2,264問 / 回答 18,959件）から
お題をランダムに出題し、自分で回答を書いたあとに「ファイルにあった答え」を見比べる練習アプリ。
仕様は `大喜利アプリ_仕様書.md`。

## 使う

**正式な実装は GitHub Pages で公開している静的ページです。** サーバ不要・iPhone含む
どのブラウザからでも固定URLで開けます。

→ `docs/index.html` を GitHub Pages で公開したURL（リポジトリの Settings → Pages で確認）

- お題データはページ自体に同梱されているので、開けばすぐ遊べる（通信不要）。
- 回答の控えはこの端末のブラウザ（`localStorage`）に保存される。サーバへの送信は無い。
- 回答するまで答えはどこにも描画されない。

## 使い方

- 上部の **出典フィルタ** でお題の出どころを絞る。既定は「茶屋を除く」（茶屋は
  全体の91%を占める短文スタイルのため）。
- 回答を書いて **回答する**。押すまでファイルの答えは見えない。
- 書かずに次へ行くなら **パス**。パス・回答済みのお題は同じセッション中に再出題されない。
- PCブラウザでは `Ctrl/Cmd + Enter` で回答、`→` でパスもできる（タッチ端末では非表示）。

## 未実装

**AIの講評**（仕様書3章）。理論ファイル2本を system プロンプトにプロンプトキャッシュ付きで載せ、
素材×飛躍×表現の3変数・被り度・改善案を返す機能はまだ入っていない。UI上は該当セクションに
プレースホルダが出る。

## お題データの再生成・ページの作り直し

元ファイルを更新したら:

```
python extract_odai.py <お題ファイルのあるフォルダ> -o odai.json
python build_pages.py
```

1つ目で `odai.json` を再生成し（`ハシリドコロ_大喜利理論_1 / _2` は自動で除外される）、
2つ目で `docs/index.html`（GitHub Pages が配信する実体）を作り直す。
`docs/index.html` は生成物なので、手で直接編集せず `page.tpl.html` を編集して
`build_pages.py` を再実行すること。

## 構成

| ファイル | 中身 |
|---|---|
| `docs/index.html` | **GitHub Pages が配信する本体**（`page.tpl.html` + `odai.json` から生成） |
| `page.tpl.html` | `docs/index.html` の元になるテンプレート |
| `build_pages.py` | `page.tpl.html` + `odai.json` → `docs/index.html` を生成するスクリプト |
| `odai.json` | 抽出済みお題データ |
| `extract_odai.py` | `odai.json` の生成スクリプト |
| `ハシリドコロ_大喜利理論_1.txt` / `_2.txt` | 講評の評価軸に使う理論文書（講評機能は未実装） |

### 参考: ローカルFlask版（任意）

デスクトップでサーバを立てて動かしたい場合向けに、同等機能の Flask 版も残してある
（`app.py` + `templates/index.html`）。回答ログは `history.jsonl` に追記される。
iPhone単体で使う分には不要 — 上記の GitHub Pages 版だけで完結する。

```
pip install -r requirements.txt
python app.py     # → http://localhost:5000
```

| エンドポイント | 中身 |
|---|---|
| `GET /api/odai?exclude=茶屋` | ランダムなお題1問（`answers` は返さない） |
| `GET /api/odai/<id>/answers` | そのお題の答え |
| `POST /api/history` | `{odai_id, answer}` を `history.jsonl` に追記 |
| `GET /api/sources` | 出典一覧（件数付き） |
| `POST /api/reset` | 出題済みの記録をクリア |

## 直した不具合

- **お題と関係ない断片が「答え」として混ざる**（2024/08/28）。`extract_odai.py` に、
  `【画像】`や`【2回戦】`のような4文字未満の区切り見出しが `continue` されずに素通りし、
  前のお題の回答として誤って追加されるバグがあった（2,266問中78件が該当）。
  `odai.json` から該当データを除去し、抽出スクリプトと `build_pages.py` の両方に
  再発防止のフィルタを入れた。
