#!/usr/bin/env python3
import contextlib
import logging

import mos6502
from mos6502 import CPU, errors, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_ADC_IMMEDIATE_0x69_simple(cpu: CPU) -> None:  # noqa: N802
    """Test ADC Immediate mode with simple addition."""
    # given:

    cpu.A = 0x50
    cpu.flags[flags.C] = 0

    # ADC #$10
    cpu.ram[0xFFFC] = instructions.ADC_IMMEDIATE_0x69
    cpu.ram[0xFFFD] = 0x10

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x60  # 80 + 16 = 96
    assert cpu.flags[flags.C] == 0  # No carry
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 0  # Positive
    assert cpu.flags[flags.V] == 0  # No overflow
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ADC_IMMEDIATE_0x69_with_carry(cpu: CPU) -> None:  # noqa: N802
    """Test ADC with carry flag set."""
    # given:

    cpu.A = 0x50
    cpu.flags[flags.C] = 1  # Carry set

    # ADC #$10
    cpu.ram[0xFFFC] = instructions.ADC_IMMEDIATE_0x69
    cpu.ram[0xFFFD] = 0x10

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x61  # 80 + 16 + 1 = 97
    assert cpu.flags[flags.C] == 0
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 0
    assert cpu.flags[flags.V] == 0
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ADC_IMMEDIATE_0x69_carry_out(cpu: CPU) -> None:  # noqa: N802
    """Test ADC with carry out."""
    # given:

    cpu.A = 0xFF
    cpu.flags[flags.C] = 0

    # ADC #$01
    cpu.ram[0xFFFC] = instructions.ADC_IMMEDIATE_0x69
    cpu.ram[0xFFFD] = 0x01

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x00  # 255 + 1 = 256, wrapped to 0
    assert cpu.flags[flags.C] == 1  # Carry set
    assert cpu.flags[flags.Z] == 1  # Zero
    assert cpu.flags[flags.N] == 0  # Not negative
    assert cpu.flags[flags.V] == 0  # No signed overflow
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ADC_IMMEDIATE_0x69_overflow_positive(cpu: CPU) -> None:  # noqa: N802
    """Test ADC signed overflow: positive + positive = negative."""
    # given:

    cpu.A = 0x7F  # +127
    cpu.flags[flags.C] = 0

    # ADC #$01
    cpu.ram[0xFFFC] = instructions.ADC_IMMEDIATE_0x69
    cpu.ram[0xFFFD] = 0x01  # +1

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x80  # Result: -128 in two's complement
    assert cpu.flags[flags.C] == 0  # No unsigned carry
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Negative
    assert cpu.flags[flags.V] == 1  # Signed overflow occurred
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ADC_IMMEDIATE_0x69_overflow_negative(cpu: CPU) -> None:  # noqa: N802
    """Test ADC signed overflow: negative + negative = positive."""
    # given:

    cpu.A = 0x80  # -128
    cpu.flags[flags.C] = 0

    # ADC #$FF
    cpu.ram[0xFFFC] = instructions.ADC_IMMEDIATE_0x69
    cpu.ram[0xFFFD] = 0xFF  # -1

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x7F  # Result: +127 (overflow wrapped)
    assert cpu.flags[flags.C] == 1  # Unsigned carry
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 0  # Positive
    assert cpu.flags[flags.V] == 1  # Signed overflow occurred
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ADC_ZEROPAGE_0x65(cpu: CPU) -> None:  # noqa: N802
    """Test ADC Zero Page mode."""
    # given:

    cpu.A = 0x20
    cpu.ram[0x0042] = 0x30
    cpu.flags[flags.C] = 0

    # ADC $42
    cpu.ram[0xFFFC] = instructions.ADC_ZEROPAGE_0x65
    cpu.ram[0xFFFD] = 0x42

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=3)

    # then:
    assert cpu.A == 0x50
    assert cpu.flags[flags.C] == 0
    assert cpu.flags[flags.V] == 0
    assert cpu.cycles_executed == 3


def test_cpu_instruction_ADC_ABSOLUTE_0x6D(cpu: CPU) -> None:  # noqa: N802
    """Test ADC Absolute mode."""
    # given:

    cpu.A = 0x10
    cpu.ram[0x1234] = 0x25
    cpu.flags[flags.C] = 1

    # ADC $1234
    cpu.ram[0xFFFC] = instructions.ADC_ABSOLUTE_0x6D
    cpu.ram[0xFFFD] = 0x34
    cpu.ram[0xFFFE] = 0x12

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=4)

    # then:
    assert cpu.A == 0x36  # 16 + 37 + 1 = 54
    assert cpu.flags[flags.C] == 0
    assert cpu.flags[flags.V] == 0
    assert cpu.cycles_executed == 4


# BCD (Decimal) Mode Tests


def test_cpu_instruction_ADC_IMMEDIATE_0x69_bcd_simple(cpu: CPU) -> None:  # noqa: N802
    """Test ADC in BCD mode with simple addition."""
    # given:

    cpu.A = 0x09  # BCD 09
    cpu.flags[flags.C] = 0
    cpu.flags[flags.D] = 1  # Enable decimal mode

    # ADC #$01
    cpu.ram[0xFFFC] = instructions.ADC_IMMEDIATE_0x69
    cpu.ram[0xFFFD] = 0x01  # BCD 01

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x10  # BCD 09 + 01 = 10
    assert cpu.flags[flags.C] == 0  # No carry
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ADC_IMMEDIATE_0x69_bcd_carry_low_nibble(cpu: CPU) -> None:  # noqa: N802
    """Test ADC in BCD mode with carry from low nibble."""
    # given:

    cpu.A = 0x08  # BCD 08
    cpu.flags[flags.C] = 0
    cpu.flags[flags.D] = 1  # Enable decimal mode

    # ADC #$05
    cpu.ram[0xFFFC] = instructions.ADC_IMMEDIATE_0x69
    cpu.ram[0xFFFD] = 0x05  # BCD 05

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x13  # BCD 08 + 05 = 13
    assert cpu.flags[flags.C] == 0  # No carry out
    assert cpu.flags[flags.Z] == 0
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ADC_IMMEDIATE_0x69_bcd_carry_high_nibble(cpu: CPU) -> None:  # noqa: N802
    """Test ADC in BCD mode with carry from high nibble."""
    # given:

    cpu.A = 0x50  # BCD 50
    cpu.flags[flags.C] = 0
    cpu.flags[flags.D] = 1  # Enable decimal mode

    # ADC #$60
    cpu.ram[0xFFFC] = instructions.ADC_IMMEDIATE_0x69
    cpu.ram[0xFFFD] = 0x60  # BCD 60

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x10  # BCD 50 + 60 = 110, wraps to 10
    assert cpu.flags[flags.C] == 1  # Carry out
    assert cpu.flags[flags.Z] == 0
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ADC_IMMEDIATE_0x69_bcd_with_carry_in(cpu: CPU) -> None:  # noqa: N802
    """Test ADC in BCD mode with carry in."""
    # given:

    cpu.A = 0x09  # BCD 09
    cpu.flags[flags.C] = 1  # Carry in
    cpu.flags[flags.D] = 1  # Enable decimal mode

    # ADC #$09
    cpu.ram[0xFFFC] = instructions.ADC_IMMEDIATE_0x69
    cpu.ram[0xFFFD] = 0x09  # BCD 09

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x19  # BCD 09 + 09 + 1 = 19
    assert cpu.flags[flags.C] == 0  # No carry out
    assert cpu.flags[flags.Z] == 0
    assert cpu.cycles_executed == 2


def test_cpu_instruction_ADC_IMMEDIATE_0x69_bcd_99_plus_1_nmos(nmos_cpu: CPU) -> None:  # noqa: N802
    """Test ADC in BCD mode: 99 + 1 = 00 with carry (NMOS variants).

    VARIANT: 6502/6502A/6502C - Z and N flags are set correctly in BCD mode
    """
    # given:
    nmos_cpu.A = 0x99  # BCD 99
    nmos_cpu.flags[flags.C] = 0
    nmos_cpu.flags[flags.D] = 1  # Enable decimal mode

    # ADC #$01
    nmos_cpu.ram[0xFFFC] = instructions.ADC_IMMEDIATE_0x69
    nmos_cpu.ram[0xFFFD] = 0x01  # BCD 01

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        nmos_cpu.execute(cycles=2)

    # then:
    assert nmos_cpu.A == 0x00  # BCD 99 + 01 = 100, wraps to 00
    assert nmos_cpu.flags[flags.C] == 1  # Carry out
    assert nmos_cpu.flags[flags.Z] == 1  # Zero (NMOS sets Z correctly in BCD)
    assert nmos_cpu.cycles_executed == 2


def test_cpu_instruction_ADC_IMMEDIATE_0x69_bcd_99_plus_1_cmos(cmos_cpu: CPU) -> None:  # noqa: N802
    """Test ADC in BCD mode: 99 + 1 = 00 with carry (CMOS 65C02).

    VARIANT: 65C02 - Z and N flags are NOT set correctly in BCD mode (hardware quirk)
    """
    # given:
    cmos_cpu.A = 0x99  # BCD 99
    cmos_cpu.flags[flags.C] = 0
    cmos_cpu.flags[flags.D] = 1  # Enable decimal mode

    # ADC #$01
    cmos_cpu.ram[0xFFFC] = instructions.ADC_IMMEDIATE_0x69
    cmos_cpu.ram[0xFFFD] = 0x01  # BCD 01

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cmos_cpu.execute(cycles=2)

    # then:
    assert cmos_cpu.A == 0x00  # BCD 99 + 01 = 100, wraps to 00
    assert cmos_cpu.flags[flags.C] == 1  # Carry out
    # Note: Z flag behavior differs on CMOS 65C02 in BCD mode
    assert cmos_cpu.cycles_executed == 2


def test_cpu_instruction_ADC_IMMEDIATE_0x69_bcd_complex(cpu: CPU) -> None:  # noqa: N802
    """Test ADC in BCD mode with complex addition."""
    # given:

    cpu.A = 0x58  # BCD 58
    cpu.flags[flags.C] = 1  # Carry in
    cpu.flags[flags.D] = 1  # Enable decimal mode

    # ADC #$46
    cpu.ram[0xFFFC] = instructions.ADC_IMMEDIATE_0x69
    cpu.ram[0xFFFD] = 0x46  # BCD 46

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.A == 0x05  # BCD 58 + 46 + 1 = 105, wraps to 05
    assert cpu.flags[flags.C] == 1  # Carry out
    assert cpu.flags[flags.Z] == 0
    assert cpu.cycles_executed == 2
