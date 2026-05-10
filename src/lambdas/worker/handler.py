"""
Worker Lambda Handler
SQS から job を受け取り、Strands Orchestrator を起動して補足文を生成する。
"""
import json
import logging
import os
from datetime import datetime, timezone, timedelta

import boto3
from slack_sdk import WebClient

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "ap-northeast-1"))

JOBS_TABLE = os.environ.get("DYNAMODB_JOBS_TABLE", "explain_jobs")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")


def update_job_status(job_id: str, status: str, **kwargs):
    """job の状態を更新する"""
    table = dynamodb.Table(JOBS_TABLE)
    now = datetime.now(timezone(timedelta(hours=9))).isoformat()

    update_expression = "SET #status = :status, updated_at = :updated_at"
    expression_attribute_names = {"#status": "status"}
    expression_attribute_values = {":status": status, ":updated_at": now}

    for key, value in kwargs.items():
        update_expression += f", {key} = :{key}"
        expression_attribute_values[f":{key}"] = value

    table.update_item(
        Key={"job_id": job_id},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=expression_attribute_names,
        ExpressionAttributeValues=expression_attribute_values,
    )


def get_thread_history(client: WebClient, channel_id: str, thread_ts: str) -> list:
    """スレッド履歴を取得する"""
    try:
        response = client.conversations_replies(
            channel=channel_id,
            ts=thread_ts,
            limit=20,
        )
        return response.get("messages", [])
    except Exception as e:
        logger.warning(f"Failed to get thread history: {e}")
        return []


def post_supplement(client: WebClient, channel_id: str, thread_ts: str, message: str) -> None:
    """元投稿のスレッドに補足文を返信する"""
    client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text=message,
        mrkdwn=True,
    )


def handler(event: dict, context) -> None:
    """
    Worker Lambda のメインハンドラ。
    SQS から job を受け取り、補足文を生成してスレッドに返信する。
    """
    for record in event.get("Records", []):
        job_data = json.loads(record["body"])
        job_id = job_data["job_id"]

        try:
            logger.info(json.dumps({"job_id": job_id, "event": "PROCESSING_START"}))

            # Slack クライアントの初期化
            slack_client = WebClient(token=SLACK_BOT_TOKEN)

            # job 状態を更新
            update_job_status(job_id, "CONTEXT_FETCHING")

            # スレッド履歴の取得
            thread_messages = get_thread_history(
                slack_client,
                job_data["slack_channel_id"],
                job_data["slack_thread_ts"],
            )

            # Orchestrator の起動。AgentCore Runtime 化しても入出力契約は維持する。
            update_job_status(job_id, "GENERATING")

            from src.agents.orchestrator.orchestrator import run_orchestrator
            result = run_orchestrator(
                job_id=job_id,
                target_message=job_data["target_message_text"],
                thread_messages=thread_messages,
                channel_id=job_data["slack_channel_id"],
                reader_profile=job_data.get("reader_profile", {}),
            )

            final_message = result.get("final_message", "補足文の生成に失敗しました。")

            # Slack スレッドに返信
            post_supplement(
                slack_client,
                job_data["slack_channel_id"],
                job_data["slack_thread_ts"],
                final_message,
            )

            # job 状態を更新
            update_job_status(
                job_id,
                "POSTED",
                final_message=final_message,
            )

            logger.info(json.dumps({"job_id": job_id, "event": "POSTED"}))

        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}", exc_info=True)
            update_job_status(job_id, "FAILED", error_message=str(e))
            raise  # SQS の再試行を有効にするために例外を再送出
