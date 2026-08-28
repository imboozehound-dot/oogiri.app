#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
odai.json を埋め込んだ単体HTML（docs/index.html）と、理論ファイル2本
（docs/theory1.txt, docs/theory2.txt、docs/theory1.html, docs/theory2.html）を書き出す。

GitHub Pages で配信するのはこの docs/ フォルダ。サーバ・ビルド不要で、
お題データはHTMLに同梱、理論ファイルは「Claudeに判定してもらう」ボタンが
押されたときに同一オリジンから fetch() される（日本語ファイル名だと
fetch時のURLエンコードが煩雑なので、docs/ 側だけASCII名にコピーする）。

.html 版は章番号にアンカー（id="1-12" 等）を振った閲覧用ページ。Claudeへの
プロンプトに「章番号を引用するときはこのURLへのMarkdownリンクにする」という
指示を入れておくことで、講評中の "(1-12)" のような引用がクリックできる
リンクになり、該当章にジャンプできる。

使い方:
    python build_pages.py

odai.json を更新したら（extract_odai.py で再抽出したら）、あるいは
理論ファイルを更新したら、このスクリプトを再実行すること。
"""
import html as htmlmod
import json
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "odai.json")
TEMPLATE = os.path.join(HERE, "page.tpl.html")
DOCS = os.path.join(HERE, "docs")
OUT = os.path.join(DOCS, "index.html")
THEORY_SRC = [
    os.path.join(HERE, "ハシリドコロ_大喜利理論_1.txt"),
    os.path.join(HERE, "ハシリドコロ_大喜利理論_2.txt"),
]
THEORY_TITLES = ["ハシリドコロ 大喜利理論 1", "ハシリドコロ 大喜利理論 2"]
THEORY_OUT_TXT = [os.path.join(DOCS, "theory1.txt"), os.path.join(DOCS, "theory2.txt")]
THEORY_OUT_HTML = [os.path.join(DOCS, "theory1.html"), os.path.join(DOCS, "theory2.html")]

# 見出し行: "1-12. 評価の多軸フレーム ― 総合点は存在しない" のような形。
# 目次にも同じ行が出るファイルがあるので、同じ番号が複数回出た場合は
# 最後（＝本文中の実見出し）を採用する。
HEADING = re.compile(r'^(\d+-\d+[a-z]?)\.\s*(.*)$')
# スクレイプ由来のページ送りノイズ（note.com のURL[+日時]＋ページ番号の2行）を除去
NOTE_URL = re.compile(r'^https?://note\.com/\S+')
PAGE_NUM = re.compile(r'^\d+\s*/\s*\d+\s*ページ$')

# 【画像】【2回戦】等、区切り見出しがパースの穴で回答として紛れ込むことがある。
# extract_odai.py 側でも直しているが、ビルド時にも二重に弾いておく。
BRACKET_HEADER = re.compile(r'^【.{0,3}】$')


def load_items():
    raw = json.load(open(SRC, encoding="utf-8"))
    items = []
    for i, d in enumerate(raw):
        if not isinstance(d, dict):
            continue
        odai = str(d.get("odai") or "").strip()
        if not odai:
            continue
        answers = []
        for a in d.get("answers") or []:
            if not isinstance(a, dict):
                continue
            t = str(a.get("text") or "").strip()
            if not t or BRACKET_HEADER.match(t):
                continue
            answers.append([t, str(a.get("comment") or "").strip()])
        if not answers:
            continue
        items.append({
            "i": d["id"] if isinstance(d.get("id"), int) else i,
            "s": str(d.get("source") or "").strip(),
            "o": odai,
            "m": str(d.get("meta") or "").strip(),
            "a": answers,
        })
    return items


def parse_theory(text):
    """理論テキストを (見出し無しの前書き, [(番号, タイトル, 本文行のリスト), ...]) に分ける。"""
    lines = text.replace("\r\n", "\n").split("\n")

    # 同じ番号が複数回出たら最後（本文の実見出し）を使う
    last_pos = {}
    for i, line in enumerate(lines):
        m = HEADING.match(line.strip())
        if m:
            last_pos[m.group(1)] = i

    # 出現位置順に並べ、見出し間を本文として切り出す
    ordered = sorted(last_pos.items(), key=lambda kv: kv[1])
    preamble = lines[:ordered[0][1]] if ordered else lines[:]
    sections = []
    for idx, (num, pos) in enumerate(ordered):
        title = HEADING.match(lines[pos].strip()).group(2)
        end = ordered[idx + 1][1] if idx + 1 < len(ordered) else len(lines)
        body = lines[pos + 1:end]
        sections.append((num, title, body))
    return preamble, sections


def clean_lines(lines):
    """note.com のURL＋ページ番号のノイズ行を落とす。"""
    out = []
    i = 0
    while i < len(lines):
        if NOTE_URL.match(lines[i].strip()) and i + 1 < len(lines) and PAGE_NUM.match(lines[i + 1].strip()):
            i += 2
            continue
        out.append(lines[i])
        i += 1
    return out


def render_block(lines):
    text = "\n".join(clean_lines(lines)).strip("\n")
    return htmlmod.escape(text)


THEORY_PAGE_TPL = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<title>{title}｜大喜利けいこ場</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Shippori+Mincho+B1:wght@500;700&family=Zen+Kaku+Gothic+New:wght@400;500;700&display=swap">
<style>
:root {{
  --paper: #eae7e1; --surface: #f4f2ee; --ink: #1a1613; --ink-2: #5c544c;
  --ink-3: #8b8279; --hi: #a8232b; --rule: #d6d0c7; --rule-2: #c4bdb2;
}}
@media (prefers-color-scheme: dark) {{
  :root {{ --paper: #191614; --surface: #221e1b; --ink: #ebe6de; --ink-2: #a79c8f;
           --ink-3: #7a7065; --hi: #d9525a; --rule: #332d28; --rule-2: #443c35; }}
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; background: var(--paper); color: var(--ink);
  font-family: "Zen Kaku Gothic New", "Hiragino Sans", "Yu Gothic", sans-serif;
  font-size: 15px; line-height: 1.8; -webkit-font-smoothing: antialiased;
}}
header {{
  position: sticky; top: 0; background: var(--paper);
  border-bottom: 1px solid var(--rule); padding: 12px 20px; z-index: 10;
}}
header a {{ color: var(--ink-2); font-size: 13px; text-decoration: none; border-bottom: 1px solid var(--rule-2); }}
header a:hover {{ color: var(--hi); border-color: var(--hi); }}
main {{ max-width: 720px; margin: 0 auto; padding: 28px 20px 80px; }}
h1 {{
  font-family: "Shippori Mincho B1", serif; font-size: 22px;
  border-left: 3px solid var(--hi); padding-left: 14px; margin: 0 0 24px;
}}
.preamble {{ color: var(--ink-2); font-size: 13.5px; white-space: pre-wrap; margin-bottom: 32px; }}
nav.toc {{
  background: var(--surface); border: 1px solid var(--rule); border-radius: 6px;
  padding: 16px 20px; margin-bottom: 36px; font-size: 13px;
}}
nav.toc summary {{ cursor: pointer; color: var(--ink-2); font-weight: 700; }}
nav.toc ol {{ margin: 12px 0 0; padding-left: 1.4em; }}
nav.toc li {{ margin: 4px 0; }}
nav.toc a {{ color: var(--ink); text-decoration: none; }}
nav.toc a:hover {{ color: var(--hi); }}
nav.toc .num {{ color: var(--hi); font-variant-numeric: tabular-nums; margin-right: .4em; }}
section {{ padding: 26px 0; border-top: 1px solid var(--rule); scroll-margin-top: 64px; }}
section:target {{ background: color-mix(in srgb, var(--hi) 10%, transparent); }}
h2 {{
  font-family: "Shippori Mincho B1", serif; font-size: 18px; margin: 0 0 14px;
  display: flex; gap: .5em; align-items: baseline;
}}
h2 .num {{ color: var(--hi); font-size: 14px; font-weight: 700; font-variant-numeric: tabular-nums; }}
.body {{ white-space: pre-wrap; word-break: break-word; }}
</style>
</head>
<body>
<header><a href="index.html">← けいこ場に戻る</a></header>
<main>
  <h1>{title}</h1>
  <div class="preamble">{preamble}</div>
  <nav class="toc">
    <details open><summary>目次（{count}章）</summary>
    <ol>{toc_items}</ol>
    </details>
  </nav>
  {sections}
</main>
</body>
</html>
"""


def build_theory_html(src_path, title, out_path):
    text = open(src_path, encoding="utf-8").read()
    preamble_lines, sections = parse_theory(text)

    toc_items = "".join(
        f'<li><a href="#{htmlmod.escape(num)}"><span class="num">{htmlmod.escape(num)}</span>'
        f'{htmlmod.escape(t)}</a></li>'
        for num, t, _ in sections
    )
    section_html = "".join(
        f'<section id="{htmlmod.escape(num)}"><h2><span class="num">{htmlmod.escape(num)}</span>'
        f'{htmlmod.escape(t)}</h2><div class="body">{render_block(body)}</div></section>'
        for num, t, body in sections
    )

    html = THEORY_PAGE_TPL.format(
        title=htmlmod.escape(title),
        preamble=render_block(preamble_lines),
        count=len(sections),
        toc_items=toc_items,
        sections=section_html,
    )
    open(out_path, "w", encoding="utf-8").write(html)
    print(f"→ {out_path}  ({len(sections)}章, {os.path.getsize(out_path) / 1e3:.0f} KB)")


def main():
    items = load_items()
    payload = json.dumps(items, ensure_ascii=False, separators=(",", ":"))
    print(f"お題 {len(items)} / 回答 {sum(len(x['a']) for x in items)} "
          f"/ 同梱データ {len(payload.encode('utf-8')) / 1e6:.2f} MB")

    html = open(TEMPLATE, encoding="utf-8").read()
    html = html.replace("/*__ODAI_DATA__*/", payload)

    os.makedirs(DOCS, exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(html)
    print(f"→ {OUT}  ({os.path.getsize(OUT) / 1e6:.2f} MB)")

    for src, dst in zip(THEORY_SRC, THEORY_OUT_TXT):
        shutil.copyfile(src, dst)
        print(f"→ {dst}  ({os.path.getsize(dst) / 1e3:.0f} KB)")

    for src, title, dst in zip(THEORY_SRC, THEORY_TITLES, THEORY_OUT_HTML):
        build_theory_html(src, title, dst)


if __name__ == "__main__":
    main()
