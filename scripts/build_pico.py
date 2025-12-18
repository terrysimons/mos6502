#!/usr/bin/env python3
"""Build MicroPython-compatible .mpy files for Pico deployment.

This builds .mpy bytecode files that can be deployed to the Pico via mpremote.
For frozen firmware builds (better performance), use build_firmware.py instead.

Usage:
    python scripts/build_pico.py
    poetry run build-pico
"""

import shutil
import subprocess
import sys
from pathlib import Path

from pico_config import (
    ROOT,
    MOS6502_SRC,
    C64_SRC,
    DIST_PICO,
    MPY_OPT,
    is_excluded,
)


def find_mpy_cross():
    """Find mpy-cross executable."""
    # Check if in PATH
    if shutil.which("mpy-cross"):
        return "mpy-cross"

    # Check common locations
    for path in [
        Path.home() / ".local" / "bin" / "mpy-cross",
        Path("/usr/local/bin/mpy-cross"),
    ]:
        if path.exists():
            return str(path)

    print("ERROR: mpy-cross not found. Install with: pip install mpy-cross")
    sys.exit(1)


def compile_file(src: Path, dst: Path, mpy_cross: str) -> bool:
    """Compile a .py file to .mpy."""
    dst.parent.mkdir(parents=True, exist_ok=True)

    # Output file is .mpy
    mpy_file = dst.with_suffix(".mpy")

    try:
        result = subprocess.run(
            [mpy_cross, MPY_OPT, "-o", str(mpy_file), str(src)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"  ERROR: {src.name}: {result.stderr.strip()}")
            return False
        return True
    except Exception as e:
        print(f"  ERROR: {src.name}: {e}")
        return False


def compile_directory(src_dir: Path, dst_dir: Path, mpy_cross: str, name: str) -> int:
    """Compile all .py files in a directory tree."""
    print(f"\nCompiling {name}...")

    count = 0
    errors = 0
    skipped = 0

    for py_file in src_dir.rglob("*.py"):
        # Skip __pycache__ and test files
        if "__pycache__" in str(py_file) or "/tests/" in str(py_file):
            continue

        # Calculate relative path and destination
        rel_path = py_file.relative_to(src_dir)

        # Skip excluded files
        if is_excluded(rel_path):
            skipped += 1
            continue

        dst_file = dst_dir / rel_path

        if compile_file(py_file, dst_file, mpy_cross):
            count += 1
        else:
            errors += 1

    status = f"  Compiled {count} files"
    if skipped:
        status += f", skipped {skipped}"
    if errors:
        status += f" ({errors} errors)"
    print(status)
    return errors


def clean():
    """Remove existing dist/pico directory."""
    if DIST_PICO.exists():
        print(f"Cleaning {DIST_PICO}...")
        shutil.rmtree(DIST_PICO)


def clean_source_mpy():
    """Remove .mpy files from source directories.

    mpy-cross sometimes leaves .mpy files in the source directories.
    This cleans them up to avoid confusion.
    """
    removed = 0
    for src_dir in [MOS6502_SRC, C64_SRC]:
        for mpy_file in src_dir.rglob("*.mpy"):
            if "__pycache__" not in str(mpy_file):
                mpy_file.unlink()
                removed += 1
    if removed:
        print(f"Cleaned up {removed} .mpy files from source directories")


def main():
    print("=" * 60)
    print("Building MicroPython distribution for Pico")
    print("=" * 60)

    # Find mpy-cross
    mpy_cross = find_mpy_cross()
    print(f"Using: {mpy_cross}")

    # Check version
    result = subprocess.run([mpy_cross, "--version"], capture_output=True, text=True)
    print(f"Version: {result.stdout.strip()}")

    # Clean and create output directory
    clean()
    DIST_PICO.mkdir(parents=True, exist_ok=True)

    # Compile mos6502
    errors = compile_directory(
        MOS6502_SRC,
        DIST_PICO / "mos6502",
        mpy_cross,
        "mos6502"
    )

    # Compile c64
    errors += compile_directory(
        C64_SRC,
        DIST_PICO / "c64",
        mpy_cross,
        "c64"
    )

    # Clean up .mpy files from source directories
    clean_source_mpy()

    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"Build completed with {errors} errors")
        print(f"Output: {DIST_PICO}")
        sys.exit(1)
    else:
        print("Build successful!")
        print(f"Output: {DIST_PICO}")

        # Count files
        mpy_count = len(list(DIST_PICO.rglob("*.mpy")))
        print(f"Total: {mpy_count} .mpy files")

    print("=" * 60)


if __name__ == "__main__":
    main()
