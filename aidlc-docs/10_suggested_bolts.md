# 10 Suggested Bolts（Construction タスク分解）

**プロジェクト名**: Context Butler / 説明補足AI（Explain Bot）

Construction フェーズで実装するタスクを Unit of Work ごとに Issue 化できる粒度で整理します。

---

## Unit A: Slack 起動・非同期ジョブ基盤

### A-01: Slack App 作成・設定

```
目的: Slack App を作成し、Message Shortcut と Interactivity URL を設定する
タスク:
  - api.slack.com で Slack App を作成する
  - Message Shortcut を定義する（callback_id: explain_message）
  - Interactivity & Shortcuts の Request URL を設定する
  - Bot Token Scopes を設定する（chat:write / groups:history / users:read）
  - Signing Secret を取得し、Parameter Store に保存する
  - Bot Token を取得し、Parameter Store に保存する
受け入れ条件:
  - Slack の三点リーダメニューに「Explain with 説明補足AI」が表示される
  - Shortcut 選択時に Interactivity Request が送信される
```

### A-02: API Gateway + Lambda Ack 実装

```
目的: Slack Interactivity Request を受信し、3 秒以内に ack する
タスク:
  - API Gateway（POST /slack/interactivity）を CDK で作成する
  - Lambda Ack を実装する
      - Slack 署名検証（X-Slack-Signature / X-Slack-Request-Timestamp）
      - payload の parse と検証
      - Message Shortcut であることを確認
      - job_id を生成（UUID v4）
      - DynamoDB に job を RECEIVED 状態で保存
      - SQS FIFO に job を投入
      - Slack に 200 OK を返す（3 秒以内）
  - Lambda タイムアウトを 10 秒に設定する
受け入れ条件:
  - Slack の 3 秒制約内に 200 OK を返せる
  - 署名検証に失敗した場合は 403 を返す
  - job_id が DynamoDB に保存される
```

### A-03: SQS FIFO 作成

```
目的: 非同期化・重複排除・エラー処理のための SQS FIFO を作成する
タスク:
  - SQS FIFO キューを CDK で作成する（explain-jobs.fifo）
  - コンテンツベース重複排除を有効にする
  - メッセージグループを {slack_channel_id} に設定する
  - 可視性タイムアウトを 300 秒に設定する
  - DLQ を作成し、最大受信数を 3 に設定する
  - DLQ にメッセージが溜まったら CloudWatch アラームを発火させる
受け入れ条件:
  - 同一リクエストの重複実行が抑制される
  - 処理失敗時に DLQ へ移動する
```

### A-04: Lambda Worker スケルトン + Slack API 連携

```
目的: SQS から job を受け取り、Slack API でメッセージ・スレッドを取得し、スレッドへ返信する
タスク:
  - Lambda Worker を実装する（スケルトン）
      - SQS から job を受け取る
      - DynamoDB の job を CONTEXT_FETCHING に更新する
      - Slack API で対象メッセージを取得する（conversations.replies）
      - Slack API でスレッド履歴を取得する
      - AgentCore / Orchestrator を起動する（Unit B に委譲）
      - 最終補足文を Slack スレッドへ返信する（chat.postMessage）
      - DynamoDB の job を POSTED に更新する
  - Lambda タイムアウトを 5 分に設定する
  - エラーハンドリングを実装する（FAILED 状態への更新）
受け入れ条件:
  - Worker が対象メッセージとスレッド履歴を取得できる
  - Worker が最終補足文を元投稿スレッドへ投稿できる
  - エラー時に DynamoDB の job が FAILED に更新される
```

---

## Unit B: AgentCore + Strands 補足生成パイプライン

### B-01: Agent 間データフロー定義（JSON スキーマ）

```
目的: 各 Agent ステージの入出力 JSON スキーマを定義し、Unit A / C との契約を固定する
タスク:
  - 省略抽出 Agent の出力 JSON スキーマを定義する
      （message_intent / omitted_points / implicit_knowledge / recommended_retrieval_plan / confidence）
  - 文脈取得 Agent の出力 JSON スキーマを定義する
      （retrieved_context / missing_context / retrieval_sources_used）
  - リテラシーレビュー Agent の出力 JSON スキーマを定義する
      （approved / final_message / review_comments / risk_level / modifications_made）
  - スキーマを src/agents/ 配下に JSON Schema ファイルとして保存する
受け入れ条件:
  - 各 Agent の入出力スキーマが定義されている
  - モックを使って Unit A / C と独立して Unit B を開発できる
```

### B-02: 省略抽出 Agent 実装

```
目的: 対象投稿から省略・暗黙知・聞き手が詰まりそうな点を構造化 JSON で抽出する
タスク:
  - 省略抽出プロンプトを実装する（prompts/omission_extractor.md）
  - Strands Agent として実装する
  - 出力を JSON Schema に従って検証する
  - モデルを Claude 3.5 Haiku / Amazon Nova Lite に設定する（temperature: 0.2）
受け入れ条件:
  - 省略点・暗黙知・recommended_retrieval_plan を構造化 JSON で出力できる
  - 補足文を生成しない（後続 Agent の役割）
```

### B-03: 文脈取得 Agent 実装

```
目的: recommended_retrieval_plan に基づき、必要な情報源のみから文脈を収集・整理する
タスク:
  - 文脈取得プロンプトを実装する（prompts/context_retriever.md）
  - Strands Agent として実装する
  - retrieval_plan に基づき KB / Drive / GitHub を選択的に呼び出す
  - 取得できた情報と取得できなかった情報を分離する
  - モデルを Claude 3.5 Haiku / Amazon Nova Lite に設定する（temperature: 0.2）
受け入れ条件:
  - retrieval_plan に含まれる情報源のみ参照する
  - 取得結果に source が付いている
  - missing_context が明示される
```

### B-04: 補足文生成 Agent 実装

```
目的: 背景・前提・用語・判断理由・次アクションを整理した補足文を生成する
タスク:
  - 補足文生成プロンプトを実装する（prompts/supplement_composer.md）
  - Strands Agent として実装する
  - 補足文の冒頭を「補足です。」で始める
  - 事実と推測を分けて書く
  - 不明点を「この投稿だけでは明記されていません」と明示する
  - モデルを Claude 3.5 Sonnet / Amazon Nova Pro に設定する（temperature: 0.5）
受け入れ条件:
  - 補足文に背景・前提・次アクションが含まれる
  - 発言者の意図を変えていない
  - 200〜500 文字程度に収まる（目安）
```

### B-05: リテラシーレビュー Agent 実装

```
目的: 補足文の品質・安全性をレビューし、最終文を出力する
タスク:
  - リテラシーレビュープロンプトを実装する（prompts/literacy_reviewer.md）
  - Strands Agent として実装する
  - 事実/推測の分離・補足過多・個人情報・機密情報をチェックする
  - 軽微な問題は自動修正し、重大な問題は approved: false にする
  - モデルを Claude 3.5 Sonnet / Amazon Nova Pro に設定する（temperature: 0.2）
受け入れ条件:
  - 根拠なし断定を検出・修正できる
  - 個人情報（氏名・メールアドレス・電話番号）の出力をチェックできる
  - 最終補足文を JSON 形式で出力できる
```

### B-06: Strands Orchestrator 実装

```
目的: 4 つの Agent ステージを順次制御する Strands Orchestrator を実装する
タスク:
  - Strands Orchestrator を実装する
  - Stage 1 → Stage 2 → Stage 3 → Stage 4 の順次制御を実装する
  - 各ステージの入出力を JSON Schema で検証する
  - エラーハンドリングを実装する
受け入れ条件:
  - 4 Agent ステージが順次実行される
  - 各ステージの入出力が正しく受け渡される
  - エラー時に適切なエラーメッセージを返す
```

### B-07: AgentCore Runtime 設定

```
目的: AgentCore Runtime 上で Strands Orchestrator をホスティングすることを第一候補として検証する
タスク:
  - AgentCore Runtime の設定を行う
  - Strands Orchestrator を AgentCore Runtime にデプロイする
  - Worker Lambda から AgentCore Runtime を呼び出す
  - 詰まった場合の一時退避手順を確認する（同じ入出力契約を保った Bedrock 直接呼び出し）
受け入れ条件:
  - AgentCore Runtime 上で Strands Orchestrator が動作する
  - Worker Lambda から AgentCore Runtime を呼び出せる
  - 一時退避手順と、予選後にAgentCoreへ戻す条件が確認されている
```

---

## Unit C: ナレッジ・MCP 連携

### C-01: デモ用 KB ソース作成

```
目的: Bedrock Knowledge Bases のソースとなるデモ用 Markdown 資料を作成する
タスク:
  - デモシナリオに合わせた Markdown 資料を作成する
      - プロジェクト概要・背景
      - 用語集（略語・専門用語の説明）
      - システム構成メモ
      - 過去の意思決定メモ（なぜこの技術を選んだか等）
      - 関連 Issue / 議事録の要約
  - S3 バケットの kb-source/ プレフィックスに配置する
受け入れ条件:
  - デモシナリオの投稿に対して、KB から関連情報が取得できる
  - 5〜10 件の Markdown 資料が用意されている
```

### C-02: Bedrock Knowledge Bases 作成

```
目的: S3 上の Markdown 資料を Bedrock Knowledge Bases として設定する
タスク:
  - Bedrock Knowledge Bases を CDK で作成する
  - S3 データソースを設定する
  - 埋め込みモデルを設定する（Amazon Titan Embeddings v2 等）
  - ベクトルストアを設定する（OpenSearch Serverless 等）
  - 文脈取得 Agent から KB を呼び出す実装を追加する
受け入れ条件:
  - 文脈取得 Agent から KB を検索できる
  - 検索結果に source が付いている
```

### C-03: AgentCore Gateway 設定（MCP tools endpoint）

```
目的: AgentCore Gateway を設定し、Google Drive / GitHub MCP を接続する
タスク:
  - AgentCore Gateway を設定する
  - Google Drive MCP を接続する（MVP Target / Future）
  - GitHub MCP を接続する（MVP Target / Future）
  - 文脈取得 Agent から AgentCore Gateway を呼び出す実装を追加する
  - MVP ではモックで代替できる設計にする
受け入れ条件:
  - 文脈取得 Agent から AgentCore Gateway を呼び出せる
  - Drive / GitHub MCP から文脈を取得できる、またはFuture化の判断と代替手段（Knowledge Bases）が明確になっている
```

---

## Unit D: データ永続化・安全性・評価

### D-01: DynamoDB テーブル作成

```
目的: job 状態管理・ユーザー設定・チャンネル文脈管理のための DynamoDB テーブルを作成する
タスク:
  - explain_jobs テーブルを CDK で作成する
      - パーティションキー: job_id (String)
      - TTL 属性: ttl
      - GSI: channel_id-created_at-index
  - user_profiles テーブルを CDK で作成する（Should）
  - channel_contexts テーブルを CDK で作成する（Future）
  - TTL を設定する（explain_jobs: 30 日）
受け入れ条件:
  - job の状態遷移を追跡できる（RECEIVED → GENERATING → POSTED / FAILED）
  - TTL が有効になっている
```

### D-02: Bedrock Guardrails 設定

```
目的: 個人情報・機密情報・根拠なし断定の過剰出力を抑制する Guardrails を設定する
タスク:
  - Bedrock Guardrails を作成する
  - 個人情報フィルタを設定する（氏名・メールアドレス・電話番号）
  - 機密情報フィルタを設定する
  - 根拠なし断定フィルタを設定する
  - リテラシーレビュー Agent の出力に Guardrails を適用する
受け入れ条件:
  - 個人情報・機密情報の過剰出力が抑制される
  - Guardrails が介入した場合にログが記録される
```

### D-03: テストデータ・評価スクリプト作成

```
目的: 想定補足ポイント充足率を評価するためのテストデータと評価スクリプトを作成する
タスク:
  - テストデータを 5〜10 パターン作成する（Slack 投稿 + 想定補足ポイント）
  - 各テストデータに想定補足ポイントを事前定義する
  - 生成結果が想定補足ポイントを満たしているかを採点するスクリプトを作成する
  - 充足率を集計するスクリプトを作成する
  - 評価データは公開リポジトリには含めず、デモ時に限定利用する
受け入れ条件:
  - 5〜10 パターンのテストデータが用意されている
  - 充足率を集計できる
  - 想定補足ポイント充足率 80% 以上を達成している
```

### D-04: CloudWatch ログ・アラーム設定

```
目的: Lambda ログの収集・エラーアラームを設定する
タスク:
  - Lambda Ack・Worker のログを CloudWatch Logs に記録する
  - ログに job_id のみ記録し、Slack 本文・個人情報・トークンを含めない
  - Lambda エラー率の CloudWatch アラームを設定する
  - DLQ メッセージ数の CloudWatch アラームを設定する
受け入れ条件:
  - Lambda ログが CloudWatch Logs に記録される
  - エラー時にアラームが発火する
  - ログに機密情報が含まれていない
```

---

## 実装順序の推奨

```
Construction Phase 1（予選MVP基盤）:
  A-01: Slack App 作成・設定
  A-02: API Gateway + Lambda Ack 実装
  A-03: SQS FIFO 作成
  A-04: Lambda Worker 最小実装
  D-01: DynamoDB テーブル作成
  B-01: Agent 間データフロー定義

Phase 2（予選 MVP）:
  B-02: 省略抽出 Agent 実装
  B-03: 文脈取得 Agent 実装
  B-04: 補足文生成 Agent 実装
  B-05: リテラシーレビュー Agent 実装
  B-06: Strands Orchestrator 実装
  B-07: AgentCore Runtime 設定
  C-01: デモ用 KB ソース作成
  C-02: Bedrock Knowledge Bases 作成
  D-03: テストデータ・評価スクリプト作成
  D-04: CloudWatch ログ・アラーム設定

Phase 3（予選後・余力があれば）:
  C-03: AgentCore Gateway 設定（Drive / GitHub MCP）
  D-02: Bedrock Guardrails 設定
```
