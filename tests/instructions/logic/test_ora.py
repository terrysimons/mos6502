#!/usr/bin/env python3
import contextlib
import logging

import mos6502
from mos6502 import exceptions, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_ORA_IMMEDIATE_0x09_basic() -> None:  # noqa: N802
    """Test ORA Immediate basic operation."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0b11110000

    # ORA #$0F (0b00001111)
    cpu.ram[0xFFFC] = instructions.ORA_IMMEDIATE_0x09
    cpu.ram[0xFFFD] = 0b00001111

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0b11111111  # 0xF0 | 0x0F = 0xFF
    assert cpu.flags[flags.Z] == 0  # Result is not zero
    assert cpu.flags[flags.N] == 1  # Bit 7 is 1
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ORA_IMMEDIATE_0x09_zero() -> None:  # noqa: N802
    """Test ORA Immediate with zero (OR with zero = no change)."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0x00

    # ORA #$00
    cpu.ram[0xFFFC] = instructions.ORA_IMMEDIATE_0x09
    cpu.ram[0xFFFD] = 0x00

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x00  # 0x00 | 0x00 = 0x00
    assert cpu.flags[flags.Z] == 1  # Result is zero
    assert cpu.flags[flags.N] == 0  # Bit 7 is 0
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ORA_IMMEDIATE_0x09_set_bits() -> None:  # noqa: N802
    """Test ORA Immediate setting specific bits."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0b10001000

    # ORA #$07 (set lower 3 bits)
    cpu.ram[0xFFFC] = instructions.ORA_IMMEDIATE_0x09
    cpu.ram[0xFFFD] = 0b00000111

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0b10001111  # 0x88 | 0x07 = 0x8F
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 1  # Bit 7 is 1
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ORA_ZEROPAGE_0x05() -> None:  # noqa: N802
    """Test ORA Zero Page addressing mode."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0b11001100
    cpu.ram[0x0042] = 0b00110011

    # ORA $42
    cpu.ram[0xFFFC] = instructions.ORA_ZEROPAGE_0x05
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=3)

    # then:
    assert cpu.A == 0xFF  # 0xCC | 0x33 = 0xFF
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 1  # Bit 7 is 1
    assert cpu.cycles_executed == 3


def test_cpu_instruction_ORA_ABSOLUTE_0x0D() -> None:  # noqa: N802
    """Test ORA Absolute addressing mode."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0x0F
    cpu.ram[0x1234] = 0x70

    # ORA $1234
    cpu.ram[0xFFFC] = instructions.ORA_ABSOLUTE_0x0D
    cpu.ram[0xFFFD] = 0x34
    cpu.ram[0xFFFE] = 0x12

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=4)

    # then:
    assert cpu.A == 0x7F  # 0x0F | 0x70 = 0x7F
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 0  # Bit 7 is 0
    assert cpu.cycles_executed == 4
