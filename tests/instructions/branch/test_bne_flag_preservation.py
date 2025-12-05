#!/usr/bin/env python3
"""Test that BNE instruction preserves all flags correctly.

This test specifically checks for a bug where BNE was corrupting the flags register,
changing 0x50 to 0xD0 (setting bit 7 incorrectly).
"""

import contextlib

from mos6502 import CPU, errors, flags, instructions
from mos6502.memory import Byte


def test_cpu_instruction_BNE_preserves_flags_when_branch_taken(cpu: CPU) -> None:  # noqa: N802
    """Test that BNE preserves all flags when branch is taken (Z=0).

    This reproduces the bug found in BASIC where:
    - CPY sets flags to 0x50 (N=0, V=1, Z=1, C=0)
    - BNE incorrectly changes flags to 0xD0 (N=1, V=1, Z=0, C=0)

    BNE should not modify ANY flags.
    """
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    # Set flags to 0x50: N=0, V=1, unused=1, B=0, D=1, I=0, Z=0, C=0
    # (In 6502 bit order: NV-BDIZC = 0101 0000)
    cpu._flags = Byte(0x50)

    # Clear Z flag so branch will be taken
    cpu.flags[flags.Z] = 0

    # Store initial flags value
    initial_flags = cpu._flags.value

    # BNE with offset +10
    cpu.ram[pc] = instructions.BNE_RELATIVE_0xD0
    cpu.ram[pc + 1] = 0x0A

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=3

    # then:
    # BNE should NOT modify any flags
    final_flags = cpu._flags.value
    assert final_flags == initial_flags, \
        f"BNE corrupted flags: 0x{initial_flags:02X} -> 0x{final_flags:02X}"


def test_cpu_instruction_BNE_preserves_flags_when_branch_not_taken(cpu: CPU) -> None:  # noqa: N802
    """Test that BNE preserves all flags when branch is not taken (Z=1)."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    # Set flags to 0x50
    cpu._flags = Byte(0x50)

    # Set Z flag so branch will NOT be taken
    cpu.flags[flags.Z] = 1

    # Store initial flags value
    initial_flags = cpu._flags.value

    # BNE with offset +10
    cpu.ram[pc] = instructions.BNE_RELATIVE_0xD0
    cpu.ram[pc + 1] = 0x0A

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    # BNE should NOT modify any flags
    final_flags = cpu._flags.value
    assert final_flags == initial_flags, \
        f"BNE corrupted flags: 0x{initial_flags:02X} -> 0x{final_flags:02X}"


def test_cpu_instruction_BNE_preserves_all_flag_combinations(cpu: CPU) -> None:  # noqa: N802
    """Test BNE with multiple possible flag combinations."""
    for flags_value in [0x00, 0x50, 0xD0, 0xFF]:
        # given:
        cpu._flags = Byte(flags_value)

        # Clear Z so branch is taken
        cpu.flags[flags.Z] = 0

        initial_flags = cpu._flags.value

        # BNE with offset +5
        cpu.PC = 0x1000
        cpu.ram[0x1000] = instructions.BNE_RELATIVE_0xD0
        cpu.ram[0x1001] = 0x05

        # when:
        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)  # cycles=3

        # then:
        final_flags = cpu._flags.value
        assert final_flags == initial_flags, \
            f"BNE corrupted flags with initial value 0x{flags_value:02X}: " \
            f"0x{initial_flags:02X} -> 0x{final_flags:02X}"


def test_cpu_instruction_BNE_page_boundary_crossing_preserves_flags(cpu: CPU) -> None:  # noqa: N802
    """Test that crossing page boundary during BNE doesn't corrupt flags."""
    # given:
    cpu._flags = Byte(0x50)

    # Clear Z so branch is taken
    cpu.flags[flags.Z] = 0

    initial_flags = cpu._flags.value

    # Set up BNE that crosses page boundary
    # PC=0x02FD, after fetch PC=0x02FF, branch +5 -> 0x0304 (crosses boundary)
    cpu.PC = 0x02FD
    cpu.ram[0x02FD] = instructions.BNE_RELATIVE_0xD0
    cpu.ram[0x02FE] = 0x05

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=4  # +1 for page crossing

    # then:
    final_flags = cpu._flags.value
    assert final_flags == initial_flags, \
        f"BNE with page boundary crossing corrupted flags: " \
        f"0x{initial_flags:02X} -> 0x{final_flags:02X}"


def test_cpu_instruction_BNE_backward_branch_preserves_flags(cpu: CPU) -> None:  # noqa: N802
    """Test that backward branches preserve flags."""
    # given:
    cpu._flags = Byte(0xD0)  # Test with the problematic 0xD0 value

    # Clear Z so branch is taken
    cpu.flags[flags.Z] = 0

    initial_flags = cpu._flags.value

    # Set up BNE with backward branch
    cpu.PC = 0x1010
    cpu.ram[0x1010] = instructions.BNE_RELATIVE_0xD0
    cpu.ram[0x1011] = 0xF0  # offset -16 (0xF0 = -16 in signed byte)

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=3

    # then:
    final_flags = cpu._flags.value
    assert final_flags == initial_flags, \
        f"BNE with backward branch corrupted flags: " \
        f"0x{initial_flags:02X} -> 0x{final_flags:02X}"
