# -*- coding: utf-8 -*-
"""チャンネル別の配色・アイコン・共通CSS。"""
import base64, os, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets_src")

# 環境変数で上書きできるようにしてある（GitHub Actionsなど、このMac以外で動かすため）。
ICON_DIR = os.environ.get(
    "GIFT_ICON_DIR",
    "/Users/karin/Desktop/Claude Code/YouTube planning/YouTube research")

THEMES = {
    "cc": {
        "channel": "claudecode",
        "site_name": "CC Gifts",
        "channel_name": "ClaudeCodeチャンネル",
        "tagline": "プレゼント図書館",
        "icon": "ClaudeCode チャンネルアイコン 2026年4月25日.png",
        "font": "'M PLUS Rounded 1c'",
        "font_url": "https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700;900&family=M+PLUS+Rounded+1c:wght@500;700;800&display=swap",
        "vars": """--brand:#D9774F;--brand-deep:#C15640;--brand-soft:rgba(217,119,79,.12);
--accent:#D9774F;--accent-deep:#B24E33;--bg:#F1ECE3;--paper:#FBF8F2;
--ink:#2A2620;--ink-mid:#6E6557;--line:#E4D9C7;""",
    },
    "aa": {
        "channel": "kawaru",
        "site_name": "Kawaru Gifts",
        "channel_name": "AIエージェント / Kawaru",
        "tagline": "プレゼント図書館",
        "icon": "Kawaru.png",
        "font": "'Noto Sans JP'",
        "font_url": "https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700;900&display=swap",
        "vars": """--brand:#1C3461;--brand-deep:#16284A;--brand-soft:rgba(28,52,97,.08);
--accent:#5BBCD4;--accent-deep:#2C7A93;--bg:#F7FAFC;--paper:#FFFFFF;
--ink:#1C3461;--ink-mid:#4A6080;--line:rgba(28,52,97,.14);""",
    },
}

def _cached(name):
    """事前計算しておいた data URI を返す（無ければ None）。

    縮小に使う sips は macOS 専用で、Pillow等で置き換えると出力バイト列が変わる。
    Macとそれ以外（GitHub Actions）で結果が変わると、両者が毎回差分を出し合うため、
    確定済みの data URI をリポジトリに置いて全環境で同じものを使う。
    アイコン画像を差し替えたときは assets_src/*.b64 を作り直すこと（MAINTAINER.md参照）。
    """
    p = os.path.join(ASSETS, name)
    return open(p, encoding="utf-8").read().strip() if os.path.exists(p) else None


def icon_data_uri(code, size=120):
    """チャンネルアイコンを縮小してdata URIにする（外部ファイル参照を作らない）。"""
    c = _cached(f"icon_{code}.b64")
    if c:
        return c
    src = os.path.join(ICON_DIR, THEMES[code]["icon"])
    with tempfile.TemporaryDirectory() as td:
        dst = os.path.join(td, "icon.png")
        subprocess.run(["sips", "-Z", str(size), src, "--out", dst],
                       check=True, capture_output=True)
        b64 = base64.b64encode(open(dst, "rb").read()).decode()
    return "data:image/png;base64," + b64


N1INC_ICON_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "assets_src", "n1inc_icon.png")


def n1inc_icon_data_uri(size=120):
    """クロスプロモ用の運営会社（株式会社エヌイチ）アイコン。KawaruのB2B系サービス
    （AI社員構築代行・Claude Code/Codex研修・会社HP）はKawaruではなくエヌイチのブランドなので、
    Kawaruのアイコンを流用しない。"""
    c = _cached("icon_n1inc.b64")
    if c:
        return c
    with tempfile.TemporaryDirectory() as td:
        dst = os.path.join(td, "icon.png")
        subprocess.run(["sips", "-Z", str(size), N1INC_ICON_SRC, "--out", dst],
                       check=True, capture_output=True)
        b64 = base64.b64encode(open(dst, "rb").read()).decode()
    return "data:image/png;base64," + b64


# キット種別ごとの line-art アイコン（stroke=currentColor で配色に乗る）
TYPE_ICONS = {
    "アプリ":         '<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 20h8M12 17v3"/><path d="M9 8.7v5.6l4.3-2.8L9 8.7Z" fill="currentColor" stroke="none"/>',
    "プロンプト集":   '<path d="M4 5h16v11H8l-4 4V5Z"/><path d="M8 9h8M8 12.5h5"/>',
    "チェックリスト": '<path d="M5 4h14v16H5z"/><path d="M8.5 9.2l1.6 1.6 3.4-3.4M8.5 15.2l1.6 1.6 3.4-3.4"/>',
    "早見表・逆引き": '<path d="M4 5h16v14H4z"/><path d="M4 9.5h16M9.5 9.5V19M4 14.2h16"/>',
    "テンプレート":   '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/><path d="M9 12h6M9 15.5h4"/>',
    "設定・スニペット": '<path d="M9 8l-4 4 4 4M15 8l4 4-4 4"/><path d="M13 5.5l-2 13"/>',
    "ワークフロー":   '<path d="M4 6h6v4H4zM14 14h6v4h-6z"/><path d="M7 10v5a1.5 1.5 0 0 0 1.5 1.5H14"/>',
    "判断シート":     '<path d="M12 3v5M12 3 6.5 8.5M12 3l5.5 5.5"/><circle cx="12" cy="13" r="2.2"/><path d="M6.5 21h11"/>',
}

def type_icon(t):
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
            'stroke-linecap="round" stroke-linejoin="round">' + TYPE_ICONS.get(t, TYPE_ICONS["テンプレート"]) + "</svg>")

def play_icon():
    """サムネが無い動画枠に置く、動画であることを示すだけの汎用アイコン。"""
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<rect x="3" y="5" width="18" height="14" rx="2.5"/>'
            '<path d="M10.5 9.2v5.6l4.8-2.8-4.8-2.8Z" fill="currentColor" stroke="none"/>'
            '</svg>')


TYPE_ORDER = ["アプリ", "プロンプト集", "設定・スニペット", "早見表・逆引き", "テンプレート",
              "チェックリスト", "判断シート", "ワークフロー"]
