# -*- coding: utf-8 -*-
"""動画（回）ごとのメタデータ（タイトル・公開日・サムネ）を、チャンネルの動画管理表
スプレッドシート（CSV）と、YouTubeチャンネルの実際の動画一覧（JSON）から組み立てる。

配布サイトの起点は「動画1本 = プレゼントのグループ」。No.は視聴者には意味がないため
サイトには出さず、あくまでフォルダ・原本の突き合わせキーとしてのみ使う。

データの作り方（このファイルは読むだけ。作り直す手順は配布サイト/MAINTAINER.md）:
  1. スプレッドシートを開き `.../export?format=csv&gid=0` に遷移 → ダウンロードされたCSVを
     data/cc_episodes.csv / data/aa_episodes.csv に置く
  2. チャンネル所有者アカウントで YouTube Studio のコンテンツ一覧
     （studio.youtube.com/channel/<ID>/videos/upload）を開き、1ページあたりの行数を50にして
     全ページの {videoId, title, date, status} を集め、
     data/cc_studio_videos.json / data/aa_studio_videos.json に保存
     （Studioの日付は実際の公開日そのもの＝公開スケジュール上の「投稿日」より正確）
  3. （補助）YouTubeチャンネルの公開動画一覧ページで ytInitialData + browse継続APIを叩いて
     {videoId, title} を集め、data/cc_youtube_videos.json / data/aa_youtube_videos.json に保存
     （Studioで見つからないときの最終フォールバックにのみ使う）

突き合わせ方針（優先順）:
  1. シートの「完成動画URL」列に実URLがあればそれを最優先で使う（確実）
  2. 無ければ、公開動画一覧の**公開日(JST)がシートのD列「投稿日」と完全一致**する動画を使う。
     公開は予約した日そのものに起きてずれない運用なので、日付は動かない事実として扱える。
     タイトルは社内の作業名（例:「Cloudflare最強」）と実タイトル（例:「【性能100倍】Codexを
     使う全人類は必ずコレと連携しておいてください」）で語彙が全く重ならないことがあり、
     タイトル一致に頼ると新しい回が丸ごと落ちる。日付ならその事故が起きない
  3. 同じ日に複数本ある場合だけ、その中でタイトルの特徴語の一致度で絞り込む
  4. 公開日が取れていない動画のために Studio データ（同日 → 前後1日）も残す
  5. それでも見つからないものだけ、公開動画一覧側で「投稿日でのランク（何番目に古いか）」を
     手がかりに、タイトルの特徴語（英数字・カタカナ・漢字複合語）の一致度で絞り込む
  6. それでも一致しないものは動画IDなし（サムネ非表示・タイトルと日付のみ表示）とする。
     誤った動画のサムネを出すより、出さない方が安全という判断
"""
import csv, datetime, json, math, os, re, unicodedata
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
# 実行環境のタイムゾーンに引きずられないよう日本時間で固定する。
# GitHub Actionsのランナーは UTC で動くため、date.today() だと 00:00〜09:00 JST の
# 実行が「前日」判定になり、その日公開済みの回が未公開扱いで落ちる。
JST = datetime.timezone(datetime.timedelta(hours=9))
TODAY = datetime.datetime.now(JST).date()

# 「日付の近さ×タイトル」で拾うときの条件。ここを緩めると誤った動画を掴み始める。
NEAR_DAYS = 2          # 投稿日からこの日数までしか候補にしない
NEAR_MIN_SCORE = 1.0   # タイトルに特徴語の一致が最低これだけ必要（0＝無関係は採らない）
NEAR_MIN_MARGIN = 0.5  # 2位との差がこれ未満＝どちらとも言えないので決めない
RANK_MIN_SCORE = 1.5   # 日付が全く使えないときの最後の手段。確信が持てなければ出さない

# 日付照合でも拾えなかった回の逃げ道。動画IDを個別に確認して書く。
# キー: (channel, No.) / 値: 確認できたvideoId
# 公開日での照合を入れた時点で、それまでの5件（cc 121・130 / aa 73・97・99）は
# すべて日付だけで同じ動画に解決できることを確認したため空にしてある。
MANUAL_OVERRIDES = {}

# 撮影資料フォルダ作成時点(旧命名規則)で No.XX_ が付いていなかったフォルダを、
# シート側のタイトル完全一致（全行検索・日付近傍に限らない）で事後的にNo.へ復元したもの。
# キー: フォルダ名 / 値: 復元できたNo.
FOLDER_NO_RECOVERY = {
    "20260723_claudecode_ループからグラフへ": 101,
    "20260723_kawaru_Codex全解説": 70,
    "20260703_claudecode_Loop入門": 81,
    "20260706_claudecode_未知を見つける": 84,
    "20260708_kawaru_Codex×X自動運用": 52,
    "20260727_claudecode_Fable5とOpus5ってどっちが最強": 109,
    "20260728_claudecode_Google Workspace Studio解説": 111,
    "20260728_kawaru_Codexで使える神プラグイン30選": 76,
}

_SHEETS = {
    "claudecode": ("cc_episodes.csv", "完成動画URL", "cc_youtube_videos.json", "cc_studio_videos.json"),
    "kawaru": ("aa_episodes.csv", "YouTubeリンク", "aa_youtube_videos.json", "aa_studio_videos.json"),
}


def _parse_date(s):
    m = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2})", s or "")
    return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def _tokens(s):
    s = unicodedata.normalize("NFKC", s or "")
    toks = set(t.lower() for t in re.findall(r"[A-Za-z][A-Za-z0-9.\-]{1,}|\d[\d.]{2,}", s))
    toks |= set(re.findall(r"[ァ-ヴー]{3,}", s))
    toks |= set(re.findall(r"[一-龠]{2,}", s))
    return toks


def _load_sheet(channel):
    fname, url_col, _, _ = _SHEETS[channel]
    rows = []
    with open(os.path.join(DATA, fname), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            no = (r.get("No.") or "").strip()
            if not no.isdigit():
                continue
            d = _parse_date(r.get("投稿日") or "")
            m = re.search(r"v=([\w-]{11})", r.get(url_col) or "")
            rows.append({
                "no": int(no), "date": d,
                "title": (r.get("タイトル名") or "").strip(),
                "vid": m.group(1) if m else None,
            })
    return rows


def _load_yt(channel):
    _, _, fname, _ = _SHEETS[channel]
    with open(os.path.join(DATA, fname), encoding="utf-8") as f:
        return json.load(f)


def _real_title_index(channel):
    """videoId → 実際にYouTubeへ出ているタイトル。

    シートの「タイトル名」は社内の作業用タイトル（例:「Grok Bot」）で、公開後の
    実タイトル（例:「【公式推奨】Claudeから神機能!? …」）とは別物。視聴者が動画を
    見分けられるのは実タイトルの方なので、動画IDが特定できた回はこちらを優先する。
    公開動画一覧を優先し、そこに無ければStudio側のタイトルで補う。
    """
    idx = {}
    _, _, _, studio_fname = _SHEETS[channel]
    studio_path = os.path.join(DATA, studio_fname)
    if os.path.exists(studio_path):
        with open(studio_path, encoding="utf-8") as f:
            for r in json.load(f):
                if r.get("status") != "公開予約":
                    idx[r["id"]] = r["title"]
    for v in _load_yt(channel):  # 公開一覧を後勝ちで上書き＝こちらを優先
        idx[v["id"]] = v["title"]
    return idx


def _yt_by_date(channel):
    """公開日(JST) → その日に公開された動画のリスト。

    公開日はシートのD列「投稿日」と一致する前提（公開予約した日にそのまま出る運用）。
    日付が取れていない動画（取得失敗・古い動画）は索引に入らず、後段の照合に回る。
    """
    by_date = {}
    for v in _load_yt(channel):
        d = _parse_date((v.get("date") or "").replace("-", "/"))
        if d:
            by_date.setdefault(d, []).append(v)
    return by_date


def _yt_dates(channel):
    """videoId → 公開日(JST)。日付が取れていない動画は入らない。"""
    out = {}
    for v in _load_yt(channel):
        d = _parse_date((v.get("date") or "").replace("-", "/"))
        if d:
            out[v["id"]] = d
    return out


def _pick_by_title(cands, title):
    """同日に複数本あるときだけ使う。特徴語が最も重なるものを選ぶ。
    どれとも1語も重ならないなら選ばない（誤った動画を割り当てない）。

    特徴語が同点で並んだときは公開時刻の遅い方を採る。同じ日に2本出る日は
    「19:00の定期回」と「モデル発表などを昼に出す臨時回」の組み合わせで、
    シート上は定期回の方がNo.が小さい（臨時回は後から行を足すため）。回はNo.の
    昇順に処理しているので、遅い時刻＝19:00の回を先に渡すのが正しい。
    実データ20日ぶんすべてこの並びだった。
    ここを一覧の並び順まかせにしてはいけない——YouTube側の並びが変わるだけで
    サムネが入れ替わるため（実測で cc No.96 と No.107 が入れ替わった）。
    """
    if len(cands) == 1:
        return cands[0]
    rt = _tokens(title)
    scored = [(len(rt & _tokens(c["title"])), c) for c in cands]
    best_n = max(n for n, _ in scored)
    if best_n == 0:
        return None
    top = [c for n, c in scored if n == best_n]
    if len(top) == 1:
        return top[0]
    # 時刻が無い動画が混ざっても結果が揺れないよう、最後は動画IDで決着させる
    return max(top, key=lambda c: (c.get("time") or "", c["id"]))


def _load_studio(channel):
    """YouTube Studioのコンテンツ一覧データ。日付は実際の公開日で、シートの
    「投稿日」より信頼できる。同日に複数本あることもあるので日付→[動画] の索引にする。
    「公開予約」（まだ公開されていない）は除く——動画IDはあってもサムネは存在しないため。
    """
    _, _, _, fname = _SHEETS[channel]
    path = os.path.join(DATA, fname)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    by_date = {}
    for r in rows:
        if r.get("status") == "公開予約":
            continue
        d = _parse_date((r.get("date") or "").replace("-", "/"))
        if not d:
            continue
        by_date.setdefault(d, []).append(r)
    return by_date


def _studio_match(studio_by_date, date, title, deltas, used):
    """指定日付（deltas日ぶんの候補）でStudioの動画を探す。複数あれば特徴語の一致度で絞る。
    used に入っているvid（他の回が既に確定済み）は候補から除く——同じ動画を2回に
    重複して割り当てない（±1日の許容幅で日付が近い2回が同じ動画を奪い合う事故を防ぐ）。
    """
    for delta in deltas:
        cands = [c for c in studio_by_date.get(date + datetime.timedelta(days=delta), [])
                 if c["id"] not in used]
        if not cands:
            continue
        if len(cands) == 1:
            return cands[0]["id"]
        rt = _tokens(title)
        best, best_n = None, -1
        for c in cands:
            n = len(rt & _tokens(c["title"]))
            if n > best_n:
                best, best_n = c, n
        return best["id"] if best else None
    return None


def build(channel):
    """{No.: {title, date(YYYY-MM-DD), vid or None, upcoming}} を返す。

    投稿日が未来の回は動画IDの照合を試みず vid=None・upcoming=True で返す
    （公開前の動画のサムネは存在しないため）。タイトル・日付は出す。
    """
    rows = _load_sheet(channel)
    dated = [r for r in rows if r["date"]]
    past = sorted((r for r in dated if r["date"] <= TODAY),
                  key=lambda r: (r["date"], r["no"]))
    future = [r for r in dated if r["date"] > TODAY]
    studio_by_date = _load_studio(channel)
    yt_by_date = _yt_by_date(channel)
    yt_date_of = _yt_dates(channel)
    real_titles = _real_title_index(channel)
    yt = _load_yt(channel)
    yt_old = list(reversed(yt))  # 古い順に並べ替え（スクレイプ時は新しい順）
    n_sheet, n_yt = len(past), len(yt_old)
    yt_tokens = [_tokens(v["title"]) for v in yt_old]

    df = Counter()
    for ts in yt_tokens:
        for t in ts:
            df[t] += 1

    def idf(t):
        return math.log((n_yt + 1) / (df[t] + 1)) + 0.3

    # 同じ動画IDを2つの回が奪い合わないよう、確度の高い方法から順に全件を1パスずつ確定させる
    # （日付完全一致 → 全ての回に対して先に確定 → その後で±1日を試す、の順）。
    # 1回のループで各行に対し複数の照合手段を順番に試す方式だと、片方が先に±1日の緩い
    # マッチで確定してしまい、後から来る完全一致の行がその動画を横取りできなくなる
    # （実例: No.128とNo.129が隣接日で同じ動画を掴んでしまった）。
    out = {}
    vid_of, used = {}, set()

    for r in past:
        if r["vid"]:
            vid_of[r["no"]] = r["vid"]
            used.add(r["vid"])
    for r in past:
        if r["no"] in vid_of:
            continue
        override = MANUAL_OVERRIDES.get((channel, r["no"]))
        if override and override not in used:
            vid_of[r["no"]] = override
            used.add(override)
    # 公開日がシートの投稿日と完全一致するものを先に確定させる。日付は動かないので、
    # タイトルの言い回しが変わっても・Studioの手動エクスポートが古くても影響を受けない。
    # 同じ日に2本ある日は、片方が確定すると残りが1本になって日付だけで決まるため、
    # 何も新たに決まらなくなるまで繰り返す。1回流すだけだと、タイトルで決めきれなかった
    # 回が兄弟の確定後に拾い直されず落ちる（実例: cc No.67・No.70）。
    while True:
        settled = False
        for r in past:
            if r["no"] in vid_of:
                continue
            cands = [v for v in yt_by_date.get(r["date"], []) if v["id"] not in used]
            v = _pick_by_title(cands, r["title"]) if cands else None
            if v:
                vid_of[r["no"]] = v["id"]
                used.add(v["id"])
                settled = True
        if not settled:
            break

    if studio_by_date:
        for r in past:
            if r["no"] in vid_of:
                continue
            v = _studio_match(studio_by_date, r["date"], r["title"], (0,), used)
            if v:
                vid_of[r["no"]] = v
                used.add(v)
        for r in past:
            if r["no"] in vid_of:
                continue
            v = _studio_match(studio_by_date, r["date"], r["title"], (-1, 1), used)
            if v:
                vid_of[r["no"]] = v
                used.add(v)
    # 日付とタイトルの「両方」が同じ動画を指しているものだけを拾う。
    # 投稿日と実際の公開日が1〜2日ずれた回（初期に数件ある）の救済で、
    # 「タイトルは似ているが日付が遠い」も「日付は近いがタイトルが無関係」も採らない。
    # 片方の信号だけで決めると別の回の動画を掴む——実データで、タイトルだけに任せると
    # cc・aa 合わせて33件が別の動画に化けることを確認している。
    while True:
        rest_r = [r for r in past if r["no"] not in vid_of]
        rest_v = [v for v in yt_old if v["id"] not in used and v["id"] in yt_date_of]
        if not rest_r or not rest_v:
            break
        def near_scores(r):
            out = []
            for v in rest_v:
                gap = abs((yt_date_of[v["id"]] - r["date"]).days)
                if gap > NEAR_DAYS:
                    continue
                title_score = sum(idf(t) for t in (_tokens(r["title"]) & _tokens(v["title"])))
                out.append((title_score - 0.15 * gap, title_score, v["id"]))
            return sorted(out, reverse=True)
        claims = []
        for r in rest_r:
            sc = near_scores(r)
            if not sc:
                continue
            top, title_score, vid = sc[0]
            runner_up = sc[1][0] if len(sc) > 1 else -1e9
            if title_score >= NEAR_MIN_SCORE and top - runner_up >= NEAR_MIN_MARGIN:
                claims.append((top, r["no"], vid))
        claims.sort(reverse=True)
        settled = False
        for top, no, vid in claims:
            if no in vid_of or vid in used:
                continue
            # その動画を最も強く主張している回でなければ譲る（取り合いでの誤爆防止）
            owner = max((s[0], r["no"]) for r in rest_r if r["no"] not in vid_of
                        for s in near_scores(r) if s[2] == vid)
            if owner[1] == no:
                vid_of[no] = vid
                used.add(vid)
                settled = True
        if not settled:
            break

    for rank, r in enumerate(past):
        if r["no"] in vid_of:
            continue
        pred = round(rank * (n_yt - 1) / max(1, n_sheet - 1)) if n_sheet > 1 else 0
        rt = _tokens(r["title"])
        best, best_score = None, -1e9
        for i, vt in enumerate(yt_tokens):
            if yt_old[i]["id"] in used:
                continue
            score = sum(idf(t) for t in (rt & vt)) - abs(i - pred) * 0.08
            if score > best_score:
                best, best_score = yt_old[i], score
        # ここは公開日もStudioも失ったときにしか動かない最後の手段。日付という
        # 確かな手がかりが無い状態なので、しきい値を上げて「確信が持てないものは
        # 出さない」側に倒してある（0.4→1.5で、実データ上の誤割り当てが42→29件に減り、
        # そのぶん未確定が増える＝サムネを間違えるより出さない方を選ぶ）。
        if best and best_score >= RANK_MIN_SCORE:
            vid_of[r["no"]] = best["id"]
            used.add(best["id"])

    for r in past:
        vid = vid_of.get(r["no"])
        title = real_titles.get(vid, r["title"]) if vid else r["title"]
        # その割り当てを何が支持しているかを残す。日付とタイトルのどちらの裏付けも
        # 無い組み合わせは、シートのURL列の打ち間違いなど人の入力ミスの可能性がある。
        # 落とさずに出したうえでビルド時に一覧させ、人が見て確かめられるようにする。
        if vid:
            d_ok = yt_date_of.get(vid) == r["date"]
            t_ok = bool(_tokens(r["title"]) & _tokens(real_titles.get(vid, "")))
            support = {(True, True): "both", (True, False): "date",
                       (False, True): "title", (False, False): "none"}[(d_ok, t_ok)]
        else:
            support = None
        out[r["no"]] = {
            "title": title,
            "date": r["date"].isoformat() if r["date"] else None,
            "vid": vid,
            "upcoming": False,
            "support": support,
        }
    for r in future:
        out[r["no"]] = {
            "title": r["title"],
            "date": r["date"].isoformat() if r["date"] else None,
            "vid": None,
            "upcoming": True,
            "support": None,
        }
    return out


_CACHE = {}


def get(channel):
    if channel not in _CACHE:
        _CACHE[channel] = build(channel)
    return _CACHE[channel]


def thumb_url(vid, quality="hqdefault"):
    return f"https://i.ytimg.com/vi/{vid}/{quality}.jpg" if vid else None


def watch_url(vid):
    return f"https://www.youtube.com/watch?v={vid}" if vid else None


def data_health(channel):
    """公開動画一覧のうち、公開日時が取れていない動画の数を (総数, 日付なし, 時刻なし) で返す。
    ここが増えていたら、日付での照合という土台が崩れかけている合図。
    """
    vids = _load_yt(channel)
    return (len(vids),
            sum(1 for v in vids if not v.get("date")),
            sum(1 for v in vids if not v.get("time")))


def resolve(ep):
    """撮影資料フォルダの ep dict（parse_kits.parse_folder_name の戻り値）から、
    動画の {title, date, vid, upcoming, uncertain} を組み立てる。

    スプレッドシートに該当No.の行がある場合はそれを使う（タイトル・日付とも配信管理表準拠で正確）。
    無い場合はフォルダ自身のトピック名・作成日にフォールバックする
    （uncertain=True。動画は特定できないがタイトル・日付は嘘にならない）。
    """
    if ep.get("no"):
        m = get(ep["channel"]).get(ep["no"])
        if m:
            return {**m, "uncertain": False}
    return {"title": ep["topic"], "date": ep["date"], "vid": None,
            "upcoming": False, "uncertain": True, "support": None}


if __name__ == "__main__":
    for ch in ("claudecode", "kawaru"):
        m = get(ch)
        with_vid = sum(1 for v in m.values() if v["vid"])
        print(f"{ch}: {len(m)}件中 動画あり{with_vid}件")
