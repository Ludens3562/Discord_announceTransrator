# Discord Announce Translator

Bot 概要
- Discord のメッセージ（本文／Embed／Markdown）を翻訳して返信する Bot
- DeepL / Google 翻訳プロバイダーを Provider インターフェースで切替可能
- マルチギルド／マルチチャンネル対応（ギルド・チャンネル単位で有効化／プロバイダー選択可）
- 設定はギルド単位で PostgreSQL に永続化する

基本的な使い方
1. 環境変数を設定する（`app/.env.example` を `app/.env` にコピーして値を設定）。
   - `BOT_TOKEN`, `DEEPL_API_KEY`（必要に応じて Google 翻訳を利用）
   - `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
2. `docker compose up -d --build` で PostgreSQL と Bot を起動する。
3. サーバー管理権限を持つメンバーが対象チャンネルを登録する: `/translate channel add`
4. ギルドの翻訳言語を設定する: `/translate config language source_lang:EN target_lang:JA`
5. 翻訳プロバイダーを切り替える: `/translate config provider provider:google`（チャンネル単位は `/translate channel provider`）

スラッシュコマンド一覧
- `/translate channel add|remove|list` — 監視チャンネルの追加・削除・一覧
- `/translate channel provider` — チャンネル単位のプロバイダー上書き（`clear` で解除）
- `/translate config language|formality|provider` — ギルド単位の言語・敬語レベル・既定プロバイダー
- `/translate config show` — 現在の設定を表示
- `/translate manual` — メッセージIDを指定して手動翻訳
- `/translate test` — 入力テキストの翻訳テスト
- `/translate usage` — DeepL API の使用量を表示
- `/translate sync` — コマンドツリーの手動同期（BOTオーナー限定）

権限
- `channel` / `config` および `manual` / `test` / `usage` はサーバー管理権限（Manage Server）またはBOTオーナーが実行できる。
- `sync` はBOTオーナーのみ実行できる。

開発者向け
- エントリーポイント: app/main.py
- BOT本体: app/bot.py（TranslatorBot）
- 翻訳ロジック: app/translation_service.py
- Provider 実装: app/providers/*_provider.py
- コマンド: app/commands/translate_group.py
- 永続化: app/db/（pool.py / repository.py / models.py）
- メッセージ処理: app/message_handler.py
- テスト: tests/ （pytest）

詳細は docs/wiki/ を参照（[目次](docs/wiki/00-目次.md)）

## Docker

- ビルドと起動（PostgreSQL 同梱）:
  - `docker compose up -d --build`
- 環境変数の扱い:
  - `BOT_TOKEN`, `DEEPL_API_KEY`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` などは `app/.env` に記述し、リポジトリにコミットしない（`.gitignore` に記載済み）。
  - docker-compose では `disbot` と `db` の両サービスが `app/.env` を読み込む。`POSTGRES_HOST` はサービス名 `db` を指定する。
  - 本番環境では Docker secrets やオーケストレータのシークレット管理を推奨する。
- データ永続化:
  - 設定は PostgreSQL に保存され、名前付きボリューム `pgdata` に永続化される。
  - スキーマは Bot 起動時に自動作成される（`CREATE TABLE IF NOT EXISTS`）。
- 注意点:
  - API キーや機密情報は公開リポジトリやコミットに含めない。
