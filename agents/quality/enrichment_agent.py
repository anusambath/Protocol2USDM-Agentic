"""
EnrichmentAgent - Adds terminology codes from NCI EVS API to extracted entities.

Responsibilities:
- Identify entities requiring terminology codes (indications, procedures, interventions)
- Query the EVS API for NCI C-codes matching entity names
- Rank by relevance and select the best match when multiple matches found
- Add Code entities with NCI codes to enriched entities
- Cache EVS responses to minimize API calls
- Handle EVS API failures gracefully with retry logic
- Track enrichment coverage (percentage of entities enriched)
- Support manual code overrides for incorrect automatic matches
- Update the Context Store with enriched entities
- Generate provenance indicating automatic vs manual enrichment
"""

import logging
import time
import uuid
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, Tuple

from agents.base import AgentCapabilities, AgentResult, AgentState, AgentTask, BaseAgent
from agents.context_store import ContextEntity, ContextStore, EntityProvenance

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enrichable entity types
# ---------------------------------------------------------------------------

ENRICHABLE_ENTITY_TYPES = frozenset({
    "indication",
    "procedure",
    "investigational_product",
    "study_intervention",
    "medical_device",
})


# ---------------------------------------------------------------------------
# EVS API data models
# ---------------------------------------------------------------------------

@dataclass
class EVSConcept:
    """A concept returned from the NCI EVS API."""
    code: str               # e.g. "C12345"
    name: str               # preferred name
    synonyms: List[str] = field(default_factory=list)
    definition: str = ""
    semantic_types: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "synonyms": self.synonyms,
            "definition": self.definition,
            "semantic_types": self.semantic_types,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EVSConcept":
        return cls(
            code=data["code"],
            name=data["name"],
            synonyms=data.get("synonyms", []),
            definition=data.get("definition", ""),
            semantic_types=data.get("semantic_types", []),
        )


@dataclass
class EnrichmentResult:
    """Result of enriching a single entity."""
    entity_id: str
    entity_type: str
    entity_name: str
    code: Optional[str] = None
    code_system: str = "NCI Thesaurus"
    code_system_version: str = "24.0"
    display_name: str = ""
    confidence: float = 0.0
    source: str = "automatic"   # "automatic" or "manual"
    matched_concept: Optional[EVSConcept] = None
    error: Optional[str] = None

    @property
    def enriched(self) -> bool:
        return self.code is not None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "entity_name": self.entity_name,
            "enriched": self.enriched,
            "source": self.source,
        }
        if self.code:
            result["code"] = self.code
            result["code_system"] = self.code_system
            result["code_system_version"] = self.code_system_version
            result["display_name"] = self.display_name
            result["confidence"] = self.confidence
        if self.error:
            result["error"] = self.error
        return result


@dataclass
class EnrichmentCoverageMetrics:
    """Tracks enrichment coverage statistics."""
    total_entities: int = 0
    enrichable_entities: int = 0
    enriched_entities: int = 0
    failed_entities: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    api_calls: int = 0
    api_failures: int = 0

    @property
    def coverage_percent(self) -> float:
        if self.enrichable_entities == 0:
            return 0.0
        return (self.enriched_entities / self.enrichable_entities) * 100.0

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return (self.cache_hits / total) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_entities": self.total_entities,
            "enrichable_entities": self.enrichable_entities,
            "enriched_entities": self.enriched_entities,
            "failed_entities": self.failed_entities,
            "coverage_percent": round(self.coverage_percent, 2),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": round(self.cache_hit_rate, 2),
            "api_calls": self.api_calls,
            "api_failures": self.api_failures,
        }


# ---------------------------------------------------------------------------
# EVS API Client Protocol (interface for dependency injection / mocking)
# ---------------------------------------------------------------------------

class EVSAPIClient(Protocol):
    """Protocol for NCI EVS API client. Implementations must provide search_concepts."""

    def search_concepts(self, term: str, max_results: int = 10) -> List[EVSConcept]:
        """Search EVS for concepts matching the given term."""
        ...


class DefaultEVSAPIClient:
    """
    Default EVS API client — calls the NCI EVS REST API (EVSREST).

    API docs: https://api-evsrest.nci.nih.gov/api/v1/
    No authentication required for public NCI Thesaurus searches.
    """

    def __init__(self, base_url: str = "https://api-evsrest.nci.nih.gov/api/v1", timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def search_concepts(self, term: str, max_results: int = 10) -> List[EVSConcept]:
        """
        Search NCI Thesaurus (NCIt) for concepts matching the given term.

        Uses the EVSREST /concept/ncit/search endpoint.
        """
        import requests

        url = f"{self.base_url}/concept/ncit/search"
        params = {
            "term": term,
            "pageSize": max_results,
            "include": "minimal",
        }

        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f"EVS API request failed for '{term}': {e}")

        concepts = []
        for item in data.get("concepts", []):
            synonyms = []
            for syn in item.get("synonyms", []):
                if isinstance(syn, dict):
                    synonyms.append(syn.get("name", ""))
                elif isinstance(syn, str):
                    synonyms.append(syn)

            concepts.append(EVSConcept(
                code=item.get("code", ""),
                name=item.get("name", ""),
                definition=item.get("definition", ""),
                synonyms=synonyms,
            ))

        return concepts


# ---------------------------------------------------------------------------
# LRU Cache for EVS responses
# ---------------------------------------------------------------------------

class EVSCache:
    """Simple LRU cache for EVS API responses. Thread-safe."""

    def __init__(self, max_size: int = 1000):
        import threading
        self._max_size = max_size
        self._cache: OrderedDict[str, List[EVSConcept]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, term: str) -> Optional[List[EVSConcept]]:
        """Get cached concepts for a term. Returns None on miss."""
        key = term.lower().strip()
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                return self._cache[key]
        return None

    def put(self, term: str, concepts: List[EVSConcept]) -> None:
        """Cache concepts for a term."""
        key = term.lower().strip()
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = concepts
            # Evict oldest if over capacity
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    def contains(self, term: str) -> bool:
        with self._lock:
            return term.lower().strip() in self._cache


# ---------------------------------------------------------------------------
# Code ranking helpers
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Normalize text for comparison."""
    return text.lower().strip()


def compute_relevance_score(entity_name: str, concept: EVSConcept) -> float:
    """
    Compute a relevance score [0.0, 1.0] for how well a concept matches an entity name.

    Scoring:
    - Exact match on preferred name: 1.0
    - Exact match on a synonym: 0.9
    - Preferred name contains entity name (or vice versa): 0.7
    - Synonym contains entity name (or vice versa): 0.6
    - Partial word overlap: proportional score
    """
    norm_name = _normalize(entity_name)
    norm_concept = _normalize(concept.name)

    # Exact match on preferred name
    if norm_name == norm_concept:
        return 1.0

    # Exact match on synonym
    norm_synonyms = [_normalize(s) for s in concept.synonyms]
    if norm_name in norm_synonyms:
        return 0.9

    # Containment checks
    if norm_name in norm_concept or norm_concept in norm_name:
        return 0.7

    for syn in norm_synonyms:
        if norm_name in syn or syn in norm_name:
            return 0.6

    # Word overlap
    name_words = set(norm_name.split())
    concept_words = set(norm_concept.split())
    if name_words and concept_words:
        overlap = len(name_words & concept_words)
        total = len(name_words | concept_words)
        if total > 0:
            return round(0.5 * (overlap / total), 2)

    return 0.0


def rank_concepts(entity_name: str, concepts: List[EVSConcept]) -> List[Tuple[EVSConcept, float]]:
    """Rank concepts by relevance to the entity name. Returns sorted (concept, score) pairs."""
    scored = [(c, compute_relevance_score(entity_name, c)) for c in concepts]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


# ---------------------------------------------------------------------------
# EnrichmentAgent
# ---------------------------------------------------------------------------

class EnrichmentAgent(BaseAgent):
    """
    Adds terminology codes from NCI EVS API to extracted entities.

    Capabilities:
    - Identify entities requiring terminology codes
    - Query EVS API for NCI C-codes
    - Rank and select best match from multiple results
    - Add Code entities with NCI codes to enriched entities
    - Cache EVS responses (LRU)
    - Retry EVS API failures with exponential backoff
    - Track enrichment coverage metrics
    - Support manual code overrides
    - Update Context Store with enriched entities
    - Generate provenance (automatic vs manual)
    """

    def __init__(
        self,
        agent_id: str = "enrichment_agent",
        config: Optional[Dict[str, Any]] = None,
        evs_client: Optional[EVSAPIClient] = None,
        cache_max_size: int = 1000,
    ):
        super().__init__(agent_id=agent_id, config=config or {})
        self._evs_client: EVSAPIClient = evs_client or DefaultEVSAPIClient()
        self._cache = EVSCache(max_size=cache_max_size)
        self._coverage = EnrichmentCoverageMetrics()
        self._manual_overrides: Dict[str, str] = {}  # entity_id -> NCI code
        self._enrichment_results: List[EnrichmentResult] = []
        self._max_retries: int = (config or {}).get("max_retries", 2)
        self._base_delay: float = (config or {}).get("base_delay", 0.5)
        self._min_confidence: float = (config or {}).get("min_confidence", 0.3)
        self._max_concurrent: int = (config or {}).get("max_concurrent", 8)
        import threading
        self._coverage_lock = threading.Lock()

    # --- Lifecycle ---

    def initialize(self) -> None:
        self.set_state(AgentState.READY)
        self._logger.info(
            f"[{self.agent_id}] Initialized. Enrichable types: {sorted(ENRICHABLE_ENTITY_TYPES)}"
        )

    def terminate(self) -> None:
        self._cache.clear()
        self.set_state(AgentState.TERMINATED)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="enrichment",
            input_types=["context_data"],
            output_types=["enriched_entities", "enrichment_report"],
            dependencies=["execution_extraction"],
            supports_parallel=False,
            timeout_seconds=300,
        )


    # --- Main execution ---

    def execute(self, task: AgentTask) -> AgentResult:
        """
        Enrich entities with NCI terminology codes.

        Input data can contain:
        - "entities": list of entity dicts
        - "context_store": a ContextStore instance
        - "manual_overrides": dict of entity_id -> NCI code
        """
        entities_data = task.input_data.get("entities", [])
        context_store: Optional[ContextStore] = (
            task.input_data.get("context_store") or self._context_store
        )
        manual_overrides = task.input_data.get("manual_overrides", {})

        # Register manual overrides
        self._manual_overrides.update(manual_overrides)

        # If no entities list, pull from context store
        if not entities_data and context_store:
            entities_data = self._entities_from_store(context_store)

        if not entities_data:
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                error="No entities provided for enrichment",
            )

        # Reset coverage metrics for this run
        self._coverage = EnrichmentCoverageMetrics()
        self._enrichment_results = []
        self._coverage.total_entities = len(entities_data)

        # Identify enrichable entities
        enrichable = self._identify_enrichable_entities(entities_data)
        self._coverage.enrichable_entities = len(enrichable)

        # Enrich entities concurrently
        results: List[EnrichmentResult] = [None] * len(enrichable)  # type: ignore[list-item]

        self._logger.info(
            f"[{self.agent_id}] Enriching {len(enrichable)} entities "
            f"(max_concurrent={self._max_concurrent})"
        )

        with ThreadPoolExecutor(max_workers=self._max_concurrent) as executor:
            future_to_idx = {
                executor.submit(self._enrich_entity, entity): idx
                for idx, entity in enumerate(enrichable)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                entity = enrichable[idx]
                entity_name = entity.get("data", {}).get("name", entity.get("id", "?"))
                try:
                    enrich_result = future.result()
                except Exception as e:
                    enrich_result = EnrichmentResult(
                        entity_id=entity.get("id", "unknown"),
                        entity_type=entity.get("entity_type", ""),
                        entity_name=entity_name,
                        error=str(e),
                    )

                results[idx] = enrich_result
                self._enrichment_results.append(enrich_result)

                if enrich_result.enriched:
                    with self._coverage_lock:
                        self._coverage.enriched_entities += 1
                    if context_store:
                        self._update_context_store(context_store, entity, enrich_result)
                elif enrich_result.error:
                    with self._coverage_lock:
                        self._coverage.failed_entities += 1

        self._logger.info(
            f"[{self.agent_id}] Enrichment complete: "
            f"{self._coverage.enriched_entities}/{len(enrichable)} enriched"
        )

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            success=True,
            data={
                "enrichment_results": [r.to_dict() for r in results],
                "coverage": self._coverage.to_dict(),
            },
            confidence_score=self._coverage.coverage_percent / 100.0 if self._coverage.enrichable_entities > 0 else 1.0,
            api_calls=self._coverage.api_calls,
        )

    # --- Entity identification ---

    def _identify_enrichable_entities(
        self, entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Filter entities to those that can be enriched with terminology codes."""
        enrichable = []
        for entity in entities:
            etype = entity.get("entity_type", "")
            if etype in ENRICHABLE_ENTITY_TYPES:
                data = entity.get("data", {})
                name = data.get("name", "")
                if name and isinstance(name, str) and name.strip():
                    enrichable.append(entity)
        return enrichable

    # --- Single entity enrichment ---

    def _enrich_entity(self, entity: Dict[str, Any]) -> EnrichmentResult:
        """Enrich a single entity with NCI code."""
        entity_id = entity.get("id", "unknown")
        entity_type = entity.get("entity_type", "")
        entity_name = entity.get("data", {}).get("name", "")

        # Check for manual override first
        if entity_id in self._manual_overrides:
            override_code = self._manual_overrides[entity_id]
            return EnrichmentResult(
                entity_id=entity_id,
                entity_type=entity_type,
                entity_name=entity_name,
                code=override_code,
                display_name=entity_name,
                confidence=1.0,
                source="manual",
            )

        # Query EVS (with cache and retry)
        concepts = self._query_evs_with_cache(entity_name)

        if concepts is None:
            # API failure after retries
            return EnrichmentResult(
                entity_id=entity_id,
                entity_type=entity_type,
                entity_name=entity_name,
                error="EVS API query failed after retries",
            )

        if not concepts:
            return EnrichmentResult(
                entity_id=entity_id,
                entity_type=entity_type,
                entity_name=entity_name,
                error="No matching concepts found in EVS",
            )

        # Rank and select best match
        ranked = rank_concepts(entity_name, concepts)
        best_concept, best_score = ranked[0]

        if best_score < self._min_confidence:
            return EnrichmentResult(
                entity_id=entity_id,
                entity_type=entity_type,
                entity_name=entity_name,
                error=f"Best match score {best_score} below threshold {self._min_confidence}",
            )

        return EnrichmentResult(
            entity_id=entity_id,
            entity_type=entity_type,
            entity_name=entity_name,
            code=best_concept.code,
            display_name=best_concept.name,
            confidence=best_score,
            source="automatic",
            matched_concept=best_concept,
        )

    # --- EVS query with cache and retry ---

    def _query_evs_with_cache(self, term: str) -> Optional[List[EVSConcept]]:
        """
        Query EVS for a term, using cache first.
        Returns None if all retries fail. Thread-safe.
        """
        # Check cache
        cached = self._cache.get(term)
        if cached is not None:
            with self._coverage_lock:
                self._coverage.cache_hits += 1
            return cached

        with self._coverage_lock:
            self._coverage.cache_misses += 1

        # Query with retry
        concepts = self._query_evs_with_retry(term)
        if concepts is not None:
            self._cache.put(term, concepts)
        return concepts

    def _query_evs_with_retry(self, term: str) -> Optional[List[EVSConcept]]:
        """Query EVS API with exponential backoff retry."""
        last_error: Optional[Exception] = None

        for attempt in range(self._max_retries):
            try:
                with self._coverage_lock:
                    self._coverage.api_calls += 1
                concepts = self._evs_client.search_concepts(term)
                return concepts
            except Exception as e:
                last_error = e
                with self._coverage_lock:
                    self._coverage.api_failures += 1
                if attempt < self._max_retries - 1:
                    delay = self._base_delay * (2 ** attempt)
                    self._logger.warning(
                        f"[{self.agent_id}] EVS API attempt {attempt + 1} failed for '{term}': {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    self._logger.error(
                        f"[{self.agent_id}] EVS API failed after {self._max_retries} attempts "
                        f"for '{term}': {last_error}"
                    )

        return None

    # --- Context Store update ---

    def _update_context_store(
        self,
        store: ContextStore,
        entity: Dict[str, Any],
        result: EnrichmentResult,
    ) -> None:
        """Update the Context Store with enrichment data."""
        entity_id = entity.get("id", "")
        if not entity_id:
            return

        try:
            existing = store.get_entity(entity_id)
            if existing:
                # Add code data to the entity
                codes = existing.data.get("codes", [])
                code_entry = {
                    "code": result.code,
                    "codeSystem": result.code_system,
                    "codeSystemVersion": result.code_system_version,
                    "decode": result.display_name,
                }
                codes.append(code_entry)

                store.update_entity(
                    entity_id,
                    {
                        "codes": codes,
                        "_enrichment_source": result.source,
                        "_enrichment_confidence": result.confidence,
                    },
                    agent_id=self.agent_id,
                )

                # Update provenance
                existing = store.get_entity(entity_id)
                if existing:
                    # source_agent_id preserved (original extractor attribution)
                    existing.provenance.confidence_score = result.confidence
        except (KeyError, ValueError) as exc:
            self._logger.warning(
                f"[{self.agent_id}] Could not update context store for entity {entity_id}: {exc}"
            )

    # --- Manual overrides ---

    def set_manual_override(self, entity_id: str, nci_code: str) -> None:
        """Set a manual code override for an entity."""
        self._manual_overrides[entity_id] = nci_code

    def remove_manual_override(self, entity_id: str) -> bool:
        """Remove a manual override. Returns True if it existed."""
        return self._manual_overrides.pop(entity_id, None) is not None

    def get_manual_overrides(self) -> Dict[str, str]:
        """Return all manual overrides."""
        return dict(self._manual_overrides)

    # --- Coverage metrics ---

    def get_coverage_metrics(self) -> EnrichmentCoverageMetrics:
        """Return current enrichment coverage metrics."""
        return self._coverage

    def get_enrichment_results(self) -> List[EnrichmentResult]:
        """Return all enrichment results from the last run."""
        return list(self._enrichment_results)

    # --- Helpers ---

    @staticmethod
    def _entities_from_store(store: ContextStore) -> List[Dict[str, Any]]:
        """Convert Context Store entities to list-of-dicts format."""
        result: List[Dict[str, Any]] = []
        for entity in store.query_entities():
            result.append({
                "id": entity.id,
                "entity_type": entity.entity_type,
                "data": entity.data,
                "relationships": entity.relationships,
            })
        return result

    @property
    def cache(self) -> EVSCache:
        """Expose cache for testing/inspection."""
        return self._cache
