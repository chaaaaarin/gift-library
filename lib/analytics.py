# -*- coding: utf-8 -*-
"""アクセス解析の差し込み口。

189個のプレゼントがあるのに、どれが開かれているか分からない状態だったため用意した。
下の SNIPPET に計測タグをそのまま貼れば、ハブ・キットページ・プレビューの
すべてに入る。空のあいだは何も出力しないので、外部への送信は一切起きない。

サービスは問わない（貼った内容をそのまま出すだけ）。選ぶときの目安:

  - Cloudflare Web Analytics … 無料・Cookieを使わない・タグ1行。
    Cookie同意バナーが要らないため、視聴者の体験を邪魔しない。
  - GoatCounter … 無料枠あり・軽量・Cookieなし。
  - Plausible / Fathom … 有料（月$9前後）・Cookieなし・画面が見やすい。
  - Google Analytics … 無料だがCookieを使うため、地域によっては同意取得が要る。

貼る前に確認すること:
  - Cookieを使う計測を入れる場合は、同意の取り方も併せて決める
  - プレゼントのURLには視聴者の個人情報が含まれないので、経路の記録自体は問題ない
"""

SNIPPET = """<!-- Cloudflare Web Analytics --><script type='module' src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{"token": "1bdbdde44b614116a41a1e00133ac91f"}'></script><!-- End Cloudflare Web Analytics -->"""


def block(preview=False):
    """</body> の直前に入れる計測タグ。未設定なら何も出さない。

    preview=True（管理者用プレビュー）では出さない。自分が確認で開いたぶんが
    視聴者の数字に混ざると、どのプレゼントが使われているかが読めなくなるため。
    """
    if preview:
        return ""
    s = SNIPPET.strip()
    return f"\n{s}\n" if s else ""
