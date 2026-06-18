FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY tests/ ./tests/

ENV ARCHIVE_PATH=/archive
ENV CACHE_DIR=/app/cache
ENV BLOG_TITLE="MyBlog"
ENV PORT=8862

RUN mkdir -p /app/cache

EXPOSE 8862

CMD ["gunicorn", "--bind", "0.0.0.0:8862", "--workers", "1", "--timeout", "300", "--log-level", "info", "app.main:app"]
