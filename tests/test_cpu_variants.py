#!/usr/bin/env python3
"""Tests for CPU variant selection and behavior."""

import contextlib

import pytest

import mos6502
from mos6502 import CPUVariant, exceptions, instructions


def test_cpu_default_variant() -> None:
    """Test CPU defaults to NMOS 6502 for backward compatibility."""
    cpu: mos6502.CPU = mos6502.CPU()
    assert cpu.variant == CPUVariant.NMOS_6502
    assert cpu.variant_name == "6502"


def test_cpu_variant_from_string_6502() -> None:
    """Test CPU variant selection via string - 6502."""
    cpu: mos6502.CPU = mos6502.CPU(cpu_variant="6502")
    assert cpu.variant == CPUVariant.NMOS_6502
    assert cpu.variant_name == "6502"


def test_cpu_variant_from_string_6502a() -> None:
    """Test CPU variant selection via string - 6502A."""
    cpu: mos6502.CPU = mos6502.CPU(cpu_variant="6502A")
    assert cpu.variant == CPUVariant.NMOS_6502A
    assert cpu.variant_name == "6502A"


def test_cpu_variant_from_string_6502c() -> None:
    """Test CPU variant selection via string - 6502C."""
    cpu: mos6502.CPU = mos6502.CPU(cpu_variant="6502C")
    assert cpu.variant == CPUVariant.NMOS_6502C
    assert cpu.variant_name == "6502C"


def test_cpu_variant_from_string_65c02() -> None:
    """Test CPU variant selection via string - 65C02."""
    cpu: mos6502.CPU = mos6502.CPU(cpu_variant="65C02")
    assert cpu.variant == CPUVariant.CMOS_65C02
    assert cpu.variant_name == "65C02"


def test_cpu_variant_from_enum() -> None:
    """Test CPU variant selection via enum."""
    cpu: mos6502.CPU = mos6502.CPU(cpu_variant=CPUVariant.CMOS_65C02)
    assert cpu.variant == CPUVariant.CMOS_65C02
    assert cpu.variant_name == "65C02"


def test_cpu_invalid_variant_string() -> None:
    """Test error handling for invalid variant."""
    with pytest.raises(ValueError, match="Unknown CPU variant"):
        mos6502.CPU(cpu_variant="6800")  # Wrong CPU family!


def test_nop_dispatch_6502() -> None:
    """Test NOP instruction works with 6502 variant."""
    cpu: mos6502.CPU = mos6502.CPU(cpu_variant="6502")
    cpu.reset()

    cpu.ram[0xFFFC] = instructions.NOP_IMPLIED_0xEA

    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    assert cpu.PC == 0xFFFD
    assert cpu.cycles_executed == 2


def test_nop_dispatch_65c02() -> None:
    """Test NOP instruction works with 65C02 variant."""
    cpu: mos6502.CPU = mos6502.CPU(cpu_variant="65C02")
    cpu.reset()

    cpu.ram[0xFFFC] = instructions.NOP_IMPLIED_0xEA

    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    assert cpu.PC == 0xFFFD
    assert cpu.cycles_executed == 2
