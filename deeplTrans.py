import discord
from discord.ext import commands
import os
import deepl
from dotenv import load_dotenv
import re
import json
import asyncio
from pathlib import Path

# インテントの設定
intents = discord.Intents.default()
intents.message_content = True

# 環境変数の読み込み
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEEPL_TOKEN = os.getenv("DEEPL_API_KEY")
BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID"))

# BOTの初期化
bot = commands.Bot(command_prefix='!', intents=intents)
translator = None

# 設定ファイルのパス
CONFIG_FILE = Path("config.json")
CHANNELS_FILE = Path("channels.json")

class TranslatorBot:
    def __init__(self):
        self.config = self.load_config()
        self.channels = self.load_channels()
        self.translator = None
        self.initialize_translator()
    
    def load_config(self):
        """設定ファイルを読み込み"""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "deepl_api_key": DEEPL_TOKEN,
            "source_lang": "EN",
            "target_lang": "JA",
            "formality": "more"
        }
    
    def save_config(self):
        """設定ファイルを保存"""
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def load_channels(self):
        """監視チャンネル情報を読み込み"""
        if CHANNELS_FILE.exists():
            with open(CHANNELS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_channels(self):
        """監視チャンネル情報を保存"""
        with open(CHANNELS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.channels, f, indent=2, ensure_ascii=False)
    
    def initialize_translator(self):
        """DeepL翻訳器を初期化"""
        if self.config.get("deepl_api_key"):
            try:
                self.translator = deepl.Translator(self.config["deepl_api_key"])
            except Exception as e:
                print(f"DeepL初期化エラー: {e}")
    
    def clean_message_content(self, content):
        """メッセージから不要な要素を削除"""
        # Unicode絵文字は保持
        # Discordメンションを保持
        # マークダウン記法を保持
        # カスタム絵文字は保護（翻訳時に保持）
        return content.strip()
    
    def protect_markdown_formatting(self, content):
        """マークダウン記法を保護用タグで囲む"""
        placeholders = {}
        counter = [0]  # リストを使用してクロージャ内で変更可能に
        
        def create_placeholder(match):
            key = f"__PLACEHOLDER_{counter[0]}__"
            placeholders[key] = match.group(0)
            counter[0] += 1
            return key
        
        # コードブロック (```...```)
        content = re.sub(r'```[\s\S]*?```', create_placeholder, content)
        
        # インラインコード (`...`)
        content = re.sub(r'`[^`]+`', create_placeholder, content)
        
        # リンク [text](url)
        content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', create_placeholder, content)
        
        # Discord メンション (<@123>, <@!123>, <#123>, <@&123>)
        content = re.sub(r'<[@#][!&]?\d+>', create_placeholder, content)
        
        # タイムスタンプ (<t:1234567890:R> など)
        content = re.sub(r'<t:\d+(?::[tTdDfFR])?>', create_placeholder, content)
        
        # カスタム絵文字を保護 (<:name:id> や <a:name:id> 形式)
        content = re.sub(r'<a?:[^:]+:\d+>', create_placeholder, content)
        
        return content, placeholders
    
    def restore_markdown_formatting(self, content, placeholders):
        """プレースホルダーを元のマークダウン記法に復元"""
        for key, value in placeholders.items():
            content = content.replace(key, value)
        return content
    
    def translate_with_formatting(self, text):
        """フォーマットを保持しながらテキストを翻訳"""
        if not self.translator or not text:
            return None
        
        try:
            # マークダウン記法を保護
            protected_text, placeholders = self.protect_markdown_formatting(text)
            
            # 翻訳を実行
            result = self.translator.translate_text(
                protected_text,
                source_lang=self.config.get("source_lang", "EN"),
                target_lang=self.config.get("target_lang", "JA"),
                formality=self.config.get("formality", "more"),
                tag_handling="xml"
            )
            
            # プレースホルダーを復元
            translated_text = self.restore_markdown_formatting(result.text, placeholders)
            return translated_text
        except Exception as e:
            print(f"翻訳エラー: {e}")
            return None
    
    async def translate_message(self, message):
        """メッセージを翻訳"""
        if not self.translator:
            return None
        
        try:
            cleaned_content = self.clean_message_content(message.content)
            if not cleaned_content:
                return None
            
            return self.translate_with_formatting(cleaned_content)
        except Exception as e:
            print(f"翻訳エラー: {e}")
            return None
    
    async def translate_embed(self, embed):
        """Embedを翻訳して新しいEmbedを返す"""
        if not self.translator:
            return None
        
        try:
            # 新しいEmbedを作成
            new_embed = discord.Embed(color=embed.color)
            
            # タイトルを翻訳
            if embed.title:
                new_embed.title = self.translate_with_formatting(embed.title)
            
            # 説明を翻訳
            if embed.description:
                new_embed.description = self.translate_with_formatting(embed.description)
            
            # URLをそのまま保持
            if embed.url:
                new_embed.url = embed.url
            
            # フィールドを翻訳
            for field in embed.fields:
                translated_name = self.translate_with_formatting(field.name) if field.name else field.name
                translated_value = self.translate_with_formatting(field.value) if field.value else field.value
                new_embed.add_field(
                    name=translated_name or field.name,
                    value=translated_value or field.value,
                    inline=field.inline
                )
            
            # フッターを翻訳
            if embed.footer and embed.footer.text:
                translated_footer = self.translate_with_formatting(embed.footer.text)
                new_embed.set_footer(
                    text=translated_footer or embed.footer.text,
                    icon_url=embed.footer.icon_url
                )
            
            # 著者情報を翻訳
            if embed.author and embed.author.name:
                translated_author = self.translate_with_formatting(embed.author.name)
                new_embed.set_author(
                    name=translated_author or embed.author.name,
                    url=embed.author.url,
                    icon_url=embed.author.icon_url
                )
            
            # 画像とサムネイルをそのまま保持
            if embed.image:
                new_embed.set_image(url=embed.image.url)
            if embed.thumbnail:
                new_embed.set_thumbnail(url=embed.thumbnail.url)
            
            # タイムスタンプをそのまま保持
            if embed.timestamp:
                new_embed.timestamp = embed.timestamp
            
            return new_embed
        except Exception as e:
            print(f"Embed翻訳エラー: {e}")
            return None

# BOTインスタンス
translator_bot = TranslatorBot()

def is_owner():
    """BOTオーナーかどうか確認するデコレータ"""
    def predicate(interaction: discord.Interaction):
        return interaction.user.id == BOT_OWNER_ID
    return discord.app_commands.check(predicate)

@bot.event
async def on_ready():
    """BOT起動時の処理"""
    print(f"Logged in as {bot.user.name}")
    await bot.change_presence(activity=discord.Game(name="WATCHING CHANNELS"))
    
    # スラッシュコマンドを同期
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    """メッセージイベント処理"""
    # BOT自身のメッセージは無視
    if message.author == bot.user:
        return
    
    # 監視対象チャンネルかどうか確認
    server_id = str(message.guild.id)
    channel_id = str(message.channel.id)
    
    if server_id in translator_bot.channels and channel_id in translator_bot.channels[server_id]:
        await translate_and_reply(message)

async def translate_and_reply(message):
    """メッセージを翻訳して返信"""
    has_content = message.content.strip()
    has_embeds = len(message.embeds) > 0
    
    if not has_content and not has_embeds:
        return
    
    # テキストコンテンツの翻訳
    translation = None
    if has_content:
        translation = await translator_bot.translate_message(message)
    
    # Embedの翻訳
    translated_embeds = []
    if has_embeds:
        for embed in message.embeds:
            translated_embed = await translator_bot.translate_embed(embed)
            if translated_embed:
                translated_embeds.append(translated_embed)
    
    # 結果を送信
    if translation or translated_embeds:
        try:
            if translation and translated_embeds:
                await message.reply(translation, embeds=translated_embeds, mention_author=False)
            elif translation:
                await message.reply(translation, mention_author=False)
            elif translated_embeds:
                await message.reply(embeds=translated_embeds, mention_author=False)
        except Exception as e:
            print(f"返信エラー: {e}")

# スラッシュコマンド定義
@bot.tree.command(name="add_channel", description="監視チャンネルを追加")
@is_owner()
async def add_channel(interaction: discord.Interaction, channel: discord.TextChannel = None):
    """監視チャンネルを追加"""
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
@is_owner()
async def remove_channel(interaction: discord.Interaction, channel: discord.TextChannel = None):
    """監視チャンネルを削除"""
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
@is_owner()
async def list_channels(interaction: discord.Interaction):
    """監視チャンネル一覧を表示"""
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
            except Exception as e:
                embed.add_field(name=f"Server {server_id}", value="エラー", inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="set_api_key", description="DeepL APIキーを設定")
@is_owner()
async def set_api_key(interaction: discord.Interaction, api_key: str, save_to_env: bool = True):
    """DeepL APIキーを設定"""
    translator_bot.config["deepl_api_key"] = api_key
    translator_bot.save_config()
    
    # .envファイルにも保存するかどうか
    if save_to_env:
        try:
            translator_bot.update_env_file("DEEPL_API_KEY", api_key)
            env_message = "（.envファイルにも保存しました）"
        except Exception as e:
            env_message = f"（.envファイルの更新に失敗: {e}）"
    else:
        env_message = "（config.jsonのみに保存）"
    
    translator_bot.initialize_translator()
    
    if translator_bot.translator:
        await interaction.response.send_message(
            f"DeepL APIキーを設定し、翻訳器を初期化しました。{env_message}", 
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"APIキーの設定に失敗しました。キーを確認してください。{env_message}", 
            ephemeral=True
        )

@bot.tree.command(name="set_languages", description="翻訳言語を設定")
@is_owner()
async def set_languages(interaction: discord.Interaction, source_lang: str, target_lang: str):
    """翻訳言語を設定"""
    translator_bot.config["source_lang"] = source_lang.upper()
    translator_bot.config["target_lang"] = target_lang.upper()
    translator_bot.save_config()
    
    await interaction.response.send_message(
        f"翻訳設定を更新しました: {source_lang.upper()} → {target_lang.upper()}"
    )

@bot.tree.command(name="set_formality", description="翻訳の敬語レベルを設定")
@is_owner()
async def set_formality(interaction: discord.Interaction, formality: str):
    """翻訳の敬語レベルを設定"""
    valid_formalities = ["default", "more", "less", "prefer_more", "prefer_less"]
    if formality not in valid_formalities:
        await interaction.response.send_message(
            f"無効な敬語レベルです。使用可能な値: {', '.join(valid_formalities)}"
        )
        return
    
    translator_bot.config["formality"] = formality
    translator_bot.save_config()
    
    await interaction.response.send_message(f"敬語レベルを '{formality}' に設定しました。")

@bot.tree.command(name="show_config", description="現在の設定を表示")
@is_owner()
async def show_config(interaction: discord.Interaction):
    """現在の設定を表示"""
    embed = discord.Embed(title="BOT設定", color=0x0099ff)
    
    # APIキーの状態を確認（キー自体は表示しない）
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

@bot.tree.command(name="test_translate", description="翻訳テスト")
@is_owner()
async def test_translate(interaction: discord.Interaction, text: str):
    """翻訳テスト"""
    if not translator_bot.translator:
        await interaction.response.send_message("DeepL APIキーが設定されていません。", ephemeral=True)
        return
    
    try:
        result = translator_bot.translator.translate_text(
            text,
            source_lang=translator_bot.config.get("source_lang", "EN"),
            target_lang=translator_bot.config.get("target_lang", "JA"),
            formality=translator_bot.config.get("formality", "more")
        )
        
        embed = discord.Embed(title="翻訳テスト", color=0x00ff00)
        embed.add_field(name="原文", value=text, inline=False)
        embed.add_field(name="翻訳結果", value=result.text, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"翻訳エラー: {e}", ephemeral=True)

# エラーハンドリング
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.CheckFailure):
        await interaction.response.send_message("このコマンドはBOTオーナーのみ実行できます。", ephemeral=True)
    else:
        await interaction.response.send_message(f"エラーが発生しました: {error}", ephemeral=True)
        print(f"Command error: {error}")

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("BOT_TOKENが設定されていません。")
    else:
        bot.run(BOT_TOKEN)
