#!/usr/bin/env python3
import contextlib
import logging

import mos6502
from mos6502 import CPU, errors, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_CPY_IMMEDIATE_0xC0_equal(cpu: CPU) -> None:  # noqa: N802
    """Test CPY when Y == M (sets Z=1, C=1, N=0)."""
    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.Y = 0x42

    # CPY #$42
    cpu.ram[pc] = instructions.CPY_IMMEDIATE_0xC0
    cpu.ram[pc + 1] = 0x42

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.Y == 0x42  # Y unchanged
    assert cpu.flags[flags.Z] == 1  # Equal
    assert cpu.flags[flags.C] == 1  # Y >= M (no borrow)
    assert cpu.flags[flags.N] == 0  # Result is 0
    assert cpu.cycles_executed - cycles_before == 2


def test_cpu_instruction_CPY_IMMEDIATE_0xC0_greater(cpu: CPU) -> None:  # noqa: N802
    """Test CPY when Y > M (sets Z=0, C=1, N varies)."""
    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.Y = 0x50

    # CPY #$30
    cpu.ram[pc] = instructions.CPY_IMMEDIATE_0xC0
    cpu.ram[pc + 1] = 0x30

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.Y == 0x50  # Y unchanged
    assert cpu.flags[flags.Z] == 0  # Not equal
    assert cpu.flags[flags.C] == 1  # Y >= M (no borrow)
    assert cpu.flags[flags.N] == 0  # Result = 0x20 (positive)
    assert cpu.cycles_executed - cycles_before == 2


def test_cpu_instruction_CPY_IMMEDIATE_0xC0_less(cpu: CPU) -> None:  # noqa: N802
    """Test CPY when Y < M (sets Z=0, C=0, N=1)."""
    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.Y = 0x30

    # CPY #$50
    cpu.ram[pc] = instructions.CPY_IMMEDIATE_0xC0
    cpu.ram[pc + 1] = 0x50

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.Y == 0x30  # Y unchanged
    assert cpu.flags[flags.Z] == 0  # Not equal
    assert cpu.flags[flags.C] == 0  # Y < M (borrow needed)
    assert cpu.flags[flags.N] == 1  # Result = 0xE0 (negative, bit 7 set)
    assert cpu.cycles_executed - cycles_before == 2


def test_cpu_instruction_CPY_ZEROPAGE_0xC4(cpu: CPU) -> None:  # noqa: N802
    """Test CPY Zero Page addressing mode."""
    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.Y = 0x50
    cpu.ram[0x0042] = 0x30  # Value at zero page address

    # CPY $42
    cpu.ram[pc] = instructions.CPY_ZEROPAGE_0xC4
    cpu.ram[pc + 1] = 0x42

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=3)

    # then:
    assert cpu.Y == 0x50  # Y unchanged
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.C] == 1  # Y > M
    assert cpu.flags[flags.N] == 0
    assert cpu.cycles_executed - cycles_before == 3


def test_cpu_instruction_CPY_ABSOLUTE_0xCC(cpu: CPU) -> None:  # noqa: N802
    """Test CPY Absolute addressing mode."""
    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.Y = 0x20
    cpu.ram[0x1234] = 0x30  # Value at absolute address

    # CPY $1234
    cpu.ram[pc] = instructions.CPY_ABSOLUTE_0xCC
    cpu.ram[pc + 1] = 0x34
    cpu.ram[pc + 2] = 0x12

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=4)

    # then:
    assert cpu.Y == 0x20  # Y unchanged
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.C] == 0  # Y < M
    assert cpu.flags[flags.N] == 1  # Negative result
    assert cpu.cycles_executed - cycles_before == 4
