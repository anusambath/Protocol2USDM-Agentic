# USDM Validator

A standalone tool for validating USDM v4.0 JSON files against CDISC conformance rules using the official CDISC CORE Rules Engine.

## Prerequisites

- Python 3.9+
- A CDISC Library API key (free — register at https://www.cdisc.org/cdisc-library)
- Internet connection (for initial setup only)

## Setup (one-time)

### 1. Download the CDISC CORE engine

```bash
python download_core.py
```

This downloads the CORE engine binary (~150 MB) from the official CDISC GitHub releases and extracts it into the `core/` directory.

### 2. Set your CDISC API key

The CORE engine needs a CDISC Library API key to download its rules cache on first run.

**Option A — Environment variable (recommended):**

```bash
# Windows PowerShell
$env:CDISC_LIBRARY_API_KEY="your-api-key-here"

# macOS / Linux
export CDISC_LIBRARY_API_KEY=your-api-key-here
```

**Option B — Command line flag:**

```bash
python validate.py my_usdm.json --api-key your-api-key-here
```

The rules cache is downloaded once and reused for subsequent runs.

## Usage

```bash
python validate.py <usdm_json_file>
```

### Examples

```bash
# Basic validation (report saved to current directory)
python validate.py my_protocol_usdm.json

# Save report to a specific directory
python validate.py my_protocol_usdm.json --output-dir results/

# Pass API key on command line
python validate.py my_protocol_usdm.json --api-key YOUR_KEY
```

### Output

The tool prints a summary to the console and writes a detailed `conformance_report.json`:

```
Validating: my_protocol_usdm.json
Engine: CDISC CORE v0.14.1
Standard: USDM v4.0

Total issues: 12

Entity                         Rule            Count  Message
----------------------------------------------------------------------------------------------------
Code                           CORE-001015         5  The id value is not unique.
EligibilityCriterion           CORE-001018         7  The eligibility criterion is not referenced...

Full report: conformance_report.json
```

The `conformance_report.json` contains:
- **Conformance_Details** — engine version, standard, runtime
- **Issue_Summary** — counts grouped by entity type and rule
- **Issue_Details** — every individual issue with paths and affected attributes

## File Structure

```
usdm-validator/
├── validate.py          # Main validation script
├── download_core.py     # CORE engine downloader
├── README.md            # This file
└── core/                # Created by download_core.py (not included in zip)
    └── core/
        ├── core.exe     # CORE engine binary
        └── resources/
            └── cache/   # Rules cache (created on first validation run)
```

## Troubleshooting

**"CORE engine not found"**
Run `python download_core.py` first.

**"CDISC rules cache not found"**
Set `CDISC_LIBRARY_API_KEY` environment variable or pass `--api-key`.

**"CORE engine timed out"**
Large USDM files may take longer. The default timeout is 120 seconds. For very large files, run the CORE engine directly:
```bash
core\core\core.exe validate -s usdm -v 4-0 -dp "C:\full\path\to\file.json" -o "C:\full\path\to\report" -of JSON
```

**Validation fails with JSONata errors**
Some CORE rules may have bugs with certain USDM structures. You can exclude specific rules:
```bash
core\core\core.exe validate -s usdm -v 4-0 -dp "..." -o "..." -of JSON -er CORE-XXXXXX
```

## References

- CDISC CORE Engine: https://github.com/cdisc-org/cdisc-rules-engine
- CDISC Library: https://www.cdisc.org/cdisc-library
- USDM / DDF Specification: https://www.cdisc.org/ddf
