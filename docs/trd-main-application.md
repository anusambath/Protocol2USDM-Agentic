# Technical Requirements Document (TRD)
# Protocol2USDM - Main Application

**Version:** 1.0  
**Date:** February 27, 2026  
**Status:** Final  
**Author:** Protocol2USDM Team

---

## Executive Summary

This Technical Requirements Document (TRD) provides detailed technical specifications for implementing the Protocol2USDM system. It covers architecture, data models, APIs, algorithms, and implementation guidelines necessary to recreate the application.

---

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Protocol2USDM System                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Entry Point Layer                      │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐         │  │
│  │  │ run_extraction.py │  │   CLI      │  │   Config   │         │  │
│  │  │            │─▶│  Parser    │─▶│   Loader   │         │  │
│  │  └────────────┘  └────────────┘  └────────────┘         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Orchestration Layer                      │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐         │  │
│  │  │  Pipeline  │  │   Phase    │  │  Pipeline  │         │  │
│  │  │Orchestrator│─▶│  Registry  │─▶│  Context   │         │  │
│  │  └────────────┘  └────────────┘  └────────────┘         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   Extraction Layer                        │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐         │  │
│  │  │    SoA     │  │  Metadata  │  │ Eligibility│         │  │
│  │  │ Extractor  │  │ Extractor  │  │ Extractor  │         │  │
│  │  └────────────┘  └────────────┘  └────────────┘         │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐         │  │
│  │  │ Objectives │  │   Study    │  │Interventions│        │  │
│  │  │ Extractor  │  │   Design   │  │ Extractor  │         │  │
│  │  └────────────┘  └────────────┘  └────────────┘         │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐         │  │
│  │  │ Execution  │  │    SAP     │  │   Sites    │         │  │
│  │  │   Model    │  │ Integration│  │Integration │         │  │
│  │  └────────────┘  └────────────┘  └────────────┘         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                     Core Layer                            │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐         │  │
│  │  │    USDM    │  │ Provenance │  │ Validation │         │  │
│  │  │   Types    │  │  Tracker   │  │   Engine   │         │  │
│  │  └────────────┘  └────────────┘  └────────────┘         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                 Post-Processing Layer                     │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐         │  │
│  │  │ Enrichment │  │   Schema   │  │   CDISC    │         │  │
│  │  │ (EVS API)  │  │ Validation │  │    CORE    │         │  │
│  │  └────────────┘  └────────────┘  └────────────┘         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Presentation Layer                       │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐         │  │
│  │  │   Web UI   │  │    API     │  │   File     │         │  │
│  │  │ (Next.js)  │  │  Server    │  │   Output   │         │  │
│  │  └────────────┘  └────────────┘  └────────────┘         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Module Structure


```
protocol2usdm/
├── run_extraction.py                    # Entry point with CLI
├── llm_providers.py              # LLM abstraction layer
├── llm_config.yaml               # Task-optimized LLM parameters
├── requirements.txt              # Python dependencies
├── .env                          # API keys (not committed)
│
├── agents/                       # Agent-based architecture
│   ├── __init__.py
│   ├── base.py                   # Base agent interface
│   ├── context_store.py          # Shared context store
│   ├── message_queue.py          # Agent message queue
│   ├── metrics.py                # Agent metrics tracking
│   ├── orchestrator.py           # Agent orchestrator
│   ├── pipeline.py               # Pipeline execution
│   ├── production.py             # Production configuration
│   ├── registry.py               # Agent registry
│   ├── extraction/               # Extraction agents
│   │   ├── __init__.py
│   │   ├── base_extraction_agent.py
│   │   ├── metadata_agent.py
│   │   ├── eligibility_agent.py
│   │   ├── objectives_agent.py
│   │   ├── studydesign_agent.py
│   │   ├── interventions_agent.py
│   │   ├── procedures_agent.py
│   │   ├── scheduling_agent.py
│   │   ├── execution_agent.py
│   │   ├── soa_vision_agent.py
│   │   ├── soa_text_agent.py
│   │   ├── narrative_agent.py
│   │   ├── advanced_agent.py
│   │   ├── docstructure_agent.py
│   │   └── biomedical_concept_agent.py
│   ├── quality/                  # Quality agents
│   │   ├── __init__.py
│   │   ├── postprocessing_agent.py
│   │   ├── validation_agent.py
│   │   ├── enrichment_agent.py
│   │   └── reconciliation_agent.py
│   └── support/                  # Support agents
│       ├── __init__.py
│       ├── pdf_parser_agent.py
│       ├── usdm_generator_agent.py
│       ├── provenance_agent.py
│       ├── checkpoint_agent.py
│       └── error_handler.py
│
├── web-ui/                       # Presentation layer
│   ├── package.json
│   ├── next.config.mjs
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── app/                      # Next.js pages
│   │   ├── layout.tsx
│   │   ├── page.tsx              # Protocol list
│   │   ├── protocols/
│   │   │   └── [id]/
│   │   │       └── page.tsx      # Protocol detail
│   │   └── api/                  # API routes
│   │       └── protocols/
│   │           └── [id]/
│   │               ├── ars/
│   │               ├── id-mapping/
│   │               ├── images/
│   │               ├── overlay/
│   │               ├── pages/
│   │               ├── provenance/
│   │               ├── usdm/
│   │               └── validation/
│   ├── components/               # React components
│   │   ├── workbench/            # VS Code-style workbench layout
│   │   ├── soa/                  # SoA components
│   │   ├── timeline/             # Timeline components
│   │   ├── protocol/             # Protocol components
│   │   ├── provenance/           # Provenance components
│   │   ├── quality/              # Quality components
│   │   ├── intermediate/         # Intermediate file viewers
│   │   ├── overlay/              # Overlay/draft components
│   │   ├── theme/                # Theme components
│   │   └── ui/                   # Base UI components
│   ├── lib/                      # Utilities
│   │   ├── adapters/             # Data adapters
│   │   ├── cache/                # Caching utilities
│   │   ├── export/               # Export utilities
│   │   ├── hooks/                # React hooks
│   │   ├── overlay/              # Overlay schema
│   │   ├── performance/          # Performance utilities
│   │   ├── provenance/           # Provenance types
│   │   ├── stores/               # Additional stores
│   │   ├── commandRegistry.ts    # Command palette registry
│   │   ├── viewRegistry.tsx      # View registry
│   │   └── utils.ts
│   └── stores/                   # State management
│       ├── protocolStore.ts
│       ├── overlayStore.ts
│       └── layoutStore.ts
│
└── tools/                        # External tools
    └── core/                     # CDISC CORE engine
        ├── download_core.py
        └── core/
            └── core.exe          # CORE engine binary
```

---

## 2. Data Models

### 2.1 USDM Entity Hierarchy

The system implements USDM v4.0 entities as Python dataclasses. Key entities:


#### 2.1.1 Core Entities

```python
@dataclass
class Code(USDMEntity):
    """USDM Code - NCI terminology code"""
    code: str                    # e.g., "C25426"
    decode: str                  # e.g., "Visit"
    codeSystem: str              # e.g., "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl"
    codeSystemVersion: str       # e.g., "24.09e"
    id: Optional[str] = None     # UUID
    instanceType: str = "Code"

@dataclass
class Study(USDMEntity):
    """USDM Study - Root entity"""
    id: str                      # UUID
    name: str                    # Study title
    studyTitle: str              # Full title
    studyPhase: Optional[Code]   # Phase 1/2/3/4
    studyType: Optional[Code]    # Interventional/Observational
    studyIdentifiers: List[StudyIdentifier]
    studyProtocolVersions: List[StudyProtocolVersion]
    studyDesigns: List[StudyDesign]
    objectives: List[Objective]
    studyInterventions: List[StudyIntervention]
    activities: List[Activity]
    encounters: List[Encounter]
    biomedicalConcepts: List[BiomedicalConcept]
    bcCategories: List[BcCategory]
    bcSurrogates: List[BcSurrogate]
    eligibilityCriteria: List[EligibilityCriterion]
    estimands: List[Estimand]
    instanceType: str = "Study"
```

#### 2.1.2 Schedule of Activities Entities

```python
@dataclass
class Activity(USDMEntity):
    """USDM Activity - A planned action"""
    id: str                      # UUID
    name: str                    # Activity name
    description: Optional[str]   # Description
    label: Optional[str]         # Display label
    studyInterventionIds: List[str]  # Linked interventions
    biomedicalConceptIds: List[str]  # Linked concepts
    definedProcedures: List[Procedure]
    instanceType: str = "Activity"

@dataclass
class Encounter(USDMEntity):
    """USDM Encounter - A scheduled visit"""
    id: str                      # UUID
    name: str                    # Visit name
    description: Optional[str]   # Description
    label: Optional[str]         # Display label
    encounterType: Optional[Code]  # Visit type
    transitionStartRule: Optional[TransitionRule]
    transitionEndRule: Optional[TransitionRule]
    epochId: Optional[str]       # Parent epoch
    previousId: Optional[str]    # Previous encounter (traversal)
    nextId: Optional[str]        # Next encounter (traversal)
    instanceType: str = "Encounter"

@dataclass
class Epoch(USDMEntity):
    """USDM Epoch - A study period"""
    id: str                      # UUID
    name: str                    # Epoch name
    description: Optional[str]   # Description
    label: Optional[str]         # Display label
    epochType: Optional[Code]    # Screening/Treatment/Follow-up
    sequenceInStudy: Optional[int]  # Order
    previousId: Optional[str]    # Previous epoch (traversal)
    nextId: Optional[str]        # Next epoch (traversal)
    instanceType: str = "Epoch"

@dataclass
class ScheduledActivityInstance(USDMEntity):
    """USDM ScheduledActivityInstance - Activity scheduled at timepoint"""
    id: str                      # UUID
    activityIds: List[str]       # Activities performed
    encounterId: str             # Parent encounter
    defaultConditionId: Optional[str]  # Conditional logic
    instanceType: str = "ScheduledActivityInstance"

@dataclass
class Timing(USDMEntity):
    """USDM Timing - Temporal specification"""
    id: str                      # UUID
    name: str                    # Timing name
    description: Optional[str]   # Description
    label: Optional[str]         # Display label
    type: Optional[Code]         # Fixed/Relative
    value: Optional[str]         # ISO 8601 duration (e.g., "P7D")
    windowLower: Optional[str]   # ISO 8601 duration (e.g., "-P3D")
    windowUpper: Optional[str]   # ISO 8601 duration (e.g., "P3D")
    relativeToFrom: Optional[str]  # Reference encounter ID
    relativeFromScheduledInstanceId: Optional[str]
    instanceType: str = "Timing"
```

#### 2.1.3 Execution Model Entities

```python
@dataclass
class Condition(USDMEntity):
    """USDM Condition - Conditional logic"""
    id: str                      # UUID
    name: str                    # Condition name
    description: Optional[str]   # Description
    label: Optional[str]         # Display label
    contextIds: List[str]        # Context entities
    appliesTo: List[str]         # Target entities
    instanceType: str = "Condition"

@dataclass
class TransitionRule(USDMEntity):
    """USDM TransitionRule - State transition logic"""
    id: str                      # UUID
    name: str                    # Rule name
    description: Optional[str]   # Description
    label: Optional[str]         # Display label
    instanceType: str = "TransitionRule"

@dataclass
class Administration(USDMEntity):
    """USDM Administration - Drug administration"""
    id: str                      # UUID
    name: str                    # Administration name
    description: Optional[str]   # Description
    label: Optional[str]         # Display label
    route: Optional[Code]        # Route of administration
    dose: Optional[str]          # Dose amount
    doseUnit: Optional[Code]     # Dose unit
    frequency: Optional[str]     # Frequency
    instanceType: str = "Administration"

@dataclass
class ScheduledDecisionInstance(USDMEntity):
    """USDM ScheduledDecisionInstance - Decision point"""
    id: str                      # UUID
    conditionId: str             # Condition to evaluate
    encounterId: str             # Parent encounter
    instanceType: str = "ScheduledDecisionInstance"
```

### 2.2 Provenance Data Model

```python
@dataclass
class ProvenanceEntry:
    """Provenance for extracted data"""
    entity_id: str               # USDM entity ID
    entity_type: str             # Entity type (Activity, Encounter, etc.)
    field_name: str              # Field name (name, description, etc.)
    source: str                  # "text", "vision", or "both"
    confidence: float            # 0.0-1.0
    extraction_method: str       # "llm_text", "llm_vision", "manual"
    model_name: Optional[str]    # LLM model used
    timestamp: str               # ISO 8601 timestamp
    page_number: Optional[int]   # Source page
    bounding_box: Optional[Dict] # Vision bounding box
```

### 2.3 Pipeline Context Data Model

```python
@dataclass
class PipelineContext:
    """Context passed between extraction phases"""
    # SoA entities (from SoA extraction)
    activities: List[Activity]
    encounters: List[Encounter]
    epochs: List[Epoch]
    scheduled_instances: List[ScheduledActivityInstance]
    
    # Metadata (from metadata phase)
    study_title: Optional[str]
    protocol_id: Optional[str]
    indication: Optional[str]
    phase: Optional[str]
    
    # Study design (from study design phase)
    arms: List[StudyArm]
    study_cells: List[StudyCell]
    
    # Execution model (from execution phase)
    time_anchors: List[Dict]
    visit_windows: List[Dict]
    state_machine: Optional[Dict]
    
    def get_summary(self) -> str:
        """Return summary of context for logging"""
        return f"Context: {len(self.activities)} activities, " \
               f"{len(self.encounters)} encounters, " \
               f"{len(self.epochs)} epochs"
```

---

## 3. API Specifications

### 3.1 LLM Provider Interface

All LLM providers implement a common interface:

```python
class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        config: LLMConfig
    ) -> str:
        """
        Generate text from messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            config: LLM configuration (temperature, max_tokens, etc.)
            
        Returns:
            Generated text
            
        Raises:
            LLMError: If generation fails
        """
        pass
    
    @abstractmethod
    def generate_with_vision(
        self,
        messages: List[Dict[str, Any]],
        images: List[str],
        config: LLMConfig
    ) -> str:
        """
        Generate text from messages and images.
        
        Args:
            messages: List of message dicts
            images: List of base64-encoded images
            config: LLM configuration
            
        Returns:
            Generated text
            
        Raises:
            LLMError: If generation fails
        """
        pass
```

#### 3.1.1 OpenAI Provider

```python
class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider"""
    
    def __init__(self, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
    
    def generate(self, messages: List[Dict], config: LLMConfig) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            response_format={"type": "json_object"} if config.json_mode else None
        )
        return response.choices[0].message.content
```

#### 3.1.2 Google Gemini Provider

```python
class GeminiProvider(LLMProvider):
    """Google Gemini provider via Vertex AI"""
    
    def __init__(self, model: str = "gemini-3-flash-preview"):
        self.client = genai.Client(
            vertexai=True,
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION")
        )
        self.model = model
    
    def generate(self, messages: List[Dict], config: LLMConfig) -> str:
        # Convert messages to Gemini format
        contents = self._convert_messages(messages)
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=genai_types.GenerateContentConfig(
                temperature=config.temperature,
                max_output_tokens=config.max_tokens,
                response_mime_type="application/json" if config.json_mode else None,
                safety_settings=[
                    genai_types.SafetySetting(
                        category=cat,
                        threshold="BLOCK_NONE"
                    ) for cat in ["HARM_CATEGORY_HATE_SPEECH", 
                                  "HARM_CATEGORY_DANGEROUS_CONTENT",
                                  "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                                  "HARM_CATEGORY_HARASSMENT"]
                ]
            )
        )
        return response.text
```

### 3.2 EVS API Integration

```python
class EVSClient:
    """NCI Enterprise Vocabulary Services API client"""
    
    BASE_URL = "https://api-evsrest.nci.nih.gov/api/v1"
    
    def __init__(self, cache_dir: str = ".evs_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def search_concept(
        self,
        term: str,
        terminology: str = "ncit"
    ) -> Optional[Dict]:
        """
        Search for concept by term.
        
        Args:
            term: Search term
            terminology: Terminology code (default: "ncit")
            
        Returns:
            Concept dict with code, name, definition
        """
        # Check cache first
        cache_key = f"{terminology}_{term.lower().replace(' ', '_')}"
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            with open(cache_file) as f:
                return json.load(f)
        
        # Call API
        url = f"{self.BASE_URL}/concept/{terminology}/search"
        params = {"term": term, "include": "minimal"}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        if data.get("concepts"):
            concept = data["concepts"][0]
            result = {
                "code": concept["code"],
                "name": concept["name"],
                "definition": concept.get("definition")
            }
            
            # Cache result
            with open(cache_file, 'w') as f:
                json.dump(result, f)
            
            return result
        
        return None
```

### 3.3 CDISC CORE API

```python
def run_cdisc_conformance(
    json_path: str,
    output_dir: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run CDISC CORE conformance validation.
    
    Priority:
    1. Local CORE engine (if available)
    2. CDISC API (if key configured)
    
    Args:
        json_path: Path to USDM JSON file
        output_dir: Directory for output report
        api_key: Optional CDISC API key
        
    Returns:
        Dict with conformance results
    """
    # Try local CORE engine first
    if CORE_ENGINE_PATH.exists():
        return _run_local_core_engine(json_path, output_dir)
    
    # Try CDISC API
    if api_key or os.getenv('CDISC_API_KEY'):
        return _run_cdisc_api(json_path, output_dir, api_key)
    
    # No validation available
    return {
        'success': False,
        'engine': 'none',
        'error': 'CDISC CORE engine not available',
        'issues': 0,
        'warnings': 0
    }
```

---

## 4. Algorithms & Processing Logic

### 4.1 SoA Extraction Algorithm


```python
def run_soa_extraction_pipeline(
    pdf_path: str,
    output_dir: str,
    model_name: str,
    config: PipelineConfig
) -> PipelineResult:
    """
    Run complete SoA extraction pipeline.
    
    Steps:
    1. Find SoA pages using vision
    2. Analyze header structure
    3. Extract data with text model
    4. Validate with vision model
    5. Build USDM output
    
    Args:
        pdf_path: Path to protocol PDF
        output_dir: Output directory
        model_name: LLM model name
        config: Pipeline configuration
        
    Returns:
        PipelineResult with extraction data
    """
    result = PipelineResult(success=False)
    
    try:
        # Step 1: Find SoA pages
        logger.info("Step 1: Finding SoA pages...")
        soa_pages = find_soa_pages(pdf_path, model_name)
        if not soa_pages:
            result.errors.append("No SoA pages found")
            return result
        
        # Step 2: Analyze header structure
        logger.info("Step 2: Analyzing header structure...")
        header_structure = analyze_soa_headers(
            pdf_path, soa_pages, model_name
        )
        
        # Step 3: Extract data with text
        logger.info("Step 3: Extracting SoA data (text)...")
        text_extraction = extract_soa_from_text(
            pdf_path, soa_pages, header_structure, model_name
        )
        
        # Step 4: Validate with vision (if enabled)
        if config.validate_with_vision:
            logger.info("Step 4: Validating with vision...")
            validation_result = validate_extraction(
                pdf_path, soa_pages, text_extraction, model_name
            )
            
            # Apply fixes
            final_extraction = apply_validation_fixes(
                text_extraction,
                validation_result,
                remove_hallucinations=config.remove_hallucinations,
                confidence_threshold=config.hallucination_confidence_threshold
            )
            
            result.validated = True
            result.hallucinations_removed = validation_result.get('hallucinations_removed', 0)
            result.missed_ticks_found = validation_result.get('missed_ticks_found', 0)
        else:
            final_extraction = text_extraction
        
        # Step 5: Build USDM output
        logger.info("Step 5: Building USDM output...")
        usdm_output = build_usdm_output(final_extraction)
        
        # Save output
        output_path = os.path.join(output_dir, "9_final_soa.json")
        with open(output_path, 'w') as f:
            json.dump(usdm_output, f, indent=2)
        
        # Save provenance
        provenance_path = get_provenance_path(output_dir)
        provenance_tracker.save(provenance_path)
        
        result.success = True
        result.output_path = output_path
        result.provenance_path = provenance_path
        result.activities_count = len(usdm_output.get('activities', []))
        result.ticks_count = len(usdm_output.get('scheduledActivityInstances', []))
        result.timepoints_count = len(usdm_output.get('encounters', []))
        
        return result
        
    except Exception as e:
        logger.error(f"SoA extraction failed: {e}")
        result.errors.append(str(e))
        return result
```

#### 4.1.1 SoA Page Identification

```python
def find_soa_pages(pdf_path: str, model_name: str) -> List[int]:
    """
    Identify SoA pages using vision model.
    
    Algorithm:
    1. Extract all pages as images
    2. For each page, ask vision model: "Is this a Schedule of Activities?"
    3. Return page numbers where model says "yes"
    
    Args:
        pdf_path: Path to PDF
        model_name: Vision model name
        
    Returns:
        List of page numbers (0-indexed)
    """
    provider = LLMProviderFactory.create_from_model(model_name)
    doc = fitz.open(pdf_path)
    soa_pages = []
    
    for page_num in range(len(doc)):
        # Convert page to image
        page = doc[page_num]
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        img_base64 = base64.b64encode(img_bytes).decode()
        
        # Ask vision model
        prompt = """Is this page a Schedule of Activities (SoA) table?
        
        A Schedule of Activities shows:
        - Activities/procedures in rows
        - Visit timepoints in columns
        - Checkmarks/X marks indicating when activities occur
        
        Respond with JSON: {"is_soa": true/false, "confidence": 0.0-1.0}
        """
        
        messages = [{"role": "user", "content": prompt}]
        response = provider.generate_with_vision(
            messages, [img_base64], LLMConfig(json_mode=True)
        )
        
        result = json.loads(response)
        if result.get("is_soa") and result.get("confidence", 0) > 0.7:
            soa_pages.append(page_num)
    
    return soa_pages
```

#### 4.1.2 Header Structure Analysis

```python
def analyze_soa_headers(
    pdf_path: str,
    soa_pages: List[int],
    model_name: str
) -> Dict:
    """
    Analyze SoA header structure using vision.
    
    Extracts:
    - Column headers (visit names, timepoints)
    - Row groups (activity categories)
    - Table structure (merged cells, hierarchy)
    
    Args:
        pdf_path: Path to PDF
        soa_pages: SoA page numbers
        model_name: Vision model name
        
    Returns:
        Header structure dict
    """
    provider = LLMProviderFactory.create_from_model(model_name)
    
    # Extract images for SoA pages
    images = extract_page_images(pdf_path, soa_pages)
    
    prompt = """Analyze this Schedule of Activities table structure.
    
    Extract:
    1. Column headers (visit names, study days, weeks)
    2. Row groups (activity categories like "Efficacy", "Safety")
    3. Epoch groupings (if columns are grouped by study phase)
    
    Return JSON with:
    {
      "columns": [
        {"index": 0, "name": "Screening", "day": -7, "week": null, "epoch": "Screening"},
        ...
      ],
      "row_groups": [
        {"name": "Efficacy Assessments", "start_row": 0, "end_row": 5},
        ...
      ],
      "epochs": [
        {"name": "Screening", "column_start": 0, "column_end": 2},
        ...
      ]
    }
    """
    
    messages = [{"role": "user", "content": prompt}]
    response = provider.generate_with_vision(
        messages, images, LLMConfig(json_mode=True)
    )
    
    return json.loads(response)
```

#### 4.1.3 Text Extraction with Structure

```python
def extract_soa_from_text(
    pdf_path: str,
    soa_pages: List[int],
    header_structure: Dict,
    model_name: str
) -> Dict:
    """
    Extract SoA data using text model with structure guidance.
    
    Algorithm:
    1. Extract text from SoA pages
    2. Provide header structure as context
    3. Ask model to extract activities and ticks
    4. Map to USDM entities
    
    Args:
        pdf_path: Path to PDF
        soa_pages: SoA page numbers
        header_structure: Header structure from vision
        model_name: Text model name
        
    Returns:
        Extraction dict with activities, ticks, etc.
    """
    provider = LLMProviderFactory.create_from_model(model_name)
    
    # Extract text
    doc = fitz.open(pdf_path)
    text = ""
    for page_num in soa_pages:
        text += doc[page_num].get_text()
    
    # Build prompt with structure context
    prompt = f"""Extract Schedule of Activities data from this text.
    
    Header structure (from vision analysis):
    {json.dumps(header_structure, indent=2)}
    
    Text:
    {text}
    
    Extract:
    1. Activities (procedures, assessments)
    2. Ticks (which activities occur at which visits)
    3. Visit details (names, days, weeks)
    4. Epochs (study periods)
    
    Return JSON with USDM-aligned structure:
    {{
      "activities": [
        {{"id": "act_1", "name": "Physical Exam", "category": "Safety"}},
        ...
      ],
      "encounters": [
        {{"id": "enc_1", "name": "Screening Visit", "day": -7, "week": null, "epoch": "Screening"}},
        ...
      ],
      "epochs": [
        {{"id": "epoch_1", "name": "Screening", "sequence": 1}},
        ...
      ],
      "scheduledActivityInstances": [
        {{"activityId": "act_1", "encounterId": "enc_1"}},
        ...
      ]
    }}
    """
    
    messages = [{"role": "user", "content": prompt}]
    response = provider.generate(messages, LLMConfig(json_mode=True))
    
    return json.loads(response)
```

#### 4.1.4 Vision Validation

```python
def validate_extraction(
    pdf_path: str,
    soa_pages: List[int],
    text_extraction: Dict,
    model_name: str
) -> Dict:
    """
    Validate text extraction against PDF images.
    
    Algorithm:
    1. For each activity-visit pair in text extraction
    2. Ask vision model: "Is there a tick/checkmark at this cell?"
    3. Compare vision result with text extraction
    4. Identify hallucinations (text says yes, vision says no)
    5. Identify missed ticks (text says no, vision says yes)
    
    Args:
        pdf_path: Path to PDF
        soa_pages: SoA page numbers
        text_extraction: Text extraction result
        model_name: Vision model name
        
    Returns:
        Validation result with corrections
    """
    provider = LLMProviderFactory.create_from_model(model_name)
    images = extract_page_images(pdf_path, soa_pages)
    
    hallucinations = []
    missed_ticks = []
    confirmed_ticks = []
    
    # Build activity-visit matrix from text extraction
    activities = {a['id']: a for a in text_extraction['activities']}
    encounters = {e['id']: e for e in text_extraction['encounters']}
    ticks = text_extraction['scheduledActivityInstances']
    
    # Validate each tick
    for tick in ticks:
        activity = activities[tick['activityId']]
        encounter = encounters[tick['encounterId']]
        
        prompt = f"""Look at this Schedule of Activities table.
        
        Is there a checkmark/tick/X for:
        - Activity: {activity['name']}
        - Visit: {encounter['name']} (Day {encounter.get('day', 'N/A')})
        
        Respond with JSON:
        {{
          "has_tick": true/false,
          "confidence": 0.0-1.0,
          "symbol": "checkmark" | "X" | "dot" | "none"
        }}
        """
        
        messages = [{"role": "user", "content": prompt}]
        response = provider.generate_with_vision(
            messages, images, LLMConfig(json_mode=True)
        )
        
        result = json.loads(response)
        
        if result['has_tick'] and result['confidence'] > 0.7:
            confirmed_ticks.append(tick)
            # Update provenance
            provenance_tracker.add_entry(
                entity_id=f"{tick['activityId']}_{tick['encounterId']}",
                entity_type="ScheduledActivityInstance",
                field_name="tick",
                source="both",  # Confirmed by both text and vision
                confidence=result['confidence']
            )
        elif not result['has_tick'] and result['confidence'] > 0.7:
            hallucinations.append(tick)
            # Mark as text-only (potential hallucination)
            provenance_tracker.add_entry(
                entity_id=f"{tick['activityId']}_{tick['encounterId']}",
                entity_type="ScheduledActivityInstance",
                field_name="tick",
                source="text",  # Only text, not confirmed by vision
                confidence=0.5
            )
    
    # Check for missed ticks (vision finds ticks not in text extraction)
    # (Implementation omitted for brevity - similar logic in reverse)
    
    return {
        'confirmed_ticks': confirmed_ticks,
        'hallucinations': hallucinations,
        'missed_ticks': missed_ticks,
        'hallucinations_removed': len(hallucinations),
        'missed_ticks_found': len(missed_ticks)
    }
```

### 4.2 Execution Model Extraction Algorithm


```python
def extract_execution_model(
    pdf_path: str,
    model_name: str,
    context: PipelineContext
) -> Dict:
    """
    Extract execution model semantics.
    
    Extracts:
    1. Time anchors (FirstDose, Baseline, etc.)
    2. Visit windows (target day, window before/after)
    3. Subject state machine (states, transitions)
    4. Dosing regimens
    5. Repetition patterns (cycles)
    6. Conditional logic (footnotes)
    
    Args:
        pdf_path: Path to protocol PDF
        model_name: LLM model name
        context: Pipeline context with SoA entities
        
    Returns:
        Execution model dict
    """
    provider = LLMProviderFactory.create_from_model(model_name)
    
    # Extract relevant sections
    text = extract_protocol_sections(pdf_path, [
        "Schedule of Activities",
        "Study Procedures",
        "Visit Windows",
        "Dosing Schedule"
    ])
    
    # Provide SoA context
    soa_context = {
        'encounters': [{'id': e.id, 'name': e.name} for e in context.encounters],
        'epochs': [{'id': ep.id, 'name': ep.name} for ep in context.epochs],
        'activities': [{'id': a.id, 'name': a.name} for a in context.activities]
    }
    
    prompt = f"""Extract execution model semantics from this protocol.
    
    Existing SoA entities (use these IDs for references):
    {json.dumps(soa_context, indent=2)}
    
    Protocol text:
    {text}
    
    Extract:
    
    1. Time Anchors - Temporal reference points
    {{
      "timeAnchors": [
        {{
          "id": "anchor_1",
          "definition": "First dose of study drug",
          "anchorType": "FirstDose",  // FirstDose, Baseline, InformedConsent, Randomization, etc.
          "dayValue": 1,
          "timelineId": null
        }}
      ]
    }}
    
    2. Visit Windows - Timing tolerances
    {{
      "visitWindows": [
        {{
          "id": "window_1",
          "encounterId": "enc_1",  // Reference existing encounter
          "targetDay": 7,
          "windowBefore": 3,  // Days before target
          "windowAfter": 3,   // Days after target
          "isRequired": true
        }}
      ]
    }}
    
    3. Subject State Machine - Subject flow
    {{
      "stateMachine": {{
        "states": [
          {{"id": "state_1", "name": "Screening", "description": "..."}}
        ],
        "transitions": [
          {{
            "from": "state_1",
            "to": "state_2",
            "condition": "Meets eligibility criteria",
            "encounterIds": ["enc_1", "enc_2"]
          }}
        ]
      }}
    }}
    
    4. Dosing Regimens
    {{
      "dosingRegimens": [
        {{
          "id": "dosing_1",
          "name": "Study Drug Dosing",
          "drug": "Drug A",
          "dose": "100 mg",
          "route": "Oral",
          "frequency": "Once daily",
          "schedule": "Days 1-28 of each cycle"
        }}
      ]
    }}
    
    5. Repetition Patterns
    {{
      "repetitions": [
        {{
          "id": "rep_1",
          "pattern": "28-day cycles",
          "count": 6,
          "encounterIds": ["enc_3", "enc_4"],  // Encounters that repeat
          "activityIds": ["act_5", "act_6"]    // Activities that repeat
        }}
      ]
    }}
    
    6. Conditional Logic (from footnotes)
    {{
      "conditions": [
        {{
          "id": "cond_1",
          "description": "Only if patient has adverse event",
          "appliesTo": ["act_10"],  // Activity IDs
          "type": "conditional_activity"
        }}
      ]
    }}
    
    Return complete JSON with all sections.
    """
    
    messages = [{"role": "user", "content": prompt}]
    response = provider.generate(messages, LLMConfig(json_mode=True))
    
    return json.loads(response)
```

#### 4.2.1 Execution Model Promotion to USDM

```python
def promote_execution_model_to_usdm(
    execution_model: Dict,
    context: PipelineContext
) -> Dict:
    """
    Promote execution model data to native USDM entities.
    
    Transformations:
    1. Visit windows → Timing.windowLower/windowUpper (ISO 8601)
    2. State machine → TransitionRule on Encounter
    3. Dosing regimens → Administration entities
    4. Repetitions → ScheduledActivityInstance expansion
    5. Conditions → Condition + ScheduledDecisionInstance
    6. Traversal → Epoch/Encounter.previousId/nextId chains
    
    Args:
        execution_model: Execution model dict
        context: Pipeline context
        
    Returns:
        USDM entities dict
    """
    usdm_entities = {
        'timings': [],
        'transitionRules': [],
        'administrations': [],
        'conditions': [],
        'scheduledDecisionInstances': [],
        'scheduledActivityInstances': []
    }
    
    # 1. Promote visit windows to Timing entities
    for window in execution_model.get('visitWindows', []):
        timing = Timing(
            id=generate_uuid(),
            name=f"Timing for {window['encounterId']}",
            type=Code.make("C99073", "Fixed Reference"),
            value=f"P{window['targetDay']}D",  # ISO 8601 duration
            windowLower=f"-P{window['windowBefore']}D" if window.get('windowBefore') else None,
            windowUpper=f"P{window['windowAfter']}D" if window.get('windowAfter') else None,
            relativeToFrom=window.get('anchorId')
        )
        usdm_entities['timings'].append(timing.to_dict())
        
        # Update encounter with timing reference
        encounter = next((e for e in context.encounters if e.id == window['encounterId']), None)
        if encounter:
            encounter.transitionStartRule = TransitionRule(
                id=generate_uuid(),
                name=f"Start rule for {encounter.name}",
                description=f"Visit window: Day {window['targetDay']} ±{window.get('windowBefore', 0)}/{window.get('windowAfter', 0)} days"
            )
    
    # 2. Promote state machine to TransitionRule entities
    state_machine = execution_model.get('stateMachine', {})
    for transition in state_machine.get('transitions', []):
        rule = TransitionRule(
            id=generate_uuid(),
            name=f"Transition: {transition['from']} → {transition['to']}",
            description=transition.get('condition', '')
        )
        usdm_entities['transitionRules'].append(rule.to_dict())
        
        # Link to encounters
        for enc_id in transition.get('encounterIds', []):
            encounter = next((e for e in context.encounters if e.id == enc_id), None)
            if encounter:
                encounter.transitionEndRule = rule
    
    # 3. Promote dosing regimens to Administration entities
    for dosing in execution_model.get('dosingRegimens', []):
        admin = Administration(
            id=generate_uuid(),
            name=dosing['name'],
            description=dosing.get('schedule', ''),
            route=Code.make("C38288", dosing.get('route', 'Oral')),
            dose=dosing.get('dose'),
            frequency=dosing.get('frequency')
        )
        usdm_entities['administrations'].append(admin.to_dict())
    
    # 4. Promote repetitions to ScheduledActivityInstance expansion
    for rep in execution_model.get('repetitions', []):
        # Expand cycles into individual instances
        for cycle_num in range(rep.get('count', 1)):
            for enc_id in rep.get('encounterIds', []):
                for act_id in rep.get('activityIds', []):
                    instance = ScheduledActivityInstance(
                        id=generate_uuid(),
                        activityIds=[act_id],
                        encounterId=f"{enc_id}_cycle{cycle_num + 1}"
                    )
                    usdm_entities['scheduledActivityInstances'].append(instance.to_dict())
    
    # 5. Promote conditions to Condition + ScheduledDecisionInstance
    for cond in execution_model.get('conditions', []):
        condition = Condition(
            id=generate_uuid(),
            name=cond.get('description', ''),
            description=cond.get('description', ''),
            appliesTo=cond.get('appliesTo', [])
        )
        usdm_entities['conditions'].append(condition.to_dict())
        
        # Create decision instances for conditional activities
        for target_id in cond.get('appliesTo', []):
            # Find encounter for this activity
            instance = next((i for i in context.scheduled_instances 
                           if target_id in i.activityIds), None)
            if instance:
                decision = ScheduledDecisionInstance(
                    id=generate_uuid(),
                    conditionId=condition.id,
                    encounterId=instance.encounterId
                )
                usdm_entities['scheduledDecisionInstances'].append(decision.to_dict())
    
    # 6. Build traversal chains (previousId/nextId)
    # Sort epochs by sequence
    sorted_epochs = sorted(context.epochs, key=lambda e: e.sequenceInStudy or 0)
    for i, epoch in enumerate(sorted_epochs):
        if i > 0:
            epoch.previousId = sorted_epochs[i-1].id
        if i < len(sorted_epochs) - 1:
            epoch.nextId = sorted_epochs[i+1].id
    
    # Sort encounters by epoch and sequence
    for epoch in context.epochs:
        epoch_encounters = [e for e in context.encounters if e.epochId == epoch.id]
        sorted_encounters = sorted(epoch_encounters, key=lambda e: e.name)
        for i, encounter in enumerate(sorted_encounters):
            if i > 0:
                encounter.previousId = sorted_encounters[i-1].id
            if i < len(sorted_encounters) - 1:
                encounter.nextId = sorted_encounters[i+1].id
    
    return usdm_entities
```

### 4.3 Schema Validation & Auto-Fix Algorithm

```python
def validate_and_fix_schema(usdm_json: Dict) -> Dict:
    """
    Validate USDM output and auto-fix common issues.
    
    Fixes:
    1. Convert simple IDs to UUIDs
    2. Validate entity placement in hierarchy
    3. Add missing required fields
    4. Synchronize provenance IDs
    
    Args:
        usdm_json: USDM JSON dict
        
    Returns:
        Fixed USDM JSON dict
    """
    # 1. Convert IDs to UUIDs
    id_mapping = {}
    for entity_type in USDM_ENTITY_TYPES:
        entities = usdm_json.get(entity_type, [])
        for entity in entities:
            old_id = entity.get('id')
            if old_id and not _is_uuid(old_id):
                new_id = str(uuid.uuid4())
                id_mapping[old_id] = new_id
                entity['id'] = new_id
    
    # Update all ID references
    _update_id_references(usdm_json, id_mapping)
    
    # 2. Validate entity placement
    # Ensure entities are at correct level in hierarchy
    study = usdm_json.get('study', {})
    
    # Move activities to study level
    if 'activities' in usdm_json and 'activities' not in study:
        study['activities'] = usdm_json.pop('activities')
    
    # Move encounters to study level
    if 'encounters' in usdm_json and 'encounters' not in study:
        study['encounters'] = usdm_json.pop('encounters')
    
    # 3. Add missing required fields
    if 'instanceType' not in study:
        study['instanceType'] = 'Study'
    
    if 'id' not in study:
        study['id'] = str(uuid.uuid4())
    
    # 4. Synchronize provenance IDs
    provenance_path = get_provenance_path(os.path.dirname(usdm_json.get('_output_path', '')))
    if os.path.exists(provenance_path):
        convert_provenance_to_uuids(provenance_path, id_mapping)
    
    usdm_json['study'] = study
    return usdm_json
```

---

## 5. Configuration & Deployment

### 5.1 Environment Configuration

**`.env` file:**
```bash
# Google Cloud (Vertex AI) - REQUIRED for Gemini models
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# Alternative: Google AI Studio (may have safety restrictions)
GOOGLE_API_KEY=AIzaSy...

# OpenAI
OPENAI_API_KEY=sk-proj-...

# Anthropic
CLAUDE_API_KEY=sk-ant-...

# CDISC API (optional)
CDISC_API_KEY=...
```

### 5.2 LLM Configuration

**`llm_config.yaml`:**
```yaml
# Task-optimized LLM parameters
categories:
  deterministic:
    temperature: 0.0
    top_p: 0.95
    description: "Structured extraction, schema validation"
  
  semantic:
    temperature: 0.1
    top_p: 0.95
    description: "Entity mapping, terminology enrichment"
  
  structured_gen:
    temperature: 0.2
    top_p: 0.95
    description: "JSON generation, USDM entity creation"
  
  narrative:
    temperature: 0.3
    top_p: 0.95
    description: "Text summarization, description generation"

# Provider-specific overrides
providers:
  openai:
    max_tokens: 16000
    json_mode: true
  
  gemini:
    max_tokens: 8192
    json_mode: true
    thinking_budget: 0  # Disable thinking mode for Gemini 3
  
  claude:
    max_tokens: 8192
    json_mode: false  # Claude uses prompt-based JSON

# Task-category mapping
tasks:
  soa_extraction: structured_gen
  metadata_extraction: deterministic
  eligibility_extraction: structured_gen
  objectives_extraction: structured_gen
  terminology_enrichment: semantic
  schema_validation: deterministic
```

### 5.3 Deployment Steps

#### 5.3.1 Local Development

```bash
# 1. Clone repository
git clone https://github.com/your-org/protocol2usdm.git
cd protocol2usdm

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API keys
cp .env.example .env
# Edit .env with your API keys

# 5. Run extraction
python run_extraction.py input/protocol.pdf --complete

# 6. Start web UI
cd web-ui
npm install
npm run dev
```

#### 5.3.2 Docker Deployment

**`Dockerfile`:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create output directory
RUN mkdir -p output

# Set environment
ENV PYTHONUNBUFFERED=1

# Run extraction
ENTRYPOINT ["python", "run_extraction.py"]
```

**`docker-compose.yml`:**
```yaml
version: '3.8'

services:
  protocol2usdm:
    build: .
    volumes:
      - ./input:/app/input
      - ./output:/app/output
      - ./.env:/app/.env
    environment:
      - GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}
      - GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    command: input/protocol.pdf --complete
  
  web-ui:
    build: ./web-ui
    ports:
      - "3000:3000"
    volumes:
      - ./output:/app/output
    environment:
      - NODE_ENV=production
```

---

## 6. Testing Strategy

### 6.1 Unit Tests

```python
# tests/test_soa_extraction.py
import pytest
from extraction.pipeline import run_soa_extraction_pipeline

def test_soa_page_identification():
    """Test SoA page identification"""
    pages = find_soa_pages("tests/fixtures/protocol.pdf", "gemini-3-flash-preview")
    assert len(pages) > 0
    assert all(isinstance(p, int) for p in pages)

def test_header_structure_analysis():
    """Test header structure extraction"""
    structure = analyze_soa_headers(
        "tests/fixtures/protocol.pdf",
        [10, 11],
        "gemini-3-flash-preview"
    )
    assert 'columns' in structure
    assert 'row_groups' in structure
    assert len(structure['columns']) > 0

def test_text_extraction():
    """Test text-based SoA extraction"""
    result = extract_soa_from_text(
        "tests/fixtures/protocol.pdf",
        [10, 11],
        {"columns": [], "row_groups": []},
        "gemini-3-flash-preview"
    )
    assert 'activities' in result
    assert 'encounters' in result
    assert len(result['activities']) > 0
```

### 6.2 Integration Tests

```python
# tests/test_full_pipeline.py
def test_complete_extraction():
    """Test complete extraction pipeline"""
    result = run_from_files(
        pdf_path="tests/fixtures/protocol.pdf",
        output_dir="tests/output",
        model_name="gemini-3-flash-preview",
        phases_to_run={
            'soa': True,
            'metadata': True,
            'eligibility': True
        }
    )
    
    assert result.success
    assert os.path.exists(result.output_path)
    
    # Validate output
    with open(result.output_path) as f:
        usdm = json.load(f)
    
    assert 'study' in usdm
    assert 'activities' in usdm['study']
    assert len(usdm['study']['activities']) > 0
```

### 6.3 End-to-End Tests

```python
# tests/test_e2e.py
def test_e2e_with_validation():
    """Test end-to-end with validation"""
    # Run extraction
    os.system("python run_extraction.py tests/fixtures/protocol.pdf --complete --output-dir tests/output")
    
    # Check output files
    assert os.path.exists("tests/output/protocol_usdm.json")
    assert os.path.exists("tests/output/provenance.json")
    assert os.path.exists("tests/output/conformance_report.json")
    
    # Validate USDM
    with open("tests/output/protocol_usdm.json") as f:
        usdm = json.load(f)
    
    # Check required entities
    assert 'study' in usdm
    assert 'activities' in usdm['study']
    assert 'encounters' in usdm['study']
    assert 'epochs' in usdm['study']
```

---

## 7. Performance Optimization

### 7.1 Caching Strategy

```python
# Implement caching for expensive operations
class CachedEVSClient(EVSClient):
    """EVS client with persistent caching"""
    
    def __init__(self, cache_dir: str = ".evs_cache"):
        super().__init__(cache_dir)
        self.memory_cache = {}
    
    def search_concept(self, term: str, terminology: str = "ncit") -> Optional[Dict]:
        # Check memory cache first
        cache_key = f"{terminology}_{term}"
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]
        
        # Check disk cache
        result = super().search_concept(term, terminology)
        
        # Update memory cache
        if result:
            self.memory_cache[cache_key] = result
        
        return result
```

### 7.2 Parallel Processing

```python
# Use ThreadPoolExecutor for parallel phase execution
def run_phases_parallel(phases: List[BasePhase], max_workers: int = 4):
    """Run independent phases in parallel"""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(phase.run, ...): phase
            for phase in phases
        }
        
        results = {}
        for future in as_completed(futures):
            phase = futures[future]
            try:
                result = future.result()
                results[phase.config.name] = result
            except Exception as e:
                logger.error(f"Phase {phase.config.name} failed: {e}")
                results[phase.config.name] = PhaseResult(success=False, error=str(e))
        
        return results
```

### 7.3 Memory Management

```python
# Stream large PDFs instead of loading entirely into memory
def extract_text_streaming(pdf_path: str, page_nums: List[int]) -> Iterator[str]:
    """Stream text extraction page by page"""
    doc = fitz.open(pdf_path)
    for page_num in page_nums:
        yield doc[page_num].get_text()
    doc.close()
```

---

## 8. Security Considerations

### 8.1 API Key Management

- Store API keys in `.env` file (never commit to git)
- Use environment variables for production
- Rotate keys regularly
- Use separate keys for dev/staging/prod

### 8.2 Data Privacy

- No data sent to external services except LLM APIs
- LLM providers may log requests (check provider policies)
- Consider on-premise LLM deployment for sensitive data
- Implement data anonymization for testing

### 8.3 Input Validation

```python
def validate_pdf_input(pdf_path: str) -> bool:
    """Validate PDF input"""
    # Check file exists
    if not os.path.exists(pdf_path):
        raise ValueError(f"PDF not found: {pdf_path}")
    
    # Check file size (max 100MB)
    if os.path.getsize(pdf_path) > 100 * 1024 * 1024:
        raise ValueError("PDF too large (max 100MB)")
    
    # Check file type
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError("File must be PDF")
    
    # Try to open with PyMuPDF
    try:
        doc = fitz.open(pdf_path)
        doc.close()
    except Exception as e:
        raise ValueError(f"Invalid PDF: {e}")
    
    return True
```

---

## 9. Monitoring & Logging

### 9.1 Logging Configuration

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('protocol2usdm.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

### 9.2 Usage Tracking

```python
class UsageTracker:
    """Track LLM API usage"""
    
    def __init__(self):
        self.calls = []
        self.total_tokens = 0
        self.total_cost = 0.0
    
    def track_call(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float
    ):
        """Track API call"""
        self.calls.append({
            'model': model,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'cost': cost,
            'timestamp': datetime.now().isoformat()
        })
        self.total_tokens += prompt_tokens + completion_tokens
        self.total_cost += cost
    
    def get_summary(self) -> Dict:
        """Get usage summary"""
        return {
            'total_calls': len(self.calls),
            'total_tokens': self.total_tokens,
            'total_cost': self.total_cost,
            'by_model': self._group_by_model()
        }
```

---

## 10. Appendices

### 10.1 USDM v4.0 Entity Reference

See official CDISC documentation:
- https://www.cdisc.org/standards/foundational/usdm
- https://github.com/cdisc-org/DDF-RA/blob/main/Deliverables/UML/dataStructure.yml

### 10.2 NCI EVS API Reference

- Base URL: https://api-evsrest.nci.nih.gov/api/v1
- Documentation: https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/

### 10.3 CDISC CORE Reference

- CORE Engine: https://www.cdisc.org/standards/conformance
- Download: https://www.cdisc.org/core-download

---

**Document Control:**
- Version: 1.0
- Last Updated: February 27, 2026
- Next Review: March 27, 2026
- Owner: Protocol2USDM Team

