# Technical Requirements Document (TRD)
# CDISC CORE Validation for USDM 4.0

**Version:** 1.0  
**Date:** February 27, 2026  
**Status:** Final  
**Author:** Protocol2USDM Team

---

## Executive Summary

This Technical Requirements Document (TRD) provides detailed technical specifications for implementing CDISC CORE validation for USDM v4.0 JSON output. It covers the local CORE engine integration, CDISC API fallback, conformance report generation, and cache management.

---

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│           CDISC CORE Validation System                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Validation Entry Point                     │ │
│  │  ┌──────────────────────────────────────────────────┐  │ │
│  │  │  run_cdisc_conformance(json_path, output_dir)    │  │ │
│  │  └──────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
│                            │                                 │
│                            ▼                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Engine Selection Logic                     │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │ │
│  │  │ Check Local  │─▶│ Check CDISC  │─▶│   Return    │  │ │
│  │  │    Engine    │  │     API      │  │    None     │  │ │
│  │  └──────────────┘  └──────────────┘  └─────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
│                            │                                 │
│                            ▼                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Validation Execution                       │ │
│  │  ┌──────────────┐              ┌──────────────┐        │ │
│  │  │   _run_local │              │  _run_cdisc  │        │ │
│  │  │ _core_engine │              │     _api     │        │ │
│  │  └──────────────┘              └──────────────┘        │ │
│  └────────────────────────────────────────────────────────┘ │
│                            │                                 │
│                            ▼                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Report Generation                          │ │
│  │  ┌──────────────────────────────────────────────────┐  │ │
│  │  │  _save_conformance_report(result, output_path)   │  │ │
│  │  └──────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Module Structure

```
protocol2usdm/
├── validation/
│   ├── __init__.py
│   └── cdisc_conformance.py      # Main validation module
│
├── tools/
│   └── core/
│       ├── download_core.py      # CORE engine downloader
│       ├── README.md              # Setup instructions
│       └── core/
│           └── core.exe           # CORE engine binary (downloaded)
│
└── .core_cache/                   # Rules cache directory
    ├── rules_v1.0.json
    ├── metadata.json
    └── .version
```

---

## 2. Data Models

### 2.1 Conformance Report Schema

```python
@dataclass
class ConformanceIssue:
    """A single conformance issue"""
    rule_id: str                   # e.g., "USDM-001"
    severity: str                  # "error", "warning", "info"
    message: str                   # Human-readable description
    location: Optional[str]        # Entity ID or path
    field: Optional[str]           # Field name
    value: Optional[Any]           # Actual value
    expected: Optional[Any]        # Expected value
    
    def to_dict(self) -> Dict:
        return {
            'rule_id': self.rule_id,
            'severity': self.severity,
            'message': self.message,
            'location': self.location,
            'field': self.field,
            'value': self.value,
            'expected': self.expected
        }

@dataclass
class ConformanceReport:
    """Complete conformance validation report"""
    success: bool                  # Overall validation success
    engine: str                    # "local", "api", or "none"
    timestamp: str                 # ISO 8601 timestamp
    usdm_version: str              # USDM version validated
    core_version: Optional[str]    # CORE engine version
    
    # Counts
    total_issues: int
    errors: int
    warnings: int
    info: int
    
    # Issues
    issues: List[ConformanceIssue]
    
    # Error details (if validation failed)
    error: Optional[str]
    error_details: Optional[str]
    
    def to_dict(self) -> Dict:
        return {
            'success': self.success,
            'engine': self.engine,
            'timestamp': self.timestamp,
            'usdm_version': self.usdm_version,
            'core_version': self.core_version,
            'summary': {
                'total_issues': self.total_issues,
                'errors': self.errors,
                'warnings': self.warnings,
                'info': self.info
            },
            'issues': [issue.to_dict() for issue in self.issues],
            'error': self.error,
            'error_details': self.error_details
        }
```

### 2.2 Cache Metadata Schema

```python
@dataclass
class CacheMetadata:
    """Metadata for rules cache"""
    version: str                   # Cache version
    core_version: str              # CORE engine version
    download_date: str             # ISO 8601 timestamp
    rule_count: int                # Number of rules
    checksum: str                  # SHA256 checksum
    
    def to_dict(self) -> Dict:
        return {
            'version': self.version,
            'core_version': self.core_version,
            'download_date': self.download_date,
            'rule_count': self.rule_count,
            'checksum': self.checksum
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CacheMetadata':
        return cls(
            version=data['version'],
            core_version=data['core_version'],
            download_date=data['download_date'],
            rule_count=data['rule_count'],
            checksum=data['checksum']
        )
```

---

## 3. API Specifications

### 3.1 Main Validation Function

```python
def run_cdisc_conformance(
    json_path: str,
    output_dir: str,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run CDISC CORE conformance validation.
    
    Priority:
    1. Local CDISC CORE engine (if available)
    2. CDISC API (if key configured and reachable)
    
    If validation fails, the error is captured and returned (no fallback).
    
    Args:
        json_path: Path to USDM JSON file
        output_dir: Directory for output report
        api_key: Optional CDISC API key (from env if not provided)
        
    Returns:
        Dict with conformance results:
        {
            'success': bool,
            'engine': 'local' | 'api' | 'none',
            'timestamp': str,
            'usdm_version': str,
            'core_version': str,
            'summary': {
                'total_issues': int,
                'errors': int,
                'warnings': int,
                'info': int
            },
            'issues': List[Dict],
            'error': Optional[str],
            'error_details': Optional[str]
        }
    """
    output_path = os.path.join(output_dir, "conformance_report.json")
    
    # Try local CORE engine first
    if CORE_ENGINE_PATH.exists():
        result = _run_local_core_engine(json_path, output_dir)
        _save_conformance_report(result, output_path)
        return result
    
    # Try CDISC API if key available
    if api_key is None:
        api_key = os.environ.get('CDISC_API_KEY')
    
    if api_key and _check_cdisc_api_available():
        result = _run_cdisc_api(json_path, output_dir, api_key)
        _save_conformance_report(result, output_path)
        return result
    
    # No validation method available
    result = {
        'success': False,
        'engine': 'none',
        'timestamp': datetime.now().isoformat(),
        'usdm_version': '4.0',
        'core_version': None,
        'summary': {
            'total_issues': 0,
            'errors': 0,
            'warnings': 0,
            'info': 0
        },
        'issues': [],
        'error': 'CDISC CORE engine not available. Download with: python tools/core/download_core.py',
        'error_details': None
    }
    _save_conformance_report(result, output_path)
    return result
```

### 3.2 Local CORE Engine Execution

```python
def _run_local_core_engine(
    json_path: str,
    output_dir: str
) -> Dict[str, Any]:
    """
    Run local CDISC CORE engine.
    
    Args:
        json_path: Path to USDM JSON file
        output_dir: Output directory
        
    Returns:
        Conformance result dict
    """
    logger.info("Running local CDISC CORE engine...")
    
    try:
        # Ensure cache directory exists
        cache_dir = CORE_ENGINE_PATH.parent / "cache"
        cache_dir.mkdir(exist_ok=True)
        
        # Prepare command
        cmd = [
            str(CORE_ENGINE_PATH),
            "--input", json_path,
            "--output", os.path.join(output_dir, "core_output.json"),
            "--cache", str(cache_dir),
            "--format", "json"
        ]
        
        # Execute engine
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )
        
        if result.returncode != 0:
            return {
                'success': False,
                'engine': 'local',
                'timestamp': datetime.now().isoformat(),
                'usdm_version': '4.0',
                'core_version': _get_core_version(),
                'summary': {'total_issues': 0, 'errors': 0, 'warnings': 0, 'info': 0},
                'issues': [],
                'error': 'CORE engine execution failed',
                'error_details': result.stderr
            }
        
        # Parse output
        output_path = os.path.join(output_dir, "core_output.json")
        with open(output_path) as f:
            core_output = json.load(f)
        
        # Convert to standard format
        return _parse_core_output(core_output, 'local')
        
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'engine': 'local',
            'timestamp': datetime.now().isoformat(),
            'usdm_version': '4.0',
            'core_version': _get_core_version(),
            'summary': {'total_issues': 0, 'errors': 0, 'warnings': 0, 'info': 0},
            'issues': [],
            'error': 'CORE engine timeout (>60s)',
            'error_details': None
        }
    except Exception as e:
        logger.error(f"Local CORE engine failed: {e}")
        return {
            'success': False,
            'engine': 'local',
            'timestamp': datetime.now().isoformat(),
            'usdm_version': '4.0',
            'core_version': _get_core_version(),
            'summary': {'total_issues': 0, 'errors': 0, 'warnings': 0, 'info': 0},
            'issues': [],
            'error': str(e),
            'error_details': None
        }
```

### 3.3 CDISC API Client

```python
def _run_cdisc_api(
    json_path: str,
    output_dir: str,
    api_key: str
) -> Dict[str, Any]:
    """
    Run CDISC API validation.
    
    Args:
        json_path: Path to USDM JSON file
        output_dir: Output directory
        api_key: CDISC API key
        
    Returns:
        Conformance result dict
    """
    logger.info("Running CDISC API validation...")
    
    try:
        # Load USDM JSON
        with open(json_path) as f:
            usdm_data = json.load(f)
        
        # Call CDISC API
        url = "https://api.cdisc.org/conformance/v1/validate"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "standard": "USDM",
            "version": "4.0",
            "data": usdm_data
        }
        
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        # Parse response
        api_output = response.json()
        return _parse_core_output(api_output, 'api')
        
    except requests.exceptions.RequestException as e:
        logger.error(f"CDISC API failed: {e}")
        return {
            'success': False,
            'engine': 'api',
            'timestamp': datetime.now().isoformat(),
            'usdm_version': '4.0',
            'core_version': None,
            'summary': {'total_issues': 0, 'errors': 0, 'warnings': 0, 'info': 0},
            'issues': [],
            'error': f'CDISC API error: {str(e)}',
            'error_details': None
        }
```

### 3.4 Output Parsing

```python
def _parse_core_output(
    core_output: Dict,
    engine: str
) -> Dict[str, Any]:
    """
    Parse CORE engine output to standard format.
    
    Args:
        core_output: Raw CORE output
        engine: Engine type ('local' or 'api')
        
    Returns:
        Standardized conformance result
    """
    issues = []
    error_count = 0
    warning_count = 0
    info_count = 0
    
    # Parse issues from CORE output
    for issue_data in core_output.get('issues', []):
        severity = issue_data.get('severity', 'info').lower()
        
        issue = ConformanceIssue(
            rule_id=issue_data.get('rule_id', 'UNKNOWN'),
            severity=severity,
            message=issue_data.get('message', ''),
            location=issue_data.get('location'),
            field=issue_data.get('field'),
            value=issue_data.get('value'),
            expected=issue_data.get('expected')
        )
        issues.append(issue)
        
        # Count by severity
        if severity == 'error':
            error_count += 1
        elif severity == 'warning':
            warning_count += 1
        else:
            info_count += 1
    
    return {
        'success': error_count == 0,
        'engine': engine,
        'timestamp': datetime.now().isoformat(),
        'usdm_version': '4.0',
        'core_version': core_output.get('core_version', _get_core_version()),
        'summary': {
            'total_issues': len(issues),
            'errors': error_count,
            'warnings': warning_count,
            'info': info_count
        },
        'issues': [issue.to_dict() for issue in issues],
        'error': None,
        'error_details': None
    }
```

---

## 4. CORE Engine Download

### 4.1 Download Script

```python
#!/usr/bin/env python3
"""
Download CDISC CORE engine binary.

Usage:
    python tools/core/download_core.py
"""

import os
import sys
import platform
import requests
from pathlib import Path
import zipfile
import tarfile

# CORE engine download URLs (platform-specific)
CORE_URLS = {
    'Windows': 'https://www.cdisc.org/downloads/core/core-windows-x64.zip',
    'Darwin': 'https://www.cdisc.org/downloads/core/core-macos-x64.tar.gz',
    'Linux': 'https://www.cdisc.org/downloads/core/core-linux-x64.tar.gz'
}

def download_core_engine():
    """Download CORE engine for current platform."""
    # Detect platform
    system = platform.system()
    if system not in CORE_URLS:
        print(f"Error: Unsupported platform: {system}")
        print("Supported platforms: Windows, macOS (Darwin), Linux")
        sys.exit(1)
    
    url = CORE_URLS[system]
    print(f"Downloading CORE engine for {system}...")
    print(f"URL: {url}")
    
    # Create output directory
    output_dir = Path(__file__).parent / "core"
    output_dir.mkdir(exist_ok=True)
    
    # Download file
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    # Determine file extension
    if url.endswith('.zip'):
        archive_path = output_dir / "core.zip"
    else:
        archive_path = output_dir / "core.tar.gz"
    
    # Save archive
    with open(archive_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"Downloaded to: {archive_path}")
    
    # Extract archive
    print("Extracting...")
    if archive_path.suffix == '.zip':
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(output_dir)
    else:
        with tarfile.open(archive_path, 'r:gz') as tar_ref:
            tar_ref.extractall(output_dir)
    
    # Remove archive
    archive_path.unlink()
    
    # Make executable (Unix-like systems)
    if system in ['Darwin', 'Linux']:
        core_exe = output_dir / "core"
        core_exe.chmod(0o755)
    
    print("✓ CORE engine installed successfully!")
    print(f"Location: {output_dir}")
    
    # Verify installation
    core_exe = output_dir / ("core.exe" if system == "Windows" else "core")
    if core_exe.exists():
        print("✓ Verification passed")
    else:
        print("✗ Verification failed: core executable not found")
        sys.exit(1)

if __name__ == "__main__":
    try:
        download_core_engine()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
```

---

## 5. Cache Management

### 5.1 Cache Structure

```
.core_cache/
├── rules_v1.0.json          # Conformance rules
├── metadata.json            # Cache metadata
└── .version                 # Cache version file
```

### 5.2 Cache Update Function

```python
def update_core_cache(api_key: str) -> bool:
    """
    Update CORE rules cache from CDISC API.
    
    Args:
        api_key: CDISC API key
        
    Returns:
        True if update successful
    """
    logger.info("Updating CORE rules cache...")
    
    try:
        # Download rules from CDISC API
        url = "https://api.cdisc.org/conformance/v1/rules"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        rules_data = response.json()
        
        # Create cache directory
        cache_dir = Path(".core_cache")
        cache_dir.mkdir(exist_ok=True)
        
        # Save rules
        rules_path = cache_dir / "rules_v1.0.json"
        with open(rules_path, 'w') as f:
            json.dump(rules_data, f, indent=2)
        
        # Calculate checksum
        import hashlib
        with open(rules_path, 'rb') as f:
            checksum = hashlib.sha256(f.read()).hexdigest()
        
        # Save metadata
        metadata = CacheMetadata(
            version="1.0",
            core_version=rules_data.get('version', 'unknown'),
            download_date=datetime.now().isoformat(),
            rule_count=len(rules_data.get('rules', [])),
            checksum=checksum
        )
        
        metadata_path = cache_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2)
        
        # Save version file
        version_path = cache_dir / ".version"
        with open(version_path, 'w') as f:
            f.write("1.0")
        
        logger.info(f"✓ Cache updated: {len(rules_data.get('rules', []))} rules")
        return True
        
    except Exception as e:
        logger.error(f"Cache update failed: {e}")
        return False
```

### 5.3 Cache Validation

```python
def validate_cache() -> bool:
    """
    Validate cache integrity.
    
    Returns:
        True if cache is valid
    """
    cache_dir = Path(".core_cache")
    
    # Check required files
    required_files = ["rules_v1.0.json", "metadata.json", ".version"]
    for filename in required_files:
        if not (cache_dir / filename).exists():
            logger.warning(f"Cache missing file: {filename}")
            return False
    
    # Load metadata
    metadata_path = cache_dir / "metadata.json"
    with open(metadata_path) as f:
        metadata = CacheMetadata.from_dict(json.load(f))
    
    # Verify checksum
    rules_path = cache_dir / "rules_v1.0.json"
    import hashlib
    with open(rules_path, 'rb') as f:
        actual_checksum = hashlib.sha256(f.read()).hexdigest()
    
    if actual_checksum != metadata.checksum:
        logger.warning("Cache checksum mismatch")
        return False
    
    # Check age (warn if >30 days)
    download_date = datetime.fromisoformat(metadata.download_date)
    age_days = (datetime.now() - download_date).days
    
    if age_days > 30:
        logger.warning(f"Cache is {age_days} days old. Consider updating.")
    
    return True
```

---

## 6. Integration with Pipeline

### 6.1 Pipeline Integration

```python
# In run_extraction.py

def main():
    # ... (argument parsing)
    
    # Run extraction phases
    result = run_from_files(
        pdf_path=args.pdf_path,
        output_dir=output_dir,
        model_name=args.model,
        phases_to_run=phases_to_run
    )
    
    # Run conformance validation (if requested)
    if args.conformance or args.complete:
        logger.info("Running CDISC CORE conformance validation...")
        
        conformance_result = run_cdisc_conformance(
            json_path=os.path.join(output_dir, "protocol_usdm.json"),
            output_dir=output_dir
        )
        
        if conformance_result['success']:
            logger.info(f"✓ Conformance validation passed")
            logger.info(f"  Issues: {conformance_result['summary']['total_issues']}")
            logger.info(f"  Errors: {conformance_result['summary']['errors']}")
            logger.info(f"  Warnings: {conformance_result['summary']['warnings']}")
        else:
            logger.warning(f"✗ Conformance validation failed")
            if conformance_result.get('error'):
                logger.warning(f"  Error: {conformance_result['error']}")
            else:
                logger.warning(f"  Errors: {conformance_result['summary']['errors']}")
        
        logger.info(f"Conformance report: {output_dir}/conformance_report.json")
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

```python
# tests/test_cdisc_conformance.py

def test_local_engine_execution():
    """Test local CORE engine execution"""
    result = _run_local_core_engine(
        "tests/fixtures/valid_usdm.json",
        "tests/output"
    )
    assert result['success']
    assert result['engine'] == 'local'
    assert 'summary' in result

def test_api_fallback():
    """Test CDISC API fallback"""
    # Mock local engine not available
    with patch('validation.cdisc_conformance.CORE_ENGINE_PATH.exists', return_value=False):
        result = run_cdisc_conformance(
            "tests/fixtures/valid_usdm.json",
            "tests/output",
            api_key="test_key"
        )
        assert result['engine'] in ['api', 'none']

def test_cache_validation():
    """Test cache validation"""
    assert validate_cache() in [True, False]

def test_report_generation():
    """Test conformance report generation"""
    result = {
        'success': True,
        'engine': 'local',
        'timestamp': datetime.now().isoformat(),
        'usdm_version': '4.0',
        'core_version': '1.0',
        'summary': {'total_issues': 0, 'errors': 0, 'warnings': 0, 'info': 0},
        'issues': []
    }
    
    _save_conformance_report(result, "tests/output/conformance_report.json")
    assert os.path.exists("tests/output/conformance_report.json")
```

---

## 8. Error Handling

### 8.1 Error Scenarios

| Scenario | Handling |
|----------|----------|
| CORE engine not found | Fallback to CDISC API |
| CDISC API unavailable | Return error with clear message |
| Invalid USDM JSON | Return validation error |
| Engine timeout | Return timeout error after 60s |
| Cache corruption | Rebuild cache from API |
| Network error | Retry with exponential backoff |

### 8.2 Error Messages

```python
ERROR_MESSAGES = {
    'engine_not_found': 'CDISC CORE engine not available. Download with: python tools/core/download_core.py',
    'api_unavailable': 'CDISC API unavailable. Check API key and network connectivity.',
    'invalid_json': 'Invalid USDM JSON. Check schema validation first.',
    'timeout': 'CORE engine timeout (>60s). Check USDM JSON size.',
    'cache_corrupt': 'Cache corrupted. Update with: python run_extraction.py --update-cache',
    'network_error': 'Network error. Check internet connectivity.'
}
```

---

## 9. Performance Optimization

### 9.1 Caching Strategy

- Cache conformance rules locally
- Cache validation results (keyed by USDM JSON checksum)
- Automatic cache refresh every 30 days
- Manual cache update command

### 9.2 Parallel Validation

```python
def validate_multiple_files(json_paths: List[str], output_dir: str) -> List[Dict]:
    """Validate multiple USDM files in parallel"""
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(run_cdisc_conformance, path, output_dir): path
            for path in json_paths
        }
        
        results = []
        for future in as_completed(futures):
            path = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Validation failed for {path}: {e}")
        
        return results
```

---

## 10. Appendices

### 10.1 CDISC CORE Engine Reference

- Download: https://www.cdisc.org/core-download
- Documentation: https://www.cdisc.org/standards/conformance
- API: https://www.cdisc.org/cdisc-api

### 10.2 USDM v4.0 Reference

- Specification: https://www.cdisc.org/standards/foundational/usdm
- Schema: https://github.com/cdisc-org/DDF-RA/blob/main/Deliverables/UML/dataStructure.yml

---

**Document Control:**
- Version: 1.0
- Last Updated: February 27, 2026
- Next Review: March 27, 2026
- Owner: Protocol2USDM Team
