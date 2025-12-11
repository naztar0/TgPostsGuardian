FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy\
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/root/.local/bin:$PATH"

WORKDIR /app

RUN apt update  \
    && apt install -y --no-install-recommends build-essential curl pkg-config libpq-dev gettext \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /opt/venv

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

COPY pyproject.toml uv.lock* ./

RUN uv sync --frozen --no-dev

RUN uv add uvicorn

COPY .. .

RUN python -m compileall -q .

RUN chmod +x ./setup.sh && ./setup.sh
RUN mv ./static ./static_build


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONOPTIMIZE=1\
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/root/.local/bin:$PATH" \
    LOG_LEVEL=WARNING

WORKDIR /app

RUN apt update  \
    && apt install -y --no-install-recommends build-essential curl pkg-config libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir /usr/sessions \
    && mkdir -p /home/appuser/.cache/uv

COPY --from=builder /app /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /root/.local /root/.local

RUN useradd -u 10001 -r -s /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app /home/appuser /opt/venv
USER appuser

CMD ["uv", "run", "uvicorn", "app.asgi:application", \
     "--host", "0.0.0.0", "--port", "8246", "--workers", "4", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
