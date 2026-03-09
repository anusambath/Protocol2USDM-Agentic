# Product Requirements Document (PRD)
# Protocol2USDM Web UI

**Version:** 1.0  
**Date:** February 27, 2026  
**Status:** Final  
**Author:** Protocol2USDM Team

---

## Executive Summary

The Protocol2USDM Web UI is a modern, interactive web application for viewing, reviewing, and analyzing clinical protocol data extracted by the Protocol2USDM pipeline. It provides rich visualizations, Provenance, and quality assessment tools to help clinical data managers, reviewers, and stakeholders understand and validate extracted protocol content.

### Key Value Propositions

- **Visual Protocol Review:** Interactive tables and diagrams for easy protocol understanding
- **Provenance Transparency:** Cell-level Provenance with color-coded confidence indicators
- **Quality Assessment:** Built-in metrics and validation results for data quality verification
- **Timeline Visualization:** Interactive graph-based timeline showing study flow and relationships
- **Execution Model Insights:** Detailed views of temporal semantics, visit windows, and conditional logic
- **Modern UX:** Fast, responsive interface built with Next.js 16 and React 19

---

## 1. Product Overview

### 1.1 Problem Statement

After extracting protocol data with the Protocol2USDM pipeline, users need to:

- **Review extracted data** for accuracy and completeness
- **Understand Provenance** to assess confidence in extracted values
- **Visualize study flow** to verify temporal relationships
- **Assess quality** through metrics and validation results
- **Navigate complex data** across multiple protocol sections

Manual review of JSON files is:
- **Time-consuming:** Difficult to navigate large JSON structures
- **Error-prone:** Easy to miss issues without visualization
- **Not user-friendly:** Requires technical expertise to interpret
- **Lacks context:** No visual representation of relationships

### 1.2 Solution

A modern web application that provides:

1. **Interactive SoA Table** with AG Grid for activities and visits
2. **Timeline Visualization** with Cytoscape.js for study flow
3. **Provenance Explorer** with color-coded confidence indicators
4. **Quality Dashboard** with metrics and validation results
5. **Multi-tab Interface** for all protocol sections
6. **Execution Model Views** for temporal semantics
7. **SAP & ARS Integration** for analysis populations and reporting
8. **VS Code-style Workbench Layout** with ActivityBar, Sidebar, CenterPanel, RightPanel, StatusBar, CommandPalette, and keyboard shortcuts for efficient navigation

### 1.3 Target Users

- **Clinical Data Managers:** Primary users who review and validate extracted data
- **Protocol Reviewers:** Stakeholders who assess protocol accuracy
- **Biostatisticians:** Users who review analysis populations and endpoints
- **Clinical Operations:** Teams who need to understand study flow and visit schedules
- **Quality Assurance:** Teams who verify data quality and conformance

---

## 2. Core Features

### 2.1 Protocol List View

**Priority:** P0 (Critical)

**Description:** Landing page showing all extracted protocols with search and filter capabilities.

**User Stories:**
- As a data manager, I want to see all extracted protocols so I can select one to review
- As a reviewer, I want to search protocols by ID or title so I can find specific protocols quickly
- As a user, I want to see extraction status so I know which protocols are ready for review

**Acceptance Criteria:**
- Display protocol cards with title, ID, date, status
- Search by protocol ID, title, or NCT number
- Filter by extraction status (complete, partial, failed)
- Sort by date (newest first)
- Click card to navigate to protocol detail
- Show protocol count and statistics

**Technical Requirements:**
- Next.js page at `/` (app/page.tsx)
- API endpoint: `GET /api/protocols`
- Protocol card component with metadata
- Search and filter UI components
- Responsive grid layout

### 2.2 Schedule of Activities (SoA) Table

**Priority:** P0 (Critical)

**Description:** Interactive table showing activities (rows) and visits (columns) with Provenance-colored cells.

**User Stories:**
- As a data manager, I want to see the SoA table so I can verify activity schedules
- As a reviewer, I want to see Provenance colors so I can assess confidence in each cell
- As a user, I want to export the table to CSV so I can share with stakeholders

**Acceptance Criteria:**
- Activities displayed as rows with categories
- Visits/timepoints displayed as columns with study days
- Cells show checkmarks (X, Xa, Xb) with Provenance colors:
  - Green: Confirmed by both text and vision
  - Blue: Text-only extraction
  - Orange: Vision-only (needs review)
  - Red: Orphaned (no Provenance)
- Epoch grouping headers for columns
- Footnote superscripts on cells
- Row/column reordering (future: draft/publish workflow)
- CSV export functionality
- Responsive table with horizontal scroll

**Technical Requirements:**
- AG Grid Enterprise for table rendering
- Custom cell renderer for Provenance colors
- Adapter: `toSoATableModel(usdm, provenance, overlay)`
- Zustand store for table state
- Export to CSV functionality

### 2.3 Timeline Visualization

**Priority:** P1 (High)

**Description:** Interactive graph diagram showing study flow with epochs, encounters, activities, and timing relationships.

**User Stories:**
- As a clinical operations manager, I want to see study flow visually so I can understand visit sequences
- As a reviewer, I want to see timing relationships so I can verify study design
- As a user, I want to interact with the diagram so I can explore relationships

**Acceptance Criteria:**
- Graph nodes for epochs, encounters, activities, timings
- Edges showing relationships (encounter-activity, timing-encounter)
- Color-coded nodes by type
- Interactive: hover for details, click for focus
- Drag nodes to reposition (snap-to-grid)
- Lock/unlock nodes for layout preservation
- Zoom and pan controls
- Export diagram as PNG/SVG
- Preset layout from overlay (if available)

**Technical Requirements:**
- Cytoscape.js for graph rendering
- Adapter: `toGraphModel(usdm, overlay)`
- Node types: epoch, encounter, activity, timing, condition
- Edge types: scheduled, timing, conditional
- Overlay schema for node positions
- Canvas component with controls

### 2.4 Provenance Explorer

**Priority:** P1 (High)

**Description:** Detailed view of Provenance data showing Provenance for all extracted entities.

**User Stories:**
- As a data manager, I want to see Provenance details so I can assess extraction confidence
- As a reviewer, I want to see PDF source pages so I can verify extraction accuracy
- As a QA analyst, I want Provenance statistics so I can assess overall quality

**Acceptance Criteria:**
- Provenance statistics dashboard:
  - Total entities extracted
  - Confirmed (text + vision) count and percentage
  - Text-only count and percentage
  - Vision-only count and percentage
  - Orphaned count and percentage
- Entity-level Provenance details:
  - Entity ID and type
  - Field name
  - Source (text/vision/both)
  - Confidence score
  - PDF page number
  - Extraction method and model
- Filter by source type
- Sort by confidence
- Export Provenance data to JSON

**Technical Requirements:**
- Provenance data model from pipeline
- Statistics calculation component
- Entity list with filtering and sorting
- Provenance detail panel
- Color-coded badges for source types

### 2.5 Study Metadata View

**Priority:** P0 (Critical)

**Description:** Display study identifiers, titles, phases, indications, and administrative information.

**User Stories:**
- As a reviewer, I want to see study metadata so I can verify protocol identifiers
- As a data manager, I want to see protocol version history so I can track amendments
- As a user, I want to see sponsor information so I understand study context

**Acceptance Criteria:**
- Study title and short title
- Protocol ID, NCT number, sponsor ID
- Study phase (Phase 1, 2, 3, 4)
- Indication and therapeutic area
- Protocol version and date
- Amendment history (if available)
- Sponsor and organization details
- Study type (interventional, observational)

**Technical Requirements:**
- Read from `study` entity in USDM JSON
- Metadata display component
- Amendment history timeline
- Organization details cards

### 2.6 Eligibility Criteria View

**Priority:** P1 (High)

**Description:** Display inclusion and exclusion criteria with proper categorization and hierarchy.

**User Stories:**
- As a site coordinator, I want to see eligibility criteria so I can screen patients
- As a reviewer, I want to verify criteria completeness so I ensure all criteria are captured
- As a user, I want to see criteria hierarchy so I understand nested criteria

**Acceptance Criteria:**
- Separate tabs for inclusion and exclusion criteria
- Numbered criteria with original numbering preserved
- Nested criteria (sub-bullets) with indentation
- Category labels (if available)
- Search/filter criteria by keyword
- Export criteria to text/PDF

**Technical Requirements:**
- Read from `studyDesign.eligibilityCriteria[]` in USDM
- Criteria list component with hierarchy
- Category grouping
- Search and filter UI

### 2.7 Objectives & Endpoints View

**Priority:** P1 (High)

**Description:** Display study objectives (primary, secondary, exploratory) and associated endpoints.

**User Stories:**
- As a biostatistician, I want to see objectives and endpoints so I can plan analyses
- As a reviewer, I want to verify objective-endpoint linkage so I ensure proper alignment
- As a user, I want to see endpoint types so I understand study goals

**Acceptance Criteria:**
- Objectives grouped by level (primary, secondary, exploratory)
- Endpoints linked to objectives
- Endpoint type (efficacy, safety, PK, PD)
- Estimands (if available)
- Objective-endpoint relationship visualization
- Export to structured format

**Technical Requirements:**
- Read from `objectives[]` and `endpoints[]` in USDM
- Objective cards with linked endpoints
- Relationship diagram (optional)
- Level-based grouping

### 2.8 Study Design View

**Priority:** P1 (High)

**Description:** Display study arms, epochs, study cells, and transition rules.

**User Stories:**
- As a clinical operations manager, I want to see study design so I can plan execution
- As a reviewer, I want to verify arm definitions so I ensure proper randomization
- As a user, I want to see epoch sequences so I understand study phases

**Acceptance Criteria:**
- Study arms with descriptions and ratios
- Epochs with sequencing and types
- Study cells (arm-epoch combinations)
- Transition rules between epochs
- Visual diagram of study design (optional)
- Export study design to diagram

**Technical Requirements:**
- Read from `studyDesign` in USDM
- Arm cards with details
- Epoch timeline
- Study cell matrix
- Transition rule list

### 2.9 Interventions & Products View

**Priority:** P1 (High)

**Description:** Display investigational products, comparators, and intervention details.

**User Stories:**
- As a pharmacist, I want to see product details so I can prepare study medications
- As a reviewer, I want to verify dosing information so I ensure accuracy
- As a user, I want to see product-arm linkage so I understand treatment assignments

**Acceptance Criteria:**
- Interventions grouped by type (investigational, comparator, placebo)
- Product details (name, dose, route, frequency)
- Substance information (active ingredients)
- Arm linkage showing which arms receive which products
- Dosing regimen details
- Export product list

**Technical Requirements:**
- Read from `studyInterventions[]` and `administrableProducts[]` in USDM
- Intervention cards with product details
- Arm-product linkage table
- Dosing regimen display

### 2.10 Execution Model View

**Priority:** P1 (High)

**Description:** Display temporal semantics including time anchors, visit windows, state machine, dosing regimens, and conditional logic.

**User Stories:**
- As a clinical operations manager, I want to see visit windows so I can schedule patient visits
- As a developer, I want to see state machine logic so I can build subject tracking systems
- As a reviewer, I want to see conditional rules so I understand protocol decision points

**Acceptance Criteria:**
- 8 tabbed panels:
  1. **Overview:** Summary statistics and timeline visualization
  2. **Time Anchors:** Temporal reference points (FirstDose, Baseline, etc.)
  3. **Visit Windows:** Target days with window tolerances
  4. **Conditions:** Conditional logic from footnotes
  5. **Repetitions:** Cycle-based patterns
  6. **Dosing Regimens:** Drug administration schedules
  7. **State Machine:** Subject flow states and transitions
  8. **Traversal:** Epoch/encounter chains (previousId/nextId)
- Color-coded badges for anchor types
- Timeline visualization showing visit windows
- State machine diagram
- Export execution model data

**Technical Requirements:**
- Read from `11_execution_model.json` intermediate file
- 8 tab components for each section
- Timeline visualization component
- State machine diagram component
- Execution model data adapter

### 2.11 SAP Data View

**Priority:** P2 (Medium)

**Description:** Display analysis populations from Statistical Analysis Plan with STATO ontology mapping.

**User Stories:**
- As a biostatistician, I want to see analysis populations so I can plan analyses
- As a reviewer, I want to verify population definitions so I ensure accuracy
- As a user, I want to see STATO codes so I understand standardized terminology

**Acceptance Criteria:**
- Analysis populations list (ITT, PP, Safety, etc.)
- Population definitions and criteria
- STATO ontology codes
- Statistical methods
- Population-objective linkage
- Export population data

**Technical Requirements:**
- Read from `11_sap_populations.json` intermediate file
- Population cards with details
- STATO code display
- Method descriptions

### 2.12 CDISC ARS View

**Priority:** P2 (Medium)

**Description:** Display Analysis Result Sets (ARS) with reporting events, analyses, and methods.

**User Stories:**
- As a biostatistician, I want to see ARS structures so I can understand analysis organization
- As a reviewer, I want to verify analysis sets so I ensure proper linkage
- As a user, I want to see reporting events so I understand analysis timing

**Acceptance Criteria:**
- Reporting events list
- Analysis sets with populations
- Analysis methods
- Result groupings
- ARS hierarchy visualization
- Export ARS data

**Technical Requirements:**
- Read from ARS data in USDM or intermediate files
- ARS hierarchy component
- Reporting event timeline
- Analysis set cards

### 2.13 Quality Metrics Dashboard

**Priority:** P1 (High)

**Description:** Display quality metrics and validation results for extracted data.

**User Stories:**
- As a QA analyst, I want to see quality metrics so I can assess extraction quality
- As a data manager, I want to see validation results so I can identify issues
- As a reviewer, I want to see entity counts so I can verify completeness

**Acceptance Criteria:**
- Entity count statistics:
  - Activities, encounters, epochs
  - Objectives, endpoints, estimands
  - Interventions, products, devices
  - Eligibility criteria
  - Organizations, sites
- Provenance statistics (from Provenance Explorer)
- Validation results:
  - Schema validation status
  - CDISC CORE conformance issues
  - Missing required fields
  - Orphaned entities
- Quality score calculation
- Export quality report

**Technical Requirements:**
- Quality metrics calculation
- Validation results parser
- Dashboard component with stat cards
- Chart visualizations (optional)
- Export to PDF/JSON

### 2.14 Intermediate Files Viewer

**Priority:** P2 (Medium)

**Description:** View intermediate extraction files for debugging and transparency.

**User Stories:**
- As a developer, I want to see intermediate files so I can debug extraction issues
- As a reviewer, I want to see raw extraction output so I can verify processing
- As a user, I want to see SoA images so I can verify vision extraction

**Acceptance Criteria:**
- List of intermediate files with descriptions
- JSON viewer with syntax highlighting
- SoA images viewer with page navigation
- Download individual files
- Compare text vs. vision extraction outputs
- View extraction prompts

**Technical Requirements:**
- File list component
- JSON viewer component (syntax highlighting)
- Image viewer component
- File download functionality
- Comparison view for text vs. vision

### 2.15 Draft/Publish Workflow (Future)

**Priority:** P3 (Low - Future Enhancement)

**Description:** Enable users to make presentation changes (layout, ordering) with draft/publish workflow.

**User Stories:**
- As a data manager, I want to reorder table rows so I can group related activities
- As a user, I want to save draft changes so I can work incrementally
- As a reviewer, I want to publish changes so they become visible to others

**Acceptance Criteria:**
- Draft overlay for presentation changes
- Save draft button
- Publish button (promotes draft to published)
- Reset button (discards draft)
- Dirty state indicator
- Overlay version tracking

**Technical Requirements:**
- Overlay schema (node positions, row/column order)
- Draft/publish API endpoints
- Overlay Zustand store
- Draft/publish controls component
- Reconciliation logic for USDM updates

---

## 3. User Workflows

### 3.1 Review Extracted Protocol

**Actor:** Clinical Data Manager

**Preconditions:**
- Protocol extracted by pipeline
- Web UI running

**Steps:**
1. Open web UI at http://localhost:3000
2. See protocol list with recently extracted protocols
3. Click on protocol card to open detail view
4. Review Overview tab for study metadata
5. Navigate to SoA tab to review activity schedule
6. Check Provenance colors for confidence assessment
7. Navigate to Timeline tab to visualize study flow
8. Review Execution Model tabs for temporal details
9. Check Quality Metrics for validation results
10. Export data if needed

**Postconditions:**
- Protocol reviewed and validated
- Issues identified (if any)

**Success Metrics:**
- Review time: <30 minutes for typical protocol
- Issue identification: >95% of issues found

### 3.2 Assess Extraction Quality

**Actor:** QA Analyst

**Preconditions:**
- Protocol extracted with Provenance
- Web UI running

**Steps:**
1. Open protocol detail view
2. Navigate to Provenance tab
3. Review Provenance statistics:
   - Confirmed percentage (target: >80%)
   - Text-only percentage
   - Vision-only percentage (target: <10%)
   - Orphaned percentage (target: <5%)
4. Navigate to Quality Metrics tab
5. Review entity counts for completeness
6. Check validation results for issues
7. Review CDISC CORE conformance report
8. Export quality report

**Postconditions:**
- Quality assessment completed
- Quality score calculated
- Report generated

**Success Metrics:**
- Assessment time: <15 minutes
- Quality score accuracy: >90%

### 3.3 Verify Study Flow

**Actor:** Clinical Operations Manager

**Preconditions:**
- Protocol extracted with execution model
- Web UI running

**Steps:**
1. Open protocol detail view
2. Navigate to Timeline tab
3. Review graph visualization:
   - Verify epoch sequence
   - Check encounter relationships
   - Validate activity assignments
4. Navigate to Execution Model tab
5. Review Visit Windows for scheduling
6. Check State Machine for subject flow
7. Verify Traversal chains (previousId/nextId)
8. Export timeline diagram

**Postconditions:**
- Study flow verified
- Visit schedule understood
- Timeline diagram exported

**Success Metrics:**
- Verification time: <20 minutes
- Flow accuracy: >95%

---

## 4. Non-Functional Requirements

### 4.1 Performance

- **Page Load Time:** <2 seconds for protocol list
- **Protocol Detail Load:** <3 seconds for typical protocol
- **SoA Table Rendering:** <1 second for 100 activities × 50 visits
- **Timeline Rendering:** <2 seconds for 100 nodes
- **Search Response:** <500ms for protocol search
- **Export Time:** <5 seconds for CSV export

### 4.2 Scalability

- **Protocol Count:** Support 100+ protocols in list
- **SoA Table Size:** Handle 200+ activities, 100+ visits
- **Timeline Nodes:** Support 500+ nodes in graph
- **Concurrent Users:** Support 10+ simultaneous users (local deployment)

### 4.3 Usability

- **Modern UI:** Clean, intuitive interface with consistent design
- **Responsive Design:** Works on desktop (1920×1080 minimum)
- **Keyboard Navigation:** Full keyboard support for accessibility
- **Loading States:** Clear loading indicators for async operations
- **Error Messages:** User-friendly error messages with recovery options
- **Help Documentation:** Inline help and tooltips

### 4.4 Accessibility

- **WCAG 2.1 AA Compliance:** Meet accessibility standards
- **Screen Reader Support:** All content accessible via screen readers
- **Keyboard Navigation:** All features accessible via keyboard
- **Color Contrast:** Minimum 4.5:1 contrast ratio
- **Focus Indicators:** Clear focus indicators for interactive elements

### 4.5 Browser Compatibility

- **Chrome:** Latest 2 versions
- **Firefox:** Latest 2 versions
- **Safari:** Latest 2 versions
- **Edge:** Latest 2 versions

### 4.6 Security

- **Local Deployment:** No external data transmission
- **File Access:** Restricted to output directory
- **No Authentication:** Local-only deployment (future: add auth for multi-user)
- **Input Validation:** Validate all user inputs
- **XSS Protection:** Sanitize all user-generated content

---

## 5. Technical Architecture

### 5.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Protocol2USDM Web UI                        │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │              Presentation Layer                     │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │ │
│  │  │  Pages   │  │Components│  │  Styles  │        │ │
│  │  │(Next.js) │  │ (React)  │  │(Tailwind)│        │ │
│  │  └──────────┘  └──────────┘  └──────────┘        │ │
│  └────────────────────────────────────────────────────┘ │
│                            │                             │
│                            ▼                             │
│  ┌────────────────────────────────────────────────────┐ │
│  │              State Management Layer                 │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │ │
│  │  │ Zustand  │  │  React   │  │  Local   │        │ │
│  │  │  Stores  │  │  Query   │  │  State   │        │ │
│  │  └──────────┘  └──────────┘  └──────────┘        │ │
│  └────────────────────────────────────────────────────┘ │
│                            │                             │
│                            ▼                             │
│  ┌────────────────────────────────────────────────────┐ │
│  │              Data Adapter Layer                     │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │ │
│  │  │   SoA    │  │ Timeline │  │Provenance│        │ │
│  │  │ Adapter  │  │ Adapter  │  │ Adapter  │        │ │
│  │  └──────────┘  └──────────┘  └──────────┘        │ │
│  └────────────────────────────────────────────────────┘ │
│                            │                             │
│                            ▼                             │
│  ┌────────────────────────────────────────────────────┐ │
│  │              API Layer (Next.js)                    │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │ │
│  │  │ Protocol │  │  USDM    │  │ Overlay  │        │ │
│  │  │   API    │  │   API    │  │   API    │        │ │
│  │  └──────────┘  └──────────┘  └──────────┘        │ │
│  └────────────────────────────────────────────────────┘ │
│                            │                             │
│                            ▼                             │
│  ┌────────────────────────────────────────────────────┐ │
│  │              File System Layer                      │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │ │
│  │  │   USDM   │  │Provenance│  │Intermediate│       │ │
│  │  │   JSON   │  │   JSON   │  │   Files  │        │ │
│  │  └──────────┘  └──────────┘  └──────────┘        │ │
│  └────────────────────────────────────────────────────┘ │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Data Flow

```
File System (output/)
    │
    ├─▶ protocol_usdm.json
    ├─▶ Provenance.json
    └─▶ intermediate files (11_execution_model.json, etc.)
    │
    ▼
Next.js API Routes
    │
    ├─▶ GET /api/protocols → List protocols
    ├─▶ GET /api/protocols/[id]/usdm → Get USDM + Provenance
    └─▶ GET /api/protocols/[id]/intermediate → Get intermediate files
    │
    ▼
Data Adapters
    │
    ├─▶ toSoATableModel(usdm, provenance, overlay)
    ├─▶ toGraphModel(usdm, overlay)
    └─▶ toProvenanceStats(provenance)
    │
    ▼
React Components
    │
    ├─▶ SoAGrid (AG Grid)
    ├─▶ TimelineCanvas (Cytoscape.js)
    └─▶ ProvenanceExplorer
    │
    ▼
User Interface
```

---

## 6. Success Metrics

### 6.1 User Adoption

- **Usage Rate:** >80% of data managers use web UI for protocol review
- **Review Time Reduction:** >50% reduction vs. manual JSON review
- **User Satisfaction:** >4.0/5.0 rating

### 6.2 Quality Assessment

- **Issue Detection:** >95% of extraction issues identified through UI
- **Provenance Transparency:** 100% of cells have Provenance
- **Quality Score Accuracy:** >90% correlation with manual review

### 6.3 Performance

- **Page Load Time:** <2 seconds (95th percentile)
- **Table Rendering:** <1 second for typical SoA
- **Timeline Rendering:** <2 seconds for typical study

### 6.4 Accessibility

- **WCAG Compliance:** 100% AA compliance
- **Keyboard Navigation:** 100% features accessible via keyboard
- **Screen Reader Support:** All content accessible

---

## 7. Risks & Mitigation

### 7.1 Large Protocol Performance

**Risk:** Large protocols (200+ activities, 100+ visits) may cause performance issues

**Mitigation:**
- Use AG Grid virtualization for large tables
- Implement pagination for large lists
- Lazy load timeline nodes
- Optimize data adapters
- Add loading indicators

### 7.2 Browser Compatibility

**Risk:** Advanced features may not work in older browsers

**Mitigation:**
- Target latest 2 versions of major browsers
- Use polyfills for missing features
- Provide fallback UI for unsupported features
- Test on all target browsers

### 7.3 Data Complexity

**Risk:** Complex USDM structures may be difficult to visualize

**Mitigation:**
- Provide multiple views (table, graph, list)
- Add filtering and search capabilities
- Use progressive disclosure (show details on demand)
- Provide help documentation and tooltips

### 7.4 Provenance Data Size

**Risk:** Large Provenance files may slow down loading

**Mitigation:**
- Load Provenance on-demand (not with initial page load)
- Implement pagination for Provenance entries
- Cache Provenance statistics
- Compress Provenance data

---

## 8. Future Enhancements

### 8.1 Phase 2 Features

- **Semantic Editing:** Edit extracted data with validation
- **Collaborative Review:** Multi-user review with comments
- **Export Formats:** Export to Excel, Word, PDF
- **Custom Views:** User-defined views and filters
- **Comparison Mode:** Compare multiple protocol versions

### 8.2 Phase 3 Features

- **Real-time Collaboration:** Live editing with multiple users
- **AI-Assisted Review:** Automated issue detection
- **Integration APIs:** REST APIs for external systems
- **Mobile Support:** Responsive design for tablets
- **Cloud Deployment:** SaaS offering with authentication

---

## 9. Appendices

### 9.1 Glossary

- **SoA:** Schedule of Activities
- **USDM:** Unified Study Definitions Model
- **Provenance:** Provenance for extracted data
- **Overlay:** Presentation-only data (layout, ordering)
- **Draft/Publish:** Workflow for making changes
- **AG Grid:** Enterprise data grid library
- **Cytoscape.js:** Graph visualization library

### 9.2 References

- Next.js 16: https://nextjs.org/
- AG Grid: https://www.ag-grid.com/
- Cytoscape.js: https://js.cytoscape.org/
- shadcn/ui: https://ui.shadcn.com/
- USDM v4.0: https://www.cdisc.org/standards/foundational/usdm

---

**Document Control:**
- Version: 1.0
- Last Updated: February 27, 2026
- Next Review: March 27, 2026
- Owner: Protocol2USDM Team

