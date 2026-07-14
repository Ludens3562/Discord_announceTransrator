import asyncio
import re

import pytest

from app.utils.markdown_helper import protect_text, restore_text
from app.translation_service import TranslationService
from app.providers.provider import Provider, ProviderError


class DummyProvider(Provider):
    def translate(self, text: str, source: str | None = None, target: str | None = None) -> str:
        # プレースホルダをそのまま保持しつつ本文を大文字化して返す簡易実装
        return text.upper()


def test_protect_and_restore_preserves_original():
    src = (
        "Here is a code block:\n```python\nprint('hello')\n```\n"
        "Inline `code` and a mention <@12345> plus a link https://example.com and emoji <:smile:123>."
    )

    protected, placeholders = protect_text(src)
    # プレースホルダが挿入され、元のコードブロックは消えていること
    assert "```python" not in protected
    assert any(k.startswith("__MD_CODEBLOCK_") for k in placeholders)

    restored = restore_text(protected, placeholders)
    assert restored == src


def test_translation_service_preserves_placeholders():
    text = "Hello `inline` and visit https://example.com and <:e:1>"
    svc = TranslationService({"dummy": DummyProvider()})

    # 非同期APIを同期的に実行
    out = asyncio.run(svc.translate_text(text, source="en", target="ja", provider_name="dummy"))

    # DummyProvider は本文を大文字化して返すが、保護対象（インラインコード/URL/絵文字）は復元される
    assert "`inline`" in out  # インラインコードは翻訳されず元のまま
    assert "https://example.com" in out
    assert "<:e:1>" in out


def test_translation_service_raises_provider_error_on_failure():
    class BrokenProvider(Provider):
        def translate(self, text: str, source: str | None = None, target: str | None = None) -> str:
            raise ProviderError("テスト用エラー")

    svc = TranslationService({"broken": BrokenProvider()})
    with pytest.raises(ProviderError):
        asyncio.run(svc.translate_text("hello", source="en", target="ja", provider_name="broken"))


def test_placeholder_collision_is_handled():
    """テキストに既知のプレースホルダ文字列が含まれていても衝突せず復元されることを確認する。"""
    # 入力に既に古い形式のプレースホルダに見える文字列を含める
    src = "This contains a literal placeholder __MD_INLINE_0__ and also `inline` code."
    svc = TranslationService({"dummy": DummyProvider()})

    out = asyncio.run(svc.translate_text(src, source="en", target="ja", provider_name="dummy"))

    # 元のリテラル文字列はそのまま保持され、保護対象のインラインコードも復元される
    assert "__MD_INLINE_0__" in out
    assert "`inline`" in out
