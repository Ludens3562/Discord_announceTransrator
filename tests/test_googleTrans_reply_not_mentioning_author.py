import asyncio
import types

import pytest

import app.googleTrans as googleTrans


class FakeMessage:
    def __init__(self, content: str):
        self.content = content
        self._reply_called = False
        self._reply_args = None

    async def reply(self, *args, **kwargs):
        self._reply_called = True
        self._reply_args = (args, kwargs)
        return types.SimpleNamespace()


async def _fake_translate(text, source, target, provider_name=None):
    return "訳文"


def test_translate_and_reply_does_not_mention_author(monkeypatch):
    # TranslationService の translate_text をモックして確実に返信が行われるようにする
    monkeypatch.setattr(googleTrans._translation_service, "translate_text", _fake_translate)

    msg = FakeMessage("Hello")

    asyncio.run(googleTrans.translate_and_reply(msg))

    assert msg._reply_called is True
    # mention_author が必ず False で渡されていること
    assert msg._reply_args is not None
    assert msg._reply_args[1].get("mention_author") is False
