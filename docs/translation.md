# 翻訳パイプライン仕様

## 概要
- 本プロジェクトは `TranslationService` を中心とした翻訳パイプラインで、入力メッセージ（本文・Embed・Markdown）を安全に翻訳します。
- DeepL / Google は `Provider` インターフェースを実装するプラグインとして扱い、実行時に切替可能です。

## Markdown の取り扱い
- 翻訳対象: 通常のテキスト（リンクの表示テキストなど）
- 非翻訳（保護）対象:
  - コードブロック（``` ```）
  - インラインコード（`code`）
  - Discord メンション（`<@...>` / `<@&...>`）
  - URL（例: `https://...`）
  - カスタム絵文字（`<:name:id>`）
- 翻訳フロー:
  1. `protect_text` で保護トークンに置換
  2. Provider に保護済み文字列を渡して翻訳（Provider はプレーンテキストで扱う）
  3. `restore_text` でトークンを元に戻す
- 注意点: リンクの URL は変更されず、リンクの表示テキストのみ翻訳されます。

## Embed の取り扱い
- 翻訳対象: `title`, `description`, `fields[*].name`, `fields[*].value`, `footer.text`
- Embed のメタデータ（色、タイムスタンプ等）は維持されます。

## Provider 切替
- `TranslationService` の `providers` に `google` / `deepl` を登録します。
- `provider_name` を指定することで特定 Provider を使用可能。
- ギルド／チャンネル単位の設定は将来の設定レイヤー（global → guild → channel）で上書き可能。

## エラーとフォールバック
- Provider 呼び出しは `ProviderError` を投げます。呼び出し元はこれを処理してフォールバックまたは管理者通知を行います。
- 長文やレート制限に対する制約は `TranslationService(max_concurrent=...)` で設定できます。
