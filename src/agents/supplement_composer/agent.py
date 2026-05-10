"""
Unit 3: 補足文生成 Agent
対象投稿に対する補足説明を生成する。
"""
import json
import logging
import os

import boto3

logger = logging.getLogger(__name__)

bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("BEDROCK_REGION", "ap-northeast-1"))


def run(
    target_message: str,
    omission_result: dict,
    retrieved_context: dict,
    reader_profile: dict,
    model_id: str,
) -> str:
    """
    Unit 3: 補足文生成 Agent を実行する。

    Args:
        target_message: 対象 Slack メッセージ
        omission_result: Unit 1 の出力
        retrieved_context: Unit 2 の出力
        reader_profile: 読み手のリテラシー設定
        model_id: 使用する Bedrock モデル ID

    Returns:
        str: 補足文ドラフト
    """
    literacy_level = reader_profile.get("literacy_level", "standard")
    audience_type = reader_profile.get("audience_type", "engineer")

    system_prompt = """あなたは Slack 投稿の補足説明を生成する専門 AI です。

対象投稿に対して、聞き手が追加質問しなくても理解できる補足説明を生成してください。

補足文の構成（必要なものだけ含める）:
1. 冒頭: 「補足です。この投稿は〜についての[共有/依頼/確認/報告]です。」
2. 背景: なぜこの話が出ているか
3. 対象範囲 / 前提: 何が対象で何が対象外か
4. 用語説明: 略語・専門用語の説明（必要な場合のみ）
5. 確認すべき人: 誰が何をすべきか（依頼の場合）
6. 次に取るべき行動: 具体的なアクション
7. 不確かな点: この投稿だけでは不明な点

重要な制約:
- 発言者の意図を変えない
- 事実と推測を混ぜない
- 不明なことは「この投稿だけでは明記されていません」と書く
- 長すぎない（目安: 200〜500 文字）
- Slack のマークダウンを使う（**太字**、箇条書き）
- 冒頭は必ず「補足です。」で始める
- 関係者に失礼な表現を避ける
- 機密情報や個人情報を過剰に出さない
- 日本語で回答する"""

    user_prompt = f"""以下の情報を基に、Slack スレッドに返信する補足文を生成してください。

## 対象投稿

{target_message}

## 省略抽出結果

{json.dumps(omission_result, ensure_ascii=False, indent=2)}

## 収集した文脈

{json.dumps(retrieved_context, ensure_ascii=False, indent=2)}

## 読み手の情報

- リテラシーレベル: {literacy_level}（simple=平易 / standard=標準 / detailed=詳細）
- 想定読者タイプ: {audience_type}（new_member=新人 / non_engineer=非エンジニア / engineer=エンジニア / project_member=プロジェクトメンバー）

## 指示

上記の情報を基に、聞き手が追加質問しなくても理解できる補足文を生成してください。
発言者の意図を変えず、事実と推測を分けて書いてください。
冒頭は「補足です。」で始めてください。
Slack のマークダウン（**太字**、箇条書き）を使ってください。
補足文のテキストのみを返してください（JSON 不要）。"""

    response = bedrock.invoke_model(
        modelId=model_id,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "temperature": 0.5,
        }),
        contentType="application/json",
        accept="application/json",
    )

    body = json.loads(response["body"].read())
    return body["content"][0]["text"]
