import os

from app.providers.deepl_provider import DeepLProvider


class FakeResult:
    def __init__(self, text):
        self.text = text


class FakeTranslator:
    def __init__(self, api_key=None):
        self._key = api_key

    def translate_text(self, text, source_lang=None, target_lang=None, formality=None, tag_handling=None):
        return FakeResult(f"D_{text}")


def test_deepl_provider_translate(monkeypatch):
    # deepl モジュールを偽装して Translator を差し替える
    import sys, types

    fake_mod = types.SimpleNamespace(Translator=FakeTranslator)
    monkeypatch.setitem(sys.modules, 'deepl', fake_mod)

    p = DeepLProvider(api_key="dummy")
    out = p.translate("hello", source="EN", target="JA")
    assert out == "D_hello"


def test_deepl_provider_raises_without_key():
    p = DeepLProvider(api_key=None)
    try:
        p.translate("x")
        raised = False
    except Exception:
        raised = True
    assert raised
