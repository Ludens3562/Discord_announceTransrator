import discord
from discord.ext import commands

# 共通の Intents 設定を集中管理
intents = discord.Intents.default()
intents.message_content = True

# Bot インスタンス（コマンド登録は各モジュール側で行う）
bot = commands.Bot(command_prefix='!', intents=intents)
