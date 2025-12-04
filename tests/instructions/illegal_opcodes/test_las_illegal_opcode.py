"""Tests for LAS (Load A, X, and S) illegal instruction.

LAS is an unstable illegal instruction on NMOS 6502 that loads (M & S) into
A, X, and S. On CMOS 65C02, it acts as a NOP.

Operation: A, X, S = M & S

Opcodes:
    $BB - LAS Absolute,Y (4* cycles)

Flags: N, Z

WARNING: This is an unstable instruction with unpredictable behavior.

References:
    - https://masswerk.at/6502/6502_instruction_set.html#LAS
    - http://www.oxyron.de/html/opcodes02.html
"""
import contextlib

from mos6502 import errors, instructions


class TestLASNMOS:
    """Test LAS instruction on NMOS variants (6502, 6502A, 6502C)."""

    def test_las_loads_and_result(self, nmos_cpu) -> None:
        """Test LAS loads (M & S) into A, X, and S."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.S = 0xFF
        nmos_cpu.Y = 0x10
        nmos_cpu.ram[0x1234 + 0x10] = 0xAA

        nmos_cpu.ram[nmos_cpu.PC] = instructions.LAS_ABSOLUTE_Y_0xBB
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x34
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0x12

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=4)

        # Verify: M & S = 0xAA & 0xFF = 0xAA
        # S register is 8-bit, compare low byte only (high byte hardwired to 0x01)
        assert nmos_cpu.A == 0xAA
        assert nmos_cpu.X == 0xAA
        assert (nmos_cpu.S & 0xFF) == 0xAA
        assert nmos_cpu.Z == 0
        assert nmos_cpu.N == 1

    def test_las_with_partial_and(self, nmos_cpu) -> None:
        """Test LAS with partial AND result."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.S = 0x0F
        nmos_cpu.Y = 0x00
        nmos_cpu.ram[0x1000] = 0xFF

        nmos_cpu.ram[nmos_cpu.PC] = instructions.LAS_ABSOLUTE_Y_0xBB
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x00
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=4)

        # Verify: M & S = 0xFF & 0x0F = 0x0F
        # S register is 8-bit, compare low byte only (high byte hardwired to 0x01)
        assert nmos_cpu.A == 0x0F
        assert nmos_cpu.X == 0x0F
        assert (nmos_cpu.S & 0xFF) == 0x0F

    def test_las_sets_zero_flag(self, nmos_cpu) -> None:
        """Test LAS sets zero flag when result is zero."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.S = 0x00
        nmos_cpu.Y = 0x00
        nmos_cpu.ram[0x2000] = 0xFF

        nmos_cpu.ram[nmos_cpu.PC] = instructions.LAS_ABSOLUTE_Y_0xBB
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x00
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=4)

        # Verify: M & S = 0xFF & 0x00 = 0x00
        # S register is 8-bit, compare low byte only (high byte hardwired to 0x01)
        assert nmos_cpu.A == 0x00
        assert nmos_cpu.X == 0x00
        assert (nmos_cpu.S & 0xFF) == 0x00
        assert nmos_cpu.Z == 1
        assert nmos_cpu.N == 0


class TestLASCMOS:
    """Test LAS instruction on CMOS variant (65C02) - acts as NOP."""

    def test_las_acts_as_nop(self, cmos_cpu) -> None:
        """Test LAS acts as NOP on CMOS (65C02)."""
        cmos_cpu.reset()
        cmos_cpu.PC = 0x0400
        cmos_cpu.A = 0x11
        cmos_cpu.X = 0x22
        cmos_cpu.S = 0xFF
        cmos_cpu.Y = 0x10
        cmos_cpu.ram[0x1244] = 0xAA

        cmos_cpu.ram[cmos_cpu.PC] = instructions.LAS_ABSOLUTE_Y_0xBB
        cmos_cpu.ram[cmos_cpu.PC + 1] = 0x34
        cmos_cpu.ram[cmos_cpu.PC + 2] = 0x12

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(cycles=4)

        # Verify nothing changed (NOP behavior)
        # S register is 8-bit, compare low byte only (high byte hardwired to 0x01)
        assert cmos_cpu.A == 0x11
        assert cmos_cpu.X == 0x22
        assert (cmos_cpu.S & 0xFF) == 0xFF
        assert cmos_cpu.Z == 0
        assert cmos_cpu.N == 0
