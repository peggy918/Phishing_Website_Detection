# 雲端展示版（Google Cloud Run）。資料庫用 SQLite，建置時就匯入參考資料、政府黑名單與模型紀錄。
# 本機正式版仍用 SQL Server，見 README。部署步驟見 docs/deploy-gcp.md。
FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# LightGBM 需要 OpenMP 執行環境
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 只裝執行需要的套件：排除測試工具（pytest、Playwright）與 SQL Server 驅動
COPY requirements.txt .
RUN grep -viE '^(playwright|pytest|pytest-cov|pytest-playwright|pyee|coverage|iniconfig|pluggy|pygments|python-slugify|text-unidecode|greenlet|pyodbc)==' requirements.txt > requirements-run.txt \
    && pip install -r requirements-run.txt gunicorn==27.0.0

COPY alembic.ini wsgi.py ./
COPY app ./app
COPY config ./config
COPY migrations ./migrations
COPY data/reference ./data/reference
# 上線中的模型：不在 git，部署時由本機上傳（見 .gcloudignore）
ARG MODEL_VERSION=lightgbm-20261108-224947
COPY models_store/${MODEL_VERSION} ./models_store/${MODEL_VERSION}


# 建資料庫的階段。政府 XML 的中文檔名從 Windows 上傳後會變成非 UTF-8 的亂碼，
# 留在映像檔裡會讓 Cloud Run 匯入失敗（ContainerImageImportFailed），所以只放在這個階段，
# 匯入時另外指定原檔名；最後的映像檔只複製建好的資料庫。
FROM base AS seed
ARG GOV_XML=通報TWNIC詐騙網址彙整表_20261008.xml
ARG MODEL_VERSION=lightgbm-20261108-224947
COPY scripts/build_sqlite.py ./scripts/
COPY data/raw/*.xml /seed/
RUN test "$(ls /seed/*.xml | wc -l)" -eq 1 \
    && python scripts/build_sqlite.py /app/instance/netcatch.db /seed/*.xml "models_store/${MODEL_VERSION}" "${GOV_XML}"


FROM base
COPY --from=seed /app/instance /app/instance
RUN useradd --create-home --uid 10001 app \
    && chown -R app:app /app/instance

USER app
# LOG_PATH 留空：紀錄只輸出到標準輸出，由 Cloud Logging 收集
# TRUSTED_PROXY_HOPS=1：Cloud Run 前面有一層代理，速率限制改用真實來源 IP
ENV DATABASE_URL=sqlite:////app/instance/netcatch.db \
    LOG_PATH= \
    TRUSTED_PROXY_HOPS=1 \
    PORT=8080

# 單一行程：SQLite 與記憶體中的速率限制計數都不跨行程共用
CMD exec gunicorn --bind ":${PORT}" --workers 1 --threads 8 --timeout 0 wsgi:app
