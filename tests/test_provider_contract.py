"""Provider の契約テスト（正常系・異常系）。

- 正常系: 翻訳が文字列を返すことを保証する。
- 異常系: プロバイダーで失敗が発生した場合は `ProviderError` を投げることを要求する。
- パッケージ公開（`app.providers`）に `ProviderError` が含まれていることを確認する。
"""

import pytest

from app.providers import Provider, ProviderError


class SuccessProvider(Provider):
    """正常に翻訳を返す実装（テスト用）"""

    def translate(self, text: str, source: str | None = None, target: str | None = None) -> str:
        return f"OK:{text}"


class FailingProvider(Provider):
    """故意に ProviderError を投げる実装（異常系検証用）"""

    def translate(self, text: str, source: str | None = None, target: str | None = None) -> str:
        raise ProviderError("プロバイダーの故障をシミュレートしました")


def test_translate_success_returns_string():
    p = SuccessProvider()
    res = p.translate("hello", source="en", target="ja")
    assert isinstance(res, str)
    assert res == "OK:hello"


def test_translate_failure_raises_provider_error():
    p = FailingProvider()
    with pytest.raises(ProviderError):
        p.translate("will fail")


def test_provider_error_is_exported_from_package():
    # `app.providers` の公開に ProviderError が含まれていることを確認
    from app import providers as providers_pkg

    assert hasattr(providers_pkg, "ProviderError")
    assert providers_pkg.ProviderError is ProviderError
