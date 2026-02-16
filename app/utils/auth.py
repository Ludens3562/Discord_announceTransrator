"""認証／チェック用ユーティリティ

コマンド用のチェック関数を格納するモジュール。
"""

import discord


async def is_owner_check(interaction: discord.Interaction) -> bool:
    """BOTオーナーかどうか確認するヘルパー（コマンドチェック用）。

    - interaction.client.is_owner を利用して判定する。
    - コマンドデコレータで直接参照して使える形にする。
    """
    return await interaction.client.is_owner(interaction.user)
