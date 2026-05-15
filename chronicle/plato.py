"""PlatoChronicle — PLATO room bridge for any agent's chronicle.

Usage:
    from chronicle import PlatoChronicle
    pc = PlatoChronicle("https://localhost:8847", "oracle1-checkin")
    pc.report("Gate pipeline deployed")
"""

from .core import Chronicle
import json, urllib.request, ssl

class PlatoChronicle:
    """Chronicle that submits to a PLATO room AND saves locally."""

    def __init__(self, plato_url, room, api_key="", local_name=None):
        self.url = plato_url.rstrip("/")
        self.room = room
        self.key = api_key
        self.local = Chronicle(local_name or f"plato-{room}")
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.key:
            h["Authorization"] = f"Bearer {self.key}"
        return h

    def report(self, message, tags=None, metadata=None):
        """File a check-in to both PLATO room and local chronicle."""
        cid = self.local.check_in(message, tags=tags, metadata=metadata)
        tile = {
            "domain": self.room,
            "question": f"checkin/{cid}",
            "answer": message[:1950],
            "tags": (tags or []) + ["checkin"],
            "source": "fleet-chronicle",
            "confidence": 0.95,
        }
        try:
            data = json.dumps(tile).encode()
            req = urllib.request.Request(
                f"{self.url}/submit", data=data, headers=self._headers())
            resp = json.loads(urllib.request.urlopen(
                req, timeout=10, context=self._ctx).read())
            return f"ok:{resp.get('status','?')}"
        except Exception as e:
            return f"local:{e}"

    def history(self, limit=50):
        try:
            req = urllib.request.Request(
                f"{self.url}/room/{self.room}/history?limit={limit}",
                headers=self._headers())
            r = json.loads(urllib.request.urlopen(req, timeout=10, context=self._ctx).read())
            return r.get("tiles", []) if isinstance(r, dict) else r
        except:
            return self.local._read_entries(limit=limit)

    def generate_html(self, path=None):
        return self.local.generate_html(path)
