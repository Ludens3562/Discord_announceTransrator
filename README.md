# Discord Announce Translator

Bot 概要
- Discord のメッセージ（本文／Embed／Markdown）を翻訳して返信する Bot
- DeepL / Google 翻訳プロバイダーを Provider インターフェースで切替可能
- マルチギルド／マルチチャンネル対応（ギルドチャンネル単位で有効化／プロバイダー選択可)

基本的な使い方
1. 環境変数を設定: BOT_TOKEN, DEEPL_API_KEY（必要に応じて GOOGLE_API_KEY）
2. 対象チャンネルを登録（管理者）: /add_channel
3. 翻訳プロバイダーを切り替え: /translate set-provider <google|deepl>

開発者向け
- 翻訳ロジック: app/translation_service.py
- Provider 実装: app/providers/*_provider.py
- コマンド: app/commands/translate_commands.py
- テスト: tests/ （pytest）

詳細は docs/translation.md / docs/migration.md を参照
