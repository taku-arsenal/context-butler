# Tasks: Context Butler（説明補足AI）

## Phase 1: 基盤構築（Construction Phase 1 - MVP 基盤）

### 1. プロジェクト初期設定

- [ ] 1.1 リポジトリ構成の整備（`src/`, `tests/`, `cdk/`, `prompts/`, `aidlc-docs/` ディレクトリ構成）
- [ ] 1.2 `.gitignore` に機密情報除外設定を追加（`.env`, `.env.*`, `*.pem`, `credentials`, `*.key`, `token.json`, `oauth*.json`, `client_secret*.json`, `service-account*.json` 等の認証情報 JSON）
- [ ] 1.3 `.env.example` にローカル開発用サンプル環境変数を定義（実際の値は含めない）
- [ ] 1.4 Python 依存関係の定義（`pyproject.toml` または `requirements.txt`）
- [ ] 1.5 `README.md` の作成（概要・セットアップ手順の骨格のみ。環境変数の具体的な設定手順・内部デモ手順は含めない）

### 2. Unit A: Slack App 設定（A-01）

- [ ] 2.1 api.slack.com で Slack App を作成する
- [ ] 2.2 Message Shortcut を定義する（callback_id: `explain_message`、名前: 「Explain with 説明補足AI」）
- [ ] 2.3 Interactivity & Shortcuts の Request URL を設定する
- [ ] 2.4 Bot Token Scopes を設定する（`chat:write` / `groups:history` / `users:read` のみ）
- [ ] 2.5 Signing Secret を取得し、AWS Parameter Store（SecureString）に保存する
- [ ] 2.6 Bot Token を取得し、AWS Parameter Store（SecureString）に保存する

### 3. Unit A: API Gateway + Lambda Ack 実装（A-02）

- [ ] 3.1 API Gateway（POST /slack/interactivity）を CDK または手動で作成する
- [ ] 3.2 Slack 署名検証ロジックを実装する（`verify_slack_signature()`）
  - [ ] 3.2.1 `X-Slack-Request-Timestamp` ヘッダーの存在確認
  - [ ] 3.2.2 タイムスタンプが現在時刻から 5 分以内であることを確認（リプレイ攻撃対策）
  - [ ] 3.2.3 `X-Slack-Signature` ヘッダーの存在確認
  - [ ] 3.2.4 `hmac.compare_digest` でタイミング攻撃を防ぎながら署名を検証
- [ ] 3.3 payload の parse と Message Shortcut であることの確認を実装する
- [ ] 3.4 job_id 発行（UUID v4）を実装する
- [ ] 3.5 DynamoDB への job 保存（RECEIVED 状態）を実装する
- [ ] 3.6 SQS FIFO へのメッセージ投入を実装する
- [ ] 3.7 3 秒以内の 200 OK 返却を実装する
- [ ] 3.8 Lambda タイムアウトを 10 秒に設定する
- [ ] 3.9 Lambda Ack の単体テストを実装する（署名検証の正確性・job 発行ロジック）

### 4. Unit A: SQS FIFO 作成（A-03）

- [ ] 4.1 SQS FIFO キュー（`explain-jobs.fifo`）を作成する
- [ ] 4.2 コンテンツベース重複排除を有効にする
- [ ] 4.3 メッセージグループを `{slack_channel_id}` に設定する
- [ ] 4.4 可視性タイムアウトを 300 秒に設定する
- [ ] 4.5 DLQ を作成し、最大受信数を 3 に設定する

### 5. Unit D: DynamoDB テーブル作成（D-01）

- [ ] 5.1 `explain_jobs` テーブルを作成する（PK: job_id (String)）
- [ ] 5.2 TTL 属性（`ttl`）を設定する（30 日）
- [ ] 5.3 GSI（`channel_id-created_at-index`）を設定する
- [ ] 5.4 `user_profiles` テーブルを作成する（Should）

### 6. Unit B: Agent 間データフロー定義（B-01）

- [ ] 6.1 省略抽出 Agent の出力 JSON スキーマを定義する（`src/agents/schemas/omission_extractor_output.json`）
  - `message_intent`, `omitted_points`, `implicit_knowledge`, `recommended_retrieval_plan`, `confidence`
- [ ] 6.2 文脈取得 Agent の出力 JSON スキーマを定義する（`src/agents/schemas/context_retriever_output.json`）
  - `retrieved_context`, `missing_context`, `retrieval_sources_used`
- [ ] 6.3 リテラシーレビュー Agent の出力 JSON スキーマを定義する（`src/agents/schemas/literacy_reviewer_output.json`）
  - `approved`, `final_message`, `review_comments`, `risk_level`, `modifications_made`
- [ ] 6.4 Pydantic モデルとして各スキーマを実装する（`src/agents/models/`）
- [ ] 6.5 スキーマ検証の単体テストを実装する

---

## Phase 2: MVP コア実装

### 7. Unit B: 省略抽出 Agent 実装（B-02）

- [ ] 7.1 省略抽出プロンプトを実装する（`prompts/omission_extractor.md`）
  - 投稿の主旨・省略点・暗黙知・retrieval_plan を構造化 JSON で出力する指示
- [ ] 7.2 Strands Agent として省略抽出 Agent を実装する（`src/agents/omission_extractor/`）
- [ ] 7.3 出力を JSON Schema に従って検証するロジックを実装する
- [ ] 7.4 モデルを Claude 3.5 Haiku / Amazon Nova Lite に設定する（temperature: 0.2）
- [ ] 7.5 省略抽出 Agent の単体テストを実装する（エッジケース: 空メッセージ・長文・略語のみ）

### 8. Unit B: 文脈取得 Agent 実装（B-03）

- [ ] 8.1 文脈取得プロンプトを実装する（`prompts/context_retriever.md`）
- [ ] 8.2 Strands Agent として文脈取得 Agent を実装する（`src/agents/context_retriever/`）
- [ ] 8.3 `retrieval_plan` に基づき KB / Drive / GitHub を選択的に呼び出すロジックを実装する
- [ ] 8.4 取得できた情報と取得できなかった情報を分離するロジックを実装する
- [ ] 8.5 モデルを Claude 3.5 Haiku / Amazon Nova Lite に設定する（temperature: 0.2）
- [ ] 8.6 文脈取得 Agent の単体テストを実装する（KB モック・MCP モック）

### 9. Unit B: 補足文生成 Agent 実装（B-04）

- [ ] 9.1 補足文生成プロンプトを実装する（`prompts/supplement_composer.md`）
  - 補足文の冒頭を「補足です。」で始める指示
  - 事実と推測を分けて書く指示
  - 不明点を「この投稿だけでは明記されていません」と明示する指示
- [ ] 9.2 Strands Agent として補足文生成 Agent を実装する（`src/agents/supplement_composer/`）
- [ ] 9.3 モデルを Claude 3.5 Sonnet / Amazon Nova Pro に設定する（temperature: 0.5）
- [ ] 9.4 補足文生成 Agent の単体テストを実装する（背景・前提・次アクションの含有確認）

### 10. Unit B: リテラシーレビュー Agent 実装（B-05）

- [ ] 10.1 リテラシーレビュープロンプトを実装する（`prompts/literacy_reviewer.md`）
  - 事実/推測の分離チェック指示
  - 補足過多チェック（200〜500 文字目安）指示
  - 個人情報・機密情報チェック指示
- [ ] 10.2 Strands Agent としてリテラシーレビュー Agent を実装する（`src/agents/literacy_reviewer/`）
- [ ] 10.3 軽微な問題は自動修正し、重大な問題は `approved: false` にするロジックを実装する
- [ ] 10.4 モデルを Claude 3.5 Sonnet / Amazon Nova Pro に設定する（temperature: 0.2）
- [ ] 10.5 リテラシーレビュー Agent の単体テストを実装する（根拠なし断定検出・個人情報チェック）

### 11. Unit B: Strands Orchestrator 実装（B-06）

- [ ] 11.1 Strands Orchestrator を実装する（`src/agents/orchestrator/`）
- [ ] 11.2 Stage 1 → Stage 2 → Stage 3 → Stage 4 の順次制御を実装する
- [ ] 11.3 各ステージの入出力を JSON Schema で検証するロジックを実装する
- [ ] 11.4 エラーハンドリングを実装する（各ステージの例外処理）
- [ ] 11.5 Orchestrator の統合テストを実装する（4 ステージの順次実行・データ受け渡し）

### 12. Unit B: AgentCore Runtime 設定（B-07）

- [ ] 12.1 AgentCore Runtime の設定を行う
- [ ] 12.2 Strands Orchestrator を AgentCore Runtime にデプロイする
- [ ] 12.3 Worker Lambda から AgentCore Runtime を呼び出す実装を追加する
- [ ] 12.4 AgentCore Runtime が利用できない場合の Bedrock 直接呼び出しフォールバックを実装する（同一入出力契約）
- [ ] 12.5 フォールバック手順と予選後に AgentCore へ戻す条件を `aidlc-docs/` に記録する

### 13. Unit A: Lambda Worker 実装（A-04）

- [ ] 13.1 Lambda Worker のスケルトンを実装する（`src/lambdas/worker/`）
- [ ] 13.2 SQS からの job 受信と DynamoDB 状態更新を実装する
- [ ] 13.3 Slack API でのメッセージ・スレッド取得を実装する（`conversations.replies`）
- [ ] 13.4 AgentCore / Orchestrator の起動を実装する（`invoke_orchestrator()`）
- [ ] 13.5 最終補足文の Slack スレッドへの返信を実装する（`chat.postMessage`）
- [ ] 13.6 エラーハンドリングを実装する（FAILED 状態への更新・例外再スロー）
- [ ] 13.7 Lambda タイムアウトを 5 分に設定する
- [ ] 13.8 Lambda Worker の単体テストを実装する（Slack API モック・AgentCore モック）

### 14. Unit C: デモ用 KB ソース作成（C-01）

- [ ] 14.1 デモシナリオに合わせた Markdown 資料を作成する（5〜10 件）
  - `kb-source/project-overview.md` - プロジェクト概要・背景
  - `kb-source/glossary.md` - 用語集（略語・専門用語の説明）
  - `kb-source/system-architecture.md` - システム構成メモ
  - `kb-source/decision-log.md` - 過去の意思決定メモ
  - `kb-source/related-issues.md` - 関連 Issue / 議事録の要約
- [ ] 14.2 S3 バケットの `kb-source/` プレフィックスに配置する
- [ ] 14.3 デモシナリオの投稿に対して KB から関連情報が取得できることを確認する

### 15. Unit C: Bedrock Knowledge Bases 作成（C-02）

- [ ] 15.1 Bedrock Knowledge Bases を作成する（CDK または手動）
- [ ] 15.2 S3 データソースを設定する
- [ ] 15.3 埋め込みモデルを設定する（Amazon Titan Embeddings v2 等）
- [ ] 15.4 ベクトルストアを設定する（OpenSearch Serverless 等）
- [ ] 15.5 文脈取得 Agent から KB を呼び出す実装を追加する
- [ ] 15.6 KB 検索の統合テストを実装する（検索結果に source が付いていることを確認）

### 16. Unit D: テストデータ・評価スクリプト作成（D-03）

- [ ] 16.1 テストデータを 5〜10 パターン作成する（Slack 投稿 + 想定補足ポイント）
  - 評価データは公開リポジトリには含めず、デモ時に限定利用する
- [ ] 16.2 各テストデータに想定補足ポイントを事前定義する
  - 例: 背景の言及・用語説明・次アクション明示・不明点の明記・事実/推測の分離
- [ ] 16.3 生成結果が想定補足ポイントを満たしているかを採点するスクリプトを実装する（`scripts/evaluate_coverage.py`）
- [ ] 16.4 充足率を集計するスクリプトを実装する
- [ ] 16.5 想定補足ポイント充足率 80% 以上を達成していることを確認する

### 17. Unit D: CloudWatch ログ・アラーム設定（D-04）

- [ ] 17.1 Lambda Ack・Worker のログを CloudWatch Logs に記録する設定を追加する
- [ ] 17.2 ログに job_id のみ記録し、Slack 本文・個人情報・トークンを含めないことを確認する（例外メッセージに含まれる可能性のある機密情報もサニタイズする）
- [ ] 17.3 Lambda エラー率の CloudWatch アラームを設定する（Should）
- [ ] 17.4 DLQ メッセージ数の CloudWatch アラームを設定する（Should）

---

## Phase 3: MVP Target・Should（余力があれば）

### 18. Unit C: AgentCore Gateway 設定（C-03）

- [ ] 18.1 AgentCore Gateway を設定する（MCP tools endpoint）
- [ ] 18.2 Google Drive MCP を接続する（MVP Target）
- [ ] 18.3 GitHub MCP を接続する（MVP Target）
- [ ] 18.4 文脈取得 Agent から AgentCore Gateway を呼び出す実装を追加する
- [ ] 18.5 MCP 接続失敗時のフォールバック（KB のみで継続）を実装する
- [ ] 18.6 MVP で実装できない場合は Future 化の判断と代替手段を `aidlc-docs/` に記録する

### 19. Unit D: Bedrock Guardrails 設定（D-02）

- [ ] 19.1 Bedrock Guardrails を作成する
- [ ] 19.2 個人情報フィルタを設定する（氏名・メールアドレス・電話番号）
- [ ] 19.3 機密情報フィルタを設定する
- [ ] 19.4 根拠なし断定フィルタを設定する
- [ ] 19.5 リテラシーレビュー Agent の出力に Guardrails を適用する

### 20. IaC（CDK）整備（Should）

- [ ] 20.1 AWS CDK（Python）で全リソースをコード化する（`cdk/` ディレクトリ）
  - API Gateway・Lambda Ack・Lambda Worker・SQS FIFO・DLQ・DynamoDB・S3・IAM
- [ ] 20.2 CDK deploy コマンドで全リソースをデプロイできることを確認する

### 21. プロパティベーステスト（Should）

- [ ] 21.1 `hypothesis` を使ったプロパティベーステストを実装する
  - 任意の非空メッセージに対して補足文が「補足です。」で始まることを検証
  - 同一入力に対して署名検証が冪等であることを検証
  - 全取得文脈アイテムに source が設定されていることを検証

---

## Phase 4: 統合テスト・デモ準備

### 22. E2E 統合テスト

- [ ] 22.1 Slack Shortcut 起動 → SQS → Worker → AgentCore → スレッド返信の全フロー E2E テストを実装する
- [ ] 22.2 AgentCore フォールバックテストを実装する（AgentCore 利用不可時に Bedrock 直接呼び出しへ正しくフォールバックするか）
- [ ] 22.3 重複排除テストを実装する（同一リクエストが 1 回のみ処理されることを確認）
- [ ] 22.4 エラーフローテストを実装する（署名検証失敗・Worker 例外・HIGH リスク検出）

### 23. デモ準備

- [ ] 23.1 デモシナリオを確認し、KB ソースがデモ投稿に対して適切な文脈を返すことを確認する
- [ ] 23.2 想定補足ポイント充足率評価を実行し、80% 以上を達成していることを確認する
- [ ] 23.3 補足文生成完了時間が 30 秒以内であることを CloudWatch で確認する
- [ ] 23.4 Slack Private チャンネルでのデモ動作を確認する
- [ ] 23.5 省略抽出 Agent の構造化 JSON 出力（何が省略されているかの分析）をデモで見せられることを確認する
- [ ] 23.6 AgentCore Runtime + Strands Orchestrator の 4 Agent ステージ処理ログをデモで見せられることを確認する
