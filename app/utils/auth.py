"""認証／チェック用ユーティリティ

コマンド用のチェック関数を格納するモジュール。
"""

# サードパーティ
import discord


async def is_owner_check(interaction: discord.Interaction) -> bool:
    """BOTオーナーかどうか確認するヘルパー（コマンドチェック用）。

    - interaction.client.is_owner を利用して判定する。
    - コマンドデコレータで直接参照して使える形にする。

    Args:
        interaction: 判定対象のインタラクション。

    Returns:
        BOTオーナーであればTrue。
    """
    return await interaction.client.is_owner(interaction.user)


async def is_guild_admin_check(interaction: discord.Interaction) -> bool:
    """ギルド管理者（サーバー管理権限保持者）またはBOTオーナーか確認する。

    - BOTオーナーはどのギルドでも常に許可する。
    - それ以外はギルドコンテキストで `manage_guild` 権限を持つメンバーのみ許可する。
    - DM（ギルド外）や Member でないユーザーは拒否する。

    Args:
        interaction: 判定対象のインタラクション。

    Returns:
        操作を許可する場合はTrue。
    """
    if await interaction.client.is_owner(interaction.user):
        return True
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        return False
    return interaction.user.guild_permissions.manage_guild
