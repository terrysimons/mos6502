#!/usr/bin/env python3
import contextlib
import logging

import mos6502
from mos6502 import CPU, errors, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_EOR_IMMEDIATE_0x49_basic(cpu: CPU) -> None:  # noqa: N802
    """Test EOR Immediate basic operation."""
    # given:

    cpu.A = 0b11110000

    # EOR #$0F (0b00001111)
    cpu.ram[0xFFFC] = instructions.EOR_IMMEDIATE_0x49
    cpu.ram[0xFFFD] = 0b00001111

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0b11111111  # 0xF0 ^ 0x0F = 0xFF
    assert cpu.flags[flags.Z] == 0  # Result is not zero
    assert cpu.flags[flags.N] == 1  # Bit 7 is 1
    assert cpu.cycles_executed == 2


def test_cpu_instruction_EOR_IMMEDIATE_0x49_zero(cpu: CPU) -> None:  # noqa: N802
    """Test EOR Immediate with zero result (XOR with itself)."""
    # given:

    cpu.A = 0b10101010

    # EOR #$AA (same value)
    cpu.ram[0xFFFC] = instructions.EOR_IMMEDIATE_0x49
    cpu.ram[0xFFFD] = 0b10101010

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x00  # 0xAA ^ 0xAA = 0x00
    assert cpu.flags[flags.Z] == 1  # Result is zero
    assert cpu.flags[flags.N] == 0  # Bit 7 is 0
    assert cpu.cycles_executed == 2


def test_cpu_instruction_EOR_IMMEDIATE_0x49_toggle_bits(cpu: CPU) -> None:  # noqa: N802
    """Test EOR Immediate toggling specific bits."""
    # given:

    cpu.A = 0b11001100

    # EOR #$0F (toggle lower nibble)
    cpu.ram[0xFFFC] = instructions.EOR_IMMEDIATE_0x49
    cpu.ram[0xFFFD] = 0b00001111

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0b11000011  # 0xCC ^ 0x0F = 0xC3
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 1  # Bit 7 is 1
    assert cpu.cycles_executed == 2


def test_cpu_instruction_EOR_ZEROPAGE_0x45(cpu: CPU) -> None:  # noqa: N802
    """Test EOR Zero Page addressing mode."""
    # given:

    cpu.A = 0xFF
    cpu.ram[0x0042] = 0x0F

    # EOR $42
    cpu.ram[0xFFFC] = instructions.EOR_ZEROPAGE_0x45
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=3)

    # then:
    assert cpu.A == 0xF0  # 0xFF ^ 0x0F = 0xF0
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 1  # Bit 7 is 1
    assert cpu.cycles_executed == 3


def test_cpu_instruction_EOR_ABSOLUTE_0x4D(cpu: CPU) -> None:  # noqa: N802
    """Test EOR Absolute addressing mode."""
    # given:

    cpu.A = 0b10101010
    cpu.ram[0x1234] = 0b01010101

    # EOR $1234
    cpu.ram[0xFFFC] = instructions.EOR_ABSOLUTE_0x4D
    cpu.ram[0xFFFD] = 0x34
    cpu.ram[0xFFFE] = 0x12

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=4)

    # then:
    assert cpu.A == 0xFF  # 0xAA ^ 0x55 = 0xFF
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 1  # Bit 7 is 1
    assert cpu.cycles_executed == 4
