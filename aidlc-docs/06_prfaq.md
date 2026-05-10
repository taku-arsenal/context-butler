# 06 PR/FAQ

**プロジェクト名**: Context Butler / 説明補足AI（Explain Bot）

---

## プレスリリース

### 「雑に言っても、AIが伝わる説明にしてくれる」— Context Butler、Slack の説明不足を自動補足

**2026 年 5 月 10 日**

Context Butler（説明補足AI）は、Slack 上の説明不足な投稿を、受け手が三点リーダから呼び出すだけで、AI が背景・前提・用語・判断理由・次アクションを補足してスレッドへ返信するアプリです。

業務チャットでは、発言者が背景・前提・判断理由を省いたまま投稿し、受け手が確認質問や認識合わせに時間を使うことが繰り返されています。「これ何の話？」「背景は？」「何をすればいい？」という追加質問は、非同期コミュニケーションの生産性を下げ、新人・途中参加者・非エンジニアを疎外します。

Context Butler は、Slack の三点リーダメニューから「Explain with 説明補足AI」を選択するだけで、4 つの Agent ステージ（省略抽出・文脈取得・補足文生成・リテラシーレビュー）を順次実行し、補足文をスレッドへ返信します。予選 MVP では Amazon Bedrock AgentCore Runtime + Strands Orchestrator の利用を第一候補とし、30 秒以内の生成を目標にします。

「説明責任」「文脈整理」「聞き手への配慮」を AI に外注することで、発言者は雑に投稿しても伝わり、受け手は追加質問を減らせます。AWS Summit Japan 2026 AI-DLC ハッカソンのテーマ「人をダメにする」を、業務効率化として成立させる切り口で実現します。

---

## FAQ

### Q1: Context Butler は何をするアプリですか？

Slack 上の説明不足な投稿を、受け手が三点リーダから呼び出すだけで、AI が補足してスレッドへ返信するアプリです。

補足文には以下が含まれます。

- この投稿の要点（何についての共有・依頼・確認か）
- 背景（なぜこの話が出ているか）
- 前提・対象範囲
- 用語説明（略語・専門用語）
- 判断理由（なぜこの判断になったか）
- 関連資料・Issue への言及
- 次に取るべき行動（誰が何をすべきか）
- 不確かな点（この投稿だけでは不明な点）

### Q2: 誰が使うアプリですか？

主に「受け手」が使います。分かりにくい投稿を見たとき、三点リーダから補足を呼び出します。

- プロジェクト途中参加者（過去の経緯が分からない）
- 新人メンバー（チームの暗黙知・略語が分からない）
- 非エンジニアのステークホルダー（技術的な投稿の意味が分からない）
- 忙しいマネージャー（追加質問する時間がない）

「投稿者」にとっても、雑に投稿しても AI が補足してくれるため、毎回丁寧に背景を書く手間を省けます。

### Q3: どのように動作しますか？

1. Slack で分かりにくい投稿を見る
2. 投稿の三点リーダ（…）から「Explain with 説明補足AI」を選択する
3. 3 秒以内に受付確認が返る
4. バックグラウンドで 4 つの Agent ステージが実行される
5. 元投稿のスレッドに補足文が自動投稿される

### Q4: どんな技術を使っていますか？

| 技術 | 用途 |
|------|------|
| Slack Message Shortcut | 起動 UX |
| Amazon API Gateway + Lambda | Slack Interactivity 受信・3 秒 ack |
| Amazon SQS FIFO | 非同期化・重複排除 |
| Amazon Bedrock AgentCore Runtime | Agent ホスティング |
| Strands Agents | Orchestrator + 4 Agent ステージの実装 |
| Amazon Bedrock（Claude / Nova） | LLM 推論 |
| Amazon Bedrock Knowledge Bases | 社内ナレッジ RAG |
| AgentCore Gateway + MCP | Google Drive / GitHub からの外部文脈取得 |
| Amazon DynamoDB | job 状態管理 |

### Q5: なぜ「人をダメにする」テーマに合うのですか？

通常、人は他者に伝わるように説明するために多くの努力をします。背景を整理し、前提を書き、関連資料を探し、専門用語を噛み砕き、聞き手の知識レベルを考慮します。

Context Butler は、これらの努力を AI に外注します。発言者は雑に投稿しても伝わり、受け手は追加質問を減らせます。人間の「説明する力」を弱らせ、人をダメにする — しかし業務効率化としては普通に便利で、実用性もある。そのギリギリのラインを攻めたプロダクトです。

### Q6: セキュリティはどう考えていますか？

MVP では以下の対策を取ります。

- **Slack Private チャンネル**: 権限のある参加者のみを招待し、Bot の投稿先をそのチャンネルに限定する
- **Slack 署名検証**: リプレイ攻撃・なりすましを防ぐ
- **最小権限**: Slack Bot スコープ・AWS IAM を必要最小限に絞る
- **TTL**: DynamoDB の job データを 30 日で自動削除し、Slack 本文を長期保存しない
- **過剰露出抑制**: Drive / GitHub 取得情報は要約のみ使用。リテラシーレビュー Agent + Guardrails で個人情報・機密情報をチェック
- **シークレット管理**: Slack Token・Signing Secret・GitHub Token は AWS Parameter Store で管理し、`.gitignore` に含める

### Q7: MVP で動く範囲はどこですか？

MVP（予選デモ）では以下が動きます。

- Slack Message Shortcut 起動 → 3 秒 ack → SQS 非同期化
- AgentCore Runtime + Strands Orchestrator で 4 Agent ステージを順次実行
- Bedrock Knowledge Bases（デモ用社内ナレッジ）を使った文脈取得
- 補足文生成 → リテラシーレビュー → スレッド返信
- DynamoDB job 状態管理

Google Drive MCP・GitHub MCP は MVP で実装を目指しますが、期間内に安定化できない場合は Future として扱い、Bedrock Knowledge Bases を使った文脈取得でデモを成立させます。Slack モーダルは Should として扱います。

### Q8: A2A は使いますか？

MVP では使いません。4 つの Agent ステージは同一 Strands Orchestrator 内部の処理単位であり、独立した外部 Agent 同士が通信する必要はありません。

将来、文脈取得 Agent を他アプリから再利用したい場合や、GitHub 調査 Agent・Drive 調査 Agent を別チームが管理する場合に A2A を採用します。

### Q9: なぜ今作るのですか？

Amazon Bedrock AgentCore Runtime が 2025 年に GA し、マルチエージェント構成を AWS 上で本番運用できる環境が整いました。Strands Agents により Python ベースで Agent パイプラインを簡潔に実装できるようになりました。

リモートワーク・非同期コミュニケーションの普及により、Slack 上の短い投稿が増加し、文脈不足による追加質問コストが顕在化しています。AWS Summit Japan 2026 AI-DLC ハッカソンが、AgentCore / MCP を活用した実用的な AI アプリを評価する場として最適なタイミングです。
