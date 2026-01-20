# ===== builder step =====
FROM python:3.13.8-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install build dependencies (removing apt list lighten docker image size)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential python3-dev libssl-dev libffi-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install dependencies into a central location (requirements.txt is used to avoid conflicts with local .venv)
COPY pyproject.toml uv.lock* README.md LICENSE.md* ./
COPY core/version.py core/version.py
RUN uv export --no-dev -o requirements.txt && \
    uv pip install --system -r requirements.txt


# ===== runner steps =====
FROM python:3.13.8-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBCONF_NOWARNINGS=yes
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Paris

# System layer
COPY Aptfile Aptfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends $(cat Aptfile) && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir /static /logs

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

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


# ===== devrunner step =====
FROM runner AS devrunner

# Install uv for development/bootstrapping
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install missing dev dependencies (into system python for dev image)
RUN uv pip install --system .[dev] || true
