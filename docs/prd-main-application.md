?# Product Requirements Document (PRD)
# Protocol2USDM - Main Application

**Version:** 1.0  
**Date:** February 27, 2026  
**Status:** Final  
**Author:** Protocol2USDM Team

---

## Executive Summary

Protocol2USDM is an AI-powered clinical protocol extraction pipeline that automatically converts clinical trial protocol PDFs into structured data conforming to the CDISC USDM v4.0 (Unified Study Definitions Model) standard. The system uses multiple Large Language Models (LLMs) to intelligently extract, validate, and structure protocol content, reducing manual data entry time from weeks to minutes.

### Key Value Propositions

- **Time Savings:** Reduce protocol digitization from 40+ hours to 5-10 minutes
- **Accuracy:** Vision-validated extraction with Provenance for every data point
- **Compliance:** Built-in CDISC USDM v4.0 conformance and CORE validation
- **Transparency:** Full Provenance showing source (text/vision/both) for confidence assessment
- **Flexibility:** Support for multiple LLM providers (Google Gemini, OpenAI GPT, Anthropic Claude)

---

## 1. Product Overview

### 1.1 Problem Statement

Clinical trial protocols contain critical study design information that must be digitized for regulatory submissions, study execution, and data analysis. Current manual digitization processes are:

- **Time-consuming:** 40-80 hours per protocol
- **Error-prone:** Manual transcription introduces inconsistencies
- **Non-standardized:** Different teams use different formats
- **Difficult to validate:** No automated conformance checking

### 1.2 Solution

Protocol2USDM automates the extraction and structuring of protocol content using:

1. **Multi-model LLM extraction** for intelligent content understanding
2. **Vision validation** to verify text extraction against actual PDF images
3. **USDM v4.0 alignment** ensuring regulatory compliance
4. **NCI terminology enrichment** for standardized coding
5. **CDISC CORE validation** for conformance checking
6. **Interactive web UI** for review and quality assessment

### 1.3 Target Users

- **Clinical Data Managers:** Primary users who digitize protocols
- **Biostatisticians:** Consumers of structured protocol data
- **Regulatory Affairs:** Users who need CDISC-compliant submissions
- **Clinical Operations:** Teams who execute trials based on protocol data
- **Software Developers:** Teams integrating protocol data into clinical systems

---

## 2. Core Features

### 2.1 Schedule of Activities (SoA) Extraction

**Priority:** P0 (Critical)

**Description:** Extract the Schedule of Activities table from protocol PDFs, including activities, timepoints, epochs, and visit schedules.

**User Stories:**
- As a data manager, I want to automatically extract the SoA table so I can avoid manual transcription
- As a reviewer, I want to see which cells were validated by vision so I can assess confidence
- As a developer, I want structured SoA data in USDM format so I can integrate with downstream systems

**Acceptance Criteria:**
- System identifies SoA pages with >95% accuracy
- Extracts activities, timepoints, epochs, encounters with proper hierarchy
- Validates text extraction against PDF images
- Tags each cell with Provenance (text/vision/both)
- Outputs USDM-compliant JSON with proper entity relationships

**Technical Requirements:**
- Vision-based page identification
- Text extraction with structure preservation
- Vision validation with confidence scoring
- Provenance for all extracted data
- USDM entity mapping (Activity, Encounter, Epoch, ScheduledActivityInstance)

### 2.2 Study Metadata Extraction

**Priority:** P0 (Critical)

**Description:** Extract core study identifiers, titles, phases, indications, and administrative information.

**User Stories:**
- As a data manager, I want study metadata automatically extracted so I can populate study databases
- As a regulatory reviewer, I want to verify study identifiers match the protocol
- As a developer, I want structured metadata for study registration systems

**Acceptance Criteria:**
- Extracts study title, protocol ID, NCT number, sponsor
- Identifies study phase (Phase 1, 2, 3, 4)
- Extracts indication and therapeutic area
- Captures protocol version and amendment history
- Maps to USDM Study entity with proper codes

**Technical Requirements:**
- Multi-page text extraction (cover page, synopsis, body)
- NCI code mapping for phase, indication
- Version tracking with amendment support
- USDM Study entity generation

### 2.3 Eligibility Criteria Extraction

**Priority:** P0 (Critical)

**Description:** Extract inclusion and exclusion criteria with proper categorization and USDM alignment.

**User Stories:**
- As a site coordinator, I want structured eligibility criteria so I can screen patients efficiently
- As a data manager, I want criteria linked to study metadata so I understand context
- As a developer, I want machine-readable criteria for patient matching algorithms

**Acceptance Criteria:**
- Separates inclusion vs. exclusion criteria
- Preserves criterion numbering and hierarchy
- Links criteria to indication/phase from metadata
- Maps to USDM EligibilityCriterion entities
- Supports nested criteria (sub-bullets)

**Technical Requirements:**
- Context-aware extraction (uses metadata for indication/phase)
- Hierarchical structure preservation
- USDM EligibilityCriterion entity generation
- Category classification (inclusion/exclusion)

### 2.4 Objectives & Endpoints Extraction

**Priority:** P1 (High)

**Description:** Extract study objectives (primary, secondary, exploratory) and associated endpoints with proper linkage.

**User Stories:**
- As a biostatistician, I want structured endpoints so I can plan statistical analyses
- As a regulatory reviewer, I want to verify endpoint alignment with objectives
- As a data manager, I want endpoint-objective linkage for study documentation

**Acceptance Criteria:**
- Classifies objectives by level (primary, secondary, exploratory)
- Extracts endpoints with proper objective linkage
- Identifies endpoint type (efficacy, safety, PK, PD)
- Maps to USDM Objective and Endpoint entities
- Preserves objective-endpoint relationships

**Technical Requirements:**
- Multi-section extraction (objectives, endpoints, estimands)
- Relationship mapping between objectives and endpoints
- USDM Objective, Endpoint, Estimand entity generation
- Context-aware extraction (uses metadata)

### 2.5 Study Design Structure Extraction

**Priority:** P1 (High)

**Description:** Extract study arms, epochs, study cells, and transition rules defining the study design.

**User Stories:**
- As a clinical operations manager, I want study design structure so I can plan study execution
- As a data manager, I want arm definitions linked to SoA so I understand visit schedules per arm
- As a developer, I want structured design for randomization systems

**Acceptance Criteria:**
- Extracts study arms with descriptions and ratios
- Identifies epochs with proper sequencing
- Creates study cells (arm-epoch combinations)
- Extracts transition rules between epochs
- Links to SoA entities (epochs, encounters)

**Technical Requirements:**
- Context-aware extraction (uses SoA epochs)
- USDM StudyArm, Epoch, StudyCell, TransitionRule entities
- Relationship mapping (arm-epoch-cell)
- Sequence preservation (epoch ordering)

### 2.6 Interventions & Products Extraction

**Priority:** P1 (High)

**Description:** Extract investigational products, comparators, and intervention details with dosing information.

**User Stories:**
- As a pharmacist, I want structured drug information so I can prepare study medications
- As a data manager, I want products linked to arms so I understand treatment assignments
- As a regulatory reviewer, I want to verify product specifications

**Acceptance Criteria:**
- Extracts investigational products and comparators
- Captures dosing information (dose, route, frequency)
- Links products to study arms
- Maps to USDM StudyIntervention, StudyProduct entities
- Includes substance details (active ingredients)

**Technical Requirements:**
- Context-aware extraction (uses arms from study design)
- USDM StudyIntervention, StudyProduct, Substance entities
- Arm-product linkage
- Dosing regimen extraction

### 2.7 Execution Model Extraction

**Priority:** P1 (High)

**Description:** Extract temporal semantics including time anchors, visit windows, subject state machine, dosing regimens, and conditional logic.

**User Stories:**
- As a clinical operations manager, I want visit windows so I can schedule patient visits
- As a developer, I want state machine logic so I can build subject tracking systems
- As a data manager, I want conditional rules so I understand protocol decision points

**Acceptance Criteria:**
- Extracts time anchors (FirstDose, Baseline, Randomization, etc.)
- Identifies visit windows (target day, window before/after)
- Captures subject state machine (states, transitions)
- Extracts dosing regimens with schedules
- Identifies conditional logic (footnotes, decision points)
- Extracts repetition patterns (cycles)
- Maps to native USDM entities (not extensions)

**Technical Requirements:**
- USDM Timing entities with windowLower/windowUpper (ISO 8601)
- TransitionRule entities for state machine
- Condition + ScheduledDecisionInstance for conditional logic
- Administration entities for dosing
- ScheduledActivityInstance expansion for repetitions
- Epoch/Encounter previousId/nextId chains for traversal

### 2.8 SAP Integration (Conditional Source)

**Priority:** P2 (Medium)

**Description:** Extract analysis populations from Statistical Analysis Plan (SAP) PDFs with STATO ontology mapping and Analysis Result Set (ARS) generation.

**User Stories:**
- As a biostatistician, I want analysis populations extracted from SAP so I can plan analyses
- As a data manager, I want populations linked to protocol so I understand study context
- As a developer, I want ARS structures for analysis system integration

**Acceptance Criteria:**
- Extracts analysis populations (ITT, PP, Safety, etc.)
- Maps populations to STATO ontology codes
- Generates Analysis Result Sets (ARS) with proper linkage
- Links populations to study objectives
- Outputs USDM AnalysisPopulation entities

**Technical Requirements:**
- SAP PDF parsing
- STATO code mapping
- ARS generation with population linkage
- USDM AnalysisPopulation, AnalysisSet entities

### 2.9 Site List Integration (Conditional Source)

**Priority:** P2 (Medium)

**Description:** Import site lists from CSV/Excel files with organization and location details.

**User Stories:**
- As a clinical operations manager, I want site lists imported so I can track study locations
- As a data manager, I want sites linked to protocol so I understand study geography
- As a developer, I want structured site data for CTMS integration

**Acceptance Criteria:**
- Imports sites from CSV/Excel files
- Extracts site identifiers, names, addresses
- Creates organization and location entities
- Maps to USDM StudySite, Organization, Address entities
- Validates required fields (site ID, name)

**Technical Requirements:**
- CSV/Excel parsing
- USDM StudySite, Organization, Address entities
- Data validation and error handling

### 2.10 NCI Terminology Enrichment

**Priority:** P1 (High)

**Description:** Automatically enrich extracted entities with NCI EVS (Enterprise Vocabulary Services) terminology codes.

**User Stories:**
- As a regulatory reviewer, I want standardized terminology codes so I can validate submissions
- As a data manager, I want automatic code assignment so I don't have to look up codes manually
- As a developer, I want coded data for semantic interoperability

**Acceptance Criteria:**
- Enriches activities, indications, phases with NCI codes
- Uses EVS API for code lookup
- Caches terminology for performance
- Updates USDM Code entities with proper codeSystem
- Handles missing codes gracefully

**Technical Requirements:**
- EVS API integration
- Local caching mechanism
- USDM Code entity generation
- Error handling for API failures

### 2.11 USDM Schema Validation

**Priority:** P0 (Critical)

**Description:** Validate output against official USDM v4.0 schema and auto-fix common issues.

**User Stories:**
- As a data manager, I want schema validation so I know output is USDM-compliant
- As a developer, I want auto-fix for common issues so I don't have to manually correct output
- As a regulatory reviewer, I want to verify USDM conformance

**Acceptance Criteria:**
- Validates against USDM v4.0 schema
- Converts simple IDs to UUIDs (USDM requirement)
- Auto-fixes missing required fields
- Validates entity placement in hierarchy
- Synchronizes Provenance IDs with entity IDs
- Reports validation errors clearly

**Technical Requirements:**
- USDM schema loader
- UUID generation and conversion
- Entity placement validation
- Provenance synchronization
- Error reporting

### 2.12 CDISC CORE Conformance Validation

**Priority:** P1 (High)

**Description:** Validate output against CDISC conformance rules using local CORE engine or CDISC API.

**User Stories:**
- As a regulatory reviewer, I want CORE validation so I can verify conformance
- As a data manager, I want to identify conformance issues before submission
- As a developer, I want automated conformance checking in CI/CD pipelines

**Acceptance Criteria:**
- Runs CDISC CORE conformance rules
- Uses local CORE engine if available
- Falls back to CDISC API if configured
- Generates conformance report with issues/warnings
- Supports cache updates for rules

**Technical Requirements:**
- Local CORE engine integration (core.exe)
- CDISC API integration (fallback)
- Conformance report generation
- Cache management for rules

### 2.13 Web UI - Protocol Viewer

**Priority:** P1 (High)

**Description:** Interactive web application for viewing, reviewing, and assessing extracted protocol data.

**User Stories:**
- As a data manager, I want to review extracted data visually so I can verify accuracy
- As a reviewer, I want to see Provenance for each cell so I can assess confidence
- As a clinical operations manager, I want timeline visualizations so I can understand study flow

**Acceptance Criteria:**
- Displays protocol list with search/filter
- Shows protocol detail with multiple tabs (Overview, SoA, Design, Eligibility, etc.)
- Renders SoA table with color-coded Provenance
- Visualizes timeline with Cytoscape graph
- Shows execution model in tabbed panels
- Displays quality metrics and validation results
- Supports intermediate file viewing

**Technical Requirements:**
- Next.js 16 with App Router
- React 19 with TypeScript
- AG Grid for SoA table
- Cytoscape.js for timeline graph
- Tailwind CSS + shadcn/ui components
- Zustand for state management
- React Query for data fetching

### 2.14 Parallel Execution

**Priority:** P2 (Medium)

**Description:** Run independent extraction phases concurrently to reduce total processing time.

**User Stories:**
- As a data manager, I want faster processing so I can digitize protocols quickly
- As a developer, I want parallel execution so I can optimize resource utilization

**Acceptance Criteria:**
- Identifies independent phases (no dependencies)
- Runs phases in parallel using ThreadPoolExecutor
- Respects phase dependencies (metadata before eligibility)
- Configurable max workers (default: 4)
- Handles errors gracefully (one phase failure doesn't block others)

**Technical Requirements:**
- Dependency graph for phases
- Wave-based execution (phases grouped by dependency level)
- ThreadPoolExecutor with configurable workers
- Error handling and result aggregation

---

## 3. User Workflows

### 3.1 Basic SoA Extraction

**Actor:** Clinical Data Manager

**Preconditions:**
- Protocol PDF available
- API keys configured (.env file)

**Steps:**
1. Run command: `python run_extraction.py protocol.pdf`
2. System identifies SoA pages
3. System extracts SoA table with text extraction
4. System validates extraction with vision
5. System generates USDM JSON output
6. User reviews output in web UI

**Postconditions:**
- `protocol_usdm.json` created with SoA entities
- Provenance file created with source tracking
- Intermediate files saved for debugging

**Success Metrics:**
- Processing time: <5 minutes
- Accuracy: >95% cell extraction
- Provenance: 100% cells tagged

### 3.2 Complete Protocol Extraction

**Actor:** Clinical Data Manager

**Preconditions:**
- Protocol PDF, SAP PDF, site list CSV available
- API keys configured

**Steps:**
1. Run command: `python run_extraction.py protocol.pdf --complete --sap sap.pdf --sites sites.csv --parallel`
2. System runs all extraction phases in parallel waves
3. System enriches entities with NCI codes
4. System validates schema and conformance
5. System generates comprehensive USDM JSON
6. User reviews output in web UI

**Postconditions:**
- Complete USDM JSON with all entities
- Conformance report generated
- Quality metrics calculated

**Success Metrics:**
- Processing time: <10 minutes
- Entity coverage: >90% protocol content
- Conformance: <10 issues

### 3.3 Protocol Review & Quality Assessment

**Actor:** Protocol Reviewer

**Preconditions:**
- Protocol extracted and output available
- Web UI running

**Steps:**
1. Open web UI at http://localhost:3000
2. Navigate to protocol detail page
3. Review SoA table with Provenance colors
4. Check timeline visualization for study flow
5. Review execution model tabs (anchors, visits, etc.)
6. Check quality metrics for entity counts
7. Review conformance report for issues

**Postconditions:**
- Quality assessment completed
- Issues identified for correction

**Success Metrics:**
- Review time: <30 minutes
- Issue identification: 100% of major issues found

---

## 4. Non-Functional Requirements

### 4.1 Performance

- **SoA Extraction:** <5 minutes for typical protocol (50-100 pages)
- **Complete Extraction:** <10 minutes with parallel execution
- **Web UI Load Time:** <2 seconds for protocol list
- **Web UI Interaction:** <500ms for tab switching

### 4.2 Scalability

- **Concurrent Extractions:** Support 4 parallel phases
- **Protocol Size:** Handle protocols up to 500 pages
- **SoA Table Size:** Support tables with 100+ activities, 50+ timepoints
- **Web UI:** Handle 100+ protocols in list

### 4.3 Reliability

- **Extraction Success Rate:** >95% for well-formatted protocols
- **Vision Validation:** >90% cell validation rate
- **API Resilience:** Automatic retry with exponential backoff for rate limits
- **Error Handling:** Graceful degradation (continue on non-critical errors)

### 4.4 Usability

- **Command Line:** Simple, intuitive commands with sensible defaults
- **Web UI:** Modern, responsive design with clear navigation
- **Error Messages:** Clear, actionable error messages
- **Documentation:** Comprehensive user guide and quick reference

### 4.5 Security

- **API Keys:** Stored in .env file (not committed to git)
- **Data Privacy:** No data sent to external services except LLM APIs
- **File Access:** Restricted to input/output directories
- **Web UI:** Local-only (no external access)

### 4.6 Maintainability

- **Code Structure:** Modular, phase-registry architecture
- **Testing:** Unit tests for core functions
- **Logging:** Comprehensive logging for debugging
- **Documentation:** Inline code comments and external docs

### 4.7 Compatibility

- **Python:** 3.9+
- **Operating Systems:** Windows, macOS, Linux
- **Browsers:** Chrome, Firefox, Safari, Edge (latest 2 versions)
- **LLM Providers:** OpenAI, Google (Gemini), Anthropic (Claude)

---

## 5. Technical Architecture

### 5.1 System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Protocol2USDM System                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   run_extraction.py │  │   Pipeline   │  │  Extraction  │      │
│  │  (Entry Point)│─▶│ Orchestrator │─▶│   Phases     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                            │                  │              │
│                            ▼                  ▼              │
│                    ┌──────────────┐  ┌──────────────┐      │
│                    │   Pipeline   │  │     Core     │      │
│                    │   Context    │  │   (USDM)     │      │
│                    └──────────────┘  └──────────────┘      │
│                            │                  │              │
│                            ▼                  ▼              │
│                    ┌──────────────┐  ┌──────────────┐      │
│                    │  Enrichment  │  │  Validation  │      │
│                    │   (EVS API)  │  │ (Schema+CORE)│      │
│                    └──────────────┘  └──────────────┘      │
│                            │                  │              │
│                            └──────┬───────────┘              │
│                                   ▼                          │
│                           ┌──────────────┐                  │
│                           │  USDM JSON   │                  │
│                           │    Output    │                  │
│                           └──────────────┘                  │
│                                   │                          │
│                                   ▼                          │
│                           ┌──────────────┐                  │
│                           │   Web UI     │                  │
│                           │  (Next.js)   │                  │
│                           └──────────────┘                  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Data Flow

```
Protocol PDF
    │
    ├─▶ [SoA Extraction]
    │       ├─▶ Find SoA pages (vision)
    │       ├─▶ Extract text
    │       ├─▶ Validate with vision
    │       └─▶ 02_extraction_soa_vision.json + Provenance
    │
    ├─▶ [Expansion Phases] (parallel)
    │       ├─▶ Metadata → 01_extraction_metadata.json
    │       ├─▶ Eligibility → 06_extraction_eligibility.json
    │       ├─▶ Objectives → 07_extraction_objectives.json
    │       ├─▶ Study Design → 08_extraction_study_design.json
    │       ├─▶ Interventions → 10_extraction_interventions.json
    │       ├─▶ Execution Model → 12_extraction_execution_model.json
    │       └─▶ ... (other phases)
    │
    ├─▶ [Conditional Sources]
    │       ├─▶ SAP → 11_sap_populations.json
    │       └─▶ Sites → 12_site_list.json
    │
    ├─▶ [Combine] → protocol_usdm.json
    │
    ├─▶ [Schema Validation] → Auto-fix UUIDs, entity placement
    │
    ├─▶ [Enrichment] → Add NCI codes via EVS API
    │
    ├─▶ [CDISC CORE] → conformance_report.json
    │
    └─▶ [Web UI] → Visualization + review
```

### 5.3 Technology Stack

**Backend (Python):**
- Python 3.9+
- PyMuPDF (PDF parsing)
- OpenAI SDK (GPT models)
- Google Generative AI SDK (Gemini models)
- Anthropic SDK (Claude models)
- PyYAML (configuration)
- Pandas (data processing)

**Frontend (Web UI):**
- Next.js 16 (React framework)
- React 19 (UI library)
- TypeScript (type safety)
- Tailwind CSS (styling)
- shadcn/ui (component library)
- AG Grid (table rendering)
- Cytoscape.js (graph visualization)
- Zustand (state management)
- React Query (data fetching)

**Infrastructure:**
- Local file system (input/output)
- EVS API (NCI terminology)
- CDISC API (conformance validation)
- LLM APIs (OpenAI, Google, Anthropic)

---

## 6. Success Metrics

### 6.1 Extraction Quality

- **SoA Accuracy:** >95% cell extraction accuracy
- **Entity Coverage:** >90% protocol content extracted
- **Provenance Coverage:** 100% cells tagged with source
- **Vision Validation Rate:** >90% cells validated

### 6.2 Performance

- **SoA Processing Time:** <5 minutes
- **Complete Processing Time:** <10 minutes (parallel)
- **Web UI Load Time:** <2 seconds

### 6.3 Compliance

- **USDM Conformance:** 100% schema-valid output
- **CDISC CORE Issues:** <10 issues per protocol
- **NCI Code Coverage:** >80% entities enriched

### 6.4 User Satisfaction

- **Time Savings:** >90% reduction vs. manual entry
- **Error Reduction:** >80% fewer transcription errors
- **User Adoption:** >80% of data managers use system

---

## 7. Risks & Mitigation

### 7.1 LLM API Availability

**Risk:** LLM APIs may be unavailable or rate-limited

**Mitigation:**
- Support multiple LLM providers (OpenAI, Google, Anthropic)
- Automatic retry with exponential backoff
- Local caching of results
- Fallback to alternative models

### 7.2 Extraction Accuracy

**Risk:** LLMs may hallucinate or miss content

**Mitigation:**
- Vision validation for SoA extraction
- Provenance for confidence assessment
- Multiple extraction attempts with validation
- Human review workflow in web UI

### 7.3 Protocol Format Variability

**Risk:** Protocols have inconsistent formats

**Mitigation:**
- Flexible extraction logic (not template-based)
- Vision-based structure detection
- Graceful degradation for missing sections
- Clear error messages for unsupported formats

### 7.4 USDM Schema Changes

**Risk:** USDM schema may evolve

**Mitigation:**
- Schema loader with version support
- Automated schema validation
- Clear version tracking in output
- Migration tools for schema updates

---

## 8. Future Enhancements

### 8.1 Phase 2 Features

- **Interactive Editing:** Edit extracted data in web UI
- **Export Formats:** Export to Excel, Word, PDF
- **Batch Processing:** Process multiple protocols in parallel
- **Template Library:** Pre-configured templates for common protocol types
- **Audit Trail:** Track all changes with user attribution

### 8.2 Phase 3 Features

- **Machine Learning:** Train custom models on protocol corpus
- **Active Learning:** Improve extraction with user feedback
- **Multi-language Support:** Extract protocols in multiple languages
- **Integration APIs:** REST APIs for system integration
- **Cloud Deployment:** SaaS offering with multi-tenancy

---

## 9. Appendices

### 9.1 Glossary

- **USDM:** Unified Study Definitions Model (CDISC standard)
- **CDISC:** Clinical Data Interchange Standards Consortium
- **CORE:** CDISC Conformance Rules Engine
- **EVS:** Enterprise Vocabulary Services (NCI)
- **SoA:** Schedule of Activities
- **SAP:** Statistical Analysis Plan
- **LLM:** Large Language Model
- **Provenance:** Source tracking for extracted data

### 9.2 References

- CDISC USDM v4.0: https://www.cdisc.org/standards/foundational/usdm
- NCI EVS: https://evs.nci.nih.gov/
- CDISC CORE: https://www.cdisc.org/standards/conformance
- OpenAI API: https://platform.openai.com/docs
- Google Gemini: https://ai.google.dev/
- Anthropic Claude: https://www.anthropic.com/

---

**Document Control:**
- Version: 1.0
- Last Updated: February 27, 2026
- Next Review: March 27, 2026
- Owner: Protocol2USDM Team

