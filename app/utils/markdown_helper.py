import re
from typing import Dict, Tuple


import uuid


def _make_placeholder(kind: str, idx: int) -> str:
    """6 桁の数字サフィックス付きプレースホルダを生成する。

    UUID.hex を使わず、uuid.uuid4().int % 1000000 を 6 桁ゼロパディングして衝突確率を下げる。
    """
    # 6 桁の数字（先頭ゼロあり）をサフィックスとする
    suffix = f"{uuid.uuid4().int % 1000000:06d}"
    return f"__MD_{kind.upper()}_{idx}_{suffix}__"


# すべてのコメントは日本語で記載しています。
def protect_text(text: str) -> Tuple[str, Dict[str, str]]:
    """テキスト中の翻訳から除外すべき部分をプレースホルダ化して返す。

    保護対象:
    - コードブロック (```...```) とインラインコード (`...`)
    - メンション (<@...>, <@&...>, <#...>)
    - カスタム絵文字 (<:name:id> / <a:name:id>)
    - URL (https?://...)

    戻り値:
        (protected_text, placeholders)
        - protected_text: プレースホルダで置き換えられた文字列
        - placeholders: プレースホルダ -> 元の文字列 の辞書

    目的: 翻訳エンジンが Markdown の構造や URL/メンションを破壊しないようにする。
    """
    placeholders: Dict[str, str] = {}
    working = text

    # 1) コードブロック（```...```）を保護（DOTALLで改行を含む）
    def _protect_codeblocks(s: str):
        idx = 0

        def _repl(m):
            nonlocal idx
            ph = _make_placeholder("CODEBLOCK", idx)
            placeholders[ph] = m.group(0)
            idx += 1
            return ph

        return re.sub(r"```.*?```", _repl, s, flags=re.DOTALL)

    working = _protect_codeblocks(working)

    # 2) インラインコード (`...`) を保護
    def _protect_inline(s: str):
        idx = 0

        def _repl(m):
            nonlocal idx
            ph = _make_placeholder("INLINE", idx)
            placeholders[ph] = m.group(0)
            idx += 1
            return ph

        return re.sub(r"`[^`]+`", _repl, s)

    working = _protect_inline(working)

    # 3) カスタム絵文字を保護 (<:name:id> / <a:name:id>)
    def _protect_custom_emoji(s: str):
        idx = 0

        def _repl(m):
            nonlocal idx
            ph = _make_placeholder("CUST_EMOJI", idx)
            placeholders[ph] = m.group(0)
            idx += 1
            return ph

        return re.sub(r"<a?:[^:>]+:\d+>", _repl, s)

    working = _protect_custom_emoji(working)

    # 4) Discord メンション類を保護 (<@...>, <@!...>, <@&...>, <#...>)
    def _protect_mentions(s: str):
        idx = 0

        def _repl(m):
            nonlocal idx
            ph = _make_placeholder("MENTION", idx)
            placeholders[ph] = m.group(0)
            idx += 1
            return ph

        return re.sub(r"<@!?:?\d+>|<@&\d+>|<#\d+>", _repl, s)

    working = _protect_mentions(working)

    # 5) URL を保護（Markdown のリンク内の URL もここで置換されるためリンク本文の翻訳は残る）
    def _protect_urls(s: str):
        idx = 0

        # シンプルな URL マッチャー（訳文中に誤って置換されるのを防ぐ）
        url_re = re.compile(r"https?://\S+", flags=re.IGNORECASE)

        def _repl(m):
            nonlocal idx
            ph = _make_placeholder("URL", idx)
            placeholders[ph] = m.group(0)
            idx += 1
            return ph

        return url_re.sub(_repl, s)

    working = _protect_urls(working)

    return working, placeholders


def restore_text(text: str, placeholders: Dict[str, str]) -> str:
    """プレースホルダ化したテキストを元に戻す。

    - placeholders のキーで置換を行う（正確一致）
    - 元の Markdown 構造を復元するために単純文字列置換で十分
    """
    out = text
    # 長いプレースホルダから置換（安全策）
    for k in sorted(placeholders.keys(), key=len, reverse=True):
        out = out.replace(k, placeholders[k])
    return out
