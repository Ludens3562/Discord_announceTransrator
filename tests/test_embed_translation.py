import asyncio

import discord

from app.translation_service import TranslationService
from app.providers.provider import Provider


class PrefixProvider(Provider):
    def translate(self, text: str, source: str | None = None, target: str | None = None) -> str:
        return f"[JA]{text}"


def make_embed():
    e = discord.Embed(title="Hello Title", description="This is desc: [link](https://ex.com)")
    e.add_field(name="Field1", value="field value", inline=False)
    e.set_footer(text="footer text")
    return e


def test_translate_embed_translates_all_parts():
    svc = TranslationService({"pref": PrefixProvider()})
    embed = make_embed()

    translated = asyncio.run(svc.translate_embed(embed, source="en", target="ja", provider_name="pref"))

    assert translated.title.startswith("[JA]")
    assert translated.description.startswith("[JA]")
    assert translated.fields[0].name.startswith("[JA]") or translated.fields[0].value.startswith("[JA]")
    assert translated.footer.text.startswith("[JA]")
