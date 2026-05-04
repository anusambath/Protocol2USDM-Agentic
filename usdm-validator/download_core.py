#!/usr/bin/env python3
"""
Download CDISC CORE Engine from official GitHub releases.
Run this once to set up the CORE engine for USDM validation.
"""

import os
import sys
import zipfile
import platform
import urllib.request
from pathlib import Path

CORE_VERSION = "0.14.1"

PLATFORM_ZIPS = {
    "Windows": f"https://github.com/cdisc-org/cdisc-rules-engine/releases/download/v{CORE_VERSION}/core-windows.zip",
    "Darwin": f"https://github.com/cdisc-org/cdisc-rules-engine/releases/download/v{CORE_VERSION}/core-macos.zip",
    "Linux": f"https://github.com/cdisc-org/cdisc-rules-engine/releases/download/v{CORE_VERSION}/core-linux.zip",
}


def download_core():
    """Download and extract CORE engine for the current platform."""
    system = platform.system()
    url = PLATFORM_ZIPS.get(system)
    if not url:
        print(f"Unsupported platform: {system}")
        sys.exit(1)

    script_dir = Path(__file__).parent
    zip_name = f"core-{system.lower()}.zip"
    zip_path = script_dir / zip_name
    extract_dir = script_dir / "core"

    # Check if already extracted
    exe_name = "core.exe" if system == "Windows" else "core"
    exe_path = extract_dir / exe_name
    if exe_path.exists():
        print(f"CORE engine already installed at: {exe_path}")
        return str(exe_path)

    # Download
    if not zip_path.exists():
        print(f"Downloading CDISC CORE Engine v{CORE_VERSION} for {system}...")
        print(f"URL: {url}")
        try:
            urllib.request.urlretrieve(url, zip_path, _progress)
            print("\nDownload complete")
        except Exception as e:
            print(f"\nDownload failed: {e}")
            print(f"\nManual download:")
            print(f"  1. Go to: https://github.com/cdisc-org/cdisc-rules-engine/releases/tag/v{CORE_VERSION}")
            print(f"  2. Download {zip_name}")
            print(f"  3. Place it in: {script_dir}")
            sys.exit(1)

    # Extract
    print(f"Extracting to: {extract_dir}")
    extract_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    # On macOS/Linux, make executable
    if system != "Windows" and exe_path.exists():
        os.chmod(exe_path, 0o755)

    print(f"CORE engine installed at: {exe_path}")
    return str(exe_path)


def _progress(block_num, block_size, total_size):
    downloaded = block_num * block_size
    percent = min(100, downloaded * 100 // total_size) if total_size > 0 else 0
    bar = "=" * (percent // 2) + "-" * (50 - percent // 2)
    sys.stdout.write(f"\r[{bar}] {percent}%")
    sys.stdout.flush()


if __name__ == "__main__":
    download_core()
