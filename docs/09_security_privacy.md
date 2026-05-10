# セキュリティ・プライバシー設計

**プロジェクト名**: 説明補足AI（Explain Bot）  
**バージョン**: 1.0.0  
**作成日**: 2026-05-10

---

## 1. Slack 署名検証

### 概要

Slack からのリクエストが正規のものかを検証します。悪意のある第三者が API Gateway のエンドポイントに直接リクエストを送ることを防ぎます。

### 検証方法

Lambda Ack で以下を検証します：

1. `X-Slack-Request-Timestamp` ヘッダーの存在確認
2. タイムスタンプが現在時刻から 5 分以内であることを確認（リプレイ攻撃対策）
3. `X-Slack-Signature` ヘッダーの存在確認
4. 署名の計算と比較

```python
import hmac
import hashlib
import time

def verify_slack_signature(
    signing_secret: str,
    body: str,
    timestamp: str,
    signature: str
) -> bool:
    """
    Slack の署名を検証する
    
    セキュリティ考慮事項:
    - タイムスタンプ検証でリプレイ攻撃を防ぐ
    - hmac.compare_digest でタイミング攻撃を防ぐ
    """
    # タイムスタンプが 5 分以上古い場合はリジェクト
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False
    
    # 署名の計算
    sig_basestring = f"v0:{timestamp}:{body}"
    computed_signature = "v0=" + hmac.new(
        signing_secret.encode("utf-8"),
        sig_basestring.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    # タイミング攻撃対策のため hmac.compare_digest を使用
    return hmac.compare_digest(computed_signature, signature)
```

### 署名検証の失敗時

署名検証に失敗した場合は、即座に `403 Forbidden` を返します。ログにはエラーを記録しますが、詳細なエラーメッセージは返しません。

```python
if not verify_slack_signature(...):
    logger.warning("Slack signature verification failed", extra={"ip": source_ip})
    return {"statusCode": 403, "body": "Forbidden"}
```

---

## 2. 最小権限の原則

### Slack Bot スコープ

必要最小限のスコープのみを付与します。

| スコープ | 用途 | 必要性 |
|---------|------|--------|
| `chat:write` | スレッドへの返信 | 必須 |
| `groups:history` | Private チャンネルの対象メッセージ・スレッド履歴取得 | MVP 必須 |
| `users:read` | 投稿者や依頼者の表示名取得 | 必要な場合のみ |
| `channels:history` | パブリックチャンネル履歴取得 | MVP では不要。公開チャンネル対応時のみ追加 |
| `im:history` | DM 履歴取得 | 任意（MVP では不要） |

**使わないスコープは付与しない。**

### MVP の Slack 権限境界

MVP デモでは、Explain Bot を権限のある参加者のみを招待した Slack Private チャンネルに追加します。この Private チャンネルを情報共有の境界とし、Bot はそのチャンネル内の対象メッセージ・スレッド・デモ用ナレッジだけを扱います。

- デモ用 Private チャンネルに参加していないユーザーには補足結果を見せない
- 本番資料ではなく、デモ用に用意した KB / Drive / GitHub 相当データを利用する
- パブリックチャンネル、DM、全社横断検索は MVP 対象外にする
- 本番化時にのみ、Drive / GitHub のユーザー権限と Slack チャンネル参加者の権限連動を設計する

### AWS IAM ポリシー

各 Lambda 関数に最小権限の IAM ロールを付与します。

#### Lambda Ack の IAM ポリシー

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:UpdateItem"
      ],
      "Resource": "arn:aws:dynamodb:ap-northeast-1:*:table/explain_jobs"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage"
      ],
      "Resource": "arn:aws:sqs:ap-northeast-1:*:explain-jobs.fifo"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter"
      ],
      "Resource": "arn:aws:ssm:ap-northeast-1:*:parameter/explain-bot/*"
    }
  ]
}
```

#### Lambda Worker の IAM ポリシー

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:ap-northeast-1:*:table/explain_jobs",
        "arn:aws:dynamodb:ap-northeast-1:*:table/user_profiles",
        "arn:aws:dynamodb:ap-northeast-1:*:table/channel_contexts"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ],
      "Resource": "arn:aws:sqs:ap-northeast-1:*:explain-jobs.fifo"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:Retrieve"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::explain-bot-*/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter"
      ],
      "Resource": "arn:aws:ssm:ap-northeast-1:*:parameter/explain-bot/*"
    }
  ]
}
```

---

## 3. データ保存とプライバシー

### DynamoDB の TTL 設定

DynamoDB に保存する job 情報には TTL を設定し、自動削除します。

| テーブル | TTL | 理由 |
|---------|-----|------|
| `explain_jobs` | 30 日 | Slack 本文を長期保存しない |
| `user_profiles` | なし | ユーザー設定は継続利用 |
| `channel_contexts` | 90 日 | チャンネル文脈は定期更新 |
| `feedback` | 180 日 | 品質改善に利用後は削除 |

**デモ用**: TTL を 7 日に短縮してもよい。

### Slack 本文の取り扱い

- Slack メッセージのテキストは DynamoDB に保存するが、TTL で自動削除する
- 長期的な分析・学習には使用しない（MVP では）
- ログには Slack 本文を含めない（job_id のみ記録）

### 取得文脈の取り扱い

- Drive / GitHub から取得した情報は DynamoDB に一時保存するが、TTL で削除する
- 取得した情報をそのまま Slack に貼らない（要約・抽象化する）
- MVP では、権限のある参加者のみを招待した Private チャンネルに投稿先を限定する
- 本番化時は、投稿先チャンネルの参加者と取得元データの権限が一致しない場合、該当情報を補足文に含めない

---

## 4. 個人情報の保護

### Slack 投稿に含まれる個人情報

Slack 投稿には個人名・メールアドレス・電話番号などが含まれる可能性があります。

#### 対策

1. **Bedrock Guardrails**: 個人情報の過剰出力をフィルタリング
2. **リテラシーレビュー Agent**: 個人情報が含まれていないかチェック
3. **出力の抽象化**: 個人名は「担当者」「投稿者」などに置き換える

#### Bedrock Guardrails の設定（任意）

```python
# Guardrails の適用
response = bedrock.apply_guardrail(
    guardrailIdentifier="explain-bot-guardrail",
    guardrailVersion="DRAFT",
    source="OUTPUT",
    content=[
        {
            "text": {
                "text": draft_message
            }
        }
    ]
)

if response["action"] == "GUARDRAIL_INTERVENED":
    # Guardrails が介入した場合の処理
    logger.warning("Guardrails intervened", extra={"job_id": job_id})
    # 安全な代替メッセージを使用
```

---

## 5. 機密情報の保護

### Drive / GitHub からの情報取得

Drive / GitHub から取得した情報には機密情報が含まれる可能性があります。

#### 対策

1. **MVP ではデモ用資料に限定**: 本番の機密情報を含む資料は使わない
2. **Slack Private チャンネルで制御**: 権限のある参加者のみをチャンネルに招待し、Bot の投稿先をそのチャンネルに限定する
3. **要約・抽象化**: 取得した情報をそのまま貼らず、要約して使用する
4. **本番化時の権限確認**: 対象ユーザーまたはアプリのアクセス権限、投稿先チャンネルの参加者に基づいて取得・出力を制御する

#### 本番化時の追加対策

- OAuth トークンの安全な管理（Secrets Manager）
- Token Vault の導入
- アクセスログの記録
- 定期的な権限レビュー

---

## 6. 事実と推測の分離

AI が推測した内容を断定しないことは、セキュリティ・プライバシーだけでなく、情報の正確性の観点からも重要です。

### 実装方針

1. **Unit 1（省略抽出）**: 「事実」「推測」「不足」を明確に分ける
2. **Unit 3（補足文生成）**: 取得した文脈から確認できることのみ断定する
3. **Unit 4（リテラシーレビュー）**: 根拠のない断定がないかチェックする

### 出力例

```
✅ 良い例:
「先週の定例議事録（2026-05-03）では、認証基盤を AWS 側に寄せる方針が合意されています。」

❌ 悪い例:
「おそらく Cognito への移行が決まったのでしょう。」

✅ 不明点の明示:
「本番適用の具体的な日程は、この投稿とスレッドだけでは明記されていません。」
```

---

## 7. シークレット管理

### AWS Secrets Manager / Parameter Store の使用

Slack トークンなどのシークレットは環境変数に直接設定せず、AWS Secrets Manager または Parameter Store で管理します。

```python
import boto3

def get_secret(parameter_name: str) -> str:
    """
    Parameter Store からシークレットを取得する
    """
    ssm = boto3.client("ssm", region_name="ap-northeast-1")
    response = ssm.get_parameter(
        Name=parameter_name,
        WithDecryption=True
    )
    return response["Parameter"]["Value"]

# 使用例
SLACK_BOT_TOKEN = get_secret("/explain-bot/slack-bot-token")
SLACK_SIGNING_SECRET = get_secret("/explain-bot/slack-signing-secret")
```

### Parameter Store の構成

```
/explain-bot/
├── slack-bot-token          # Slack Bot Token (SecureString)
├── slack-signing-secret     # Slack Signing Secret (SecureString)
├── bedrock-kb-id            # Knowledge Base ID (String)
└── github-token             # GitHub Token (SecureString, 将来対応)
```

---

## 8. ネットワークセキュリティ

### API Gateway

- HTTPS のみ許可（HTTP は自動リダイレクト）
- WAF の導入を検討（本番化時）
- レート制限の設定

### Lambda

- VPC 内に配置することを推奨（本番化時）
- VPC エンドポイントで DynamoDB・S3・Bedrock に接続
- NAT Gateway 経由で Slack API に接続

### DynamoDB / S3

- VPC エンドポイントを使用
- パブリックアクセスをブロック
- サーバーサイド暗号化を有効化

---

## 9. 監査ログ

### CloudWatch Logs

すべての Lambda 関数のログを CloudWatch Logs に記録します。

```python
import logging
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def log_job_event(job_id: str, event: str, details: dict = None):
    """
    job イベントをログに記録する
    注意: Slack 本文などの機密情報はログに含めない
    """
    log_entry = {
        "job_id": job_id,
        "event": event,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if details:
        log_entry["details"] = details
    
    logger.info(json.dumps(log_entry, ensure_ascii=False))
```

### ログに含めるもの

- job_id
- イベント種別（RECEIVED / CONTEXT_FETCHING / GENERATING / REVIEWING / POSTED / FAILED）
- 処理時間
- エラーメッセージ（エラー時のみ）

### ログに含めないもの

- Slack メッセージの本文
- ユーザーの個人情報
- Drive / GitHub から取得した内容
- Slack トークン・署名シークレット

---

## 10. セキュリティチェックリスト

### MVP 時点での確認事項

- [ ] Slack 署名検証が実装されている
- [ ] Slack Bot スコープが最小権限になっている
- [ ] AWS IAM ポリシーが最小権限になっている
- [ ] DynamoDB に TTL が設定されている
- [ ] シークレットが Parameter Store / Secrets Manager で管理されている
- [ ] CloudWatch Logs にログが記録されている
- [ ] ログに機密情報が含まれていない

### 本番化時の追加確認事項

- [ ] WAF の導入
- [ ] VPC 内への Lambda 配置
- [ ] VPC エンドポイントの設定
- [ ] Bedrock Guardrails の有効化
- [ ] OAuth トークン管理の強化
- [ ] 定期的な権限レビュー
- [ ] セキュリティインシデント対応手順の整備
