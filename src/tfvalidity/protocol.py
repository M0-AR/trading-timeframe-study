from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .utils import stable_hash


@dataclass
class TimeframeLock:
    path: Path

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _last_hash(self) -> str:
        if not self.path.exists():
            return "0" * 64
        last = "0" * 64
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    last = json.loads(line)["hash"]
        return last

    def record(self, event: str, payload: dict) -> dict:
        prev = self._last_hash()
        body = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            "payload": payload,
            "prev_hash": prev,
        }
        body["hash"] = stable_hash(body)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(body, sort_keys=True, default=str) + "\n")
        return body

    def verify(self) -> dict:
        prev = "0" * 64
        n = 0
        ok = True
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                body = {k: rec[k] for k in ("timestamp", "event", "payload", "prev_hash")}
                if rec["prev_hash"] != prev or stable_hash(body) != rec["hash"]:
                    ok = False
                prev = rec["hash"]
                n += 1
        return {"records": n, "valid": ok, "head": prev}
