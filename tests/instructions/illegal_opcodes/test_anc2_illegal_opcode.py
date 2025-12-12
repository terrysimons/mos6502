"""Tests for ANC2 (AND with Carry) illegal instruction - opcode 0x2B.

ANC2 is identical to ANC (0x0B). It's a duplicate opcode that performs
AND with the immediate value, then copies bit 7 to the carry flag.
On CMOS 65C02, it acts as a NOP.

Operation: A = A & immediate, C = N

Opcode: $2B - ANC Immediate (2 cycles)

References:
    - http://www.oxyron.de/html/opcodes02.html
    - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""
import contextlib

from mos6502 import errors, instructions


class TestANC2NMOS:
    """Test ANC2 instruction on NMOS variants (6502, 6502A, 6502C)."""

    def test_anc2_and_operation(self, nmos_cpu) -> None:
        """Test ANC2 performs AND operation identically to ANC."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xAA
        nmos_cpu.C = 0

        nmos_cpu.ram[nmos_cpu.PC] = instructions.ANC_IMMEDIATE_0x2B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x55

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=2

        # Verify AND: A = 0xAA & 0x55 = 0x00
        assert nmos_cpu.A == 0x00
        assert nmos_cpu.Z == 1
        assert nmos_cpu.N == 0
        assert nmos_cpu.C == 0  # Matches N

    def test_anc2_sets_carry_from_bit7(self, nmos_cpu) -> None:
        """Test ANC2 sets carry from bit 7 of result."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.C = 0

        nmos_cpu.ram[nmos_cpu.PC] = instructions.ANC_IMMEDIATE_0x2B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0xC0

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        # Verify AND: A = 0xFF & 0xC0 = 0xC0
        assert nmos_cpu.A == 0xC0
        assert nmos_cpu.N == 1
        assert nmos_cpu.C == 1  # Matches N

    def test_anc2_non_zero_result(self, nmos_cpu) -> None:
        """Test ANC2 with non-zero positive result."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x33
        nmos_cpu.C = 1  # Pre-set

        nmos_cpu.ram[nmos_cpu.PC] = instructions.ANC_IMMEDIATE_0x2B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x0F

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        # Verify AND: A = 0x33 & 0x0F = 0x03
        assert nmos_cpu.A == 0x03
        assert nmos_cpu.Z == 0
        assert nmos_cpu.N == 0
        assert nmos_cpu.C == 0  # Cleared because N=0


class TestANC2CMOS:
    """Test ANC2 instruction on CMOS variant (65C02) - acts as NOP."""

    def test_anc2_acts_as_nop(self, cmos_cpu) -> None:
        """Test ANC2 acts as NOP on CMOS."""
        cmos_cpu.reset()
        cmos_cpu.PC = 0x0400
        cmos_cpu.A = 0xAA
        cmos_cpu.C = 1

        cmos_cpu.ram[cmos_cpu.PC] = instructions.ANC_IMMEDIATE_0x2B
        cmos_cpu.ram[cmos_cpu.PC + 1] = 0x55

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(max_instructions=1)

        # Verify A and C unchanged (NOP behavior)
        assert cmos_cpu.A == 0xAA
        assert cmos_cpu.C == 1
        # PC advances by 2
        assert cmos_cpu.PC == 0x0402
