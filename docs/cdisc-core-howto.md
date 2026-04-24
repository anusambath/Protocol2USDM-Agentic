# How To: CDISC CORE Rules Engine — Download & USDM Validation

## What is the CDISC CORE Rules Engine?

The CDISC CORE (Community Open-source Rules Engine) is an open-source tool maintained by CDISC that validates clinical data files against CDISC conformance rules. It supports multiple standards including SDTM, ADaM, and USDM. For our purposes, we use it to validate USDM v4.0 JSON files against the official CDISC DDF schema and business rules.

GitHub repository: https://github.com/cdisc-org/cdisc-rules-engine

## Prerequisites

- Windows, macOS, or Linux
- A CDISC Library API key (free — register at https://www.cdisc.org/cdisc-library)

## 1. Download the CORE Engine

1. Go to https://github.com/cdisc-org/cdisc-rules-engine/releases
2. Find the latest release (e.g., v0.14.1)
3. Download the appropriate binary for your OS:
   - `core-windows.zip` for Windows
   - `core-macos.zip` for macOS
   - `core-linux.zip` for Linux
4. Extract the zip to a directory of your choice (e.g., `C:\tools\cdisc-core\`)
5. The main executable is `core.exe` (Windows) or `core` (macOS/Linux)

### Verify installation

```bash
# Windows
core.exe --version

# macOS / Linux
./core --version
```

## 2. Initialize the Rules Cache (first run only)

The CORE engine needs to download its rules dictionary from the CDISC Library before it can validate anything. This is a one-time setup that takes 2–3 minutes.

```bash
core.exe update-cache --apikey YOUR_CDISC_API_KEY
```

This creates a `resources/cache/rules_dictionary.pkl` file in the engine's directory. Once cached, you don't need to run this again unless you want to update to newer rules.

You can also set the API key as an environment variable instead of passing it on the command line:

```bash
# PowerShell
$env:CDISC_LIBRARY_API_KEY="your-api-key-here"

# Bash
export CDISC_LIBRARY_API_KEY=your-api-key-here
```

## 3. Validate a USDM JSON File

### Basic command

```bash
core.exe validate -s usdm -v 4-0 -dp "C:\path\to\my_usdm.json" -o "C:\path\to\output\report" -of JSON
```

### Parameters explained

| Flag | Description |
|------|-------------|
| `-s usdm` | Standard to validate against (USDM) |
| `-v 4-0` | Standard version (use dashes, not dots: `4-0` not `4.0`) |
| `-dp` | Path to the dataset file (your USDM JSON). Must be an absolute path. |
| `-o` | Output base path for the report. The engine appends `.json` automatically. |
| `-of JSON` | Output format. Options: `JSON`, `XLSX` |
| `-p disabled` | (Optional) Disable the progress bar for cleaner terminal output |
| `-er RULE_ID` | (Optional) Exclude a specific rule from validation. Can be repeated. |

### Full example (Windows)

```bash
core.exe validate ^
    -s usdm ^
    -v 4-0 ^
    -dp "C:\data\my_protocol_usdm.json" ^
    -o "C:\data\conformance_report" ^
    -of JSON ^
    -p disabled
```

### Full example (macOS / Linux)

```bash
./core validate \
    -s usdm \
    -v 4-0 \
    -dp "/data/my_protocol_usdm.json" \
    -o "/data/conformance_report" \
    -of JSON \
    -p disabled
```

The engine writes the report to `conformance_report.json` (appending `.json` to the `-o` path).

## 4. Reading the Conformance Report

The JSON report contains an `issues` array. Each issue looks like:

```json
{
  "rule_id": "CORE-000123",
  "severity": "Error",
  "message": "Missing required field 'label' in StudyEpoch",
  "dataset": "StudyEpoch",
  "variable": "epoch_1"
}
```

Severity levels:
- **Error** — Schema violation or missing required field. Must be fixed for conformance.
- **Warning** — Recommended field missing or best practice not followed. Should be reviewed.
- **Info** — Informational note. No action required.

## 5. Known Issues

- The `-dp` path must be absolute. Relative paths may cause the engine to fail silently.
- The first run after `update-cache` may be slower as the engine loads the rules dictionary into memory.
- If you encounter NoneType or JSONata errors on specific rules, you can exclude individual rules with the `-er` flag:
  ```bash
  core.exe validate -s usdm -v 4-0 -dp "..." -o "..." -of JSON -er CORE-XXXXXX
  ```

## References

- CDISC CORE GitHub: https://github.com/cdisc-org/cdisc-rules-engine
- CDISC Library (API key registration): https://www.cdisc.org/cdisc-library
- USDM / DDF specification: https://www.cdisc.org/ddf
