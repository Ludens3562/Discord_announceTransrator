import os
import discord
from discord import app_commands

from app.bot import bot

# deeplTrans.py 側で TranslatorBot のインスタンスが作成された後にこのモジュールが
# インポートされることを想定しているため、ここで deeplTrans を遅延インポートする。
from app import deeplTrans

translator_bot = deeplTrans.translator_bot

async def is_owner_check(interaction: discord.Interaction) -> bool:
    """BOTオーナーかどうか確認するヘルパー（コマンドチェック用）"""
    return await interaction.client.is_owner(interaction.user)


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
                    inline=False
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
    translator_bot.config["source_lang"] = source_lang.upper()
    translator_bot.config["target_lang"] = target_lang.upper()
    translator_bot.save_config()
    await interaction.response.send_message(f"翻訳設定を更新しました: {source_lang.upper()} → {target_lang.upper()}")


@bot.tree.command(name="set_formality", description="翻訳の敬語レベルを設定")
@discord.app_commands.check(is_owner_check)
async def set_formality(interaction: discord.Interaction, formality: str):
    valid_formalities = ["default", "more", "less", "prefer_more", "prefer_less"]
    if formality not in valid_formalities:
        await interaction.response.send_message(f"無効な敬語レベルです。使用可能な値: {', '.join(valid_formalities)}")
        return

    translator_bot.config["formality"] = formality
    translator_bot.save_config()
    await interaction.response.send_message(f"敬語レベルを '{formality}' に設定しました。")


@bot.tree.command(name="show_config", description="現在の設定を表示")
@discord.app_commands.check(is_owner_check)
async def show_config(interaction: discord.Interaction):
    embed = discord.Embed(title="BOT設定", color=0x0099ff)
    api_key = os.getenv("DEEPL_API_KEY")
    api_key_status = "設定済み" if api_key else "未設定"

    embed.add_field(name="DeepL APIキー", value=api_key_status, inline=False)
    embed.add_field(name="翻訳元言語", value=translator_bot.config.get("source_lang", "EN"), inline=True)
    embed.add_field(name="翻訳先言語", value=translator_bot.config.get("target_lang", "JA"), inline=True)
    embed.add_field(name="敬語レベル", value=translator_bot.config.get("formality", "more"), inline=True)
    embed.add_field(name="監視サーバー数", value=str(len(translator_bot.channels)), inline=True)

    total_channels = sum(len(channels) for channels in translator_bot.channels.values())
    embed.add_field(name="監視チャンネル数", value=str(total_channels), inline=True)

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

We need to continue reading further but we've identified commands. The commands module should include imports for os, etc. Ensure to import os in commands module for set_api_key and show_config functions. I did not import os earlier in translate_commands.py — need to add 