# ---- Build stage ----
FROM python:3.12-slim AS builder

WORKDIR /build

COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install .

# ---- Runtime stage ----
FROM python:3.12-slim AS runtime

# Create non-root user
RUN groupadd -r linkdrip && useradd -r -g linkdrip -d /app -s /sbin/nologin linkdrip

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY src/ ./src/

# Create data directory for SQLite database
RUN mkdir -p /app/data && chown -R linkdrip:linkdrip /app

# Switch to non-root user
USER linkdrip

# Expose port
EXPOSE 8000

# Environment defaults
ENV APP_URL=http://localhost:8000 \
    DATABASE_URL=sqlite+aiosqlite:///./data/linkdrip.db \
    SECRET_KEY=change-me-in-production

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
