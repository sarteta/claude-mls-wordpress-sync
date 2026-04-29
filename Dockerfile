FROM python:3.13-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

COPY requirements.txt ./
RUN pip install --prefix=/install -r requirements.txt


FROM python:3.13-slim-bookworm

LABEL org.opencontainers.image.source="https://github.com/sarteta/claude-mls-wordpress-sync"
LABEL org.opencontainers.image.description="MLS to WordPress sync with field-mapping YAML, dry-run diff, and a health endpoint"
LABEL org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN groupadd --system --gid 10001 app \
 && useradd  --system --uid 10001 --gid app --create-home app

COPY --from=builder /install /usr/local

WORKDIR /app
COPY --chown=app:app src ./src
COPY --chown=app:app config ./config
RUN mkdir -p /app/state /app/logs && chown -R app:app /app/state /app/logs

USER app

# Default: preview a sync against the mock provider.
#   docker run --rm ghcr.io/sarteta/claude-mls-wordpress-sync          # dry-run mock
#   docker run --rm ghcr.io/sarteta/claude-mls-wordpress-sync \
#     --provider mock                                                  # apply
ENTRYPOINT ["python", "-m", "src.sync"]
CMD ["--provider", "mock", "--dry-run"]
