"""Tests for LAX (Load A and X) illegal instruction.

LAX is a stable illegal instruction on NMOS 6502 that loads memory into both
the A and X registers simultaneously. On CMOS 65C02, it acts as a NOP.

Operation: A,X = M

This is functionally equivalent to:
    LDA {operand}
    LDX {operand}
but executes in a single instruction.

Opcodes:
    $A7 - LAX Zero Page (3 cycles)
    $B7 - LAX Zero Page,Y (4 cycles)
    $A3 - LAX (Indirect,X) (6 cycles)
    $B3 - LAX (Indirect),Y (5* cycles)
    $AF - LAX Absolute (4 cycles)
    $BF - LAX Absolute,Y (4* cycles)
    $AB - LAX Immediate (2 cycles) **UNSTABLE - NOT TESTED**

References:
    - https://masswerk.at/6502/6502_instruction_set.html#LAX
    - http://www.oxyron.de/html/opcodes02.html
"""
import contextlib

from mos6502 import errors, instructions


class TestLAXNMOS:
    """Test LAX instruction on NMOS variants (6502, 6502A, 6502C)."""

    def test_lax_zeropage_loads_value_into_both_registers(self, nmos_cpu) -> None:
        """Test LAX zero page loads memory into both A and X."""
        nmos_cpu.reset()
        nmos_cpu.ram[0x10] = 0x42

        nmos_cpu.ram[0xFFFC] = instructions.LAX_ZEROPAGE_0xA7
        nmos_cpu.ram[0xFFFD] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=3)

        assert nmos_cpu.A == 0x42
        assert nmos_cpu.X == 0x42
        assert nmos_cpu.Z == 0
        assert nmos_cpu.N == 0
        assert nmos_cpu.cycles_executed == 3

    def test_lax_sets_zero_flag(self, nmos_cpu) -> None:
        """Test LAX sets zero flag when loading zero value."""
        nmos_cpu.reset()
        nmos_cpu.ram[0x20] = 0x00

        nmos_cpu.ram[0xFFFC] = instructions.LAX_ZEROPAGE_0xA7
        nmos_cpu.ram[0xFFFD] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=3)

        assert nmos_cpu.A == 0x00
        assert nmos_cpu.X == 0x00
        assert nmos_cpu.Z == 1
        assert nmos_cpu.cycles_executed == 3

    def test_lax_sets_negative_flag(self, nmos_cpu) -> None:
        """Test LAX sets negative flag when bit 7 is set."""
        nmos_cpu.reset()
        nmos_cpu.ram[0x30] = 0xFF

        nmos_cpu.ram[0xFFFC] = instructions.LAX_ZEROPAGE_0xA7
        nmos_cpu.ram[0xFFFD] = 0x30

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=3)

        assert nmos_cpu.A == 0xFF
        assert nmos_cpu.X == 0xFF
        assert nmos_cpu.N == 1
        assert nmos_cpu.cycles_executed == 3

    def test_lax_absolute(self, nmos_cpu) -> None:
        """Test LAX absolute addressing."""
        nmos_cpu.reset()
        nmos_cpu.ram[0x4567] = 0x77

        nmos_cpu.ram[0xFFFC] = instructions.LAX_ABSOLUTE_0xAF
        nmos_cpu.ram[0xFFFD] = 0x67
        nmos_cpu.ram[0xFFFE] = 0x45

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=4)

        assert nmos_cpu.A == 0x77
        assert nmos_cpu.X == 0x77
        assert nmos_cpu.cycles_executed == 4

    def test_lax_zeropage_y(self, nmos_cpu) -> None:
        """Test LAX zero page,Y with offset."""
        nmos_cpu.reset()
        nmos_cpu.Y = 0x05
        nmos_cpu.ram[0x15] = 0x55  # Base $10 + Y $05 = $15

        nmos_cpu.ram[0xFFFC] = instructions.LAX_ZEROPAGE_Y_0xB7
        nmos_cpu.ram[0xFFFD] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=4)

        assert nmos_cpu.A == 0x55
        assert nmos_cpu.X == 0x55
        assert nmos_cpu.cycles_executed == 4


class TestLAXCMOS:
    """Test LAX instruction on CMOS variant (65C02) - acts as NOP."""

    def test_lax_acts_as_nop(self, cmos_cpu) -> None:
        """Test LAX acts as NOP on CMOS (65C02)."""
        cmos_cpu.reset()
        cmos_cpu.A = 0x11
        cmos_cpu.X = 0x22
        cmos_cpu.ram[0x10] = 0x42

        cmos_cpu.ram[0xFFFC] = instructions.LAX_ZEROPAGE_0xA7
        cmos_cpu.ram[0xFFFD] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(cycles=3)

        # Verify A and X are unchanged (NOP behavior)
        assert cmos_cpu.A == 0x11
        assert cmos_cpu.X == 0x22
        # Verify no flags are modified
        assert cmos_cpu.Z == 0
        assert cmos_cpu.N == 0
        assert cmos_cpu.cycles_executed == 3
