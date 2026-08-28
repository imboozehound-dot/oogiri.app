#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大喜利ファイル → odai.json 変換スクリプト

使い方:
    python extract_odai.py <お題ファイルのあるディレクトリ> [-o odai.json]

「ハシリドコロ_大喜利理論_1 / _2」は自動で除外する（これらは評価軸用の資料）。
"""
import re, os, json, argparse, collections

EXCLUDE_PREFIX = "ハシリドコロ"

# 答えではない「見出し行」を落とすためのパターン
SECTION = re.compile(
    r'^('
    r'\d+[\.．/／]\d+.*'                                  # 8.11 夏270 / 74/39
    r'|[☀️🌙🌞🌜⭐️☆★🌸]+'                                  # 時間帯マーク等
    r'|(地上|対流圏|成層圏|中間圏|熱圏|外気圏)[\s　]*(グループ)?[\s　]*\d*'
    r'|予選.*回戦|準?決勝.*|本戦.*|\d+回戦'
    r'|\d+\s*'
    r'|https?://.*'
    r')$'
)

def clean_odai(s: str) -> str:
    s = re.sub(r'^\d+[\.．]?\s*', '', s)   # 先頭の通し番号 "1【…】"
    return re.sub(r'\s+', ' ', s).strip()

def parse_file(path: str, fname: str):
    text = open(path, encoding='utf-8').read().replace('\r\n', '\n')
    items, cur = [], None
    buf = None                              # 複数行にまたがる【お題】の受け皿

    for raw in text.split('\n'):
        line = raw.strip()

        # --- 複数行お題の継続 ---
        if buf is not None:
            buf += line
            if '】' in buf:
                body, _, rest = buf.partition('】')
                cur = {'source': fname, 'odai': clean_odai(body.lstrip('【')),
                       'meta': rest.strip(), 'answers': []}
                items.append(cur)
                buf = None
            continue

        # --- お題の開始 ---
        if '【' in line:
            head = line[line.index('【'):]
            if '】' in head:
                body, _, rest = head.partition('】')
                title = body.lstrip('【')
                if len(title) >= 4:         # 【発射台】等の見出しを除外
                    cur = {'source': fname, 'odai': clean_odai(title),
                           'meta': rest.strip(), 'answers': []}
                    items.append(cur)
                # 4文字未満は【画像】【2回戦】等の区切り見出し。
                # 新しいお題にはせず、かといって前のお題の回答としても
                # 拾わない（そのまま続けると下の回答処理に落ちてしまう）。
                continue
            else:
                buf = head
                continue

        if not line or cur is None:
            continue
        if SECTION.match(line):
            continue

        # --- 回答行 ---
        star = line[0] in '☆★⭐'
        s = line.lstrip('☆★⭐️ 　')
        # タブ / 全角2つ以上 / 半角3つ以上 の後ろは自分のコメント
        parts = re.split(r'\t+|　{2,}| {3,}', s)
        answer = parts[0].strip()
        comment = '　'.join(p.strip() for p in parts[1:] if p.strip())
        if answer:
            cur['answers'].append({'text': answer, 'comment': comment, 'star': star})

    return items

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('-o', '--out', default='odai.json')
    a = ap.parse_args()

    data = []
    for fname in sorted(os.listdir(a.src)):
        p = os.path.join(a.src, fname)
        if not os.path.isfile(p) or fname.startswith(EXCLUDE_PREFIX):
            continue
        data += parse_file(p, fname)

    data = [d for d in data if d['answers']]     # 回答ゼロ（URLのみ）のお題は除外
    for i, d in enumerate(data):
        d['id'] = i

    json.dump(data, open(a.out, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    c = collections.Counter(d['source'] for d in data)
    print(f'お題 {len(data)} / 回答 {sum(len(d["answers"]) for d in data)} '
          f'/ コメント付き {sum(1 for d in data for x in d["answers"] if x["comment"])}')
    for k, v in c.most_common():
        print(f'  {k:35} {v}')

if __name__ == '__main__':
    main()
