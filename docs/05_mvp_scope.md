# MVP スコープ

**プロジェクト名**: 説明補足AI（Explain Bot）  
**バージョン**: 1.0.0  
**作成日**: 2026-05-10

---

## 1. MVP の定義

MVP（Minimum Viable Product）は、ハッカソン予選でデモできる最小限の動作するプロダクトです。

**MVP の目標**: Slack の三点リーダから起動し、説明不足な投稿に対して補足文をスレッドに返信できること。

---

## 2. スコープ定義

### Must（必須 / MVP に含める）

| # | 機能 | 説明 |
|---|------|------|
| M-01 | Slack Message Shortcut 起動 | 三点リーダから「Explain with 説明補足AI」を呼び出せる |
| M-02 | Slack 3 秒以内 ack | Interactivity Request に 3 秒以内に応答する |
| M-03 | SQS 非同期化 | 生成 AI 処理を非同期で実行する |
| M-04 | 対象メッセージ取得 | Slack API で対象メッセージを取得する |
| M-05 | スレッド履歴取得 | Slack API でスレッド履歴を取得する |
| M-06 | 省略抽出 Agent | 省略点・必要文脈を構造化 JSON で抽出する |
| M-07 | 文脈取得 Agent（最小版） | Slack スレッドと社内ナレッジ KB から必要文脈を取得する |
| M-08 | 補足文生成 Agent | 背景・前提・次アクションを整理した補足文を生成する |
| M-09 | リテラシーレビュー Agent | 品質・安全性を確認し最終文を出力する |
| M-10 | AgentCore Runtime + Strands Orchestrator | MVP から 4 Agent ステージを順次制御する第一候補として利用する |
| M-11 | スレッド返信 | 元投稿のスレッドに補足文を返信する |
| M-12 | DynamoDB job 管理 | job の状態を DynamoDB で管理する |
| M-13 | README 整備 | GitHub に公開できる README を作成する |
| M-14 | AI-DLC Inception ドキュメント | 書類審査用の Inception ドキュメントを作成する |

### Should（できれば / 予選までに追加したい）

| # | 機能 | 説明 |
|---|------|------|
| S-01 | 文脈取得 Agent（強化版） | チャンネル要約・Drive・GitHub からの文脈取得を追加する |
| S-02 | Bedrock Knowledge Bases の改善 | 社内ナレッジ KB の検索精度を高める |
| S-03 | チャンネル履歴要約 | チャンネル履歴の要約を文脈取得に利用する |
| S-04 | ユーザーリテラシー設定 | DynamoDB でユーザーの役割・リテラシーを管理する |
| S-05 | Slack モーダル | 補足レベル・想定読者を選択できるモーダルを実装する |
| S-06 | CloudWatch ログ | Lambda・Agent のログを CloudWatch で確認できる |
| S-07 | Bedrock Guardrails | 出力フィルタリングを実装する |

### Could（余力があれば）

| # | 機能 | 説明 |
|---|------|------|
| C-01 | Google Drive MCP | Drive から議事録・仕様書を取得する |
| C-02 | GitHub MCP | GitHub から Issue・PR・README を取得する |
| C-03 | フィードバックボタン | 生成結果に「役に立った」「長すぎる」などのボタンを付ける |
| C-04 | チャンネル用語集 | チャンネルごとの用語集を管理する |
| C-05 | チャンネル履歴の定期要約 | EventBridge で定期的にチャンネル履歴を要約する |

### Won't for MVP（MVP では実装しない）

| # | 機能 | 理由 |
|---|------|------|
| W-01 | LINE 対応 | Slack に集中する |
| W-02 | Web 会議リアルタイム対応 | 実装難易度が高い |
| W-03 | Slack MCP | Slack API を直接使う |
| W-04 | A2A によるエージェント間通信 | MVP では Orchestrator 内部で完結させる |
| W-05 | 全社横断の大規模検索 | デモ用資料に限定する |
| W-06 | 完全自動のチャンネル履歴学習 | 手動設定で代替する |
| W-07 | 多言語対応 | 日本語のみ |

---

## 3. 実装フェーズ

### Phase 0: リポジトリ準備（書類審査前）

```
目標: GitHub リポジトリを公開できる状態にする

タスク:
  [ ] README.md 作成
  [ ] docs/ ディレクトリ作成
  [ ] AI-DLC Inception ドキュメント作成（docs/01_inception.md）
  [ ] アーキテクチャドキュメント作成（docs/03_architecture.md）
  [ ] 開発環境構築（Python 3.12 / CDK v2）
  [ ] IaC 方針決定（AWS CDK Python）
  [ ] .gitignore 設定
  [ ] .env.example 作成
```

### Phase 1: Slack App 最小実装

```
目標: Slack Message Shortcut から起動し、3 秒以内に ack できる

タスク:
  [ ] Slack App 作成（api.slack.com）
  [ ] Message Shortcut 設定
  [ ] Interactivity URL 設定
  [ ] API Gateway 作成（CDK）
  [ ] Lambda Ack 作成
      [ ] Slack 署名検証
      [ ] payload parse
      [ ] job_id 生成
      [ ] DynamoDB job 保存（RECEIVED）
      [ ] SQS 投入
      [ ] 200 OK 返却
  [ ] SQS FIFO 作成（CDK）
  [ ] Worker Lambda 作成（スケルトン）
  [ ] Slack 対象メッセージ取得
  [ ] Slack スレッド返信（ハードコードテキスト）
  [ ] DynamoDB テーブル作成（explain_jobs）
```

### Phase 2: 最小 AI 補足生成

```
目標: Bedrock を使って補足文を生成し、スレッドに返信できる

タスク:
  [ ] Bedrock 呼び出し実装
  [ ] 省略抽出プロンプト実装
  [ ] 文脈取得プロンプト実装（最小版: Slack スレッド + 社内ナレッジ KB）
  [ ] 補足文生成プロンプト実装
  [ ] リテラシーレビュープロンプト実装
  [ ] AgentCore Runtime + Strands Orchestrator の最小設定
  [ ] DynamoDB job 状態更新
  [ ] CloudWatch ログ整備
  [ ] エラーハンドリング
```

### Phase 3: AgentCore / Strands 構成化

```
目標: Strands Orchestrator で 4 Agent ステージを順次実行できる

タスク:
  [ ] 省略抽出 Agent 実装
  [ ] 文脈取得 Agent 実装（Slack スレッド + 社内ナレッジ KB）
  [ ] 補足文生成 Agent 実装
  [ ] リテラシーレビュー Agent 実装
  [ ] Strands Orchestrator 実装
  [ ] AgentCore Runtime 設定の安定化
  [ ] Agent 間データフロー実装
```

### Phase 4: 文脈取得強化

```
目標: KB・チャンネル要約を文脈取得に利用できる

タスク:
  [ ] スレッド履歴取得の完全実装
  [ ] チャンネル履歴要約の実装
  [ ] 社内ナレッジ KB 資料作成（Markdown）
  [ ] Bedrock Knowledge Bases 作成
  [ ] KB 検索の実装
  [ ] Drive MCP 実装（Could）
  [ ] GitHub MCP 実装（Could）
```

### Phase 5: UX 強化

```
目標: Slack モーダルでユーザーが設定を選択できる

タスク:
  [ ] Slack モーダル実装
  [ ] 補足レベル選択（かんたん / 標準 / 詳細）
  [ ] 想定読者選択（新人 / 非エンジニア / エンジニア / プロジェクトメンバー）
  [ ] 例示有無選択
  [ ] フィードバックボタン実装（Could）
  [ ] ユーザーリテラシー設定（DynamoDB）
```

### Phase 6: デモ・プレゼン準備

```
目標: ハッカソン予選でデモできる状態にする

タスク:
  [ ] デモ用 Slack 投稿を準備する
  [ ] デモ用 Drive 相当資料を準備する
  [ ] デモ用 GitHub Issue 相当データを準備する
  [ ] 社内ナレッジ KB 資料を準備する
  [ ] プレゼン資料を準備する
  [ ] README 最終整備
  [ ] 構成図最終整備
```

---

## 4. 優先順位マトリクス

```
高インパクト・低コスト（最優先）:
  - Slack Message Shortcut 起動
  - 3 秒以内 ack
  - 文脈取得 Agent 最小版（Slack スレッド + 社内ナレッジ KB）
  - 補足文生成 Agent
  - スレッド返信

高インパクト・高コスト（次に優先）:
  - AgentCore Runtime + Strands Orchestrator の安定化
  - Drive / GitHub MCP
  - Slack モーダル

低インパクト・低コスト（余力があれば）:
  - フィードバックボタン
  - チャンネル用語集

低インパクト・高コスト（MVP では不要）:
  - A2A
  - LINE 対応
  - Web 会議リアルタイム対応
```

---

## 5. デモ完成度の定義

### 予選デモの最低ライン（合格条件）

1. Slack の三点リーダから起動できる
2. 数秒後にスレッドに補足文が返信される
3. 補足文に背景・前提・次アクションが含まれる
4. Slack スレッドと社内ナレッジ KB を使った文脈取得が動く
5. AgentCore Runtime + Strands Orchestrator で 4 Agent ステージの処理ログを見せられる

### 予選デモの理想ライン

1. 上記に加えて
2. Slack モーダルで想定読者を選択できる
3. Drive・GitHub からの文脈取得を見せられる
4. フィードバックボタンが機能する

### 決勝デモの目標

1. AWS 上にデプロイされた動作するデモ
2. 複数の投稿パターンでデモできる
3. A2A 将来対応の設計を説明できる
4. ユーザーフィードバックによる品質改善を見せられる

---

## 6. MVP 評価方法

MVP の評価は、審査員に伝わる体験価値を重視した定性評価を中心にします。あわせて、事前に用意したテストデータごとの期待補足ポイントをどれだけ満たせたかを定量評価します。

| 評価項目 | 方法 | 目標 |
|---------|------|------|
| 理解しやすさ | デモ参加者が補足文を読んで元投稿の意図を説明できるか確認する | 大半の参加者が意図・背景・次アクションを説明できる |
| 役に立つ感 | 「この補足があれば追加質問が減るか」を定性評価する | 審査員に業務利用イメージが伝わる |
| テーマ適合 | 「説明責任をAIに外注する」面白さが伝わるか確認する | 「人をダメにする」テーマとの接続を説明できる |
| 想定補足ポイント充足率 | テストデータに期待補足ポイントを事前定義し、生成結果が何項目満たすか採点する | 80% 以上 |
| 事実・推測の分離 | 不明点を断定せず、根拠のある情報と分けているか確認する | 重大な根拠なし断定がない |

手動修正回数は評価者や文章の好みに左右されやすいため、MVP の主要指標にはしません。

---

## 7. リスクと対策

| リスク | 対策 |
|--------|------|
| Bedrock のレイテンシが高い | 軽い Agent は Haiku / Nova Lite を使う |
| Slack API のレート制限 | 必要最小限の API 呼び出しに絞る |
| AgentCore Runtime の設定が複雑 | MVP から利用することを第一候補にする。予選直前に詰まる場合のみ、Agent 入出力契約を保った Bedrock 直接呼び出しで継続する |
| MCP 接続が複雑 | MVP ではモックで代替 |
| デモ中に生成が遅い | 「生成中です」メッセージで UX を補完 |
| 社内ナレッジ KB が不十分 | Markdown 資料を事前に充実させる |
