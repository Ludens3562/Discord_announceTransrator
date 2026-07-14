"""Provider インターフェースの単体テスト。

- `FakeProvider` を使って `Provider` 抽象クラスの契約（抽象メソッドの要求）を検証する。
- 具体的なプロバイダー実装には依存しない簡易テスト。
"""

import pytest

from app.providers.provider import Provider


class FakeProvider(Provider):
    """テスト用の簡易プロバイダー実装。translate の振る舞いを単純化している。"""

    def translate(self, text: str, source: str | None = None, target: str | None = None) -> str:
        # 簡単に動作確認できるように target を前置して返す
        return f"[{target}]{text}" if target else text


def test_fake_provider_translates_text():
    p = FakeProvider()
    assert p.translate("hello", source="en", target="ja") == "[ja]hello"
    assert p.translate("plain") == "plain"


def test_provider_is_abstract_enforced():
    # translate を実装していないサブクラスはインスタンス化できないことを確認
    class BadProvider(Provider):
        pass

    with pytest.raises(TypeError):
        BadProvider()
