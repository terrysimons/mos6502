#!/usr/bin/env python3
"""Generate test cartridges for all C64 cartridge hardware types.

This is a thin driver script that uses cartridge classes to generate test
fixtures. Each cartridge class implements get_cartridge_variants() and
create_test_cartridge() methods.

Usage:
    python scripts/create_test_carts.py

Creates:
    tests/fixtures/c64/cartridge_types/  - All test cartridges (CRT and BIN formats)
    systems/c64/cartridges/error_cartridges/  - Error display cartridges for unsupported types
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "systems"))

from c64 import C64
from c64.cartridges import (
    CARTRIDGE_TYPES,
    UNIMPLEMENTED_CARTRIDGE_TYPES,
    create_error_cartridge_rom,
)


def get_safe_name(hw_type: int) -> str:
    """Get safe filename from hardware type using C64.CRT_HARDWARE_TYPES.

    This must match test_cartridge_types.py's _get_crt_path logic exactly.
    """
    type_name = C64.CRT_HARDWARE_TYPES.get(hw_type, f"unknown_{hw_type}")
    return (
        type_name.lower()
        .replace(" ", "_")
        .replace(",", "")
        .replace("/", "_")
        .replace("(", "")
        .replace(")", "")
        .replace(".", "")
    )


def get_cart_filename(hw_type: int, variant_desc: str) -> str:
    """Generate filename for a test cartridge.

    Format: test_cart_type_XX_{type_name}[_{variant}].crt
    """
    safe_name = get_safe_name(hw_type)
    base = f"test_cart_type_{hw_type:02d}_{safe_name}"
    if variant_desc:
        return f"{base}_{variant_desc}"
    return base


def main():
    """Generate all test cartridges."""
    fixtures_dir = project_root / "tests" / "fixtures" / "c64"
    cartridge_types_dir = fixtures_dir / "cartridge_types"
    cartridge_types_dir.mkdir(parents=True, exist_ok=True)

    print("Generating test cartridges...")
    print(f"  Output directory: {cartridge_types_dir}")
    print()

    total_carts = 0
    total_variants = 0

    # Process implemented cartridge types
    print("=== Implemented Types ===")
    for cart_type, cart_class in sorted(CARTRIDGE_TYPES.items(), key=lambda x: x[0].value):
        hw_type = cart_type.value
        type_name = C64.CRT_HARDWARE_TYPES.get(hw_type, cart_type.name)

        variants = cart_class.get_cartridge_variants()
        if not variants:
            print(f"  Type {hw_type:2d} ({type_name}): No variants, skipping")
            continue

        print(f"  Type {hw_type:2d} ({type_name}): {len(variants)} variant(s)")

        for variant in variants:
            image = cart_class.create_test_cartridge(variant)
            filename = get_cart_filename(hw_type, variant.description)

            crt_path = cartridge_types_dir / f"{filename}.crt"
            crt_path.write_bytes(image.to_crt())

            if hw_type == 0:
                bin_path = cartridge_types_dir / f"{filename}.bin"
                bin_path.write_bytes(image.to_bin())
                print(f"    - {filename}.crt + .bin")
            else:
                print(f"    - {filename}.crt")

            total_variants += 1
        total_carts += 1

    print()

    # Process unimplemented cartridge types
    print("=== Unimplemented Types ===")
    for hw_type, cart_class in sorted(UNIMPLEMENTED_CARTRIDGE_TYPES.items()):
        type_name = C64.CRT_HARDWARE_TYPES.get(hw_type, f"Type {hw_type}")
        variants = cart_class.get_cartridge_variants()

        print(f"  Type {hw_type:2d} ({type_name})")

        for variant in variants:
            image = cart_class.create_test_cartridge(variant)
            filename = get_cart_filename(hw_type, variant.description)

            crt_path = cartridge_types_dir / f"{filename}.crt"
            crt_path.write_bytes(image.to_crt())
            print(f"    - {filename}.crt")

            total_variants += 1
        total_carts += 1

    print()

    # Generate error cartridges for all unsupported hardware types
    print("=== Error Cartridges ===")
    error_cart_dir = project_root / "systems" / "c64" / "cartridges" / "error_cartridges"
    error_cart_dir.mkdir(parents=True, exist_ok=True)

    error_cart_count = 0
    # Generate error carts for types 1-85 (type 0 is always supported)
    for hw_type in range(1, 86):
        type_name = C64.CRT_HARDWARE_TYPES.get(hw_type, f"unknown_{hw_type}")
        safe_name = get_safe_name(hw_type)

        # Generate error display lines
        error_lines = [
            "{RED}UNSUPPORTED CARTRIDGE",
            "",
            f"{{WHITE}}TYPE: {{YELLOW}}{hw_type}",
            f"{{WHITE}}NAME: {{CYAN}}{type_name.upper()[:20]}",
            "",
            "{WHITE}THIS CARTRIDGE TYPE IS",
            "{WHITE}NOT YET IMPLEMENTED.",
        ]

        rom_data = create_error_cartridge_rom(error_lines, border_color=0x02)
        filename = f"error_cart_type_{hw_type:02d}_{safe_name}.bin"
        error_path = error_cart_dir / filename
        error_path.write_bytes(rom_data)
        error_cart_count += 1

    print(f"  Generated {error_cart_count} error cartridges")
    print(f"  Output directory: {error_cart_dir}")

    print()
    print(f"=== Summary ===")
    print(f"  Total cartridge types: {total_carts}")
    print(f"  Total variant files: {total_variants}")
    print(f"  Total error cartridges: {error_cart_count}")
    print(f"  Test cart directory: {cartridge_types_dir}")
    print(f"  Error cart directory: {error_cart_dir}")


if __name__ == "__main__":
    main()
