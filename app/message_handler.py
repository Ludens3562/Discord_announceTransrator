"""監視チャンネルのメッセージを翻訳して返信する処理を提供するモジュール。

BOT本体から分離し、単体テストで直接呼び出せる純粋な関数として実装する。
"""

# 標準ライブラリ
import logging

# サードパーティ
import discord

# ローカルモジュール
from app.db.repository import ConfigRepository
from app.providers.provider import ProviderError
from app.translation_service import TranslationService

logger = logging.getLogger(__name__)


async def translate_and_reply(
    message: discord.Message,
    repository: ConfigRepository,
    translation_service: TranslationService,
) -> None:
    """監視対象チャンネルのメッセージを翻訳し、返信する。

    監視対象外のチャンネルや空メッセージ、ギルド外メッセージは何もしない。
    翻訳失敗や返信失敗は警告ログを出して握りつぶす（ユーザーへの通知は行わない）。

    Args:
        message: 受信したメッセージ。
        repository: 翻訳設定を解決するリポジトリ。
        translation_service: 翻訳を実行するサービス。
    """
    # ギルド外（DM等）や空メッセージは対象外
    if message.guild is None:
        return
    if not message.content.strip():
        return

    settings = await repository.get_channel_translation_settings(message.channel.id)
    if settings is None:
        # 監視対象外のチャンネルは何もしない
        return

    try:
        translation = await translation_service.translate_text(
            message.content,
            source=settings.source_lang,
            target=settings.target_lang,
            provider_name=settings.provider,
        )
    except ProviderError as error:
        logger.warning("翻訳に失敗しました（channel_id=%s）: %s", message.channel.id, error)
        return

    if not translation:
        return

    try:
        await message.reply(translation, mention_author=False)
    except discord.HTTPException as error:
        logger.warning("翻訳結果の返信に失敗しました（channel_id=%s）: %s", message.channel.id, error)
