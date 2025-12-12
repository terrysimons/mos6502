"""Tests for SBX (Subtract from X) illegal instruction.

SBX is a stable illegal instruction on NMOS 6502 that performs (A & X) - immediate
and stores the result in X. It uses CMP-style subtraction (ignores carry input).
On CMOS 65C02, it acts as a NOP.

Operation: X = (A & X) - immediate

Opcode: $CB - SBX Immediate (2 cycles)

References:
    - http://www.oxyron.de/html/opcodes02.html
    - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""
import contextlib

from mos6502 import errors, instructions


class TestSBXNMOS:
    """Test SBX instruction on NMOS variants (6502, 6502A, 6502C)."""

    def test_sbx_basic_subtract(self, nmos_cpu) -> None:
        """Test SBX performs (A & X) - immediate."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.X = 0xFF

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SBX_IMMEDIATE_0xCB
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x0F

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=2

        # Verify: (0xFF & 0xFF) - 0x0F = 0xFF - 0x0F = 0xF0
        assert nmos_cpu.X == 0xF0
        assert nmos_cpu.Z == 0
        assert nmos_cpu.N == 1
        assert nmos_cpu.C == 1  # No borrow (result >= 0)

    def test_sbx_with_borrow(self, nmos_cpu) -> None:
        """Test SBX clears carry when result is negative (borrow)."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x0F
        nmos_cpu.X = 0x0F

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SBX_IMMEDIATE_0xCB
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0xFF

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=2

        # Verify: (0x0F & 0x0F) - 0xFF = 0x0F - 0xFF = -240 = 0x10 (wrapped)
        assert nmos_cpu.X == 0x10
        assert nmos_cpu.C == 0  # Borrow occurred

    def test_sbx_zero_result(self, nmos_cpu) -> None:
        """Test SBX sets zero flag when result is zero."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.X = 0xFF

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SBX_IMMEDIATE_0xCB
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0xFF

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=2

        # Verify: (0xFF & 0xFF) - 0xFF = 0xFF - 0xFF = 0x00
        assert nmos_cpu.X == 0x00
        assert nmos_cpu.Z == 1
        assert nmos_cpu.N == 0
        assert nmos_cpu.C == 1  # No borrow

    def test_sbx_and_operation(self, nmos_cpu) -> None:
        """Test SBX properly ANDs A with X before subtraction."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xAA  # 10101010
        nmos_cpu.X = 0x55  # 01010101

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SBX_IMMEDIATE_0xCB
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x00

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=2

        # Verify: (0xAA & 0x55) - 0x00 = 0x00 - 0x00 = 0x00
        assert nmos_cpu.X == 0x00
        assert nmos_cpu.Z == 1

    def test_sbx_preserves_a(self, nmos_cpu) -> None:
        """Test SBX does not modify A register."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x42
        nmos_cpu.X = 0xFF

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SBX_IMMEDIATE_0xCB
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        # A should be unchanged
        assert nmos_cpu.A == 0x42


class TestSBXCMOS:
    """Test SBX instruction on CMOS variant (65C02) - acts as NOP."""

    def test_sbx_acts_as_nop(self, cmos_cpu) -> None:
        """Test SBX acts as NOP on CMOS."""
        cmos_cpu.reset()
        cmos_cpu.PC = 0x0400
        cmos_cpu.A = 0xFF
        cmos_cpu.X = 0xFF

        cmos_cpu.ram[cmos_cpu.PC] = instructions.SBX_IMMEDIATE_0xCB
        cmos_cpu.ram[cmos_cpu.PC + 1] = 0x0F

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(max_instructions=1)

        # Verify X unchanged (NOP behavior)
        assert cmos_cpu.X == 0xFF
        # PC advances by 2
        assert cmos_cpu.PC == 0x0402
