import hashlib
import json
from pathlib import Path

from pydantic import BaseModel

from token_gateway.normalization import normalize_request


class CacheEntry(BaseModel):
    key: str
    prompt: str
    response: str


class ExactPromptCache:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self._entries: dict[str, CacheEntry] = {}
        if self.path and self.path.exists():
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self._entries = {key: CacheEntry.model_validate(value) for key, value in raw.items()}

    def key_for(self, prompt: str) -> str:
        normalized = normalize_request(prompt)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def get(self, prompt: str) -> CacheEntry | None:
        return self._entries.get(self.key_for(prompt))

    def set(self, prompt: str, response: str) -> CacheEntry:
        key = self.key_for(prompt)
        entry = CacheEntry(key=key, prompt=prompt, response=response)
        self._entries[key] = entry
        self._flush()
        return entry

    def _flush(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {key: entry.model_dump() for key, entry in self._entries.items()}
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

