#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""data/ の4ファイル（動画管理表CSV・公開動画一覧JSON）を最新化する。
外部ライブラリ不要（urllib標準ライブラリのみ）・ログイン不要。

公開動画一覧には各動画の公開日時(JST)も入れる。動画の公開日はシートの「投稿日」と
一致する運用（公開予約した日からずれない）なので、タイトルの言い回しに頼らず日付だけで
回と動画を突き合わせられる。日付はwatchページから1本ずつ取るが、一度取れたものは
使い回すので、日々の更新で増えるリクエストは新しく公開された本数だけ。

対象外（このスクリプトでは更新しない）:
  - data/cc_studio_videos.json / aa_studio_videos.json
    YouTube Studioはチャンネル所有者ログインが要るため自動化していない。
    公開日での照合が効くので通常は使わない、取りこぼし時のフォールバック。

使い方:
    python3 scripts/refresh_data.py
"""
import datetime
import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

SHEETS = {
    "cc_episodes.csv": "12o5YfZARlIXjcF2h9ObBgNzaM5wQLmN4berI6AUCwYo",
    "aa_episodes.csv": "1jMuj5XoTHtSwsmdPpR035TzwPyErpSdEg3Si5VC8bvA",
}
CHANNELS = {
    "cc_youtube_videos.json": "n8nchannel",
    "aa_youtube_videos.json": "aiagent-kawaru",
}


def _get(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=20) as res:
        return res.read()


def _write_atomic(path, text):
    """同ディレクトリの一時ファイルへ書いてから置換する。

    直接 open(path,"w") すると、書き込み途中で落ちたときに欠けた内容が残る。
    4ファイルのうち一部だけ新しいという不整合も避けたいので、
    「検証を通ったものだけを最後に置換する」形にしている。
    """
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def _guard_shrink(label, old, new, ratio=0.8):
    """前回より件数が大きく減っていたら中断する。

    ネットワークやAPI側の不調で「例外にはならないが中身が欠けた」応答が返ることがあり、
    それをそのまま書くと公開サイトから配布回が消える。動画一覧もシートも通常は増える一方
    なので、2割以上減っていたら取得失敗とみなす。
    """
    if old and new < old * ratio:
        raise RuntimeError(
            f"{label}: 件数が {old} → {new} に急減した。"
            "取得内容が欠けている可能性があるため書き込みを中断"
        )


def refresh_sheet(fname, sheet_id):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
    body = _get(url)
    text = body.decode("utf-8")
    if not text.strip() or "<html" in text[:200].lower():
        raise RuntimeError(f"{fname}: CSVではなくHTMLが返ってきた（共有設定が変わった可能性）")
    path = os.path.join(DATA, fname)
    n = text.count("\n")
    old = 0
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = f.read().count("\n")
    _guard_shrink(fname, old, n)
    _write_atomic(path, text)
    print(f"  {fname}: {n}行")


def _find_grids(o):
    out = []
    def walk(x):
        if isinstance(x, dict):
            if "richGridRenderer" in x:
                out.append(x["richGridRenderer"])
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(o)
    return out


def _extract_page(contents, seen):
    """richItemRenderer(lockupViewModel)からid・titleを拾い、継続tokenを返す。"""
    token = None
    for it in contents:
        lvm = (it.get("richItemRenderer", {}).get("content", {}).get("lockupViewModel"))
        if lvm and lvm.get("contentType") == "LOCKUP_CONTENT_TYPE_VIDEO":
            vid = lvm.get("contentId")
            title = (lvm.get("metadata", {}).get("lockupMetadataViewModel", {})
                     .get("title", {}).get("content"))
            if vid and title and vid not in seen:
                seen[vid] = title
        cont = it.get("continuationItemRenderer")
        if cont:
            token = (cont.get("continuationEndpoint", {})
                     .get("continuationCommand", {}).get("token"))
    return token


JST = datetime.timezone(datetime.timedelta(hours=9))

# 公開日の取得に使ってよい時間の上限（チャンネルごと・秒）。
# 1本あたり1リクエストなので、キャッシュが空の状態（初回・data/を作り直した直後）だと
# 200本超を取りに行くことになり、回線が不調だと日次更新が何十分も止まりかねない。
# 打ち切っても日付が空のまま残るだけで、次回の実行で続きから取り直せる。
DATE_BUDGET_SEC = 90


def _publish_moment(vid):
    """動画の公開日時(JST)を (YYYY-MM-DD, HH:MM) で返す。取れなければ (None, None)。

    公開日は視聴者から見える確定した事実で、シートの投稿日とずれない。
    時刻も持つのは、同じ日に2本公開された日の区別に要るため——19:00が定期回、
    昼や早朝に出るのがモデル発表などの臨時回で、時刻を見ないとどちらの回の
    プレゼントか決められない（決められないまま一覧の並び順に任せると、
    YouTube側の並びが変わった日にサムネが入れ替わる）。
    一覧ページ側は「3週間前」のような相対表記しか持たないため、watchページの
    publishDate（ISO8601・タイムゾーン付き）を見る。
    """
    try:
        html = _get(f"https://www.youtube.com/watch?v={vid}").decode("utf-8", "replace")
    except (urllib.error.URLError, OSError):
        return None, None
    m = re.search(r'"publishDate":"([^"]+)"', html) or re.search(r'"uploadDate":"([^"]+)"', html)
    if not m:
        return None, None
    try:
        dt = datetime.datetime.fromisoformat(m.group(1))
    except ValueError:
        return None, None
    if dt.tzinfo is not None:
        dt = dt.astimezone(JST)
    return dt.date().isoformat(), dt.strftime("%H:%M")


def refresh_youtube_list(fname, handle, max_pages=30):
    html = _get(f"https://www.youtube.com/@{handle}/videos",
                headers={"Accept-Language": "ja-JP,ja;q=0.9"}).decode("utf-8")

    m = re.search(r"var ytInitialData = (\{.*?\});</script>", html)
    if not m:
        raise RuntimeError(f"{fname}: ytInitialDataが見つからない（YouTube側の構造変更の可能性）")
    data = json.loads(m.group(1))

    api_key_m = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', html)
    ctx_m = re.search(r'"INNERTUBE_CONTEXT":(\{.*?\}),"INNERTUBE_CONTEXT_CLIENT_NAME"', html)
    if not api_key_m or not ctx_m:
        raise RuntimeError(f"{fname}: INNERTUBE_API_KEY/CONTEXTが見つからない")
    api_key = api_key_m.group(1)
    context = json.loads(ctx_m.group(1))

    grids = _find_grids(data)
    if not grids:
        raise RuntimeError(f"{fname}: richGridRendererが見つからない")

    seen = {}
    token = _extract_page(grids[0].get("contents", []), seen)

    rounds = 0
    while token and rounds < max_pages:
        rounds += 1
        body = _get(
            f"https://www.youtube.com/youtubei/v1/browse?key={api_key}",
            data=json.dumps({"context": context, "continuation": token}).encode(),
            headers={"Content-Type": "application/json"},
        )
        res = json.loads(body)
        actions = res.get("onResponseReceivedActions") or res.get("onResponseReceivedEndpoints") or []
        items = None
        for act in actions:
            if "appendContinuationItemsAction" in act:
                items = act["appendContinuationItemsAction"]["continuationItems"]
                break
            if "reloadContinuationItemsCommand" in act:
                items = act["reloadContinuationItemsCommand"]["continuationItems"]
                break
        if not items:
            break
        token = _extract_page(items, seen)

    path = os.path.join(DATA, fname)
    old, known = 0, {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                prev = json.load(f)
            old = len(prev)
            known = {v["id"]: (v["date"], v["time"])
                     for v in prev if v.get("date") and v.get("time")}
        except (ValueError, OSError, KeyError):
            old, known = 0, {}  # 前回分が壊れていても今回の取得は妨げない

    out, fetched, deferred = [], 0, 0
    deadline = time.monotonic() + DATE_BUDGET_SEC
    for vid, title in seen.items():
        date, tm = known.get(vid, (None, None))
        if not date:
            if time.monotonic() < deadline:
                date, tm = _publish_moment(vid)
                fetched += 1
            else:
                deferred += 1
        out.append({"id": vid, "title": title, "date": date, "time": tm})

    _guard_shrink(fname, old, len(out))
    _write_atomic(path, json.dumps(out, ensure_ascii=False, indent=1))
    n_dated = sum(1 for v in out if v["date"])
    tail = f" / 時間切れで次回送り {deferred}件" if deferred else ""
    print(f"  {fname}: {len(out)}件（{rounds}ページ）/ "
          f"公開日あり {n_dated}件（今回取得 {fetched}件）{tail}")


def main():
    print("動画管理表CSVを更新:")
    for fname, sheet_id in SHEETS.items():
        refresh_sheet(fname, sheet_id)

    print("YouTube公開動画一覧を更新:")
    for fname, handle in CHANNELS.items():
        refresh_youtube_list(fname, handle)

    print("\ndata/ 更新完了")


if __name__ == "__main__":
    main()
