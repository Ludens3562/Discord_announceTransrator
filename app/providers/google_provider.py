import asyncio
from typing import Optional

from app.providers.provider import Provider, ProviderError


class GoogleProvider(Provider):
    """googletrans を利用する Provider 実装。

    - コンストラクタで外部呼び出しは行わない（副作用は遅延）
    - 同期版 `translate` と非同期補助 `translate_async` を提供する
    `translate_async` は `asyncio.to_thread` で同期呼び出しを別スレッドで実行する。
    """

    def __init__(self):
        # 副作用を避けるために Translator の生成は translate 呼び出し時に行う
        pass

    def translate(self, text: str, source: Optional[str] = None, target: Optional[str] = None) -> str:
        """同期的に googletrans を呼ぶ（テストで直接呼べるようにする）。"""
        try:
            from googletrans import Translator  # 遅延インポート

            translator = Translator()
            # googletrans の引数名は src/dest
            res = translator.translate(text, src=source or "auto", dest=target)
            return getattr(res, "text", str(res))
        except Exception as e:
            raise ProviderError(f"GoogleProvider エラー: {e}")

    async def translate_async(self, text: str, source: Optional[str] = None, target: Optional[str] = None) -> str:
        """非同期ラッパー: ブロッキングな translate を別スレッドで実行する。"""
        return await asyncio.to_thread(self.translate, text, source, target)
