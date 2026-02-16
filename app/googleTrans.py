import discord
import os
try:
    from googletrans import Translator as _Translator
    # 安全のため callable であればインスタンス化、さもなければ None を使用
    translator = _Translator() if callable(_Translator) else None
    Translator = _Translator
except Exception:
    # テスト環境や googletrans 未インストール時の安全策
    Translator = None
    translator = None
from dotenv import load_dotenv

# 新設: TranslationService を使うラッパーを追加（既存の挙動は維持）
from app.translation_service import TranslationService
from app.providers.google_provider import GoogleProvider

# インテントの設定
intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)
# 互換性のために既存の translator 変数を残す（モジュールにインポートできるよう安全に None を許容）
# `Translator` が利用可能な場合は上の try ブロックで初期化済み

# TranslationService の簡易インスタンス（モジュールレベルで使えるようにする）
_translation_service = TranslationService({"google": GoogleProvider()})

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
google_translate_api_key = os.getenv("GOOGLE_API_KEY")


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
    try:
        if message.content:
            # TranslationService を経由して翻訳（互換性のため provider 名を指定）
            translation = await _translation_service.translate_text(message.content, source="en", target="ja", provider_name="google")
            # 翻訳結果を元のメッセージに返信（ユーザーへのメンションを行わない）
            await message.reply(translation, mention_author=False)

    except Exception as e:
        print(f"翻訳エラー: {str(e)}")


bot.run(BOT_TOKEN)
