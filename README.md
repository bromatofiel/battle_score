
# Installation

## Docker

Make sure you have the following dependencies installed on your system:

- make
- docker >= 19.03
- docker-compose >= 1.27
- gsutils >= 4.60
- gsed (on MacOS)

Then run the following commands:

```sh
# Create docker images
just update
# Start serveur
just start
# Run tests
just test
```

If you want any custom docker configuration, please use the `docker-compose.override.yml` file (and DON'T try to commit it). Example:

```yml
version: '3.7'

services:
  db:
	restart: always

  cache:
	restart: always

server:
    tty: yes
    stdin_open: yes
	restart: always

worker:
	restart: always
```

## Localhost

UV is required to install BattleScore. See https://docs.astral.sh/uv/getting-started/installation/#pypi for UV install options.

```sh
uv sync
```


# Configuration

To customize django, please use the `.env` file (NEVER commit it). Example:

```ini
SECRET_KEY=s3cr3t(*_*)
ALLOWED_HOSTS=*
DEBUG_QUERIES=False
LOGGING_COLORED=True
API_STATIC_CACHE_DURATION=0

USE_LOCAL_SERVER=True
USE_LOCAL_MEDIA=True
USE_LOCAL_STATIC=True

```

NB: for more exhaustive killing options, ask a buddy dev ;)


# License

BattleScore is released under the **Business Source License (BSL)**.

## What you can do
- View and study the source code
- Use BattleScore for personal or educational purposes
- Self-host BattleScore for a **non-profit association**, provided that:
  - it is used only internally;
  - members are not charged for access or participation;
  - no revenue is generated using the software.

## What requires a paid license
- Running BattleScore as a paid service (SaaS)
- Managing paid tournaments or events
- Use by clubs or associations charging membership or participation fees
- Commercial hosting, resale, or integration

For commercial licenses (SaaS or on-premise), contact me on LinkedIn: https://www.linkedin.com/in/j%C3%A9r%C3%A9my-marc-98877423/
