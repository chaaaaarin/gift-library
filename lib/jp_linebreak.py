# -*- coding: utf-8 -*-
"""日本語の「意味の切れ目でだけ改行させる」ための文節チャンカー（正典・2026-07-27確立）

背景: ブラウザは日本語をどこでも改行できてしまうため、放っておくと
「分身させす／ぎ」を」のように文節の途中で割れる。No.108でユーザーから
「改行の位置に文脈的なこだわりが感じられない」と指摘されたのが確立の経緯。

やり方: テキストを文節相当のチャンクに割り、各チャンクを
<span class="nb">…</span>（CSS: display:inline-block）で括る。
inline-block は内部で改行しないので、改行は必ずチャンクの境界＝意味の切れ目で起きる。

使い方:
    import sys; sys.path.insert(0, "/Users/karin/.claude/skills/research/references")
    from jp_linebreak import apply_nb_to_html
    html2 = apply_nb_to_html(html, selectors_done_by_caller)  # 下の apply_to_file が実務用

前提: 対象HTMLの <style> に次を入れておくこと（無いと効かない）:
    .nb{display:inline-block;}
"""

import re

# 改行してよい位置＝チャンクの切れ目。この文字の「後ろ」で切る
# ／ は「コピペ／ダウンロード」のように語を密に繋ぐので入れない
BREAK_AFTER = "。、！？・,"
# 閉じ括弧の後ろでも切れる
CLOSE_BRACKETS = "」』）】〉》"
# 開き括弧の「前」で切る
OPEN_BRACKETS = "「『（【〈《"
# 助詞（チャンクが長すぎるときの二次分割に使う）
PARTICLES = ["まで", "から", "より", "では", "には", "とは", "への", "を", "は", "が", "に", "で", "と", "も", "へ", "の"]

DEFAULT_MAX = 18   # このチャンク長を超えたら二次分割を試みる
HARD_MAX = 26      # これを超えるチャンクは .nb で括らない（括ると枠からはみ出すため）


def _split_primary(text):
    """句読点・記号・括弧で一次分割する。"""
    chunks, buf = [], ""
    for i, ch in enumerate(text):
        nxt = text[i + 1] if i + 1 < len(text) else ""
        # 開き括弧の前で切る（直前までを確定）
        if ch in OPEN_BRACKETS and buf:
            chunks.append(buf)
            buf = ch
            continue
        buf += ch
        if ch in BREAK_AFTER or ch in CLOSE_BRACKETS:
            # 句読点の直後にさらに句読点が続く場合はまとめる
            if nxt and (nxt in BREAK_AFTER or nxt in CLOSE_BRACKETS):
                continue
            # 閉じ括弧の直後の助詞は行頭に落とさない（「話す量」／は… を防ぐ）
            if ch in CLOSE_BRACKETS and nxt and nxt in "はがをにでともへのやかへ":
                continue
            chunks.append(buf)
            buf = ""
    if buf:
        chunks.append(buf)
    return chunks


def _particle_cuts(text):
    """助詞の直後で切ってよい位置（終端インデックス）を全部集める。"""
    cuts = set()
    for p in PARTICLES:
        start = 0
        while True:
            idx = text.find(p, start)
            if idx < 0:
                break
            start = idx + 1
            if idx == 0:                      # 行頭の助詞では切らない
                continue
            end = idx + len(p)
            if end >= len(text):              # 末尾では切る意味がない
                continue
            nxt = text[end]
            # 助詞の直後がさらに助詞・接続なら切らない
            # （「では」の分断や「Opus 5と／の付き合い方」のような誤分割を防ぐ）
            if nxt in "はがをにでともへのなやかねよ":
                continue
            # 句読点・閉じ括弧だけが次行に取り残されるのを防ぐ（行頭禁則）
            if nxt in BREAK_AFTER + CLOSE_BRACKETS:
                continue
            cuts.add(end)
    return sorted(cuts)


def _split_by_particle(chunk, max_len):
    """長いチャンクを助詞の後ろで二次分割する。

    max_len 以下で切れる位置があればその中で最も後ろを選び、無ければ
    max_len を超える最も近い位置で切る（切れる場所が有るのに切らない、を防ぐ）。
    """
    out, rest = [], chunk
    while len(rest) > max_len:
        cuts = _particle_cuts(rest)
        if not cuts:
            break
        under = [c for c in cuts if c <= max_len]
        cut = under[-1] if under else cuts[0]
        out.append(rest[:cut])
        rest = rest[cut:]
    if rest:
        out.append(rest)
    return out


def chunk_text(text, max_len=DEFAULT_MAX):
    """日本語テキストを文節相当のチャンク列にする。"""
    chunks = []
    for c in _split_primary(text):
        chunks.extend(_split_by_particle(c, max_len))
    return [c for c in chunks if c]


_JP = re.compile(r'[ぁ-んァ-ヴ一-龥]')


def wrap_text(text, max_len=DEFAULT_MAX, hard_max=HARD_MAX):
    """テキストを <span class="nb"> で括った HTML にする。

    括らない（自然改行に委ねる）のは次の2つ:
    - hard_max を超えるチャンク（inline-block にするとコンテナ幅を超えてはみ出す）
    - 日本語を含まないチャンク（英数字は元々語中で改行されないので括る必要がなく、
      番号バッジのような1文字要素まで span で包むと親のCSSと干渉する）
    """
    parts = []
    for c in chunk_text(text, max_len):
        stripped = c.strip()
        if not stripped or len(stripped) > hard_max or not _JP.search(stripped):
            parts.append(c)
        else:
            parts.append(f'<span class="nb">{c}</span>')
    return "".join(parts)


_TAG = re.compile(r'<[^>]+>')


def wrap_inner_html(inner, max_len=DEFAULT_MAX, hard_max=HARD_MAX):
    """要素の innerHTML を、タグを壊さずにテキスト部分だけチャンク化する。"""
    if 'class="nb"' in inner:      # 適用済みなら二重掛けしない
        return inner
    out, last = [], 0
    for m in _TAG.finditer(inner):
        seg = inner[last:m.start()]
        if seg:
            out.append(wrap_text(seg, max_len, hard_max))
        out.append(m.group(0))
        last = m.end()
    seg = inner[last:]
    if seg:
        out.append(wrap_text(seg, max_len, hard_max))
    return "".join(out)


def apply_to_file(path, patterns, max_len=DEFAULT_MAX, hard_max=HARD_MAX, verbose=True):
    """HTMLファイルの指定パターンにチャンク化を適用する。

    patterns: [(正規表現, グループ番号), ...]。グループが innerHTML を指すこと。
      例: [(r'(<p class="lead"[^>]*>)(.*?)(</p>)', 2)]  ← 2番目のグループを処理
    """
    with open(path, encoding="utf-8") as f:
        s = f.read()

    total = 0
    for pat, gi in patterns:
        rx = re.compile(pat, re.S)

        def repl(m):
            nonlocal total
            groups = list(m.groups())
            inner = groups[gi - 1]
            new = wrap_inner_html(inner, max_len, hard_max)
            if new != inner:
                total += 1
            groups[gi - 1] = new
            return "".join(groups)

        s = rx.sub(repl, s)

    with open(path, "w", encoding="utf-8") as f:
        f.write(s)
    if verbose:
        print(f"{path}: {total} elements chunked")
    return total
