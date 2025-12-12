"""Tests for ANC (AND with Carry) illegal instruction - opcode 0x0B.

ANC is a stable illegal instruction on NMOS 6502 that performs AND with
the immediate value, then copies bit 7 to the carry flag.
On CMOS 65C02, it acts as a NOP.

Operation: A = A & immediate, C = N

Opcode: $0B - ANC Immediate (2 cycles)

References:
    - http://www.oxyron.de/html/opcodes02.html
    - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""
import contextlib

from mos6502 import errors, instructions


class TestANCNMOS:
    """Test ANC instruction on NMOS variants (6502, 6502A, 6502C)."""

    def test_anc_and_operation(self, nmos_cpu) -> None:
        """Test ANC performs AND operation."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xF0
        nmos_cpu.C = 0

        nmos_cpu.ram[nmos_cpu.PC] = instructions.ANC_IMMEDIATE_0x0B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x0F

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=2

        # Verify AND: A = 0xF0 & 0x0F = 0x00
        assert nmos_cpu.A == 0x00
        assert nmos_cpu.Z == 1
        assert nmos_cpu.N == 0
        # C should match N (both 0)
        assert nmos_cpu.C == 0

    def test_anc_sets_carry_when_negative(self, nmos_cpu) -> None:
        """Test ANC sets carry to match negative flag."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.C = 0

        nmos_cpu.ram[nmos_cpu.PC] = instructions.ANC_IMMEDIATE_0x0B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x80

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=2

        # Verify AND: A = 0xFF & 0x80 = 0x80
        assert nmos_cpu.A == 0x80
        assert nmos_cpu.Z == 0
        assert nmos_cpu.N == 1
        # C should match N (both 1)
        assert nmos_cpu.C == 1

    def test_anc_clears_carry_when_positive(self, nmos_cpu) -> None:
        """Test ANC clears carry when result is positive."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.C = 1  # Pre-set

        nmos_cpu.ram[nmos_cpu.PC] = instructions.ANC_IMMEDIATE_0x0B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x7F

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        # Verify AND: A = 0xFF & 0x7F = 0x7F
        assert nmos_cpu.A == 0x7F
        assert nmos_cpu.N == 0
        assert nmos_cpu.C == 0  # Cleared because N=0


class TestANCCMOS:
    """Test ANC instruction on CMOS variant (65C02) - acts as NOP."""

    def test_anc_acts_as_nop(self, cmos_cpu) -> None:
        """Test ANC acts as NOP on CMOS."""
        cmos_cpu.reset()
        cmos_cpu.PC = 0x0400
        cmos_cpu.A = 0xF0
        cmos_cpu.C = 0

        cmos_cpu.ram[cmos_cpu.PC] = instructions.ANC_IMMEDIATE_0x0B
        cmos_cpu.ram[cmos_cpu.PC + 1] = 0x0F

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(max_instructions=1)

        # Verify A unchanged (NOP behavior)
        assert cmos_cpu.A == 0xF0
        assert cmos_cpu.C == 0
        # PC advances by 2
        assert cmos_cpu.PC == 0x0402
