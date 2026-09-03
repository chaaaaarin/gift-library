# -*- coding: utf-8 -*-
"""動画（回）ごとの解説資料3点セットへのリンクを組み立てる。

各撮影資料フォルダはそれ自体が1つのGitHubリポジトリ（`chaaaaarin/<repo>`・Pages有効）で、
そこに README.md（教科書本体）・slides.html・onepager.html が公開されている。
配布サイトは各動画の「▶ 動画を見る」の下に、この3点へのボタンを出す。

リポジトリ名には規則がない（`claudecode-channel-20260829` / `claudecode-channel-20260821-2` /
`kawaru-20260629` / `kawaru-20260626-amodei` …）ため、フォルダ名からは導出できない。
`撮影資料/<回>/.git/config` の origin リモートから読むしかない。

Mac と GitHub Actions で出力を揃えるため、Mac 側でこのリンク表を
`data/episode_links.json` に落とし、両ビルダーがそれを読む（`kits/` ミラーと同じ方式）。
Actions 側は `kits/`（`*/kit/***` だけの複製・`.git` なし）からビルドするので、
このファイルを自力では作れない——コミット済みの JSON を読む。

  python3 lib/links.py <撮影資料ディレクトリ> <出力先json>   # 手動で作り直す
"""
import glob, json, os, re, subprocess, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
DEFAULT_JSON = os.path.join(DATA, "episode_links.json")

# parse_kits と同じ既定・同じ環境変数（GitHub Actions などこのMac以外で動かすため）
SHOOT_DIR = os.environ.get(
    "GIFT_SHOOT_DIR",
    "/Users/karin/Desktop/Claude Code/YouTube planning/YouTube research/撮影資料")


def _parse_remote(url):
    """origin リモートURL → (owner, repo)。https/ssh の両形式を許容。合わなければ None。"""
    url = url.strip()
    m = (re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", url)
         or re.match(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?/?$", url))
    return (m.group(1), m.group(2)) if m else None


def _origin_url(folder_path):
    cfg = os.path.join(folder_path, ".git", "config")
    if not os.path.exists(cfg):
        return None
    try:
        out = subprocess.run(
            ["git", "config", "--file", cfg, "--get", "remote.origin.url"],
            capture_output=True, text=True, check=True).stdout.strip()
        return out or None
    except (OSError, subprocess.CalledProcessError):
        return None


def refresh(shoot_dir, out_path):
    """撮影資料フォルダを走査して {folder: {repo, slides, onepager}} を書き出す。

    slides.html / onepager.html は実在するものだけ入れる。
    キーは NFC 正規化する（parse_kits._nfc と揃える。揃えないと Mac(NFD) と
    Linux(NFC) で同じ回が別キーになる）。
    """
    table = {}
    for entry in sorted(os.listdir(shoot_dir)):
        fp = os.path.join(shoot_dir, entry)
        if not os.path.isdir(fp):
            continue
        url = _origin_url(fp)
        if not url:
            continue
        parsed = _parse_remote(url)
        if not parsed:
            continue
        owner, repo = parsed
        rec = {"repo": f"https://github.com/{owner}/{repo}"}
        pages = f"https://{owner}.github.io/{repo}"
        for name, key in (("slides.html", "slides"), ("onepager.html", "onepager")):
            if os.path.exists(os.path.join(fp, name)):
                rec[key] = f"{pages}/{name}"
        table[unicodedata.normalize("NFC", entry)] = rec

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(table, f, ensure_ascii=False, sort_keys=True, indent=1)
        f.write("\n")
    return table


_CACHE = {}


def load(path=DEFAULT_JSON):
    if path not in _CACHE:
        try:
            with open(path, encoding="utf-8") as f:
                _CACHE[path] = json.load(f)
        except (OSError, ValueError):
            _CACHE[path] = {}
    return _CACHE[path]


def for_folder(folder):
    return load().get(unicodedata.normalize("NFC", folder), {})


def refresh_local():
    """Mac 上で本物の撮影資料が見えているときだけ episode_links.json を作り直す。

    CI（GIFT_SHOOT_DIR=…/kits・.git なし）では何もしない＝コミット済み JSON を使う。
    """
    if glob.glob(os.path.join(SHOOT_DIR, "*", ".git")):
        refresh(SHOOT_DIR, DEFAULT_JSON)
        _CACHE.pop(DEFAULT_JSON, None)


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else SHOOT_DIR
    dst = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_JSON
    t = refresh(src, dst)
    n_slides = sum(1 for v in t.values() if "slides" in v)
    n_one = sum(1 for v in t.values() if "onepager" in v)
    print(f"{dst}: {len(t)}回 / slides {n_slides} / onepager {n_one}")
