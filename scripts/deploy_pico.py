#!/usr/bin/env python3
"""Deploy compiled .mpy files to a Pico via mpremote.

Usage:
    python scripts/deploy_pico.py
    python scripts/deploy_pico.py --port /dev/ttyUSB0
    python scripts/deploy_pico.py --with-roms --rom-dir ./roms
    poetry run deploy-pico
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Project root
ROOT = Path(__file__).parent.parent

# Distribution directory
DIST_PICO = ROOT / "dist" / "pico"

# Main script for Pico
PICO_MAIN = ROOT / "scripts" / "pico_main.py"

# Default ROM directory
DEFAULT_ROM_DIR = ROOT / "systems" / "roms"


def find_mpremote():
    """Check if mpremote is available."""
    import shutil
    if not shutil.which("mpremote"):
        print("ERROR: mpremote not found. Install with: pip install mpremote")
        sys.exit(1)
    return "mpremote"


def run_mpremote(*args, port=None):
    """Run mpremote command."""
    cmd = ["mpremote"]
    if port:
        cmd.extend(["connect", port])
    cmd.extend(args)

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr


def create_directories(port=None):
    """Create /lib directory structure on Pico."""
    print("Creating directories...")

    dirs = [
        ":/lib",
        ":/lib/mos6502",
        ":/lib/c64",
    ]

    # Find all subdirectories in dist/pico
    for subdir in DIST_PICO.rglob("*"):
        if subdir.is_dir():
            rel = subdir.relative_to(DIST_PICO)
            dirs.append(f":/lib/{rel}")

    for d in sorted(set(dirs)):
        run_mpremote("fs", "mkdir", d, port=port)
        print(f"  {d}")


def deploy_files(port=None):
    """Copy all .mpy files to Pico."""
    print("\nDeploying files...")

    count = 0
    errors = 0

    for mpy_file in sorted(DIST_PICO.rglob("*.mpy")):
        rel_path = mpy_file.relative_to(DIST_PICO)
        remote_path = f":/lib/{rel_path}"

        success, stdout, stderr = run_mpremote(
            "fs", "cp", str(mpy_file), remote_path, port=port
        )

        if success:
            print(f"  {rel_path}")
            count += 1
        else:
            print(f"  ERROR: {rel_path}: {stderr.strip()}")
            errors += 1

    return count, errors


def deploy_main(port=None):
    """Deploy main.py to Pico."""
    print("\nDeploying main.py...")

    if not PICO_MAIN.exists():
        print(f"  WARNING: {PICO_MAIN} not found, skipping main.py")
        return False

    success, stdout, stderr = run_mpremote(
        "fs", "cp", str(PICO_MAIN), ":/main.py", port=port
    )

    if success:
        print(f"  main.py deployed")
        return True
    else:
        print(f"  ERROR: Failed to deploy main.py: {stderr.strip()}")
        return False


def deploy_roms(rom_dir: Path, port=None):
    """Deploy ROM files to Pico.

    Args:
        rom_dir: Directory containing ROM files (basic, kernal, char)
        port: Serial port for mpremote
    """
    print("\nDeploying ROMs...")

    if not rom_dir.exists():
        print(f"  ERROR: ROM directory not found: {rom_dir}")
        return False

    # Create /roms directory
    run_mpremote("fs", "mkdir", ":/roms", port=port)
    print("  Created /roms directory")

    # Expected ROM files (try multiple names for each)
    rom_files = {
        "basic": ["basic", "basic.rom", "basic.901226-01.bin"],
        "kernal": ["kernal", "kernal.rom", "kernal.901227-03.bin"],
        "char": ["char", "char.rom", "characters.901225-01.bin", "chargen"],
    }

    deployed = 0
    for rom_type, names in rom_files.items():
        for name in names:
            rom_path = rom_dir / name
            if rom_path.exists():
                success, stdout, stderr = run_mpremote(
                    "fs", "cp", str(rom_path), f":/roms/{rom_type}", port=port
                )
                if success:
                    print(f"  {rom_type}: {name} -> /roms/{rom_type}")
                    deployed += 1
                    break
                else:
                    print(f"  ERROR: Failed to deploy {name}: {stderr.strip()}")
        else:
            print(f"  WARNING: No {rom_type} ROM found (tried: {', '.join(names)})")

    return deployed == len(rom_files)


def install_dependencies(port=None):
    """Install MicroPython dependencies via mip."""
    print("\nInstalling dependencies...")

    dependencies = [
        "contextlib",  # Required by mos6502.compat
    ]

    for dep in dependencies:
        print(f"  Installing {dep}...")
        success, stdout, stderr = run_mpremote("mip", "install", dep, port=port)
        if not success:
            print(f"    WARNING: Failed to install {dep}: {stderr.strip()}")
        else:
            print(f"    OK")


def main():
    parser = argparse.ArgumentParser(description="Deploy to Pico")
    parser.add_argument(
        "--port", "-p",
        help="Serial port (e.g., /dev/ttyUSB0, /dev/cu.usbmodem101)"
    )
    parser.add_argument(
        "--clean", "-c",
        action="store_true",
        help="Remove existing /lib before deploying"
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip installing MicroPython dependencies"
    )
    parser.add_argument(
        "--with-main",
        action="store_true",
        help="Deploy main.py (C64 emulator startup script)"
    )
    parser.add_argument(
        "--with-roms",
        action="store_true",
        help="Deploy ROM files (basic, kernal, char) from --rom-dir"
    )
    parser.add_argument(
        "--rom-dir",
        type=Path,
        default=DEFAULT_ROM_DIR,
        help=f"Directory containing ROM files (default: {DEFAULT_ROM_DIR})"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Deploying to Pico")
    print("=" * 60)

    # Check prerequisites
    if not DIST_PICO.exists():
        print(f"ERROR: {DIST_PICO} not found. Run build-pico first.")
        sys.exit(1)

    find_mpremote()

    # Clean if requested
    if args.clean:
        print("Cleaning /lib on Pico...")
        run_mpremote("fs", "rm", "-r", ":/lib", port=args.port)
        if args.with_roms:
            print("Cleaning /roms on Pico...")
            run_mpremote("fs", "rm", "-r", ":/roms", port=args.port)

    # Install dependencies (requires network on Pico, or will use mpremote's mip)
    if not args.skip_deps:
        install_dependencies(port=args.port)

    # Create directories
    create_directories(port=args.port)

    # Deploy files
    count, errors = deploy_files(port=args.port)

    # Deploy main.py if requested
    if args.with_main:
        deploy_main(port=args.port)

    # Deploy ROMs if requested
    if args.with_roms:
        deploy_roms(args.rom_dir, port=args.port)

    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"Deployed {count} files with {errors} errors")
        sys.exit(1)
    else:
        print(f"Successfully deployed {count} files to Pico")
        if args.with_main:
            print("  + main.py (emulator startup script)")
        if args.with_roms:
            print("  + ROMs in /roms/")
    print("=" * 60)


if __name__ == "__main__":
    main()
