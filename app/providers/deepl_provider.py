import os
import asyncio
from typing import Optional

from app.providers.provider import Provider, ProviderError


class DeepLProvider(Provider):
    """DeepL API を利用する簡易 Provider 実装。

    - コンストラクタで外部呼び出しは行わない（APIキーの保存のみ）
    - translate は同期的に deepl.Translator を生成して呼び出す
    - 非同期補助 translate_async を提供
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPL_API_KEY")

    def translate(self, text: str, source: Optional[str] = None, target: Optional[str] = None) -> str:
        if not self.api_key:
            raise ProviderError("DeepL APIキーが設定されていません。")
        try:
            import deepl  # 遅延インポート

            translator = deepl.Translator(self.api_key)
            # 既存コードとの互換のため tag_handling を xml に指定
            res = translator.translate_text(
                text,
                source_lang=(source or "EN"),
                target_lang=(target or "JA"),
                tag_handling="xml",
            )
            return getattr(res, "text", str(res))
        except Exception as e:
            raise ProviderError(f"DeepLProvider エラー: {e}")

    async def translate_async(self, text: str, source: Optional[str] = None, target: Optional[str] = None) -> str:
        return await asyncio.to_thread(self.translate, text, source, target)
