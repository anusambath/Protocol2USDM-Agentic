"""
Unit tests for ContextStore.

Covers: CRUD, relationships, queries, transactions, serialization.
"""

import pytest
from agents.context_store import ContextEntity, ContextStore, EntityProvenance


class TestEntityCRUD:
    def test_add_entity(self, context_store, sample_entity):
        eid = context_store.add_entity(sample_entity)
        assert eid == "entity_1"
        assert context_store.entity_count == 1

    def test_add_duplicate_raises(self, context_store, sample_entity):
        context_store.add_entity(sample_entity)
        with pytest.raises(ValueError, match="already exists"):
            context_store.add_entity(sample_entity)

    def test_get_entity(self, context_store, sample_entity):
        context_store.add_entity(sample_entity)
        found = context_store.get_entity("entity_1")
        assert found is not None
        assert found.data["name"] == "Screening"

    def test_get_nonexistent(self, context_store):
        assert context_store.get_entity("nonexistent") is None

    def test_update_entity(self, context_store, sample_entity):
        context_store.add_entity(sample_entity)
        context_store.update_entity("entity_1", {"name": "Updated"}, agent_id="updater")
        entity = context_store.get_entity("entity_1")
        assert entity.data["name"] == "Updated"
        assert entity.version == 2

    def test_update_nonexistent_raises(self, context_store):
        with pytest.raises(KeyError, match="not found"):
            context_store.update_entity("nonexistent", {"key": "val"})

    def test_delete_entity(self, context_store, sample_entity):
        context_store.add_entity(sample_entity)
        assert context_store.delete_entity("entity_1") is True
        assert context_store.entity_count == 0

    def test_delete_nonexistent(self, context_store):
        assert context_store.delete_entity("nonexistent") is False


class TestRelationships:
    def test_add_relationship(self, context_store):
        e1 = ContextEntity(id="e1", entity_type="epoch", data={"name": "Screening"},
                           provenance=EntityProvenance(entity_id="e1", source_agent_id="a1"))
        e2 = ContextEntity(id="e2", entity_type="encounter", data={"name": "Visit 1"},
                           provenance=EntityProvenance(entity_id="e2", source_agent_id="a1"))
        context_store.add_entity(e1)
        context_store.add_entity(e2)
        context_store.add_relationship("e1", "e2", "contains")

        related = context_store.get_related_entities("e1", "contains")
        assert len(related) == 1
        assert related[0].id == "e2"

    def test_relationship_missing_entity_raises(self, context_store, sample_entity):
        context_store.add_entity(sample_entity)
        with pytest.raises(KeyError):
            context_store.add_relationship("entity_1", "nonexistent", "rel")

    def test_get_related_all_types(self, context_store):
        e1 = ContextEntity(id="e1", entity_type="epoch", data={},
                           provenance=EntityProvenance(entity_id="e1", source_agent_id="a1"))
        e2 = ContextEntity(id="e2", entity_type="encounter", data={},
                           provenance=EntityProvenance(entity_id="e2", source_agent_id="a1"))
        e3 = ContextEntity(id="e3", entity_type="activity", data={},
                           provenance=EntityProvenance(entity_id="e3", source_agent_id="a1"))
        context_store.add_entity(e1)
        context_store.add_entity(e2)
        context_store.add_entity(e3)
        context_store.add_relationship("e1", "e2", "contains")
        context_store.add_relationship("e1", "e3", "has_activity")

        all_related = context_store.get_related_entities("e1")
        assert len(all_related) == 2


class TestQueries:
    def test_query_by_type(self, context_store):
        for i in range(3):
            context_store.add_entity(ContextEntity(
                id=f"epoch_{i}", entity_type="epoch", data={"name": f"Epoch {i}"},
                provenance=EntityProvenance(entity_id=f"epoch_{i}", source_agent_id="a1"),
            ))
        context_store.add_entity(ContextEntity(
            id="enc_1", entity_type="encounter", data={"name": "Visit 1"},
            provenance=EntityProvenance(entity_id="enc_1", source_agent_id="a1"),
        ))
        epochs = context_store.query_entities(entity_type="epoch")
        assert len(epochs) == 3

    def test_query_with_filters(self, context_store):
        context_store.add_entity(ContextEntity(
            id="e1", entity_type="epoch", data={"name": "Screening", "phase": "pre"},
            provenance=EntityProvenance(entity_id="e1", source_agent_id="a1"),
        ))
        context_store.add_entity(ContextEntity(
            id="e2", entity_type="epoch", data={"name": "Treatment", "phase": "main"},
            provenance=EntityProvenance(entity_id="e2", source_agent_id="a1"),
        ))
        results = context_store.query_entities(entity_type="epoch", filters={"phase": "main"})
        assert len(results) == 1
        assert results[0].data["name"] == "Treatment"

    def test_query_all(self, context_store, sample_entity):
        context_store.add_entity(sample_entity)
        all_entities = context_store.query_entities()
        assert len(all_entities) == 1

    def test_entity_types(self, context_store):
        context_store.add_entity(ContextEntity(
            id="e1", entity_type="epoch", data={},
            provenance=EntityProvenance(entity_id="e1", source_agent_id="a1"),
        ))
        context_store.add_entity(ContextEntity(
            id="e2", entity_type="encounter", data={},
            provenance=EntityProvenance(entity_id="e2", source_agent_id="a1"),
        ))
        types = context_store.entity_types
        assert "epoch" in types
        assert "encounter" in types


class TestTransactions:
    def test_commit_transaction(self, context_store, sample_entity):
        context_store.add_entity(sample_entity)
        txn_id = context_store.begin_transaction()
        context_store.update_entity("entity_1", {"name": "Modified"})
        context_store.commit_transaction(txn_id)
        assert context_store.get_entity("entity_1").data["name"] == "Modified"

    def test_rollback_transaction(self, context_store, sample_entity):
        context_store.add_entity(sample_entity)
        txn_id = context_store.begin_transaction()
        context_store.update_entity("entity_1", {"name": "Modified"})
        context_store.rollback_transaction(txn_id)
        assert context_store.get_entity("entity_1").data["name"] == "Screening"

    def test_rollback_restores_entity_count(self, context_store, sample_entity):
        context_store.add_entity(sample_entity)
        txn_id = context_store.begin_transaction()
        context_store.add_entity(ContextEntity(
            id="e2", entity_type="encounter", data={},
            provenance=EntityProvenance(entity_id="e2", source_agent_id="a1"),
        ))
        assert context_store.entity_count == 2
        context_store.rollback_transaction(txn_id)
        assert context_store.entity_count == 1

    def test_invalid_transaction_raises(self, context_store):
        with pytest.raises(KeyError):
            context_store.commit_transaction("nonexistent")
        with pytest.raises(KeyError):
            context_store.rollback_transaction("nonexistent")


class TestSerialization:
    def test_round_trip(self, context_store):
        for i in range(3):
            context_store.add_entity(ContextEntity(
                id=f"e_{i}", entity_type="epoch", data={"name": f"Epoch {i}"},
                provenance=EntityProvenance(
                    entity_id=f"e_{i}", source_agent_id="agent_1",
                    confidence_score=0.9, source_pages=[i],
                ),
            ))
        context_store.add_relationship("e_0", "e_1", "follows")

        serialized = context_store.serialize()
        restored = ContextStore.deserialize(serialized)

        assert restored.entity_count == 3
        for i in range(3):
            entity = restored.get_entity(f"e_{i}")
            assert entity is not None
            assert entity.data["name"] == f"Epoch {i}"
            assert entity.provenance.confidence_score == 0.9

    def test_entity_provenance_round_trip(self):
        prov = EntityProvenance(
            entity_id="e1", source_agent_id="agent_1",
            confidence_score=0.85, source_pages=[1, 2, 3],
            model_used="gpt-4", version=2,
        )
        d = prov.to_dict()
        restored = EntityProvenance.from_dict(d)
        assert restored.entity_id == prov.entity_id
        assert restored.confidence_score == prov.confidence_score
        assert restored.source_pages == prov.source_pages
        assert restored.model_used == prov.model_used

    def test_version_increment(self, context_store, sample_entity):
        context_store.add_entity(sample_entity)
        assert context_store.get_entity("entity_1").version == 1
        context_store.update_entity("entity_1", {"key": "val"})
        assert context_store.get_entity("entity_1").version == 2
        context_store.update_entity("entity_1", {"key": "val2"})
        assert context_store.get_entity("entity_1").version == 3
