# 07 Non-Functional Requirements (NFRs)

**プロジェクト名**: Context Butler / 説明補足AI（Explain Bot）

---

## 1. レイテンシ

| 要件 | 目標値 | 根拠 | MVP / Future |
|------|--------|------|-------------|
| Slack Interactivity への応答時間 | 3 秒以内 | Slack の仕様上、3 秒以内に応答しないとタイムアウトエラーになる | MVP Must |
| Lambda Ack の処理時間 | 1 秒以内 | 署名検証と SQS 投入のみに特化し、AI 処理を行わない | MVP Must |
| 補足文生成の完了時間 | 30 秒以内（目標） | デモ中に待ち時間が長すぎると体験が悪化する | MVP Must |
| Worker Lambda のタイムアウト設定 | 5 分 | Bedrock の推論時間・KB 検索・MCP 呼び出しを考慮 | MVP Must |

**対策**: 軽い Agent（省略抽出・文脈取得）は Claude 3.5 Haiku / Amazon Nova Lite で高速化。生成中は「補足を生成中です」メッセージで UX を補完。

---

## 2. 可用性・信頼性

| 要件 | 目標値 | 対策 | MVP / Future |
|------|--------|------|-------------|
| job 処理成功率 | 95% 以上（目標） | SQS DLQ + Lambda 再試行 | MVP Must |
| 重複実行の防止 | 同一リクエストを 1 回のみ処理 | SQS FIFO のコンテンツベース重複排除 | MVP Must |
| エラー時の可視性 | 失敗 job を追跡できる | DynamoDB job 状態管理（FAILED 状態）+ CloudWatch アラーム | MVP Must |
| DLQ 監視 | DLQ にメッセージが溜まったらアラート | CloudWatch アラーム | MVP Should |

---

## 3. セキュリティ

| 要件 | 対策 | MVP / Future |
|------|------|-------------|
| Slack リクエストの正当性確認 | Slack 署名検証（X-Slack-Signature / X-Slack-Request-Timestamp）。`hmac.compare_digest` でタイミング攻撃を防ぐ | MVP Must |
| リプレイ攻撃対策 | タイムスタンプが現在時刻から 5 分以内であることを確認 | MVP Must |
| Slack Bot スコープの最小権限化 | `chat:write` / `groups:history` / `users:read` のみ付与 | MVP Must |
| AWS IAM の最小権限化 | Lambda Ack・Worker それぞれに必要最小限のポリシーを付与 | MVP Must |
| シークレット管理 | Slack Token・Signing Secret・GitHub Token・Google OAuth Client Secret は AWS Parameter Store（SecureString）で管理 | MVP Must |
| `.gitignore` への機密情報除外 | `.env` / `.env.*` / `*.pem` / `credentials` / `*.key` を `.gitignore` に含める | MVP Must |
| 出力フィルタリング | Bedrock Guardrails で個人情報・機密情報・根拠なし断定を抑制 | MVP Should |

---

## 4. プライバシー

| 要件 | 対策 | MVP / Future |
|------|------|-------------|
| Slack 本文の長期保存禁止 | DynamoDB `explain_jobs` に TTL 30 日を設定し自動削除 | MVP Must |
| 個人情報の過剰出力防止 | リテラシーレビュー Agent が氏名・メールアドレス・電話番号の出力をチェック | MVP Must |
| 機密情報の過剰露出防止 | Drive / GitHub 取得情報は要約のみ使用。そのまま Slack に貼らない | MVP Must |
| MVP の権限境界 | MVP デモは権限のある参加者のみを招待した Slack Private チャンネルで実施する | MVP Must |
| ログへの機密情報除外 | CloudWatch Logs に Slack 本文・個人情報・トークンを含めない。job_id のみ記録 | MVP Must |

---

## 5. 監視・運用性

| 要件 | 対策 | MVP / Future |
|------|------|-------------|
| Lambda ログの収集 | CloudWatch Logs に Lambda Ack・Worker のログを記録 | MVP Must |
| エラーアラーム | Lambda エラー率・DLQ メッセージ数の CloudWatch アラーム | MVP Should |
| job 状態の追跡 | DynamoDB `explain_jobs` で RECEIVED → GENERATING → POSTED / FAILED を追跡 | MVP Must |
| 処理時間の計測 | Lambda Worker で補足生成完了時間を記録 | MVP Should |
| デバッグ容易性 | job_id を起点に Lambda ログ・DynamoDB レコードを追跡できる | MVP Must |

---

## 6. コスト

| サービス | MVP での想定利用量 | コスト対策 |
|---------|-----------------|-----------|
| Lambda | 数十〜数百回/日（デモ用） | 無料枠内に収まる見込み |
| SQS FIFO | 数十〜数百メッセージ/日 | 無料枠内に収まる見込み |
| DynamoDB | 数十〜数百 job/日 | オンデマンドモード。無料枠内に収まる見込み |
| Bedrock（LLM） | 数十〜数百リクエスト/日 | 軽い Agent は Haiku / Nova Lite で低コスト化 |
| Bedrock Knowledge Bases | デモ用 KB（数 MB） | 小規模 KB で低コスト |
| S3 | KB ソース（数 MB） | 無料枠内に収まる見込み |
| CloudWatch | ログ・メトリクス | 無料枠内に収まる見込み |

**方針**: MVP はデモ用途のため、コストよりも動作確認を優先する。本番化時にコスト最適化を検討する。

---

## 7. 運用性

| 要件 | 対策 | MVP / Future |
|------|------|-------------|
| IaC による再現性 | AWS CDK（Python）で全リソースをコード化 | MVP Should |
| 設定値の管理 | `.env.example` はローカル開発用のサンプルに限定し、実際の値は Parameter Store で管理 | MVP Must |
| デプロイの容易性 | CDK deploy コマンドで全リソースをデプロイできる | MVP Should |
| ロールバック容易性 | CDK の前バージョンに戻せる | Future |
| ドキュメントの整備 | README・aidlc-docs/ に設計・運用手順を記載 | MVP Must |
