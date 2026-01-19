#!/bin/bash

set -ex

echo "sleep for 5 seconds for PGSQL init" && sleep 5

exec "$@"
