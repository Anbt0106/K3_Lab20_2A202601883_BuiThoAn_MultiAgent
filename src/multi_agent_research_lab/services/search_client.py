"""Shared Tavily-first search client with offline corpus and mock fallbacks."""

import json
import re
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.schemas import SourceDocument


class SearchClient:
    """Search Tavily first, then the teacher's offline corpus, then mock data."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._offline_index = OfflineCorpusIndex(Path(self.settings.offline_corpus_dir))

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Return normalized documents using the shared provider precedence."""

        if not query.strip():
            raise ValueError("Search query must not be empty")
        max_results = max(1, min(max_results, 20))
        tavily_error: str | None = None
        if self.settings.tavily_api_key:
            try:
                tavily_results = self._search_tavily(query, max_results)
                if tavily_results:
                    return [self._tavily_document(item) for item in tavily_results]
            except (HTTPError, URLError, TimeoutError, ValueError) as exc:
                tavily_error = str(exc)

        offline_results = self._offline_index.search(query, max_results)
        if offline_results:
            return offline_results
        return self._mock_results(query, max_results, fallback_reason=tavily_error)

    def _search_tavily(self, query: str, max_results: int) -> list[dict[str, Any]]:
        if not self.settings.tavily_api_key:
            return []
        request = Request(
            "https://api.tavily.com/search",
            data=json.dumps(
                {
                    "api_key": self.settings.tavily_api_key,
                    "query": query,
                    "max_results": max_results,
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.settings.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        results = cast(list[dict[str, Any]], payload.get("results", []))
        return results[:max_results]

    @staticmethod
    def _tavily_document(item: dict[str, Any]) -> SourceDocument:
        return SourceDocument(
            title=item.get("title", "Untitled source"),
            url=item.get("url"),
            snippet=item.get("content", item.get("snippet", "")),
            metadata={"provider": "tavily"},
        )

    @staticmethod
    def _mock_results(
        query: str, max_results: int, fallback_reason: str | None = None
    ) -> list[SourceDocument]:
        metadata: dict[str, Any] = {"provider": "mock"}
        if fallback_reason:
            metadata["fallback_reason"] = fallback_reason
        return [
            SourceDocument(
                title=f"Mock source {index} for: {query}",
                url=f"https://example.invalid/mock/{index}",
                snippet=f"Synthetic evidence generated for the query: {query}.",
                metadata=metadata,
            )
            for index in range(1, max_results + 1)
        ]


class OfflineCorpusIndex:
    """Keyword index over the teacher-provided topic JSON files."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._topics = self._load_topics()

    def _load_topics(self) -> list[dict[str, Any]]:
        topics_dir = self.root / "topics"
        if not topics_dir.is_dir():
            return []
        topics: list[dict[str, Any]] = []
        for path in sorted(topics_dir.glob("*.json")):
            try:
                topics.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        return topics

    def search(self, query: str, max_results: int) -> list[SourceDocument]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []
        ranked_topics = sorted(
            ((self._topic_score(topic, query_tokens), topic) for topic in self._topics),
            key=lambda item: item[0],
            reverse=True,
        )
        if not ranked_topics or ranked_topics[0][0] == 0:
            return []
        topic = ranked_topics[0][1]
        topic_id = topic.get("benchmark_metadata", {}).get("topic_id") or "unknown"
        candidates = self._candidates(topic, topic_id, query_tokens)
        candidates.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in candidates[:max_results] if item[0] > 0]

    @staticmethod
    def _topic_score(topic: dict[str, Any], query_tokens: set[str]) -> int:
        topic_info = topic.get("topic", {})
        text = " ".join(
            str(value)
            for value in (
                topic_info.get("name", ""),
                topic_info.get("research_question", ""),
                topic_info.get("tags", []),
            )
        )
        return len(query_tokens & _tokens(text))

    @staticmethod
    def _candidates(
        topic: dict[str, Any], topic_id: str, query_tokens: set[str]
    ) -> list[tuple[int, SourceDocument]]:
        knowledge = topic.get("knowledge_base", {})
        candidates: list[tuple[int, SourceDocument]] = []
        for item in knowledge.get("source_documents", []):
            text = (
                f"{item.get('title', '')} {item.get('full_text', '')} "
                f"{' '.join(item.get('key_takeaways', []))}"
            )
            candidates.append(
                (
                    len(query_tokens & _tokens(text)),
                    SourceDocument(
                        title=item.get("title", "Untitled source"),
                        url=item.get("provenance_url"),
                        snippet=item.get("full_text", "")[:1200],
                        metadata={
                            "provider": "offline",
                            "topic_id": topic_id,
                            "document_id": item.get("document_id"),
                            "is_synthetic": item.get("is_synthetic", False),
                        },
                    ),
                )
            )
        for item in knowledge.get("knowledge_articles", []):
            text = f"{item.get('title', '')} {item.get('content', '')}"
            candidates.append(
                (
                    len(query_tokens & _tokens(text)),
                    SourceDocument(
                        title=item.get("title", "Untitled article"),
                        snippet=item.get("content", "")[:1200],
                        metadata={
                            "provider": "offline",
                            "topic_id": topic_id,
                            "article_id": item.get("article_id"),
                            "is_synthetic": False,
                        },
                    ),
                )
            )
        return candidates


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.casefold()) if len(token) >= 3}
