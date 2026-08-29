# 【公式速報】ClaudeCode史上1番ヤバい神アプデが発表され、Codexを100倍超える結果になりました — プレゼント一式
# 2026-08-06 配布 / 3点
# ==========================================================


### 1. MCP用語辞典（早見表・逆引き）
# 本編に出てくる新用語を一言で解説します。

# 🎁 MCP用語辞典

本編に出てくる新用語を一言で解説します。

**受け取り方**: 下のコードブロック右上のコピーボタンでコピーするか、このファイルをそのままダウンロードしてください。

```text
【MCP用語辞典】

■ ステートレス — リクエストごとに必要な情報を全部含める方式。サーバー側が「前回のやり取り」を覚えておく必要がない
■ ステートフル — サーバー側が会話の状態（セッション）を覚えておく方式。今回の改訂前のMCPの standard な方式だった
■ セッションID — 旧方式で使われていた、クライアントとサーバーの会話を識別する受付番号。新仕様では廃止された
■ ハンドル — サーバーが発行する「引換券」。状態が必要な処理で、以降のリクエストに毎回添えることで文脈を保つ
■ initialize / initializedハンドシェイク — 旧方式での「最初の挨拶」の手続き。新仕様では廃止され、毎回のリクエストが自己完結するようになった
■ _meta フィールド — 各リクエストに含まれる、クライアント情報やプロトコルバージョンなどの自己紹介情報
■ Mcp-Method / Mcp-Name ヘッダー — リクエストの中身を検査しなくても、どの処理かをゲートウェイが判断できる新しいHTTPヘッダー
■ Extensions（拡張機能） — Tasks・MCP Apps・EMAなど、コア仕様とは独立してバージョン管理される追加機能の枠組み
■ Tasks — 時間のかかる処理を、その場で待たずポーリング（tasks/get）で結果を確認できるようにする拡張機能
■ MCP Apps — サーバーがサンドボックス化されたiframe内で、会話の中に直接インタラクティブなUIを表示できる機能
■ Enterprise Managed Authorization（EMA） — 企業向けに認可の仕組みを一元管理するための拡張機能
■ Client ID Metadata Documents（CIMD） — Dynamic Client Registration（DCR）に代わる、新しいクライアント登録の仕組み
■ 非推奨ポリシー — 廃止予定の機能でも最低12ヶ月は動作を保証するという、今回新設された正式なルール
```


### 2. MCPサーバー移行チェックリスト（チェックリスト）
# 新仕様（2026-07-28）への対応状況を自己診断するチェックリストです。

# 🎁 MCPサーバー移行チェックリスト

新仕様（2026-07-28）への対応状況を自己診断するチェックリストです。

**受け取り方**: 下のコードブロック右上のコピーボタンでコピーするか、このファイルをそのままダウンロードしてください。

**使い方**: 上から順にチェックし、YESの指示に従ってください。

```text
【MCPサーバー移行チェックリスト】

■ ステップ1：今使っているサーバーを洗い出す
□ claude mcp list で接続中のMCPサーバー一覧を確認した
→ YES: 各サーバーの提供元（公式ドキュメント・GitHub）を確認する
指示例: 「claude mcp listの結果を元に、それぞれのMCPサーバーの公式GitHubリポジトリを探して」

■ ステップ2：新仕様（2026-07-28）対応状況を確認する
□ サーバーのchangelog・リリースノートに「2026-07-28」または「stateless」の記載がある
→ YES: 対応済み。特に作業は不要
□ 記載が見当たらない
→ YES: 非推奨機能への依存を確認する（次のステップへ）
指示例: 「このMCPサーバーのGitHubリポジトリを開いて、2026-07-28仕様への対応状況を確認して」

■ ステップ3：非推奨機能への依存を確認する
□ Roots・Sampling・Loggingを使うカスタムサーバーを自作している
→ YES: 最低12ヶ月の移行猶予がある。代替手段（ツール引数・LLM直接統合・OpenTelemetry）への移行を計画に入れる
□ HTTP+SSEの旧トランスポートを使っている
→ YES: 同じく12ヶ月猶予。新しいStreamable HTTPへの移行を検討する

■ ステップ4：様子見でよいか判断する
□ 上記いずれにも該当しない（使う側だけ、または対応済みサーバーのみ）
→ YES: 今は何もしなくてOK。次にサーバーを追加するときに新仕様対応かだけ確認すればよい
指示例: 「新しくMCPサーバーを追加する前に、2026-07-28仕様に対応しているか確認して」

```

**ポイント**: 「今すぐ対応が必要」なケースは少なく、ほとんどの人は様子見でOKです。


### 3. 厳選MCPサーバー100選 つなぐだけコピペ設定（設定・スニペット）
# 実在するMCPサーバー100件を、カテゴリ別に接続コマンドの目安つきでまとめました。

# 🎁 厳選MCPサーバー100選 つなぐだけコピペ設定

実在するMCPサーバー100件を、カテゴリ別に接続コマンドの目安つきでまとめました。

**受け取り方**: 下のコードブロック右上のコピーボタンでコピーするか、このファイルをそのままダウンロードしてください。

**使い方**: `claude mcp add`のコマンドをターミナルに貼るだけでClaude Codeに接続できます（環境によってはAPIキー等の追加設定が必要な場合があります）。

```text
# 🎁 厳選MCPサーバー100選 つなぐだけコピペ設定

実在するMCPサーバー100件を、カテゴリ別に「何をするか」と接続コマンドの目安つきでまとめました。

**注意**: パッケージ名・コマンドは変更される場合があります。使う前に必ず提供元のREADME（GitHub等）で最新の手順を確認してください。


## 開発・実行環境

1. **Playwright**（Microsoft） — ブラウザを自動操作してWebページの操作・スクレイピングを行う
   `claude mcp add playwright -- npx -y @playwright/mcp`
2. **E2B**（E2B Dev） — セキュアなサンドボックス環境でコードを実行する
   `claude mcp add e2b -- npx -y @e2b-dev/mcp-server`
3. **Riza**（Riza.io） — LLMが書いたコードを安全な環境で実行するプラットフォーム
   `claude mcp add riza -- npx -y @riza-io/riza-mcp`
4. **YepCode**（YepCode） — JavaScript/Pythonコードを安全に実行できる環境を提供する
   `claude mcp add yepcode -- npx -y @yepcode/mcp-server-js`
5. **Semgrep**（Semgrep） — コードの静的解析で品質チェック・脆弱性検出を行う
   `claude mcp add semgrep -- npx -y @semgrep/mcp`
6. **Docker**（コミュニティ） — DockerコンテナやDocker Composeをそのまま操作する
   `claude mcp add docker -- npx -y docker-mcp`

## 検索・Web

7. **Exa**（Exa） — AIエージェント向けに最適化された検索エンジンを使う
   `claude mcp add exa -- npx -y exa-mcp-server`
8. **Tavily**（Tavily） — AIエージェント向けのリアルタイムWeb検索を行う
   `claude mcp add tavily -- npx -y tavily-mcp`
9. **Firecrawl**（Mendable） — Webページをクロールしてクリーンなデータとして抽出する
   `claude mcp add firecrawl -- npx -y firecrawl-mcp-server`
10. **Jina Reader**（コミュニティ） — 任意のURLをMarkdown形式に変換して読み込む
   `claude mcp add jina-reader -- npx -y mcp-jina-reader`
11. **Browserbase**（Browserbase） — クラウド上のブラウザを自動操作する
   `claude mcp add browserbase -- npx -y mcp-server-browserbase`
12. **Bright Data**（Bright Data） — 大規模なWebデータの探索・抽出を行う
   `claude mcp add bright-data -- npx -y brightdata-mcp`
13. **Oxylabs**（Oxylabs） — 動的レンダリングにも対応したWebスクレイピングを行う
   `claude mcp add oxylabs -- npx -y oxylabs-mcp`

## データベース

14. **Neon Postgres**（Neon） — サーバーレスPostgres（Neon）をAIから直接操作する
   `claude mcp add neon-postgres -- npx -y mcp-server-neon`
15. **MongoDB**（コミュニティ） — MongoDBのコレクションを直接操作する
   `claude mcp add mongodb -- npx -y mongo-mcp`
16. **ClickHouse**（ClickHouse） — ClickHouseデータベースへのクエリ実行を行う
   `claude mcp add clickhouse -- npx -y mcp-clickhouse`
17. **MotherDuck / DuckDB**（MotherDuck） — DuckDBとMotherDuckのデータ分析クエリを実行する
   `claude mcp add motherduck-duckdb -- npx -y mcp-server-motherduck`
18. **Neo4j**（Neo4j） — グラフデータベースの操作とメモリシステムとして使う
   `claude mcp add neo4j -- npx -y mcp-neo4j`
19. **Supabase**（Supabase Community） — Supabaseのテーブル・認証設定などを操作する
   `claude mcp add supabase -- npx -y supabase-mcp`
20. **Qdrant**（Qdrant） — ベクトル検索エンジンQdrantに埋め込みを保存・検索する
   `claude mcp add qdrant -- npx -y mcp-server-qdrant`
21. **Chroma**（Chroma） — 埋め込み・ベクトル検索・ドキュメント保存を行う
   `claude mcp add chroma -- npx -y chroma-mcp`

## クラウド・インフラ

22. **AWS Documentation**（AWS Labs） — AWS公式ドキュメントを検索して正確な情報を取得する
   `claude mcp add aws-documentation -- npx -y awslabs.aws-documentation-mcp-server`
23. **AWS Cost Analysis**（AWS Labs） — AWSのコスト分析・料金情報を取得する
   `claude mcp add aws-cost-analysis -- npx -y awslabs.cost-analysis-mcp-server`
24. **Google Cloud Run**（Google Cloud） — Cloud Runへアプリケーションをデプロイする
   `claude mcp add google-cloud-run -- npx -y cloud-run-mcp`
25. **DigitalOcean**（コミュニティ） — DigitalOceanのリソースをAPI経由で操作する
   `claude mcp add digitalocean -- npx -y digitalocean-mcp-server`
26. **Kubernetes**（コミュニティ） — Kubernetesのポッド・デプロイメントを管理する
   `claude mcp add kubernetes -- npx -y mcp-server-kubernetes`
27. **Azure DevOps**（Microsoft） — Azure DevOpsのパイプライン・作業項目を操作する
   `claude mcp add azure-devops -- npx -y @microsoft/azure-devops-mcp`
28. **Cloudflare**（Cloudflare） — Workers・KV・R2・D1などCloudflareのリソースを操作する
   `claude mcp add cloudflare -- npx -y @cloudflare/mcp-server-cloudflare`

## コミュニケーション

29. **Slack**（コミュニティ） — Slackワークスペースのメッセージ送受信・検索を行う
   `claude mcp add slack -- npx -y slack-mcp-server`
30. **Twilio**（Twilio Labs） — SMS送信・通話・電話番号管理を行う
   `claude mcp add twilio -- npx -y @twilio-labs/mcp`
31. **LINE公式アカウント**（LINE） — LINE Messaging APIでの配信・応答を行う
   `claude mcp add line -- npx -y line-bot-mcp-server`
32. **Ntfy**（コミュニティ） — ntfy経由でプッシュ通知を送受信する
   `claude mcp add ntfy -- npx -y ntfy-me-mcp`

## デザイン・コンテンツ生成

33. **ElevenLabs**（ElevenLabs） — テキストを自然な音声に変換する
   `claude mcp add elevenlabs -- npx -y elevenlabs-mcp`
34. **SlideSpeak**（SlideSpeak） — テキストからプレゼンテーションスライドを自動生成する
   `claude mcp add slidespeak -- npx -y slidespeak-mcp`
35. **Mermaid**（コミュニティ） — Mermaid記法から図・チャートを生成する
   `claude mcp add mermaid -- npx -y mcp-mermaid`
36. **AntV Chart**（Antvis） — AntVエンジンで各種ビジュアルチャートを生成する
   `claude mcp add antv-chart -- npx -y @antv/mcp-server-chart`

## ビジネス・生産性

37. **Notion**（Notion） — Notionのページ・データベースを読み書きする
   `claude mcp add notion -- npx -y @notionhq/notion-mcp-server`
38. **Taskade**（Taskade） — タスク・プロジェクト・ワークフローを管理する
   `claude mcp add taskade -- npx -y @taskade/mcp`
39. **Linear**（コミュニティ） — Linearのプロジェクト・課題を操作する
   `claude mcp add linear -- npx -y mcp-linear`
40. **Jira**（コミュニティ） — Jiraのボード・課題・担当者を管理する
   `claude mcp add jira -- npx -y jira-mcp`
41. **Airtable**（コミュニティ） — Airtableのデータベースを読み書きする
   `claude mcp add airtable -- npx -y airtable-mcp-server`
42. **Obsidian**（コミュニティ） — ObsidianのノートをREST API経由で操作する
   `claude mcp add obsidian -- npx -y mcp-obsidian`

## 財務・決済

43. **Stripe**（Stripe） — Stripeの決済・顧客情報をAPI経由で操作する
   `claude mcp add stripe -- npx -y @stripe/agent-toolkit`
44. **PayPal**（PayPal） — PayPalの取引・アカウント情報を操作する
   `claude mcp add paypal -- npx -y @paypal/agent-toolkit`
45. **Square**（Square） — Square決済プラットフォームの情報を取得・操作する
   `claude mcp add square -- npx -y square-mcp-server`
46. **Xero**（Xero） — Xeroの会計データ（請求書・仕訳等）を操作する
   `claude mcp add xero -- npx -y xero-mcp-server`

## マーケティング・分析

47. **Google Search Console**（コミュニティ） — Search Consoleの検索パフォーマンスデータを取得する
   `claude mcp add google-search-console -- npx -y mcp-server-gsc`
48. **Google Ads**（コミュニティ） — Google広告の配信・レポートを管理する
   `claude mcp add google-ads -- npx -y google-ads-mcp-server`
49. **Facebook Ads**（コミュニティ） — Facebook広告の配信・レポートを管理する
   `claude mcp add facebook-ads -- npx -y facebook-ads-mcp-server`

## セキュリティ・監視

50. **Sentry**（Sentry） — アプリのクラッシュレポート・エラー監視を確認する
   `claude mcp add sentry -- npx -y @sentry/mcp-server`
51. **Grafana**（Grafana） — Grafanaダッシュボード・インシデントを調査する
   `claude mcp add grafana -- npx -y mcp-grafana`
52. **SonarQube**（SonarSource） — コード品質・脆弱性の分析結果を取得する
   `claude mcp add sonarqube -- npx -y sonarqube-mcp-server`

## DevOps・CI/CD

53. **GitHub**（GitHub） — GitHubのIssue・PR・リポジトリ操作を行う公式サーバー
   `claude mcp add github -- npx -y github-mcp-server`
54. **Buildkite**（Buildkite） — Buildkiteのパイプライン・ビルド状況を管理する
   `claude mcp add buildkite -- npx -y buildkite-mcp-server`
55. **CircleCI**（CircleCI） — CircleCIのビルド失敗の調査・修正を支援する
   `claude mcp add circleci -- npx -y mcp-server-circleci`

## その他ユーティリティ

56. **Memory**（MCP公式リファレンス） — ナレッジグラフ形式の永続メモリを保持する
   `claude mcp add memory -- npx -y @modelcontextprotocol/server-memory`
57. **Sequential Thinking**（MCP公式リファレンス） — 段階的な思考プロセスを記録しながら問題を解く
   `claude mcp add sequential-thinking -- npx -y @modelcontextprotocol/server-sequentialthinking`
58. **Time**（MCP公式リファレンス） — 現在時刻の取得とタイムゾーン変換を行う
   `claude mcp add time -- npx -y @modelcontextprotocol/server-time`
59. **Fetch**（MCP公式リファレンス） — Webコンテンツを取得してMarkdown等に変換する
   `claude mcp add fetch -- npx -y @modelcontextprotocol/server-fetch`
60. **Filesystem**（MCP公式リファレンス） — 許可した範囲のローカルファイルを読み書きする
   `claude mcp add filesystem -- npx -y @modelcontextprotocol/server-filesystem`
61. **Git**（MCP公式リファレンス） — Gitリポジトリの履歴・差分を読み取り操作する
   `claude mcp add git -- npx -y mcp-server-git`
62. **Everything**（MCP公式リファレンス） — プロンプト・リソース・ツール機能のデモ用サーバー
   `claude mcp add everything -- npx -y @modelcontextprotocol/server-everything`
63. **Calculator**（コミュニティ） — 誤差のない精密な数値計算を行う
   `claude mcp add calculator -- npx -y mcp-server-calculator`
64. **Home Assistant**（コミュニティ） — スマートホーム機器（照明・家電等）を制御する
   `claude mcp add home-assistant -- npx -y hass-mcp`

## 検索・Web

65. **WebScraping.AI**（WebScraping.AI） — 各種Webデータ抽出サービスを統合的に呼び出す
   `claude mcp add webscraping-ai -- npx -y webscraping-ai-mcp-server`
66. **Scrapeless**（Scrapeless） — Google検索結果（SERP）を取得する
   `claude mcp add scrapeless -- npx -y scrapeless-mcp-server`

## データベース

67. **Couchbase**（Couchbase） — Couchbaseへのクエリ実行を行う
   `claude mcp add couchbase -- npx -y mcp-server-couchbase`
68. **CockroachDB**（コミュニティ） — CockroachDBの管理・操作を行う
   `claude mcp add cockroachdb -- npx -y mcp-cockroachdb`
69. **Milvus**（Zilliz） — 大規模ベクトルデータベースの検索を行う
   `claude mcp add milvus -- npx -y mcp-server-milvus`
70. **Fireproof**（Fireproof） — 改ざん検知可能な不変台帳データベースを操作する
   `claude mcp add fireproof -- npx -y mcp-database-server`
71. **SQLite**（コミュニティ） — ローカルのSQLiteファイルを直接操作する
   `claude mcp add sqlite -- npx -y mcp-sqlite`

## クラウド・インフラ

72. **AWS Bedrock KB**（AWS Labs） — Amazon Bedrockのナレッジベースを検索する
   `claude mcp add aws-bedrock-kb -- npx -y awslabs.bedrock-kb-retrieval-mcp-server`
73. **AWS CDK**（AWS Labs） — AWS CDKのコードレビュー・アドバイスを受ける
   `claude mcp add aws-cdk -- npx -y awslabs.cdk-mcp-server`
74. **Render**（Render） — Renderのサービス管理・ログ確認を行う
   `claude mcp add render -- npx -y render-mcp-server`
75. **Hetzner Cloud**（コミュニティ） — Hetzner Cloudのサーバーリソースを管理する
   `claude mcp add hetzner-cloud -- npx -y mcp-hetzner`

## コミュニケーション

76. **Email**（コミュニティ） — 複数のメールプロバイダ経由でメールを送信する
   `claude mcp add email -- npx -y mcp-server-email`
77. **Google Keep**（コミュニティ） — Google Keepのメモを作成・検索する
   `claude mcp add google-keep -- npx -y keep-mcp`

## デザイン・コンテンツ生成

78. **Pollinations**（Pollinations） — 画像・音声・テキストを無料で生成する
   `claude mcp add pollinations -- npx -y model-context-protocol`
79. **AWS Nova Canvas**（AWS Labs） — Amazon Nova Canvasで画像を生成する
   `claude mcp add aws-nova-canvas -- npx -y awslabs.nova-canvas-mcp-server`
80. **Mux**（Mux） — 動画のアップロード・管理・字幕生成を行う
   `claude mcp add mux -- npx -y mux-node-sdk`
81. **ECharts**（コミュニティ） — EChartsエンジンでビジュアルチャートを生成する
   `claude mcp add echarts -- npx -y mcp-echarts`

## ビジネス・生産性

82. **Fibery**（Fibery） — Fiberyワークスペースのデータを操作する
   `claude mcp add fibery -- npx -y fibery-mcp-server`
83. **Plane**（Plane） — Planeのプロジェクト・課題を管理する
   `claude mcp add plane -- npx -y plane-mcp-server`
84. **NocoDB**（コミュニティ） — NocoDBのテーブルを読み書きする
   `claude mcp add nocodb -- npx -y nocodb-mcp-server`
85. **Baserow**（Baserow） — Baserowのテーブル操作を行う
   `claude mcp add baserow -- npx -y baserow-mcp-server`

## 財務・決済

86. **Ramp**（Ramp） — 企業カードの支出分析・インサイトを取得する
   `claude mcp add ramp -- npx -y ramp-mcp`
87. **Chargebee**（Chargebee） — サブスクリプション課金・請求管理を行う
   `claude mcp add chargebee -- npx -y agentkit`
88. **LunchMoney**（コミュニティ） — 個人の財務・予算管理データを操作する
   `claude mcp add lunchmoney -- npx -y lunchmoney-mcp`
89. **CoinGecko**（CoinGecko） — 暗号資産の価格・市場データを取得する
   `claude mcp add coingecko -- npx -y coingecko-mcp-server`
90. **Alpha Vantage**（Alpha Vantage） — 株式等の金融市場データを取得する
   `claude mcp add alpha-vantage -- npx -y alphavantage-mcp-server`

## マーケティング・分析

91. **Fathom Analytics**（コミュニティ） — Fathomのアクセス解析データを取得する
   `claude mcp add fathom-analytics -- npx -y mcp-fathom-analytics`
92. **PlainSignal**（PlainSignal） — リアルタイムのWebサイト分析データを取得する
   `claude mcp add plainsignal -- npx -y plainsignal-mcp`
93. **Audiense Insights**（Audiense） — オーディエンス分析・マーケティングインサイトを取得する
   `claude mcp add audiense-insights -- npx -y mcp-audiense-insights`

## セキュリティ・監視

94. **Axiom**（Axiom） — ログ・トレース・イベントデータを分析する
   `claude mcp add axiom -- npx -y mcp-server-axiom`
95. **Raygun**（Mindscape） — クラッシュ・パフォーマンス監視データを確認する
   `claude mcp add raygun -- npx -y mcp-server-raygun`
96. **Cycode**（Cycode） — SAST・SCA・シークレット漏洩の検査を行う
   `claude mcp add cycode -- npx -y cycode-cli`

## DevOps・CI/CD

97. **Currents**（Currents） — Playwrightのテスト失敗結果を分析する
   `claude mcp add currents -- npx -y currents-mcp`

## その他ユーティリティ

98. **Dolt**（DoltHub） — バージョン管理付きデータベースDoltを操作する
   `claude mcp add dolt -- npx -y dolt-mcp`
99. **Browser MCP**（コミュニティ） — ローカルブラウザを自動操作する
   `claude mcp add browser-mcp -- npx -y browsermcp`
100. **Zapier**（Zapier） — 8000以上のアプリ連携をワークフローとして呼び出す
   `claude mcp add zapier -- npx -y zapier-mcp`

以上、100個です。内訳はカテゴリ順に上から並んでいます。
```

**ポイント**: パッケージ名・コマンドは変更される場合があります。使う前に提供元のREADMEで最新情報を確認してください。
