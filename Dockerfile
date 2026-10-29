# syntax=docker/dockerfile:1
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
COPY skills ./skills
COPY landing/dist ./landing/dist
COPY landing/scripts/package_skill.py ./landing/scripts/package_skill.py
RUN python landing/scripts/package_skill.py && uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim AS runtime
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 libgomp1 ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 memory && useradd --uid 10001 --gid memory --create-home memory \
    && mkdir /data && chown memory:memory /data
COPY --from=build /app/.venv /app/.venv
COPY LICENSE /app/LICENSE
USER memory
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    MEMORY_DATA_DIR=/data MEMORY_EMBEDDING_CACHE=/data/models \
    HF_HOME=/data/cache/huggingface XDG_CACHE_HOME=/data/cache \
    MEMORY_HOST=0.0.0.0 MEMORY_PORT=8080 \
    MEMORY_PUBLIC_ORIGIN=http://localhost:8080
EXPOSE 8080
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"
CMD ["vibe-memory", "serve"]
