#!/bin/sh
set -eu

python <<'PY'
import os
import sys
import time

import psycopg

url = os.environ["DATABASE_URL"]
if url.startswith("postgres://"):
    url = "postgresql://" + url.removeprefix("postgres://")

last_error = "unknown"
for attempt in range(30):
    try:
        with psycopg.connect(url, connect_timeout=2) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
        sys.exit(0)
    except Exception as exc:
        last_error = str(exc)
        print(f"waiting for postgres ({attempt + 1}/30): {last_error}", flush=True)
        time.sleep(1)

print(f"postgres did not become ready: {last_error}", file=sys.stderr)
sys.exit(1)
PY

python manage.py migrate --noinput
exec python manage.py runserver 0.0.0.0:8000
