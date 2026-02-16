"""翻訳プロバイダーの抽象インターフェースを定義するモジュール。

このモジュールはプロバイダー実装が従うべき契約を明確にします。
`Provider.translate` は成功時に翻訳文字列を返し、プロバイダー側の
期待される失敗（APIエラー、ネットワーク異常、想定外のレスポンス等）は
`ProviderError` を投げすべきであることを規定します。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class ProviderError(Exception):
    """プロバイダーの実行中に発生するエラーを表す例外クラス。

    - プロバイダー固有の失敗（外部APIエラー、認証失敗、ネットワーク障害、
      期待しないレスポンス等）を呼び出し元に伝搬するために使用する。
    - 呼び出し元はこの例外を捕捉して適切に扱う（ログ記録、リトライ、
      ユーザーへの通知など）ことを期待する。
    """


class Provider(ABC):
    """翻訳プロバイダーが実装すべき契約（抽象クラス）。

    実装クラスは `translate` メソッドを提供する必要があります。
    - 正常系: 翻訳後の文字列 (`str`) を返すこと。
    - 異常系（プロバイダー側の失敗）: `ProviderError` を投げること。

    これにより、上位レイヤーはプロバイダー固有の失敗を統一的に
    ハンドリングできます。
    """

    @abstractmethod
    def translate(self, text: str, source: Optional[str] = None, target: Optional[str] = None) -> str:
        """テキストを翻訳して翻訳後の文字列を返す。

        Args:
            text: 翻訳対象の文字列
            source: 元言語コード（例: "en"）、省略可
            target: 目標言語コード（例: "ja"）、省略可

        Returns:
            翻訳された文字列（str）

        Raises:
            ProviderError: 外部APIの失敗やネットワークエラーなど、
                プロバイダー実装が想定する失敗時に投げること。
        """
        raise NotImplementedError
