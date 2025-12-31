import discord
import os
import re
from googletrans import Translator
from dotenv import load_dotenv

# インテントの設定
intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)
translator = Translator()

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
google_translate_api_key = os.getenv("GOOGLE_API_KEY")


def protect_markdown_formatting(content):
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


def restore_markdown_formatting(content, placeholders):
    """プレースホルダーを元のマークダウン記法に復元"""
    for key, value in placeholders.items():
        content = content.replace(key, value)
    return content


def translate_with_formatting(text, src="en", dest="ja"):
    """フォーマットを保持しながらテキストを翻訳"""
    if not text:
        return None
    
    try:
        # マークダウン記法を保護
        protected_text, placeholders = protect_markdown_formatting(text)
        
        # 翻訳を実行
        result = translator.translate(protected_text, src=src, dest=dest)
        
        # プレースホルダーを復元
        translated_text = restore_markdown_formatting(result.text, placeholders)
        return translated_text
    except Exception as e:
        print(f"翻訳エラー: {e}")
        return None


def translate_embed(embed, src="en", dest="ja"):
    """Embedを翻訳して新しいEmbedを返す"""
    try:
        # 新しいEmbedを作成
        new_embed = discord.Embed(color=embed.color)
        
        # タイトルを翻訳
        if embed.title:
            new_embed.title = translate_with_formatting(embed.title, src, dest)
        
        # 説明を翻訳
        if embed.description:
            new_embed.description = translate_with_formatting(embed.description, src, dest)
        
        # URLをそのまま保持
        if embed.url:
            new_embed.url = embed.url
        
        # フィールドを翻訳
        for field in embed.fields:
            translated_name = translate_with_formatting(field.name, src, dest) if field.name else field.name
            translated_value = translate_with_formatting(field.value, src, dest) if field.value else field.value
            new_embed.add_field(
                name=translated_name or field.name,
                value=translated_value or field.value,
                inline=field.inline
            )
        
        # フッターを翻訳
        if embed.footer and embed.footer.text:
            translated_footer = translate_with_formatting(embed.footer.text, src, dest)
            new_embed.set_footer(
                text=translated_footer or embed.footer.text,
                icon_url=embed.footer.icon_url
            )
        
        # 著者情報を翻訳
        if embed.author and embed.author.name:
            translated_author = translate_with_formatting(embed.author.name, src, dest)
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


@bot.event
async def on_ready():
    # 起動時メッセージ
    print(f"Logged in as {bot.user.name}")
    await bot.change_presence(activity=discord.Game(name="WATCHING ANNOUNCEMENT"))


@bot.event
async def on_message(message):
    # メッセージがBOT自身のメッセージでないことを確認
    if message.author == bot.user:
        return  # 自分のBOTのメッセージには反応しない
    # ターゲットチャンネル指定
    target_channel_id = int(os.getenv("CHANNEL_ID"))
    if message.channel.id == target_channel_id:
        await translate_and_reply(message)


async def translate_and_reply(message):
    """メッセージを翻訳して返信"""
    try:
        has_content = message.content.strip() if message.content else False
        has_embeds = len(message.embeds) > 0
        
        if not has_content and not has_embeds:
            return
        
        # テキストコンテンツの翻訳
        translation = None
        if has_content:
            translation = translate_with_formatting(message.content, src="en", dest="ja")
        
        # Embedの翻訳
        translated_embeds = []
        if has_embeds:
            for embed in message.embeds:
                translated_embed = translate_embed(embed, src="en", dest="ja")
                if translated_embed:
                    translated_embeds.append(translated_embed)
        
        # 結果を送信
        if translation or translated_embeds:
            if translation and translated_embeds:
                await message.reply(translation, embeds=translated_embeds, mention_author=False)
            elif translation:
                await message.reply(translation, mention_author=False)
            elif translated_embeds:
                await message.reply(embeds=translated_embeds, mention_author=False)

    except Exception as e:
        print(f"翻訳エラー: {str(e)}")


bot.run(BOT_TOKEN)
