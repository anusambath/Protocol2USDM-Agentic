"""
BiomedicalConcept Extractor — derives BiomedicalConcept entities from SoA activities.

Takes activity names extracted by the SoA agents and maps them to formal
BiomedicalConcept + BiomedicalConceptCategory structures following USDM 4.0.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

from core.llm_client import call_llm
from .schema import (
    BiomedicalConcept,
    BiomedicalConceptCategory,
    BiomedicalConceptProperty,
    ResponseCode,
)
from .prompts import build_bc_extraction_prompt

logger = logging.getLogger(__name__)


@dataclass
class BCExtractionResult:
    """Result of BiomedicalConcept extraction."""
    success: bool
    biomedical_concepts: List[BiomedicalConcept] = field(default_factory=list)
    categories: List[BiomedicalConceptCategory] = field(default_factory=list)
    raw_response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    model_used: Optional[str] = None


def extract_biomedical_concepts(
    activity_names: List[str],
    model_name: str = "gemini-2.5-pro",
) -> BCExtractionResult:
    """
    Extract BiomedicalConcept entities from a list of SoA activity names.

    Args:
        activity_names: List of unique activity names from the SoA
        model_name: LLM model to use

    Returns:
        BCExtractionResult with BiomedicalConcepts and BiomedicalConceptCategories
    """
    result = BCExtractionResult(success=False, model_used=model_name)

    if not activity_names:
        result.error = "No activity names provided"
        return result

    # Deduplicate while preserving order
    seen = set()
    unique_names = []
    for name in activity_names:
        if name and name.strip() and name.lower() not in seen:
            seen.add(name.lower())
            unique_names.append(name.strip())

    if not unique_names:
        result.error = "No valid activity names after deduplication"
        return result

    logger.info(f"Extracting BiomedicalConcepts for {len(unique_names)} unique activities")

    # Chunk large activity lists to stay within LLM context limits
    MAX_ACTIVITIES_PER_CALL = 60
    all_raw_bcs: List[Dict] = []
    all_raw_cats: List[Dict] = []

    chunks = [unique_names[i:i + MAX_ACTIVITIES_PER_CALL]
              for i in range(0, len(unique_names), MAX_ACTIVITIES_PER_CALL)]

    for chunk_idx, chunk in enumerate(chunks):
        logger.info(f"Processing chunk {chunk_idx + 1}/{len(chunks)} ({len(chunk)} activities)")
        prompt = build_bc_extraction_prompt(chunk)

        response = call_llm(
            prompt=prompt,
            model_name=model_name,
            json_mode=True,
            extractor_name="biomedical_concepts",
        )

        if "error" in response:
            logger.warning(f"LLM error on chunk {chunk_idx + 1}: {response['error']}")
            continue

        raw = _parse_json_response(response.get("response", ""))
        if not raw:
            logger.warning(f"Could not parse JSON for chunk {chunk_idx + 1}")
            continue

        all_raw_bcs.extend(raw.get("biomedicalConcepts", []))
        all_raw_cats.extend(raw.get("categories", []))

    if not all_raw_bcs:
        result.error = "LLM returned no BiomedicalConcepts"
        return result

    # Build structured objects from raw LLM response
    bcs, cats = _build_bc_objects(all_raw_bcs, all_raw_cats)

    result.biomedical_concepts = bcs
    result.categories = cats
    result.raw_response = {
        "biomedicalConceptCount": len(bcs),
        "categoryCount": len(cats),
    }
    result.success = True

    logger.info(f"Extracted {len(bcs)} BiomedicalConcepts in {len(cats)} categories")
    return result


def _build_bc_objects(
    raw_bcs: List[Dict],
    raw_cats: List[Dict],
) -> Tuple[List[BiomedicalConcept], List[BiomedicalConceptCategory]]:
    """Build BiomedicalConcept and BiomedicalConceptCategory objects from raw LLM dicts."""

    # Build category name → id map (from LLM-provided cats, dedup by name)
    cat_name_to_id: Dict[str, str] = {}
    cats_map: Dict[str, BiomedicalConceptCategory] = {}

    for i, cat_raw in enumerate(raw_cats):
        if not isinstance(cat_raw, dict):
            continue
        cname = (cat_raw.get("name") or "").strip()
        if not cname:
            continue
        cid = cat_raw.get("id") or f"bcc_{i+1}"
        if cname.lower() not in cat_name_to_id:
            cat_name_to_id[cname.lower()] = cid
            cats_map[cid] = BiomedicalConceptCategory(
                id=cid,
                name=cname,
                label=cat_raw.get("label") or cname,
                bc_ids=[],
            )

    # Auto-create missing categories referenced in BC entries
    def _get_or_create_cat(cat_name: str) -> str:
        if not cat_name:
            return _get_or_create_cat("Other")
        key = cat_name.lower()
        if key not in cat_name_to_id:
            new_id = f"bcc_{len(cats_map) + 1}"
            cat_name_to_id[key] = new_id
            cats_map[new_id] = BiomedicalConceptCategory(
                id=new_id,
                name=cat_name,
                label=cat_name,
                bc_ids=[],
            )
        return cat_name_to_id[key]

    bcs: List[BiomedicalConcept] = []

    for i, bc_raw in enumerate(raw_bcs):
        if not isinstance(bc_raw, dict):
            continue

        bc_id = bc_raw.get("id") or f"bc_{i+1}"
        bc_name = (bc_raw.get("name") or "").strip()
        if not bc_name:
            continue

        bc_label = bc_raw.get("label") or bc_name
        nci_code = bc_raw.get("nciCode") or None
        nci_decode = bc_raw.get("nciDecode") or None
        synonyms = bc_raw.get("synonyms") or []
        category_name = bc_raw.get("categoryName") or "Other"

        # Resolve or create category
        cat_id = _get_or_create_cat(category_name)

        # Build properties
        properties = []
        for j, prop_raw in enumerate(bc_raw.get("properties") or []):
            if not isinstance(prop_raw, dict):
                continue
            prop_name = (prop_raw.get("name") or "").strip()
            if not prop_name:
                continue
            properties.append(BiomedicalConceptProperty(
                id=f"{bc_id}_prop_{j+1}",
                name=prop_name,
                label=prop_raw.get("label") or prop_name,
                is_required=bool(prop_raw.get("isRequired", False)),
                datatype=prop_raw.get("datatype") or "string",
            ))

        bc = BiomedicalConcept(
            id=bc_id,
            name=bc_name,
            label=bc_label,
            synonyms=synonyms if isinstance(synonyms, list) else [str(synonyms)],
            code=nci_code,
            code_decode=nci_decode,
            category_ids=[cat_id],
            properties=properties,
        )
        bcs.append(bc)

        # Register BC in its category
        if cat_id in cats_map:
            cats_map[cat_id].bc_ids.append(bc_id)

    # Populate LLM-provided category bcIds (may have been pre-filled by LLM)
    # Also update from the auto-tracking above (already done)
    categories = list(cats_map.values())

    return bcs, categories


def _parse_json_response(response_text: str) -> Optional[Dict[str, Any]]:
    """Parse JSON from LLM response, handling markdown code blocks."""
    if not response_text:
        return None

    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
    if json_match:
        response_text = json_match.group(1)

    response_text = response_text.strip()

    try:
        result = json.loads(response_text)
        if isinstance(result, list):
            return {"biomedicalConcepts": result, "categories": []}
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse BC JSON response: {e}")
        return None
