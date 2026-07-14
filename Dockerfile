FROM python:3.12-slim-bullseye

# 実行環境の最適化
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV LANG=ja_JP.UTF-8
ENV LANGUAGE=ja_JP:ja
ENV LC_ALL=ja_JP.UTF-8
ENV TZ=Asia/Tokyo

WORKDIR /app

# 最小限のランタイム依存のみをインストール（ロケールとタイムゾーン）
RUN apt-get update \
    && apt-get install -y --no-install-recommends locales tzdata \
    && locale-gen ja_JP.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

# 依存関係を先にコピーしてキャッシュを有効活用
COPY requirements.txt ./
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# アプリケーションコピーと非特権ユーザーの設定
COPY . /app
RUN useradd --system --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

# コンテナをデターミニスティックに実行するためのエントリポイント
ENTRYPOINT ["python", "-u"]
# モジュールとして実行することでパッケージの相対インポート問題を回避する
# 例: python -m app.main
CMD ["-m", "app.main"]
