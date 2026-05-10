# Slack App 設計・設定手順

**プロジェクト名**: 説明補足AI（Explain Bot）  
**バージョン**: 1.0.0  
**作成日**: 2026-05-10

---

## 1. Slack App の概要

| 項目 | 値 |
|------|-----|
| App 名 | 説明補足AI（Explain Bot） |
| 起動方法 | Message Shortcut（三点リーダメニュー） |
| 返信方法 | 元投稿のスレッドに返信 |
| Bot 名 | @explain-bot |

---

## 2. Slack App 作成手順

### 2.1 App の作成

1. [https://api.slack.com/apps](https://api.slack.com/apps) にアクセス
2. 「Create New App」をクリック
3. 「From scratch」を選択
4. App Name: `説明補足AI`（または `Explain Bot`）
5. Workspace を選択
6. 「Create App」をクリック

### 2.2 Basic Information の確認

以下の情報を控えておく：

- **App ID**: `A...`
- **Client ID**: `...`
- **Client Secret**: `...`
- **Signing Secret**: `...`（Lambda Ack での署名検証に使用）

---

## 3. Bot Token Scopes の設定

「OAuth & Permissions」→「Scopes」→「Bot Token Scopes」で以下を追加：

### 必須スコープ

| スコープ | 用途 |
|---------|------|
| `chat:write` | スレッドに補足文を返信する |
| `groups:history` | MVP デモ用 Private チャンネルの対象メッセージ・スレッド履歴を取得する |

### 任意スコープ（Should）

| スコープ | 用途 |
|---------|------|
| `users:read` | 投稿者や依頼者の表示名を取得する |
| `team:read` | ワークスペース情報を取得する |
| `links:read` | リンクのメタデータを取得する |
| `channels:history` | パブリックチャンネル対応を追加する場合に利用する |

### 使わないスコープ

| スコープ | 理由 |
|---------|------|
| `app_mentions:read` | メンション起動は MVP では使わない |
| `files:read` | MVP では不要 |
| `channels:read` | 必要になったら追加 |
| `im:history` | DM 対応は MVP では行わない |
| `mpim:history` | グループ DM 対応は MVP では行わない |
| `commands` | Message Shortcut 起動のため Slash コマンドは使わない |

**方針**: MVP は権限のある参加者のみを招待した Private チャンネルで実施し、最小権限で設計する。必要になったスコープのみ追加する。

---

## 4. Message Shortcut の設定

「Interactivity & Shortcuts」→「Shortcuts」→「Create New Shortcut」

| 項目 | 値 |
|------|-----|
| Where the shortcut appears | Messages |
| Name | Explain with 説明補足AI |
| Short Description | AIが背景・前提・次アクションを補足します |
| Callback ID | `explain_message` |

**Callback ID は Lambda Ack での識別に使用します。**

---

## 5. Interactivity の設定

「Interactivity & Shortcuts」→「Interactivity」を ON にする

| 項目 | 値 |
|------|-----|
| Request URL | `https://{api-gateway-id}.execute-api.ap-northeast-1.amazonaws.com/prod/slack/interactivity` |

**CDK デプロイ後に API Gateway の URL を設定してください。**

---

## 6. App のインストール

「OAuth & Permissions」→「Install to Workspace」をクリック

インストール後、以下を控えておく：

- **Bot User OAuth Token**: `xoxb-...`（Worker Lambda での Slack API 呼び出しに使用）

---

## 7. Slack 3 秒制約への対応

Slack の Interactivity Request は **3 秒以内に応答** する必要があります。

### 非同期処理の構成

```
Slack Interactivity Request
        │
        ▼
  API Gateway
        │
        ▼
  Lambda Ack（3 秒以内に 200 OK を返す）
  ┌─────────────────────────────────────┐
  │ 1. Slack 署名検証                   │
  │ 2. payload parse                    │
  │ 3. Message Shortcut か確認          │
  │ 4. job_id 生成                      │
  │ 5. DynamoDB に job 保存（RECEIVED） │
  │ 6. SQS FIFO に投入                  │
  │ 7. 200 OK を返す                    │
  └─────────────────────────────────────┘
        │
        ▼（非同期）
  SQS FIFO
        │
        ▼
  Worker Lambda（生成 AI 処理）
        │
        ▼
  Slack Thread Reply
```

### Lambda Ack での応答例

```python
# 即時 ack（モーダルなし）
return {
    "statusCode": 200,
    "body": ""
}

# 「生成中です」メッセージを返す場合
# chat.postMessage を使って一時メッセージを投稿
slack_client.chat_postMessage(
    channel=channel_id,
    thread_ts=message_ts,
    text="補足を生成中です... :hourglass_flowing_sand:"
)
```

---

## 8. Slack 署名検証

Lambda Ack では、Slack からのリクエストが正規のものかを検証します。

```python
import hmac
import hashlib
import time

def verify_slack_signature(signing_secret: str, body: str, timestamp: str, signature: str) -> bool:
    """
    Slack の署名を検証する
    
    Args:
        signing_secret: Slack App の Signing Secret
        body: リクエストボディ（生の文字列）
        timestamp: X-Slack-Request-Timestamp ヘッダーの値
        signature: X-Slack-Signature ヘッダーの値
    
    Returns:
        bool: 署名が正しければ True
    """
    # タイムスタンプが 5 分以上古い場合はリジェクト（リプレイ攻撃対策）
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False
    
    # 署名の計算
    sig_basestring = f"v0:{timestamp}:{body}"
    computed_signature = "v0=" + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # タイミング攻撃対策のため hmac.compare_digest を使用
    return hmac.compare_digest(computed_signature, signature)
```

---

## 9. Slack API の使用方法

### 対象メッセージの取得

Message Shortcut の payload から対象メッセージを取得します。

```python
def extract_target_message(payload: dict) -> dict:
    """
    Message Shortcut の payload から対象メッセージを抽出する
    """
    message = payload.get("message", {})
    return {
        "text": message.get("text", ""),
        "ts": message.get("ts", ""),
        "user": message.get("user", ""),
        "channel": payload.get("channel", {}).get("id", ""),
        "thread_ts": message.get("thread_ts", message.get("ts", "")),
    }
```

### スレッド履歴の取得

```python
from slack_sdk import WebClient

def get_thread_history(client: WebClient, channel_id: str, thread_ts: str) -> list:
    """
    スレッド履歴を取得する
    """
    response = client.conversations_replies(
        channel=channel_id,
        ts=thread_ts,
        limit=20  # 最大 20 件
    )
    return response.get("messages", [])
```

### 補足文の返信

```python
def post_supplement(client: WebClient, channel_id: str, thread_ts: str, message: str) -> None:
    """
    元投稿のスレッドに補足文を返信する
    """
    client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text=message,
        mrkdwn=True  # Slack マークダウンを有効にする
    )
```

---

## 10. Slack モーダル（Should）

### モーダルの表示

Message Shortcut 選択後にモーダルを表示する場合：

```python
def open_modal(client: WebClient, trigger_id: str, job_id: str) -> None:
    """
    補足設定モーダルを表示する
    """
    client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "callback_id": "explain_modal",
            "private_metadata": job_id,
            "title": {"type": "plain_text", "text": "説明補足AI"},
            "submit": {"type": "plain_text", "text": "補足を生成"},
            "close": {"type": "plain_text", "text": "キャンセル"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "補足の設定を選択してください。"
                    }
                },
                {
                    "type": "input",
                    "block_id": "literacy_level",
                    "label": {"type": "plain_text", "text": "補足レベル"},
                    "element": {
                        "type": "static_select",
                        "action_id": "select_literacy",
                        "placeholder": {"type": "plain_text", "text": "選択してください"},
                        "options": [
                            {"text": {"type": "plain_text", "text": "かんたん"}, "value": "simple"},
                            {"text": {"type": "plain_text", "text": "標準"}, "value": "standard"},
                            {"text": {"type": "plain_text", "text": "詳細"}, "value": "detailed"},
                        ],
                        "initial_option": {"text": {"type": "plain_text", "text": "標準"}, "value": "standard"}
                    }
                },
                {
                    "type": "input",
                    "block_id": "audience_type",
                    "label": {"type": "plain_text", "text": "想定読者"},
                    "element": {
                        "type": "static_select",
                        "action_id": "select_audience",
                        "placeholder": {"type": "plain_text", "text": "選択してください"},
                        "options": [
                            {"text": {"type": "plain_text", "text": "新人"}, "value": "new_member"},
                            {"text": {"type": "plain_text", "text": "非エンジニア"}, "value": "non_engineer"},
                            {"text": {"type": "plain_text", "text": "エンジニア"}, "value": "engineer"},
                            {"text": {"type": "plain_text", "text": "プロジェクトメンバー"}, "value": "project_member"},
                        ],
                        "initial_option": {"text": {"type": "plain_text", "text": "エンジニア"}, "value": "engineer"}
                    }
                },
                {
                    "type": "input",
                    "block_id": "include_examples",
                    "label": {"type": "plain_text", "text": "例示を含める"},
                    "element": {
                        "type": "static_select",
                        "action_id": "select_examples",
                        "options": [
                            {"text": {"type": "plain_text", "text": "あり"}, "value": "true"},
                            {"text": {"type": "plain_text", "text": "なし"}, "value": "false"},
                        ],
                        "initial_option": {"text": {"type": "plain_text", "text": "なし"}, "value": "false"}
                    }
                }
            ]
        }
    )
```

---

## 11. 環境変数

Lambda 関数で使用する環境変数：

| 変数名 | 説明 | 例 |
|--------|------|-----|
| `SLACK_BOT_TOKEN` | Bot User OAuth Token | `xoxb-...` |
| `SLACK_SIGNING_SECRET` | Signing Secret | `abc123...` |
| `SQS_QUEUE_URL` | SQS FIFO の URL | `https://sqs.ap-northeast-1.amazonaws.com/...` |
| `DYNAMODB_JOBS_TABLE` | explain_jobs テーブル名 | `explain_jobs` |
| `DYNAMODB_USERS_TABLE` | user_profiles テーブル名 | `user_profiles` |
| `DYNAMODB_CHANNELS_TABLE` | channel_contexts テーブル名 | `channel_contexts` |
| `BEDROCK_KB_ID` | Knowledge Bases の ID | `abc123...` |
| `BEDROCK_REGION` | Bedrock のリージョン | `ap-northeast-1` |
| `BEDROCK_MODEL_HAIKU` | Haiku モデル ID | `anthropic.claude-3-5-haiku-20241022-v1:0` |
| `BEDROCK_MODEL_SONNET` | Sonnet モデル ID | `anthropic.claude-3-5-sonnet-20241022-v2:0` |

**注意**: 環境変数は AWS Secrets Manager または Parameter Store で管理することを推奨します。Lambda の環境変数に直接設定する場合は、暗号化を有効にしてください。
