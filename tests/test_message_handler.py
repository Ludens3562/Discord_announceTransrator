"""translate_and_reply の単体テスト。

実データベース・実Discord接続を使わず、フェイクで検証する。
"""

# 標準ライブラリ
import asyncio
import types
from typing import Optional

# ローカルモジュール
from app.db.models import ChannelTranslationSettings
from app.message_handler import translate_and_reply


class FakeMessage:
    """discord.Message の最小フェイク。"""

    def __init__(self, content: str, channel_id: int = 123) -> None:
        self.content = content
        self.guild = object()  # ギルド内メッセージを表す（None でなければよい）
        self.channel = types.SimpleNamespace(id=channel_id)
        self._reply_called = False
        self._reply_args: Optional[tuple] = None

    async def reply(self, *args, **kwargs):
        """reply のフェイク実装。呼び出しを記録する。"""
        self._reply_called = True
        self._reply_args = (args, kwargs)
        return types.SimpleNamespace()


class FakeRepository:
    """ConfigRepository のフェイク。設定を固定で返す。"""

    def __init__(self, settings: Optional[ChannelTranslationSettings]) -> None:
        self._settings = settings

    async def get_channel_translation_settings(
        self, channel_id: int
    ) -> Optional[ChannelTranslationSettings]:
        """固定の設定（またはNone）を返す。"""
        return self._settings


class FakeTranslationService:
    """TranslationService のフェイク。固定の訳文を返す。"""

    async def translate_text(self, text, source, target, provider_name=None) -> str:
        """固定の訳文を返す。"""
        return "訳文"


def _monitored_settings() -> ChannelTranslationSettings:
    """監視対象チャンネルの設定を生成する。"""
    return ChannelTranslationSettings(
        channel_id=123,
        guild_id=456,
        source_lang="EN",
        target_lang="JA",
        formality="more",
        provider="deepl",
    )


def test_translate_and_reply_does_not_mention_author():
    """監視対象チャンネルでは翻訳を返信し、投稿者をメンションしないことを確認する。"""
    message = FakeMessage("Hello")
    repository = FakeRepository(_monitored_settings())
    service = FakeTranslationService()

    asyncio.run(translate_and_reply(message, repository, service))

    assert message._reply_called is True
    assert message._reply_args is not None
    assert message._reply_args[1].get("mention_author") is False


def test_translate_and_reply_skips_unmonitored_channel():
    """監視対象外のチャンネルでは返信しないことを確認する（異常系）。"""
    message = FakeMessage("Hello")
    repository = FakeRepository(None)  # 監視対象外
    service = FakeTranslationService()

    asyncio.run(translate_and_reply(message, repository, service))

    assert message._reply_called is False


def test_translate_and_reply_skips_empty_content():
    """空メッセージでは返信しないことを確認する（異常系）。"""
    message = FakeMessage("   ")
    repository = FakeRepository(_monitored_settings())
    service = FakeTranslationService()

    asyncio.run(translate_and_reply(message, repository, service))

    assert message._reply_called is False
