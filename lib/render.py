# -*- coding: utf-8 -*-
"""ハブ（辞典）ページと、キットごとの受け取りページを組み立てる。"""
import html, json, re, sys

# jp_linebreak.py は lib/ に取り込んである（正典は
# ~/.claude/skills/research/references/jp_linebreak.py。このMac以外でも動かすため複製した）。
# 正典が更新されたら lib/jp_linebreak.py も差し替えること。
from jp_linebreak import wrap_text
import theme as T
import analytics as A

E = lambda s: html.escape(s or "", quote=True)


def NB(s, max_len=18, hard_max=26):
    """意味の切れ目でだけ改行させる（.nb チャンク化・正典 jp_linebreak.py）。"""
    return wrap_text(E(s), max_len=max_len, hard_max=hard_max) if s else ""


def _head(title, theme, icon, css_path, desc="", noindex=False, share_img="", css_ver=""):
    """ページの<head>。

    share_img は X・LINE・Slack などに貼ったときのカード画像。
    OGPの画像は絶対URLでないと拾われないため、data URI のチャンネルアイコンは使えない。
    代わりに動画のサムネイル（i.ytimg.com の絶対URL）を渡している。
    og:url は入れない——入れると特定のホスト名に固定されてしまい、
    「どこに置いても動く」という前提が崩れるため（クローラは取得先URLを使う）。
    """
    robots = '<meta name="robots" content="noindex,nofollow">\n' if noindex else ""
    og = f"""<meta property="og:type" content="website">
<meta property="og:site_name" content="{E(theme['site_name'])}">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
"""
    tw = '<meta name="twitter:card" content="summary">\n'
    if share_img:
        og += f'<meta property="og:image" content="{E(share_img)}">\n'
        tw = (f'<meta name="twitter:card" content="summary_large_image">\n'
              f'<meta name="twitter:image" content="{E(share_img)}">\n')
    tw += (f'<meta name="twitter:title" content="{E(title)}">\n'
           f'<meta name="twitter:description" content="{E(desc)}">\n')
    return f"""<!doctype html>
<html lang="ja"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
{og}{tw}{robots}<link rel="icon" href="{icon}">
<link rel="stylesheet" href="{css_path}{('?v=' + css_ver) if css_ver else ''}">
</head><body>"""


# ============================ クロスプロモ（ポップアップ） ============================
# アプリの案内モーダルのような「画面中央に大きく出る・×は大きく分かりやすい」ポップアップ。
# 動画概要欄によく出てくるリンク（Kawaru本体・Kawaru Coach・エヌイチのB2Bサービス2つ・会社HP）
# から毎回ランダムに1つ表示する。閉じたら同じセッション中は出さない（sessionStorage）。
# CC・AA両サイトに共通で入れる。

PROMO_JS = r"""
(function(){
  if (sessionStorage.getItem('promoClosed')) return;
  var el = document.getElementById('promo');
  if (!el) return;
  var creatives = window.PROMO_CREATIVES || [];
  if (!creatives.length) return;
  var c = creatives[Math.floor(Math.random() * creatives.length)];
  var banner = document.getElementById('promoBanner');
  var icon = document.getElementById('promoIcon');
  // 画像があるものは横長の絵で見せる。無いものは従来どおり丸アイコン。
  if (c.img) {
    banner.src = c.img;
    banner.style.display = 'block';
    icon.style.display = 'none';
    // 差し替え等で画像が消えていたら、アイコン表示に戻す
    banner.onerror = function(){
      banner.style.display = 'none';
      if (c.icon) { icon.src = c.icon; icon.style.display = 'block'; }
    };
  } else {
    icon.src = c.icon;
    icon.style.display = 'block';
    banner.style.display = 'none';
  }
  // 画像で見分けられないもの（エヌイチ系は先方のog:imageが3件とも同じ）は色で差をつける
  var tag = document.getElementById('promoTag');
  var cta = document.getElementById('promoLink');
  if (c.accent) {
    tag.style.color = c.accent;
    tag.style.background = c.accent + '1F';
    cta.style.background = c.accent;
  } else {
    tag.style.color = ''; tag.style.background = ''; cta.style.background = '';
  }
  tag.textContent = c.tag;
  document.getElementById('promoTitle').textContent = c.title;
  var txt = document.getElementById('promoText');
  txt.textContent = c.text || '';
  txt.style.display = c.text ? 'block' : 'none';
  document.getElementById('promoCta').textContent = c.cta;
  var link = document.getElementById('promoLink');
  link.href = c.url;
  function close(){
    el.classList.remove('show');
    sessionStorage.setItem('promoClosed', '1');
  }
  // 動画の概要欄から来た人が、自分のプレゼントを探し始める瞬間に被らないようにする。
  // 以前は読み込み1.6秒後に無条件で出しており、いちばん目的意識の高い時間を塞いでいた。
  // 中身を見に行った（＝目当てのものに辿り着いた）ころに出す。
  var shown = false;
  function show(){
    if (shown) return;
    // 絞り込みシートを開いている間は被せない（開いたら少し待って出直す）
    if (document.body.classList.contains('sheet-open')) { setTimeout(show, 2500); return; }
    shown = true;
    el.classList.add('show');
    removeEventListener('scroll', onScroll);
  }
  function onScroll(){
    if (scrollY > innerHeight * 0.4) show();
  }
  addEventListener('scroll', onScroll, {passive:true});
  // まったくスクロールしない人にも最後には出す
  setTimeout(show, 10000);
  document.getElementById('promoClose').addEventListener('click', function(e){ e.preventDefault(); close(); });
  el.addEventListener('click', function(e){ if (e.target === el) close(); });
})();
"""


def _video_creatives(episodes, limit=6):
    """最近の動画を、サムネイル付きでプロモに混ぜる。

    従来は5種類すべてが丸アイコン2種の使い回しで、どれが出ても同じ広告に見えていた。
    動画はサムネイルがそのまま素材になり、回ごとに絵が違うので変化が出る。
    """
    out = []
    for e in episodes:
        if e["upcoming"] or not e["thumb"] or not e["watch"]:
            continue
        t = e["title"]
        out.append({
            "icon": "",
            "img": e["thumb"],
            "tag": "最新の動画",
            "title": t[:44] + ("…" if len(t) > 44 else ""),
            "text": "",
            "cta": "動画を見る",
            "url": e["watch"],
        })
        if len(out) >= limit:
            break
    return out


def _promo_creatives(kawaru_icon, n1inc_icon):
    return [
        {
            "icon": kawaru_icon,
            "img": "https://lp.kawaru-ai.jp/wp-content/uploads/2026/05/Frame-2611706-scaled.png",
            "tag": "AIエージェント",
            "title": "Kawaru",
            "text": "「これ自動化して」と話すだけで、業務フローが自動で完成。",
            "cta": "無料で試す",
            "url": "https://lp.kawaru-ai.jp/",
        },
        {
            "icon": kawaru_icon,
            "img": "https://kawarucoach-lp.kawaru-ai.jp/wp-content/uploads/2026/08/Frame-1000001051.png",
            "tag": "伴走型AI顧問サービス",
            "title": "Kawaru Coach",
            "text": "AIのプロが専属で伴走。月5万円から、組織のAI活用が進む。",
            "cta": "詳しく見る",
            "url": "https://kawarucoach-lp.kawaru-ai.jp/",
        },
        {
            "icon": n1inc_icon,
            "accent": "#1C3461",
            "tag": "AI社員構築代行",
            "title": "エヌイチ",
            "text": "あなたの代わりに働く「AI社員」を、無料相談から構築。",
            "cta": "無料相談を見る",
            "url": "https://n1-inc.co.jp/lp-ai-staff-build-offer-with-image/",
        },
        {
            "icon": n1inc_icon,
            "accent": "#276C82",
            "tag": "法人研修",
            "title": "Claude Code / Codex研修",
            "text": "指示するだけで仕事が進む組織へ。現場定着まで伴走します。",
            "cta": "研修内容を見る",
            "url": "https://n1-inc.co.jp/lp-claude-codex-training-offer-with-image/",
        },
        {
            "icon": n1inc_icon,
            "accent": "#3F4A5A",
            "tag": "運営会社",
            "title": "株式会社エヌイチ",
            "text": "AI・ChatGPTを活用した社内DXと人材育成のプロ集団です。",
            "cta": "会社サイトを見る",
            "url": "https://n1-inc.co.jp/",
        },
    ]


def promo_block(kawaru_icon, n1inc_icon, episodes=None):
    creatives = _promo_creatives(kawaru_icon, n1inc_icon) + _video_creatives(episodes or [])
    creatives_json = json.dumps(creatives, ensure_ascii=False)
    return f"""<div id="promo" class="promo">
  <div class="promo-card">
    <button id="promoClose" class="promo-x" aria-label="閉じる">×</button>
    <img class="promo-banner" id="promoBanner" src="" alt="">
    <img class="promo-icon" id="promoIcon" src="" alt="">
    <p class="promo-tag" id="promoTag"></p>
    <p class="promo-title" id="promoTitle"></p>
    <p class="promo-text" id="promoText"></p>
    <a id="promoLink" class="promo-cta" href="#" target="_blank" rel="noopener sponsored">
      <span id="promoCta"></span><span class="promo-arrow">→</span>
    </a>
  </div>
</div>
<script>window.PROMO_CREATIVES = {creatives_json};</script>
<script>{PROMO_JS}</script>"""


# ============================ おすすめ診断 ============================
# 194件から「どれを選べばいいか分からない人」を数問で絞り込む。
# 個別の対応表は持たず、キット名・説明・動画タイトルへの当たりで採点する。
# こうしておくと、毎日増える回にもルールが自動で追従する。
# 語句を足したいときはここだけ直せばよい。
#
# 実測（2026-08-27・194件）: ツール軸はどれにも当たらないものが7件だけ。
# ただし Claude Code 113件・Codex 100件と重なりが大きいので、
# 「該当/非該当」で切らずにスコア順で出している。

FINDER = [
    {
        "id": "tool",
        "q": "何を使っていますか？",
        "opts": [
            {"l": "Claude Code",   "re": r"claude ?code|claude\.md"},
            {"l": "Codex / GPT",   "re": r"codex|gpt|openai"},
            {"l": "Gemini",        "re": r"gemini"},
            {"l": "Grok",          "re": r"grok"},
            {"l": "MCP・スキル",    "re": r"mcp|skill|スキル|hooks|フック"},
            {"l": "まだ決めていない", "re": ""},
        ],
    },
    {
        "id": "need",
        "q": "いま困っているのは？",
        "opts": [
            {"l": "料金を抑えたい",     "re": r"コスト|料金|節約|安く|無料|削減|価格"},
            {"l": "始め方が分からない", "re": r"入門|はじめ|始め|導入|初心者|セットアップ|最初"},
            {"l": "安全に使いたい",     "re": r"セキュリ|安全|権限|リスク|事故|防止"},
            {"l": "作業を速くしたい",   "re": r"効率|時短|高速|自動|一括|爆速"},
            {"l": "チームに広げたい",   "re": r"チーム|組織|社内|研修|共有|運用"},
        ],
    },
    {
        "id": "form",
        "q": "欲しい形（任意）",
        "opts": [
            {"l": "そのまま使える指示文", "t": "プロンプト集"},
            {"l": "抜け漏れを防ぎたい",   "t": "チェックリスト"},
            {"l": "書き換えて使う型",     "t": "テンプレート"},
            {"l": "設定をコピーしたい",   "t": "設定・スニペット"},
            {"l": "選び方を知りたい",     "t": "判断シート"},
            {"l": "困りごとから引きたい", "t": "早見表・逆引き"},
        ],
    },
]


def _finder_block():
    """統計バーの下に置く、細い1行の入口。

    主な来訪者は動画の概要欄から「その回のプレゼント」を取りに来た人なので、
    診断を大きく出すとその導線の邪魔になる。既定は閉じた状態にして、
    必要な人だけが開く形にしてある。
    """
    qs = []
    for grp in FINDER:
        opts = "".join(
            f'<button type="button" class="fopt" data-g="{grp["id"]}" '
            f'data-v="{E(o.get("re", o.get("t", "")))}">{E(o["l"])}</button>'
            for o in grp["opts"])
        qs.append(f'<div class="fq"><h4>{E(grp["q"])}</h4><div class="fopts">{opts}</div></div>')
    return f"""<details class="finder">
    <summary>どれを選べばいいか分からない方へ<span class="fhint">2つの質問でおすすめを出します</span></summary>
    <div class="finder-body">
      {"".join(qs)}
      <div class="fresult" id="fresult"></div>
    </div>
  </details>
"""


# ============================ ハブ（動画ごとのプレゼント一覧） ============================

HUB_JS = r"""
const EPS = window.EPISODES || [];
const $ = s => document.querySelector(s);
const out = $('#out'), cnt = $('#shown');
let f = {q:'', type:'', sort:'new'};

// 貼り付いているヘッダ＋ツールバー＋月ナビの実寸。月ジャンプの着地位置に使う。
// 広い画面では #mstick は display:contents で高さ0なので、月ナビ単体の高さを見る。
function stickOffset(){
  const h = document.querySelector('header');
  const hb = h ? h.getBoundingClientRect().height : 0;
  const ms = document.getElementById('mstick');
  const msb = ms ? ms.getBoundingClientRect().height : 0;
  const mb = document.getElementById('monthbar');
  const mbb = (mb && !mb.hidden) ? mb.getBoundingClientRect().height : 0;
  return Math.round(hb + Math.max(msb, mbb) + 6);
}

function norm(s){ return (s||'').toLowerCase().replace(/[ぁ-ん]/g, c => String.fromCharCode(c.charCodeAt(0)+0x60)); }

// 前回来たときより後に増えた回に NEW を出す。毎日増えるので、常連が新着を見分けられるように。
// 同じ日に何度見てもバッジが消えないよう、基準（prev）は日付が変わったときだけ進める。
const SINCE = (() => {
  const KEY = 'giftVisit';
  const d = new Date();
  const today = d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0')
              + '-' + String(d.getDate()).padStart(2,'0');
  let st = {prev:null, cur:null};
  try { st = JSON.parse(localStorage.getItem(KEY)) || st; } catch(e){}
  if (st.cur !== today){
    st.prev = st.cur;
    st.cur = today;
    try { localStorage.setItem(KEY, JSON.stringify(st)); } catch(e){}
  }
  return st.prev;   // 初回訪問（null）のときは何にも NEW を付けない
})();

function isNew(date){ return !!(SINCE && date && date > SINCE); }

function fmtDate(d){
  if (!d) return '';
  const m = d.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  return m ? `${m[1]}年${+m[2]}月${+m[3]}日` : d;
}

const esc = s => (s||'').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

// 検索語に当たった項目の番号（カードの採番と同じ。無ければ -1）
function itemHit(g, q){
  if (!q || !g.i) return -1;
  for (let i = 0; i < g.i.length; i++) if (norm(g.i[i]).includes(q)) return i;
  return -1;
}

function kitChip(g, q){
  const badge = g.c ? `<span class="badge">${g.c}${g.u}</span>`
               : (g.t === 'アプリ' ? `<span class="badge">アプリ</span>` : '');
  // 中の項目が当たったときは、その項目へ直接飛ばす（開いてから探し直さなくて済む）
  const hi = itemHit(g, q);
  const href = hi >= 0 ? `apps/${g.s}/#i${hi + 1}` : `apps/${g.s}/`;
  const hit = hi >= 0 ? `<span class="khit-in">この中の「${esc(g.i[hi])}」へ</span>` : '';
  return `<a class="kchip" href="${href}" target="_blank" rel="noopener">
    <span class="ic">${window.ICONS[g.t]||''}</span>
    <span class="kt">${g.nh}${hit}</span>${badge}<span class="go">開く →</span>
  </a>`;
}

// 動画ごとの解説資料（README＝教科書 / スライド / 1枚資料）へのボタン。
// 「▶ 動画を見る」の直下に並べる。リンクが無い回（未pushなど）は何も出さない。
const DOC_BTNS = [['repo','📚 資料'], ['slides','🖥 スライド'], ['onepager','📄 1枚資料']];
function docBtns(e){
  const d = e.docs || {};
  const b = DOC_BTNS.filter(([k]) => d[k]).map(([k, lbl]) =>
    `<a class="docbtn" href="${esc(d[k])}" target="_blank" rel="noopener">${lbl}</a>`).join('');
  return b ? `<div class="ep-docs">${b}</div>` : '';
}

function epCard(e, kitsToShow, q){
  const thumb = e.thumb
    ? `<img src="${e.thumb}" alt="" loading="lazy">`
    : `<div class="noimg">${window.ICONS['_play']||''}</div>`;
  const upBadge = e.upcoming ? '<span class="upbadge">近日公開</span>' : '';
  const watchLink = (e.watch && !e.upcoming)
    ? `<a class="watch" href="${e.watch}" target="_blank" rel="noopener">▶ 動画を見る</a>` : '';
  const bundle = e.kits.length >= 2
    ? `<a class="epbundle" href="bundles/${esc(e.slug)}.md" download="プレゼント一式_${esc(e.date||'')}.md">⬇ この回のプレゼントを全部ダウンロード</a>` : '';
  return `<article class="ep">
    <div class="ep-left">
      <div class="ep-thumb">${thumb}${upBadge}</div>
      ${watchLink}
      ${docBtns(e)}
    </div>
    <div class="ep-body">
      <div class="ep-date">${fmtDate(e.date) || '日付未定'}${isNew(e.date) ? '<span class="newbadge">NEW</span>' : ''}</div>
      <h2 class="ep-title">${e.th}</h2>
      <div class="ep-kits">${kitsToShow.map(g=>kitChip(g, q)).join('')}</div>
      ${bundle}
    </div>
  </article>`;
}

function matchKit(g){
  if (f.type && g.t !== f.type) return false;
  return true;
}

// 月ナビ（‹ 2026年8月 ›）。日付順のとき一覧の上に貼り付き、いま見ている月を出す。
// ‹＝古い月へ / ›＝新しい月へ スクロールする（Googleカレンダーの月切り替えのイメージ）。
const monthBar = document.getElementById('monthbar');
const monthLabel = document.getElementById('monthLabel');
const mbPrev = document.getElementById('mbPrev');
const mbNext = document.getElementById('mbNext');
const fmtMonth = m => `${m.slice(0,4)}年${+m.slice(5,7)}月`;
const monthMarks = () => [...out.querySelectorAll('.ep[data-month]')].map(el => el.dataset.month);

function jumpMonth(m){
  const el = document.getElementById('m-' + m);
  if (!el) return;
  // scrollIntoView + scroll-margin ではなく絶対位置へ。貼り付いたヘッダ＋月ナビのぶんを引く
  const y = el.getBoundingClientRect().top + window.pageYOffset - stickOffset();
  window.scrollTo({top: Math.max(0, y), behavior: 'instant'});
}

// 画面のいちばん上に来ている月（貼り付いたバーの下に潜った最後の目印）。
function currentMonth(){
  const marks = [...out.querySelectorAll('.ep[data-month]')];
  if (!marks.length) return null;
  const off = stickOffset() + 4;
  let cm = marks[0].dataset.month;
  for (const el of marks){
    if (el.getBoundingClientRect().top - off <= 1) cm = el.dataset.month;
    else break;
  }
  return cm;
}

let mbCur = null;   // いまバーに出している月（スクロール毎の無駄な更新を省く）

function setMonthBar(cm){
  mbCur = cm;
  const marks = monthMarks();
  const i = marks.indexOf(cm);
  monthLabel.textContent = fmtMonth(cm);
  // marks はリストの並び順（new＝新しい月が先、old＝古い月が先）。表示順に依らず ‹＝古い月 に固定
  const older = f.sort === 'old' ? marks[i - 1] : marks[i + 1];
  const newer = f.sort === 'old' ? marks[i + 1] : marks[i - 1];
  mbPrev.disabled = !older;
  mbNext.disabled = !newer;
  // クリックでは飛んだ先の月にバーを即あわせる（スクロールイベント待ちにしない）
  mbPrev.onclick = older ? () => { jumpMonth(older); setMonthBar(older); } : null;
  mbNext.onclick = newer ? () => { jumpMonth(newer); setMonthBar(newer); } : null;
}

function updateMonthBar(){
  if (!monthBar) return;
  const marks = monthMarks();
  monthBar.hidden = (f.sort === 'name' || !marks.length);
  mbCur = null;
  if (!monthBar.hidden) setMonthBar(currentMonth() || marks[0]);
}

addEventListener('scroll', () => {
  if (!monthBar || monthBar.hidden) return;
  const cm = currentMonth();
  if (cm && cm !== mbCur) setMonthBar(cm);
}, {passive: true});

function render(){
  const q = norm(f.q);
  let list = EPS.map(e => {
    const kits = e.kits.filter(matchKit);
    return {e, kits};
  }).filter(x => x.kits.length);

  if (q){
    list = list.map(({e, kits}) => {
      const epHit = norm(e.title).includes(q);
      const kitHits = kits.filter(g => norm(g.q).includes(q) || itemHit(g, q) >= 0);
      return {e, kits: epHit ? kits : kitHits, hit: epHit || kitHits.length > 0};
    }).filter(x => x.hit);
  }

  list.sort((a,b) => {
    if (f.sort === 'old')  return (a.e.date||'0').localeCompare(b.e.date||'0') || (a.e.no||0)-(b.e.no||0);
    if (f.sort === 'name') return a.e.title.localeCompare(b.e.title, 'ja');
    return (b.e.date||'0').localeCompare(a.e.date||'0') || (b.e.no||0)-(a.e.no||0);
  });

  cnt.textContent = list.length;
  // 絞り込んでいるときだけ出す（未絞り込みでは「配布回」と同じ数字が並ぶだけになる）
  $('#shownBox').classList.toggle('hidden', !(f.q || f.type));
  $('.stats').classList.toggle('filtered', !!(f.q || f.type));
  updateFilterBadge();
  if (!list.length){
    out.innerHTML = `<div class="empty">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="10" cy="10" r="6.2"/><path d="M15 15l5.5 5.5"/><path d="M7.3 10h5.4"/></svg>
      <p>条件に合うプレゼントが見つかりませんでした。<br>キーワードを短くするか、種別を「すべて」に戻してみてください。</p>
    </div>`;
    updateMonthBar();
    return;
  }
  // 日付順のときは、各月の先頭カードに #m-YYYY-MM の目印を付ける（月ナビの飛び先）
  const grouped = f.sort !== 'name';
  let cur = null, html = '';
  for (const {e, kits} of list){
    let card = epCard(e, kits, q);
    if (grouped && e.date){
      const m = e.date.slice(0, 7);
      if (m !== cur){
        cur = m;
        card = card.replace('<article class="ep"', `<article class="ep" id="m-${m}" data-month="${m}"`);
      }
    }
    html += card;
  }
  out.innerHTML = `<div class="eplist">${html}</div>`;
  updateMonthBar();
}

// しぼり込みの状態をURLに残す。
// 共有・ブックマーク・戻るボタンが効くようになり、
// 動画の概要欄から「プロンプト集だけ」のような形で直接リンクできる。
function readURL(){
  const p = new URLSearchParams(location.search);
  f.q = p.get('q') || '';
  f.type = p.get('type') || '';
  f.sort = p.get('sort') || 'new';
  $('#q').value = f.q;
  { const q2 = $('#q2'); if (q2) q2.value = f.q; }
  $('#sort').value = f.sort;
  const r = document.querySelector(`input[name=type][value="${CSS.escape(f.type)}"]`);
  if (r) r.checked = true; else f.type = '';
}

function writeURL(push){
  const p = new URLSearchParams();
  if (f.q) p.set('q', f.q);
  if (f.type) p.set('type', f.type);
  if (f.sort !== 'new') p.set('sort', f.sort);
  const s = p.toString();
  const url = s ? location.pathname + '?' + s : location.pathname;
  // 入力のたびに履歴を積むと戻るボタンが使い物にならないので、検索欄だけ置き換えにする
  history[push ? 'pushState' : 'replaceState'](null, '', url);
}

// 検索欄はスマホ用（ツールバー内 #q2）とサイド用（#q）の2つ。値は常に同期させる。
function setQ(v){
  f.q = v.trim();
  const a = $('#q'), b = $('#q2');
  if (a && a.value !== v) a.value = v;
  if (b && b.value !== v) b.value = v;
}
$('#q').addEventListener('input', e => { setQ(e.target.value); writeURL(false); render(); });
{ const q2 = $('#q2');
  if (q2) q2.addEventListener('input', e => { setQ(e.target.value); writeURL(false); render(); }); }
$('#sort').addEventListener('change', e => { f.sort = e.target.value; writeURL(true); render(); });
document.querySelectorAll('input[name=type]').forEach(r =>
  r.addEventListener('change', e => { f.type = e.target.value; writeURL(true); render(); }));
$('#reset').addEventListener('click', () => {
  f = {q:'', type:'', sort:'new'};
  setQ(''); $('#sort').value='new';
  document.querySelector('input[name=type][value=""]').checked = true;
  writeURL(true); render();
});
addEventListener('popstate', () => { readURL(); render(); });

// 絞り込みシート（スマホ）。ツールバーの「絞り込み」で開閉。
// 開いている間はダイアログとして扱う: 役割付与・フォーカス移動と閉じ込め・背面スクロール固定。
const filterBtn = $('#filterBtn'), sheetBackdrop = $('#sheetBackdrop'), sheetEl = $('#side');
let sheetReturnFocus = null, sheetSavedY = 0;
const sheetOpen = () => document.body.classList.contains('sheet-open');

function sheetFocusables(){
  return [...sheetEl.querySelectorAll('a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])')]
    .filter(el => el.offsetWidth || el.offsetHeight || el.getClientRects().length);
}
function trapTab(e){
  if (e.key !== 'Tab' || !sheetOpen()) return;
  const list = sheetFocusables();
  if (!list.length) return;
  const first = list[0], last = list[list.length - 1];
  if (e.shiftKey && (document.activeElement === first || !sheetEl.contains(document.activeElement))){
    e.preventDefault(); last.focus();
  } else if (!e.shiftKey && document.activeElement === last){
    e.preventDefault(); first.focus();
  }
}
function openSheet(){
  if (sheetOpen() || !sheetEl) return;
  sheetReturnFocus = (document.activeElement && document.activeElement !== document.body)
    ? document.activeElement : filterBtn;
  sheetSavedY = window.scrollY || window.pageYOffset || 0;
  document.body.style.top = (-sheetSavedY) + 'px';
  document.body.classList.add('sheet-open');
  filterBtn && filterBtn.setAttribute('aria-expanded', 'true');
  sheetEl.setAttribute('role', 'dialog');
  sheetEl.setAttribute('aria-modal', 'true');
  const close = $('#sheetClose');
  if (close) close.focus();
  addEventListener('keydown', trapTab, true);
}
function closeSheet(){
  if (!sheetOpen()) return;
  document.body.classList.remove('sheet-open');
  document.body.style.top = '';
  window.scrollTo(0, sheetSavedY);
  filterBtn && filterBtn.setAttribute('aria-expanded', 'false');
  sheetEl.removeAttribute('role');
  sheetEl.removeAttribute('aria-modal');
  removeEventListener('keydown', trapTab, true);
  if (sheetReturnFocus && sheetReturnFocus.focus) sheetReturnFocus.focus();
}
filterBtn && filterBtn.addEventListener('click', () => sheetOpen() ? closeSheet() : openSheet());
sheetBackdrop && sheetBackdrop.addEventListener('click', closeSheet);
$('#sheetClose') && $('#sheetClose').addEventListener('click', closeSheet);
$('#sheetApply') && $('#sheetApply').addEventListener('click', closeSheet);
addEventListener('keydown', e => { if (e.key === 'Escape' && sheetOpen()) closeSheet(); });

// ツールバーの「絞り込み」に、効いている条件の数を出す（種別・並び順）。
function updateFilterBadge(){
  const n = (f.type ? 1 : 0) + (f.sort !== 'new' ? 1 : 0);
  const b = $('#fbadge');
  if (b){ b.textContent = String(n); b.hidden = n === 0; }
  filterBtn && filterBtn.classList.toggle('on', n > 0);
}

// 貼り付くツールバーの top に使うヘッダ実寸を CSS 変数へ。
// 幅0など異常な描画時の巨大値が残らないよう上限を設ける。
function setHdr(){
  const h = document.querySelector('header');
  if (!h || !window.innerWidth) return;
  document.documentElement.style.setProperty('--hdr', Math.min(h.offsetHeight, 160) + 'px');
}
setHdr();
addEventListener('resize', setHdr);

readURL();
render();

// おすすめ診断。数問の答えを点数にして上位を出す。
// 「該当/非該当」で切らないのは、Claude CodeとCodexのように語が重なるキットが多く、
// 絞り込みだとほとんど減らないため（2026-08-27に実データで確認）。
(function(){
  var box = document.getElementById('fresult');
  if (!box) return;
  var pick = {tool:'', need:'', form:''};
  var newest = EPS.reduce(function(a, e){ return (e.date || '') > a ? e.date : a; }, '');

  // AIの情報は古くなるのが速いので、新しい回を優遇する
  function freshness(date){
    if (!date || !newest) return 0;
    var d = (new Date(newest) - new Date(date)) / 86400000;
    return d <= 14 ? 2 : (d <= 60 ? 1 : 0);
  }

  function run(){
    if (!pick.tool && !pick.need && !pick.form){ box.innerHTML = ''; return; }
    // ツールと目的は語の重なりが大きいので点数にする。
    // 「形」は種別そのもので迷いようがないため、点数ではなく絞り込みにする
    // （チェックリストを選んだ人にプロンプト集を出さない）。
    function collect(useForm){
      var rows = [];
      EPS.forEach(function(e){
        e.kits.forEach(function(g){
          if (useForm && pick.form && g.t !== pick.form) return;
          var hay = (g.n + ' ' + (g.q || '') + ' ' + e.title).toLowerCase();
          var s = 0;
          if (pick.tool && new RegExp(pick.tool, 'i').test(hay)) s += 3;
          if (pick.need && new RegExp(pick.need, 'i').test(hay)) s += 3;
          if (!s && !(useForm && pick.form)) return;
          rows.push({e:e, g:g, s: s + freshness(e.date)});
        });
      });
      rows.sort(function(a,b){ return b.s - a.s || (b.e.date||'').localeCompare(a.e.date||''); });
      return rows;
    }
    var rows = collect(true);
    var loosened = false;
    // 形で絞ると0件になることがある（判断シートは全体で4件しかない等）。
    // 行き止まりにせず、形を外して出し直したことを伝える。
    if (!rows.length && pick.form){ rows = collect(false); loosened = rows.length > 0; }

    if (!rows.length){
      box.innerHTML = '<p class="fnone">条件に合うものが見つかりませんでした。'
        + '「まだ決めていない」を選ぶか、下の一覧から探してみてください。</p>';
      return;
    }
    box.innerHTML = '<p class="flabel">この' + Math.min(rows.length, 5) + '件がおすすめです'
      + (loosened ? '<span class="fhint">（その形では見つからなかったので、形の指定を外しました）</span>' : '')
      + '</p>'
      + '<div class="ep-kits">'
      + rows.slice(0, 5).map(function(r){
          var badge = r.g.c ? '<span class="badge">' + r.g.c + r.g.u + '</span>' : '';
          return '<a class="kchip" href="apps/' + r.g.s + '/" target="_blank" rel="noopener">'
            + '<span class="ic">' + (window.ICONS[r.g.t] || '') + '</span>'
            + '<span class="kt">' + r.g.nh
            + '<span class="khit-in">' + fmtDate(r.e.date) + 'の回</span></span>'
            + badge + '<span class="go">開く →</span></a>';
        }).join('')
      + '</div>';
  }

  document.querySelectorAll('.fopt').forEach(function(b){
    b.addEventListener('click', function(){
      var g = b.dataset.g;
      var same = pick[g] === b.dataset.v && b.classList.contains('on');
      document.querySelectorAll('.fopt[data-g="' + g + '"]').forEach(function(x){ x.classList.remove('on'); });
      if (same) { pick[g] = ''; } else { pick[g] = b.dataset.v; b.classList.add('on'); }
      run();
    });
  });
})();

// 「/」ですぐ検索を始められるようにする。入力中は邪魔しない。
addEventListener('keydown', e => {
  if (e.key !== '/' || e.metaKey || e.ctrlKey || e.altKey) return;
  const t = e.target;
  if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
  const box = document.getElementById('q') || document.getElementById('kq');
  if (!box) return;
  e.preventDefault();
  box.focus();
  box.select();
});
"""


def hub(theme, icon, episodes, type_stats, type_icons, type_desc, promo_icon, n1inc_icon, preview=False, data_ver="", css_ver="", promo_eps=None):
    ch = theme["channel_name"]
    kits_flat = [k for e in episodes for k in e["kits"]]
    n_kit = len(kits_flat)
    n_item = sum(k["count"] or 0 for k in kits_flat if k["unit"] == "個")
    n_ep = len(episodes)
    n_type = len(type_stats)

    radios = ['<label><input type="radio" name="type" value="" checked>'
              f'すべて<span class="n">{n_kit}</span></label>']
    for t, n in type_stats:
        radios.append(f'<label><input type="radio" name="type" value="{E(t)}">'
                      f'{E(t)}<span class="n">{n}</span></label>')

    preview_banner = ("""<div style="background:#B0281C;color:#fff;text-align:center;
      padding:9px 14px;font-weight:800;font-size:12.5px;">
      🔒 これは管理者用プレビューです（未公開の回を含む・一般公開されていません）
    </div>
""" if preview else "")

    # 共有カードの絵には最新回のサムネイルを使う（絶対URLが必要なため、アイコンのdata URIは使えない）
    share = next((e["thumb"] for e in episodes if e.get("thumb")), "")
    body = f"""{_head(f"{theme['site_name']} — {ch} プレゼント図書館", theme, icon, "assets/site.css",
                      f"{ch}でこれまで配布したプレゼント{n_kit}点を、動画ごとに検索できる図書館です。",
                      noindex=preview, share_img=share, css_ver=css_ver)}
{preview_banner}<header><div class="top">
  <img src="{icon}" alt="">
  <div class="ttl">{E(theme['site_name'])}<small>{E(ch)} {E(theme['tagline'])}</small></div>
</div></header>

<div class="wrap">
  <section class="hero">
    <p class="eyebrow">PRESENT LIBRARY</p>
    <h1>{E(ch)}の<br>プレゼント図書館</h1>
    <p>{NB("これまでの動画でお配りしてきたプレゼントを、動画ごとに1か所へまとめました。キーワード検索と種別のしぼり込みで、いま必要なものだけを探せます。どのページも、項目ごとのコピーと、全件のダウンロードに対応しています。")}</p>
  </section>

  <div class="stats">
    <div><b>{n_ep}</b><span>配布回</span></div>
    <div><b>{n_kit}</b><span>プレゼント</span></div>
    <div><b>{n_item:,}</b><span>収録アイテム</span></div>
    <div><b>{n_type}</b><span>種別</span></div>
    <div id="shownBox" class="hidden"><b id="shown">{n_ep}</b><span>表示中</span></div>
  </div>

  <div class="mstick" id="mstick">
    <div class="mtoolbar">
      <label class="mtb-search">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.6-3.6"/></svg>
        <input id="q2" type="search" placeholder="プレゼントを検索" autocomplete="off" aria-label="キーワード検索">
      </label>
      <button type="button" class="mtb-filter" id="filterBtn" aria-expanded="false" aria-controls="side">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6h16M7 12h10M10 18h4"/></svg>
        <span>絞り込み</span><span class="fbadge" id="fbadge" hidden>0</span>
      </button>
    </div>
    <div class="monthbar" id="monthbar" hidden>
      <button class="mb-arrow" id="mbPrev" type="button" aria-label="前の月へ">❮</button>
      <span class="mb-label" id="monthLabel"></span>
      <button class="mb-arrow" id="mbNext" type="button" aria-label="次の月へ">❯</button>
    </div>
  </div>
  <div class="cols">
    <aside class="side" id="side" aria-labelledby="sheetTitle">
      <div class="sheet-head">
        <span class="sheet-title" id="sheetTitle">検索・絞り込み</span>
        <button type="button" class="sheet-close" id="sheetClose" aria-label="閉じる">×</button>
      </div>
      <div class="grp"><h3>キーワード検索</h3>
        <input id="q" type="search" placeholder="例: 動画タイトル、プロンプト、設定" autocomplete="off"></div>
      <div class="grp type-grp"><h3>種別でしぼる</h3>
        <div class="grp-body">{''.join(radios)}</div></div>
      <div class="grp"><h3>並び順</h3>
        <div class="selwrap"><select id="sort">
          <option value="new">投稿が新しい順</option>
          <option value="old">投稿が古い順</option>
          <option value="name">動画タイトル順</option>
        </select></div>
        <button class="reset" id="reset">条件をリセット</button></div>
      {_finder_block()}
      <button type="button" class="sheet-apply" id="sheetApply">この条件で見る</button>
    </aside>
    <main id="out"></main>
  </div>
  <div class="sheet-backdrop" id="sheetBackdrop"></div>

  <footer>{E(ch)} — プレゼント図書館</footer>
</div>

<script src="data.js?v={data_ver}"></script>
<script>
window.ICONS = {json.dumps(type_icons, ensure_ascii=False)};
</script>
<script>{HUB_JS}</script>
{promo_block(promo_icon, n1inc_icon, promo_eps)}
{A.block(preview)}</body></html>"""
    return body


def _kit_row(k):
    """ハブの検索に使うデータを組み立てる。

    項目名は1本の連結文字列ではなく配列で持つ。連結だと「どの項目が一致したか」が
    分からず、検索で見つけたキットを開いてもう一度その中を探す必要があった。
    配列にすると一致した項目を名指しでき、その項目へ直接リンクできる。
    対象は items ではなく cards（実際に表示・採番される単位）。CC 124キット中80キットは
    items が空で、それらの項目名はこれまで検索に一切かからなかった。
    実測（CC・gzip後）: 索引される項目 1,789 → 2,875、data.js は 43KB → 67KB。
    """
    cards = k["cards"]
    cats, seen = [], set()
    for c in cards:
        if c["cat"] and c["cat"] not in seen:
            seen.add(c["cat"])
            cats.append(c["cat"])
    return {
        "s": k["slug"], "n": k["name"],
        "nh": E(k["name"]),
        "t": k["type"],
        "c": k["count"], "u": k["unit"],
        "q": re.sub(r"\s+", " ", " ".join([k["name"], k["desc"], k["type"]] + cats)),
        "i": [c["title"] for c in cards],
    }


def data_js(episodes):
    rows = []
    for e in episodes:
        rows.append({
            "title": e["title"],
            "th": NB(e["title"], max_len=16, hard_max=24),
            "date": e["date"],
            "no": e["no"],
            "slug": episode_anchor(e),
            "thumb": e["thumb"],
            "watch": e["watch"],
            "upcoming": e["upcoming"],
            "docs": e.get("links") or {},
            "kits": [_kit_row(k) for k in e["kits"]],
        })
    return "window.EPISODES = " + json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + ";\n"


# 動画ごとの解説資料（README＝教科書 / スライド / 1枚資料）へのボタン。
# 「▶ 動画を見る」の直下に並べる。まだ push されていない回はリンクが無く、何も出さない。
DOC_BTNS = [("repo", "📚 資料"), ("slides", "🖥 スライド"), ("onepager", "📄 1枚資料")]


def _doc_btns(links):
    if not links:
        return ""
    btns = "".join(
        f'<a class="docbtn" href="{E(links[k])}" target="_blank" rel="noopener">{lbl}</a>'
        for k, lbl in DOC_BTNS if links.get(k))
    return f'<div class="ep-docs">{btns}</div>' if btns else ""


def episode_anchor(episode):
    """回ごとの安定した識別子。「この回を全部ダウンロード」の bundles/<anchor>.md の
    ファイル名に使う。動画IDが最優先（不変）。無ければ日付。"""
    return (episode.get("vid")
            or ("d" + (episode.get("date") or "").replace("-", ""))
            or "ep")


def _episode_bundle_btn(episode, rel=""):
    """その回のプレゼントを1ファイルにまとめた .md へのダウンロードボタン。2点以上のときだけ。"""
    if len(episode.get("kits") or []) < 2:
        return ""
    fname = f"プレゼント一式_{episode.get('date') or ''}.md"
    return (f'<a class="epbundle" href="{rel}bundles/{episode_anchor(episode)}.md" '
            f'download="{E(fname)}">⬇ この回のプレゼントを全部ダウンロード</a>')


# ============================ 受け取りページ ============================

KIT_JS = r"""

// チェックリストを実際に使えるようにする。
// □ の行を押すと済みになり、状態はこのブラウザに残る（ページを閉じても消えない）。
// <pre> の中身自体は変えていないので、コピーとダウンロードの内容は今までどおり。
(function(){
  var lines = [].slice.call(document.querySelectorAll('.cline'));
  if (!lines.length) return;
  var KEY = 'giftCheck:' + location.pathname;
  var done = {};
  try { done = JSON.parse(localStorage.getItem(KEY)) || {}; } catch(e){}

  function save(){
    try { localStorage.setItem(KEY, JSON.stringify(done)); } catch(e){}
  }
  function paint(){
    var n = 0;
    lines.forEach(function(l){
      var on = !!done[l.dataset.c];
      l.classList.toggle('on', on);
      if (on) n++;
    });
    bar.textContent = n ? n + ' / ' + lines.length + ' 完了' : lines.length + ' 項目 ・ タップでチェック';
    reset.style.display = n ? 'inline' : 'none';
  }

  var bar = document.createElement('span');
  var reset = document.createElement('button');
  reset.type = 'button';
  reset.className = 'creset';
  reset.textContent = 'チェックを消す';
  reset.addEventListener('click', function(){ done = {}; save(); paint(); });

  var wrap = document.createElement('div');
  wrap.className = 'cprog';
  wrap.appendChild(bar);
  wrap.appendChild(reset);
  var host = lines[0].closest('.icard') || lines[0].closest('pre');
  host.insertBefore(wrap, host.firstChild);

  lines.forEach(function(l){
    l.addEventListener('click', function(){
      var k = l.dataset.c;
      if (done[k]) delete done[k]; else done[k] = 1;
      save(); paint();
    });
  });
  paint();
})();

// 名指しリンク（#i37）で来たとき、その項目まで確実に運んで少しの間だけ目立たせる。
// ブラウザ任せだと、項目数の多いページでは狙った位置に着かないことがある
// （html に scroll-behavior:smooth が効いており、数万px を滑らせようとして届かない）。
(function(){
  function go(){
    if (!location.hash) return;
    var el = document.querySelector(location.hash);
    if (!el || !el.classList.contains('icard')) return;
    // behavior:'auto' は CSS の scroll-behavior:smooth に従うため、
    // 数万px 離れた項目へは滑らかに移動しようとして事実上たどり着かない。
    // 名指しリンクは「開いたらそこにいる」のが正しいので即時で飛ばす。
    el.scrollIntoView({block: 'start', behavior: 'instant'});
    el.classList.add('flashme');
    setTimeout(function(){ el.classList.remove('flashme'); }, 2400);
  }
  addEventListener('hashchange', go);
  if (document.readyState === 'loading') addEventListener('DOMContentLoaded', go);
  else go();
})();
// 項目の多いキットで、目的の1件に辿り着けるようにする絞り込み。
// 検索はタイトル・説明だけでなく本文も対象にする（「あの文言が入っていた項目」で探せるように）。
(function(){
  var q = document.getElementById('kq');
  if (!q) return;
  var hit = document.getElementById('khit');
  var cards = [].slice.call(document.querySelectorAll('.kwrap .icard'));
  var heads = [].slice.call(document.querySelectorAll('.kwrap h2.cat'));
  var chips = [].slice.call(document.querySelectorAll('.kcat'));
  var cat = '';

  // ひらがな・カタカナの違いで取りこぼさないようにする（ハブ側の検索と同じ扱い）
  function norm(s){
    return (s || '').toLowerCase().replace(/[ぁ-ん]/g, function(c){
      return String.fromCharCode(c.charCodeAt(0) + 0x60);
    });
  }

  // カード全体の textContent だとボタンの「コピー」まで拾ってしまうため、中身を選んで集める
  cards.forEach(function(c){
    var t = c.querySelector('.ititle'), d = c.querySelector('.imeta'), p = c.querySelector('.prompt');
    c._t = norm((t ? t.textContent : '') + ' ' + (d ? d.textContent : '') + ' ' + (p ? p.textContent : ''));
  });

  function apply(){
    var kw = norm(q.value.trim()), n = 0, shown = {};
    cards.forEach(function(c){
      var ok = (!cat || c.getAttribute('data-cat') === cat)
            && (!kw || c._t.indexOf(kw) !== -1);
      c.classList.toggle('hide', !ok);
      if (ok){ n++; shown[c.getAttribute('data-cat')] = 1; }
    });
    // 残った項目が1件も無いカテゴリの見出しは隠す
    heads.forEach(function(h){
      h.classList.toggle('hide', !shown[h.getAttribute('data-cat')]);
    });
    hit.textContent = (kw || cat)
      ? (n ? n + '件を表示中' : '該当する項目がありません')
      : '';
  }

  q.addEventListener('input', apply);
  chips.forEach(function(b){
    b.addEventListener('click', function(){
      cat = b.getAttribute('data-cat');
      chips.forEach(function(x){ x.classList.toggle('on', x === b); });
      apply();
    });
  });
})();

function flash(btn, label){
  const old = btn.textContent, cls = btn.className;
  btn.textContent = label; btn.classList.add('ok');
  setTimeout(() => { btn.textContent = old; btn.className = cls; }, 1600);
}
function textOf(id){ return document.getElementById(id).textContent; }

async function copyText(btn, id){
  const t = textOf(id);
  try {
    await navigator.clipboard.writeText(t);
  } catch (e) {
    const ta = document.createElement('textarea');
    ta.value = t; ta.style.position='fixed'; ta.style.opacity='0';
    document.body.appendChild(ta); ta.select();
    document.execCommand('copy'); ta.remove();
  }
  flash(btn, '✓ コピーしました');
}

function saveText(btn, id, name){
  const blob = new Blob([textOf(id)], {type:'text/plain;charset=utf-8'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  if (btn) flash(btn, '✓ 保存しました');
}

document.addEventListener('click', e => {
  const b = e.target.closest('[data-copy]');
  if (b) { copyText(b, b.dataset.copy); return; }
  const d = e.target.closest('[data-save]');
  if (d) { saveText(d, d.dataset.save, d.dataset.name); return; }
  // その項目だけを名指しで人に渡せるようにする
  const l = e.target.closest('[data-link]');
  if (l) {
    const url = location.origin + location.pathname + '#' + l.dataset.link;
    navigator.clipboard.writeText(url).then(() => flash(l, '✓ コピーしました'));
  }
});

// 「/」ですぐ検索を始められるようにする。入力中は邪魔しない。
addEventListener('keydown', e => {
  if (e.key !== '/' || e.metaKey || e.ctrlKey || e.altKey) return;
  const t = e.target;
  if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
  const box = document.getElementById('q') || document.getElementById('kq');
  if (!box) return;
  e.preventDefault();
  box.focus();
  box.select();
});

// 「この中から探す」の貼り付き位置を、実際のヘッダ高さに合わせる（スマホでヘッダが低い）。
(function(){
  var h = document.querySelector('header');
  if (!h) return;
  var set = function(){
    if (!window.innerWidth) return;
    document.documentElement.style.setProperty('--hdr', Math.min(h.offsetHeight, 160) + 'px');
  };
  set();
  addEventListener('resize', set);
})();
"""


def _checkable(escaped_body, prefix="b"):
    """本文中の「□ …」の行を、クリックできるようにspanで包む。

    チェックリストは□がただの文字で、押せなかった（CC17件・AA22件が該当）。
    包むだけなので <pre> の textContent は変わらず、コピーと全件ダウンロードの
    中身は今までどおり。見た目のチェック状態はブラウザ側に保存する。

    prefix はカードごとに変える。ページ内で通し番号にしないと、別のカードの
    同じ番号どうしが打ち消し合う（2026-08-27の実装時に踏んだ）。
    """
    if "□" not in escaped_body:
        return escaped_body
    out, n = [], 0
    for line in escaped_body.split("\n"):
        st = line.lstrip()
        if st.startswith("□"):
            indent = line[:len(line) - len(st)]
            out.append(f'{indent}<span class="cline" data-c="{prefix}-{n}">'
                       f'<span class="cbx">□</span>{st[1:]}</span>')
            n += 1
        else:
            out.append(line)
    return "\n".join(out) if n else escaped_body


def _item_card(idx, it, slug, cat=""):
    tid = f"b{idx}"
    fname = f"{slug}-{idx:03d}.txt"
    desc = f'<p class="imeta">{NB(it["desc"])}</p>' if it["desc"] else ""
    return f"""<div class="icard" id="i{idx}" data-cat="{E(cat)}">
  <div class="ih"><span class="num">{idx:03d}</span><span class="ititle">{E(it['title'])}</span></div>
  {desc}
  <pre class="prompt" id="{tid}">{_checkable(E(it["body"]), tid)}</pre>
  <div class="cbtns">
    <button class="btn sm" data-copy="{tid}">📋 コピー</button>
    <button class="btn ghost sm" data-save="{tid}" data-name="{fname}">⬇ ダウンロード</button>
    <button class="btn ghost sm" data-link="i{idx}">🔗 リンク</button>
  </div>
</div>"""


def _related_kits(kit, related, limit=4):
    """種別が同じ、別の回のプレゼントへの導線。

    キットページの下部にあるのは同じ回のものだけで、種別をまたいだ回遊は
    一覧に戻って絞り込み直すしかなかった。新しい回から数件だけ出す。
    """
    if not related:
        return ""
    chips = "".join(
        f'<a class="kchip" href="../{E(o["slug"])}/">'
        f'<span class="kt">{E(o["name"])}</span>'
        + (f'<span class="badge">{o["count"]}{o["unit"]}</span>' if o["count"] else "")
        + '<span class="go">開く →</span></a>'
        for o in related[:limit]
    )
    return f"""<section class="epctx">
  <p class="epctx-label">ほかの回の「{E(kit["type"])}」</p>
  <div class="ep-kits">{chips}</div>
</section>"""


def _sibling_kits(episode, current_slug):
    others = [k for k in episode["kits"] if k["slug"] != current_slug]
    if not others:
        return ""
    def _badge(o):
        if o["count"]:
            return f'<span class="badge">{o["count"]}{o["unit"]}</span>'
        if o.get("is_app"):
            return '<span class="badge">アプリ</span>'
        return ""

    chips = "".join(
        f'<a class="kchip" href="../{o["slug"]}/">'
        f'<span class="kt">{E(o["name"])}</span>'
        + _badge(o)
        + '<span class="go">開く →</span></a>'
        for o in others
    )
    return f"""<section class="epctx">
  <p class="epctx-label">この動画のほかのプレゼント</p>
  <div class="ep-kits">{chips}</div>
</section>"""


def _episode_header(episode):
    thumb = (f'<img src="{E(episode["thumb"])}" alt="">' if episode["thumb"]
             else f'<div class="noimg">{T.play_icon()}</div>')
    date_txt = episode["date"] or "日付未定"
    watch = (f'<a class="watch" href="{E(episode["watch"])}" target="_blank" rel="noopener">▶ 動画を見る</a>'
             if episode["watch"] and not episode["upcoming"] else "")
    up = '<span class="upbadge">近日公開</span>' if episode["upcoming"] else ""
    return f"""<section class="epctx epctx-top">
  <div class="ep-left">
    <div class="ep-thumb epctx-thumb">{thumb}{up}</div>
    {watch}
    {_doc_btns(episode.get("links"))}
  </div>
  <div>
    <p class="epctx-label">この動画のプレゼントです</p>
    <p class="epctx-title">{E(episode["title"])}</p>
    <p class="epctx-date">{E(date_txt)}</p>
    {_episode_bundle_btn(episode, "../../")}
  </div>
</section>"""


def _kit_tools(total, cats):
    """項目の多いキットに「この中から探す」を付ける。

    2026-08-27まで、100項目・22カテゴリのページにも検索も目次も無く、
    目的の1件に辿り着くには延々スクロールするしかなかった。
    項目が少ないキットではかえって邪魔になるので、ある程度の件数から出す。
    """
    if total < 12:
        return ""
    named = [(c, n) for c, n in cats.items() if c]
    chips = ""
    if len(named) >= 2:
        btns = [f'<button type="button" class="kcat on" data-cat="">'
                f'すべて<span class="n">{total}</span></button>']
        btns += [f'<button type="button" class="kcat" data-cat="{E(c)}">'
                 f'{E(c)}<span class="n">{n}</span></button>' for c, n in named]
        chips = f'<div class="kcats">{"".join(btns)}</div>'
    return f"""<div class="ktools">
  <input type="search" id="kq" placeholder="この中から探す" autocomplete="off" aria-label="この中から探す">
  {chips}
  <p class="khit" id="khit" role="status"></p>
</div>
"""


def kit_page(theme, icon, kit, raw_md, episode, promo_icon, n1inc_icon, preview=False, related=None, css_ver="", promo_eps=None):
    ep = kit["ep"]
    slug = kit["slug"]
    badge = f'<span class="badge">{kit["count"]}{kit["unit"]}</span>' if kit["count"] else ""
    ep_label = f"No.{ep['no']} {ep['topic']}" if ep["no"] else ep["topic"]

    if kit["cards"]:
        blocks, cur, n = [], None, 0
        cats = {}
        for it in kit["cards"]:
            cat = it["cat"] or ""
            cats[cat] = cats.get(cat, 0) + 1
            if it["cat"] != cur:
                cur = it["cat"]
                if cur:
                    blocks.append(f'<h2 class="cat" data-cat="{E(cur)}">{E(cur)}</h2>')
            n += 1
            blocks.append(_item_card(n, it, slug, cat))
        content = _kit_tools(len(kit["cards"]), cats) + "\n".join(blocks)
        if kit["intro"] and not kit["intro"].lstrip().startswith("#"):
            content = f'<p class="imeta" style="margin:0 0 18px">{NB(kit["intro"])}</p>' + content
        howto = ("下のカードから、1件ずつコピー、または個別にダウンロードできます。"
                 "まとめて欲しいときは、上の「全件ダウンロード」をお使いください。")
    else:
        content = f"""<div class="icard">
  <pre class="prompt" id="b1" style="max-height:none;">{_checkable(E(kit['whole']))}</pre>
  <div class="cbtns">
    <button class="btn" data-copy="b1">📋 コピー</button>
    <button class="btn ghost" data-save="b1" data-name="{slug}.txt">⬇ ダウンロード</button>
  </div>
</div>"""
        howto = "下のボタンで、全文をそのままコピー、またはテキストファイルとして保存できます。"

    meta = [f'<span>{E(kit["type"])}</span>', f'<span>{E(ep_label)}</span>',
            f'<span>{E(ep["date"])} 配布</span>']
    if kit["count"]:
        meta.insert(1, f'<span>収録 {kit["count"]}{kit["unit"]}</span>')

    return f"""{_head(f"{kit['name']} — {theme['site_name']}", theme, icon, "../../assets/site.css", kit['desc'], noindex=preview, share_img=episode.get("thumb", ""), css_ver=css_ver)}
<header class="kh"><div class="top">
  <a class="back" href="../../">← 一覧へ</a>
  <img src="{icon}" alt="">
  <h1>{E(kit['name'])}</h1>
  {badge}
  <button class="btn ghost sm" style="margin-left:auto" data-copy="pfull" aria-label="全件コピー">📋<span class="blabel"> 全件コピー</span></button>
  <button class="btn sm" data-save="pfull" data-name="{slug}.md" aria-label="全件ダウンロード">⬇<span class="blabel"> 全件ダウンロード</span></button>
</div></header>

<div class="kwrap">
  {_episode_header(episode)}

  <section class="kintro">
    <h2>{E(kit['name'])}</h2>
    <p>{NB(kit["desc"])}</p>
    <div class="kmeta">{''.join(meta)}</div>
    <div class="pnote">{NB(howto)}</div>
  </section>

  {content}

  {_sibling_kits(episode, slug)}
  {_related_kits(kit, related)}

  <footer><a href="../../">← {E(theme['channel_name'])} プレゼント図書館にもどる</a></footer>
</div>

<pre id="pfull" class="hidden">{E(raw_md)}</pre>
<script>{KIT_JS}</script>
{promo_block(promo_icon, n1inc_icon, promo_eps)}
{A.block(preview)}</body></html>"""


# ============================ アプリ受け取りページ ============================
# 実体（原本そのまま）は同じフォルダの app.html。iframeは同一オリジンなので、
# postMessage無しでcontentWindow.documentへ直接アクセスして高さを合わせられる。

APP_JS = r"""
(function(){
  var f = document.getElementById('appframe');
  if (!f) return;
  function fit(){
    try {
      // body.scrollHeightだけを見る: documentElement.scrollHeightはiframe自身の
      // 現在の高さを下限として含んでしまい、一度大きくなると縮められなくなるため使わない。
      var h = f.contentWindow.document.body.scrollHeight;
      if (h) f.style.height = h + 'px';
    } catch (e) {}
  }
  f.addEventListener('load', function(){
    fit();
    try { new ResizeObserver(fit).observe(f.contentWindow.document.body); }
    catch (e) { setInterval(fit, 900); }
  });
})();
"""


def app_page(theme, icon, kit, episode, promo_icon, n1inc_icon, preview=False, related=None, css_ver="", promo_eps=None):
    ep = kit["ep"]
    slug = kit["slug"]
    ep_label = f"No.{ep['no']} {ep['topic']}" if ep["no"] else ep["topic"]
    meta = [f'<span>{E(kit["type"])}</span>', f'<span>{E(ep_label)}</span>',
            f'<span>{E(ep["date"])} 配布</span>']

    return f"""{_head(f"{kit['name']} — {theme['site_name']}", theme, icon, "../../assets/site.css", kit['desc'], noindex=preview, share_img=episode.get("thumb", ""), css_ver=css_ver)}
<header class="kh"><div class="top">
  <a class="back" href="../../">← 一覧へ</a>
  <img src="{icon}" alt="">
  <h1>{E(kit['name'])}</h1>
  <span class="badge">アプリ</span>
  <a class="btn sm" style="margin-left:auto" href="app.html" download="{E(slug)}.html" aria-label="ダウンロード">⬇<span class="blabel"> ダウンロード</span></a>
</div></header>

<div class="kwrap">
  {_episode_header(episode)}

  <section class="kintro">
    <h2>{E(kit['name'])}</h2>
    <p>{NB(kit["desc"])}</p>
    <div class="kmeta">{''.join(meta)}</div>
    <div class="pnote">{NB("このページでそのまま操作できます。ダウンロードすると、このアプリ単体のファイルとしてオフラインでも開けます。")}</div>
  </section>

  <div class="appwrap">
    <iframe id="appframe" class="appframe" src="app.html" title="{E(kit['name'])}" loading="lazy"></iframe>
  </div>

  {_sibling_kits(episode, slug)}
  {_related_kits(kit, related)}

  <footer><a href="../../">← {E(theme['channel_name'])} プレゼント図書館にもどる</a></footer>
</div>

<script>{APP_JS}</script>
{promo_block(promo_icon, n1inc_icon, promo_eps)}
{A.block(preview)}</body></html>"""
