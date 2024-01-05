import discord
import os
import deepl
from dotenv import load_dotenv
import re

# インテントの設定
intents = discord.Intents.default()
intents.message_content = True

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEEPL_TOKEN = os.getenv("DEEPL_API_KEY")

bot = discord.Client(intents=intents)
translator = deepl.Translator(DEEPL_TOKEN)


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
            text = re.sub(r":[^:]+:", "", message.content)
            translation = translator.translate_text(
                text,
                source_lang="EN",
                target_lang="JA",
                formality="more",
                tag_handling="xml",
            )
            # 翻訳結果を元のメッセージに返信
            await message.reply(translation)
    except Exception as e:
        print(f"翻訳エラー: {str(e)}")


bot.run(BOT_TOKEN)
