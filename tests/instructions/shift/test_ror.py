#!/usr/bin/env python3
import contextlib
import logging

import mos6502
from mos6502 import CPU, exceptions, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_ROR_ACCUMULATOR_0x6A(cpu: CPU) -> None:  # noqa: N802
    """Test ROR Accumulator mode with carry clear."""
    # given:

    cpu.A = 0x42  # 0100 0010
    cpu.flags[flags.C] = 0

    # ROR A
    cpu.ram[0xFFFC] = instructions.ROR_ACCUMULATOR_0x6A

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x21  # 0010 0001 (shifted right, carry 0 in bit 7)
    assert cpu.flags[flags.C] == 0  # Bit 0 was 0
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 0  # Bit 7 clear
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ROR_ACCUMULATOR_0x6A_with_carry(cpu: CPU) -> None:  # noqa: N802
    """Test ROR with carry set."""
    # given:

    cpu.A = 0x42  # 0100 0010
    cpu.flags[flags.C] = 1  # Carry set

    # ROR A
    cpu.ram[0xFFFC] = instructions.ROR_ACCUMULATOR_0x6A

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0xA1  # 1010 0001 (shifted right, carry 1 in bit 7)
    assert cpu.flags[flags.C] == 0  # Bit 0 was 0
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Bit 7 now set from carry
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ROR_ACCUMULATOR_0x6A_carry_out(cpu: CPU) -> None:  # noqa: N802
    """Test ROR with bit 0 set (carry out)."""
    # given:

    cpu.A = 0x81  # 1000 0001 (bit 0 set)
    cpu.flags[flags.C] = 0

    # ROR A
    cpu.ram[0xFFFC] = instructions.ROR_ACCUMULATOR_0x6A

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x40  # 0100 0000
    assert cpu.flags[flags.C] == 1  # Bit 0 was 1
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 0  # Bit 7 clear
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ROR_ZEROPAGE_0x66(cpu: CPU) -> None:  # noqa: N802
    """Test ROR Zero Page mode."""
    # given:

    cpu.ram[0x0042] = 0xAA  # 1010 1010
    cpu.flags[flags.C] = 1

    # ROR $42
    cpu.ram[0xFFFC] = instructions.ROR_ZEROPAGE_0x66
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=5)

    # then:
    assert cpu.ram[0x0042] == 0xD5  # 1101 0101 (shifted right with carry 1)
    assert cpu.flags[flags.C] == 0  # Bit 0 was 0
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Bit 7 set from carry
    assert cpu.cycles_executed == 5


def test_cpu_instruction_ROR_ZEROPAGE_X_0x76(cpu: CPU) -> None:  # noqa: N802
    """Test ROR Zero Page,X mode."""
    # given:

    cpu.X = 0x05
    cpu.ram[0x0047] = 0x01  # 0x42 + 0x05
    cpu.flags[flags.C] = 0

    # ROR $42,X
    cpu.ram[0xFFFC] = instructions.ROR_ZEROPAGE_X_0x76
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=6)

    # then:
    assert cpu.ram[0x0047] == 0x00  # 0000 0000 (bit 0 rotated out)
    assert cpu.flags[flags.C] == 1  # Bit 0 was 1
    assert cpu.flags[flags.Z] == 1  # Zero
    assert cpu.flags[flags.N] == 0
    assert cpu.cycles_executed == 6


def test_cpu_instruction_ROR_ABSOLUTE_0x6E(cpu: CPU) -> None:  # noqa: N802
    """Test ROR Absolute mode."""
    # given:

    cpu.ram[0x1234] = 0xFF  # 1111 1111
    cpu.flags[flags.C] = 0

    # ROR $1234
    cpu.ram[0xFFFC] = instructions.ROR_ABSOLUTE_0x6E
    cpu.ram[0xFFFD] = 0x34
    cpu.ram[0xFFFE] = 0x12

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=6)

    # then:
    assert cpu.ram[0x1234] == 0x7F  # 0111 1111
    assert cpu.flags[flags.C] == 1  # Bit 0 was 1
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 0  # Bit 7 clear
    assert cpu.cycles_executed == 6


def test_cpu_instruction_ROR_ABSOLUTE_X_0x7E(cpu: CPU) -> None:  # noqa: N802
    """Test ROR Absolute,X mode."""
    # given:

    cpu.X = 0x10
    cpu.ram[0x1244] = 0x80  # 0x1234 + 0x10
    cpu.flags[flags.C] = 1

    # ROR $1234,X
    cpu.ram[0xFFFC] = instructions.ROR_ABSOLUTE_X_0x7E
    cpu.ram[0xFFFD] = 0x34
    cpu.ram[0xFFFE] = 0x12

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=7)

    # then:
    assert cpu.ram[0x1244] == 0xC0  # 1100 0000 (shifted right with carry 1)
    assert cpu.flags[flags.C] == 0  # Bit 0 was 0
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Bit 7 set from carry
    assert cpu.cycles_executed == 7
