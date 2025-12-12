"""Tests for ALR (AND then LSR) illegal instruction.

ALR is a stable illegal instruction on NMOS 6502 that performs AND with
the immediate value, then logical shifts right.
On CMOS 65C02, it acts as a NOP.

Operation: A = (A & immediate) >> 1

Opcode: $4B - ALR Immediate (2 cycles)

References:
    - http://www.oxyron.de/html/opcodes02.html
    - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""
import contextlib

from mos6502 import errors, instructions


class TestALRNMOS:
    """Test ALR instruction on NMOS variants (6502, 6502A, 6502C)."""

    def test_alr_and_then_shift(self, nmos_cpu) -> None:
        """Test ALR performs AND then LSR."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF

        nmos_cpu.ram[nmos_cpu.PC] = instructions.ALR_IMMEDIATE_0x4B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x0F

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=2

        # Verify AND then shift: (0xFF & 0x0F) >> 1 = 0x0F >> 1 = 0x07
        assert nmos_cpu.A == 0x07
        assert nmos_cpu.Z == 0
        assert nmos_cpu.N == 0  # Always 0 after LSR
        assert nmos_cpu.C == 1  # Bit 0 of 0x0F was 1

    def test_alr_sets_carry_from_bit0(self, nmos_cpu) -> None:
        """Test ALR sets carry from bit 0 of AND result."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xAA

        nmos_cpu.ram[nmos_cpu.PC] = instructions.ALR_IMMEDIATE_0x4B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x55

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=2

        # Verify: (0xAA & 0x55) >> 1 = 0x00 >> 1 = 0x00
        assert nmos_cpu.A == 0x00
        assert nmos_cpu.Z == 1
        assert nmos_cpu.C == 0  # Bit 0 of 0x00 was 0

    def test_alr_zero_result_sets_carry(self, nmos_cpu) -> None:
        """Test ALR sets zero flag and carry when shifting 1."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x01

        nmos_cpu.ram[nmos_cpu.PC] = instructions.ALR_IMMEDIATE_0x4B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x01

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=2

        # Verify: (0x01 & 0x01) >> 1 = 0x01 >> 1 = 0x00
        assert nmos_cpu.A == 0x00
        assert nmos_cpu.Z == 1
        assert nmos_cpu.C == 1  # Bit 0 of 0x01 was 1

    def test_alr_high_value(self, nmos_cpu) -> None:
        """Test ALR with high byte value."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF

        nmos_cpu.ram[nmos_cpu.PC] = instructions.ALR_IMMEDIATE_0x4B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0xFE  # Even number, bit 0 = 0

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        # Verify: (0xFF & 0xFE) >> 1 = 0xFE >> 1 = 0x7F
        assert nmos_cpu.A == 0x7F
        assert nmos_cpu.Z == 0
        assert nmos_cpu.N == 0  # LSR always clears N
        assert nmos_cpu.C == 0  # Bit 0 of 0xFE was 0


class TestALRCMOS:
    """Test ALR instruction on CMOS variant (65C02) - acts as NOP."""

    def test_alr_acts_as_nop(self, cmos_cpu) -> None:
        """Test ALR acts as NOP on CMOS."""
        cmos_cpu.reset()
        cmos_cpu.PC = 0x0400
        cmos_cpu.A = 0xFF
        cmos_cpu.C = 0

        cmos_cpu.ram[cmos_cpu.PC] = instructions.ALR_IMMEDIATE_0x4B
        cmos_cpu.ram[cmos_cpu.PC + 1] = 0x0F

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(max_instructions=1)

        # Verify A unchanged (NOP behavior)
        assert cmos_cpu.A == 0xFF
        assert cmos_cpu.C == 0
        # PC advances by 2
        assert cmos_cpu.PC == 0x0402
