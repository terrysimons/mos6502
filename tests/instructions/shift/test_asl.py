#!/usr/bin/env python3
import contextlib
import logging

import mos6502
from mos6502 import CPU, exceptions, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_ASL_ACCUMULATOR_0x0A(cpu: CPU) -> None:  # noqa: N802
    """Test ASL Accumulator mode."""
    # given:

    cpu.A = 0x42  # 0100 0010

    # ASL A
    cpu.ram[0xFFFC] = instructions.ASL_ACCUMULATOR_0x0A

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x84  # 1000 0100 (shifted left)
    assert cpu.flags[flags.C] == 0  # Bit 7 was 0
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Bit 7 now set
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ASL_ACCUMULATOR_0x0A_carry(cpu: CPU) -> None:  # noqa: N802
    """Test ASL with carry flag set."""
    # given:

    cpu.A = 0x81  # 1000 0001 (bit 7 set)

    # ASL A
    cpu.ram[0xFFFC] = instructions.ASL_ACCUMULATOR_0x0A

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x02  # 0000 0010
    assert cpu.flags[flags.C] == 1  # Bit 7 was 1
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 0  # Bit 7 now clear
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ASL_ACCUMULATOR_0x0A_zero(cpu: CPU) -> None:  # noqa: N802
    """Test ASL resulting in zero."""
    # given:

    cpu.A = 0x80  # 1000 0000

    # ASL A
    cpu.ram[0xFFFC] = instructions.ASL_ACCUMULATOR_0x0A

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x00  # 0000 0000
    assert cpu.flags[flags.C] == 1  # Bit 7 was 1
    assert cpu.flags[flags.Z] == 1  # Zero
    assert cpu.flags[flags.N] == 0  # Bit 7 clear
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ASL_ZEROPAGE_0x06(cpu: CPU) -> None:  # noqa: N802
    """Test ASL Zero Page mode."""
    # given:

    cpu.ram[0x0042] = 0x55  # 0101 0101

    # ASL $42
    cpu.ram[0xFFFC] = instructions.ASL_ZEROPAGE_0x06
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=5)

    # then:
    assert cpu.ram[0x0042] == 0xAA  # 1010 1010
    assert cpu.flags[flags.C] == 0  # Bit 7 was 0
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Bit 7 now set
    assert cpu.cycles_executed == 5


def test_cpu_instruction_ASL_ZEROPAGE_X_0x16(cpu: CPU) -> None:  # noqa: N802
    """Test ASL Zero Page,X mode."""
    # given:

    cpu.X = 0x05
    cpu.ram[0x0047] = 0x01  # 0x42 + 0x05

    # ASL $42,X
    cpu.ram[0xFFFC] = instructions.ASL_ZEROPAGE_X_0x16
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=6)

    # then:
    assert cpu.ram[0x0047] == 0x02
    assert cpu.flags[flags.C] == 0
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 0
    assert cpu.cycles_executed == 6


def test_cpu_instruction_ASL_ABSOLUTE_0x0E(cpu: CPU) -> None:  # noqa: N802
    """Test ASL Absolute mode."""
    # given:

    cpu.ram[0x1234] = 0x40  # 0100 0000

    # ASL $1234
    cpu.ram[0xFFFC] = instructions.ASL_ABSOLUTE_0x0E
    cpu.ram[0xFFFD] = 0x34
    cpu.ram[0xFFFE] = 0x12

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=6)

    # then:
    assert cpu.ram[0x1234] == 0x80  # 1000 0000
    assert cpu.flags[flags.C] == 0  # Bit 7 was 0
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Bit 7 now set
    assert cpu.cycles_executed == 6


def test_cpu_instruction_ASL_ABSOLUTE_X_0x1E(cpu: CPU) -> None:  # noqa: N802
    """Test ASL Absolute,X mode."""
    # given:

    cpu.X = 0x10
    cpu.ram[0x1244] = 0xFF  # 0x1234 + 0x10

    # ASL $1234,X
    cpu.ram[0xFFFC] = instructions.ASL_ABSOLUTE_X_0x1E
    cpu.ram[0xFFFD] = 0x34
    cpu.ram[0xFFFE] = 0x12

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=7)

    # then:
    assert cpu.ram[0x1244] == 0xFE  # 1111 1110
    assert cpu.flags[flags.C] == 1  # Bit 7 was 1
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Bit 7 set
    assert cpu.cycles_executed == 7
