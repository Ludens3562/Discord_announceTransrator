from app.providers.google_provider import GoogleProvider


class FakeResult:
    def __init__(self, text):
        self.text = text


class FakeTranslator:
    def translate(self, text, src=None, dest=None):
        return FakeResult(f"G_{text}")


def test_google_provider_translate_sync(monkeypatch):
    # googletrans モジュール自体をモックして Translator を差し替える
    import sys, types

    fake_mod = types.SimpleNamespace(Translator=FakeTranslator)
    monkeypatch.setitem(sys.modules, 'googletrans', fake_mod)

    p = GoogleProvider()
    out = p.translate("hello world", source="en", target="ja")
    assert out == "G_hello world"


def test_google_provider_translate_async(monkeypatch):
    import sys, types

    fake_mod = types.SimpleNamespace(Translator=FakeTranslator)
    monkeypatch.setitem(sys.modules, 'googletrans', fake_mod)

    p = GoogleProvider()
    import asyncio

    out = asyncio.run(p.translate_async("async test", source="en", target="ja"))
    assert out == "G_async test"
