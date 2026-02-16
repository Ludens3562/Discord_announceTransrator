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

## Docker ⚙️

- ビルド:
  - `docker build -t discord-announce-translator:latest .`
- 実行（環境変数をファイルで渡す例）:
  - `docker run -d --name disbot --env-file .env --restart unless-stopped discord-announce-translator:latest`
- docker-compose（リポジトリにある `docker-compose.yml` を使用）:
  - `docker compose up -d --build`
- `.env` の扱い:
  - `BOT_TOKEN`, `DEEPL_API_KEY`（必要に応じて `GOOGLE_API_KEY`）は `.env` に記述し、リポジトリにコミットしないでください（`.gitignore` に既に記載されています）。
  - 本番環境では Docker secrets やオーケストレータのシークレット管理を推奨します。
- 注意点:
  - アプリは実行時に `config.json` / `channels.json` を読み書きします。ホストのソースコードを読み取り専用でマウントすると動作が壊れる可能性があるため、永続化が必要な場合は専用のボリュームやファイルをマウントしてください（`docker-compose.yml` のコメントを参照）。
  - API キーや機密情報は公開リポジトリやコミットに含めないでください。

