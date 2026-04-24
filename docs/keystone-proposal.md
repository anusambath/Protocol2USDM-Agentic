# PRISM — Protocol Reading and Intelligent Structure Mapping

### Keystone Project Proposal

## 1. Target Personas

### Primary: Clinical Data Standards Programmer
These are the people at pharma companies and CROs (Contract Research Organizations) who today spend weeks manually reading a 50–80 page clinical trial protocol PDF and hand-coding the structured data into CDISC-compliant formats. They know USDM, SDTM, and CDISC terminology inside out, but their work is tedious, error-prone, and bottlenecked by the sheer volume of unstructured text. They don't need AI to think for them — they need it to do the first 80% of the extraction so they can focus on review and correction.

**Pain point:** A single protocol takes 2–4 weeks of manual effort to convert into structured USDM JSON. With 4,000+ new trials registered on ClinicalTrials.gov each year, the backlog is enormous.

### Secondary: Clinical Operations / Study Start-Up Teams
These teams are responsible for getting a trial operational — setting up sites, configuring EDC (Electronic Data Capture) systems, building the Schedule of Assessments in their CTMS (Clinical Trial Management System). They consume the structured data that the standards programmers produce. Faster, more accurate structured output means faster study start-up.

**Pain point:** Study start-up timelines are 3–6 months. Delays in getting structured protocol data cascade into delays in site activation, patient enrollment, and ultimately drug approval.

### Tertiary: Regulatory & Compliance Teams
CDISC's Unified Study Definitions Model (USDM) is becoming the standard for digital protocol exchange. Regulatory agencies (FDA, EMA) are moving toward requiring machine-readable protocol submissions. Teams responsible for regulatory compliance need tools that produce schema-valid, terminology-enriched output that passes conformance checks — not just "close enough" JSON.

**Pain point:** Manual USDM authoring is so labor-intensive that most organizations haven't adopted it yet, despite regulatory pressure. The tooling gap is the blocker.

---

## 2. Why Agentic AI and Not Rule-Based

### The Problem with Rules
Clinical trial protocols are authored by humans in natural language. There is no universal template. A Phase 3 oncology protocol from Pfizer looks nothing like a Phase 1 PK study from Alexion — different structure, different terminology, different table layouts, different footnote conventions. Rule-based systems fail here because:

- **No consistent structure.** Section numbering, heading styles, and document organization vary wildly across sponsors. A rule that says "eligibility criteria are in Section 5" breaks when Lilly puts them in Section 10.
- **Tables are visual, not textual.** The Schedule of Activities (SoA) — the most data-dense part of the protocol — is a complex multi-page table with merged cells, superscript footnote markers, and epoch headers that span columns. PDF text extraction produces garbled output. You need vision models to interpret the visual layout.
- **Context matters.** "Day -7" under an epoch header "Inpatient Period 1" means something different than "Day -7" under "Check-In." Understanding which encounter belongs to which epoch requires spatial reasoning about merged cell boundaries — not string matching.
- **Terminology is ambiguous.** The same concept appears as "Adverse Events", "AEs", "Safety Assessments", or "Treatment-Emergent Adverse Events" across different protocols. Mapping these to CDISC controlled terminology codes (like NCI EVS C-codes) requires semantic understanding, not lookup tables.

### Why Agents Specifically
A single monolithic LLM call cannot handle a 74-page protocol. The context window would be consumed by the raw text, leaving no room for the detailed extraction instructions needed for each entity type. Our agentic approach solves this by decomposition:

- **14 specialized extraction agents**, each with a focused prompt and targeted pages. The metadata agent reads pages 0–2. The eligibility agent finds and reads only the inclusion/exclusion criteria sections. The SoA vision agent processes only the table pages. Each agent is an expert at one thing.
- **Wave-based parallel execution.** Independent agents run simultaneously (metadata, narrative, SoA vision all in wave 0), while dependent agents wait for their inputs (SoA text needs vision results, scheduling needs procedures). This cuts wall-clock time from what would be 30+ minutes sequentially to ~8 minutes.
- **Shared Context Store.** All agents write to a common entity store. The reconciliation agent then detects duplicates across agents (e.g., both the procedures agent and the execution agent extract "Physical Examination") and merges them intelligently based on source priority.
- **Quality pipeline.** After extraction, four quality agents run: post-processing (cleanup), reconciliation (dedup), validation (schema checks), and enrichment (NCI EVS terminology codes). This layered approach catches errors that any single agent would miss.
- **Provenance tracking.** Every entity records which agent extracted it, from which PDF pages, with what confidence score. This makes the output auditable — a critical requirement in regulated industries.

A rule-based system would need to be re-engineered for every new protocol format. The agentic system adapts because each agent uses an LLM that can reason about novel layouts and terminology.

---

## 3. What's Our MOAT? (Why Not Just Use ChatGPT)

### What happens when you paste a protocol into ChatGPT
You get a decent summary. Maybe a rough table of eligibility criteria. But you don't get:
- A 6,000-line schema-valid USDM v4.0 JSON with 40+ entity types
- NCI EVS terminology codes (C-codes) on every coded field
- A Schedule of Activities with correct epoch-encounter mappings extracted from visual table layout
- Cell-level provenance tracking back to specific PDF pages
- CDISC CORE conformance validation

ChatGPT is a general-purpose conversational AI. It doesn't know what USDM v4.0 is. It doesn't know that a StudyEpoch needs a `type` Code object with codeSystem `http://www.cdisc.org`. It doesn't know that encounter names must be unique within a timeline, or that visit windows are not encounters.

### Our specific advantages

**1. Domain-Specific Schema Compliance**
The output isn't "structured data" in a generic sense — it's a specific, validated USDM v4.0 JSON document that conforms to the CDISC DDF schema. The USDM generator enforces required fields, correct instanceTypes, proper Code object structure, and relationship integrity (e.g., every ScheduledActivityInstance references valid epoch, encounter, and activity IDs). We run automated schema validation and optional CDISC CORE engine conformance checking on every output.

**2. Vision + Text Multimodal Extraction**
The SoA table — often the most valuable part of the protocol — cannot be extracted from text alone. PDF text extraction of complex tables produces unusable output. We render SoA pages as images and use vision models to extract the column hierarchy (epochs, encounters, timepoints) from the visual layout, then cross-reference with text extraction for the cell-level data. This dual-modality approach with reconciliation is something a chat interface simply cannot do.

**3. Terminology Enrichment Pipeline**
Raw extraction gives you "Phase 3" as a string. Our enrichment agent queries the NCI Enterprise Vocabulary Services (EVS) API to resolve it to `{code: "C49686", codeSystem: "http://www.cdisc.org", decode: "Phase III Trial"}`. This happens for study phases, epoch types, intervention types, route of administration, dosage forms, and more — 85+ API calls per protocol. This is the difference between "looks right" and "submittable to FDA."

**4. Provenance and Auditability**
In regulated industries, you can't just trust AI output — you need to verify it. Every entity in our output traces back to specific PDF pages and the agent that extracted it. The web UI shows color-coded provenance: green means both vision and text agents agree, orange means only one source. This lets a human reviewer quickly focus on low-confidence extractions rather than re-reading the entire protocol.

**5. Reproducible, Automated Pipeline**
ChatGPT requires a human in the loop for every protocol. Our pipeline runs end-to-end: `python run_extraction.py protocol.pdf` → USDM JSON + provenance + validation report in ~10 minutes. No copy-pasting, no prompt engineering, no manual assembly. This is the difference between a tool and a product.

**6. Extensible Agent Architecture**
Adding a new entity type (say, biomarker assay details) means adding one new extraction agent with its own prompt and page-finding logic. The orchestrator, context store, reconciliation, and USDM generator all work automatically. The architecture scales to new requirements without rewriting the pipeline.

### The real moat: domain depth
General-purpose AI tools will always be broader. Our advantage is depth. We've encoded months of domain knowledge about CDISC standards, USDM schema quirks, clinical protocol conventions, and edge cases (like Unicode superscript footnote markers, or epoch names that differ by a single digit) into a purpose-built system. That domain depth compounds — every protocol we process reveals new edge cases that get fixed in the pipeline, making the next extraction better.
