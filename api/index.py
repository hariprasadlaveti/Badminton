from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import server  # noqa: E402


class handler(server.Handler):
    def _run(self, action):
        if not server.USE_SUPABASE:
            present = {name: bool(os.environ.get(name, "").strip()) for name in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY")}
            self.send_json(500, {"ok": False, "error": "Supabase env vars missing", "present": present, "vercel_env": os.environ.get("VERCEL_ENV")})
            return
        try:
            action()
        except RuntimeError as error:
            self.send_json(502, {"ok": False, "error": str(error)})

    def do_GET(self):
        self._run(super().do_GET)

    def do_POST(self):
        self._run(super().do_POST)

    def do_DELETE(self):
        self._run(super().do_DELETE)
