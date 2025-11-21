#!/usr/bin/env python3
"""Test the exact C64 RAM test sequence that's failing."""

import contextlib
import pytest
from mos6502 import CPU, errors, flags, instructions


def test_c64_ram_test_loop_exit(cpu: CPU) -> None:
    """Test the exact sequence from C64 ROM at $FD83-$FD86.

    This is the sequence that should exit after Y wraps:
    $FD83: INY        ; Y: $FF -> $00, Z=1
    $FD84: BNE $E8    ; Should NOT branch (Z=1)
    $FD86: BEQ $E4    ; Should branch to $FD6C (Z=1)
    """
    # Set up: Y=$FF (about to wrap)
    cpu.Y = 0xFF
    cpu.PC = 0x0200

    # Write the exact sequence
    cpu.ram[0x0200] = instructions.INY_IMPLIED_0xC8     # INY
    cpu.ram[0x0201] = instructions.BNE_RELATIVE_0xD0    # BNE
    cpu.ram[0x0202] = 0xE8  # offset -24 (but shouldn't branch)
    cpu.ram[0x0203] = instructions.BEQ_RELATIVE_0xF0    # BEQ
    cpu.ram[0x0204] = 0xE4  # offset -28 (should branch)

    # Execute INY
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # After INY: Y should be 0, Z should be 1
    assert cpu.Y == 0, f"After INY: Y should be $00, got ${cpu.Y:02X}"
    assert cpu.flags[flags.Z] == 1, f"After INY: Z flag should be 1, got {cpu.flags[flags.Z]}"
    assert cpu.PC == 0x0201, f"After INY: PC should be $0201, got ${cpu.PC:04X}"

    # Execute BNE (should NOT branch because Z=1)
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # After BNE: Should fall through (not branch)
    assert cpu.PC == 0x0203, f"After BNE: PC should be $0203 (didn't branch), got ${cpu.PC:04X}"
    assert cpu.flags[flags.Z] == 1, f"After BNE: Z flag should still be 1, got {cpu.flags[flags.Z]}"

    # Execute BEQ (SHOULD branch because Z=1)
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=3)

    # After BEQ: Should have branched
    expected_pc = (0x0205 - 28) & 0xFFFF  # 0x0205 + (-28) = 0x01E9
    assert cpu.PC == expected_pc, f"After BEQ: PC should be ${expected_pc:04X} (branched), got ${cpu.PC:04X}"


def test_c64_ram_test_loop_continue(cpu: CPU) -> None:
    """Test the same sequence when Y doesn't wrap (should loop back)."""
    # Set up: Y=$42 (not wrapping)
    cpu.Y = 0x42
    cpu.PC = 0x0200

    # Write the exact sequence
    cpu.ram[0x0200] = instructions.INY_IMPLIED_0xC8     # INY
    cpu.ram[0x0201] = instructions.BNE_RELATIVE_0xD0    # BNE
    cpu.ram[0x0202] = 0xE8  # offset -24 (should branch)
    cpu.ram[0x0203] = instructions.BEQ_RELATIVE_0xF0    # BEQ
    cpu.ram[0x0204] = 0xE4  # offset -28

    # Execute INY
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # After INY: Y should be $43, Z should be 0
    assert cpu.Y == 0x43, f"After INY: Y should be $43, got ${cpu.Y:02X}"
    assert cpu.flags[flags.Z] == 0, f"After INY: Z flag should be 0, got {cpu.flags[flags.Z]}"

    # Execute BNE (SHOULD branch because Z=0)
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=3)

    # After BNE: Should have branched
    expected_pc = (0x0203 - 24) & 0xFFFF  # 0x0203 + (-24) = 0x01EB
    assert cpu.PC == expected_pc, f"After BNE: PC should be ${expected_pc:04X} (branched), got ${cpu.PC:04X}"
