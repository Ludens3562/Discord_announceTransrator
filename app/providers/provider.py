"""翻訳プロバイダーの抽象インターフェースを定義するモジュール。

この抽象クラスは既存の実装（DeepL / Google）を直ちに変更せずに
将来的に各プロバイダーが従う契約を明確にするためのものです。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class Provider(ABC):
    """翻訳プロバイダーが実装すべき契約（抽象クラス）。

    実装クラスは `translate` メソッドを提供する必要があります。
    メソッドの詳細な動作（外部API呼び出しやエラー処理）は各実装に任せます。
    """

    @abstractmethod
    def translate(self, text: str, source: Optional[str] = None, target: Optional[str] = None) -> str:
        """テキストを翻訳して翻訳後の文字列を返す。

        Args:
            text: 翻訳対象の文字列
            source: 元言語コード（例: "en"）、省略可
            target: 目標言語コード（例: "ja"）、省略可

        Returns:
            翻訳された文字列
        """
        raise NotImplementedError
