FROM python:3.12.11

ENV PYTHONUNBUFFERED=1
ENV UV_NO_CACHE=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

COPY pyproject.toml uv.lock /app/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

COPY ./migrations /app/migrations
COPY ./alembic.ini /app/alembic.ini
COPY app /app/app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
