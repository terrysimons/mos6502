"""Tests for ARR (AND then ROR) illegal instruction.

ARR is a stable illegal instruction on NMOS 6502 that performs AND with
the immediate value, then rotates right through carry. It has special
flag behavior different from normal ROR.
On CMOS 65C02, it acts as a NOP.

Operation: A = (A & immediate) ROR 1
Flags: C = bit 6 of result, V = bit 6 XOR bit 5 of result

Opcode: $6B - ARR Immediate (2 cycles)

References:
    - http://www.oxyron.de/html/opcodes02.html
    - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""
import contextlib

from mos6502 import errors, instructions


class TestARRNMOS:
    """Test ARR instruction on NMOS variants (6502, 6502A, 6502C)."""

    def test_arr_and_then_rotate(self, nmos_cpu) -> None:
        """Test ARR performs AND then ROR."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x7F
        nmos_cpu.C = 1

        nmos_cpu.ram[nmos_cpu.PC] = instructions.ARR_IMMEDIATE_0x6B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0xFF

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=2

        # Verify: (0x7F & 0xFF) ROR with C=1 = 0x7F ROR = 0xBF
        assert nmos_cpu.A == 0xBF
        assert nmos_cpu.Z == 0
        assert nmos_cpu.N == 1

    def test_arr_carry_from_bit6(self, nmos_cpu) -> None:
        """Test ARR sets carry from bit 6 of result."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.C = 0

        nmos_cpu.ram[nmos_cpu.PC] = instructions.ARR_IMMEDIATE_0x6B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0xFF

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=2

        # Verify: (0xFF & 0xFF) ROR with C=0 = 0xFF ROR = 0x7F
        assert nmos_cpu.A == 0x7F
        # C is set from bit 6 of result (0x7F = 01111111, bit 6 = 1)
        assert nmos_cpu.C == 1

    def test_arr_overflow_cleared(self, nmos_cpu) -> None:
        """Test ARR clears overflow when bit 6 XOR bit 5 = 0."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.C = 0

        nmos_cpu.ram[nmos_cpu.PC] = instructions.ARR_IMMEDIATE_0x6B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0xC0  # 11000000

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=2

        # Verify: (0xFF & 0xC0) ROR with C=0 = 0xC0 ROR = 0x60
        assert nmos_cpu.A == 0x60  # 01100000
        # bit 6 = 1, bit 5 = 1, V = 1 XOR 1 = 0
        assert nmos_cpu.V == 0

    def test_arr_overflow_set(self, nmos_cpu) -> None:
        """Test ARR sets overflow when bit 6 XOR bit 5 = 1."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.C = 1

        nmos_cpu.ram[nmos_cpu.PC] = instructions.ARR_IMMEDIATE_0x6B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x40  # 01000000

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=2

        # Verify: (0xFF & 0x40) ROR with C=1 = 0x40 ROR = 0xA0
        assert nmos_cpu.A == 0xA0  # 10100000
        # bit 6 = 0, bit 5 = 1, V = 0 XOR 1 = 1
        assert nmos_cpu.V == 1

    def test_arr_zero_result(self, nmos_cpu) -> None:
        """Test ARR with zero result."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xAA
        nmos_cpu.C = 0

        nmos_cpu.ram[nmos_cpu.PC] = instructions.ARR_IMMEDIATE_0x6B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x00

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        # Verify: (0xAA & 0x00) ROR with C=0 = 0x00 ROR = 0x00
        assert nmos_cpu.A == 0x00
        assert nmos_cpu.Z == 1
        assert nmos_cpu.C == 0  # Bit 6 of 0x00 is 0


class TestARRCMOS:
    """Test ARR instruction on CMOS variant (65C02) - acts as NOP."""

    def test_arr_acts_as_nop(self, cmos_cpu) -> None:
        """Test ARR acts as NOP on CMOS."""
        cmos_cpu.reset()
        cmos_cpu.PC = 0x0400
        cmos_cpu.A = 0x7F
        cmos_cpu.C = 1

        cmos_cpu.ram[cmos_cpu.PC] = instructions.ARR_IMMEDIATE_0x6B
        cmos_cpu.ram[cmos_cpu.PC + 1] = 0xFF

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(max_instructions=1)

        # Verify A and C unchanged (NOP behavior)
        assert cmos_cpu.A == 0x7F
        assert cmos_cpu.C == 1
        # PC advances by 2
        assert cmos_cpu.PC == 0x0402
