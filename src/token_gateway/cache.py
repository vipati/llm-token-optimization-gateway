import json
import os
import threading
import time
from collections import Counter, OrderedDict
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from token_gateway.normalization import fingerprint
from token_gateway.text import cosine_similarity, term_vector

Clock = Callable[[], float]


class CacheEntry(BaseModel):
    key: str
    prompt: str
    response: str
    created_at: float = 0.0


class ExactPromptCache:
    """Thread-safe LRU cache keyed on the normalized prompt, with TTL and optional persistence.

    `namespace` separates entries that must never be shared, such as responses from different
    models. When `path` is set, the cache is loaded on start-up and written atomically on change.
    """

    def __init__(
        self,
        path: Path | None = None,
        max_entries: int = 10_000,
        ttl_seconds: float | None = None,
        clock: Clock = time.time,
    ) -> None:
        self.path = path
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()
        if self.path and self.path.exists():
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            for key, value in raw.items():
                self._entries[key] = CacheEntry.model_validate(value)

    def key_for(self, prompt: str, namespace: str = "") -> str:
        return fingerprint(namespace, prompt)

    def get(self, prompt: str, namespace: str = "") -> CacheEntry | None:
        key = self.key_for(prompt, namespace)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if self._expired(entry):
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return entry

    def set(self, prompt: str, response: str, namespace: str = "") -> CacheEntry:
        key = self.key_for(prompt, namespace)
        entry = CacheEntry(key=key, prompt=prompt, response=response, created_at=self._clock())
        with self._lock:
            self._entries[key] = entry
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)
            self._flush()
        return entry

    def __len__(self) -> int:
        return len(self._entries)

    def _expired(self, entry: CacheEntry) -> bool:
        return self.ttl_seconds is not None and self._clock() - entry.created_at > self.ttl_seconds

    def _flush(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {key: entry.model_dump() for key, entry in self._entries.items()}
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(temp_path, self.path)


class _SemanticEntry(BaseModel):
    question: str
    response: str
    vector: dict[str, int]
    created_at: float


class SemanticMatch(BaseModel):
    question: str
    response: str
    similarity: float


class SemanticCache:
    """Serves a cached answer when a new question is close enough to one already answered.

    Matching is scoped to the same model and the same context, so a paraphrased question about
    the same documents can reuse an answer, but a similar question about different documents
    cannot. Similarity is cosine over stemmed content-word counts: cheap, deterministic, and
    dependency-free. An embedding model would catch more paraphrases, at the cost of a model call.
    """

    def __init__(
        self,
        threshold: float = 0.8,
        max_entries: int = 10_000,
        ttl_seconds: float | None = None,
        clock: Clock = time.time,
    ) -> None:
        self.threshold = threshold
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._scopes: OrderedDict[str, list[_SemanticEntry]] = OrderedDict()
        self._size = 0

    def lookup(self, question: str, scope: str) -> SemanticMatch | None:
        vector = term_vector(question)
        now = self._clock()
        with self._lock:
            entries = self._scopes.get(scope)
            if not entries:
                return None
            live = [entry for entry in entries if not self._expired(entry, now)]
            self._size -= len(entries) - len(live)
            self._scopes[scope] = live
            best: SemanticMatch | None = None
            for entry in live:
                similarity = cosine_similarity(vector, Counter(entry.vector))
                if similarity >= self.threshold and (best is None or similarity > best.similarity):
                    best = SemanticMatch(
                        question=entry.question, response=entry.response, similarity=similarity
                    )
            if best:
                self._scopes.move_to_end(scope)
            return best

    def store(self, question: str, response: str, scope: str) -> None:
        entry = _SemanticEntry(
            question=question,
            response=response,
            vector=dict(term_vector(question)),
            created_at=self._clock(),
        )
        with self._lock:
            self._scopes.setdefault(scope, []).append(entry)
            self._scopes.move_to_end(scope)
            self._size += 1
            while self._size > self.max_entries and self._scopes:
                oldest_scope, oldest_entries = next(iter(self._scopes.items()))
                oldest_entries.pop(0)
                self._size -= 1
                if not oldest_entries:
                    del self._scopes[oldest_scope]

    def __len__(self) -> int:
        return self._size

    def _expired(self, entry: _SemanticEntry, now: float) -> bool:
        return self.ttl_seconds is not None and now - entry.created_at > self.ttl_seconds
