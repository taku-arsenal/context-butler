"""
Slack API クライアント
"""
import logging
import os
from typing import Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


class SlackClientWrapper:
    """Slack API クライアントのラッパー"""

    def __init__(self, token: Optional[str] = None):
        self.client = WebClient(token=token or os.environ.get("SLACK_BOT_TOKEN", ""))

    def get_thread_messages(self, channel_id: str, thread_ts: str, limit: int = 20) -> list:
        """スレッドのメッセージを取得する"""
        try:
            response = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=limit,
            )
            return response.get("messages", [])
        except SlackApiError as e:
            logger.warning(f"Failed to get thread messages: {e.response['error']}")
            return []

    def get_channel_history(self, channel_id: str, limit: int = 50) -> list:
        """チャンネルの履歴を取得する"""
        try:
            response = self.client.conversations_history(
                channel=channel_id,
                limit=limit,
            )
            return response.get("messages", [])
        except SlackApiError as e:
            logger.warning(f"Failed to get channel history: {e.response['error']}")
            return []

    def post_message(self, channel_id: str, text: str, thread_ts: Optional[str] = None) -> bool:
        """メッセージを投稿する"""
        try:
            kwargs = {
                "channel": channel_id,
                "text": text,
                "mrkdwn": True,
            }
            if thread_ts:
                kwargs["thread_ts"] = thread_ts

            self.client.chat_postMessage(**kwargs)
            return True
        except SlackApiError as e:
            logger.error(f"Failed to post message: {e.response['error']}")
            return False

    def get_user_info(self, user_id: str) -> dict:
        """ユーザー情報を取得する"""
        try:
            response = self.client.users_info(user=user_id)
            return response.get("user", {})
        except SlackApiError as e:
            logger.warning(f"Failed to get user info: {e.response['error']}")
            return {}

    def open_modal(self, trigger_id: str, view: dict) -> bool:
        """モーダルを開く"""
        try:
            self.client.views_open(trigger_id=trigger_id, view=view)
            return True
        except SlackApiError as e:
            logger.error(f"Failed to open modal: {e.response['error']}")
            return False
