#!/usr/bin/env python3
import contextlib
import logging

import mos6502
from mos6502 import CPU, exceptions, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_BIT_ZEROPAGE_0x24_zero_result(cpu: CPU) -> None:  # noqa: N802
    """Test BIT when A AND M = 0 (sets Z=1, N and V from memory bits)."""
    # given:

    cpu.A = 0x0F  # 0000 1111
    cpu.ram[0x0042] = 0xF0  # 1111 0000 (bit 7=1, bit 6=1)

    # BIT $42
    cpu.ram[0xFFFC] = instructions.BIT_ZEROPAGE_0x24
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=3)

    # then:
    assert cpu.A == 0x0F  # A unchanged
    assert cpu.flags[flags.Z] == 1  # A AND M = 0
    assert cpu.flags[flags.N] == 1  # Bit 7 of memory = 1
    assert cpu.flags[flags.V] == 1  # Bit 6 of memory = 1
    assert cpu.cycles_executed == 3


def test_cpu_instruction_BIT_ZEROPAGE_0x24_nonzero_result(cpu: CPU) -> None:  # noqa: N802
    """Test BIT when A AND M != 0 (sets Z=0, N and V from memory bits)."""
    # given:

    cpu.A = 0xFF  # 1111 1111
    cpu.ram[0x0042] = 0x42  # 0100 0010 (bit 7=0, bit 6=1)

    # BIT $42
    cpu.ram[0xFFFC] = instructions.BIT_ZEROPAGE_0x24
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=3)

    # then:
    assert cpu.A == 0xFF  # A unchanged
    assert cpu.flags[flags.Z] == 0  # A AND M = 0x42 (nonzero)
    assert cpu.flags[flags.N] == 0  # Bit 7 of memory = 0
    assert cpu.flags[flags.V] == 1  # Bit 6 of memory = 1
    assert cpu.cycles_executed == 3


def test_cpu_instruction_BIT_ZEROPAGE_0x24_n_flag_clear(cpu: CPU) -> None:  # noqa: N802
    """Test BIT with memory bit 7 clear (N=0)."""
    # given:

    cpu.A = 0xFF
    cpu.ram[0x0042] = 0x3F  # 0011 1111 (bit 7=0, bit 6=0)

    # BIT $42
    cpu.ram[0xFFFC] = instructions.BIT_ZEROPAGE_0x24
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=3)

    # then:
    assert cpu.A == 0xFF  # A unchanged
    assert cpu.flags[flags.Z] == 0  # A AND M = 0x3F (nonzero)
    assert cpu.flags[flags.N] == 0  # Bit 7 of memory = 0
    assert cpu.flags[flags.V] == 0  # Bit 6 of memory = 0
    assert cpu.cycles_executed == 3


def test_cpu_instruction_BIT_ZEROPAGE_0x24_v_flag_set(cpu: CPU) -> None:  # noqa: N802
    """Test BIT with memory bit 6 set but bit 7 clear (N=0, V=1)."""
    # given:

    cpu.A = 0xFF
    cpu.ram[0x0042] = 0x40  # 0100 0000 (bit 7=0, bit 6=1)

    # BIT $42
    cpu.ram[0xFFFC] = instructions.BIT_ZEROPAGE_0x24
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=3)

    # then:
    assert cpu.A == 0xFF  # A unchanged
    assert cpu.flags[flags.Z] == 0  # A AND M = 0x40 (nonzero)
    assert cpu.flags[flags.N] == 0  # Bit 7 of memory = 0
    assert cpu.flags[flags.V] == 1  # Bit 6 of memory = 1
    assert cpu.cycles_executed == 3


def test_cpu_instruction_BIT_ABSOLUTE_0x2C(cpu: CPU) -> None:  # noqa: N802
    """Test BIT Absolute addressing mode."""
    # given:

    cpu.A = 0xAA  # 1010 1010
    cpu.ram[0x1234] = 0xC5  # 1100 0101 (bit 7=1, bit 6=1)

    # BIT $1234
    cpu.ram[0xFFFC] = instructions.BIT_ABSOLUTE_0x2C
    cpu.ram[0xFFFD] = 0x34
    cpu.ram[0xFFFE] = 0x12

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=4)

    # then:
    assert cpu.A == 0xAA  # A unchanged
    assert cpu.flags[flags.Z] == 0  # A AND M = 0x80 (nonzero)
    assert cpu.flags[flags.N] == 1  # Bit 7 of memory = 1
    assert cpu.flags[flags.V] == 1  # Bit 6 of memory = 1
    assert cpu.cycles_executed == 4


def test_cpu_instruction_BIT_ABSOLUTE_0x2C_all_flags_clear(cpu: CPU) -> None:  # noqa: N802
    """Test BIT Absolute with all flags clearing."""
    # given:

    cpu.A = 0x0F  # 0000 1111
    cpu.ram[0x1234] = 0x30  # 0011 0000 (bit 7=0, bit 6=0, AND result=0)

    # BIT $1234
    cpu.ram[0xFFFC] = instructions.BIT_ABSOLUTE_0x2C
    cpu.ram[0xFFFD] = 0x34
    cpu.ram[0xFFFE] = 0x12

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=4)

    # then:
    assert cpu.A == 0x0F  # A unchanged
    assert cpu.flags[flags.Z] == 1  # A AND M = 0 (zero)
    assert cpu.flags[flags.N] == 0  # Bit 7 of memory = 0
    assert cpu.flags[flags.V] == 0  # Bit 6 of memory = 0
    assert cpu.cycles_executed == 4
