#!/usr/bin/env python3
import contextlib
import logging

import mos6502
from mos6502 import exceptions, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_LSR_ACCUMULATOR_0x4A() -> None:  # noqa: N802
    """Test LSR Accumulator mode."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0x42  # 0100 0010

    # LSR A
    cpu.ram[0xFFFC] = instructions.LSR_ACCUMULATOR_0x4A

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x21  # 0010 0001 (shifted right)
    assert cpu.flags[flags.C] == 0  # Bit 0 was 0
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 0  # Always 0 for LSR
    assert cpu.cycles_executed == 2


def test_cpu_instruction_LSR_ACCUMULATOR_0x4A_carry() -> None:  # noqa: N802
    """Test LSR with carry flag set."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0x81  # 1000 0001 (bit 0 set)

    # LSR A
    cpu.ram[0xFFFC] = instructions.LSR_ACCUMULATOR_0x4A

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x40  # 0100 0000
    assert cpu.flags[flags.C] == 1  # Bit 0 was 1
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 0  # Always 0 for LSR
    assert cpu.cycles_executed == 2


def test_cpu_instruction_LSR_ACCUMULATOR_0x4A_zero() -> None:  # noqa: N802
    """Test LSR resulting in zero."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0x01  # 0000 0001

    # LSR A
    cpu.ram[0xFFFC] = instructions.LSR_ACCUMULATOR_0x4A

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x00  # 0000 0000
    assert cpu.flags[flags.C] == 1  # Bit 0 was 1
    assert cpu.flags[flags.Z] == 1  # Zero
    assert cpu.flags[flags.N] == 0  # Always 0 for LSR
    assert cpu.cycles_executed == 2


def test_cpu_instruction_LSR_ZEROPAGE_0x46() -> None:  # noqa: N802
    """Test LSR Zero Page mode."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.ram[0x0042] = 0xAA  # 1010 1010

    # LSR $42
    cpu.ram[0xFFFC] = instructions.LSR_ZEROPAGE_0x46
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=5)

    # then:
    assert cpu.ram[0x0042] == 0x55  # 0101 0101
    assert cpu.flags[flags.C] == 0  # Bit 0 was 0
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 0  # Always 0 for LSR
    assert cpu.cycles_executed == 5


def test_cpu_instruction_LSR_ZEROPAGE_X_0x56() -> None:  # noqa: N802
    """Test LSR Zero Page,X mode."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.X = 0x05
    cpu.ram[0x0047] = 0x02  # 0x42 + 0x05

    # LSR $42,X
    cpu.ram[0xFFFC] = instructions.LSR_ZEROPAGE_X_0x56
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=6)

    # then:
    assert cpu.ram[0x0047] == 0x01
    assert cpu.flags[flags.C] == 0
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 0
    assert cpu.cycles_executed == 6


def test_cpu_instruction_LSR_ABSOLUTE_0x4E() -> None:  # noqa: N802
    """Test LSR Absolute mode."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.ram[0x1234] = 0x80  # 1000 0000

    # LSR $1234
    cpu.ram[0xFFFC] = instructions.LSR_ABSOLUTE_0x4E
    cpu.ram[0xFFFD] = 0x34
    cpu.ram[0xFFFE] = 0x12

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=6)

    # then:
    assert cpu.ram[0x1234] == 0x40  # 0100 0000
    assert cpu.flags[flags.C] == 0  # Bit 0 was 0
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 0  # Always 0 for LSR
    assert cpu.cycles_executed == 6


def test_cpu_instruction_LSR_ABSOLUTE_X_0x5E() -> None:  # noqa: N802
    """Test LSR Absolute,X mode."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.X = 0x10
    cpu.ram[0x1244] = 0xFF  # 0x1234 + 0x10

    # LSR $1234,X
    cpu.ram[0xFFFC] = instructions.LSR_ABSOLUTE_X_0x5E
    cpu.ram[0xFFFD] = 0x34
    cpu.ram[0xFFFE] = 0x12

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=7)

    # then:
    assert cpu.ram[0x1244] == 0x7F  # 0111 1111
    assert cpu.flags[flags.C] == 1  # Bit 0 was 1
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 0  # Always 0 for LSR
    assert cpu.cycles_executed == 7
