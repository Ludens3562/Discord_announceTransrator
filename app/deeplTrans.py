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
        """設定ファイルを読み込み（シークレット情報は除く）。

        - 既存の設定ファイルを互換的に読み込み、必要なキー（プロバイダ設定等）を補完する。
        """
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                # 互換性のためのデフォルト補完
                cfg.setdefault("source_lang", "EN")
                cfg.setdefault("target_lang", "JA")
                cfg.setdefault("formality", "more")
                cfg.setdefault("default_provider", "deepl")
                cfg.setdefault("guild_providers", {})
                cfg.setdefault("channel_providers", {})
                return cfg
        return {
            "source_lang": "EN",
            "target_lang": "JA",
            "formality": "more",
            "default_provider": "deepl",
            "guild_providers": {},
            "channel_providers": {}
        }
    
    def save_config(self):
        """設定ファイルを保存（シークレット情報は除く）。

        - provider 設定やギルド/チャンネル上書き情報も保存する（互換維持）。
        """
        config_to_save = {
            "source_lang": self.config.get("source_lang", "EN"),
            "target_lang": self.config.get("target_lang", "JA"),
            "formality": self.config.get("formality", "more"),
            "default_provider": self.config.get("default_provider", "deepl"),
            "guild_providers": self.config.get("guild_providers", {}),
            "channel_providers": self.config.get("channel_providers", {})
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_to_save, f, indent=2, ensure_ascii=False)
    
    def update_env_file(self, key, value):
        """環境変数ファイルを更新"""
        env_path = Path('.env')
        
        if env_path.exists():
            # 既存の.envファイルを読み込み
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 該当する行を探して更新
            updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith(f'{key}='):
                    lines[i] = f'{key}={value}\n'
                    updated = True
                    break
            
            # 該当する行がない場合は追加
            if not updated:
                lines.append(f'{key}={value}\n')
            
            # ファイルに書き戻し
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
        else:
            # .envファイルが存在しない場合は新規作成
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(f'{key}={value}\n')
    
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
        """DeepL翻訳器を初期化

        - 既存の deepl.Translator を初期化しつつ、TranslationService にも
          DeepLProvider を登録する（副作用は遅延する）。
        """
        # 環境変数から最新のAPIキーを取得
        api_key = os.getenv("DEEPL_API_KEY")
        if api_key:
            try:
                self.translator = deepl.Translator(api_key)
            except Exception as e:
                print(f"DeepL初期化エラー: {e}")

        # TranslationService 用の DeepLProvider を作成（初期化は副作用なし）
        try:
            from app.translation_service import TranslationService
            from app.providers.deepl_provider import DeepLProvider

            if api_key:
                self.translation_service = TranslationService({"deepl": DeepLProvider(api_key=api_key)})
            else:
                self.translation_service = None
        except Exception:
            # テスト環境等で import に失敗しても既存の動作に影響を与えない
            self.translation_service = None
    
    def clean_message_content(self, content):
        """メッセージから絵文字や不要な要素を削除"""
        # カスタム絵文字を削除 (<:name:id> や <a:name:id> 形式)
        content = re.sub(r'<a?:[^:]+:\d+>', '', content)
        # Unicode絵文字は保持
        # Discordメンションを保持
        # マークダウン記法を保持
        return content.strip()
    
    async def get_usage_info(self):
        """DeepL APIの使用量情報を取得"""
        if not self.translator:
            return None
        
        try:
            usage = self.translator.get_usage()
            return {
                "character_count": usage.character.count,
                "character_limit": usage.character.limit,
                "document_count": usage.document.count if hasattr(usage, 'document') else 0,
                "document_limit": usage.document.limit if hasattr(usage, 'document') else 0
            }
        except Exception as e:
            print(f"使用量取得エラー: {e}")
            return None
    
    async def translate_message(self, message):
        """メッセージを翻訳

        - 可能であれば TranslationService を経由して翻訳を行う（既存挙動は維持）
        """
        # TranslationService が利用可能ならそちらを優先して利用する
        if getattr(self, "translation_service", None):
            try:
                # Provider の決定（channel > guild > global の優先順位）
                guild_id = str(message.guild.id) if message.guild else None
                channel_id = str(message.channel.id)
                provider_name = None

                channel_providers = self.config.get("channel_providers", {})
                guild_providers = self.config.get("guild_providers", {})

                if channel_id and channel_id in channel_providers:
                    provider_name = channel_providers[channel_id]
                elif guild_id and guild_id in guild_providers:
                    provider_name = guild_providers[guild_id]
                else:
                    provider_name = self.config.get("default_provider", "deepl")

                return await self.translation_service.translate_text(
                    message.content,
                    source=self.config.get("source_lang", "EN"),
                    target=self.config.get("target_lang", "JA"),
                    provider_name=provider_name,
                )
            except Exception as e:
                # Provider 側のエラーが発生しても既存の同期的実装へフォールバックする
                print(f"TranslationService 経由の翻訳でエラーが発生しました: {e}")

        # 既存の実装（フォールバック）
        if not self.translator:
            return None
        
        try:
            cleaned_content = self.clean_message_content(message.content)
            if not cleaned_content:
                return None
            
            result = self.translator.translate_text(
                cleaned_content,
                source_lang=self.config.get("source_lang", "EN"),
                target_lang=self.config.get("target_lang", "JA"),
                formality=self.config.get("formality", "more"),
                tag_handling="xml"
            )
            return result.text
        except Exception as e:
            print(f"翻訳エラー: {e}")
            return None

# BOTインスタンス
translator_bot = TranslatorBot()

# コマンドは専用モジュールに分割して登録する
from app.commands import translate_commands  # コマンドを登録する

@bot.event
async def on_ready():
    """BOT起動時の処理"""
    print(f"Logged in as {bot.user.name}")
    await bot.change_presence(activity=discord.Game(name="WATCHING CHANNELS"))
    
    # 開発サーバーのギルドID（環境変数で設定）
    dev_guild_id = os.getenv("DEV_GUILD_ID")
    
    if dev_guild_id:
        # 開発サーバーのみに同期（即座に反映）
        try:
            guild = discord.Object(id=int(dev_guild_id))
            synced = await bot.tree.sync(guild=guild)
            print(f"Synced {len(synced)} command(s) to development guild {dev_guild_id}")
        except Exception as e:
            print(f"Failed to sync commands to development guild: {e}")
    else:
        # グローバル同期（反映に最大1時間かかる）
        try:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} command(s) globally")
        except Exception as e:
            print(f"Failed to sync commands globally: {e}")

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
    if not message.content.strip():
        return
    
    translation = await translator_bot.translate_message(message)
    if translation:
        try:
            await message.reply(translation, mention_author=False)
        except Exception as e:
            print(f"返信エラー: {e}")

@bot.tree.command(name="set_languages", description="翻訳言語を設定")
@discord.app_commands.check(is_owner_check)
async def set_languages(interaction: discord.Interaction, source_lang: str, target_lang: str):
    """翻訳言語を設定"""
    translator_bot.config["source_lang"] = source_lang.upper()
    translator_bot.config["target_lang"] = target_lang.upper()
    translator_bot.save_config()
    
    await interaction.response.send_message(
        f"翻訳設定を更新しました: {source_lang.upper()} → {target_lang.upper()}"
    )

@bot.tree.command(name="set_formality", description="翻訳の敬語レベルを設定")
@discord.app_commands.check(is_owner_check)
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
@discord.app_commands.check(is_owner_check)
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

@bot.tree.command(name="translate_message", description="メッセージIDを指定して手動翻訳")
@discord.app_commands.check(is_owner_check)
async def translate_message_by_id(interaction: discord.Interaction, message_id: str, channel: discord.TextChannel = None):
    """メッセージIDを指定して手動翻訳"""
    if not translator_bot.translator:
        await interaction.response.send_message("DeepL APIキーが設定されていません。", ephemeral=True)
        return
    
    # チャンネルが指定されていない場合は現在のチャンネルを使用
    if channel is None:
        channel = interaction.channel
    
    try:
        # メッセージIDを数値に変換
        message_id_int = int(message_id)
        
        # メッセージを取得
        try:
            message = await channel.fetch_message(message_id_int)
        except discord.NotFound:
            await interaction.response.send_message("指定されたメッセージが見つかりません。", ephemeral=True)
            return
        except discord.Forbidden:
            await interaction.response.send_message("メッセージにアクセスする権限がありません。", ephemeral=True)
            return
        
        # メッセージに内容がない場合
        if not message.content.strip():
            await interaction.response.send_message("指定されたメッセージに翻訳可能なテキストがありません。", ephemeral=True)
            return
        
        # 翻訳実行
        translation = await translator_bot.translate_message(message)
        if not translation:
            await interaction.response.send_message("翻訳に失敗しました。", ephemeral=True)
            return
        
        # 結果を表示
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
    """DeepL APIの使用量を表示"""
    if not translator_bot.translator:
        await interaction.response.send_message("DeepL APIキーが設定されていません。", ephemeral=True)
        return
    
    # 使用量を取得
    usage_info = await translator_bot.get_usage_info()
    if not usage_info:
        await interaction.response.send_message("使用量の取得に失敗しました。", ephemeral=True)
        return
    
    embed = discord.Embed(title="DeepL API 使用量", color=0x0099ff)
    
    # 文字数の使用量
    char_count = usage_info["character_count"]
    char_limit = usage_info["character_limit"]
    char_percentage = (char_count / char_limit * 100) if char_limit > 0 else 0
    
    embed.add_field(
        name="?? 文字数使用量",
        value=f"{char_count:,} / {char_limit:,} 文字\n({char_percentage:.1f}%)",
        inline=True
    )
    
    # 残り文字数
    char_remaining = char_limit - char_count
    embed.add_field(
        name="?? 残り文字数",
        value=f"{char_remaining:,} 文字",
        inline=True
    )
    
    # プログレスバーの作成
    progress_chars = 20
    filled_chars = int(char_percentage / 100 * progress_chars)
    empty_chars = progress_chars - filled_chars
    progress_bar = "?" * filled_chars + "?" * empty_chars
    
    embed.add_field(
        name="?? 使用率",
        value=f"`{progress_bar}` {char_percentage:.1f}%",
        inline=False
    )
    
    # ドキュメント翻訳の使用量（プランによって利用可能）
    if usage_info["document_limit"] > 0:
        doc_count = usage_info["document_count"]
        doc_limit = usage_info["document_limit"]
        doc_percentage = (doc_count / doc_limit * 100) if doc_limit > 0 else 0
        
        embed.add_field(
            name="?? ドキュメント使用量",
            value=f"{doc_count} / {doc_limit} ドキュメント\n({doc_percentage:.1f}%)",
            inline=True
        )
    
    # 使用量に応じて色を変更
    if char_percentage >= 90:
        embed.color = 0xff0000  # 赤
    elif char_percentage >= 75:
        embed.color = 0xff9900  # オレンジ
    elif char_percentage >= 50:
        embed.color = 0xffff00  # 黄色
    else:
        embed.color = 0x00ff00  # 緑
    
    # フッターに更新時刻を追加
    embed.set_footer(text="使用量は数分の遅延がある場合があります")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="sync_commands", description="スラッシュコマンドを手動同期")
@discord.app_commands.check(is_owner_check)
async def sync_commands(interaction: discord.Interaction, global_sync: bool = False):
    """スラッシュコマンドを手動同期"""
    try:
        if global_sync:
            # グローバル同期
            synced = await bot.tree.sync()
            await interaction.response.send_message(
                f"グローバルに {len(synced)} 個のコマンドを同期しました。\n"
                "※反映には最大1時間かかる場合があります。", 
                ephemeral=True
            )
        else:
            # 現在のサーバーに同期
            guild = interaction.guild
            synced = await bot.tree.sync(guild=guild)
            await interaction.response.send_message(
                f"このサーバーに {len(synced)} 個のコマンドを同期しました。", 
                ephemeral=True
            )
    except Exception as e:
        await interaction.response.send_message(
            f"コマンド同期に失敗しました: {e}", 
            ephemeral=True
        )

@bot.tree.command(name="test_translate", description="翻訳テスト")
@discord.app_commands.check(is_owner_check)
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
        
        response_text = f"""**翻訳テスト**

**原文:**
{text}

**翻訳結果:**
{result.text}"""
        
        await interaction.response.send_message(response_text, ephemeral=True)
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
