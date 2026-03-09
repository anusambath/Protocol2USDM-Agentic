"""
BiomedicalConcept Extraction Schema — Internal types for the extraction pipeline.

Maps to USDM 4.0 entities:
  BiomedicalConcept         → study.versions[0].biomedicalConcepts[]
  BiomedicalConceptCategory → study.versions[0].bcCategories[]

Each SoA Activity references one or more BiomedicalConcepts via
Activity.biomedicalConceptIds, enabling downstream SDTM domain mapping.

Schema source: https://github.com/cdisc-org/usdm
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from core.usdm_types import generate_uuid


@dataclass
class ResponseCode:
    """
    USDM ResponseCode — a permissible value for a BiomedicalConceptProperty.

    Examples: Y/N for yes/no questions, NORMAL/ABNORMAL for lab results.
    """
    id: str
    code: str           # The coded value (e.g., "Y", "N")
    decode: str         # Human-readable label (e.g., "Yes", "No")
    code_system: str = "NCI"
    instance_type: str = "ResponseCode"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "code": {
                "id": generate_uuid(),
                "code": self.code,
                "codeSystem": self.code_system,
                "decode": self.decode,
                "instanceType": "Code",
            },
            "instanceType": self.instance_type,
        }


@dataclass
class BiomedicalConceptProperty:
    """
    USDM BiomedicalConceptProperty — one data element within a BiomedicalConcept.

    Maps to a single CDASH/SDTM variable (e.g., SYSBP for Systolic Blood Pressure).
    """
    id: str
    name: str            # Variable name (e.g., "SYSBP")
    label: str           # Human label (e.g., "Systolic Blood Pressure")
    is_required: bool = False
    datatype: str = "string"   # string | integer | float | boolean | datetime | uri
    response_codes: List[ResponseCode] = field(default_factory=list)
    concept_code: Optional[str] = None      # NCI code for this property
    concept_decode: Optional[str] = None    # NCI decode for this property
    instance_type: str = "BiomedicalConceptProperty"

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "label": self.label,
            "isRequired": self.is_required,
            "datatype": self.datatype,
            "instanceType": self.instance_type,
        }
        if self.response_codes:
            result["responseCodes"] = [rc.to_dict() for rc in self.response_codes]
        if self.concept_code:
            result["concept"] = {
                "id": generate_uuid(),
                "code": self.concept_code,
                "codeSystem": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl",
                "codeSystemVersion": "25.01d",
                "decode": self.concept_decode or self.label,
                "instanceType": "Code",
            }
        return result


@dataclass
class BiomedicalConcept:
    """
    USDM BiomedicalConcept — formal clinical concept linked to SoA activities.

    Bridges the protocol SoA to standard terminologies (NCI, SNOMED, LOINC)
    and enables downstream SDTM domain mapping.
    """
    id: str
    name: str           # Short name (e.g., "Systolic Blood Pressure")
    label: str          # Full display label
    synonyms: List[str] = field(default_factory=list)
    code: Optional[str] = None          # Primary NCI code
    code_decode: Optional[str] = None   # NCI decode
    category_ids: List[str] = field(default_factory=list)   # BiomedicalConceptCategory IDs
    properties: List[BiomedicalConceptProperty] = field(default_factory=list)
    instance_type: str = "BiomedicalConcept"

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "label": self.label,
            "synonyms": self.synonyms,
            "categories": self.category_ids,
            "properties": [p.to_dict() for p in self.properties],
            "instanceType": self.instance_type,
        }
        if self.code:
            result["code"] = {
                "id": generate_uuid(),
                "code": self.code,
                "codeSystem": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl",
                "codeSystemVersion": "25.01d",
                "decode": self.code_decode or self.name,
                "instanceType": "Code",
            }
        return result


@dataclass
class BiomedicalConceptCategory:
    """
    USDM BiomedicalConceptCategory — groups BiomedicalConcepts by clinical domain.

    Examples: "Vital Signs", "Laboratory Tests", "ECG", "Pharmacokinetics".
    """
    id: str
    name: str           # Category name (e.g., "Vital Signs")
    label: str          # Display label
    bc_ids: List[str] = field(default_factory=list)   # Member BiomedicalConcept IDs
    instance_type: str = "BiomedicalConceptCategory"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "label": self.label,
            "bcIds": self.bc_ids,
            "instanceType": self.instance_type,
        }
