#!/usr/bin/env python3
import contextlib
import logging

import mos6502
from mos6502 import exceptions, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_DEC_ZEROPAGE_0xC6() -> None:  # noqa: N802
    """Test DEC Zero Page addressing mode."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.ram[0x0042] = 0x05

    # DEC $42
    cpu.ram[0xFFFC] = instructions.DEC_ZEROPAGE_0xC6
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=5)

    # then:
    assert cpu.ram[0x0042] == 0x04
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 0  # Positive
    assert cpu.cycles_executed == 5


def test_cpu_instruction_DEC_ZEROPAGE_0xC6_to_zero() -> None:  # noqa: N802
    """Test DEC to zero."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.ram[0x0042] = 0x01

    # DEC $42
    cpu.ram[0xFFFC] = instructions.DEC_ZEROPAGE_0xC6
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=5)

    # then:
    assert cpu.ram[0x0042] == 0x00
    assert cpu.flags[flags.Z] == 1  # Zero
    assert cpu.flags[flags.N] == 0  # Not negative
    assert cpu.cycles_executed == 5


def test_cpu_instruction_DEC_ZEROPAGE_0xC6_wrap_to_ff() -> None:  # noqa: N802
    """Test DEC wrapping from 0x00 to 0xFF."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.ram[0x0042] = 0x00

    # DEC $42
    cpu.ram[0xFFFC] = instructions.DEC_ZEROPAGE_0xC6
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=5)

    # then:
    assert cpu.ram[0x0042] == 0xFF
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Negative (bit 7 set)
    assert cpu.cycles_executed == 5


def test_cpu_instruction_DEC_ZEROPAGE_0xC6_negative() -> None:  # noqa: N802
    """Test DEC resulting in negative value (bit 7 set)."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.ram[0x0042] = 0x81  # 129

    # DEC $42
    cpu.ram[0xFFFC] = instructions.DEC_ZEROPAGE_0xC6
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=5)

    # then:
    assert cpu.ram[0x0042] == 0x80  # 128 (bit 7 set)
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Negative (bit 7 set)
    assert cpu.cycles_executed == 5


def test_cpu_instruction_DEC_ZEROPAGE_X_0xD6() -> None:  # noqa: N802
    """Test DEC Zero Page,X addressing mode."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.X = 0x05
    cpu.ram[0x0047] = 0x10  # 0x42 + 0x05 = 0x47

    # DEC $42,X
    cpu.ram[0xFFFC] = instructions.DEC_ZEROPAGE_X_0xD6
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=6)

    # then:
    assert cpu.ram[0x0047] == 0x0F
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 0
    assert cpu.cycles_executed == 6


def test_cpu_instruction_DEC_ABSOLUTE_0xCE() -> None:  # noqa: N802
    """Test DEC Absolute addressing mode."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.ram[0x1234] = 0x42

    # DEC $1234
    cpu.ram[0xFFFC] = instructions.DEC_ABSOLUTE_0xCE
    cpu.ram[0xFFFD] = 0x34
    cpu.ram[0xFFFE] = 0x12

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=6)

    # then:
    assert cpu.ram[0x1234] == 0x41
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 0
    assert cpu.cycles_executed == 6


def test_cpu_instruction_DEC_ABSOLUTE_X_0xDE() -> None:  # noqa: N802
    """Test DEC Absolute,X addressing mode."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.X = 0x10
    cpu.ram[0x1244] = 0x80  # 0x1234 + 0x10 = 0x1244

    # DEC $1234,X
    cpu.ram[0xFFFC] = instructions.DEC_ABSOLUTE_X_0xDE
    cpu.ram[0xFFFD] = 0x34
    cpu.ram[0xFFFE] = 0x12

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=7)

    # then:
    assert cpu.ram[0x1244] == 0x7F
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 0  # 0x7F doesn't have bit 7 set
    assert cpu.cycles_executed == 7
