# Kiro向けプロンプト: AI-DLC Inception成果物の再整備

以下の前提を踏まえて、AWS Summit Japan 2026 AI-DLC ハッカソンの書類審査に提出できる **Inception フェーズの AI-DLC 成果物**を再整備してください。既存ドキュメントを単に要約するのではなく、AI-DLC の用語を正しく使い、審査員が Intent、Unit 分解、テーマ適合性、MVP 実現性を判断できる状態にしてください。

## 参照資料

- `AI-Driven Development Lifecycle.pdf`
- `AWS_Summit_Japan_2026_Hackathon_参加規約.pdf`
- `AWS-Summit-Japan-2026-Hackathon_説明会_配布用.pdf`
- 既存の `README.md` と `docs/` 配下の設計書
- Diagram MCP 生成図:
  - `docs/images/context-butler-aws-mcp-architecture.png`
  - `docs/images/context-butler-aidlc-unit-of-work.png`

上記PDFは内部参考資料であり、GitHubに公開しないでください。

## 重要な用語定義

AI-DLC における **Unit of Work** は、実行時の Agent 名ではありません。Intent から導かれる、凝集度が高く自己完結した作業単位です。DDD のサブドメインや Scrum の Epic に近く、複数の user story / task / risk / NFR / measurement criteria を束ね、並行開発しやすい単位として扱います。

本アプリには実行時の AI 処理として以下の Agent ステージがありますが、これらをそのまま AI-DLC Unit と呼ばないでください。

- 省略抽出 Agent
- 文脈取得 Agent
- 補足文生成 Agent
- リテラシーレビュー Agent

上記は主に Unit of Work B に含まれる実行時コンポーネントです。

## プロダクト前提

- プロダクト名: Context Butler / 説明補足AI（Explain Bot）
- GitHub URL: `https://github.com/taku-arsenal/context-butler`
- Slack 上の説明不足な投稿を、三点リーダの Message Shortcut から呼び出し、AI が背景・前提・用語・判断理由・次アクションを補足して元投稿のスレッドへ返信する。
- ハッカソンテーマ「人をダメにする」に対しては、「説明責任」「文脈整理」「聞き手への配慮」を AI に外注し、人間が説明を考える努力を減らす、という切り口で接続する。
- ただし、業務効率化として成立する実用性を強調し、倫理的に危険な印象になりすぎない表現にする。

## アーキテクチャ方針

- Slack Message Shortcut を起点にする。
- Slack Interactivity は API Gateway + Lambda Ack で受け、3秒以内に ack する。
- 生成AI処理は SQS FIFO + Worker Lambda で非同期化する。
- MVP から Amazon Bedrock AgentCore Runtime + Strands Orchestrator の利用を第一候補にする。
- AgentCore が必須要件という書き方は避けるが、予選MVPから利用したい主要技術として扱う。詰まった場合のみ、同じ入出力契約を保って Bedrock 直接呼び出しに一時退避できる設計にする。
- MCP は Google Drive / GitHub の外部文脈取得に限定する。
- Slack 文脈取得と返信は Slack MCP ではなく Slack Web API を直接使う。
- A2A は MVP では使わず、将来拡張として扱う。
- セキュリティは、MVP では Slack Private チャンネルを作成し、権限のある人だけを招待する Slack 側の権限制御を主軸にする。その上で、署名検証、最小権限、TTL、秘密情報の `.gitignore`、Guardrails / レビュー Agent による過剰露出抑制も記載する。

## AI-DLC Inception 成果物として作るもの

`aidlc-docs/` を作成し、少なくとも以下を含めてください。説明会資料では「全て含む必要はない」とされているが、書類審査で伝わりやすくするため網羅的に作成します。

1. `aidlc-state.md`
   - Inception フェーズ完了状態を明示する。
   - Intent、主要 Unit、主要リスク、次に Construction で実装する内容を短くまとめる。

2. `aidlc-docs/01_intent.md`
   - Business Intent
   - ハッカソンテーマとの接続
   - 対象ユーザー
   - 解決する業務課題
   - MVP で証明したい仮説

3. `aidlc-docs/02_requirements_analysis.md`
   - 機能要件
   - 非機能要件
   - 制約
   - MVP / Future の切り分け

4. `aidlc-docs/03_user_stories.md`
   - Persona ごとの user story
   - Acceptance criteria
   - 優先度

5. `aidlc-docs/04_unit_of_work_plan.md`
   - AI-DLC の Unit of Work を正しく定義する。
   - 本プロジェクトの Unit of Work は以下の4つにする。
     - Unit A: Slack起動・非同期ジョブ基盤
     - Unit B: AgentCore + Strands 補足生成パイプライン
     - Unit C: ナレッジ・MCP連携
     - Unit D: データ永続化・安全性・評価
   - 各Unitについて、目的、含まれるuser stories、主な成果物、依存関係、並行開発できる理由、受け入れ条件、リスク、測定基準を記載する。
   - 省略抽出 / 文脈取得 / 補足文生成 / リテラシーレビューは、Unit Bに含まれる Agent ステージとして説明する。

6. `aidlc-docs/05_application_design.md`
   - Diagram MCP生成図を参照して、AWS構成、Slackから返信までの流れ、MCP利用範囲、データ保存、セキュリティを記載する。
   - `docs/images/context-butler-aws-mcp-architecture.png` を参照する。

7. `aidlc-docs/06_prfaq.md`
   - PRFAQ形式で、このアプリが何を実現するか、誰に価値があるか、なぜ今作るのかを説明する。

8. `aidlc-docs/07_nfrs.md`
   - レイテンシ、可用性、セキュリティ、プライバシー、監視、コスト、運用性を整理する。

9. `aidlc-docs/08_risks.md`
   - 事実誤認、過剰補足、機密情報露出、Slack API権限不足、MCP接続複雑化、生成遅延、「ただの要約Bot」に見えるリスクを扱う。
   - それぞれに mitigation を書く。

10. `aidlc-docs/09_measurement_criteria.md`
    - 成功指標は定性評価を中心にする。
    - 定量評価として、あらかじめ用意したテストデータの「想定補足ポイント」に対して、生成結果がどれだけ満たしているかを測る。
    - 例: 想定補足ポイント充足率 80%以上、job成功率、3秒ack達成、デモ中の補足生成完了。
    - 手動修正回数は人によりばらつくため、主要指標にしない。

11. `aidlc-docs/10_suggested_bolts.md`
    - Construction に進むためのタスク分解を Unit ごとに Issue 化できる粒度で書く。
    - Slack基盤、AgentCore/Strands、Knowledge Bases、MCP、DynamoDB、Guardrails、評価データの作成を含める。

## README / docs の公開範囲

- README には環境変数の具体的な設定手順や内部デモ手順を載せない。
- README 末尾にチーム紹介は載せない。
- デモシナリオ、テストデータ、内部評価表、PDF資料は公開GitHubに載せない。
- 認証情報、OAuth token、`.env`、AWS credential、Slack signing secret、GitHub token、Google OAuth client secret は `.gitignore` に含める。

## 出力品質の条件

- 審査員が1分で「何を作るのか」「なぜ面白いのか」「AI-DLCとしてどう分解したのか」を理解できる。
- Unit of Work と実行時 Agent ステージを混同しない。
- Intent から Unit of Work へのトレーサビリティがある。
- MVPで動く範囲と将来拡張が分かれている。
- AWS / Slack / Bedrock / AgentCore / MCP の利用目的が明確。
- 書類審査の観点である Intent の明確さ、Unit分解の適切さ、創造性とテーマ適合性、ドキュメント品質に直接効く文章にする。
