from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import server  # noqa: E402


class handler(server.Handler):
    def _run(self, action):
        if not server.USE_SUPABASE:
            self.send_json(500, {"ok": False, "error": "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in Vercel"})
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
