import json
import re
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_TELEMETRY_PATH = Path(__file__).resolve().parent.parent / "data" / "telemetry_logs.json"


class TelemetryRAGEngine:
    """Offline-first deterministic RAG engine over structured field telemetry logs."""

    def __init__(self, log_path: str | Path = DEFAULT_TELEMETRY_PATH) -> None:
        self.log_path = Path(log_path)
        self.logs: List[Dict[str, Any]] = self._load_logs()

    def _load_logs(self) -> List[Dict[str, Any]]:
        if not self.log_path.exists():
            return []
        try:
            with self.log_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {tok for tok in re.findall(r"[a-z0-9_]+", text.lower()) if len(tok) > 2}

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve top_k relevant telemetry records using deterministic token overlap."""
        query_tokens = self._tokenize(query)
        if not query_tokens or not self.logs:
            return self.logs[:top_k]

        scored: List[tuple[int, Dict[str, Any]]] = []
        for entry in self.logs:
            haystack = " ".join(
                str(entry.get(k, ""))
                for k in ("section", "species", "category", "observation", "action_taken")
            )
            entry_tokens = self._tokenize(haystack)
            overlap = len(query_tokens.intersection(entry_tokens))
            if overlap > 0:
                scored.append((overlap, entry))

        scored.sort(key=lambda item: item[0], reverse=True)
        if not scored:
            return self.logs[:top_k]
        return [item[1] for item in scored[:top_k]]
