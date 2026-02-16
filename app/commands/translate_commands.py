import os
import discord
from discord import app_commands

from app.bot import bot

# deeplTrans.py 側で TranslatorBot のインスタンスが作成された後にこのモジュールが
# インポートされることを想定しているため、ここで deeplTrans を遅延インポートする。
from app import deeplTrans

translator_bot = deeplTrans.translator_bot

from app.utils.auth import is_owner_check


@bot.tree.command(name="add_channel", description="監視チャンネルを追加")
@discord.app_commands.check(is_owner_check)
async def add_channel(interaction: discord.Interaction, channel: discord.TextChannel = None):
    """監視チャンネルを追加するコマンド"""
    if channel is None:
        channel = interaction.channel

    server_id = str(interaction.guild.id)
    channel_id = str(channel.id)

    if server_id not in translator_bot.channels:
        translator_bot.channels[server_id] = []

    if channel_id not in translator_bot.channels[server_id]:
        translator_bot.channels[server_id].append(channel_id)
        translator_bot.save_channels()
        await interaction.response.send_message(f"チャンネル {channel.mention} を監視対象に追加しました。")
    else:
        await interaction.response.send_message(f"チャンネル {channel.mention} は既に監視対象です。")


@bot.tree.command(name="remove_channel", description="監視チャンネルを削除")
@discord.app_commands.check(is_owner_check)
async def remove_channel(interaction: discord.Interaction, channel: discord.TextChannel = None):
    """監視チャンネルを削除するコマンド"""
    if channel is None:
        channel = interaction.channel

    server_id = str(interaction.guild.id)
    channel_id = str(channel.id)

    if server_id in translator_bot.channels and channel_id in translator_bot.channels[server_id]:
        translator_bot.channels[server_id].remove(channel_id)
        if not translator_bot.channels[server_id]:
            del translator_bot.channels[server_id]
        translator_bot.save_channels()
        await interaction.response.send_message(f"チャンネル {channel.mention} を監視対象から削除しました。")
    else:
        await interaction.response.send_message(f"チャンネル {channel.mention} は監視対象ではありません。")


@bot.tree.command(name="list_channels", description="監視チャンネル一覧を表示")
@discord.app_commands.check(is_owner_check)
async def list_channels(interaction: discord.Interaction):
    """監視チャンネル一覧を埋め込んで表示する"""
    embed = discord.Embed(title="監視チャンネル一覧", color=0x00ff00)

    if not translator_bot.channels:
        embed.description = "監視チャンネルが設定されていません。"
    else:
        for server_id, channel_ids in translator_bot.channels.items():
            try:
                guild = bot.get_guild(int(server_id))
                server_name = guild.name if guild else f"Unknown Server ({server_id})"

                channel_mentions = []
                for channel_id in channel_ids:
                    channel = bot.get_channel(int(channel_id))
                    if channel:
                        channel_mentions.append(channel.mention)
                    else:
                        channel_mentions.append(f"Unknown Channel ({channel_id})")

                embed.add_field(
                    name=server_name,
                    value="\n".join(channel_mentions) if channel_mentions else "なし",
                    inline=False,
                )
            except Exception:
                embed.add_field(name=f"Server {server_id}", value="エラー", inline=False)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="set_api_key", description="DeepL APIキーを設定")
@discord.app_commands.check(is_owner_check)
async def set_api_key(interaction: discord.Interaction, api_key: str):
    """DeepL APIキーを .env に保存して翻訳器を再初期化する"""
    try:
        translator_bot.update_env_file("DEEPL_API_KEY", api_key)
        os.environ["DEEPL_API_KEY"] = api_key
        translator_bot.initialize_translator()

        if translator_bot.translator:
            await interaction.response.send_message("DeepL APIキーを設定し、翻訳器を初期化しました。", ephemeral=True)
        else:
            await interaction.response.send_message("APIキーの設定に失敗しました。キーを確認してください。", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"APIキーの設定中にエラーが発生しました: {e}", ephemeral=True)


@bot.tree.command(name="set_languages", description="翻訳言語を設定")
@discord.app_commands.check(is_owner_check)
async def set_languages(interaction: discord.Interaction, source_lang: str, target_lang: str):
    """翻訳元/先言語を設定して保存する"""
    translator_bot.config["source_lang"] = source_lang.upper()
    translator_bot.config["target_lang"] = target_lang.upper()
    translator_bot.save_config()
    await interaction.response.send_message(f"翻訳設定を更新しました: {source_lang.upper()} → {target_lang.upper()}")


@bot.tree.command(name="set_formality", description="翻訳の敬語レベルを設定")
@discord.app_commands.check(is_owner_check)
async def set_formality(interaction: discord.Interaction, formality: str):
    """敬語（formality）設定を更新する"""
    valid_formalities = ["default", "more", "less", "prefer_more", "prefer_less"]
    if formality not in valid_formalities:
        await interaction.response.send_message(f"無効な敬語レベルです。使用可能な値: {', '.join(valid_formalities)}")
        return

    translator_bot.config["formality"] = formality
    translator_bot.save_config()
    await interaction.response.send_message(f"敬語レベルを '{formality}' に設定しました。")


@bot.tree.command(name="set_provider", description="翻訳プロバイダーを設定（default/guild/channel）")
@discord.app_commands.check(is_owner_check)
async def set_provider(
    interaction: discord.Interaction,
    scope: str,
    provider: str,
    channel: discord.TextChannel = None,
):
    """プロバイダー設定を保存する。

    scope: 'default'|'guild'|'channel' のいずれか。
    - default: 全体のデフォルトプロバイダーを設定
    - guild: 現在のギルドに対する上書き（interaction.guild を使用）
    - channel: 指定されたチャンネル、またはコマンド実行チャンネルに対する上書き

    provider: プロバイダー名（例: 'deepl', 'google'）。'none' を指定すると上書きを削除します。
    """
    valid_scopes = {"default", "guild", "channel"}
    if scope not in valid_scopes:
        await interaction.response.send_message(f"無効な scope です。使用可能: {', '.join(sorted(valid_scopes))}", ephemeral=True)
        return

    # 利用可能なプロバイダー名を収集（TranslationService が存在する場合はそれを尊重）
    available_providers = None
    ts = getattr(translator_bot, "translation_service", None)
    if getattr(ts, "providers", None):
        available_providers = set(ts.providers.keys())
    else:
        available_providers = {"deepl", "google"}

    provider_lower = provider.lower()

    # 'none' は上書き解除を意味する
    if provider_lower in {"none", "clear", "remove"}:
        remove = True
    else:
        remove = False
        if provider_lower not in available_providers:
            await interaction.response.send_message(
                f"無効なプロバイダーです。使用可能なプロバイダー: {', '.join(sorted(available_providers))}",
                ephemeral=True,
            )
            return

    # scope ごとに設定／解除を実行
    if scope == "default":
        if remove:
            translator_bot.config.pop("default_provider", None)
            await interaction.response.send_message("デフォルトプロバイダーをデフォルト値にリセットしました。", ephemeral=True)
        else:
            translator_bot.config["default_provider"] = provider_lower
            await interaction.response.send_message(f"デフォルトプロバイダーを '{provider_lower}' に設定しました。", ephemeral=True)

    elif scope == "guild":
        if not interaction.guild:
            await interaction.response.send_message("ギルドコンテキストでのみ使用できます。", ephemeral=True)
            return
        gid = str(interaction.guild.id)
        guild_providers = translator_bot.config.setdefault("guild_providers", {})

        if remove:
            if gid in guild_providers:
                guild_providers.pop(gid)
                await interaction.response.send_message("このギルドのプロバイダー上書きを削除しました。", ephemeral=True)
            else:
                await interaction.response.send_message("このギルドに設定された上書きはありません。", ephemeral=True)
        else:
            guild_providers[gid] = provider_lower
            await interaction.response.send_message(f"このギルドのプロバイダーを '{provider_lower}' に設定しました。", ephemeral=True)

    else:  # channel
        target_channel = channel or interaction.channel
        if target_channel is None:
            await interaction.response.send_message("対象チャンネルが見つかりません。", ephemeral=True)
            return

        cid = str(target_channel.id)
        channel_providers = translator_bot.config.setdefault("channel_providers", {})

        if remove:
            if cid in channel_providers:
                channel_providers.pop(cid)
                await interaction.response.send_message("このチャンネルのプロバイダー上書きを削除しました。", ephemeral=True)
            else:
                await interaction.response.send_message("このチャンネルに設定された上書きはありません。", ephemeral=True)
        else:
            channel_providers[cid] = provider_lower
            await interaction.response.send_message(
                f"チャンネル {target_channel.mention} のプロバイダーを '{provider_lower}' に設定しました。",
                ephemeral=True,
            )

    translator_bot.save_config()


@bot.tree.command(name="show_config", description="現在の設定を表示（プロバイダー情報を含む）")
@discord.app_commands.check(is_owner_check)
async def show_config(interaction: discord.Interaction):
    """現在の設定とプロバイダー上書き（default/guild/channel）を表示する"""
    embed = discord.Embed(title="BOT設定", color=0x0099ff)

    # APIキーの状態を確認（キー自体は表示しない）
    api_key = os.getenv("DEEPL_API_KEY")
    api_key_status = "設定済み" if api_key else "未設定"
    embed.add_field(name="DeepL APIキー", value=api_key_status, inline=False)

    # 基本設定
    embed.add_field(name="翻訳元言語", value=translator_bot.config.get("source_lang", "EN"), inline=True)
    embed.add_field(name="翻訳先言語", value=translator_bot.config.get("target_lang", "JA"), inline=True)
    embed.add_field(name="敬語レベル", value=translator_bot.config.get("formality", "more"), inline=True)

    # プロバイダー設定（デフォルト）
    default_provider = translator_bot.config.get("default_provider", "deepl")
    embed.add_field(name="デフォルトプロバイダー", value=default_provider, inline=True)

    # 監視件数
    embed.add_field(name="監視サーバー数", value=str(len(translator_bot.channels)), inline=True)
    total_channels = sum(len(channels) for channels in translator_bot.channels.values())
    embed.add_field(name="監視チャンネル数", value=str(total_channels), inline=True)

    # ギルド別プロバイダー上書き
    guild_providers = translator_bot.config.get("guild_providers", {}) or {}
    if guild_providers:
        lines = []
        for gid, prov in guild_providers.items():
            guild = bot.get_guild(int(gid)) if gid.isdigit() else None
            name = guild.name if guild else f"Unknown Guild ({gid})"
            lines.append(f"{name}: {prov}")
        embed.add_field(name="ギルドごとのプロバイダー", value="\n".join(lines), inline=False)
    else:
        embed.add_field(name="ギルドごとのプロバイダー", value="なし", inline=False)

    # チャンネル別プロバイダー上書き
    channel_providers = translator_bot.config.get("channel_providers", {}) or {}
    if channel_providers:
        lines = []
        for cid, prov in channel_providers.items():
            channel_obj = bot.get_channel(int(cid)) if cid.isdigit() else None
            ch_display = channel_obj.mention if channel_obj else f"Unknown Channel ({cid})"
            lines.append(f"{ch_display}: {prov}")
        embed.add_field(name="チャンネルごとのプロバイダー", value="\n".join(lines), inline=False)
    else:
        embed.add_field(name="チャンネルごとのプロバイダー", value="なし", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="translate_message", description="メッセージIDを指定して手動翻訳")
@discord.app_commands.check(is_owner_check)
async def translate_message_by_id(interaction: discord.Interaction, message_id: str, channel: discord.TextChannel = None):
    if not translator_bot.translator:
        await interaction.response.send_message("DeepL APIキーが設定されていません。", ephemeral=True)
        return

    if channel is None:
        channel = interaction.channel

    try:
        message_id_int = int(message_id)
        try:
            message = await channel.fetch_message(message_id_int)
        except discord.NotFound:
            await interaction.response.send_message("指定されたメッセージが見つかりません。", ephemeral=True)
            return
        except discord.Forbidden:
            await interaction.response.send_message("メッセージにアクセスする権限がありません。", ephemeral=True)
            return

        if not message.content.strip():
            await interaction.response.send_message("指定されたメッセージに翻訳可能なテキストがありません。", ephemeral=True)
            return

        translation = await translator_bot.translate_message(message)
        if not translation:
            await interaction.response.send_message("翻訳に失敗しました。", ephemeral=True)
            return

        embed = discord.Embed(title="手動翻訳結果", color=0x00ff00)
        embed.add_field(name="作成者", value=message.author.mention, inline=True)
        embed.add_field(name="チャンネル", value=channel.mention, inline=True)
        embed.add_field(name="投稿日時", value=message.created_at.strftime("%Y/%m/%d %H:%M:%S"), inline=True)
        embed.add_field(name="原文", value=message.content[:1024], inline=False)
        embed.add_field(name="翻訳結果", value=translation[:1024], inline=False)
        embed.add_field(name="メッセージリンク", value=f"[元のメッセージに移動]({message.jump_url})", inline=False)

        await interaction.response.send_message(embed=embed)

    except ValueError:
        await interaction.response.send_message("無効なメッセージIDです。数字を入力してください。", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {e}", ephemeral=True)
        print(f"Manual translation error: {e}")


@bot.tree.command(name="deepl_usage", description="DeepL APIの使用量を表示")
@discord.app_commands.check(is_owner_check)
async def show_deepl_usage(interaction: discord.Interaction):
    if not translator_bot.translator:
        await interaction.response.send_message("DeepL APIキーが設定されていません。", ephemeral=True)
        return

    usage_info = await translator_bot.get_usage_info()
    if not usage_info:
        await interaction.response.send_message("使用量の取得に失敗しました。", ephemeral=True)
        return

    embed = discord.Embed(title="DeepL API 使用量", color=0x0099ff)
    embed.add_field(name="文字数（使用/上限）", value=f"{usage_info['character_count']} / {usage_info['character_limit']}", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)