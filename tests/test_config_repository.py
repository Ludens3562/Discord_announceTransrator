"""ConfigRepository の単体テスト。

FakePool を用いて実データベースに接続せずに検証する。
"""

# 標準ライブラリ
import asyncio

# ローカルモジュール
from app.db.repository import ConfigRepository


def test_get_channel_translation_settings_returns_none_when_not_monitored(fake_pool):
    """監視対象外のチャンネルでは None を返すことを確認する。"""
    fake_pool.fetchrow_result = None
    repository = ConfigRepository(fake_pool)

    result = asyncio.run(repository.get_channel_translation_settings(123))

    assert result is None


def test_get_channel_translation_settings_maps_row():
    """結合結果の行が解決済み設定へ正しくマッピングされることを確認する。"""
    from tests.conftest import FakePool

    pool = FakePool()
    pool.fetchrow_result = {
        "channel_id": 123,
        "guild_id": 456,
        "source_lang": "EN",
        "target_lang": "JA",
        "formality": "more",
        "provider": "google",
    }
    repository = ConfigRepository(pool)

    result = asyncio.run(repository.get_channel_translation_settings(123))

    assert result is not None
    assert result.channel_id == 123
    assert result.guild_id == 456
    assert result.provider == "google"


def test_add_monitored_channel_returns_true_when_inserted(fake_pool):
    """新規追加時に True を返すことを確認する。"""
    fake_pool.fetchrow_result = {"channel_id": 123}
    repository = ConfigRepository(fake_pool)

    result = asyncio.run(repository.add_monitored_channel(123, 456))

    assert result is True


def test_add_monitored_channel_returns_false_on_conflict(fake_pool):
    """既に監視対象の場合に False を返すことを確認する（異常系）。"""
    fake_pool.fetchrow_result = None
    repository = ConfigRepository(fake_pool)

    result = asyncio.run(repository.add_monitored_channel(123, 456))

    assert result is False


def test_remove_monitored_channel_returns_false_when_absent(fake_pool):
    """監視対象でないチャンネルの削除時に False を返すことを確認する（異常系）。"""
    fake_pool.fetchrow_result = None
    repository = ConfigRepository(fake_pool)

    result = asyncio.run(repository.remove_monitored_channel(123))

    assert result is False


def test_get_guild_settings_returns_defaults_without_insert(fake_pool):
    """行が存在しない場合、デフォルト値を返し INSERT を行わないことを確認する。"""
    fake_pool.fetchrow_result = None
    repository = ConfigRepository(fake_pool)

    result = asyncio.run(repository.get_guild_settings(456))

    assert result.guild_id == 456
    assert result.source_lang == "EN"
    assert result.target_lang == "JA"
    assert result.formality == "more"
    assert result.provider == "deepl"
    # 遅延作成のため execute（INSERT）は呼ばれないこと
    assert all(call[0] != "execute" for call in fake_pool.calls)


def test_set_channel_provider_override_clear_passes_none(fake_pool):
    """上書き解除時に provider=None が渡されることを確認する。"""
    fake_pool.fetchrow_result = {"channel_id": 123}
    repository = ConfigRepository(fake_pool)

    result = asyncio.run(repository.set_channel_provider_override(123, None))

    assert result is True
    # 最後の fetchrow 呼び出しの引数に None（上書き解除）が含まれること
    method, _sql, args = fake_pool.calls[-1]
    assert method == "fetchrow"
    assert args == (123, None)


def test_set_channel_provider_override_returns_false_when_channel_absent(fake_pool):
    """監視対象でないチャンネルへの上書き設定時に False を返すことを確認する（異常系）。"""
    fake_pool.fetchrow_result = None
    repository = ConfigRepository(fake_pool)

    result = asyncio.run(repository.set_channel_provider_override(123, "google"))

    assert result is False


def test_upsert_guild_language_executes_with_args(fake_pool):
    """言語設定の upsert が正しい引数で execute を呼ぶことを確認する。"""
    repository = ConfigRepository(fake_pool)

    asyncio.run(repository.upsert_guild_language(456, "EN", "JA"))

    method, _sql, args = fake_pool.calls[-1]
    assert method == "execute"
    assert args == (456, "EN", "JA")
