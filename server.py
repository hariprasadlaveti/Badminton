from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlparse
from urllib.request import Request, urlopen
import json
import sqlite3

ROOT = Path(__file__).parent
DATABASE = ROOT / "badminton.sqlite3"
HOST = "127.0.0.1"
PORT = 8000
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)


def record_to_row(record):
    return {
        "id": record["id"],
        "date": record["date"],
        "name": record.get("name"),
        "record_type": record.get("recordType", "participation"),
        "value": record.get("value"),
        "amount": record.get("amount"),
        "sponsor": record.get("sponsor"),
    }


def record_from_mapping(row):
    record = {
        "id": row["id"],
        "date": row["date"],
        "recordType": row["record_type"],
    }
    for key in ("name", "value", "amount", "sponsor"):
        value = row.get(key)
        if value is not None:
            record[key] = value
    return record


def supabase_request(method, path, payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        f"{SUPABASE_URL}/rest/v1/{path}",
        data=body,
        method=method,
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            content = response.read().decode("utf-8")
            return json.loads(content) if content else None
    except HTTPError as error:
        detail = error.read().decode("utf-8")
        raise RuntimeError(f"Supabase request failed: {error.code} {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Supabase request failed: {error.reason}") from error


def connection():
    database = sqlite3.connect(DATABASE)
    database.row_factory = sqlite3.Row
    database.execute(
        """
        CREATE TABLE IF NOT EXISTS records (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            name TEXT,
            record_type TEXT NOT NULL,
            value REAL,
            amount REAL,
            sponsor TEXT
        )
        """
    )
    database.commit()
    return database


def record_from_row(row):
    return record_from_mapping(row)


def get_records():
    if USE_SUPABASE:
        rows = supabase_request("GET", "records?select=*&order=id.asc") or []
        return [record_from_mapping(row) for row in rows]
    with connection() as database:
        rows = database.execute("SELECT * FROM records ORDER BY id").fetchall()
    return [record_from_row(row) for row in rows]


def save_record(record):
    if USE_SUPABASE:
        supabase_request("POST", "records", record_to_row(record))
        return
    with connection() as database:
        database.execute(
            """
            INSERT INTO records (id, date, name, record_type, value, amount, sponsor)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                date=excluded.date,
                name=excluded.name,
                record_type=excluded.record_type,
                value=excluded.value,
                amount=excluded.amount,
                sponsor=excluded.sponsor
            """,
            (
                record["id"],
                record["date"],
                record.get("name"),
                record.get("recordType", "participation"),
                record.get("value"),
                record.get("amount"),
                record.get("sponsor"),
            ),
        )


def delete_record(record_id):
    if USE_SUPABASE:
        supabase_request("DELETE", f"records?id=eq.{quote(record_id, safe='')}")
        return
    with connection() as database:
        database.execute("DELETE FROM records WHERE id = ?", (record_id,))


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/records":
            self.send_json(200, get_records())
            return
        if path == "/api/health":
            self.send_json(200, {"ok": True, "database": "supabase" if USE_SUPABASE else DATABASE.name})
            return
        if path == "/" or path == "/index.html":
            content = (ROOT / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return
        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/api/records", "/api/records/batch"):
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or "{}")
        records = payload if isinstance(payload, list) else [payload]
        for record in records:
            save_record(record)
        self.send_json(200, {"saved": len(records)})

    def do_DELETE(self):
        path = urlparse(self.path).path
        prefix = "/api/records/"
        if not path.startswith(prefix):
            self.send_error(404)
            return
        record_id = unquote(path[len(prefix):])
        delete_record(record_id)
        self.send_json(200, {"deleted": record_id})

    def log_message(self, format_string, *args):
        print(format_string % args)


if __name__ == "__main__":
    if not USE_SUPABASE:
        connection().close()
    print(f"Badminton Attendance shared database: http://localhost:{PORT}")
    print(f"Database backend: {'Supabase' if USE_SUPABASE else 'SQLite'}")
    if USE_SUPABASE:
        print(f"Supabase URL: {SUPABASE_URL}")
    else:
        print(f"SQLite file: {DATABASE}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
