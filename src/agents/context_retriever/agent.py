"""
Unit 2: 文脈取得 Agent
省略抽出結果に基づき、補足文生成に必要な文脈を収集・整理する。
"""
import json
import logging
import os

import boto3

logger = logging.getLogger(__name__)

bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("BEDROCK_REGION", "ap-northeast-1"))
bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=os.environ.get("BEDROCK_REGION", "ap-northeast-1"))

KB_ID = os.environ.get("BEDROCK_KB_ID", "")


def search_knowledge_base(query: str, kb_id: str, max_results: int = 3) -> list:
    """Bedrock Knowledge Bases を検索する"""
    if not kb_id:
        return []
    try:
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {"numberOfResults": max_results}
            },
        )
        results = []
        for item in response.get("retrievalResults", []):
            results.append({
                "title": item.get("location", {}).get("s3Location", {}).get("uri", "不明"),
                "summary": item.get("content", {}).get("text", ""),
                "source": "knowledge_base",
                "relevance": item.get("score", 0.0),
            })
        return results
    except Exception as e:
        logger.warning(f"Knowledge Base search failed: {e}")
        return []


def run(
    omission_result: dict,
    target_message: str,
    thread_text: str,
    channel_id: str,
    model_id: str,
) -> dict:
    """
    Unit 2: 文脈取得 Agent を実行する。

    Args:
        omission_result: Unit 1 の出力
        target_message: 対象 Slack メッセージ
        thread_text: スレッド履歴テキスト
        channel_id: チャンネル ID
        model_id: 使用する Bedrock モデル ID

    Returns:
        dict: 文脈取得結果
    """
    retrieval_plan = omission_result.get("recommended_retrieval_plan", ["thread"])

    retrieved_context = {}
    missing_context = []

    # スレッド履歴の取得
    if "thread" in retrieval_plan and thread_text:
        retrieved_context["thread_summary"] = thread_text[:500]  # 最大 500 文字

    # Knowledge Base の検索
    if "kb" in retrieval_plan and KB_ID:
        kb_query = target_message[:200]  # クエリは最大 200 文字
        kb_results = search_knowledge_base(kb_query, KB_ID)
        if kb_results:
            retrieved_context["kb_context"] = kb_results
        else:
            missing_context.append("Knowledge Base から関連情報が見つかりませんでした")

    # TODO: GitHub MCP の実装
    if "github" in retrieval_plan:
        missing_context.append("GitHub 検索は現在未実装です（将来対応）")

    # TODO: Google Drive MCP の実装
    if "drive" in retrieval_plan:
        missing_context.append("Google Drive 検索は現在未実装です（将来対応）")

    # Bedrock で文脈を整理する
    system_prompt = """あなたは Slack 投稿の補足に必要な文脈を整理する専門 AI です。
収集した文脈を要約・整理し、補足文生成に必要な情報を構造化 JSON で返してください。
日本語で回答してください。"""

    user_prompt = f"""以下の情報を整理してください。

## 省略抽出結果
{json.dumps(omission_result, ensure_ascii=False, indent=2)}

## 収集した文脈
{json.dumps(retrieved_context, ensure_ascii=False, indent=2)}

## 取得できなかった情報
{json.dumps(missing_context, ensure_ascii=False)}

以下の JSON 形式で返してください：
{{
  "retrieved_context": {{
    "thread_summary": "スレッドの要約",
    "channel_summary": "チャンネルの概要",
    "kb_context": [],
    "github_context": [],
    "drive_context": []
  }},
  "confidence": 0.0,
  "missing_context": [],
  "retrieval_sources_used": []
}}"""

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

    try:
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        return json.loads(result_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Unit 2 output as JSON: {e}")
        return {
            "retrieved_context": retrieved_context,
            "confidence": 0.5,
            "missing_context": missing_context,
            "retrieval_sources_used": list(retrieved_context.keys()),
        }
