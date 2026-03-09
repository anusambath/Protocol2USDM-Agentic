"""
Context Store - Shared knowledge repository for all agents.

Provides entity storage with versioning, relationship tracking,
provenance metadata, transactional updates, and JSON serialization.
"""

import copy
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class EntityProvenance:
    """Tracks the source and confidence of extracted data."""
    entity_id: str
    source_agent_id: str
    extraction_timestamp: datetime = field(default_factory=datetime.now)
    confidence_score: float = 0.0
    source_pages: List[int] = field(default_factory=list)
    model_used: str = ""
    version: int = 1
    parent_entity_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "source_agent_id": self.source_agent_id,
            "extraction_timestamp": self.extraction_timestamp.isoformat(),
            "confidence_score": self.confidence_score,
            "source_pages": self.source_pages,
            "model_used": self.model_used,
            "version": self.version,
            "parent_entity_id": self.parent_entity_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntityProvenance":
        return cls(
            entity_id=data["entity_id"],
            source_agent_id=data["source_agent_id"],
            extraction_timestamp=datetime.fromisoformat(data["extraction_timestamp"]),
            confidence_score=data.get("confidence_score", 0.0),
            source_pages=data.get("source_pages", []),
            model_used=data.get("model_used", ""),
            version=data.get("version", 1),
            parent_entity_id=data.get("parent_entity_id"),
        )


@dataclass
class ContextEntity:
    """Wrapper for entities stored in the Context Store."""
    id: str
    entity_type: str
    data: Dict[str, Any] = field(default_factory=dict)
    provenance: EntityProvenance = field(default_factory=lambda: EntityProvenance(entity_id="", source_agent_id=""))
    relationships: Dict[str, List[str]] = field(default_factory=dict)
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "data": self.data,
            "provenance": self.provenance.to_dict(),
            "relationships": self.relationships,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextEntity":
        prov = EntityProvenance.from_dict(data["provenance"])
        return cls(
            id=data["id"],
            entity_type=data["entity_type"],
            data=data.get("data", {}),
            provenance=prov,
            relationships=data.get("relationships", {}),
            version=data.get("version", 1),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


class _Transaction:
    """Internal transaction state for rollback support."""

    def __init__(self, transaction_id: str):
        self.transaction_id = transaction_id
        self.snapshot: Optional[Dict[str, Any]] = None
        self.created_at = datetime.now()


class ContextStore:
    """
    Shared knowledge repository for all agents.

    Features:
    - Entity storage with versioning
    - Relationship tracking between entities
    - Provenance metadata tracking
    - Query by ID, type, or attribute filters
    - Transactional updates with rollback
    - Thread-safe concurrent read access
    - JSON serialization/deserialization
    """

    def __init__(self):
        self._entities: Dict[str, ContextEntity] = {}
        self._type_index: Dict[str, Set[str]] = {}
        self._relationship_index: Dict[str, Set[str]] = {}
        self._lock = threading.RLock()
        self._active_transactions: Dict[str, _Transaction] = {}

    # --- CRUD Operations ---

    def add_entity(self, entity: ContextEntity) -> str:
        """Add a new entity. Raises ValueError if ID already exists."""
        with self._lock:
            if entity.id in self._entities:
                raise ValueError(f"Entity '{entity.id}' already exists")
            self._entities[entity.id] = entity
            self._index_entity(entity)
            logger.debug(f"Added entity: {entity.id} (type={entity.entity_type})")
            return entity.id

    def get_entity(self, entity_id: str) -> Optional[ContextEntity]:
        """Retrieve entity by ID."""
        with self._lock:
            return self._entities.get(entity_id)

    def update_entity(self, entity_id: str, data: Dict[str, Any],
                      agent_id: str = "") -> None:
        """
        Update an existing entity's data. Increments version.
        Raises KeyError if entity not found.
        """
        with self._lock:
            if entity_id not in self._entities:
                raise KeyError(f"Entity '{entity_id}' not found")
            entity = self._entities[entity_id]
            entity.data.update(data)
            entity.version += 1
            entity.updated_at = datetime.now()
            # agent_id param accepted but source_agent_id is preserved (original extractor keeps attribution)
            entity.provenance.version = entity.version

    def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity. Returns True if found and removed."""
        with self._lock:
            if entity_id not in self._entities:
                return False
            entity = self._entities.pop(entity_id)
            # Remove from type index
            type_set = self._type_index.get(entity.entity_type)
            if type_set:
                type_set.discard(entity_id)
            # Remove from relationship index
            self._relationship_index.pop(entity_id, None)
            # Remove references to this entity from others
            for other_id, related_ids in self._relationship_index.items():
                related_ids.discard(entity_id)
            for other_entity in self._entities.values():
                for rel_type, rel_ids in list(other_entity.relationships.items()):
                    if entity_id in rel_ids:
                        rel_ids.remove(entity_id)
            return True

    # --- Relationship Tracking ---

    def add_relationship(self, from_id: str, to_id: str,
                         relationship_type: str) -> None:
        """Add a typed relationship between two entities."""
        with self._lock:
            if from_id not in self._entities:
                raise KeyError(f"Source entity '{from_id}' not found")
            if to_id not in self._entities:
                raise KeyError(f"Target entity '{to_id}' not found")

            from_entity = self._entities[from_id]
            if relationship_type not in from_entity.relationships:
                from_entity.relationships[relationship_type] = []
            if to_id not in from_entity.relationships[relationship_type]:
                from_entity.relationships[relationship_type].append(to_id)

            if from_id not in self._relationship_index:
                self._relationship_index[from_id] = set()
            self._relationship_index[from_id].add(to_id)

    def get_related_entities(self, entity_id: str,
                             relationship_type: Optional[str] = None) -> List[ContextEntity]:
        """Get entities related to the given entity."""
        with self._lock:
            entity = self._entities.get(entity_id)
            if not entity:
                return []

            if relationship_type:
                related_ids = entity.relationships.get(relationship_type, [])
            else:
                related_ids = list(self._relationship_index.get(entity_id, set()))

            return [self._entities[rid] for rid in related_ids if rid in self._entities]

    # --- Query Interface ---

    def query_entities(self, entity_type: Optional[str] = None,
                       filters: Optional[Dict[str, Any]] = None) -> List[ContextEntity]:
        """Query entities by type and/or attribute filters."""
        with self._lock:
            if entity_type:
                entity_ids = self._type_index.get(entity_type, set())
                entities = [self._entities[eid] for eid in entity_ids if eid in self._entities]
            else:
                entities = list(self._entities.values())

            if filters:
                entities = [e for e in entities if self._matches_filters(e, filters)]

            return entities

    def query_by_attribute(self, key: str, value: Any) -> List[ContextEntity]:
        """Shorthand to query entities where data[key] == value."""
        return self.query_entities(filters={key: value})

    @property
    def entity_count(self) -> int:
        with self._lock:
            return len(self._entities)

    @property
    def entity_types(self) -> List[str]:
        with self._lock:
            return list(self._type_index.keys())

    # --- Transactions ---

    def begin_transaction(self) -> str:
        """Begin a transaction. Returns transaction ID."""
        txn_id = str(uuid.uuid4())
        with self._lock:
            txn = _Transaction(txn_id)
            txn.snapshot = self._snapshot()
            self._active_transactions[txn_id] = txn
        logger.debug(f"Transaction started: {txn_id}")
        return txn_id

    def commit_transaction(self, transaction_id: str) -> None:
        """Commit a transaction (discard snapshot)."""
        with self._lock:
            if transaction_id not in self._active_transactions:
                raise KeyError(f"Transaction '{transaction_id}' not found")
            self._active_transactions.pop(transaction_id)
        logger.debug(f"Transaction committed: {transaction_id}")

    def rollback_transaction(self, transaction_id: str) -> None:
        """Rollback a transaction to the snapshot state."""
        with self._lock:
            if transaction_id not in self._active_transactions:
                raise KeyError(f"Transaction '{transaction_id}' not found")
            txn = self._active_transactions.pop(transaction_id)
            if txn.snapshot:
                self._restore_snapshot(txn.snapshot)
        logger.debug(f"Transaction rolled back: {transaction_id}")

    # --- Serialization ---

    def serialize(self) -> Dict[str, Any]:
        """Serialize the entire Context Store to a JSON-compatible dict."""
        with self._lock:
            return {
                "entities": {
                    eid: entity.to_dict()
                    for eid, entity in self._entities.items()
                },
                "metadata": {
                    "entity_count": len(self._entities),
                    "entity_types": list(self._type_index.keys()),
                    "serialized_at": datetime.now().isoformat(),
                },
            }

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "ContextStore":
        """Deserialize a Context Store from a JSON-compatible dict."""
        store = cls()
        for entity_data in data.get("entities", {}).values():
            entity = ContextEntity.from_dict(entity_data)
            store.add_entity(entity)
        return store

    # --- Internal Helpers ---

    def _index_entity(self, entity: ContextEntity) -> None:
        if entity.entity_type not in self._type_index:
            self._type_index[entity.entity_type] = set()
        self._type_index[entity.entity_type].add(entity.id)

    def _matches_filters(self, entity: ContextEntity,
                         filters: Dict[str, Any]) -> bool:
        for key, value in filters.items():
            if key not in entity.data or entity.data[key] != value:
                return False
        return True

    def _snapshot(self) -> Dict[str, Any]:
        """Create a deep copy snapshot of current state."""
        return {
            "entities": {
                eid: copy.deepcopy(entity.to_dict())
                for eid, entity in self._entities.items()
            }
        }

    def _restore_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """Restore state from a snapshot."""
        self._entities.clear()
        self._type_index.clear()
        self._relationship_index.clear()
        for entity_data in snapshot.get("entities", {}).values():
            entity = ContextEntity.from_dict(entity_data)
            self._entities[entity.id] = entity
            self._index_entity(entity)
            # Rebuild relationship index
            for rel_type, rel_ids in entity.relationships.items():
                if entity.id not in self._relationship_index:
                    self._relationship_index[entity.id] = set()
                self._relationship_index[entity.id].update(rel_ids)

    def __repr__(self) -> str:
        return f"<ContextStore entities={self.entity_count} types={self.entity_types}>"
