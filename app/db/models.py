"""データベースの行を表現するデータモデルを定義するモジュール。

`ConfigRepository` が返す不変オブジェクトを提供する。
"""

# 標準ライブラリ
from dataclasses import dataclass


@dataclass(frozen=True)
class GuildSettings:
    """ギルド単位の翻訳設定を表す不変オブジェクト。

    `guild_settings` テーブルの1行、または行が存在しない場合のデフォルト値を表す。

    Attributes:
        guild_id: ギルドID。
        source_lang: 翻訳元言語コード（例: "EN"）。
        target_lang: 翻訳先言語コード（例: "JA"）。
        formality: 敬語レベル（"default"/"more"/"less"/"prefer_more"/"prefer_less"）。
        provider: このギルドの既定翻訳プロバイダー名（例: "deepl"/"google"）。
    """

    guild_id: int
    source_lang: str
    target_lang: str
    formality: str
    provider: str


@dataclass(frozen=True)
class ChannelTranslationSettings:
    """監視チャンネルの翻訳解決結果を表す不変オブジェクト。

    `monitored_channels` と `guild_settings` を結合した結果を表し、
    `on_message` のホットパスで使用する。`provider` はチャンネル上書きと
    ギルド既定の優先順位が既に解決済みの値である。

    Attributes:
        channel_id: チャンネルID。
        guild_id: チャンネルが属するギルドID。
        source_lang: 翻訳元言語コード。
        target_lang: 翻訳先言語コード。
        formality: 敬語レベル。
        provider: 解決済みの翻訳プロバイダー名（チャンネル上書き > ギルド既定）。
    """

    channel_id: int
    guild_id: int
    source_lang: str
    target_lang: str
    formality: str
    provider: str
