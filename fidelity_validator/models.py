"""
Pydantic models for the USDM Fidelity Validator report structure.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class Severity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class Dimension(str, Enum):
    PRESENCE = "presence"
    COVERAGE = "coverage"
    FAITHFULNESS = "faithfulness"
    PLACEMENT = "placement"
    HALLUCINATION = "hallucination"


# ─────────────────────────────────────────────────────────────────────────────
# Finding (individual issue)
# ─────────────────────────────────────────────────────────────────────────────

class Finding(BaseModel):
    """A single fidelity issue found during comparison."""
    dimension: Dimension
    severity: Severity
    section_id: str = Field(description="Canonical section ID from the section map")
    protocol_page: Optional[int] = Field(None, description="1-indexed page in the PDF")
    usdm_path: Optional[str] = Field(None, description="JSON path in the USDM (e.g., study.versions[0].studyDesigns[0].eligibilityCriteria[3])")
    protocol_evidence: Optional[str] = Field(None, description="Snippet from the protocol text")
    usdm_evidence: Optional[str] = Field(None, description="Snippet from the USDM JSON value")
    message: str = Field(description="Human-readable description of the issue")
    item_id: Optional[str] = Field(None, description="Identifier of the atomic item (e.g., criterion number)")


# ─────────────────────────────────────────────────────────────────────────────
# Dimension Scores
# ─────────────────────────────────────────────────────────────────────────────

class DimensionScore(BaseModel):
    """Score for a single fidelity dimension within a section."""
    dimension: Dimension
    score: float = Field(ge=0.0, le=1.0, description="0.0 = total failure, 1.0 = perfect")
    total_items: int = Field(0, description="Total atomic items evaluated")
    passed_items: int = Field(0, description="Items that passed this dimension")
    findings: List[Finding] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Section Report
# ─────────────────────────────────────────────────────────────────────────────

class SectionReport(BaseModel):
    """Fidelity report for a single protocol section."""
    section_id: str
    section_name: str
    protocol_pages: List[int] = Field(default_factory=list, description="Pages where this section appears")
    usdm_entity_count: int = Field(0, description="Number of USDM entities found for this section")
    protocol_item_count: int = Field(0, description="Number of atomic items in the protocol section")
    
    # Per-dimension scores
    presence: DimensionScore
    coverage: DimensionScore
    faithfulness: DimensionScore
    placement: DimensionScore
    hallucination: DimensionScore
    
    # Aggregate
    overall_score: float = Field(ge=0.0, le=1.0, description="Weighted average across dimensions")
    
    def compute_overall(self, weights: Optional[Dict[Dimension, float]] = None) -> float:
        """Compute weighted overall score."""
        if weights is None:
            weights = {
                Dimension.PRESENCE: 0.15,
                Dimension.COVERAGE: 0.30,
                Dimension.FAITHFULNESS: 0.30,
                Dimension.PLACEMENT: 0.10,
                Dimension.HALLUCINATION: 0.15,
            }
        scores = {
            Dimension.PRESENCE: self.presence.score,
            Dimension.COVERAGE: self.coverage.score,
            Dimension.FAITHFULNESS: self.faithfulness.score,
            Dimension.PLACEMENT: self.placement.score,
            Dimension.HALLUCINATION: self.hallucination.score,
        }
        total_weight = sum(weights.values())
        self.overall_score = sum(
            scores[dim] * w for dim, w in weights.items()
        ) / total_weight
        return self.overall_score


# ─────────────────────────────────────────────────────────────────────────────
# Full Report
# ─────────────────────────────────────────────────────────────────────────────

class FidelityReport(BaseModel):
    """Complete fidelity validation report."""
    protocol_file: str
    usdm_file: str
    section_map_version: str = "1.0"
    usdm_version: str = "4.0"
    
    # Per-section results
    sections: List[SectionReport] = Field(default_factory=list)
    
    # Aggregate scores
    overall_score: float = Field(0.0, ge=0.0, le=1.0)
    dimension_scores: Dict[str, float] = Field(default_factory=dict)
    
    # Summary counts
    total_findings: int = 0
    critical_findings: int = 0
    major_findings: int = 0
    minor_findings: int = 0
    
    def compute_aggregates(self) -> None:
        """Compute aggregate scores from section reports."""
        if not self.sections:
            return
        
        # Overall = average of section overall scores
        self.overall_score = sum(s.overall_score for s in self.sections) / len(self.sections)
        
        # Per-dimension averages
        for dim in Dimension:
            scores = []
            for s in self.sections:
                dim_score = getattr(s, dim.value)
                scores.append(dim_score.score)
            self.dimension_scores[dim.value] = sum(scores) / len(scores) if scores else 0.0
        
        # Finding counts
        all_findings = []
        for s in self.sections:
            for dim_score in [s.presence, s.coverage, s.faithfulness, s.placement, s.hallucination]:
                all_findings.extend(dim_score.findings)
        
        self.total_findings = len(all_findings)
        self.critical_findings = sum(1 for f in all_findings if f.severity == Severity.CRITICAL)
        self.major_findings = sum(1 for f in all_findings if f.severity == Severity.MAJOR)
        self.minor_findings = sum(1 for f in all_findings if f.severity == Severity.MINOR)


# ─────────────────────────────────────────────────────────────────────────────
# Section Map Schema (for loading/validating the YAML)
# ─────────────────────────────────────────────────────────────────────────────

class AttributeSpec(BaseModel):
    """Specification for a USDM entity attribute."""
    name: str
    required: bool = True
    description: Optional[str] = None


class USDMTarget(BaseModel):
    """A USDM entity that should capture content from a protocol section."""
    entity: str = Field(description="USDM entity type name (e.g., EligibilityCriterion)")
    path: str = Field(description="JSON path template to the entity array/object")
    cardinality: Optional[str] = Field(None, description="one_to_one or one_to_many")
    attributes: List[AttributeSpec] = Field(default_factory=list)


class ValidationRule(BaseModel):
    """A validation rule specific to a section."""
    rule: str
    description: str
    severity: Severity = Severity.MAJOR
    tolerance: Optional[int] = None


class SectionSpec(BaseModel):
    """Specification for a protocol section in the section map."""
    id: str
    name: str
    aliases: List[str] = Field(default_factory=list)
    usdm_targets: List[USDMTarget] = Field(default_factory=list)
    validation_rules: List[ValidationRule] = Field(default_factory=list)
    notes: Optional[str] = None


class SectionMap(BaseModel):
    """The complete section map configuration."""
    schema_version: str = "1.0"
    usdm_version: str = "4.0"
    sections: List[SectionSpec] = Field(default_factory=list)
    
    def get_section(self, section_id: str) -> Optional[SectionSpec]:
        """Look up a section by ID."""
        return next((s for s in self.sections if s.id == section_id), None)
    
    def find_section_by_name(self, name: str) -> Optional[SectionSpec]:
        """Find a section by name or alias (case-insensitive)."""
        name_lower = name.lower().strip()
        for s in self.sections:
            if s.name.lower() == name_lower:
                return s
            if any(a.lower() == name_lower for a in s.aliases):
                return s
        return None
