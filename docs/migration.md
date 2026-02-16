# 移行手順（既存ユーザー向け）

このリリースでは設定スキーマを拡張し、翻訳プロバイダーの選択とマルチギルド対応をサポートします。既存設定は互換的に読み込まれます。

手順（安全な方法）
1. 既存の `config.json` と `channels.json` をバックアップしてください（例: `cp config.json config.json.bak`）。
2. 新バージョンをデプロイして起動します（既存ファイルは読み込まれます）。
3. 起動後、管理者として `/translate show-config` を実行して設定を確認してください。
4. 必要に応じて `/translate set-provider <google|deepl>` を実行してギルドやチャンネルごとにプロバイダーを切り替えてください。

ロールバック
- 問題が発生した場合はバックアップした `config.json.bak` と `channels.json.bak` を復元して再起動してください。

注意点
- API キーは `.env` または環境変数で管理され、設定ファイルには書き込まれません。
- 新しい `TranslationService` はデフォルトで既存の動作と互換性がありますが、プロバイダーごとの微妙な訳語差はあり得ます。

## Docker でのデプロイ（簡易）

- イメージビルド:
  - `docker build -t disbot:latest .`
- 単一コンテナ実行（.env 使用例）:
  - `docker run -d --name disbot --env-file .env --restart unless-stopped disbot:latest`
- docker-compose を使う場合:
  - `docker compose up -d --build` (リポジトリの `docker-compose.yml` を使用)
- 環境変数 / シークレット:
  - `BOT_TOKEN`, `DEEPL_API_KEY`, `GOOGLE_API_KEY` などは `.env` に設定し、リポジトリに含めないでください（`.gitignore` に記載済み）。本番では Docker secrets やオーケストレータのシークレット管理を検討してください。
- ボリュームと永続化:
  - アプリは `config.json` / `channels.json` を実行時に更新します。永続化が必要な場合は専用ボリュームやホストファイルをマウントしてください。ホストのソースコードを直接マウントする際は書き込み権限に注意してください。
