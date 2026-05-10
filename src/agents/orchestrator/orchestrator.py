"""
Strands Orchestrator
4 つの専門 Agent を順次制御する。
"""
import json
import logging
import os
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("BEDROCK_REGION", "ap-northeast-1"))

MODEL_HAIKU = os.environ.get("BEDROCK_MODEL_HAIKU", "anthropic.claude-3-5-haiku-20241022-v1:0")
MODEL_SONNET = os.environ.get("BEDROCK_MODEL_SONNET", "anthropic.claude-3-5-sonnet-20241022-v2:0")


def invoke_bedrock(model_id: str, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
    """Bedrock を呼び出す"""
    response = bedrock.invoke_model(
        modelId=model_id,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "temperature": temperature,
        }),
        contentType="application/json",
        accept="application/json",
    )
    body = json.loads(response["body"].read())
    return body["content"][0]["text"]


def run_orchestrator(
    job_id: str,
    target_message: str,
    thread_messages: list,
    channel_id: str,
    reader_profile: Optional[dict] = None,
) -> dict:
    """
    4 Unit の Agent を順次実行する。

    Args:
        job_id: ジョブ ID
        target_message: 対象 Slack メッセージ
        thread_messages: スレッド履歴
        channel_id: チャンネル ID
        reader_profile: 読み手のリテラシー設定

    Returns:
        dict: 最終補足文とレビュー結果
    """
    if reader_profile is None:
        reader_profile = {"literacy_level": "standard", "audience_type": "engineer"}

    logger.info(json.dumps({"job_id": job_id, "event": "ORCHESTRATOR_START"}))

    # スレッド履歴のフォーマット
    thread_text = "\n".join([
        f"[{msg.get('user', 'unknown')}]: {msg.get('text', '')}"
        for msg in thread_messages[:10]  # 最大 10 件
    ])

    # Unit 1: 省略抽出 Agent
    logger.info(json.dumps({"job_id": job_id, "event": "UNIT1_START"}))
    from src.agents.omission_extractor.agent import run as run_unit1
    omission_result = run_unit1(
        target_message=target_message,
        thread_text=thread_text,
        model_id=MODEL_HAIKU,
    )
    logger.info(json.dumps({"job_id": job_id, "event": "UNIT1_DONE"}))

    # Unit 2: 文脈取得 Agent
    logger.info(json.dumps({"job_id": job_id, "event": "UNIT2_START"}))
    from src.agents.context_retriever.agent import run as run_unit2
    retrieved_context = run_unit2(
        omission_result=omission_result,
        target_message=target_message,
        thread_text=thread_text,
        channel_id=channel_id,
        model_id=MODEL_HAIKU,
    )
    logger.info(json.dumps({"job_id": job_id, "event": "UNIT2_DONE"}))

    # Unit 3: 補足文生成 Agent
    logger.info(json.dumps({"job_id": job_id, "event": "UNIT3_START"}))
    from src.agents.supplement_composer.agent import run as run_unit3
    draft_message = run_unit3(
        target_message=target_message,
        omission_result=omission_result,
        retrieved_context=retrieved_context,
        reader_profile=reader_profile,
        model_id=MODEL_SONNET,
    )
    logger.info(json.dumps({"job_id": job_id, "event": "UNIT3_DONE"}))

    # Unit 4: リテラシーレビュー Agent
    logger.info(json.dumps({"job_id": job_id, "event": "UNIT4_START"}))
    from src.agents.literacy_reviewer.agent import run as run_unit4
    review_result = run_unit4(
        draft_message=draft_message,
        target_message=target_message,
        omission_result=omission_result,
        retrieved_context=retrieved_context,
        reader_profile=reader_profile,
        model_id=MODEL_SONNET,
    )
    logger.info(json.dumps({"job_id": job_id, "event": "UNIT4_DONE"}))

    logger.info(json.dumps({"job_id": job_id, "event": "ORCHESTRATOR_DONE"}))

    return {
        "final_message": review_result.get("final_message", draft_message),
        "omission_result": omission_result,
        "retrieved_context": retrieved_context,
        "review_result": review_result,
    }
