# --- Stage 1: Build dependencies ---
FROM python:3.13-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Stage 2: Production image ---
FROM python:3.13-slim AS production

# Security: no root, no shell fallback
RUN groupadd -r appuser && useradd -r -g appuser -s /usr/sbin/nologin appuser

# Copy only installed packages
COPY --from=builder /install /usr/local

# App code
WORKDIR /app
COPY chore_calendar_app.py gunicorn.conf.py ./

# Files: read-only for all. Directories: read+execute for traversal.
RUN find /app -type f -exec chmod 444 {} + && \
    find /app -type d -exec chmod 555 {} +

# No .pyc files, unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

USER appuser

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/')" || exit 1

ENTRYPOINT ["gunicorn", "-c", "gunicorn.conf.py", "chore_calendar_app:app"]
