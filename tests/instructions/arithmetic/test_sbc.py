#!/usr/bin/env python3
import contextlib
import logging

import mos6502
from mos6502 import exceptions, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_SBC_IMMEDIATE_0xE9_simple() -> None:  # noqa: N802
    """Test SBC Immediate mode with simple subtraction."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0x50
    cpu.flags[flags.C] = 1  # No borrow

    # SBC #$10
    cpu.ram[0xFFFC] = instructions.SBC_IMMEDIATE_0xE9
    cpu.ram[0xFFFD] = 0x10

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x40  # 80 - 16 = 64
    assert cpu.flags[flags.C] == 1  # No borrow (A >= M)
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 0  # Positive
    assert cpu.flags[flags.V] == 0  # No overflow
    assert cpu.cycles_executed == 2


def test_cpu_instruction_SBC_IMMEDIATE_0xE9_with_borrow() -> None:  # noqa: N802
    """Test SBC with borrow (C=0)."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0x50
    cpu.flags[flags.C] = 0  # Borrow set

    # SBC #$10
    cpu.ram[0xFFFC] = instructions.SBC_IMMEDIATE_0xE9
    cpu.ram[0xFFFD] = 0x10

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x3F  # 80 - 16 - 1 = 63
    assert cpu.flags[flags.C] == 1  # No borrow needed for result
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 0
    assert cpu.flags[flags.V] == 0
    assert cpu.cycles_executed == 2


def test_cpu_instruction_SBC_IMMEDIATE_0xE9_borrow_out() -> None:  # noqa: N802
    """Test SBC with borrow out (underflow)."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0x00
    cpu.flags[flags.C] = 1  # No borrow in

    # SBC #$01
    cpu.ram[0xFFFC] = instructions.SBC_IMMEDIATE_0xE9
    cpu.ram[0xFFFD] = 0x01

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0xFF  # 0 - 1 = -1 (255 in unsigned)
    assert cpu.flags[flags.C] == 0  # Borrow occurred
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Negative
    assert cpu.flags[flags.V] == 0  # No signed overflow
    assert cpu.cycles_executed == 2


def test_cpu_instruction_SBC_IMMEDIATE_0xE9_zero() -> None:  # noqa: N802
    """Test SBC resulting in zero."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0x50
    cpu.flags[flags.C] = 1

    # SBC #$50
    cpu.ram[0xFFFC] = instructions.SBC_IMMEDIATE_0xE9
    cpu.ram[0xFFFD] = 0x50

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x00
    assert cpu.flags[flags.C] == 1  # No borrow
    assert cpu.flags[flags.Z] == 1  # Zero
    assert cpu.flags[flags.N] == 0
    assert cpu.flags[flags.V] == 0
    assert cpu.cycles_executed == 2


def test_cpu_instruction_SBC_IMMEDIATE_0xE9_overflow() -> None:  # noqa: N802
    """Test SBC signed overflow: positive - negative = negative."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0x50  # +80
    cpu.flags[flags.C] = 1

    # SBC #$B0
    cpu.ram[0xFFFC] = instructions.SBC_IMMEDIATE_0xE9
    cpu.ram[0xFFFD] = 0xB0  # -80 in two's complement

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0xA0  # Result wraps (overflow)
    assert cpu.flags[flags.C] == 0  # Borrow occurred
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 1  # Negative
    assert cpu.flags[flags.V] == 1  # Signed overflow
    assert cpu.cycles_executed == 2


def test_cpu_instruction_SBC_ZEROPAGE_0xE5() -> None:  # noqa: N802
    """Test SBC Zero Page mode."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0x50
    cpu.ram[0x0042] = 0x30
    cpu.flags[flags.C] = 1

    # SBC $42
    cpu.ram[0xFFFC] = instructions.SBC_ZEROPAGE_0xE5
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=3)

    # then:
    assert cpu.A == 0x20
    assert cpu.flags[flags.C] == 1
    assert cpu.flags[flags.V] == 0
    assert cpu.cycles_executed == 3


def test_cpu_instruction_SBC_ABSOLUTE_0xED() -> None:  # noqa: N802
    """Test SBC Absolute mode."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    cpu.A = 0x50
    cpu.ram[0x1234] = 0x25
    cpu.flags[flags.C] = 0  # Borrow

    # SBC $1234
    cpu.ram[0xFFFC] = instructions.SBC_ABSOLUTE_0xED
    cpu.ram[0xFFFD] = 0x34
    cpu.ram[0xFFFE] = 0x12

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=4)

    # then:
    assert cpu.A == 0x2A  # 80 - 37 - 1 = 42
    assert cpu.flags[flags.C] == 1
    assert cpu.flags[flags.V] == 0
    assert cpu.cycles_executed == 4
