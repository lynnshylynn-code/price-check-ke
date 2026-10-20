FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY data ./data

RUN pip install --no-cache-dir . \
    && adduser --system --group appuser

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "uvicorn price_check_api.main:app --app-dir src --host 0.0.0.0 --port ${PORT:-8000}"]
