#!/usr/bin/env python3
import contextlib
import logging

import mos6502
from mos6502 import CPU, errors, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_CPX_IMMEDIATE_0xE0_equal(cpu: CPU) -> None:  # noqa: N802
    """Test CPX when X == M (sets Z=1, C=1, N=0)."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.X = 0x42

    # CPX #$42
    cpu.ram[pc] = instructions.CPX_IMMEDIATE_0xE0
    cpu.ram[pc + 1] = 0x42

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.X == 0x42  # X unchanged
    assert cpu.flags[flags.Z] == 1  # Equal
    assert cpu.flags[flags.C] == 1  # X >= M (no borrow)
    assert cpu.flags[flags.N] == 0  # Result is 0
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_CPX_IMMEDIATE_0xE0_greater(cpu: CPU) -> None:  # noqa: N802
    """Test CPX when X > M (sets Z=0, C=1, N varies)."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.X = 0x50

    # CPX #$30
    cpu.ram[pc] = instructions.CPX_IMMEDIATE_0xE0
    cpu.ram[pc + 1] = 0x30

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.X == 0x50  # X unchanged
    assert cpu.flags[flags.Z] == 0  # Not equal
    assert cpu.flags[flags.C] == 1  # X >= M (no borrow)
    assert cpu.flags[flags.N] == 0  # Result = 0x20 (positive)
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_CPX_IMMEDIATE_0xE0_less(cpu: CPU) -> None:  # noqa: N802
    """Test CPX when X < M (sets Z=0, C=0, N=1)."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.X = 0x30

    # CPX #$50
    cpu.ram[pc] = instructions.CPX_IMMEDIATE_0xE0
    cpu.ram[pc + 1] = 0x50

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.X == 0x30  # X unchanged
    assert cpu.flags[flags.Z] == 0  # Not equal
    assert cpu.flags[flags.C] == 0  # X < M (borrow needed)
    assert cpu.flags[flags.N] == 1  # Result = 0xE0 (negative, bit 7 set)
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_CPX_ZEROPAGE_0xE4(cpu: CPU) -> None:  # noqa: N802
    """Test CPX Zero Page addressing mode."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.X = 0x50
    cpu.ram[0x0042] = 0x30  # Value at zero page address

    # CPX $42
    cpu.ram[pc] = instructions.CPX_ZEROPAGE_0xE4
    cpu.ram[pc + 1] = 0x42

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=3

    # then:
    assert cpu.X == 0x50  # X unchanged
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.C] == 1  # X > M
    assert cpu.flags[flags.N] == 0
    # assert cpu.cycles_executed - cycles_before == 3
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_CPX_ABSOLUTE_0xEC(cpu: CPU) -> None:  # noqa: N802
    """Test CPX Absolute addressing mode."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.X = 0x20
    cpu.ram[0x1234] = 0x30  # Value at absolute address

    # CPX $1234
    cpu.ram[pc] = instructions.CPX_ABSOLUTE_0xEC
    cpu.ram[pc + 1] = 0x34
    cpu.ram[pc + 2] = 0x12

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=4

    # then:
    assert cpu.X == 0x20  # X unchanged
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.C] == 0  # X < M
    assert cpu.flags[flags.N] == 1  # Negative result
    # assert cpu.cycles_executed - cycles_before == 4
    assert cpu.instructions_executed - instructions_before == 1
