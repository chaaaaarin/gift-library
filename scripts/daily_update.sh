#!/bin/bash
# 毎日実行: data/更新 → ビルド → push → 「公開ページが実際に最新か」の検証。
# launchd（com.karin.gift-library-daily）から呼ばれる。手動実行も可。
#
# 設計方針: 各工程の成否ではなく「公開ページが手元と一致したか」を最終判定にする。
# git push が通っても GitHub Pages のビルドが落ちれば公開されず、しかも次回は
# git 差分が無いため永久に再試行されない（2026-08-27に実際に発生）。これを防ぐため、
# 差分の有無にかかわらず毎回 公開側と手元の data.js を突き合わせ、
# ズレていれば Pages の再ビルドを要求する。
set -e

cd "$(dirname "$0")/.."
mkdir -p logs
LOG="logs/$(date +%Y%m%d_%H%M%S).log"

REPO="chaaaaarin/gift-library"
BASE="https://chaaaaarin.github.io/gift-library"
GH=/opt/homebrew/bin/gh   # launchdのPATHは /usr/bin:/bin:/usr/sbin:/sbin のみ。絶対パス必須
LOCK="$PWD/.update.lock"
STATUS="$PWD/logs/last_status.txt"
SHOOT_DIR="${GIFT_SHOOT_DIR:-/Users/karin/Desktop/Claude Code/YouTube planning/YouTube research/撮影資料}"

# 多重起動防止（mkdirは原子的）。実行間隔は30分だが、検証待ちを含むと十数分かかる
# ことがあり、重なると data/ の同時書き込みや .git/index.lock 衝突で壊れる。
if ! mkdir "$LOCK" 2>/dev/null; then
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +90 2>/dev/null)" ]; then
    rmdir "$LOCK" 2>/dev/null || true
    mkdir "$LOCK" 2>/dev/null || exit 0
    echo "=== $(date '+%F %T') 古いロックを回収して続行 ===" >> "$LOG"
  else
    echo "=== $(date '+%F %T') 別の実行が進行中のためスキップ ===" >> "$LOG"
    exit 0
  fi
fi
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT

notify() {
  osascript -e "display notification \"$1\" with title \"プレゼント図書館 自動更新エラー\"" 2>/dev/null || true
}

# 「最後に公開が確認できたのはいつか」を1行で残す。通知は見逃せば終わりなので、
# 後から状態を確かめられる場所を1つ用意しておく。
status_write() {  # $1=OK|FAIL  $2=一言
  echo "$1  $(date '+%Y-%m-%d %H:%M:%S')  $2" > "$STATUS"
}

# 間隔を伸ばしながらリトライする。8/26はネットワークが1時間規模で不通だったため、
# 短い一定間隔では届かなかった。
retry() {  # $1=表示名  以降=実行するコマンド
  local label="$1"; shift
  local n=0 w
  if "$@"; then return 0; fi
  for w in 30 60 120; do
    n=$((n+1))
    echo "${label} 失敗（${n}回目）。${w}秒後リトライ"
    sleep "$w"
    if "$@"; then return 0; fi
  done
  echo "${label} が4回失敗しました。手動確認が必要です"
  notify "${label} が繰り返し失敗しました。ログを確認してください。"
  status_write FAIL "${label} 失敗"
  return 1
}

# 手元と公開側を突き合わせる。CDNキャッシュを踏まないよう毎回クエリを変える。
# index.html も見るのは、data.js だけ一致して index.html が古いままの
# 部分的な取りこぼしを検知するため（index.html は data.js のバージョンも抱えている）。
published_matches() {
  local c f lh ph
  for c in cc aa; do
    for f in index.html data.js; do
      [ -f "$c/$f" ] || return 1
      lh=$(shasum -a 256 "$c/$f" | cut -d' ' -f1)
      ph=$(curl -fsS --max-time 30 -H 'Cache-Control: no-cache' \
             "$BASE/$c/$f?t=$(date +%s)-$$" 2>/dev/null | shasum -a 256 | cut -d' ' -f1)
      [ "$lh" = "$ph" ] || return 1
    done
  done
  return 0
}

wait_published() {  # $1=試行回数（30秒間隔）
  local i
  for i in $(seq 1 "$1"); do
    if published_matches; then return 0; fi
    sleep 30
  done
  return 1
}

# ビルド結果が前回公開分より大幅に減っていたら公開を見送る。
# 撮影資料フォルダの移動・読み取り失敗などで配布回が消えたまま公開されるのを防ぐ
# （refresh_data.py 側の件数チェックと同じ考え方を、最終成果物にも掛ける）。
# 見送ってもコミットしないだけなので、公開中のサイトは無傷のまま残る。
# 生成器ソースを非公開リポジトリ(gift-library-src)へ退避する。
# 公開リポジトリ(gift-library)は成果物のcc/・aa/しか追跡せず、親リポジトリも
# 配布サイト/を除外しているため、ここが build.py・lib/・scripts/ の唯一のバックアップ。
# 同じ作業ディレクトリに別のgitディレクトリ(.git-src)を持たせている。
# 撮影資料のうち、ビルドが実際に読む kit/ だけを kits/ に複製する。
# GitHub Actions 側はこの複製からビルドする（撮影資料は500MBあるが大半は動画素材で、
# ビルドが読むのは */kit/*.md と */kit/*.app.html の233ファイル・3.9MBだけ）。
# 誤って動画素材を巻き込まないよう、kit配下だけを明示的に指定している。
mirror_kits() {
  [ -d "$SHOOT_DIR" ] || { echo "[警告] 撮影資料が見つからない: $SHOOT_DIR"; return 0; }
  rsync -am --delete --include='*/' --include='kit/***' --exclude='*' "$SHOOT_DIR/" kits/
  echo "kits/: $(find kits -type f | wc -l | tr -d ' ') ファイル"
  # 動画ごとの解説資料リンク（README/slides/onepager）を撮影資料フォルダの .git から拾って
  # data/episode_links.json に落とす。Actions 側は kits/ しか持たず .git が無いので、
  # ここで作ってコミット（直後の backup_src が git add -A で拾う）しないと CI に届かない。
  python3 lib/links.py "$SHOOT_DIR" data/episode_links.json \
    || echo "[警告] episode_links.json の生成に失敗（公開処理は続行）"
}

backup_src() {
  [ -d .git-src ] || return 0
  git --git-dir=.git-src --work-tree=. add -A . || return 1
  if git --git-dir=.git-src --work-tree=. diff --cached --quiet; then
    echo "ソース: 変更なし"
    return 0
  fi
  git --git-dir=.git-src --work-tree=. commit -q -m "ソース自動退避 $(date +%Y-%m-%d)" || return 1
  git --git-dir=.git-src --work-tree=. push -q || return 1
  echo "ソース: 退避完了"
}

build_sane() {
  local c new old
  for c in cc aa; do
    new=$(grep -o '"date":"' "$c/data.js" | wc -l | tr -d ' ')
    old=$(git show "HEAD:$c/data.js" 2>/dev/null | grep -o '"date":"' | wc -l | tr -d ' ')
    if [ "${old:-0}" -gt 0 ] && [ "$new" -lt $((old * 8 / 10)) ]; then
      echo "[中断] $c: 配布回が ${old} → ${new} に急減。公開を見送ります"
      return 1
    fi
  done
  return 0
}

# 動画公開(19:00)に張り付く見張りモード。19:01〜19:15に2分おきに呼ばれる。
#
# 「動画が公開された瞬間にプレゼントも公開される」のが目標だが、毎回フルで回すと
# cc/・aa/の21MBを2分おきに書き直すことになり、iCloud同期と競合しやすくなる
# （2026-08-25にそれでビルドが連続失敗している）。そこで、まずYouTubeの公開済み一覧
# だけを取り直し、前回から変化が無ければ何もせずに終わる。
# 変化を見つけたときだけ、下の通常処理へ流れてビルド・公開する。
WATCH=0
if [ "${1:-}" = "--watch" ]; then
  # ネットワークが不調な回は黙って見送る（2分後にまた来る）
  python3 scripts/refresh_data.py >/dev/null 2>&1 || exit 0
  sig=$(cat data/cc_youtube_videos.json data/aa_youtube_videos.json | shasum -a 256 | cut -d' ' -f1)
  if [ "$sig" = "$(cat logs/.watch_sig 2>/dev/null || true)" ]; then
    exit 0
  fi
  printf '%s' "$sig" > logs/.watch_sig
  WATCH=1
fi

# kitの複製とソース退避だけを行う軽量モード（30分おきに呼ばれる）。
# 「kitを書いたのに一度も同期しないままMacを閉じ、Actionsに届かない」を防ぐためのもの。
# ビルドも公開もしないので1秒程度で終わる。変化が無かった回は何も記録しない。
if [ "${1:-}" = "--sync-only" ]; then
  out=$( { mirror_kits; backup_src; } 2>&1 ) || true
  if ! printf '%s' "$out" | grep -q "ソース: 変更なし"; then
    {
      echo "=== $(date '+%Y-%m-%d %H:%M:%S') 同期 ==="
      printf '%s\n' "$out"
    } >> logs/sync.log
  fi
  exit 0
fi

{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') ==="

  # 公開の成否とは独立なので先に済ませる（公開が失敗する日でもソースは残す）
  mirror_kits || echo "[警告] kitの複製に失敗（公開処理は続行）"
  backup_src || echo "[警告] ソース退避に失敗（公開処理は続行）"

  if [ "$WATCH" = 1 ]; then
    echo "新しい動画を検知したため公開処理を行います（見張りモード）"
  else
    retry "refresh_data.py" python3 scripts/refresh_data.py
  fi
  retry "build.py" python3 build.py

  # 投稿日を過ぎているのに動画IDが特定できず、プレゼントが出ていない回の検知。
  # サイト自体は正常に見えるうえ配布回の急減にもならないため、
  # ログを読まない限り気づけない（2026-08-27 aa No.99 が丸一日出ていなかった）。
  UNRESOLVED=""
  if grep -q '\[要確認\]' "$LOG" 2>/dev/null; then
    UNRESOLVED=" / [要確認] 動画ID未確定の回あり"
    # 見張りモード（19:01〜19:21）は動画公開直後でYouTubeの一覧が数分遅れる時間帯そのもの。
    # ここでの未確定は次の見張り（2分後）でほぼ解消するので通知しない（毎回の誤報になっていた）。
    # 20:10の通常ビルドまで解消しなければ本物なので、そのときだけ通知する
    # （last_status.txt には見張り回も含め毎回残すので、記録は失わない）。
    if [ "$WATCH" != 1 ]; then
      notify "投稿日を過ぎたのに動画IDが特定できない回があります。プレゼントが出ていないのでログを確認してください。"
    fi
  fi

  if ! build_sane; then
    notify "ビルド結果の配布回が急減したため公開を見送りました。ログを確認してください。"
    status_write FAIL "ビルド結果が急減"
    exit 1
  fi

  # 外部からの見張り用ハートビート。1日1回だけ書き換える（毎回書くとコミットが増える）。
  # このファイルが公開URLで新しい日付のまま読めること自体が、
  # 「Macが動いた → pushされた → Pagesが配信した」までの証明になる。
  today=$(date +%Y-%m-%d)
  prev=$(grep -o '"date":"[0-9-]*"' status.json 2>/dev/null | grep -o '[0-9-]\{10\}' || true)
  if [ "$prev" != "$today" ]; then
    printf '{"date":"%s","time":"%s","cc_latest":"%s","aa_latest":"%s"}\n' \
      "$today" "$(date '+%Y-%m-%d %H:%M:%S')" \
      "$(grep -o '"date":"[0-9-]*"' cc/data.js | sort -u | tail -1 | grep -o '[0-9-]\{10\}')" \
      "$(grep -o '"date":"[0-9-]*"' aa/data.js | sort -u | tail -1 | grep -o '[0-9-]\{10\}')" \
      > status.json
    echo "ハートビート更新: $today"
  fi

  git add README.md .nojekyll cc aa status.json

  if git diff --cached --quiet; then
    echo "ビルド結果に変更なし"
  else
    git commit -m "自動更新 $(date +%Y-%m-%d)"
    echo "コミット作成"
  fi

  # 前回 push に失敗して手元に残ったコミットもここで拾う。これが無いと
  # 「commitは通ったがpushが落ちた」日以降、git差分が無いため二度とpushされない。
  ahead=$(git rev-list --count @{u}..HEAD 2>/dev/null || echo 0)
  if [ "$ahead" -gt 0 ]; then
    echo "未pushコミット ${ahead}件をpush"
    if ! retry "git push" git push; then
      # GitHub Actions と同時に走ると片方のpushが弾かれる。両者の出力は完全に一致するので、
      # リモートが手元のビルドと同じ内容なら、向こうが先にpushしただけ＝実害はない。
      git fetch -q origin || true
      if git diff --quiet origin/main -- cc aa; then
        echo "Actions側が同じ内容を先にpush済み。手元のコミットは取り下げる"
        git reset -q --hard origin/main
      else
        # 内容まで違う場合（Actionsのビルド後に新しいキットが増えた等）。
        # ここで exit すると、手元のコミットがリモートの後ろに残ったまま
        # 毎回 push が弾かれ、以後どの回も公開されなくなる（回復不能な詰み）。
        # 成果物はソースから作り直せるので、リモートに合わせてからビルドし直す。
        echo "リモートが先に進んでいるため、合わせ直してビルドし直します"
        git reset -q --hard origin/main
        retry "build.py(再ビルド)" python3 build.py
        git add README.md .nojekyll cc aa status.json
        if ! git diff --cached --quiet; then
          git commit -m "自動更新 $(date +%Y-%m-%d)"
          if ! retry "git push(再試行)" git push; then
            notify "リモートに合わせ直してもpushできませんでした。手動確認が必要です。"
            status_write FAIL "push再試行も失敗"
            exit 1
          fi
        fi
      fi
    fi
  else
    echo "pushすべきコミットなし"
  fi

  # ここが最終判定。push成功＝公開ではない。
  echo "公開状態を検証中..."
  if wait_published 10; then
    echo "公開を確認"
  else
    echo "公開が手元と一致しない。Pagesの再ビルドを要求します"
    if [ -x "$GH" ]; then
      "$GH" api -X POST "repos/$REPO/pages/builds" || true
    else
      echo "[警告] $GH が見つからないため再ビルドを要求できません"
    fi
    if wait_published 10; then
      echo "再ビルド後に公開を確認"
    else
      echo "再ビルドしても公開が一致しません。手動確認が必要です"
      notify "公開ページが最新になっていません。ログを確認してください。"
      status_write FAIL "公開検証に失敗"
      exit 1
    fi
  fi

  cc_latest=$(grep -o '"date":"[0-9-]*"' cc/data.js | sort -u | tail -1 | grep -o '[0-9-]\{10\}')
  aa_latest=$(grep -o '"date":"[0-9-]*"' aa/data.js | sort -u | tail -1 | grep -o '[0-9-]\{10\}')
  status_write OK "公開確認 / CC最新 ${cc_latest} / AA最新 ${aa_latest}${UNRESOLVED}"
  echo "CC: $BASE/cc/"
  echo "AA: $BASE/aa/"
  echo "=== 完了 ==="
} >> "$LOG" 2>&1

# 直近30日分だけログを残す
find logs -name '*.log' -mtime +30 -delete
