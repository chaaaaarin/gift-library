#!/bin/bash
# 旅行前チェック: Macを持たずに出かけても、プレゼントが自動で公開され続けるかを確認する。
#
#   bash scripts/pretravel_check.sh
#
# 見ているのは「留守中にGitHub Actionsが使う材料が、全部GitHubに渡っているか」。
# kitをActions側へ送っているのはMacだけなので、そこだけは出発前に済ませる必要がある。
set -e

cd "$(dirname "$0")/.."
SHOOT_DIR="${GIFT_SHOOT_DIR:-/Users/karin/Desktop/Claude Code/YouTube planning/YouTube research/撮影資料}"
NG=0

echo "=============================================="
echo " 旅行前チェック  $(date '+%Y-%m-%d %H:%M')"
echo "=============================================="
echo

echo "[1] 書いたkitがActions側に渡っているか"
if [ ! -d "$SHOOT_DIR" ]; then
  echo "    NG: 撮影資料が見つかりません: $SHOOT_DIR"
  NG=1
else
  pending=$(rsync -amn --delete --include='*/' --include='kit/***' --exclude='*' \
              "$SHOOT_DIR/" kits/ 2>/dev/null | grep -cE "\.(md|html)$" || true)
  if [ "$pending" -gt 0 ]; then
    echo "    NG: まだ複製されていないkitが ${pending} 件あります"
    echo "        → bash scripts/daily_update.sh を実行してください"
    NG=1
  else
    echo "    OK: kits/ は撮影資料と一致しています（$(find kits -type f | wc -l | tr -d ' ') ファイル）"
  fi
fi
echo

echo "[2] ソースとkitがGitHubにpush済みか"
if [ -n "$(git --git-dir=.git-src --work-tree=. status --porcelain 2>/dev/null)" ]; then
  echo "    NG: 未コミットの変更が残っています"
  echo "        → bash scripts/daily_update.sh を実行してください"
  NG=1
elif [ "$(git --git-dir=.git-src --work-tree=. rev-list --count @{u}..HEAD 2>/dev/null || echo 0)" -gt 0 ]; then
  echo "    NG: 未pushのコミットがあります"
  echo "        → git --git-dir=.git-src --work-tree=. push"
  NG=1
else
  echo "    OK: gift-library-src は最新です"
fi
echo

echo "[3] 留守中に自動公開される回"
python3 - <<'PY'
import sys
sys.path.insert(0, "lib")
sys.argv = ["pretravel"]
import parse_kits as P, theme as T, build as B
for code in ("cc", "aa"):
    kits = B.assign_slugs(P.collect(T.THEMES[code]["channel"]))
    eps, upcoming = B.assemble_episodes(kits, include_upcoming=False)
    name = T.THEMES[code]["channel_name"]
    if upcoming:
        print(f"    [{code}] {name}: {len(upcoming)}回ぶんのkitが待機中")
        for d, t in sorted(upcoming):
            print(f"          {d}  {t[:44]}")
    else:
        print(f"    [{code}] {name}: 待機中のkitはありません")
PY
echo "    ※ ここに出ている回は、動画が公開された時点で自動的にプレゼントが出ます。"
echo "      予定している動画がこの一覧に無い場合は、その回のkitがまだ書けていません。"
echo

echo "[4] 自動更新が今動いているか"
body=$(curl -fsS --max-time 20 -H 'Cache-Control: no-cache' \
        "https://chaaaaarin.github.io/gift-library/status.json?t=$(date +%s)" 2>/dev/null || true)
if [ -z "$body" ]; then
  echo "    NG: status.json を取得できません"
  NG=1
else
  last=$(echo "$body" | grep -o '"date":"[0-9-]*"' | grep -o '[0-9-]\{10\}')
  echo "    最終更新: $last"
  if [ "$last" = "$(date +%Y-%m-%d)" ] || [ "$last" = "$(date -v-1d +%Y-%m-%d)" ]; then
    echo "    OK: 自動更新は動いています"
  else
    echo "    NG: 更新が止まっている可能性があります"
    NG=1
  fi
fi
echo

echo "=============================================="
if [ "$NG" -eq 0 ]; then
  echo " 問題なし。このまま出かけて大丈夫です。"
  echo " 出先での確認: https://chaaaaarin.github.io/gift-library/status.json"
else
  echo " 上の NG を解消してから出発してください。"
fi
echo "=============================================="
