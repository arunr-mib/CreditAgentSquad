# API and worker image. Build from the repository root.
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /srv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend ./backend
COPY synthetic ./synthetic
COPY evals ./evals
ENV PYTHONPATH=/srv/backend PATH="/srv/.venv/bin:$PATH"
WORKDIR /srv/backend
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
