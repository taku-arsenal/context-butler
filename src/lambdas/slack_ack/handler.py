"""
Lambda Ack Handler
Slack Interactivity Request を受け取り、3 秒以内に応答する。
生成 AI は呼ばない。署名検証・job 作成・SQS 投入のみ。
"""
import json
import logging
import os
import time
import uuid
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from urllib.parse import parse_qs

import boto3

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "ap-northeast-1"))
sqs = boto3.client("sqs", region_name=os.environ.get("AWS_REGION", "ap-northeast-1"))

JOBS_TABLE = os.environ.get("DYNAMODB_JOBS_TABLE", "explain_jobs")
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL", "")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")


def verify_slack_signature(body: str, timestamp: str, signature: str) -> bool:
    """
    Slack の署名を検証する。
    タイミング攻撃対策のため hmac.compare_digest を使用。
    """
    # タイムスタンプが 5 分以上古い場合はリジェクト（リプレイ攻撃対策）
    if abs(time.time() - int(timestamp)) > 60 * 5:
        logger.warning("Slack request timestamp is too old")
        return False

    sig_basestring = f"v0:{timestamp}:{body}"
    computed_signature = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode("utf-8"),
        sig_basestring.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed_signature, signature)


def handler(event: dict, context) -> dict:
    """
    Lambda Ack のメインハンドラ。
    3 秒以内に 200 OK を返す。
    """
    try:
        # ヘッダーの取得
        headers = event.get("headers", {})
        timestamp = headers.get("X-Slack-Request-Timestamp", headers.get("x-slack-request-timestamp", ""))
        signature = headers.get("X-Slack-Signature", headers.get("x-slack-signature", ""))
        body = event.get("body", "")

        # Slack 署名検証
        if not verify_slack_signature(body, timestamp, signature):
            logger.warning("Slack signature verification failed")
            return {"statusCode": 403, "body": "Forbidden"}

        # payload の parse
        parsed = parse_qs(body)
        payload_str = parsed.get("payload", ["{}"])[0]
        payload = json.loads(payload_str)

        # Message Shortcut か確認
        if payload.get("type") != "message_action":
            logger.info("Not a message action, ignoring")
            return {"statusCode": 200, "body": ""}

        callback_id = payload.get("callback_id", "")
        if callback_id != "explain_message":
            logger.info(f"Unknown callback_id: {callback_id}")
            return {"statusCode": 200, "body": ""}

        # job_id の生成
        job_id = str(uuid.uuid4())

        # メッセージ情報の抽出
        message = payload.get("message", {})
        channel = payload.get("channel", {})
        user = payload.get("user", {})
        team = payload.get("team", {})

        target_message_text = message.get("text", "")
        slack_message_ts = message.get("ts", "")
        slack_thread_ts = message.get("thread_ts", slack_message_ts)
        slack_channel_id = channel.get("id", "")
        slack_user_id = user.get("id", "")
        target_user_id = message.get("user", "")
        slack_team_id = team.get("id", "")

        # DynamoDB に job を保存
        now = datetime.now(timezone(timedelta(hours=9))).isoformat()
        ttl = int(time.time()) + 30 * 24 * 60 * 60  # 30 日後

        table = dynamodb.Table(JOBS_TABLE)
        table.put_item(
            Item={
                "job_id": job_id,
                "slack_team_id": slack_team_id,
                "slack_channel_id": slack_channel_id,
                "slack_message_ts": slack_message_ts,
                "slack_thread_ts": slack_thread_ts,
                "requested_by_user_id": slack_user_id,
                "target_user_id": target_user_id,
                "target_message_text": target_message_text,
                "status": "RECEIVED",
                "created_at": now,
                "updated_at": now,
                "ttl": ttl,
            }
        )

        # SQS に job を投入
        sqs_message = {
            "job_id": job_id,
            "slack_team_id": slack_team_id,
            "slack_channel_id": slack_channel_id,
            "slack_message_ts": slack_message_ts,
            "slack_thread_ts": slack_thread_ts,
            "requested_by_user_id": slack_user_id,
            "target_user_id": target_user_id,
            "target_message_text": target_message_text,
            "reader_profile": {
                "literacy_level": "standard",
                "audience_type": "engineer",
            },
        }

        sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(sqs_message, ensure_ascii=False),
            MessageGroupId=slack_channel_id,
            MessageDeduplicationId=job_id,
        )

        logger.info(json.dumps({"job_id": job_id, "event": "RECEIVED"}))

        # 3 秒以内に 200 OK を返す
        return {"statusCode": 200, "body": ""}

    except Exception as e:
        logger.error(f"Error in ack handler: {e}", exc_info=True)
        # エラーでも 200 を返す（Slack の再送を防ぐ）
        return {"statusCode": 200, "body": ""}
