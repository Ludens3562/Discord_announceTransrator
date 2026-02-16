# 🧩 7. APIドキュメント（スラッシュコマンド）

※ すべての管理コマンドは BOT オーナーまたはギルド管理権限が必要です。

## `/add_channel [channel]`
- 説明: 監視対象チャンネルを追加
- 引数: `channel` (省略時は呼び出しチャンネル)
- 例: `/add_channel #announcements`

## `/remove_channel [channel]`
- 説明: 監視対象チャンネルを削除

## `/list_channels`
- 説明: 現在の監視対象チャンネル一覧を表示

## `/set_provider <provider> [channel]`
- 説明: ギルドまたはチャンネル単位で使用する翻訳プロバイダーを設定
- provider: `google` | `deepl` | `none`（解除）
- 優先度: channel > guild > global
- 例: `/set_provider google`（ギルド全体のデフォルトを google に設定）

## `/show_config`
- 説明: 現在の設定（言語、プロバイダー、監視チャンネル数 等）を表示

## `/set_api_key <api_key>`
- 説明: DeepL API キーを `.env` に保存して翻訳器を初期化

## `/set_languages <source> <target>`
- 説明: 翻訳元/翻訳先言語を設定（例: EN → JA）

## `/deepl_usage`
- 説明: DeepL API の使用状況を表示（quota）

## `/translate_message <message_id> [channel]`
- 説明: 指定メッセージを手動で翻訳（管理者用）

## 実装ノート
- 翻訳は `TranslationService` 経由で行われ、`provider_name` を指定すると特定 Provider を利用します。
- コマンドはすべて `app/commands/translate_commands.py` に実装。
