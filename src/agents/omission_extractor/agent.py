"""
Stage 1: 省略抽出 Agent
対象 Slack 投稿から省略・暗黙知・不足情報を抽出する。
"""
import json
import logging
import os
from pathlib import Path

import boto3

logger = logging.getLogger(__name__)

bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("BEDROCK_REGION", "ap-northeast-1"))

# プロンプトファイルの読み込み
PROMPT_FILE = Path(__file__).parent.parent.parent.parent / "prompts" / "omission_extractor.md"


def load_system_prompt() -> str:
    """プロンプトファイルからシステムプロンプトを読み込む"""
    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text(encoding="utf-8")

    return """あなたは Slack 投稿の「省略・暗黙知・不足情報」を抽出する専門 AI です。

対象 Slack メッセージを読み、以下を抽出してください：
- 何が省略されているか
- 何が暗黙知になっているか
- 聞き手がどこで詰まりそうか
- 補足文生成のためにどの情報源を参照すべきか

重要な制約:
- 補足文を生成しない
- 発言者の意図を決めつけすぎない
- 「事実」「推測」「不足」を明確に分ける
- 構造化 JSON のみを返す
- 日本語で回答する

出力形式（JSON のみ）:
{
  "message_intent": "投稿の主な意図",
  "omitted_points": ["省略されている点1", "省略されている点2"],
  "implicit_knowledge": ["暗黙知になっている点1"],
  "required_context": ["補足に必要な文脈1"],
  "risk": "このままでは聞き手がどのような追加質問をする可能性があるか",
  "recommended_retrieval_plan": ["thread", "channel_summary", "kb", "github", "drive"],
  "confidence": 0.0
}"""


def run(target_message: str, thread_text: str, model_id: str) -> dict:
    """
    Stage 1: 省略抽出 Agent を実行する。

    Args:
        target_message: 対象 Slack メッセージ
        thread_text: スレッド履歴テキスト
        model_id: 使用する Bedrock モデル ID

    Returns:
        dict: 省略抽出結果
    """
    system_prompt = load_system_prompt()

    user_prompt = f"""以下の Slack 投稿を分析し、省略・暗黙知・不足情報を抽出してください。

## 対象投稿

{target_message}

## 直近の会話（参考）

{thread_text if thread_text else "（スレッドなし）"}

## 指示

上記の投稿から、聞き手が理解するために不足している情報を抽出してください。
補足文は生成しないでください。構造化 JSON のみを返してください。"""

    response = bedrock.invoke_model(
        modelId=model_id,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "temperature": 0.2,
        }),
        contentType="application/json",
        accept="application/json",
    )

    body = json.loads(response["body"].read())
    result_text = body["content"][0]["text"]

    # JSON の抽出
    try:
        # JSON ブロックを抽出
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        return json.loads(result_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Stage 1 output as JSON: {e}")
        # フォールバック
        return {
            "message_intent": "不明",
            "omitted_points": ["省略抽出に失敗しました"],
            "implicit_knowledge": [],
            "required_context": ["スレッド"],
            "risk": "省略抽出に失敗したため、補足文の品質が低下する可能性があります",
            "recommended_retrieval_plan": ["thread"],
            "confidence": 0.0,
        }
