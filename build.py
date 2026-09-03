#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""チャンネル別プレゼント配布サイトを静的生成する。

  python3 build.py          # cc・aa の両方を生成
  python3 build.py cc       # 片方だけ
  python3 build.py --preview          # cc・aa の「未公開回も含む」プレビュー版をローカルに生成
  python3 build.py --preview-publish  # 同内容を、管理者間で共有できる推測困難なURLとしてGitHub Pagesに生成

出力は build.py と同じ階層の cc/ ・ aa/。ビルド不要・相対パスのみの純静的サイトなので、
Vercel / Cloudflare Pages / GitHub Pages のどれにもそのまま置ける。
撮影資料フォルダは読み取りしかしない。

--preview は動画未公開の回も含めて別ディレクトリ preview/cc/ ・ preview/aa/ に書き出す
（本番の cc/ ・ aa/ には一切触れない）。管理者（自分）が動画公開前にプレゼントの見た目・
動作をローカルで確認するための専用モードで、preview/ はローカル専用（.gitignore対象・push
しない）。

--preview-publish は同じ「未公開回も含む」内容を、gh-preview/preview-<token>/cc/ ・
gh-preview/preview-<token>/aa/ に書き出す。<token> は一度だけ生成して使い回す推測困難な
文字列（.preview_token・ローカル管理・.gitignore対象）。gh-preview/ は本番の cc/・aa/ と
同様に git add してpushする対象——本番とは別の「知っていれば誰でも見れるが、リンクされて
おらず検索にも出ない」隠しURLとして、管理者間でリンク共有するために使う（各ページに
noindexも付く）。詳細は MAINTAINER.md 参照。
"""
import collections, hashlib, os, secrets, shutil, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))

import css, episodes as EP, links as L, parse_kits as P, render, theme as T


def _replace_dir(tmp, final, retries=5, delay=3):
    """tmp を final にアトミックに差し替える（rename方式・リトライ付き）。

    2026-08-25発覚: 旧実装は final を直接 shutil.rmtree → os.makedirs していたが、
    iCloud Drive同期（このプロジェクトは Desktop 配下）との競合で rmtree が
    OSError: [Errno 11] Resource deadlock avoided を起こし、launchdの自動更新
    （18:45・19:15の2回）が連続で異常終了し、動画公開当日にプレゼントが反映
    されない事故が起きた。final を直接消さず、いったん tmp に作ってから最後に
    rename で差し替えることで、途中失敗しても final は無傷のまま残る
    （＝失敗しても「反映されない」だけで「壊れる」ことはない）。
    それでも rename/rmtree 自体が一時的に競合することがあるためリトライする。
    """
    old = final + ".old"
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            if os.path.isdir(old):
                shutil.rmtree(old)
            if os.path.isdir(final):
                os.rename(final, old)
            os.rename(tmp, final)
            if os.path.isdir(old):
                shutil.rmtree(old)
            return
        except OSError as e:
            last_err = e
            print(f"  [警告] {final} への差し替えに失敗（{attempt}/{retries}回目・{e}）。{delay}秒後リトライ")
            time.sleep(delay)
    raise RuntimeError(f"{final} への差し替えに{retries}回失敗しました: {last_err}")


def preview_token():
    """管理者限定プレビュー公開（--preview-publish）用の推測困難なURLトークン。
    一度生成したら使い回す（ローカル管理ファイル・.gitignore対象・push不要）。"""
    path = os.path.join(HERE, ".preview_token")
    if os.path.exists(path):
        return open(path, encoding="utf-8").read().strip()
    token = secrets.token_urlsafe(9)
    open(path, "w", encoding="utf-8").write(token)
    return token

TYPE_DESC = {
    "アプリ":           "入力すると結果が出る、ブラウザでそのまま動くミニアプリ。",
    "プロンプト集":     "そのまま貼って使える指示文のコレクション。",
    "設定・スニペット": "設定ファイルやコマンドに、コピーして貼るだけのもの。",
    "早見表・逆引き":   "「困りごとから引く」形の一覧表。",
    "テンプレート":     "自分の状況に合わせて書き換えて使うひな型。",
    "チェックリスト":   "抜け漏れを防ぐための、順に確認していく表。",
    "判断シート":       "どれを選ぶか迷ったときに、判断の軸をくれるシート。",
    "ワークフロー":     "はじめから終わりまでの進め方をまとめたもの。",
}


def assign_slugs(kits):
    """URLを安定させるため、古い回から順に素のslugを与え、衝突分だけ回番号を足す。"""
    kits = sorted(kits, key=lambda k: (k["ep"]["date"], k["ep"]["no"] or 0, k["slug"]))
    used = set()
    for k in kits:
        s = k["slug"]
        if s in used:
            suffix = f"no{k['ep']['no']}" if k["ep"]["no"] else k["ep"]["date"].replace("-", "")
            s = f"{k['slug']}-{suffix}"
            n = 2
            while s in used:
                s = f"{k['slug']}-{suffix}-{n}"; n += 1
        used.add(s)
        k["slug"] = s
    return kits


def assemble_episodes(kits, include_upcoming=False):
    """kitを撮影資料フォルダ（=配布した動画1本）単位でグループ化する。

    サイトの主導線は「動画→その回のプレゼント」なので、これがハブの表示単位になる。
    include_upcoming=True（--preview時）は未公開回も含める。管理者が動画公開前に
    実際の見た目・動作を確認するための専用モードで、本番ビルドでは使わない。
    """
    by_folder = collections.OrderedDict()
    for k in kits:
        by_folder.setdefault(k["ep"]["folder"], []).append(k)

    episodes, skipped_upcoming, skipped_unresolved, unsupported = [], [], [], []
    for folder, ks in by_folder.items():
        ep = ks[0]["ep"]
        meta = EP.resolve(ep)
        if not include_upcoming and (meta["upcoming"] or not meta["vid"]):
            # 動画がまだ公開されていない回、または動画が特定できなかった回は
            # サイトに一切出さない（キットページも作らない）。
            # 視聴者が動画より先にプレゼントへ辿り着けてしまう方が、
            # 一時的にサイトに出ないより悪いという判断。
            # ただし「まだ公開日が来ていない（正常）」と「公開済みなのに動画IDが
            # 特定できない（異常）」は原因も対処も別物なので、混ぜずに分けて記録する。
            # 一緒くたに「近日公開のため除外」と出していたせいで、公開済みの回が
            # 落ちているのに気づけなかったことがある（2026-08-27 aa No.99）。
            (skipped_upcoming if meta["upcoming"] else skipped_unresolved).append(
                (meta["date"], meta["title"]))
            continue
        if meta.get("support") == "none":
            # 投稿日とも動画タイトルとも噛み合っていない割り当て。出しはするが、
            # 人が一度は目で確かめられるように控えておく。
            unsupported.append((meta["date"], meta["title"]))
        episodes.append({
            "folder": folder,
            "channel": ep["channel"],
            "no": ep["no"],
            "title": meta["title"],
            "date": meta["date"],
            "vid": meta["vid"],
            "thumb": EP.thumb_url(meta["vid"]),
            "watch": EP.watch_url(meta["vid"]),
            "upcoming": meta["upcoming"],
            "uncertain": meta["uncertain"],
            "links": L.for_folder(folder),  # その回の解説資料（README/slides/onepager）へのリンク
            "kits": ks,
        })
    # 日付なしは末尾に回す（新しい順で見たときに紛れ込まないように）
    episodes.sort(key=lambda e: e["date"] or "0000-00-00", reverse=True)
    return episodes, skipped_upcoming, skipped_unresolved, unsupported


def build(code, preview=False, publish_token=None):
    th = T.THEMES[code]
    if publish_token:
        final_out = os.path.join(HERE, "gh-preview", f"preview-{publish_token}", code)
    elif preview:
        final_out = os.path.join(HERE, "preview", code)
    else:
        final_out = os.path.join(HERE, code)
    out = final_out + ".building"  # 完成するまでは一時ディレクトリに書く（_replace_dir参照）
    is_preview_mode = preview or bool(publish_token)
    kits = assign_slugs(P.collect(th["channel"]))
    icon = T.icon_data_uri(code)
    promo_icon = T.icon_data_uri("aa")  # クロスプロモ用（Kawaru系）。CC・AA両サイト共通
    n1inc_icon = T.n1inc_icon_data_uri()  # クロスプロモ用（エヌイチのB2Bサービス・会社HP）
    episodes, skipped_upcoming, skipped_unresolved, unsupported = assemble_episodes(
        kits, include_upcoming=is_preview_mode)
    visible_kits = [k for e in episodes for k in e["kits"]]
    # プロモに混ぜる動画（公開済みのものだけ。サムネイルがそのまま素材になる）
    promo_eps = [e for e in episodes if not e["upcoming"] and e["thumb"] and e["watch"]]

    if os.path.isdir(out):
        shutil.rmtree(out)  # 前回ビルドが途中失敗して残った一時ディレクトリの掃除
    os.makedirs(os.path.join(out, "assets"), exist_ok=True)

    # data.js も site.css も max-age=600 で配信されるため、内容ハッシュをクエリに付けて
    # 更新直後に古いキャッシュが使われるのを防ぐ（2026-08-27発覚: 公開済みなのに
    # ブラウザが古いdata.jsを掴んだままで「反映されていない」ように見えた。
    # 2026-08-29: CSSだけの変更が同じ理由で反映されて見えなかったので site.css も同様に）。
    css_text = css.build(th)
    css_ver = hashlib.sha256(css_text.encode("utf-8")).hexdigest()[:12]
    with open(os.path.join(out, "assets", "site.css"), "w", encoding="utf-8") as f:
        f.write(css_text)

    counts = collections.Counter(k["type"] for k in visible_kits)
    type_stats = [(t, counts[t]) for t in T.TYPE_ORDER if counts[t]]
    icons = {t: T.type_icon(t) for t, _ in type_stats}
    icons["_play"] = T.play_icon()

    data_js_text = render.data_js(episodes)
    data_ver = hashlib.sha256(data_js_text.encode("utf-8")).hexdigest()[:12]

    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write(render.hub(th, icon, episodes, type_stats, icons, TYPE_DESC, promo_icon, n1inc_icon,
                           preview=is_preview_mode, data_ver=data_ver, css_ver=css_ver, promo_eps=promo_eps))
    with open(os.path.join(out, "data.js"), "w", encoding="utf-8") as f:
        f.write(data_js_text)

    for ep in episodes:
        for k in ep["kits"]:
            d = os.path.join(out, "apps", k["slug"])
            os.makedirs(d, exist_ok=True)
            # 種別が同じ、別の回のプレゼント（新しい回から数件）
            related = [o for o in visible_kits
                       if o["type"] == k["type"] and o["ep"]["folder"] != ep["folder"]]
            related.sort(key=lambda o: (o["ep"]["date"] or "", o["ep"]["no"] or 0), reverse=True)
            if k.get("is_app"):
                # 原本そのまま app.html として置く: iframeのsrc兼、単体で開ける/ダウンロードできるURL
                with open(os.path.join(d, "app.html"), "w", encoding="utf-8") as f:
                    f.write(k["raw"])
                with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
                    f.write(render.app_page(th, icon, k, ep, promo_icon, n1inc_icon,
                                            preview=is_preview_mode, related=related, css_ver=css_ver,
                                            promo_eps=promo_eps))
            else:
                raw = open(k["src"], encoding="utf-8").read()
                with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
                    f.write(render.kit_page(th, icon, k, raw, ep, promo_icon, n1inc_icon,
                                            preview=is_preview_mode, related=related, css_ver=css_ver,
                                            promo_eps=promo_eps))

    # 回ごとの「まとめて1ファイル」ダウンロード（プレゼントが2点以上のときだけ）。
    # zipにしないのは、zlibのバージョン差でMacとGitHub Actionsのバイト列がずれ、
    # 両者が毎回差分を出し合うため（sips/アイコンと同じ問題）。素の.md連結なら生成が安定し、
    # GitHub Pagesがテキストをgzip配信するのでサイズも小さい。既存の「全件ダウンロード」と同じ素の.md。
    n_bundle = 0
    for ep in episodes:
        if len(ep["kits"]) < 2:
            continue
        bdir = os.path.join(out, "bundles")
        os.makedirs(bdir, exist_ok=True)
        parts = [f"# {ep['title']} — プレゼント一式",
                 f"# {ep['date'] or '日付未定'} 配布 / {len(ep['kits'])}点",
                 "# " + "=" * 58]
        for i, k in enumerate(ep["kits"], 1):
            parts.append(f"\n\n### {i}. {k['name']}（{k['type']}）")
            if k["desc"]:
                parts.append(f"# {k['desc']}")
            if k.get("is_app"):
                parts.append("\n（このプレゼントはブラウザで開いて使うアプリです。"
                             "図書館の受け取りページからご利用ください。）")
            else:
                parts.append("\n" + open(k["src"], encoding="utf-8").read().rstrip())
        with open(os.path.join(bdir, render.episode_anchor(ep) + ".md"), "w", encoding="utf-8") as f:
            f.write("\n".join(parts) + "\n")
        n_bundle += 1

    cards = sum(len(k["cards"]) or 1 for k in visible_kits)
    with_thumb = sum(1 for e in episodes if e["thumb"])
    size = sum(os.path.getsize(os.path.join(r, n))
               for r, _, ns in os.walk(out) for n in ns)

    _replace_dir(out, final_out)  # 完成した一時ディレクトリを本番パスへアトミックに差し替え

    if publish_token:
        tag = "（管理者限定プレビュー・GitHub Pages公開用）"
    elif preview:
        tag = "（プレビュー・非公開）"
    else:
        tag = ""
    print(f"[{code}]{tag} {th['channel_name']}")
    print(f"   配布回 {len(episodes)}回（サムネあり{with_thumb}） / "
          f"キット {len(visible_kits)}件 / 項目カード {cards:,}枚 / "
          f"まとめDL {n_bundle}件 / {size/1024/1024:.1f}MB")
    for t, n in type_stats:
        print(f"     - {t}: {n}")
    if skipped_upcoming:
        print(f"   非公開（投稿日がまだ来ていないため除外）: {len(skipped_upcoming)}回")
        for d, t in sorted(skipped_upcoming):
            print(f"     - {d}  {t}")
    n_all, no_date, no_time = EP.data_health(th["channel"])
    if no_date or no_time:
        # 自己修復する（次回の更新で取り直す）ので警告にはしないが、
        # 続くようなら取得が壊れている合図になるので必ず見えるようにしておく。
        print(f"   公開日時が未取得の動画: {no_date}/{n_all}本（時刻のみ未取得 {no_time}本）"
              f" ※次回の更新で取り直し")
    if unsupported:
        print(f"   [要確認] 投稿日とも動画タイトルとも噛み合っていない回: {len(unsupported)}回")
        for d, t in sorted(unsupported):
            print(f"     - {d}  {t}")
    if skipped_unresolved:
        # 投稿日を過ぎているのに動画が特定できていない＝プレゼントが出るはずの回が
        # 出ていない状態。ログを見た人が必ず気づくよう、警告として別枠で出す。
        print(f"   [要確認] 投稿日を過ぎているのに動画IDが特定できず除外: "
              f"{len(skipped_unresolved)}回")
        for d, t in sorted(skipped_unresolved):
            print(f"     - {d}  {t}")
    return visible_kits


if __name__ == "__main__":
    args = sys.argv[1:]
    preview = "--preview" in args
    publish = "--preview-publish" in args
    targets = [a for a in args if not a.startswith("--")] or ["cc", "aa"]
    L.refresh_local()  # Mac 上でだけ episode_links.json を作り直す（CIはコミット済みを使う）
    token = preview_token() if publish else None
    for c in targets:
        build(c, preview=preview, publish_token=token)
    if publish:
        print(f"\n公開URL（要push・gh-preview/ を git add してください）:")
        for c in targets:
            print(f"  https://chaaaaarin.github.io/gift-library/gh-preview/preview-{token}/{c}/")
