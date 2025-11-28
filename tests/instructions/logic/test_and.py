#!/usr/bin/env python3
import contextlib
import logging

import mos6502
from mos6502 import CPU, errors, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_AND_IMMEDIATE_0x29_basic(cpu: CPU) -> None:  # noqa: N802
    """Test AND Immediate basic operation."""
    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0b11110000

    # AND #$0F (0b00001111)
    cpu.ram[pc] = instructions.AND_IMMEDIATE_0x29
    cpu.ram[pc + 1] = 0b00001111

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0b00000000  # 0xF0 & 0x0F = 0x00
    assert cpu.flags[flags.Z] == 1  # Result is zero
    assert cpu.flags[flags.N] == 0  # Bit 7 is 0
    assert cpu.cycles_executed - cycles_before == 2


def test_cpu_instruction_AND_IMMEDIATE_0x29_nonzero(cpu: CPU) -> None:  # noqa: N802
    """Test AND Immediate with non-zero result."""
    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0b11110101

    # AND #$F0
    cpu.ram[pc] = instructions.AND_IMMEDIATE_0x29
    cpu.ram[pc + 1] = 0b11110000

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0b11110000  # 0xF5 & 0xF0 = 0xF0
    assert cpu.flags[flags.Z] == 0  # Result is not zero
    assert cpu.flags[flags.N] == 1  # Bit 7 is 1
    assert cpu.cycles_executed - cycles_before == 2


def test_cpu_instruction_AND_IMMEDIATE_0x29_negative(cpu: CPU) -> None:  # noqa: N802
    """Test AND Immediate setting negative flag."""
    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0xFF

    # AND #$80
    cpu.ram[pc] = instructions.AND_IMMEDIATE_0x29
    cpu.ram[pc + 1] = 0x80

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x80  # 0xFF & 0x80 = 0x80
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 1  # Bit 7 is 1
    assert cpu.cycles_executed - cycles_before == 2


def test_cpu_instruction_AND_ZEROPAGE_0x25(cpu: CPU) -> None:  # noqa: N802
    """Test AND Zero Page addressing mode."""
    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0b11001100
    cpu.ram[0x0042] = 0b10101010

    # AND $42
    cpu.ram[pc] = instructions.AND_ZEROPAGE_0x25
    cpu.ram[pc + 1] = 0x42

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=3)

    # then:
    assert cpu.A == 0b10001000  # 0xCC & 0xAA = 0x88
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 1
    assert cpu.cycles_executed - cycles_before == 3


def test_cpu_instruction_AND_ABSOLUTE_0x2D(cpu: CPU) -> None:  # noqa: N802
    """Test AND Absolute addressing mode."""
    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0xFF
    cpu.ram[0x1234] = 0x0F

    # AND $1234
    cpu.ram[pc] = instructions.AND_ABSOLUTE_0x2D
    cpu.ram[pc + 1] = 0x34
    cpu.ram[pc + 2] = 0x12

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=4)

    # then:
    assert cpu.A == 0x0F  # 0xFF & 0x0F = 0x0F
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 0  # Bit 7 is 0
    assert cpu.cycles_executed - cycles_before == 4
