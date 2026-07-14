"""権限チェック関数 is_guild_admin_check の単体テスト。"""

# 標準ライブラリ
import asyncio
from unittest.mock import AsyncMock, MagicMock

# サードパーティ
import discord

# ローカルモジュール
from app.utils.auth import is_guild_admin_check


def _make_interaction(is_owner: bool, guild, user) -> MagicMock:
    """テスト用のインタラクションモックを生成する。

    Args:
        is_owner: is_owner が返す値。
        guild: interaction.guild に設定する値。
        user: interaction.user に設定する値。

    Returns:
        設定済みのインタラクションモック。
    """
    interaction = MagicMock()
    interaction.client.is_owner = AsyncMock(return_value=is_owner)
    interaction.guild = guild
    interaction.user = user
    return interaction


def test_bot_owner_is_always_allowed():
    """BOTオーナーはギルド権限に関わらず許可されることを確認する。"""
    user = MagicMock(spec=discord.Member)
    user.guild_permissions.manage_guild = False
    interaction = _make_interaction(is_owner=True, guild=MagicMock(), user=user)

    assert asyncio.run(is_guild_admin_check(interaction)) is True


def test_member_with_manage_guild_is_allowed():
    """manage_guild 権限を持つメンバーは許可されることを確認する。"""
    user = MagicMock(spec=discord.Member)
    user.guild_permissions.manage_guild = True
    interaction = _make_interaction(is_owner=False, guild=MagicMock(), user=user)

    assert asyncio.run(is_guild_admin_check(interaction)) is True


def test_member_without_manage_guild_is_denied():
    """manage_guild 権限を持たないメンバーは拒否されることを確認する（異常系）。"""
    user = MagicMock(spec=discord.Member)
    user.guild_permissions.manage_guild = False
    interaction = _make_interaction(is_owner=False, guild=MagicMock(), user=user)

    assert asyncio.run(is_guild_admin_check(interaction)) is False


def test_dm_context_is_denied():
    """ギルド外（DM）では拒否されることを確認する（異常系）。"""
    user = MagicMock(spec=discord.Member)
    user.guild_permissions.manage_guild = True
    interaction = _make_interaction(is_owner=False, guild=None, user=user)

    assert asyncio.run(is_guild_admin_check(interaction)) is False


def test_non_member_user_is_denied():
    """Member でないユーザー（例: DMのdiscord.User）は拒否されることを確認する（異常系）。"""
    user = MagicMock(spec=discord.User)
    interaction = _make_interaction(is_owner=False, guild=MagicMock(), user=user)

    assert asyncio.run(is_guild_admin_check(interaction)) is False
