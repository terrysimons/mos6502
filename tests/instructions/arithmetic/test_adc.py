#!/usr/bin/env python3
import contextlib
import logging

import mos6502
from mos6502 import exceptions, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_ADC_IMMEDIATE_0x69_simple() -> None:  # noqa: N802
    """Test ADC Immediate mode with simple addition."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0x50
    cpu.flags[flags.C] = 0

    # ADC #$10
    cpu.ram[0xFFFC] = instructions.ADC_IMMEDIATE_0x69
    cpu.ram[0xFFFD] = 0x10

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x60  # 80 + 16 = 96
    assert cpu.flags[flags.C] == 0  # No carry
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 0  # Positive
    assert cpu.flags[flags.V] == 0  # No overflow
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ADC_IMMEDIATE_0x69_with_carry() -> None:  # noqa: N802
    """Test ADC with carry flag set."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0x50
    cpu.flags[flags.C] = 1  # Carry set

    # ADC #$10
    cpu.ram[0xFFFC] = instructions.ADC_IMMEDIATE_0x69
    cpu.ram[0xFFFD] = 0x10

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x61  # 80 + 16 + 1 = 97
    assert cpu.flags[flags.C] == 0
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 0
    assert cpu.flags[flags.V] == 0
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ADC_IMMEDIATE_0x69_carry_out() -> None:  # noqa: N802
    """Test ADC with carry out."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0xFF
    cpu.flags[flags.C] = 0

    # ADC #$01
    cpu.ram[0xFFFC] = instructions.ADC_IMMEDIATE_0x69
    cpu.ram[0xFFFD] = 0x01

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x00  # 255 + 1 = 256, wrapped to 0
    assert cpu.flags[flags.C] == 1  # Carry set
    assert cpu.flags[flags.Z] == 1  # Zero
    assert cpu.flags[flags.N] == 0  # Not negative
    assert cpu.flags[flags.V] == 0  # No signed overflow
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ADC_IMMEDIATE_0x69_overflow_positive() -> None:  # noqa: N802
    """Test ADC signed overflow: positive + positive = negative."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0x7F  # +127
    cpu.flags[flags.C] = 0

    # ADC #$01
    cpu.ram[0xFFFC] = instructions.ADC_IMMEDIATE_0x69
    cpu.ram[0xFFFD] = 0x01  # +1

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x80  # Result: -128 in two's complement
    assert cpu.flags[flags.C] == 0  # No unsigned carry
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Negative
    assert cpu.flags[flags.V] == 1  # Signed overflow occurred
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ADC_IMMEDIATE_0x69_overflow_negative() -> None:  # noqa: N802
    """Test ADC signed overflow: negative + negative = positive."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0x80  # -128
    cpu.flags[flags.C] = 0

    # ADC #$FF
    cpu.ram[0xFFFC] = instructions.ADC_IMMEDIATE_0x69
    cpu.ram[0xFFFD] = 0xFF  # -1

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x7F  # Result: +127 (overflow wrapped)
    assert cpu.flags[flags.C] == 1  # Unsigned carry
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 0  # Positive
    assert cpu.flags[flags.V] == 1  # Signed overflow occurred
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ADC_ZEROPAGE_0x65() -> None:  # noqa: N802
    """Test ADC Zero Page mode."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0x20
    cpu.ram[0x0042] = 0x30
    cpu.flags[flags.C] = 0

    # ADC $42
    cpu.ram[0xFFFC] = instructions.ADC_ZEROPAGE_0x65
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=3)

    # then:
    assert cpu.A == 0x50
    assert cpu.flags[flags.C] == 0
    assert cpu.flags[flags.V] == 0
    assert cpu.cycles_executed == 3


def test_cpu_instruction_ADC_ABSOLUTE_0x6D() -> None:  # noqa: N802
    """Test ADC Absolute mode."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0x10
    cpu.ram[0x1234] = 0x25
    cpu.flags[flags.C] = 1

    # ADC $1234
    cpu.ram[0xFFFC] = instructions.ADC_ABSOLUTE_0x6D
    cpu.ram[0xFFFD] = 0x34
    cpu.ram[0xFFFE] = 0x12

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=4)

    # then:
    assert cpu.A == 0x36  # 16 + 37 + 1 = 54
    assert cpu.flags[flags.C] == 0
    assert cpu.flags[flags.V] == 0
    assert cpu.cycles_executed == 4
