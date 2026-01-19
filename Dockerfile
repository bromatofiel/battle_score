# ===== builder step =====
FROM python:3.13.8-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
# Copy from the cache instead of linking since it's a separate stage
ENV UV_LINK_MODE=copy

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# ===== runner steps =====
FROM python:3.13.8-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBCONF_NOWARNINGS=yes
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Paris
ENV PATH="/app/.venv/bin:$PATH"

# System layer
COPY Aptfile Aptfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends $(cat Aptfile) && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir /static /logs

# Dependencies layer
COPY --from=builder /app/.venv /app/.venv

# Set cache
RUN tldextract --update

# Javascript layer
RUN apt-get update && apt-get install -y --no-install-recommends npm && \
    npm install -g @redocly/cli@latest && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Source layer
COPY . .

# Statics
RUN python manage.py collectstatic --noinput
