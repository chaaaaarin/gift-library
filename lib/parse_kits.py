# -*- coding: utf-8 -*-
"""撮影資料/*/kit/*.md を読み取り専用でスキャンし、配布サイト用のデータ構造に変換する。

原本（撮影資料フォルダ）には一切書き込まない。
"""
import html, os, re, glob, unicodedata
from episodes import FOLDER_NO_RECOVERY

# 環境変数で上書きできるようにしてある（GitHub Actionsなど、このMac以外で動かすため）。
SHOOT_DIR = os.environ.get(
    "GIFT_SHOOT_DIR",
    "/Users/karin/Desktop/Claude Code/YouTube planning/YouTube research/撮影資料")

CHANNELS = {
    "claudecode": {"code": "cc", "name": "ClaudeCodeチャンネル"},
    "kawaru":     {"code": "aa", "name": "AIエージェント / Kawaru"},
}

# キット名からタイプを判定する。上から順に最初に当たったものを採用。
TYPE_RULES = [
    ("プロンプト集", r"プロンプト|指示文|依頼文|呼びかけ|言い換え|テンプレ文"),
    ("設定・スニペット", r"設定|スニペット|コマンド|スクリプト|SKILL\.md|CLAUDE\.md|AGENTS\.md|フック|hooks"),
    ("早見表・逆引き", r"早見表|逆引き|カタログ|一覧|辞典|対応表|チートシート"),
    ("チェックリスト", r"チェック|点検|確認|診断"),
    ("判断シート", r"判断|使い分け|選び方|見極め|棚卸"),
    ("ワークフロー", r"ワークフロー|手順|フロー|ロードマップ|進め方|段取り"),
    ("テンプレート", r"テンプレート|ひな型|ひな形|雛形|シート|ワークシート|設計"),
]

def detect_type(name, n_items):
    for label, pat in TYPE_RULES:
        if re.search(pat, name):
            return label
    return "プロンプト集" if n_items >= 10 else "テンプレート"


def parse_folder_name(folder):
    """20260821_claudecode_No.138_トピック → dict"""
    parts = folder.split("_")
    if len(parts) < 3:
        return None
    date, ch = parts[0], parts[1]
    if ch not in CHANNELS or not re.fullmatch(r"\d{8}", date):
        return None
    rest = parts[2:]
    no = None
    if rest and re.fullmatch(r"No\.\d+", rest[0]):
        no = int(rest[0][3:])
        rest = rest[1:]
    if no is None:
        no = FOLDER_NO_RECOVERY.get(folder)
    return {
        "folder": folder,
        "date": f"{date[:4]}-{date[4:6]}-{date[6:]}",
        "channel": ch,
        "no": no,
        "topic": "_".join(rest) or folder,
    }


def _count_from_name(name):
    """「100選」「60本」「50個」などの数値を拾う。"""
    m = re.search(r"(\d+)\s*(選|本|個|点|パターン|項目)", name)
    return int(m.group(1)) if m else None


def parse_kit_md(path):
    src = open(path, encoding="utf-8").read()
    lines = src.split("\n")

    m = re.match(r"#\s*(?:🎁\s*)?(.+)", lines[0].strip())
    if m:
        name = m.group(1).strip()
        body_start = 1
    else:
        # タイトル行が無い版（【名前】から始まる型）
        m2 = re.match(r"【(.+?)】", lines[0].strip())
        name = m2.group(1).strip() if m2 else os.path.basename(path)[:-3]
        body_start = 0

    # 説明 = タイトル直後の、見出し・強調行でない最初の段落
    desc = ""
    for ln in lines[body_start:body_start + 8]:
        s = ln.strip()
        if not s or s.startswith(("#", "**", "```", "■", "□", "【")):
            continue
        desc = s
        break
    desc = re.sub(r"\*\*(.+?)\*\*", r"\1", desc)

    # 個別項目（### N. タイトル）の抽出
    items, cur_cat = [], ""
    blocks = re.split(r"^(##\s+.+|###\s+.+)$", src, flags=re.M)
    i = 1
    while i < len(blocks) - 1:
        head, body = blocks[i].strip(), blocks[i + 1]
        if head.startswith("### "):
            title = head[4:].strip()
            title = _plain(re.sub(r"^\d+[.．、]\s*", "", title))
            dm = re.search(r"^説明[:：]\s*(.+)$", body, re.M)
            fm = re.search(r"```(?:text)?\n(.*?)\n```", body, re.S)
            if not title:
                # 「### 1.」のように見出しが番号だけのキットは、本文の「指示:」から見出しを起こす
                title = _title_from_body(fm.group(1) if fm else body)
            items.append({
                "cat": cur_cat,
                "title": title,
                "desc": dm.group(1).strip() if dm else "",
                "body": fm.group(1) if fm else body.strip(),
            })
        else:
            cur_cat = head[3:].strip()
        i += 2

    # 一括本文型（項目が無い場合）: 最大のテキストフェンス、無ければ本文全体
    whole = ""
    if not items:
        fences = re.findall(r"```(?:text)?\n(.*?)\n```", src, re.S)
        if fences:
            whole = max(fences, key=len)
        else:
            whole = "\n".join(lines[body_start:]).strip()

    count = _count_from_name(name) or len(items) or None
    unit = "個"
    if count is None and whole:
        # チェックリスト型は「□」の数を項目数とみなす
        boxes = whole.count("□") + len(re.findall(r"^\s*[-*]\s*\[ \]", whole, re.M))
        if boxes >= 5:
            count, unit = boxes, "項目"
    if items:
        unit = "個"
    # 「### 項目」が無いキットは本文を二段目パーサでカードに割る（割れなければ1枚で見せる）
    cards = items if items else split_body(whole)
    return {
        "name": name,
        "desc": desc,
        "items": items,
        "cards": cards,
        "intro": "" if items else preamble(whole),
        "whole": whole,
        "count": count,
        "unit": unit,
        "type": detect_type(name, len(items)),
        "slug": os.path.basename(path)[:-3],
        "is_app": False,
    }


def parse_kit_app(path):
    """kit/<name>.app.html を読み取る。中身には触らず、<title>/<meta description>だけ拾う。

    実体（原本そのまま）はサイト側で `apps/<slug>/app.html` として単体URLにも置かれる
    （iframe埋め込み用と、ダウンロード対象を兼ねる）。
    """
    src = open(path, encoding="utf-8").read()
    m = re.search(r"<title[^>]*>(.*?)</title>", src, re.S | re.I)
    name = html.unescape(m.group(1)).strip() if m else os.path.basename(path)
    dm = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', src, re.S | re.I)
    desc = html.unescape(dm.group(1)).strip() if dm else ""
    slug = os.path.basename(path)
    if slug.endswith(".app.html"):
        slug = slug[:-len(".app.html")]
    return {
        "name": name, "desc": desc, "items": [], "cards": [],
        "intro": "", "whole": "", "count": None, "unit": "",
        "type": "アプリ", "slug": slug, "is_app": True, "raw": src,
    }


def _nfc(s):
    """ファイル名をNFC（合成形）に揃える。

    macOSはファイル名をNFD（分解形）で返し、Linux上のgitチェックアウトはNFCになる。
    「アプデ」の「プ」（フ+゜）などが該当し、見た目は同じでもバイト列が違うため、
    揃えないとMacとGitHub Actionsが同じ回を別物として出力し、互いに上書きし合う。
    フォルダ名は経路にも使うが、macOSは照合時に正規化を吸収するのでNFCのままでよい。
    """
    return unicodedata.normalize("NFC", s)


def collect(channel=None):
    out = []
    for folder in sorted(os.listdir(SHOOT_DIR), key=_nfc):
        meta = parse_folder_name(_nfc(folder))
        if not meta:
            continue
        if channel and meta["channel"] != channel:
            continue
        for md in sorted(glob.glob(os.path.join(SHOOT_DIR, folder, "kit", "*.md"))):
            kit = parse_kit_md(md)
            kit["src"] = md
            kit["ep"] = meta
            out.append(kit)
        for ap in sorted(glob.glob(os.path.join(SHOOT_DIR, folder, "kit", "*.app.html"))):
            kit = parse_kit_app(ap)
            kit["src"] = ap
            kit["ep"] = meta
            out.append(kit)
    return out


if __name__ == "__main__":
    import collections, json
    kits = collect()
    print(f"キット総数: {len(kits)}")
    print(f"個別項目総数: {sum(len(k['items']) for k in kits)}")
    print("\n=== タイプ別 ===")
    for t, n in collections.Counter(k["type"] for k in kits).most_common():
        print(f"  {n:4d}  {t}")
    print("\n=== 個数バッジが取れなかったもの ===")
    miss = [k for k in kits if not k["count"]]
    print(f"  {len(miss)}件")
    print("\n=== 説明が空のもの ===")
    for k in kits:
        if not k["desc"]:
            print("  ", k["slug"], "|", k["ep"]["folder"][:40])


# ============ 一括本文型の二段目パース ============
# 「### 項目」形式でないキット（チェックリスト・早見表など）も、本文中の
# ■見出し・##見出し・連番で項目に割れる。割れると1項目ずつコピーできる。

_SEC_MARK = re.compile(r"^(■\s*.+|##+\s+.+)$", re.M)
_NUM_LINE = re.compile(r"^\s*(\d+)[.．、]\s*(.+)$", re.M)
MIN_SPLIT_LEN = 500      # これより短い本文は割らずに1枚で見せる
NUM_ITEMS_MIN = 5        # 本文全体でこの数以上の連番があれば、各セクションを連番で割る


def _title_from_body(body, limit=44):
    """見出しの無い項目に、本文の「指示:」行から見出しを起こす。"""
    m = re.search(r"^(?:指示|依頼|やること)[:：]\s*(.+)$", body, re.M)
    line = m.group(1) if m else next(
        (l.strip() for l in body.split("\n") if l.strip()), "")
    line = re.sub(r"^(?:前提|背景|状況)[:：]\s*", "", line)
    line = re.split(r"(?<=[。．])", line)[0]
    return line[:limit] + ("…" if len(line) > limit else "")


def _plain(s):
    """見出しに出す文字列から、Markdownの装飾記号を落とす。

    説明文（desc）は以前から `**` を外していたが、項目名は素通しだったため、
    カード見出しに `**Playwright**（Microsoft）` のように記号がそのまま出ていた
    （2026-08-27時点で105項目）。
    """
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    return s.strip()


def _title_of(text, limit=42):
    """項目本文の先頭から、カード見出しに使う短い一文を作る。"""
    head = _plain(text.strip().split("\n")[0])
    # 「/list-agents が…」のようにスラッシュ始まりの行を空に切らないよう、先頭の区切りは無視する
    first = re.split(r"\s*[/｜|]\s*", head)[0].strip()
    head = first or head
    head = re.sub(r"^(困りごと|症状|場面|ケース|状況)\s*[:：]\s*", "", head).strip()
    return head[:limit] + ("…" if len(head) > limit else "")


def _split_numbered(text, cat):
    """『1. …』『2. …』の連番で割る。"""
    marks = list(_NUM_LINE.finditer(text))
    if len(marks) < 2:
        return []
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.start():end].strip()
        body = re.sub(r"^\s*\d+[.．、]\s*", "", body)
        out.append({"cat": cat, "title": _title_of(body), "desc": "", "body": body})
    return out


def split_body(whole):
    """一括本文を項目カードに割る。割れなければ空リストを返す。"""
    if not whole or len(whole) < MIN_SPLIT_LEN:
        return []

    marks = list(_SEC_MARK.finditer(whole))
    if marks:
        # 連番で割るかはキット単位で決める。セクションごとに判定すると、
        # 同じキットの中で「1枚だけの章」と「N枚の章」が混ざって不揃いになる。
        use_num = len(_NUM_LINE.findall(whole)) >= NUM_ITEMS_MIN
        out = []
        for i, m in enumerate(marks):
            head = m.group(0).strip().lstrip("#■ 　").strip()
            head = re.sub(r"^\d+[.．、]\s*", "", head)
            start = m.end()
            end = marks[i + 1].start() if i + 1 < len(marks) else len(whole)
            body = whole[start:end].strip()
            if not body:
                continue
            nums = _split_numbered(body, head) if use_num else []
            out.extend(nums if nums else
                       [{"cat": "", "title": _plain(head), "desc": "", "body": body}])
        return out if len(out) > 1 else []

    nums = _split_numbered(whole, "")
    return nums if len(nums) > 1 else []


def preamble(whole):
    """最初の見出し・連番より前の導入文（カードにせず本文上部に置く）。"""
    m = _SEC_MARK.search(whole) or _NUM_LINE.search(whole)
    if not m:
        return ""
    head = whole[:m.start()].strip()
    head = re.sub(r"^【.+?】\s*", "", head)
    return head
