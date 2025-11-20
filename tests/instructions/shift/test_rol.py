#!/usr/bin/env python3
import contextlib
import logging

import mos6502
from mos6502 import exceptions, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_ROL_ACCUMULATOR_0x2A() -> None:  # noqa: N802
    """Test ROL Accumulator mode with carry clear."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0x42  # 0100 0010
    cpu.flags[flags.C] = 0

    # ROL A
    cpu.ram[0xFFFC] = instructions.ROL_ACCUMULATOR_0x2A

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x84  # 1000 0100 (shifted left, carry 0 in bit 0)
    assert cpu.flags[flags.C] == 0  # Bit 7 was 0
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Bit 7 now set
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ROL_ACCUMULATOR_0x2A_with_carry() -> None:  # noqa: N802
    """Test ROL with carry set."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0x42  # 0100 0010
    cpu.flags[flags.C] = 1  # Carry set

    # ROL A
    cpu.ram[0xFFFC] = instructions.ROL_ACCUMULATOR_0x2A

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x85  # 1000 0101 (shifted left, carry 1 in bit 0)
    assert cpu.flags[flags.C] == 0  # Bit 7 was 0
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Bit 7 now set
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ROL_ACCUMULATOR_0x2A_carry_out() -> None:  # noqa: N802
    """Test ROL with bit 7 set (carry out)."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0x81  # 1000 0001 (bit 7 set)
    cpu.flags[flags.C] = 0

    # ROL A
    cpu.ram[0xFFFC] = instructions.ROL_ACCUMULATOR_0x2A

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x02  # 0000 0010
    assert cpu.flags[flags.C] == 1  # Bit 7 was 1
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 0  # Bit 7 clear
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ROL_ZEROPAGE_0x26() -> None:  # noqa: N802
    """Test ROL Zero Page mode."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.ram[0x0042] = 0x55  # 0101 0101
    cpu.flags[flags.C] = 1

    # ROL $42
    cpu.ram[0xFFFC] = instructions.ROL_ZEROPAGE_0x26
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=5)

    # then:
    assert cpu.ram[0x0042] == 0xAB  # 1010 1011 (shifted left with carry 1)
    assert cpu.flags[flags.C] == 0  # Bit 7 was 0
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Bit 7 now set
    assert cpu.cycles_executed == 5


def test_cpu_instruction_ROL_ZEROPAGE_X_0x36() -> None:  # noqa: N802
    """Test ROL Zero Page,X mode."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.X = 0x05
    cpu.ram[0x0047] = 0x80  # 0x42 + 0x05
    cpu.flags[flags.C] = 0

    # ROL $42,X
    cpu.ram[0xFFFC] = instructions.ROL_ZEROPAGE_X_0x36
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=6)

    # then:
    assert cpu.ram[0x0047] == 0x00  # 0000 0000 (bit 7 rotated out)
    assert cpu.flags[flags.C] == 1  # Bit 7 was 1
    assert cpu.flags[flags.Z] == 1  # Zero
    assert cpu.flags[flags.N] == 0
    assert cpu.cycles_executed == 6


def test_cpu_instruction_ROL_ABSOLUTE_0x2E() -> None:  # noqa: N802
    """Test ROL Absolute mode."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.ram[0x1234] = 0xFF  # 1111 1111
    cpu.flags[flags.C] = 0

    # ROL $1234
    cpu.ram[0xFFFC] = instructions.ROL_ABSOLUTE_0x2E
    cpu.ram[0xFFFD] = 0x34
    cpu.ram[0xFFFE] = 0x12

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=6)

    # then:
    assert cpu.ram[0x1234] == 0xFE  # 1111 1110
    assert cpu.flags[flags.C] == 1  # Bit 7 was 1
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Bit 7 set
    assert cpu.cycles_executed == 6


def test_cpu_instruction_ROL_ABSOLUTE_X_0x3E() -> None:  # noqa: N802
    """Test ROL Absolute,X mode."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.X = 0x10
    cpu.ram[0x1244] = 0x01  # 0x1234 + 0x10
    cpu.flags[flags.C] = 1

    # ROL $1234,X
    cpu.ram[0xFFFC] = instructions.ROL_ABSOLUTE_X_0x3E
    cpu.ram[0xFFFD] = 0x34
    cpu.ram[0xFFFE] = 0x12

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=7)

    # then:
    assert cpu.ram[0x1244] == 0x03  # 0000 0011 (shifted left with carry 1)
    assert cpu.flags[flags.C] == 0  # Bit 7 was 0
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 0
    assert cpu.cycles_executed == 7
