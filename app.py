#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大喜利練習アプリ

    python app.py   →  http://localhost:5000

odai.json からお題をランダムに出題し、自分で回答を書いたあとに
「ファイルにあった答え」を見比べる。回答は history.jsonl に追記される。

講評（Anthropic API）はこの版では未実装。
"""
import json
import os
import random
import secrets
import threading
from datetime import datetime

from flask import Flask, jsonify, render_template, request, session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ODAI_PATH = os.path.join(BASE_DIR, "odai.json")
HISTORY_PATH = os.path.join(BASE_DIR, "history.jsonl")

# 仕様 1-2: 茶屋ファイルは全体の91%を占める短文スタイルなので既定では除外する
DEFAULT_EXCLUDE = "茶屋"

app = Flask(__name__)
# ローカル実行専用。セッション（出題済みお題の管理）にしか使わない。
app.secret_key = os.environ.get("OOGIRI_SECRET_KEY") or secrets.token_hex(16)


# --------------------------------------------------------------------------
# データ読み込み
# --------------------------------------------------------------------------
def load_odai(path=ODAI_PATH):
    """odai.json を読み、壊れたレコードを落として返す。

    仕様 1-2: パースは完全ではない（長文の散文が回答欄に紛れている等）。
    異常データでも落ちないよう、ここで最低限の正規化だけしておく。
    """
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

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
            text = str(a.get("text") or "").strip()
            if not text:
                continue
            answers.append({
                "text": text,
                # comment は自分の書き込み。回答本文とは別物として扱う
                "comment": str(a.get("comment") or "").strip(),
                # star は品質評価ではない（茶屋では時間帯の区切り記号）。
                # 並び替え・強調には使わず、そのまま保持だけする。
                "star": bool(a.get("star")),
            })
        if not answers:
            continue

        items.append({
            "id": d["id"] if isinstance(d.get("id"), int) else i,
            "source": str(d.get("source") or "").strip(),
            "odai": odai,
            "meta": str(d.get("meta") or "").strip(),
            "answers": answers,
        })
    return items


ODAI = load_odai()
ODAI_BY_ID = {d["id"]: d for d in ODAI}
SOURCES = sorted({d["source"] for d in ODAI if d["source"]})

# 出題済みお題のセッション管理（回答済み・パス済みともに再出題しない）
_seen_lock = threading.Lock()
SEEN = {}  # session_token -> set[int]


def seen_set():
    token = session.get("token")
    if not token:
        token = secrets.token_hex(8)
        session["token"] = token
    with _seen_lock:
        return SEEN.setdefault(token, set())


def matching(source=None, exclude=None):
    """出典フィルタを適用したお題リスト。

    source  … 完全一致する出典だけに絞る（"" / None なら絞らない）
    exclude … 出典名にこの文字列を含むものを除外する
    """
    out = ODAI
    if source:
        out = [d for d in out if d["source"] == source]
    if exclude:
        out = [d for d in out if exclude not in d["source"]]
    return out


def filter_args():
    source = (request.args.get("source") or "").strip()
    if "exclude" in request.args:
        exclude = (request.args.get("exclude") or "").strip()
    else:
        exclude = DEFAULT_EXCLUDE
    # 出典を名指ししているときに既定の除外が効くと 0 件になりうるので外す
    if source:
        exclude = ""
    return source, exclude


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template(
        "index.html",
        sources=SOURCES,
        default_exclude=DEFAULT_EXCLUDE,
    )


@app.route("/api/sources")
def api_sources():
    """出典フィルタ用の一覧。件数付き。"""
    counts = {}
    for d in ODAI:
        counts[d["source"]] = counts.get(d["source"], 0) + 1
    return jsonify({
        "total": len(ODAI),
        "default_exclude": DEFAULT_EXCLUDE,
        "sources": [{"name": s, "count": counts[s]} for s in SOURCES],
    })


@app.route("/api/odai")
def api_odai():
    """ランダムなお題を1問返す。answers は含めない（先に見えると練習にならない）。"""
    source, exclude = filter_args()
    pool = matching(source, exclude)
    seen = seen_set()
    unseen = [d for d in pool if d["id"] not in seen]

    if not unseen:
        return jsonify({
            "odai": None,
            "remaining": 0,
            "total": len(pool),
            "exhausted": True,
        })

    d = random.choice(unseen)
    seen.add(d["id"])
    return jsonify({
        "odai": {
            "id": d["id"],
            "odai": d["odai"],
            "source": d["source"],
            "meta": d["meta"],
            "answer_count": len(d["answers"]),
        },
        # この1問を出した後に残っている数
        "remaining": len(unseen) - 1,
        "total": len(pool),
        "exhausted": False,
    })


@app.route("/api/odai/<int:odai_id>/answers")
def api_answers(odai_id):
    """そのお題の、ファイルにあった答え。回答ボタンを押した後にだけ取りに来る。"""
    d = ODAI_BY_ID.get(odai_id)
    if d is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "id": d["id"],
        "odai": d["odai"],
        "source": d["source"],
        "answers": d["answers"],
    })


@app.route("/api/history", methods=["POST"])
def api_history():
    """回答を history.jsonl に1行追記する。閲覧UIは無し（仕様 4）。"""
    body = request.get_json(silent=True) or {}
    odai_id = body.get("odai_id")
    answer = str(body.get("answer") or "").strip()
    d = ODAI_BY_ID.get(odai_id) if isinstance(odai_id, int) else None
    if d is None or not answer:
        return jsonify({"error": "odai_id と answer が必要です"}), 400

    record = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "odai_id": d["id"],
        "odai": d["odai"],
        "source": d["source"],
        "answer": answer,
        # 講評未実装のためスコアは空。実装後にここへ {"素材":..,"飛躍":..,"表現":..} が入る
        "scores": None,
    }
    with open(HISTORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return jsonify({"ok": True})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """出題済みの記録を捨てて、また最初から出題できるようにする。"""
    seen_set().clear()
    return jsonify({"ok": True})


if __name__ == "__main__":
    print(f"お題 {len(ODAI)} 問 / 出典 {len(SOURCES)} 種類")
    print("http://localhost:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
