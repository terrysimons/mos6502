#!/usr/bin/env python3
"""Test that all instructions are properly registered in both OPCODE_LOOKUP and InstructionSet.map."""

import pytest
from mos6502 import instructions


def test_all_opcodes_in_lookup_are_in_map():
    """Verify every opcode in OPCODE_LOOKUP is also in InstructionSet.map."""
    missing_from_map = []

    for opcode, opcode_obj in instructions.OPCODE_LOOKUP.items():
        if opcode not in instructions.InstructionSet.map:
            missing_from_map.append((opcode, opcode_obj))

    if missing_from_map:
        error_msg = "The following opcodes are in OPCODE_LOOKUP but missing from InstructionSet.map:\n"
        for opcode, obj in missing_from_map:
            func_name = getattr(obj, "function", "unknown")
            error_msg += f"  0x{opcode:02X}: {func_name}\n"
        error_msg += "\nThis means instruction metadata (bytes, cycles, assembler) is missing."
        error_msg += "\nFix: Ensure the instruction's register_*_instructions() function is called in instructions/__init__.py"
        pytest.fail(error_msg)


def test_all_opcodes_in_map_are_in_lookup():
    """Verify every opcode in InstructionSet.map is also in OPCODE_LOOKUP."""
    missing_from_lookup = []

    for opcode in instructions.InstructionSet.map:
        if opcode not in instructions.OPCODE_LOOKUP:
            missing_from_lookup.append(opcode)

    if missing_from_lookup:
        error_msg = "The following opcodes are in InstructionSet.map but missing from OPCODE_LOOKUP:\n"
        for opcode in missing_from_lookup:
            entry = instructions.InstructionSet.map[opcode]
            error_msg += f"  0x{opcode:02X}: {entry.get('assembler', 'unknown')}\n"
        error_msg += "\nThis means the instruction cannot be executed (no variant handler)."
        pytest.fail(error_msg)


def test_opcode_metadata_consistency():
    """Verify opcodes have consistent metadata between OPCODE_LOOKUP and InstructionSet.map."""
    inconsistent = []

    for opcode in instructions.OPCODE_LOOKUP:
        if opcode not in instructions.InstructionSet.map:
            continue  # Already caught by test_all_opcodes_in_lookup_are_in_map

        opcode_obj = instructions.OPCODE_LOOKUP[opcode]
        map_entry = instructions.InstructionSet.map[opcode]

        # Verify opcode values match
        if hasattr(opcode_obj, "value") and opcode_obj.value != opcode:
            inconsistent.append((opcode, "opcode value mismatch"))

        # Verify the map entry has required fields
        required_fields = ["bytes", "cycles", "assembler"]
        for field in required_fields:
            if field not in map_entry:
                inconsistent.append((opcode, f"missing '{field}' in map entry"))

    if inconsistent:
        error_msg = "The following opcodes have inconsistent metadata:\n"
        for opcode, issue in inconsistent:
            error_msg += f"  0x{opcode:02X}: {issue}\n"
        pytest.fail(error_msg)


def test_all_256_opcodes_accounted_for():
    """Verify all 256 possible opcodes (0x00-0xFF) are either registered or documented as unimplemented."""
    registered = set(instructions.OPCODE_LOOKUP.keys())

    # Count how many opcodes are registered
    registered_count = len(registered)

    # We expect most opcodes to be registered (legal + illegal instructions)
    # The 6502 has 151 legal opcodes and many stable illegal opcodes
    # Let's require at least 200 opcodes to be registered
    assert registered_count >= 200, (
        f"Only {registered_count} opcodes are registered. Expected at least 200.\n"
        f"Missing opcodes might indicate incomplete registration."
    )

    # Find unregistered opcodes
    all_opcodes = set(range(256))
    unregistered = all_opcodes - registered

    # It's OK to have some unregistered (unstable illegal opcodes)
    # But we should document if there are too many
    if len(unregistered) > 50:
        pytest.fail(
            f"Too many unregistered opcodes: {len(unregistered)}/256\n"
            f"Unregistered: {sorted(unregistered)}"
        )


def test_critical_instructions_registered():
    """Verify critical instructions used in tests and real programs are registered."""
    # These are commonly used instructions that should definitely be registered
    critical_opcodes = {
        # Branch instructions (the bug we just fixed)
        0xD0: "BNE",
        0xF0: "BEQ",
        0x10: "BPL",
        0x30: "BMI",
        0x90: "BCC",
        0xB0: "BCS",
        0x50: "BVC",
        0x70: "BVS",

        # Load/Store
        0xA9: "LDA immediate",
        0xA2: "LDX immediate",
        0xA0: "LDY immediate",
        0x85: "STA zeropage",
        0x86: "STX zeropage",
        0x84: "STY zeropage",

        # Arithmetic
        0xC8: "INY",
        0xE8: "INX",
        0xCA: "DEX",
        0x88: "DEY",

        # Transfer
        0xAA: "TAX",
        0xA8: "TAY",
        0x8A: "TXA",
        0x98: "TYA",

        # Flags
        0x18: "CLC",
        0x38: "SEC",
        0x78: "SEI",
        0x58: "CLI",

        # Stack
        0x48: "PHA",
        0x68: "PLA",
        0x08: "PHP",
        0x28: "PLP",
    }

    missing = []
    for opcode, name in critical_opcodes.items():
        if opcode not in instructions.OPCODE_LOOKUP:
            missing.append((opcode, name, "not in OPCODE_LOOKUP"))
        elif opcode not in instructions.InstructionSet.map:
            missing.append((opcode, name, "not in InstructionSet.map"))

    if missing:
        error_msg = "Critical instructions are not properly registered:\n"
        for opcode, name, issue in missing:
            error_msg += f"  0x{opcode:02X} {name}: {issue}\n"
        pytest.fail(error_msg)
