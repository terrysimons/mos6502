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


def test_brk_d_flag_preserved_nmos_6502() -> None:
    """Test BRK preserves D flag on NMOS 6502 variant.

    VARIANT: 6502 - D (decimal) flag is NOT cleared by BRK
    Reference: https://masswerk.at/6502/6502_instruction_set.html#BRK
    """
    from mos6502 import flags

    cpu: mos6502.CPU = mos6502.CPU(cpu_variant="6502")
    cpu.reset()

    # Set D flag before BRK
    cpu.D = flags.ProcessorStatusFlags.D[flags.D]
    assert cpu.D, "D flag should be set initially"

    cpu.ram[0xFFFC] = instructions.BRK_IMPLIED_0x00
    cpu.ram[0xFFFD] = 0x00

    with contextlib.suppress(exceptions.CPUCycleExhaustionError, exceptions.CPUBreakError):
        cpu.execute(cycles=7)

    # NMOS 6502: D flag should still be set (preserved)
    assert cpu.D, "D flag should be preserved (not cleared) on NMOS 6502"
    # I flag should be set
    assert cpu.I, "I flag should be set after BRK"


def test_brk_d_flag_preserved_nmos_6502a() -> None:
    """Test BRK preserves D flag on NMOS 6502A variant.

    VARIANT: 6502A - D (decimal) flag is NOT cleared by BRK
    Reference: https://masswerk.at/6502/6502_instruction_set.html#BRK
    """
    from mos6502 import flags

    cpu: mos6502.CPU = mos6502.CPU(cpu_variant="6502A")
    cpu.reset()

    # Set D flag before BRK
    cpu.D = flags.ProcessorStatusFlags.D[flags.D]
    assert cpu.D, "D flag should be set initially"

    cpu.ram[0xFFFC] = instructions.BRK_IMPLIED_0x00
    cpu.ram[0xFFFD] = 0x00

    with contextlib.suppress(exceptions.CPUCycleExhaustionError, exceptions.CPUBreakError):
        cpu.execute(cycles=7)

    # NMOS 6502A: D flag should still be set (preserved)
    assert cpu.D, "D flag should be preserved (not cleared) on NMOS 6502A"
    # I flag should be set
    assert cpu.I, "I flag should be set after BRK"


def test_brk_d_flag_preserved_nmos_6502c() -> None:
    """Test BRK preserves D flag on NMOS 6502C variant.

    VARIANT: 6502C - D (decimal) flag is NOT cleared by BRK
    Reference: https://masswerk.at/6502/6502_instruction_set.html#BRK
    """
    from mos6502 import flags

    cpu: mos6502.CPU = mos6502.CPU(cpu_variant="6502C")
    cpu.reset()

    # Set D flag before BRK
    cpu.D = flags.ProcessorStatusFlags.D[flags.D]
    assert cpu.D, "D flag should be set initially"

    cpu.ram[0xFFFC] = instructions.BRK_IMPLIED_0x00
    cpu.ram[0xFFFD] = 0x00

    with contextlib.suppress(exceptions.CPUCycleExhaustionError, exceptions.CPUBreakError):
        cpu.execute(cycles=7)

    # NMOS 6502C: D flag should still be set (preserved)
    assert cpu.D, "D flag should be preserved (not cleared) on NMOS 6502C"
    # I flag should be set
    assert cpu.I, "I flag should be set after BRK"


def test_brk_d_flag_cleared_cmos_65c02() -> None:
    """Test BRK clears D flag on CMOS 65C02 variant.

    VARIANT: 65C02 - D (decimal) flag IS cleared by BRK and all interrupts
    This is the key difference from NMOS variants.
    Reference: https://masswerk.at/6502/6502_instruction_set.html#BRK
    """
    from mos6502 import flags

    cpu: mos6502.CPU = mos6502.CPU(cpu_variant="65C02")
    cpu.reset()

    # Set D flag before BRK
    cpu.D = flags.ProcessorStatusFlags.D[flags.D]
    assert cpu.D, "D flag should be set initially"

    cpu.ram[0xFFFC] = instructions.BRK_IMPLIED_0x00
    cpu.ram[0xFFFD] = 0x00

    with contextlib.suppress(exceptions.CPUCycleExhaustionError, exceptions.CPUBreakError):
        cpu.execute(cycles=7)

    # CMOS 65C02: D flag should be cleared
    assert not cpu.D, "D flag should be cleared on CMOS 65C02"
    # I flag should be set
    assert cpu.I, "I flag should be set after BRK"
