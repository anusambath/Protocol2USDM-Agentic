# Product Requirements Document (PRD)
# CDISC CORE Validation for USDM 4.0

**Version:** 1.0  
**Date:** February 27, 2026  
**Status:** Final  
**Author:** Protocol2USDM Team

---

## Executive Summary

This document describes the requirements for validating USDM v4.0 JSON output against CDISC conformance rules using a locally downloaded CDISC CORE engine. The validation ensures that extracted protocol data conforms to CDISC standards before regulatory submission.

---

## 1. Product Overview

### 1.1 Problem Statement

USDM JSON output must conform to CDISC standards for regulatory submissions. Manual conformance checking is:

- **Time-consuming:** Requires expert review of hundreds of rules
- **Error-prone:** Easy to miss conformance issues
- **Inconsistent:** Different reviewers may interpret rules differently
- **Not scalable:** Cannot validate large volumes of protocols

### 1.2 Solution

Automated CDISC CORE validation using a locally downloaded conformance engine that:

1. **Validates** USDM JSON against CDISC conformance rules
2. **Reports** issues and warnings with clear descriptions
3. **Runs locally** without requiring internet connectivity
4. **Integrates** seamlessly into the Protocol2USDM pipeline
5. **Caches** rules for performance

### 1.3 Target Users

- **Clinical Data Managers:** Validate protocol data before submission
- **Regulatory Affairs:** Ensure conformance for regulatory submissions
- **Quality Assurance:** Verify data quality and standards compliance
- **Software Developers:** Integrate validation into automated pipelines

---

## 2. Core Features

### 2.1 Local CORE Engine Integration

**Priority:** P0 (Critical)

**Description:** Download and integrate CDISC CORE engine for local validation without internet dependency.

**User Stories:**
- As a data manager, I want to validate USDM JSON locally so I don't depend on internet connectivity
- As a developer, I want to integrate CORE validation into CI/CD pipelines
- As a regulatory reviewer, I want to verify conformance before submission

**Acceptance Criteria:**
- Download CORE engine binary from CDISC
- Store engine in `tools/core/core/core.exe` directory
- Execute engine with USDM JSON input
- Parse engine output (JSON format)
- Report issues and warnings clearly
- Support Windows, macOS, Linux platforms

**Technical Requirements:**
- Python script to download CORE engine
- Subprocess execution of CORE binary
- JSON parsing of CORE output
- Error handling for missing engine
- Platform-specific binary selection

### 2.2 CDISC API Fallback

**Priority:** P1 (High)

**Description:** Fallback to CDISC API when local engine is not available.

**User Stories:**
- As a user without local engine, I want to use CDISC API so I can still validate
- As a developer, I want automatic fallback so validation doesn't fail

**Acceptance Criteria:**
- Check for local engine first
- If not available, check for CDISC_API_KEY
- Call CDISC API with USDM JSON
- Parse API response
- Report issues and warnings
- Handle API errors gracefully

**Technical Requirements:**
- CDISC API client implementation
- API key management (environment variable)
- HTTP request/response handling
- Rate limiting and retry logic
- Error handling for API failures

### 2.3 Conformance Report Generation

**Priority:** P0 (Critical)

**Description:** Generate detailed conformance report with issues, warnings, and recommendations.

**User Stories:**
- As a data manager, I want a detailed report so I can fix conformance issues
- As a regulatory reviewer, I want to see all issues in one place
- As a developer, I want machine-readable output for automation

**Acceptance Criteria:**
- Report includes issue count, warning count
- Each issue has: rule ID, severity, description, location
- Report saved as JSON file
- Report includes validation timestamp
- Report indicates engine used (local/API)
- Clear error messages for validation failures

**Technical Requirements:**
- JSON report schema
- Issue categorization (error/warning/info)
- Location tracking (entity ID, field name)
- Timestamp generation
- File I/O for report saving

### 2.4 Rules Cache Management

**Priority:** P2 (Medium)

**Description:** Cache CDISC conformance rules locally for performance and offline use.

**User Stories:**
- As a user, I want fast validation so I don't wait for rule downloads
- As a developer, I want offline validation so I can work without internet
- As an admin, I want to update rules cache when new versions are released

**Acceptance Criteria:**
- Download rules from CDISC API
- Store rules in local cache directory
- Use cached rules for validation
- Support cache update command
- Cache includes version information
- Automatic cache refresh (configurable interval)

**Technical Requirements:**
- Cache directory management
- Rule download from CDISC API
- Cache versioning
- Cache expiration logic
- Update command implementation

### 2.5 Pipeline Integration

**Priority:** P0 (Critical)

**Description:** Integrate CORE validation into Protocol2USDM pipeline as final step.

**User Stories:**
- As a data manager, I want automatic validation after extraction
- As a developer, I want validation as part of the pipeline
- As a user, I want to skip validation if needed (--no-conformance flag)

**Acceptance Criteria:**
- Validation runs automatically with --conformance flag
- Validation runs as part of --complete mode
- Validation can be skipped with --no-conformance
- Validation report saved in output directory
- Pipeline continues even if validation fails (non-blocking)
- Validation results logged clearly

**Technical Requirements:**
- Integration with pipeline orchestrator
- Command-line flag handling
- Non-blocking execution
- Result logging
- Output file management

---

## 3. User Workflows

### 3.1 First-Time Setup

**Actor:** Clinical Data Manager

**Preconditions:**
- Protocol2USDM installed
- Python environment configured

**Steps:**
1. Run download command: `python tools/core/download_core.py`
2. System downloads CORE engine binary
3. System stores engine in `tools/core/core/` directory
4. System verifies engine installation
5. User receives confirmation message

**Postconditions:**
- CORE engine installed and ready
- Validation can run locally

**Success Metrics:**
- Download time: <2 minutes
- Installation success rate: >95%

### 3.2 Validate USDM JSON

**Actor:** Clinical Data Manager

**Preconditions:**
- USDM JSON file available
- CORE engine installed

**Steps:**
1. Run validation: `python run_extraction.py protocol.pdf --conformance`
2. System extracts protocol data
3. System validates USDM JSON with CORE engine
4. System generates conformance report
5. User reviews report for issues

**Postconditions:**
- Conformance report generated
- Issues identified and documented

**Success Metrics:**
- Validation time: <30 seconds
- Report completeness: 100% of issues captured

### 3.3 Update Rules Cache

**Actor:** System Administrator

**Preconditions:**
- CDISC_API_KEY configured
- Internet connectivity

**Steps:**
1. Run update command: `python run_extraction.py --update-cache`
2. System downloads latest rules from CDISC API
3. System updates local cache
4. System verifies cache integrity
5. User receives confirmation message

**Postconditions:**
- Rules cache updated
- Latest conformance rules available

**Success Metrics:**
- Update time: <1 minute
- Cache integrity: 100% verified

---

## 4. Non-Functional Requirements

### 4.1 Performance

- **Validation Time:** <30 seconds for typical USDM JSON (500KB)
- **Engine Startup:** <2 seconds
- **Report Generation:** <1 second
- **Cache Update:** <1 minute

### 4.2 Reliability

- **Validation Success Rate:** >99% for valid USDM JSON
- **Engine Availability:** Local engine preferred, API fallback
- **Error Handling:** Graceful degradation on failures
- **Cache Integrity:** Automatic verification on load

### 4.3 Usability

- **Clear Error Messages:** Actionable descriptions for all issues
- **Report Format:** Human-readable and machine-parseable (JSON)
- **Command-Line Interface:** Simple, intuitive commands
- **Documentation:** Comprehensive user guide

### 4.4 Security

- **API Key Storage:** Environment variable (not committed)
- **Local Execution:** No data sent to external services (local engine)
- **File Permissions:** Restricted access to cache directory
- **Input Validation:** Validate JSON before processing

### 4.5 Compatibility

- **USDM Version:** v4.0
- **CORE Engine:** Latest stable version
- **Operating Systems:** Windows, macOS, Linux
- **Python:** 3.9+

---

## 5. Technical Architecture

### 5.1 Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│              CDISC CORE Validation System                │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Validation Orchestrator              │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐ │  │
│  │  │   Input    │  │  Engine    │  │   Report   │ │  │
│  │  │ Validator  │─▶│  Selector  │─▶│ Generator  │ │  │
│  │  └────────────┘  └────────────┘  └────────────┘ │  │
│  └──────────────────────────────────────────────────┘  │
│                            │                             │
│                            ▼                             │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Validation Engines                   │  │
│  │  ┌────────────┐              ┌────────────┐      │  │
│  │  │   Local    │              │   CDISC    │      │  │
│  │  │    CORE    │              │    API     │      │  │
│  │  │   Engine   │              │   Client   │      │  │
│  │  └────────────┘              └────────────┘      │  │
│  └──────────────────────────────────────────────────┘  │
│                            │                             │
│                            ▼                             │
│  ┌──────────────────────────────────────────────────┐  │
│  │                 Cache Layer                       │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐ │  │
│  │  │   Rules    │  │  Results   │  │  Metadata  │ │  │
│  │  │   Cache    │  │   Cache    │  │   Cache    │ │  │
│  │  └────────────┘  └────────────┘  └────────────┘ │  │
│  └──────────────────────────────────────────────────┘  │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Data Flow

```
USDM JSON
    │
    ├─▶ [Input Validation]
    │       └─▶ Validate JSON structure
    │
    ├─▶ [Engine Selection]
    │       ├─▶ Check local CORE engine
    │       └─▶ Fallback to CDISC API
    │
    ├─▶ [Validation Execution]
    │       ├─▶ Load rules from cache
    │       ├─▶ Execute validation
    │       └─▶ Collect issues/warnings
    │
    ├─▶ [Report Generation]
    │       ├─▶ Format issues
    │       ├─▶ Add metadata
    │       └─▶ Save JSON report
    │
    └─▶ [Output]
            └─▶ conformance_report.json
```

---

## 6. Success Metrics

### 6.1 Validation Quality

- **Issue Detection Rate:** >99% of conformance issues identified
- **False Positive Rate:** <1% of reported issues are false positives
- **Rule Coverage:** 100% of CDISC CORE rules applied

### 6.2 Performance

- **Validation Time:** <30 seconds for typical USDM JSON
- **Engine Startup:** <2 seconds
- **Cache Hit Rate:** >90% for rules

### 6.3 User Satisfaction

- **Setup Time:** <5 minutes for first-time setup
- **Error Resolution:** >80% of issues resolved with report guidance
- **User Adoption:** >90% of users enable conformance validation

---

## 7. Risks & Mitigation

### 7.1 CORE Engine Availability

**Risk:** CORE engine may not be available for download

**Mitigation:**
- Provide fallback to CDISC API
- Include engine binary in repository (if licensing allows)
- Document manual download process
- Cache engine locally after first download

### 7.2 API Rate Limiting

**Risk:** CDISC API may rate-limit requests

**Mitigation:**
- Prefer local engine over API
- Implement exponential backoff for API calls
- Cache API responses
- Document API usage limits

### 7.3 Rule Version Mismatch

**Risk:** Cached rules may be outdated

**Mitigation:**
- Include version information in cache
- Automatic cache refresh (configurable)
- Manual update command
- Warning when cache is old (>30 days)

### 7.4 Platform Compatibility

**Risk:** CORE engine may not work on all platforms

**Mitigation:**
- Test on Windows, macOS, Linux
- Provide platform-specific binaries
- Document platform requirements
- Fallback to API for unsupported platforms

---

## 8. Future Enhancements

### 8.1 Phase 2 Features

- **Custom Rules:** Support for organization-specific conformance rules
- **Rule Editor:** Visual editor for creating custom rules
- **Batch Validation:** Validate multiple USDM files in parallel
- **Validation History:** Track validation results over time
- **Integration Tests:** Automated testing of validation logic

### 8.2 Phase 3 Features

- **Cloud Validation:** SaaS offering for validation
- **Real-time Validation:** Validate during extraction (not just at end)
- **Rule Recommendations:** Suggest fixes for common issues
- **Validation Dashboard:** Web UI for viewing validation results
- **API Integration:** REST API for external systems

---

## 9. Appendices

### 9.1 Glossary

- **CDISC:** Clinical Data Interchange Standards Consortium
- **CORE:** Conformance Rules Engine
- **USDM:** Unified Study Definitions Model
- **Conformance:** Adherence to CDISC standards
- **Rule:** A conformance requirement that must be met

### 9.2 References

- CDISC CORE: https://www.cdisc.org/standards/conformance
- USDM v4.0: https://www.cdisc.org/standards/foundational/usdm
- CDISC API: https://www.cdisc.org/cdisc-api

---

**Document Control:**
- Version: 1.0
- Last Updated: February 27, 2026
- Next Review: March 27, 2026
- Owner: Protocol2USDM Team
