import json
import os
import sqlite3
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).parent
DATABASE = ROOT / "badminton.sqlite3"
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
BATCH_SIZE = 500


def require_environment():
    missing = []
    if not SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not SUPABASE_KEY:
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    if missing:
        names = ", ".join(missing)
        raise SystemExit(f"Missing environment variable(s): {names}")


def sqlite_records():
    if not DATABASE.exists():
        raise SystemExit(f"SQLite database not found: {DATABASE}")
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            "select id, date, name, record_type, value, amount, sponsor from records order by id"
        ).fetchall()
    finally:
        connection.close()
    return [
        {
            "id": row["id"],
            "date": row["date"],
            "name": row["name"],
            "record_type": row["record_type"],
            "value": row["value"],
            "amount": row["amount"],
            "sponsor": row["sponsor"],
        }
        for row in rows
    ]


def upsert_batch(records):
    request = Request(
        f"{SUPABASE_URL}/rest/v1/records",
        data=json.dumps(records).encode("utf-8"),
        method="POST",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            response.read()
    except HTTPError as error:
        detail = error.read().decode("utf-8")
        raise SystemExit(f"Supabase import failed: {error.code} {detail}") from error
    except URLError as error:
        raise SystemExit(f"Supabase import failed: {error.reason}") from error


def main():
    require_environment()
    records = sqlite_records()
    for start in range(0, len(records), BATCH_SIZE):
        upsert_batch(records[start:start + BATCH_SIZE])
    print(f"Imported {len(records)} record(s) into Supabase.")


if __name__ == "__main__":
    main()
