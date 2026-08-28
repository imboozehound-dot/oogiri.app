#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
odai.json を埋め込んだ単体HTML（docs/index.html）と、理論ファイル2本
（docs/theory1.txt, docs/theory2.txt）を書き出す。

GitHub Pages で配信するのはこの docs/ フォルダ。サーバ・ビルド不要で、
お題データはHTMLに同梱、理論ファイルは「Claudeに判定してもらう」ボタンが
押されたときに同一オリジンから fetch() される（日本語ファイル名だと
fetch時のURLエンコードが煩雑なので、docs/ 側だけASCII名にコピーする）。

使い方:
    python build_pages.py

odai.json を更新したら（extract_odai.py で再抽出したら）、あるいは
理論ファイルを更新したら、このスクリプトを再実行すること。
"""
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
THEORY_OUT = [os.path.join(DOCS, "theory1.txt"), os.path.join(DOCS, "theory2.txt")]

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

    for src, dst in zip(THEORY_SRC, THEORY_OUT):
        shutil.copyfile(src, dst)
        print(f"→ {dst}  ({os.path.getsize(dst) / 1e3:.0f} KB)")


if __name__ == "__main__":
    main()
