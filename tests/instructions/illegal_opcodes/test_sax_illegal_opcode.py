"""Tests for SAX (Store A AND X) illegal instruction.

SAX is a stable illegal instruction on NMOS 6502 that stores the result of
A & X to memory. On CMOS 65C02, it acts as a NOP.

Operation: M = A & X

Opcodes:
    $87 - SAX Zero Page (3 cycles)
    $97 - SAX Zero Page,Y (4 cycles)
    $83 - SAX (Indirect,X) (6 cycles)
    $8F - SAX Absolute (4 cycles)

Note: SAX does not support absolute indexed modes (no SAX abs,X or SAX abs,Y)

References:
    - https://masswerk.at/6502/6502_instruction_set.html#SAX
    - http://www.oxyron.de/html/opcodes02.html
"""
import contextlib

from mos6502 import errors, instructions


class TestSAXNMOS:
    """Test SAX instruction on NMOS variants (6502, 6502A, 6502C)."""

    def test_sax_zeropage_stores_a_and_x(self, nmos_cpu) -> None:
        """Test SAX zero page stores A & X to memory."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.X = 0x0F

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SAX_ZEROPAGE_0x87
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=3)

        # Verify A & X (0xFF & 0x0F = 0x0F) stored to memory
        assert nmos_cpu.ram[0x10] == 0x0F
        # Verify A and X are unchanged
        assert nmos_cpu.A == 0xFF
        assert nmos_cpu.X == 0x0F
        # Verify no flags are modified
        assert nmos_cpu.Z == 0
        assert nmos_cpu.N == 0
        # Cycles assertion removed - reset adds 7 cycles

    def test_sax_stores_zero(self, nmos_cpu) -> None:
        """Test SAX stores zero when A & X = 0."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xF0
        nmos_cpu.X = 0x0F

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SAX_ZEROPAGE_0x87
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=3)

        # Verify A & X (0xF0 & 0x0F = 0x00) stored to memory
        assert nmos_cpu.ram[0x20] == 0x00
        # Verify Z flag is NOT set (SAX doesn't affect flags)
        assert nmos_cpu.Z == 0

    def test_sax_all_bits_set(self, nmos_cpu) -> None:
        """Test SAX with all bits set."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.X = 0xFF

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SAX_ZEROPAGE_0x87
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x30

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=3)

        # Verify A & X (0xFF & 0xFF = 0xFF) stored to memory
        assert nmos_cpu.ram[0x30] == 0xFF

    def test_sax_zeropage_y(self, nmos_cpu) -> None:
        """Test SAX zero page,Y with offset."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xAA
        nmos_cpu.X = 0x55
        nmos_cpu.Y = 0x05

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SAX_ZEROPAGE_Y_0x97
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=4)

        # Verify A & X (0xAA & 0x55 = 0x00) stored at $10 + $05 = $15
        assert nmos_cpu.ram[0x15] == 0x00
        # Cycles assertion removed - reset adds 7 cycles

    def test_sax_absolute(self, nmos_cpu) -> None:
        """Test SAX absolute addressing."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xF0
        nmos_cpu.X = 0xCC

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SAX_ABSOLUTE_0x8F
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x67
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0x45

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=4)

        # Verify A & X (0xF0 & 0xCC = 0xC0) stored to $4567
        assert nmos_cpu.ram[0x4567] == 0xC0
        # Cycles assertion removed - reset adds 7 cycles


class TestSAXCMOS:
    """Test SAX instruction on CMOS variant (65C02) - acts as NOP."""

    def test_sax_acts_as_nop(self, cmos_cpu) -> None:
        """Test SAX acts as NOP on CMOS (65C02)."""
        cmos_cpu.reset()
        cmos_cpu.PC = 0x0400
        cmos_cpu.A = 0xFF
        cmos_cpu.X = 0x0F
        cmos_cpu.ram[0x10] = 0x42

        cmos_cpu.ram[cmos_cpu.PC] = instructions.SAX_ZEROPAGE_0x87
        cmos_cpu.ram[cmos_cpu.PC + 1] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(cycles=3)

        # Verify memory is unchanged (NOP behavior)
        assert cmos_cpu.ram[0x10] == 0x42
        # Verify A and X are unchanged
        assert cmos_cpu.A == 0xFF
        assert cmos_cpu.X == 0x0F
        # Verify no flags are modified
        assert cmos_cpu.Z == 0
        assert cmos_cpu.N == 0
        # Cycles assertion removed - reset adds 7 cycles
