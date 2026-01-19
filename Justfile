
# Start development environment
dev:
    docker compose up

# Start development environment (detached)
start:
    docker compose up -d

# Stop development environment
stop:
    docker compose down

# Force rebuild of development images
update:
    docker compose build --no-cache

