# Doc: https://suyog942.medium.com/why-justfile-outshines-makefile-in-modern-devops-workflows-a64d99b2e9f0

DOCKER			    := "docker exec -i"
DOCKER_TTY		    := "docker exec -it"
COMPOSE			    := "docker compose"
CONTAINER_SERVER    := "bts_server"
PYTHON              := DOCKER_TTY + " " + CONTAINER_SERVER + " python"
DJANGO              := PYTHON + " manage.py"

default:
    just --list

# Start development environment
dev:
    {{ COMPOSE }} up

# Start development environment (detached)
start:
    {{ COMPOSE }} up

start-d:
    {{ COMPOSE }} up -d

# Stop development environment
stop:
    {{ COMPOSE }} down

# Force rebuild of development images
update:
    {{ COMPOSE }} build --no-cache

# Connect to local container
ssh:
    {{ DOCKER_TTY }} {{ CONTAINER_SERVER }} bash

# Connect to local container
shell:
    {{ PYTHON }} manage.py shell_plus

add *args:
    {{ DOCKER_TTY }} {{ CONTAINER_SERVER }} uv add {{ args }}


# Model targets
migrate *args:
    {{ DJANGO }} migrate {{ args }}

showmigrations:
    {{ DJANGO }} showmigrations

makemigrations *args:
    {{ DJANGO }} makemigrations {{ args }}

# Run tests
test *args:
    {{ DJANGO }} test {{ args }}
