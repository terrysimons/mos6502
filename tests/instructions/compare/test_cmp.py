#!/usr/bin/env python3
import contextlib
import logging

import mos6502
from mos6502 import CPU, errors, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_CMP_IMMEDIATE_0xC9_equal(cpu: CPU) -> None:  # noqa: N802
    """Test CMP when A == M (sets Z=1, C=1, N=0)."""
    # given:

    cpu.A = 0x42

    # CMP #$42
    cpu.ram[0xFFFC] = instructions.CMP_IMMEDIATE_0xC9
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x42  # A unchanged
    assert cpu.flags[flags.Z] == 1  # Equal
    assert cpu.flags[flags.C] == 1  # A >= M (no borrow)
    assert cpu.flags[flags.N] == 0  # Result is 0
    assert cpu.cycles_executed == 2


def test_cpu_instruction_CMP_IMMEDIATE_0xC9_greater(cpu: CPU) -> None:  # noqa: N802
    """Test CMP when A > M (sets Z=0, C=1, N varies)."""
    # given:

    cpu.A = 0x50

    # CMP #$30
    cpu.ram[0xFFFC] = instructions.CMP_IMMEDIATE_0xC9
    cpu.ram[0xFFFD] = 0x30

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x50  # A unchanged
    assert cpu.flags[flags.Z] == 0  # Not equal
    assert cpu.flags[flags.C] == 1  # A >= M (no borrow)
    assert cpu.flags[flags.N] == 0  # Result = 0x20 (positive)
    assert cpu.cycles_executed == 2


def test_cpu_instruction_CMP_IMMEDIATE_0xC9_less(cpu: CPU) -> None:  # noqa: N802
    """Test CMP when A < M (sets Z=0, C=0, N=1)."""
    # given:

    cpu.A = 0x30

    # CMP #$50
    cpu.ram[0xFFFC] = instructions.CMP_IMMEDIATE_0xC9
    cpu.ram[0xFFFD] = 0x50

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x30  # A unchanged
    assert cpu.flags[flags.Z] == 0  # Not equal
    assert cpu.flags[flags.C] == 0  # A < M (borrow needed)
    assert cpu.flags[flags.N] == 1  # Result = 0xE0 (negative, bit 7 set)
    assert cpu.cycles_executed == 2


def test_cpu_instruction_CMP_IMMEDIATE_0xC9_zero(cpu: CPU) -> None:  # noqa: N802
    """Test CMP when A = 0 and M = 0."""
    # given:

    cpu.A = 0x00

    # CMP #$00
    cpu.ram[0xFFFC] = instructions.CMP_IMMEDIATE_0xC9
    cpu.ram[0xFFFD] = 0x00

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x00
    assert cpu.flags[flags.Z] == 1  # Equal
    assert cpu.flags[flags.C] == 1  # A >= M
    assert cpu.flags[flags.N] == 0  # Result = 0
    assert cpu.cycles_executed == 2


def test_cpu_instruction_CMP_ZEROPAGE_0xC5(cpu: CPU) -> None:  # noqa: N802
    """Test CMP Zero Page addressing mode."""
    # given:

    cpu.A = 0x50
    cpu.ram[0x0042] = 0x30  # Value at zero page address

    # CMP $42
    cpu.ram[0xFFFC] = instructions.CMP_ZEROPAGE_0xC5
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=3)

    # then:
    assert cpu.A == 0x50  # A unchanged
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.C] == 1  # A > M
    assert cpu.flags[flags.N] == 0
    assert cpu.cycles_executed == 3


def test_cpu_instruction_CMP_ABSOLUTE_0xCD(cpu: CPU) -> None:  # noqa: N802
    """Test CMP Absolute addressing mode."""
    # given:

    cpu.A = 0x20
    cpu.ram[0x1234] = 0x30  # Value at absolute address

    # CMP $1234
    cpu.ram[0xFFFC] = instructions.CMP_ABSOLUTE_0xCD
    cpu.ram[0xFFFD] = 0x34
    cpu.ram[0xFFFE] = 0x12

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=4)

    # then:
    assert cpu.A == 0x20  # A unchanged
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.C] == 0  # A < M
    assert cpu.flags[flags.N] == 1  # Negative result
    assert cpu.cycles_executed == 4
