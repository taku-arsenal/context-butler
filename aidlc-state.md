# AI-DLC Inception フェーズ 完了状態

**プロジェクト名**: Context Butler / 説明補足AI（Explain Bot）  
**GitHub**: https://github.com/taku-arsenal/context-butler  
**ハッカソン**: AWS Summit Japan 2026 AI-DLC ハッカソン  
**フェーズ**: Inception 完了 → Construction 開始待ち  
**更新日**: 2026-05-10

---

## Intent（一言）

> Slack 上の説明不足な投稿を、受け手が三点リーダから呼び出すだけで、AI が背景・前提・用語・判断理由・次アクションを補足してスレッドへ返信する。  
> 「説明責任」「文脈整理」「聞き手への配慮」を AI に外注し、人間が説明を考える努力を減らす。ハッカソンテーマ「人をダメにする」を業務効率化として成立させる切り口。

---

## Inception で確定した主要 Unit of Work

| Unit | 名称 | 目的 |
|------|------|------|
| A | Slack 起動・非同期ジョブ基盤 | Message Shortcut 受信 → 3 秒 ack → SQS 非同期化 → スレッド返信 |
| B | AgentCore + Strands 補足生成パイプライン | 省略抽出・文脈取得・補足文生成・リテラシーレビューの 4 Agent ステージを Strands Orchestrator で順次制御 |
| C | ナレッジ・MCP 連携 | Bedrock Knowledge Bases をMVP Mustとし、AgentCore Gateway 経由の Google Drive / GitHub MCP はMVPで実装を目指す |
| D | データ永続化・安全性・評価 | DynamoDB job 管理・Guardrails・想定補足ポイント充足率評価 |

> **注意**: 省略抽出 / 文脈取得 / 補足文生成 / リテラシーレビューは Unit B に含まれる **実行時 Agent ステージ** であり、AI-DLC の Unit of Work ではありません。

---

## 主要リスク（Inception 時点）

| リスク | 影響 | 対策 |
|--------|------|------|
| AgentCore Runtime 設定の遅延 | 中 | MVP から第一候補として利用。詰まった場合のみ同じ入出力契約で Bedrock 直接呼び出しへ退避し、予選後にAgentCoreへ戻す |
| 事実誤認・根拠なし断定 | 高 | リテラシーレビュー Agent + Guardrails で事実/推測を分離。不明点は「不明」と明記 |
| 機密情報の過剰露出 | 高 | MVP は Slack Private チャンネル + 権限者のみ招待。Drive/GitHub 取得情報は要約のみ使用 |
| 「ただの要約 Bot」に見える | 中 | 省略抽出の構造化出力・KB/Drive/GitHub 連携・リテラシーレビューを明示してデモ |

---

## Construction で最初に実装する内容

1. **Unit A**: Slack App 作成 → API Gateway → Lambda Ack（署名検証・SQS 投入・3 秒 ack）→ SQS FIFO → Worker Lambda 最小実装
2. **Unit B**: Strands Orchestrator + 4 Agent ステージの最小実装（AgentCore Runtime を第一候補）
3. **Unit D**: DynamoDB `explain_jobs` テーブル作成・job 状態管理
4. **Unit C**: Bedrock Knowledge Bases（デモ用 Markdown KB）→ 文脈取得 Agent に接続

---

## 詳細ドキュメント

| ファイル | 内容 |
|---------|------|
| [aidlc-docs/01_intent.md](aidlc-docs/01_intent.md) | Business Intent・テーマ接続・対象ユーザー・MVP 仮説 |
| [aidlc-docs/02_requirements_analysis.md](aidlc-docs/02_requirements_analysis.md) | 機能要件・非機能要件・制約・MVP/Future 切り分け |
| [aidlc-docs/03_user_stories.md](aidlc-docs/03_user_stories.md) | Persona 別 user story・acceptance criteria・優先度 |
| [aidlc-docs/04_unit_of_work_plan.md](aidlc-docs/04_unit_of_work_plan.md) | Unit A〜D の詳細定義・依存関係・受け入れ条件 |
| [aidlc-docs/05_application_design.md](aidlc-docs/05_application_design.md) | AWS 構成・シーケンス・MCP 利用範囲・セキュリティ |
| [aidlc-docs/06_prfaq.md](aidlc-docs/06_prfaq.md) | PRFAQ 形式のプロダクト説明 |
| [aidlc-docs/07_nfrs.md](aidlc-docs/07_nfrs.md) | レイテンシ・可用性・セキュリティ・コスト等の NFR |
| [aidlc-docs/08_risks.md](aidlc-docs/08_risks.md) | リスク一覧と mitigation |
| [aidlc-docs/09_measurement_criteria.md](aidlc-docs/09_measurement_criteria.md) | 成功指標・定性評価・定量評価 |
| [aidlc-docs/10_suggested_bolts.md](aidlc-docs/10_suggested_bolts.md) | Construction タスク分解（Unit 別 Issue 粒度） |
