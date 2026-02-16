from __future__ import annotations

import asyncio
from typing import Dict, Optional

import discord

from app.providers.provider import Provider, ProviderError
from app.utils.markdown_helper import protect_text, restore_text


class TranslationService:
    """翻訳のパイプラインを提供するクラス。

    - 入力テキストを保護 (protect_text)
    - 指定プロバイダーへ翻訳要求を委譲
    - プレースホルダを復元して結果を返す

    例:
        svc = TranslationService({"google": GoogleProvider(), "deepl": DeepLProvider()})
    """

    def __init__(self, providers: Dict[str, Provider], max_concurrent: Optional[int] = None):
        # プロバイダー名 -> Provider インスタンス
        self.providers = providers or {}
        # 並列呼び出し上限（None の場合は制限なし）
        # 指定された場合は asyncio.BoundedSemaphore で同時実行数を制限する
        self._max_concurrent = max_concurrent
        self._sem: Optional[asyncio.BoundedSemaphore] = asyncio.BoundedSemaphore(max_concurrent) if max_concurrent is not None else None

    async def _call_provider(self, provider: Provider, text: str, source: Optional[str], target: Optional[str]) -> str:
        """プロバイダー呼び出しラッパー。

        - Provider に async 実装がある場合はそれを await
        - ない場合はブロッキング実装を asyncio.to_thread で実行して非同期的に扱う
        - プロバイダー固有のエラーは ProviderError として伝搬させる
        - `max_concurrent` が指定されていれば同時実行数を制限する
        """
        async def _invoke():
            # 非同期メソッドが定義されていればそれを呼ぶ
            if hasattr(provider, "translate_async") and asyncio.iscoroutinefunction(getattr(provider, "translate_async")):
                try:
                    return await provider.translate_async(text, source, target)  # type: ignore[attr-defined]
                except ProviderError:
                    raise
                except Exception as e:
                    raise ProviderError(f"プロバイダー呼び出し中にエラーが発生しました: {e}")

            # 同期的な translate を別スレッドで呼ぶ
            if hasattr(provider, "translate"):
                try:
                    return await asyncio.to_thread(provider.translate, text, source, target)
                except ProviderError:
                    raise
                except Exception as e:
                    raise ProviderError(f"プロバイダー呼び出し中にエラーが発生しました: {e}")

            raise ProviderError("指定したプロバイダーは translate を実装していません")

        # セマフォが設定されていれば制限内で実行
        if self._sem is not None:
            async with self._sem:
                return await _invoke()

        return await _invoke()

    async def translate_text(self, text: str, source: str, target: str, provider_name: Optional[str] = None) -> str:
        """テキスト翻訳を行うパイプライン。

        - Markdown の保護 -> プロバイダー呼び出し -> 復元 の順で処理する
        - provider_name が None の場合は登録された最初のプロバイダーを使用する
        """
        if not text:
            return text

        protected, placeholders = protect_text(text)

        # プロバイダー決定
        if provider_name:
            provider = self.providers.get(provider_name)
            if not provider:
                raise ProviderError(f"プロバイダー '{provider_name}' が見つかりません")
        else:
            # デフォルトは最初に登録されたプロバイダー
            if not self.providers:
                raise ProviderError("利用可能なプロバイダーがありません")
            provider = next(iter(self.providers.values()))

        translated = await self._call_provider(provider, protected, source, target)

        # プレースホルダを元に戻す
        restored = restore_text(translated, placeholders)
        return restored

    async def translate_embed(self, embed: discord.Embed, source: str, target: str, provider_name: Optional[str] = None) -> discord.Embed:
        """Embed の title/description/fields/footer を翻訳して新しい Embed を返す。

        - 元の Embed を破壊しない（新しいインスタンスを返す）
        - 翻訳に失敗した場合は ProviderError を投げる
        """
        new = discord.Embed()
        # メタデータをコピー（色など）
        try:
            new.colour = embed.colour
            new.timestamp = embed.timestamp
        except Exception:
            pass

        # title/description
        if embed.title:
            new.title = await self.translate_text(embed.title, source, target, provider_name)
        if embed.description:
            new.description = await self.translate_text(embed.description, source, target, provider_name)

        # fields
        for f in embed.fields:
            name = await self.translate_text(f.name, source, target, provider_name) if f.name else f.name
            value = await self.translate_text(f.value, source, target, provider_name) if f.value else f.value
            new.add_field(name=name, value=value, inline=f.inline)

        # footer
        if embed.footer and embed.footer.text:
            new.set_footer(text=await self.translate_text(embed.footer.text, source, target, provider_name))

        return new

    async def translate_message(self, message: "discord.Message", source: str, target: str, provider_name: Optional[str] = None) -> Dict:
        """discord.Message を受け取り content と embeds を翻訳して dict で返す。

        戻り値の形式:
            {"content": translated_content, "embeds": [translated_embed, ...]}
        """
        out = {"content": None, "embeds": []}

        if message.content:
            out["content"] = await self.translate_text(message.content, source, target, provider_name)

        if message.embeds:
            for e in message.embeds:
                out["embeds"].append(await self.translate_embed(e, source, target, provider_name))

        return out
