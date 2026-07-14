"""翻訳BOTのエントリーポイント。

環境変数を読み込み、TranslatorBot を生成して起動する。
`python -m app.main` として実行する。
"""

# 標準ライブラリ
import logging
import os
from pathlib import Path

# サードパーティ
from dotenv import load_dotenv

# ローカルモジュール
from app.bot import TranslatorBot

logger = logging.getLogger(__name__)


def main() -> None:
    """環境変数を読み込みBOTを起動する。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # .env は app ディレクトリ直下に配置される想定のため明示的にパスを指定する
    dotenv_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(dotenv_path=dotenv_path)

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logger.error("BOT_TOKEN が設定されていません。")
        return

    bot = TranslatorBot()
    bot.run(bot_token)


if __name__ == "__main__":
    main()
