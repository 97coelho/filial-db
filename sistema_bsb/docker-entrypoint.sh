#!/bin/sh
set -eu

flask db upgrade
flask seed
exec "$@"
