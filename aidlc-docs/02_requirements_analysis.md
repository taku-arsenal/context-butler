# 02 Requirements Analysis

**プロジェクト名**: Context Butler / 説明補足AI（Explain Bot）

---

## 1. 機能要件

### 1.1 Slack 連携

| ID | 要件 | MVP / Future |
|----|------|-------------|
| F-01 | Slack の Message Shortcut（三点リーダメニュー）からアプリを起動できる | MVP Must |
| F-02 | Slack Interactivity Request を 3 秒以内に ack できる | MVP Must |
| F-03 | 対象メッセージのテキストを取得できる | MVP Must |
| F-04 | 対象メッセージのスレッド履歴を取得できる | MVP Must |
| F-05 | 元投稿のスレッドに補足文を返信できる | MVP Must |
| F-06 | チャンネル履歴の要約を取得・利用できる | MVP Should |
| F-07 | Slack モーダルで補足レベル・想定読者を選択できる | MVP Should |
| F-08 | 生成結果にフィードバックボタンを付けられる | Future |

### 1.2 AI 処理（Unit B の Agent ステージ）

| ID | 要件 | MVP / Future |
|----|------|-------------|
| F-10 | 対象投稿から省略・暗黙知・聞き手が詰まる点を構造化 JSON で抽出できる（省略抽出 Agent） | MVP Must |
| F-11 | Slack スレッドと社内ナレッジ KB から必要な文脈を収集・整理できる（文脈取得 Agent 最小版） | MVP Must |
| F-12 | 背景・前提・用語・判断理由・次アクションを整理した補足文を生成できる（補足文生成 Agent） | MVP Must |
| F-13 | 補足文の品質・安全性をレビューし最終文を出力できる（リテラシーレビュー Agent） | MVP Must |
| F-14 | 発言者の意図を変えずに補足できる | MVP Must |
| F-15 | 事実と推測を分けて記述できる | MVP Must |
| F-16 | 不明な点は「不明」と明記できる | MVP Must |
| F-17 | 文脈取得 Agent の強化（Drive / GitHub MCP 連携） | MVP Target / Future |

### 1.3 文脈取得・ナレッジ連携（Unit C）

| ID | 要件 | MVP / Future |
|----|------|-------------|
| F-20 | Slack スレッド履歴を取得できる（Slack Web API を直接使用） | MVP Must |
| F-21 | チャンネル履歴要約を利用できる | MVP Should |
| F-22 | Bedrock Knowledge Bases からデモ用社内ナレッジを検索できる | MVP Must |
| F-23 | Google Drive MCP から議事録・仕様書を取得できる（AgentCore Gateway 経由） | MVP Target / Future |
| F-24 | GitHub MCP から Issue・PR・README を取得できる（AgentCore Gateway 経由） | MVP Target / Future |
| F-25 | 必要な情報源のみ参照する（省略抽出 Agent の retrieval_plan に基づく） | MVP Must |

### 1.4 データ管理・評価（Unit D）

| ID | 要件 | MVP / Future |
|----|------|-------------|
| F-30 | job の状態を DynamoDB で管理できる（RECEIVED → GENERATING → POSTED / FAILED） | MVP Must |
| F-31 | ユーザーのリテラシー・役割情報を管理できる | MVP Should |
| F-32 | チャンネルごとの文脈・用語集を管理できる | Future |
| F-33 | フィードバックを記録できる | Future |
| F-34 | 事前に用意したテストデータに対して想定補足ポイント充足率を集計できる | MVP Must |

---

## 2. 非機能要件

### 2.1 パフォーマンス

| ID | 要件 | 目標値 | MVP / Future |
|----|------|--------|-------------|
| NF-01 | Slack Interactivity への応答時間 | 3 秒以内 | MVP Must |
| NF-02 | 補足文生成の完了時間 | 30 秒以内（目標） | MVP Must |
| NF-03 | Lambda Ack の処理時間 | 1 秒以内 | MVP Must |
| NF-04 | Worker Lambda のタイムアウト設定 | 5 分 | MVP Must |

### 2.2 可用性・信頼性

| ID | 要件 | MVP / Future |
|----|------|-------------|
| NF-10 | SQS FIFO による重複排除 | MVP Must |
| NF-11 | SQS DLQ によるエラー処理 | MVP Must |
| NF-12 | Lambda の再試行設定 | MVP Must |
| NF-13 | job 状態管理による処理追跡 | MVP Must |
| NF-14 | job 処理成功率 95% 以上 | MVP Must |

### 2.3 セキュリティ

| ID | 要件 | MVP / Future |
|----|------|-------------|
| NF-20 | Slack 署名検証（X-Slack-Signature / X-Slack-Request-Timestamp） | MVP Must |
| NF-21 | Slack Bot スコープの最小権限化 | MVP Must |
| NF-22 | AWS IAM の最小権限化 | MVP Must |
| NF-23 | DynamoDB の TTL 設定（job データの自動削除） | MVP Must |
| NF-24 | Bedrock Guardrails による出力フィルタリング | MVP Should |
| NF-25 | 機密情報・個人情報の過剰出力防止 | MVP Must |
| NF-26 | MVP デモは権限のある参加者のみを招待した Slack Private チャンネルで実施する | MVP Must |
| NF-27 | 認証情報・トークン・シークレットを .gitignore に含める | MVP Must |

### 2.4 運用・監視

| ID | 要件 | MVP / Future |
|----|------|-------------|
| NF-30 | CloudWatch Logs によるログ収集 | MVP Must |
| NF-31 | Lambda エラーの CloudWatch アラーム | MVP Should |
| NF-32 | job 状態の可視化 | MVP Should |

---

## 3. 制約条件

| 制約 | 内容 | 理由 |
|------|------|------|
| チャネル | Slack のみ（LINE・Teams は将来対応） | MVP の実装範囲を絞るため |
| 起動方法 | Message Shortcut を本命とする | 対象メッセージが明確で業務 UX として自然 |
| AI エージェント基盤 | AgentCore Runtime + Strands Orchestrator を MVP の第一候補にする | AWS ハッカソンでの AgentCore 活用アピール。詰まった場合のみ同じ入出力契約で Bedrock 直接呼び出しへ退避 |
| MCP 利用範囲 | Google Drive と GitHub のみ（Slack MCP は使わない） | Slack 文脈取得は Slack Web API を直接使い、MCP の接続複雑性を避ける |
| A2A | MVP では使わない（将来拡張として設計） | 実装複雑性を抑えるため。将来 Agent を外部サービス化する段階で採用 |
| Slack 権限境界 | MVP デモは権限のある参加者のみを招待した Private チャンネルで実施する | 機密情報の過剰露出を防ぐため |
| リージョン | ap-northeast-1（東京）を基本とする | 日本語処理・レイテンシ最適化 |

---

## 4. MVP / Future の切り分け

### MVP（予選デモで動く範囲）

```
Slack Message Shortcut 起動
  → API Gateway + Lambda Ack（3 秒以内 ack）
  → SQS FIFO（非同期化）
  → Worker Lambda（Slack API でメッセージ・スレッド取得）
  → AgentCore Runtime + Strands Orchestrator
      → 省略抽出 Agent（構造化 JSON 出力）
      → 文脈取得 Agent（Slack スレッド + Bedrock Knowledge Bases）
      → 補足文生成 Agent（背景・前提・次アクション）
      → リテラシーレビュー Agent（事実/推測分離・品質確認）
  → Slack スレッドへ返信
  → DynamoDB job 状態管理
```

### Future（MVP 後に追加する範囲）

```
- Google Drive MCP（AgentCore Gateway 経由。MVPで実装を目指し、難しい場合はFuture）
- GitHub MCP（AgentCore Gateway 経由。MVPで実装を目指し、難しい場合はFuture）
- Slack モーダル（補足レベル・想定読者選択）
- フィードバックボタン
- チャンネル用語集自動生成
- ユーザー別リテラシー学習
- A2A 対応（Agent の外部サービス化・再利用）
- Web 会議リアルタイム補足
- SSO 連携・監査ログ・権限連動検索
```
