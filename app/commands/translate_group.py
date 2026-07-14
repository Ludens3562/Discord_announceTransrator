"""`/translate` スラッシュコマンドツリーを定義するモジュール。

`translate` グループの配下に `channel` / `config` サブグループと、
`manual` / `test` / `usage` / `sync` コマンドを持つ。各コマンドは
`interaction.client`（TranslatorBot）経由でリポジトリと翻訳サービスへアクセスする。
"""

# 標準ライブラリ
import asyncio
import logging
import os
from typing import TYPE_CHECKING, Literal, Optional

# サードパーティ
import discord
from discord import app_commands

# ローカルモジュール
from app.providers.provider import ProviderError
from app.utils.auth import is_guild_admin_check, is_owner_check

if TYPE_CHECKING:
    # 循環インポートを避けるため型チェック時のみ参照する
    from app.bot import TranslatorBot

logger = logging.getLogger(__name__)

# 設定可能な定数
VALID_FORMALITIES = ("default", "more", "less", "prefer_more", "prefer_less")

# プロバイダー選択に使う型エイリアス（Discordの選択肢UIを自動生成する）
ProviderChoice = Literal["deepl", "google"]
ChannelProviderChoice = Literal["deepl", "google", "clear"]
FormalityChoice = Literal["default", "more", "less", "prefer_more", "prefer_less"]
SyncScope = Literal["guild", "global"]


def _get_bot(interaction: discord.Interaction) -> "TranslatorBot":
    """インタラクションからTranslatorBotインスタンスを取得する。

    Args:
        interaction: 対象インタラクション。

    Returns:
        BOTインスタンス。
    """
    # interaction.client は起動している TranslatorBot 実体である
    return interaction.client  # type: ignore[return-value]


def _available_providers(bot: "TranslatorBot") -> set[str]:
    """利用可能な翻訳プロバイダー名の集合を返す。

    Args:
        bot: BOTインスタンス。

    Returns:
        登録済みプロバイダー名の集合。未初期化時は既知の2種を返す。
    """
    service = bot.translation_service
    if service is not None and service.providers:
        return set(service.providers.keys())
    return {"deepl", "google"}


class ChannelGroup(app_commands.Group):
    """`/translate channel` サブグループ。監視チャンネルの管理を行う。"""

    def __init__(self) -> None:
        super().__init__(name="channel", description="監視チャンネルの管理")

    @app_commands.command(name="add", description="監視チャンネルを追加")
    @app_commands.check(is_guild_admin_check)
    async def add(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
    ) -> None:
        """監視チャンネルを追加する。

        Args:
            interaction: インタラクション。
            channel: 追加するチャンネル。省略時は実行チャンネル。
        """
        if interaction.guild is None:
            await interaction.response.send_message("ギルド内でのみ使用できます。", ephemeral=True)
            return

        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("テキストチャンネルを指定してください。", ephemeral=True)
            return

        bot = _get_bot(interaction)
        added = await bot.repository.add_monitored_channel(target.id, interaction.guild.id)
        if added:
            await interaction.response.send_message(f"チャンネル {target.mention} を監視対象に追加しました。")
        else:
            await interaction.response.send_message(f"チャンネル {target.mention} は既に監視対象です。")

    @app_commands.command(name="remove", description="監視チャンネルを削除")
    @app_commands.check(is_guild_admin_check)
    async def remove(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
    ) -> None:
        """監視チャンネルを削除する。

        Args:
            interaction: インタラクション。
            channel: 削除するチャンネル。省略時は実行チャンネル。
        """
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("テキストチャンネルを指定してください。", ephemeral=True)
            return

        bot = _get_bot(interaction)
        removed = await bot.repository.remove_monitored_channel(target.id)
        if removed:
            await interaction.response.send_message(f"チャンネル {target.mention} を監視対象から削除しました。")
        else:
            await interaction.response.send_message(f"チャンネル {target.mention} は監視対象ではありません。")

    @app_commands.command(name="list", description="監視チャンネル一覧を表示")
    @app_commands.check(is_guild_admin_check)
    async def list_channels(self, interaction: discord.Interaction) -> None:
        """ギルド内の監視チャンネル一覧を表示する。

        Args:
            interaction: インタラクション。
        """
        if interaction.guild is None:
            await interaction.response.send_message("ギルド内でのみ使用できます。", ephemeral=True)
            return

        bot = _get_bot(interaction)
        channel_ids = await bot.repository.list_monitored_channels(interaction.guild.id)

        embed = discord.Embed(title="監視チャンネル一覧", color=0x00FF00)
        if not channel_ids:
            embed.description = "監視チャンネルが設定されていません。"
        else:
            mentions = []
            for channel_id in channel_ids:
                channel = bot.get_channel(channel_id)
                mentions.append(channel.mention if channel else f"不明なチャンネル ({channel_id})")
            embed.description = "\n".join(mentions)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="provider", description="チャンネル単位の翻訳プロバイダー上書きを設定")
    @app_commands.check(is_guild_admin_check)
    async def provider(
        self,
        interaction: discord.Interaction,
        provider: ChannelProviderChoice,
        channel: Optional[discord.TextChannel] = None,
    ) -> None:
        """チャンネル単位のプロバイダー上書きを設定または解除する。

        Args:
            interaction: インタラクション。
            provider: プロバイダー名。"clear" を指定すると上書きを解除する。
            channel: 対象チャンネル。省略時は実行チャンネル。
        """
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("テキストチャンネルを指定してください。", ephemeral=True)
            return

        bot = _get_bot(interaction)

        # "clear" 以外は登録済みプロバイダーか検証する
        override: Optional[str]
        if provider == "clear":
            override = None
        else:
            if provider not in _available_providers(bot):
                available = ", ".join(sorted(_available_providers(bot)))
                await interaction.response.send_message(
                    f"利用できないプロバイダーです。利用可能: {available}", ephemeral=True
                )
                return
            override = provider

        updated = await bot.repository.set_channel_provider_override(target.id, override)
        if not updated:
            await interaction.response.send_message(
                f"チャンネル {target.mention} は監視対象ではありません。先に追加してください。",
                ephemeral=True,
            )
            return

        if override is None:
            await interaction.response.send_message(
                f"チャンネル {target.mention} のプロバイダー上書きを解除しました。", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"チャンネル {target.mention} のプロバイダーを '{override}' に設定しました。", ephemeral=True
            )


class ConfigGroup(app_commands.Group):
    """`/translate config` サブグループ。ギルド単位の翻訳設定を管理する。"""

    def __init__(self) -> None:
        super().__init__(name="config", description="ギルド単位の翻訳設定")

    @app_commands.command(name="language", description="翻訳元・翻訳先言語を設定")
    @app_commands.check(is_guild_admin_check)
    async def language(
        self, interaction: discord.Interaction, source_lang: str, target_lang: str
    ) -> None:
        """ギルドの翻訳元・翻訳先言語を設定する。

        Args:
            interaction: インタラクション。
            source_lang: 翻訳元言語コード。
            target_lang: 翻訳先言語コード。
        """
        if interaction.guild is None:
            await interaction.response.send_message("ギルド内でのみ使用できます。", ephemeral=True)
            return

        source = source_lang.upper()
        target = target_lang.upper()
        bot = _get_bot(interaction)
        await bot.repository.upsert_guild_language(interaction.guild.id, source, target)
        await interaction.response.send_message(f"翻訳設定を更新しました: {source} → {target}")

    @app_commands.command(name="formality", description="翻訳の敬語レベルを設定")
    @app_commands.check(is_guild_admin_check)
    async def formality(self, interaction: discord.Interaction, formality: FormalityChoice) -> None:
        """ギルドの敬語レベルを設定する。

        Args:
            interaction: インタラクション。
            formality: 敬語レベル。
        """
        if interaction.guild is None:
            await interaction.response.send_message("ギルド内でのみ使用できます。", ephemeral=True)
            return

        bot = _get_bot(interaction)
        await bot.repository.upsert_guild_formality(interaction.guild.id, formality)
        await interaction.response.send_message(f"敬語レベルを '{formality}' に設定しました。")

    @app_commands.command(name="provider", description="ギルドの既定翻訳プロバイダーを設定")
    @app_commands.check(is_guild_admin_check)
    async def provider(self, interaction: discord.Interaction, provider: ProviderChoice) -> None:
        """ギルドの既定プロバイダーを設定する。

        Args:
            interaction: インタラクション。
            provider: プロバイダー名。
        """
        if interaction.guild is None:
            await interaction.response.send_message("ギルド内でのみ使用できます。", ephemeral=True)
            return

        bot = _get_bot(interaction)
        if provider not in _available_providers(bot):
            available = ", ".join(sorted(_available_providers(bot)))
            await interaction.response.send_message(
                f"利用できないプロバイダーです。利用可能: {available}", ephemeral=True
            )
            return

        await bot.repository.upsert_guild_provider(interaction.guild.id, provider)
        await interaction.response.send_message(f"既定プロバイダーを '{provider}' に設定しました。")

    @app_commands.command(name="show", description="現在の設定を表示")
    @app_commands.check(is_guild_admin_check)
    async def show(self, interaction: discord.Interaction) -> None:
        """現在のギルド設定と監視チャンネル情報を表示する。

        Args:
            interaction: インタラクション。
        """
        if interaction.guild is None:
            await interaction.response.send_message("ギルド内でのみ使用できます。", ephemeral=True)
            return

        bot = _get_bot(interaction)
        settings = await bot.repository.get_guild_settings(interaction.guild.id)
        channel_ids = await bot.repository.list_monitored_channels(interaction.guild.id)

        deepl_key_status = "設定済み" if os.getenv("DEEPL_API_KEY") else "未設定"
        google_available = "google" in _available_providers(bot)

        embed = discord.Embed(title="翻訳BOT設定", color=0x0099FF)
        embed.add_field(name="翻訳元言語", value=settings.source_lang, inline=True)
        embed.add_field(name="翻訳先言語", value=settings.target_lang, inline=True)
        embed.add_field(name="敬語レベル", value=settings.formality, inline=True)
        embed.add_field(name="既定プロバイダー", value=settings.provider, inline=True)
        embed.add_field(name="監視チャンネル数", value=str(len(channel_ids)), inline=True)
        embed.add_field(name="DeepL APIキー", value=deepl_key_status, inline=True)
        embed.add_field(name="Google翻訳", value="利用可能" if google_available else "利用不可", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)


class TranslateGroup(app_commands.Group):
    """`/translate` トップレベルグループ。"""

    def __init__(self) -> None:
        super().__init__(name="translate", description="翻訳BOTの設定と操作")
        # サブグループを子として追加する
        self.add_command(ChannelGroup())
        self.add_command(ConfigGroup())

    @app_commands.command(name="manual", description="メッセージIDを指定して手動翻訳")
    @app_commands.check(is_guild_admin_check)
    async def manual(
        self,
        interaction: discord.Interaction,
        message_id: str,
        channel: Optional[discord.TextChannel] = None,
    ) -> None:
        """メッセージIDを指定して手動翻訳し、結果をEmbedで表示する。

        Args:
            interaction: インタラクション。
            message_id: 翻訳対象メッセージのID。
            channel: 対象チャンネル。省略時は実行チャンネル。
        """
        if interaction.guild is None:
            await interaction.response.send_message("ギルド内でのみ使用できます。", ephemeral=True)
            return

        target_channel = channel or interaction.channel
        if not isinstance(target_channel, discord.TextChannel):
            await interaction.response.send_message("テキストチャンネルを指定してください。", ephemeral=True)
            return

        try:
            message_id_int = int(message_id)
        except ValueError:
            await interaction.response.send_message("無効なメッセージIDです。数字を入力してください。", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            message = await target_channel.fetch_message(message_id_int)
        except discord.NotFound:
            await interaction.followup.send("指定されたメッセージが見つかりません。", ephemeral=True)
            return
        except discord.Forbidden:
            await interaction.followup.send("メッセージにアクセスする権限がありません。", ephemeral=True)
            return

        if not message.content.strip():
            await interaction.followup.send("指定されたメッセージに翻訳可能なテキストがありません。", ephemeral=True)
            return

        bot = _get_bot(interaction)
        # チャンネルの解決済み設定を優先し、監視対象外ならギルド既定にフォールバックする
        channel_settings = await bot.repository.get_channel_translation_settings(target_channel.id)
        if channel_settings is not None:
            source_lang = channel_settings.source_lang
            target_lang = channel_settings.target_lang
            provider_name = channel_settings.provider
        else:
            guild_settings = await bot.repository.get_guild_settings(interaction.guild.id)
            source_lang = guild_settings.source_lang
            target_lang = guild_settings.target_lang
            provider_name = guild_settings.provider

        try:
            translation = await bot.translation_service.translate_text(
                message.content, source=source_lang, target=target_lang, provider_name=provider_name
            )
        except ProviderError as error:
            logger.warning("手動翻訳に失敗しました: %s", error)
            await interaction.followup.send("翻訳に失敗しました。", ephemeral=True)
            return

        embed = discord.Embed(title="手動翻訳結果", color=0x00FF00)
        embed.add_field(name="作成者", value=message.author.mention, inline=True)
        embed.add_field(name="チャンネル", value=target_channel.mention, inline=True)
        embed.add_field(name="投稿日時", value=message.created_at.strftime("%Y/%m/%d %H:%M:%S"), inline=True)
        embed.add_field(name="原文", value=message.content[:1024], inline=False)
        embed.add_field(name="翻訳結果", value=translation[:1024], inline=False)
        embed.add_field(name="メッセージリンク", value=f"[元のメッセージに移動]({message.jump_url})", inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="test", description="入力テキストの翻訳テスト")
    @app_commands.check(is_guild_admin_check)
    async def test(self, interaction: discord.Interaction, text: str) -> None:
        """入力テキストをギルド設定で翻訳し結果を返す。

        Args:
            interaction: インタラクション。
            text: 翻訳するテキスト。
        """
        if interaction.guild is None:
            await interaction.response.send_message("ギルド内でのみ使用できます。", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        bot = _get_bot(interaction)
        settings = await bot.repository.get_guild_settings(interaction.guild.id)
        try:
            translation = await bot.translation_service.translate_text(
                text,
                source=settings.source_lang,
                target=settings.target_lang,
                provider_name=settings.provider,
            )
        except ProviderError as error:
            logger.warning("翻訳テストに失敗しました: %s", error)
            await interaction.followup.send(f"翻訳エラー: {error}", ephemeral=True)
            return

        await interaction.followup.send(
            f"**翻訳テスト**\n\n**原文:**\n{text}\n\n**翻訳結果:**\n{translation}", ephemeral=True
        )

    @app_commands.command(name="usage", description="DeepL APIの使用量を表示")
    @app_commands.check(is_guild_admin_check)
    async def usage(self, interaction: discord.Interaction) -> None:
        """DeepL APIの文字数使用量を表示する。

        Args:
            interaction: インタラクション。
        """
        api_key = os.getenv("DEEPL_API_KEY")
        if not api_key:
            await interaction.response.send_message("DeepL APIキーが設定されていません。", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            usage = await asyncio.to_thread(_fetch_deepl_usage, api_key)
        except Exception as error:  # noqa: BLE001 - deepl 側の例外種別が広いため集約する
            logger.warning("DeepL使用量の取得に失敗しました: %s", error)
            await interaction.followup.send("使用量の取得に失敗しました。", ephemeral=True)
            return

        char_count, char_limit = usage
        char_percentage = (char_count / char_limit * 100) if char_limit > 0 else 0.0
        embed = discord.Embed(title="DeepL API 使用量", color=0x0099FF)
        embed.add_field(
            name="文字数使用量",
            value=f"{char_count:,} / {char_limit:,} 文字（{char_percentage:.1f}%）",
            inline=False,
        )
        embed.set_footer(text="使用量は数分の遅延がある場合があります")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="sync", description="スラッシュコマンドを手動同期（BOTオーナー限定）")
    @app_commands.check(is_owner_check)
    async def sync(self, interaction: discord.Interaction, scope: SyncScope = "guild") -> None:
        """スラッシュコマンドツリーを手動同期する。

        Args:
            interaction: インタラクション。
            scope: "guild"（現在のギルド）または "global"（全体）。
        """
        bot = _get_bot(interaction)
        await interaction.response.defer(ephemeral=True)
        try:
            if scope == "global":
                synced = await bot.tree.sync()
                await interaction.followup.send(
                    f"グローバルに {len(synced)} 個のコマンドを同期しました。\n"
                    "※反映には最大1時間かかる場合があります。",
                    ephemeral=True,
                )
            else:
                if interaction.guild is None:
                    await interaction.followup.send("ギルド同期はギルド内でのみ使用できます。", ephemeral=True)
                    return
                synced = await bot.tree.sync(guild=interaction.guild)
                await interaction.followup.send(
                    f"このギルドに {len(synced)} 個のコマンドを同期しました。", ephemeral=True
                )
        except discord.HTTPException as error:
            logger.warning("コマンド同期に失敗しました: %s", error)
            await interaction.followup.send(f"コマンド同期に失敗しました: {error}", ephemeral=True)


def _fetch_deepl_usage(api_key: str) -> tuple[int, int]:
    """DeepL APIの文字数使用量を同期的に取得する。

    `Provider` 抽象の対象外（翻訳ではなく使用量参照）のため、ここで直接 deepl を呼ぶ。

    Args:
        api_key: DeepL APIキー。

    Returns:
        (使用文字数, 上限文字数) のタプル。
    """
    # サードパーティ（関数内で遅延インポート）
    import deepl

    translator = deepl.Translator(api_key)
    usage = translator.get_usage()
    return usage.character.count, usage.character.limit


async def handle_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
) -> None:
    """アプリケーションコマンドのエラーハンドラ。

    権限エラーは日本語で通知し、その他のエラーはログに残して汎用メッセージを返す。

    Args:
        interaction: インタラクション。
        error: 発生したエラー。
    """
    if isinstance(error, app_commands.CheckFailure):
        message = "この操作にはサーバー管理権限またはBOTオーナー権限が必要です。"
    else:
        logger.error("コマンド実行中にエラーが発生しました: %s", error)
        message = f"エラーが発生しました: {error}"

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)
