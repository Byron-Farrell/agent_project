FROM python:3.12-slim-bookworm

RUN pip install --no-cache-dir --root-user-action=ignore uv==0.13.8

WORKDIR /app

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:${PATH}"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY . .
RUN chmod +x docker-entrypoint.sh \
    && mv docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
