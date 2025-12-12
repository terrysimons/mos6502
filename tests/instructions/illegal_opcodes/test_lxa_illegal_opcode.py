"""Tests for LXA/LAX immediate (0xAB) - HIGHLY UNSTABLE illegal instruction.

LXA is a highly unstable illegal instruction on NMOS 6502.
Operation: A,X = (A | CONST) & immediate

Where CONST is chip-dependent (0xFF for 6502/6502A, 0xEE for 6502C).
On CMOS 65C02, it acts as a NOP.

WARNING: Real hardware behavior varies significantly between chips and even
with temperature. These tests verify our emulation's chosen behavior.

Opcode: $AB - LXA/LAX Immediate (2 cycles)

References:
    - http://www.oxyron.de/html/opcodes02.html
    - https://www.nesdev.org/wiki/CPU_unofficial_opcodes#Highly_unstable_opcodes
"""
import contextlib

from mos6502 import errors, instructions


class TestLXANMOS:
    """Test LXA/LAX immediate (0xAB) - HIGHLY UNSTABLE instruction."""

    def test_lxa_basic_operation(self, nmos_cpu) -> None:
        """Test LXA basic operation with CONST behavior."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x00  # Will be ORed with CONST

        nmos_cpu.ram[nmos_cpu.PC] = instructions.LAX_IMMEDIATE_0xAB
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x55

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=2

        # Result depends on CONST value (0xFF or 0xEE)
        # Both load into A and X
        assert nmos_cpu.A == nmos_cpu.X
        assert nmos_cpu.PC == 0x0402

    def test_lxa_x_matches_a(self, nmos_cpu) -> None:
        """Test LXA loads same value into both A and X."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.X = 0x00  # Should be overwritten

        nmos_cpu.ram[nmos_cpu.PC] = instructions.LAX_IMMEDIATE_0xAB
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0xAA

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        # A and X should have the same value
        assert nmos_cpu.A == nmos_cpu.X

    def test_lxa_sets_zero_flag(self, nmos_cpu) -> None:
        """Test LXA sets zero flag when result is zero."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x00

        nmos_cpu.ram[nmos_cpu.PC] = instructions.LAX_IMMEDIATE_0xAB
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x00  # AND with 0 always = 0

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        assert nmos_cpu.A == 0x00
        assert nmos_cpu.X == 0x00
        assert nmos_cpu.Z == 1

    def test_lxa_sets_negative_flag(self, nmos_cpu) -> None:
        """Test LXA sets negative flag when bit 7 is set."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF

        nmos_cpu.ram[nmos_cpu.PC] = instructions.LAX_IMMEDIATE_0xAB
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x80  # Result will have bit 7 set

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        assert nmos_cpu.A == 0x80
        assert nmos_cpu.X == 0x80
        assert nmos_cpu.N == 1

    def test_lxa_preserves_y(self, nmos_cpu) -> None:
        """Test LXA does not modify Y register."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.Y = 0x42

        nmos_cpu.ram[nmos_cpu.PC] = instructions.LAX_IMMEDIATE_0xAB
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x55

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        assert nmos_cpu.Y == 0x42


class TestLXACMOS:
    """Test LXA/LAX immediate on CMOS variant (65C02) - acts as NOP."""

    def test_lxa_acts_as_nop(self, cmos_cpu) -> None:
        """Test LXA acts as NOP on CMOS (65C02)."""
        cmos_cpu.reset()
        cmos_cpu.PC = 0x0400
        cmos_cpu.A = 0x42
        cmos_cpu.X = 0x33

        cmos_cpu.ram[cmos_cpu.PC] = instructions.LAX_IMMEDIATE_0xAB
        cmos_cpu.ram[cmos_cpu.PC + 1] = 0xFF

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(max_instructions=1)

        # Verify A and X are unchanged (NOP behavior)
        assert cmos_cpu.A == 0x42
        assert cmos_cpu.X == 0x33
        # PC advances by 2 (2-byte NOP)
        assert cmos_cpu.PC == 0x0402

    def test_lxa_nop_preserves_flags(self, cmos_cpu) -> None:
        """Test LXA NOP does not modify flags on CMOS."""
        cmos_cpu.reset()
        cmos_cpu.PC = 0x0400
        cmos_cpu.A = 0x42
        cmos_cpu.X = 0x33
        cmos_cpu.N = 1
        cmos_cpu.Z = 1

        cmos_cpu.ram[cmos_cpu.PC] = instructions.LAX_IMMEDIATE_0xAB
        cmos_cpu.ram[cmos_cpu.PC + 1] = 0x00

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(max_instructions=1)

        # Flags should be unchanged
        assert cmos_cpu.N == 1
        assert cmos_cpu.Z == 1
