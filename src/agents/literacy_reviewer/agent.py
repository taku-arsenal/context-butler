"""
Stage 4: リテラシーレビュー Agent
補足文の品質・安全性を確認し、最終文を出力する。
"""
import json
import logging
import os

import boto3

logger = logging.getLogger(__name__)

bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("BEDROCK_REGION", "ap-northeast-1"))


def run(
    draft_message: str,
    target_message: str,
    omission_result: dict,
    retrieved_context: dict,
    reader_profile: dict,
    model_id: str,
) -> dict:
    """
    Stage 4: リテラシーレビュー Agent を実行する。

    Args:
        draft_message: Stage 3 の出力（補足文ドラフト）
        target_message: 対象 Slack メッセージ
        omission_result: Stage 1 の出力
        retrieved_context: Stage 2 の出力
        reader_profile: 読み手のリテラシー設定
        model_id: 使用する Bedrock モデル ID

    Returns:
        dict: レビュー結果（最終補足文を含む）
    """
    literacy_level = reader_profile.get("literacy_level", "standard")
    audience_type = reader_profile.get("audience_type", "engineer")
    missing_context = retrieved_context.get("missing_context", [])

    system_prompt = """あなたは Slack 投稿の補足文をレビューする専門 AI です。

生成された補足文をレビューし、以下を確認してください：
1. 初見の人に伝わるか
2. 専門用語が多すぎないか（想定読者に合っているか）
3. 必要な用語説明があるか
4. 発言者の意図を変えていないか
5. 補足しすぎていないか
6. 事実と推測が混ざっていないか
7. 根拠がない断定をしていないか
8. Slack のスレッド返信として自然か
9. 失礼な表現になっていないか
10. 機密情報を過剰に出していないか
11. 個人情報を含んでいないか

出力形式（JSON のみ）:
{
  "approved": true/false,
  "final_message": "最終的な Slack 投稿文",
  "review_comments": ["レビューコメント1"],
  "risk_level": "low / medium / high",
  "modifications_made": ["修正内容1"]
}

修正の方針:
- 軽微な問題は自動修正する
- 重大な問題（事実誤認、機密情報の露出）は approved: false にする
- 不明点は「この投稿だけでは明記されていません」に統一する
- 日本語で回答する"""

    user_prompt = f"""以下の補足文をレビューし、Slack に投稿できる品質かを確認してください。

## 補足文ドラフト

{draft_message}

## 対象投稿

{target_message}

## 省略抽出結果（参考）

{json.dumps(omission_result, ensure_ascii=False, indent=2)}

## 取得できなかった情報（参考）

{json.dumps(missing_context, ensure_ascii=False)}

## 読み手の情報

- リテラシーレベル: {literacy_level}
- 想定読者タイプ: {audience_type}

## 指示

上記の補足文をレビューし、問題があれば修正してください。
最終的な Slack 投稿文を JSON 形式で返してください。"""

    response = bedrock.invoke_model(
        modelId=model_id,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
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
        logger.error(f"Failed to parse Stage 4 output as JSON: {e}")
        # フォールバック: ドラフトをそのまま返す
        return {
            "approved": True,
            "final_message": draft_message,
            "review_comments": ["レビュー結果の解析に失敗しました。ドラフトをそのまま使用します。"],
            "risk_level": "medium",
            "modifications_made": [],
        }
