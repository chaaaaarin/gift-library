# チャンネル別 プレゼント配布サイト

回ごとの `present.html` に代えて、**チャンネルごとの常設サイト**にプレゼントを集約する。
動画ごとのGitHubリポからは、このサイトのURLを貼るだけにする。

サイトの主導線は「**動画1本 = プレゼントのグループ**」。ハブは種別の棚ではなく、
配布回（動画）を新しい順に並べたカード一覧で、各カードに実サムネ・投稿日・動画タイトルと、
その回のキットへのリンクを並べる。視聴者は「この動画で言ってたやつ」を見た目で探せる。

```
配布サイト/
├── build.py           生成スクリプト（これを実行するだけ）
├── data/               動画メタデータの原本（このフォルダだけ手動更新・下記参照）
│   ├── cc_episodes.csv / aa_episodes.csv   チャンネルの動画管理表CSV
│   ├── cc_youtube_videos.json / aa_youtube_videos.json  YouTube実動画一覧
│   └── episode_links.json  回ごとの解説資料リンク（撮影資料の.gitから自動生成・下記参照）
├── lib/
│   ├── parse_kits.py  撮影資料/*/kit/*.md（テキスト）・*.app.html（アプリ）を読み取り、項目カードに割る
│   ├── episodes.py    No.→{タイトル・投稿日・動画ID} の突き合わせ（下記参照）
│   ├── links.py       撮影資料/*/.git → 回ごとの資料リンク（README/slides/onepager）を episode_links.json に落とす
│   ├── theme.py        チャンネル配色・アイコン・種別アイコン
│   ├── css.py           共通スタイル（CC資料の語彙: 左5px罫・丸ピル・濃色pre）
│   └── render.py        ハブ（動画カード）と受け取りページの組み立て（kit_page=テキスト・app_page=アプリ）
├── cc/                ← 生成物: ClaudeCodeチャンネル
│   ├── index.html     ハブ（動画カード一覧・検索・種別しぼり込み・並び替え・月グルーピング）
│   ├── data.js         動画ごとのカード一覧データ
│   ├── assets/site.css
│   ├── bundles/<動画ID>.md  ← その回のプレゼントを1ファイルにまとめた版（2点以上の回のみ）
│   └── apps/<キット名>/index.html   受け取りページ（冒頭にその動画の文脈を表示）
│       └── apps/<キット名>/app.html  ← アプリ型のみ: 原本そのまま（iframeのsrc兼、単体URL/ダウンロード対象）
└── aa/                ← 生成物: Kawaruチャンネル（同構造）
```

## ハブの導線（2026-08-29 追加分）

- **この回を全部ダウンロード**: プレゼントが2点以上の回に、全プレゼントを1本にまとめた
  `bundles/<動画ID>.md` へのボタンを出す（ハブのカード＋受け取りページ）。ファイル名の
  `<動画ID>` は `render.episode_anchor()`（動画ID優先・無ければ日付）。zipにしないのは
  zlibのバージョン差でMac/CIのバイト列がずれるため（既存「全件ダウンロード」と同じ素の.md）。
- **月ナビ（`❮ 2026年8月 ❯`）**: 日付順のとき、2カラム（`.cols`）の上に細い行として出す
  （`.cols` の外に置くことで、左サイドと一覧カードの上端がそろう）。ヘッダ(約62px)直下に
  貼り付き、いま画面に来ている月をラベルに出し（スクロールに追従）、`❮`＝古い月へ /
  `❯`＝新しい月へ スクロールする。飛び先は各月の先頭カードに付けた `id="m-YYYY-MM"`。
  枠・影は持たせず地色フェードのみ。タイトル順では隠す。`.side` の `top:100px` はこのバーの
  下に来るための値（初期位置は `.cols` 上端のままなので上端そろえは崩れない）。
  （当初は左サイドの「月で移動」リンク一覧 → カレンダー風の中央バー → この控えめな行、と調整）
- **おすすめ診断（`.finder`）**: 以前は `.stats` と `.cols` の間に全幅で置いていたが、
  導線の邪魔になるので左サイドの検索・しぼり込みの下へ、小さい折りたたみとして移動した。

（回ごとのディープリンク `#ep-<動画ID>` は 2026-08-29 に一度入れたが、導線が増えて
ややこしくなるため同日中に撤去した。id は付けていない。）

## 作り直す＋公開する（毎回セット・ユーザー指定）

```bash
python3 build.py        # cc・aa の両方
git add README.md .nojekyll cc aa    # data/・lib/・build.py・MAINTAINER.mdは絶対に足さない
git commit -m "update"
git push
```

`cc/` `aa/` は毎回まるごと作り直される。**手で編集しても次回のビルドで消える**ので、
直すときは `lib/` 側を直す。原本の `撮影資料/` は読み取りしかしない。

公開先: `https://github.com/chaaaaarin/gift-library`（Pages有効化済み・push後1〜2分で反映）
- CC: https://chaaaaarin.github.io/gift-library/cc/
- AA: https://chaaaaarin.github.io/gift-library/aa/

**公開してよいのはこの4つだけ**: `README.md`（このファイルではなく公開用の短いもの）・
`.nojekyll`・`cc/`・`aa/`。`data/`（スタッフ名・再生数など内部の動画管理表）と
`lib/`・`build.py`・この `MAINTAINER.md` は非公開のまま。`git add -A` は使わない。

## 手元で確認する

```bash
python3 -m http.server 8781
```

`http://localhost:8781/cc/` を開く。`file://` 直開きでも動くが、確認はHTTP経由で行う。

## 動画公開前にプレゼントを確認する（管理者用プレビュー・2026-08-25〜）

本番ビルドは「動画がまだ公開されていない回」をサイトから自動で除外する（視聴者が動画より
先にプレゼントへ辿り着けてしまうのを防ぐため・上記「中身の作られ方」参照）。この設計の
副作用として、管理者も動画公開までプレゼントの実際の見た目・動作を確認できなくなる。
これを解決するのが `--preview`（ローカル専用）と `--preview-publish`（管理者間で共有できる
GitHub Pages公開）の2つのフラグ。

```bash
python3 build.py --preview            # ローカル専用（自分のMacでしか見られない）
python3 build.py --preview-publish    # 管理者全員で共有できるURLとしてGitHub Pagesに生成
```

共通: 出力には「動画がまだ公開されていない回」も含まれ、ハブページ上部に赤い
「🔒 管理者用プレビューです」バナーが出る（本番と見分けるため）。

**`--preview`（ローカル専用）**
- 出力先は本番と別の `preview/cc/` `preview/aa/`。本番の `cc/` `aa/` には一切触れない
- `preview/` は `.gitignore` 対象で、`git add cc aa` の明示列挙にも含まれないため、
  誤って公開される心配はない
- 見るときは自分のMac上で `python3 -m http.server` を `preview/` に対して立てて開く
  （`file://` はチャットのリンク自動検出で開けないことがあるため、http.server推奨。
  2026-08-25に発覚）

**`--preview-publish`（管理者間で共有・GitHub Pages公開）**
- 出力先は `gh-preview/preview-<token>/cc/` `gh-preview/preview-<token>/aa/`。
  `<token>` は初回のみランダム生成し `.preview_token`（ローカル管理・.gitignore対象）に
  保存して使い回す推測困難な文字列
- `gh-preview/` は本番の `cc/`・`aa/` と同様に **git add してpushする対象**。
  本番とは別の「知っていれば誰でも見れるが、リンクされておらず検索にも出ない」隠しURLとして
  管理者間で共有する（各ページに `<meta name="robots" content="noindex,nofollow">` も付く）
- 公開URL: `https://chaaaaarin.github.io/gift-library/gh-preview/preview-<token>/cc/`
  （`/aa/` も同様。回ごとに変わらない固定値）
- push手順: `git add README.md .nojekyll cc aa gh-preview` → commit → push
  （通常の本番pushに `gh-preview` を足すだけ）

動画が実際に公開されたら、プレビューは消してもよい（次に必要になったときまた作ればよい）。
本番反映は従来どおり `python3 build.py`（引数なし）または毎日の自動更新で行う。

## 置き場所（2026-08-27にDesktopから移動）

**このフォルダは `~/gift-library/` に置く。Desktop配下（iCloud同期対象）には戻さないこと。**

ビルドは `cc/` `aa/` の14MBを1日に何度も書き直すため、iCloud同期と競合する。
2026-08-25にビルドが連続失敗し（`Resource deadlock avoided`）、
2026-08-27には `cc/` 本体がiCloudに `cc 6` へリネームされて消えた
（公開済みだったため実害なし・再生成で復旧）。競合コピーは同日59件・18.4MB削除した。

撮影資料（`YouTube research/撮影資料/`）はDesktopのままでよい。読み取りしかしないため。

## 毎日の自動更新（launchd・2026-08-27〜）

動画の公開は **19:00 JST**。「動画が公開された瞬間にプレゼントも公開される」ことを目標に、
`scripts/daily_update.sh` を3つのジョブが役割を分けて呼ぶ。

| ジョブ | 時刻 | モード | 役割 |
|---|---|---|---|
| `gift-library-watch` | 19:01〜19:21 の2分おき（11回） | `--watch` | **公開の瞬間を捕まえる**。毎回YouTubeの一覧を取り直すだけ（約10秒・`cc/`には触らない）で、新着を見つけた回だけビルドして公開する |
| `gift-library-daily` | 20:10 | （通常） | 見張りが取りこぼした場合のフルビルド |
| `gift-library-sync` | 30分おき | `--sync-only` | 書いたkitをActions側へ届ける（約1秒） |

見張りが毎回ビルドしないのは、`cc/`・`aa/` の21MBを2分おきに書き直すと
iCloud同期と競合しやすくなるため（2026-08-25にそれでビルドが連続失敗している）。
実測でビルドは0.57秒だが、YouTubeの確認に12秒かかる＝ネットワークが律速。

通常モードは `data/` 更新 → ビルド → push → **公開されたことの検証**まで行う。

設計の要点は「push が通った＝公開された、ではない」こと。GitHub Pages のビルドが
落ちると公開されないうえ、次回は git 差分が無いため二度と再試行されない
（2026-08-27に実際に発生）。そのため**差分の有無にかかわらず毎回**、公開側と手元の
`index.html` / `data.js` のハッシュを突き合わせ、ズレていれば Pages の再ビルドを要求する。

内蔵している安全装置:

| 仕組み | 防ぐ事故 |
|---|---|
| `.update.lock`（mkdir・90分でstale回収） | 実行の重なりによる `data/` 同時書き込み・`.git/index.lock` 衝突 |
| 30/60/120秒のリトライ | 一時的なネットワーク断（2026-08-26に1時間規模で発生） |
| `refresh_data.py` の件数急減チェック | 欠けた応答をそのまま書いて配布回が消えること |
| `build_sane`（配布回が2割以上減ったら中断） | 撮影資料の読み取り失敗のまま公開すること |
| 未pushコミットの拾い直し | commit成功→push失敗の日以降、永久にpushされなくなること |
| 公開ハッシュ検証＋Pages再ビルド要求 | Pagesビルド失敗に気づかないこと |

**状態の確認は `logs/last_status.txt` を見る**（`OK <日時> 公開確認 / CC最新 … / AA最新 …`）。
日時が古ければ、その時点から自動更新が止まっている。詳細は `logs/<日時>.log`。

外出先・スマホからは **<https://chaaaaarin.github.io/gift-library/status.json>** を開けば同じことが分かる
（1日1回だけ書き換わる。このURLで新しい日付が読める＝Macが動きpushされPagesが配信した、までの証明）。

### ソースの保全（gift-library-src・非公開）

公開リポジトリ `gift-library` は成果物の `cc/` `aa/` しか追跡しない。生成器のソースは
**非公開リポジトリ `chaaaaarin/gift-library-src`** に退避している。同じ作業ディレクトリに
別のgitディレクトリ `.git-src` を持たせる方式で、ファイルの二重管理は起きない。

`daily_update.sh` が毎回 `backup_src` で自動退避するので普段は何もしなくてよい。手動なら:

```
git --git-dir=.git-src --work-tree=. status
git --git-dir=.git-src --work-tree=. push
```

### GitHub Actions でも同じものをビルドする（2026-08-27〜）

Macが落ちていても更新されるよう、**非公開リポジトリ `gift-library-src` の
`.github/workflows/build.yml`** が 18:45 / 20:00 / 21:30 JST にビルドし、成果物だけを
公開リポジトリへpushする。認証はそのリポジトリ1つに限定したデプロイキー（PATより権限が狭い）。

**Mac側とActions側は同じ出力になるように揃えてある**ので、両方動いていても衝突しない:

- `sips`（macOS専用）で作っていたアイコンの data URI は `assets_src/*.b64` に事前計算済み。
  Pillow等で置き換えると出力バイト列が変わり、両者が毎回差分を出し合うことになるため
- フォルダ名は `parse_kits._nfc` でNFCに正規化。macOSはNFD（「アプデ」の「プ」＝フ+゜）、
  Linuxのgitチェックアウトは NFC を返すため、揃えないと同じ回が別物として出力される
- pushが競合したときは、リモートが手元のビルドと同じ内容であることを確かめた上で取り下げる

**Mac側のジョブは止めないこと。** 新しく書いたkitを `kits/` に複製して
`gift-library-src` へ送っているのはMac側だけで、これが止まるとActionsは古いkitでビルドし続ける。

アイコン画像を差し替えたときは `assets_src/*.b64` を作り直す:

```
python3 -c "import sys;sys.path.insert(0,'lib');import theme as T;open('assets_src/icon_cc.b64','w').write(T.icon_data_uri('cc'))"
```

### Macを持たずに何日か離れるとき

**特別な操作は要らない。** 公開はActions側が独立して回しており、Macの電源とは無関係。
「旅行だから切り替える」という手順は存在しない。

Mac依存が唯一残るのは「書いたkitをActions側へ届ける」ところだが、これも
**`com.karin.gift-library-sync` が30分おきに自動で行う**（`daily_update.sh --sync-only`。
ビルドも公開もしないので1秒程度）。kitを書いてMacを閉じても、30分以内に届いている。

念のため確認したいときだけ:

```
bash scripts/pretravel_check.sh
```

kitが渡っているか・push済みか・留守中に自動公開される回はどれか・自動更新が動いているかを
まとめて出す。**書き忘れた回に気づくのが主な用途**で、予定している動画が一覧に無ければ
その回のkitがまだ無い。

出先からの確認は <https://chaaaaarin.github.io/gift-library/status.json>。

制約: Actionsは公開リポジトリのPages再ビルドAPIを叩けない（デプロイキーはgit専用）ため、
Pages側のビルドが失敗した場合は自動復旧せず、ワークフロー失敗のメールが届くだけになる。
Macが動いていれば自動で復旧する。

### 外部からの見張り（GitHub Actions）

Macの電源が落ちていれば、Mac上のどの仕組みも通知を出せない。`.github/workflows/watchdog.yml`
が毎日00:00 JSTに公開サイトの `status.json` を確認し、2日以上滞っていればワークフローを
失敗させる（GitHubからメールが届く）。手動確認は `gh workflow run watchdog.yml`。

注意: launchd の PATH は `/usr/bin:/bin:/usr/sbin:/sbin` しかないため、`gh` は
`/opt/homebrew/bin/gh` と**絶対パス**で書いている。素の `gh` にすると手動実行では
動くのに launchd からだけ落ちる。

## クロスプロモ（ポップアップ広告）

`lib/render.py` の `_promo_creatives`（固定の宣伝）と `_video_creatives`（最近の動画）を
合わせた中から、毎回ランダムに1つ出す。閉じたらそのタブでは再表示しない。

出るタイミングは「0.4画面ぶんスクロールした時点」または「10秒経過」。
動画の概要欄から来た人がプレゼントを探している瞬間を塞がないための設計。

見た目の出し分け:

- `img` があるものは横長の画像で見せる（動画はサムネイル、LPは先方の og:image）
- `img` が無いものは丸アイコン。`accent` を指定するとタグとボタンの色が変わる
- 画像が404になった場合はアイコン表示に自動で戻る

宣伝を足すときは `_promo_creatives` に1件追加するだけ。画像があるなら `img` を、
無いなら `accent` で他と色を変えると、続けて出たときに同じ広告に見えにくい。

**エヌイチ系3件は先方のog:imageが3件とも同一**のため、画像では見分けられない。
個別の画像が用意できたら `img` を足すのが望ましい。

## アクセス解析を入れるとき

`lib/analytics.py` の `SNIPPET` に計測タグをそのまま貼り、ビルドし直すだけ。
ハブ・キットページ・プレビューのすべての `</body>` 直前に入る。
空のあいだは1文字も出力しないので、外部への送信は起きない。

サービスは問わない。Cookieを使うもの（Google Analytics等）を入れる場合は、
同意の取り方も併せて決めること。Cookieを使わないもの
（Cloudflare Web Analytics・GoatCounter・Plausible等）なら同意バナーは不要。

## どこに置いても動く

ビルド不要・相対パスのみの純静的サイト。Vercel / Cloudflare Pages / GitHub Pages の
どれにも `cc/` `aa/` をそのまま置ける。ホスティングは未確定のまま作れる。

- **サブドメイン方式**（参考: fuuuuuuma.dev）にする場合も、`apps/<キット名>/` の階層は
  そのまま使えるので、あとから独自ドメインを被せるだけでよい
- `data.js` は JSON ではなく `window.GIFTS = […]` の形にしてある。`fetch` を使わないので
  `file://` でも動き、ホスト側の設定に依存しない

## 中身の作られ方

原本は `撮影資料/<回>/kit/*.md`（テキスト）と `kit/*.app.html`（アプリ・単体で動くHTML）だけ。
`present.html` や `kit-*.html` は参照しない。

| mdの形 | サイトでの見え方 |
|---|---|
| `### N. タイトル` ＋ `説明:` ＋ ```text 本文 | 1項目 = 1カード（コピー・個別DL付き） |
| `■ 見出し` ＋ 連番（本文全体で5個以上） | 連番1つ = 1カード、■ = カテゴリ見出し |
| `■ ステップN` ＋ `□ 判定項目` | ■ 1つ = 1カード |
| `## 見出し` のみ | ## 1つ = 1カード |
| 500文字未満・構造なし | 1枚のカードにそのまま |

見出しが `### 1.` のように番号だけのキットは、本文の `指示:` 行から見出しを起こす。

「全件ダウンロード」は `kit/*.md` の**原本そのまま**を返す（バイト単位で一致）。

`kit/*.app.html` は `<title>`＝名前・`<meta name="description">`＝説明として拾い、原本をそのまま
`apps/<スラッグ>/app.html` に配置する。受け取りページ（`apps/<スラッグ>/index.html`）はこれを
同一オリジンのiframeで埋め込み、`contentWindow.document` の高さを見て自動でリサイズする
（postMessage不要。原本の中身には一切手を入れない）。ダウンロードボタンは `app.html` への直リンク
（`download`属性）。書式の詳細は `memory/present-kit-guide.md` §4.7。

## 動画ごとの資料リンク（資料・スライド・1枚資料）

ハブの動画カードと受け取りページの「▶ 動画を見る」の下に、その回の解説資料3点への
ボタンを出す（2026-08-29〜）。

| ボタン | リンク先 | 実体 |
|---|---|---|
| 📚 資料 | `https://github.com/chaaaaarin/<repo>` | 撮影資料/<回>/README.md（教科書本体） |
| 🖥 スライド | `https://chaaaaarin.github.io/<repo>/slides.html` | 撮影資料/<回>/slides.html |
| 📄 1枚資料 | `https://chaaaaarin.github.io/<repo>/onepager.html` | 撮影資料/<回>/onepager.html |

`<repo>` はリポジトリ名で、規則が無い（`claudecode-channel-20260829` /
`claudecode-channel-20260821-2` / `kawaru-20260629` …）。フォルダ名からは導出できないので、
**各 `撮影資料/<回>/.git/config` の origin リモートから読む**。`lib/links.py` がこれをやり、
`slides.html`・`onepager.html` が実在する回だけ URL を入れて `data/episode_links.json` に
書き出す（キーは NFC 正規化した撮影資料フォルダ名）。

- **Mac**: `build.py` 実行時に `links.refresh_local()` が毎回作り直す（撮影資料に `.git` が
  見えているときだけ動く）。`daily_update.sh` の `mirror_kits()` でも作り直し、直後の
  `backup_src` が `.git-src` へコミットする。
- **GitHub Actions**: 撮影資料を持たず `kits/`（`*/kit/***` だけ・`.git` 無し）からビルドするため
  自力では作れない。`.git-src` に入っている `data/episode_links.json` を読む。
- **新しい回**: リポジトリを push しても、`episode_links.json` に載るのは次の
  `--sync-only`（30分おき）または Mac のフルビルドの後。それまでボタンは出ない
  （リンクが無ければ何も描画しない）。

手動で作り直す: `python3 lib/links.py "<撮影資料ディレクトリ>" data/episode_links.json`

## 動画メタデータ（タイトル・投稿日・サムネ）の作られ方

撮影資料フォルダ名の `No.XX` は視聴者には意味がないため、サイトには一切出さない
（内部の突き合わせキーとしてのみ使う）。表に出すのは常に「動画の実タイトル・実際の投稿日」。

- **タイトル・投稿日**: チャンネルの動画管理スプレッドシートのCSV（`data/*_episodes.csv`）から。
  `No.` 列で撮影資料フォルダと対応させる
- **サムネ・動画リンク**: YouTubeチャンネルの実際の動画一覧（`data/*_youtube_videos.json`）から。
  スプレッドシートの「完成動画URL」列に実URLがあればそれを最優先。無い場合は
  投稿日の並び順とタイトルの特徴語（英数字・カタカナ・固有名詞）でYouTube側の動画を推定する
  （`lib/episodes.py` の `build()`）。**それでも一致しないものは動画IDを付けない**——
  誤った動画のサムネを出すより、出さない方が安全という判断。その場合もタイトルと日付は
  スプレッドシートから正しく出るので、視聴者が困ることはない
- **投稿日が未来の回**（編集済みだがまだ公開前）は「近日公開」表示にし、サムネなしでタイトル・
  日付だけ出す。動画が実際に公開されたら、`data/*_youtube_videos.json` を撮り直して
  再ビルドすれば自動でサムネが付く

### `data/` の更新手順（動画が新しく公開されたら）

1. スプレッドシートを開き `.../export?format=csv&gid=0` へ遷移 → ダウンロードされたCSVを
   `data/cc_episodes.csv` / `data/aa_episodes.csv` に上書き
2. YouTubeチャンネルの動画一覧ページ（`@n8nchannel/videos` = CC、`@aiagent-kawaru/videos` = AA）
   を開き、ページ内の `ytInitialData` と `/youtubei/v1/browse` 継続APIを叩いて全動画の
   `{videoId, title}` を集め、`data/cc_youtube_videos.json` / `data/aa_youtube_videos.json` に保存
   （手順はいずれもブラウザの開発者コンソール相当の操作。次回は同じ手順をこのセッションの
   会話ログか `lib/episodes.py` の docstring を参照して再現する）
3. `python3 build.py`

## 新しい回を足すとき

`撮影資料/` に新しい回のフォルダと `kit/*.md`（`kit/*.app.html` も可）を置いて `python3 build.py` を実行するだけ。
URL（`apps/<キット名>/`）は**古い回から順に**確定するので、回を足しても既存URLは変わらない。
キット名が過去と衝突したときだけ `-noNN` が付く。
動画メタデータが古くなっている場合は、先に上記の `data/` 更新手順を行ってからビルドする。
