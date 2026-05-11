# Requirements Document: Context Butler（説明補足AI）

## Introduction

Context Butler は、Slack 上の説明不足な投稿を受け手が三点リーダの Message Shortcut から呼び出し、AI が背景・前提・用語・判断理由・次アクションを補足して元投稿のスレッドへ返信するアプリケーションである。

本ドキュメントは、`design.md` に記載された技術設計から導出した機能要件・非機能要件・制約条件を定義する。

---

## Requirements

### 1. Slack 連携（Unit A）

#### 1.1 Message Shortcut 起動

**User Story**: US-01（途中参加のプロジェクトメンバーが三点リーダから補足を呼び出せる）

**Requirement**: システムは Slack の三点リーダメニューに「Explain with 説明補足AI」を表示し、選択時に Interactivity Request を受信できなければならない。

**Acceptance Criteria**:
- [ ] Slack App に Message Shortcut（callback_id: `explain_message`）が定義されている
- [ ] Slack の三点リーダメニューに「Explain with 説明補足AI」が表示される
- [ ] Shortcut 選択時に API Gateway の POST /slack/interactivity エンドポイントへリクエストが送信される
- [ ] Bot Token Scopes に `chat:write` / `groups:history` / `users:read` が設定されている

---

#### 1.2 3 秒以内の ack

**User Story**: US-01

**Requirement**: システムは Slack Interactivity Request を受信してから 3 秒以内に 200 OK を返さなければならない。Lambda Ack は AI 処理を一切行わない。

**Acceptance Criteria**:
- [ ] Lambda Ack の処理時間が 1 秒以内である
- [ ] Slack Interactivity への応答時間が 3 秒以内である
- [ ] Lambda Ack は Bedrock / AgentCore を呼び出さない
- [ ] Lambda Ack のタイムアウトが 10 秒に設定されている

---

#### 1.3 Slack 署名検証

**User Story**: US-01（セキュリティ前提）

**Requirement**: システムは全ての Slack Interactivity Request に対して署名検証を行い、不正なリクエストを拒否しなければならない。

**Acceptance Criteria**:
- [ ] `X-Slack-Signature` ヘッダーが存在しない場合は 403 を返す
- [ ] `X-Slack-Request-Timestamp` ヘッダーが存在しない場合は 403 を返す
- [ ] タイムスタンプが現在時刻から 5 分以上古い場合は 403 を返す（リプレイ攻撃対策）
- [ ] HMAC-SHA256 署名が一致しない場合は 403 を返す
- [ ] `hmac.compare_digest` を使用してタイミング攻撃を防ぐ

---

#### 1.4 非同期ジョブ管理

**User Story**: US-01

**Requirement**: システムは SQS FIFO を使って非同期化し、同一リクエストの重複実行を防がなければならない。

**Acceptance Criteria**:
- [ ] SQS FIFO キュー（`explain-jobs.fifo`）が作成されている
- [ ] コンテンツベース重複排除が有効になっている
- [ ] メッセージグループが `{slack_channel_id}` に設定されている
- [ ] 可視性タイムアウトが 300 秒に設定されている
- [ ] DLQ が設定されており、最大受信数が 3 に設定されている
- [ ] 同一リクエストの重複実行が抑制される

---

#### 1.5 Slack メッセージ・スレッド取得

**User Story**: US-01, US-02

**Requirement**: Lambda Worker は Slack Web API を使って対象メッセージとスレッド履歴を取得できなければならない。Slack MCP は使わない。

**Acceptance Criteria**:
- [ ] `conversations.replies` API で対象メッセージのスレッド履歴を取得できる
- [ ] 取得したメッセージに `ts`・`user`・`text` が含まれる
- [ ] Slack MCP を使わず、Slack Web API を直接呼び出す
- [ ] Slack API エラー時に job を FAILED 状態に更新し、例外を再スローする

---

#### 1.6 スレッドへの補足文返信

**User Story**: US-01

**Requirement**: システムは最終補足文を元投稿のスレッドへ返信できなければならない。

**Acceptance Criteria**:
- [ ] `chat.postMessage` API で元投稿のスレッドへ返信できる
- [ ] 返信が元投稿のスレッドに紐付いている（`thread_ts` が設定されている）
- [ ] 返信成功後に DynamoDB の job を POSTED 状態に更新する

---

### 2. AI 補足生成パイプライン（Unit B）

#### 2.1 省略抽出 Agent

**User Story**: US-03, US-07

**Requirement**: 省略抽出 Agent は対象投稿から省略・暗黙知・聞き手が詰まりそうな点を構造化 JSON で抽出できなければならない。

**Acceptance Criteria**:
- [ ] `message_intent`（投稿の主旨）を 1 文で出力できる
- [ ] `omitted_points`（省略されている情報）をリストで出力できる
- [ ] `implicit_knowledge`（暗黙知・略語・専門用語）を構造化 JSON で出力できる
- [ ] `recommended_retrieval_plan`（必要な情報源の取得計画）を出力できる
- [ ] 出力が JSON Schema に準拠している
- [ ] 補足文を生成しない（後続 Agent の役割）
- [ ] モデルが Claude 3.5 Haiku または Amazon Nova Lite に設定されている

---

#### 2.2 文脈取得 Agent

**User Story**: US-02

**Requirement**: 文脈取得 Agent は `recommended_retrieval_plan` に基づき、必要な情報源のみから文脈を収集・整理できなければならない。

**Acceptance Criteria**:
- [ ] `retrieval_plan` に含まれる情報源のみ参照する
- [ ] 取得結果に `source`（`slack_message` / `slack_thread` / KB / Drive / GitHub）が付いている
- [ ] 取得できた情報と取得できなかった情報（`missing_context`）を分離できる
- [ ] Bedrock Knowledge Bases から関連情報を検索できる
- [ ] KB 検索結果が空の場合は `missing_context` に記録する
- [ ] モデルが Claude 3.5 Haiku または Amazon Nova Lite に設定されている

---

#### 2.3 補足文生成 Agent

**User Story**: US-05, US-07, US-09

**Requirement**: 補足文生成 Agent は背景・前提・用語・判断理由・次アクションを整理した補足文を生成できなければならない。

**Acceptance Criteria**:
- [ ] 補足文の冒頭が「補足です。」で始まる
- [ ] 補足文に「背景」「前提」「次アクション」が含まれる
- [ ] 略語・専門用語の説明が含まれる（必要な場合）
- [ ] 発言者の意図を変えていない
- [ ] 補足文が 200〜500 文字程度に収まる（目安）
- [ ] モデルが Claude 3.5 Sonnet または Amazon Nova Pro に設定されている

---

#### 2.4 リテラシーレビュー Agent

**User Story**: US-08, US-10

**Requirement**: リテラシーレビュー Agent は補足文の品質・安全性をレビューし、最終文を出力できなければならない。

**Acceptance Criteria**:
- [ ] 取得した文脈から確認できることは断定形で書かれる
- [ ] 確認できないことは「〜と考えられます」「〜の可能性があります」と書かれる
- [ ] 不明な点は「この投稿だけでは明記されていません」と明示される
- [ ] 根拠なし断定を検出・修正できる
- [ ] 個人情報（氏名・メールアドレス・電話番号）の出力をチェックできる
- [ ] 補足過多をチェックし、200〜500 文字程度に収める
- [ ] 最終補足文を JSON 形式（`LiteracyReviewerOutput`）で出力できる
- [ ] `risk_level: HIGH` の場合は `approved: false` を返す
- [ ] モデルが Claude 3.5 Sonnet または Amazon Nova Pro に設定されている

---

#### 2.5 Strands Orchestrator

**User Story**: US-01〜US-10（全体）

**Requirement**: Strands Orchestrator は 4 つの Agent ステージを順次制御し、最終補足文を返せなければならない。

**Acceptance Criteria**:
- [ ] Stage 1（省略抽出）→ Stage 2（文脈取得）→ Stage 3（補足文生成）→ Stage 4（リテラシーレビュー）の順で実行される
- [ ] 各ステージの入出力が JSON Schema で検証される
- [ ] エラー時に適切なエラーメッセージを返す
- [ ] AgentCore Runtime 上で動作する（第一候補）
- [ ] AgentCore Runtime が利用できない場合、同一入出力契約で Bedrock 直接呼び出しへフォールバックできる

---

#### 2.6 想定補足ポイント充足率

**User Story**: US-02, US-03, US-05, US-07, US-08, US-09

**Requirement**: システムは事前に用意したテストデータに対して、想定補足ポイントを 80% 以上満たす補足文を生成できなければならない。

**Acceptance Criteria**:
- [ ] 5〜10 パターンのテストデータが用意されている
- [ ] 各テストデータに想定補足ポイントが事前定義されている
- [ ] 充足率を集計するスクリプトが実装されている
- [ ] 全テストデータの平均充足率が 80% 以上である

---

### 3. ナレッジ・MCP 連携（Unit C）

#### 3.1 Bedrock Knowledge Bases

**User Story**: US-02

**Requirement**: システムは Bedrock Knowledge Bases からデモ用社内ナレッジを検索し、source 付きで結果を返せなければならない。

**Acceptance Criteria**:
- [ ] S3 の `kb-source/` プレフィックスに Markdown 資料が配置されている（5〜10 件）
- [ ] Bedrock Knowledge Bases が S3 データソースを参照している
- [ ] 文脈取得 Agent から KB を検索できる
- [ ] 検索結果に `source`（S3 URI または Markdown ファイル名）が付いている
- [ ] デモシナリオの投稿に対して KB から関連情報が取得できる

---

#### 3.2 AgentCore Gateway（MCP tools endpoint）

**User Story**: US-02（MVP Target / Future）

**Requirement**: システムは AgentCore Gateway 経由で Google Drive / GitHub MCP に接続し、外部文脈を取得できなければならない。ただし MVP では実装を目指し、期間内に安定化できない場合は Future として扱う。

**Acceptance Criteria**:
- [ ] AgentCore Gateway が設定されている
- [ ] 文脈取得 Agent から AgentCore Gateway を呼び出せる
- [ ] Drive / GitHub MCP から文脈を取得できる、または Future 化の判断と代替手段（KB）が明確になっている
- [ ] MCP 接続失敗時は `missing_context` に記録し、KB のみで処理を継続する
- [ ] Slack 文脈取得は Slack Web API を直接使い、Slack MCP は使わない

---

### 4. データ永続化・安全性・評価（Unit D）

#### 4.1 job 状態管理

**User Story**: US-01

**Requirement**: システムは DynamoDB で job の状態遷移を追跡できなければならない。

**Acceptance Criteria**:
- [ ] `explain_jobs` テーブルが作成されている（PK: job_id）
- [ ] job の状態遷移を追跡できる（RECEIVED → CONTEXT_FETCHING → GENERATING → REVIEWING → POSTED / FAILED）
- [ ] TTL が 30 日に設定されている
- [ ] GSI（channel_id-created_at-index）が設定されている
- [ ] エラー時に `error_message` が記録される（Slack 本文・トークン等の機密情報はサニタイズして保存する）

---

#### 4.2 セキュリティ・プライバシー

**User Story**: US-08（安全性前提）

**Requirement**: システムは機密情報・個人情報の過剰露出を防ぎ、最小権限の原則に従わなければならない。

**Acceptance Criteria**:
- [ ] Slack Bot スコープが `chat:write` / `groups:history` / `users:read` のみに制限されている
- [ ] Lambda Ack IAM が DynamoDB PutItem / SQS SendMessage / SSM GetParameter のみに制限されている
- [ ] Lambda Worker IAM が必要最小限のポリシーのみに制限されている
- [ ] Slack Token・Signing Secret・GitHub Token・Google OAuth Client Secret が AWS Parameter Store（SecureString）で管理されている
- [ ] `.env` / `.env.*` / `*.pem` / `credentials` / `*.key` が `.gitignore` に含まれている
- [ ] CloudWatch Logs に Slack 本文・個人情報・トークンが含まれない（job_id のみ記録）
- [ ] MVP デモが権限のある参加者のみを招待した Slack Private チャンネルで実施される

---

#### 4.3 Bedrock Guardrails（Should）

**User Story**: US-08

**Requirement**: システムは Bedrock Guardrails で個人情報・機密情報・根拠なし断定の過剰出力を抑制できなければならない（MVP Should）。

**Acceptance Criteria**:
- [ ] Bedrock Guardrails が作成されている
- [ ] 個人情報フィルタ（氏名・メールアドレス・電話番号）が設定されている
- [ ] 機密情報フィルタが設定されている
- [ ] Guardrails が介入した場合にログが記録される

---

#### 4.4 監視・運用性

**User Story**: US-01（運用前提）

**Requirement**: システムは Lambda ログの収集・エラーアラームを設定し、job 状態を追跡できなければならない。

**Acceptance Criteria**:
- [ ] Lambda Ack・Worker のログが CloudWatch Logs に記録される
- [ ] Lambda エラー率の CloudWatch アラームが設定されている（Should）
- [ ] DLQ メッセージ数の CloudWatch アラームが設定されている（Should）
- [ ] job_id を起点に Lambda ログ・DynamoDB レコードを追跡できる

---

### 5. 非機能要件

#### 5.1 パフォーマンス

| ID | 要件 | 目標値 | 優先度 |
|----|------|--------|--------|
| NF-01 | Slack Interactivity への応答時間 | 3 秒以内 | Must |
| NF-02 | Lambda Ack の処理時間 | 1 秒以内 | Must |
| NF-03 | 補足文生成の完了時間 | 30 秒以内（目標） | Must |
| NF-04 | Worker Lambda のタイムアウト設定 | 5 分 | Must |

#### 5.2 可用性・信頼性

| ID | 要件 | 優先度 |
|----|------|--------|
| NF-10 | SQS FIFO による重複排除 | Must |
| NF-11 | SQS DLQ によるエラー処理（最大受信数: 3） | Must |
| NF-12 | Lambda の再試行設定 | Must |
| NF-13 | job 状態管理による処理追跡 | Must |
| NF-14 | job 処理成功率 95% 以上 | Must |

#### 5.3 セキュリティ

| ID | 要件 | 優先度 |
|----|------|--------|
| NF-20 | Slack 署名検証（X-Slack-Signature / X-Slack-Request-Timestamp） | Must |
| NF-21 | リプレイ攻撃対策（タイムスタンプ 5 分以内チェック） | Must |
| NF-22 | Slack Bot スコープの最小権限化 | Must |
| NF-23 | AWS IAM の最小権限化 | Must |
| NF-24 | DynamoDB の TTL 設定（job データ 30 日で自動削除） | Must |
| NF-25 | 機密情報・個人情報の過剰出力防止 | Must |
| NF-26 | MVP デモは Slack Private チャンネルで実施 | Must |
| NF-27 | 認証情報・トークン・シークレットを .gitignore に含める | Must |
| NF-28 | Bedrock Guardrails による出力フィルタリング | Should |

#### 5.4 運用・監視

| ID | 要件 | 優先度 |
|----|------|--------|
| NF-30 | CloudWatch Logs によるログ収集 | Must |
| NF-31 | Lambda エラーの CloudWatch アラーム | Should |
| NF-32 | DLQ メッセージ数の CloudWatch アラーム | Should |
| NF-33 | job 状態の可視化（DynamoDB） | Must |
| NF-34 | AWS CDK による IaC | Should |

---

### 6. 制約条件

| 制約 | 内容 |
|------|------|
| チャネル | Slack のみ（LINE・Teams は将来対応） |
| 起動方法 | Message Shortcut を本命とする |
| AI エージェント基盤 | AgentCore Runtime + Strands Orchestrator を MVP の第一候補にする。詰まった場合のみ同じ入出力契約で Bedrock 直接呼び出しへ退避 |
| MCP 利用範囲 | Google Drive と GitHub のみ（Slack MCP は使わない） |
| A2A | MVP では使わない（将来拡張として設計） |
| Slack 権限境界 | MVP デモは権限のある参加者のみを招待した Private チャンネルで実施する |
| リージョン | ap-northeast-1（東京）を基本とする |
| 主要定量指標 | 想定補足ポイント充足率 80% 以上（手動修正回数は主要指標にしない） |
| 公開禁止事項 | デモシナリオ・テストデータ・内部評価表・PDF 資料は公開 GitHub に載せない |
| 公開禁止事項 | 認証情報・OAuth token・.env・AWS credential・Slack signing secret・GitHub token・Google OAuth client secret は .gitignore に含める |
| 公開禁止事項 | README には環境変数の具体的な設定手順や内部デモ手順を載せない |

---

### 7. MVP / Future の切り分け

#### MVP Must（予選デモで必須）

- Slack Message Shortcut 起動 → API Gateway + Lambda Ack（3 秒以内 ack）
- SQS FIFO（非同期化・重複排除）
- Lambda Worker（Slack API でメッセージ・スレッド取得）
- AgentCore Runtime + Strands Orchestrator（4 Agent ステージ、第一候補）。AgentCore が利用できない場合は同一入出力契約で Bedrock 直接呼び出しへフォールバック
- Bedrock Knowledge Bases（デモ用社内ナレッジ RAG）
- 補足文生成 → リテラシーレビュー → スレッド返信
- DynamoDB job 状態管理（TTL 30 日）
- Slack 署名検証・最小権限・シークレット管理
- 想定補足ポイント充足率評価スクリプト

#### MVP Target（予選デモで実装を目指す）

- Google Drive MCP（AgentCore Gateway 経由）
- GitHub MCP（AgentCore Gateway 経由）

#### MVP Should（余力があれば）

- Slack モーダル（補足レベル・想定読者選択）
- Bedrock Guardrails
- AWS CDK による IaC
- CloudWatch アラーム

#### Future（MVP 後に追加）

- フィードバックボタン
- チャンネル用語集自動生成
- ユーザー別リテラシー学習
- A2A 対応
- Web 会議リアルタイム補足
- SSO 連携・監査ログ・権限連動検索
