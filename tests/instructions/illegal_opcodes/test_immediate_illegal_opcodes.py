"""Tests for immediate mode illegal instructions (ANC, ALR, ARR, SBX).

These are stable illegal instructions on NMOS 6502 that only have immediate
addressing modes. On CMOS 65C02, they act as NOPs.

Instructions:
- ANC: AND with Carry (opcodes $0B, $2B)
- ALR: AND then Logical Shift Right (opcode $4B)
- ARR: AND then Rotate Right (opcode $6B)
- SBX: Subtract from X (opcode $CB)

References:
    - https://masswerk.at/6502/6502_instruction_set.html
    - http://www.oxyron.de/html/opcodes02.html
"""
import contextlib

from mos6502 import errors, instructions


class TestANCNMOS:
    """Test ANC instruction on NMOS variants (6502, 6502A, 6502C)."""

    def test_anc_and_operation(self, nmos_cpu):
        """Test ANC performs AND operation."""
        nmos_cpu.reset()
        nmos_cpu.A = 0xF0
        nmos_cpu.C = 0

        nmos_cpu.ram[0xFFFC] = instructions.ANC_IMMEDIATE_0x0B
        nmos_cpu.ram[0xFFFD] = 0x0F

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=2)

        # Verify AND: A = 0xF0 & 0x0F = 0x00
        assert nmos_cpu.A == 0x00
        assert nmos_cpu.Z == 1
        assert nmos_cpu.N == 0
        # C should match N (both 0)
        assert nmos_cpu.C == 0

    def test_anc_sets_carry_when_negative(self, nmos_cpu):
        """Test ANC sets carry to match negative flag."""
        nmos_cpu.reset()
        nmos_cpu.A = 0xFF
        nmos_cpu.C = 0

        nmos_cpu.ram[0xFFFC] = instructions.ANC_IMMEDIATE_0x0B
        nmos_cpu.ram[0xFFFD] = 0x80

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=2)

        # Verify AND: A = 0xFF & 0x80 = 0x80
        assert nmos_cpu.A == 0x80
        assert nmos_cpu.Z == 0
        assert nmos_cpu.N == 1
        # C should match N (both 1)
        assert nmos_cpu.C == 1

    def test_anc_duplicate_opcode(self, nmos_cpu):
        """Test ANC duplicate opcode $2B works identically."""
        nmos_cpu.reset()
        nmos_cpu.A = 0xAA
        nmos_cpu.C = 0

        nmos_cpu.ram[0xFFFC] = instructions.ANC_IMMEDIATE_0x2B
        nmos_cpu.ram[0xFFFD] = 0x55

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=2)

        # Verify AND: A = 0xAA & 0x55 = 0x00
        assert nmos_cpu.A == 0x00
        assert nmos_cpu.C == 0  # Matches N


class TestALRNMOS:
    """Test ALR instruction on NMOS variants (6502, 6502A, 6502C)."""

    def test_alr_and_then_shift(self, nmos_cpu):
        """Test ALR performs AND then LSR."""
        nmos_cpu.reset()
        nmos_cpu.A = 0xFF

        nmos_cpu.ram[0xFFFC] = instructions.ALR_IMMEDIATE_0x4B
        nmos_cpu.ram[0xFFFD] = 0x0F

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=2)

        # Verify AND then shift: (0xFF & 0x0F) >> 1 = 0x0F >> 1 = 0x07
        assert nmos_cpu.A == 0x07
        assert nmos_cpu.Z == 0
        assert nmos_cpu.N == 0  # Always 0 after LSR
        assert nmos_cpu.C == 1  # Bit 0 of 0x0F was 1

    def test_alr_sets_carry(self, nmos_cpu):
        """Test ALR sets carry from bit 0 of AND result."""
        nmos_cpu.reset()
        nmos_cpu.A = 0xAA

        nmos_cpu.ram[0xFFFC] = instructions.ALR_IMMEDIATE_0x4B
        nmos_cpu.ram[0xFFFD] = 0x55

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=2)

        # Verify: (0xAA & 0x55) >> 1 = 0x00 >> 1 = 0x00
        assert nmos_cpu.A == 0x00
        assert nmos_cpu.Z == 1
        assert nmos_cpu.C == 0  # Bit 0 of 0x00 was 0

    def test_alr_result_zero(self, nmos_cpu):
        """Test ALR sets zero flag when result is zero."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x01

        nmos_cpu.ram[0xFFFC] = instructions.ALR_IMMEDIATE_0x4B
        nmos_cpu.ram[0xFFFD] = 0x01

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=2)

        # Verify: (0x01 & 0x01) >> 1 = 0x01 >> 1 = 0x00
        assert nmos_cpu.A == 0x00
        assert nmos_cpu.Z == 1
        assert nmos_cpu.C == 1  # Bit 0 of 0x01 was 1


class TestARRNMOS:
    """Test ARR instruction on NMOS variants (6502, 6502A, 6502C)."""

    def test_arr_and_then_rotate(self, nmos_cpu):
        """Test ARR performs AND then ROR."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x7F
        nmos_cpu.C = 1

        nmos_cpu.ram[0xFFFC] = instructions.ARR_IMMEDIATE_0x6B
        nmos_cpu.ram[0xFFFD] = 0xFF

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=2)

        # Verify: (0x7F & 0xFF) ROR with C=1 = 0x7F ROR = 0xBF
        assert nmos_cpu.A == 0xBF
        assert nmos_cpu.Z == 0
        assert nmos_cpu.N == 1

    def test_arr_special_carry_flag(self, nmos_cpu):
        """Test ARR sets carry from bit 6 of result."""
        nmos_cpu.reset()
        nmos_cpu.A = 0xFF
        nmos_cpu.C = 0

        nmos_cpu.ram[0xFFFC] = instructions.ARR_IMMEDIATE_0x6B
        nmos_cpu.ram[0xFFFD] = 0xFF

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=2)

        # Verify: (0xFF & 0xFF) ROR with C=0 = 0xFF ROR = 0x7F
        assert nmos_cpu.A == 0x7F
        # C is set from bit 6 of result (0x7F = 01111111, bit 6 = 1)
        assert nmos_cpu.C == 1

    def test_arr_special_overflow_flag(self, nmos_cpu):
        """Test ARR sets overflow from bit 6 XOR bit 5."""
        nmos_cpu.reset()
        nmos_cpu.A = 0xFF
        nmos_cpu.C = 0

        nmos_cpu.ram[0xFFFC] = instructions.ARR_IMMEDIATE_0x6B
        nmos_cpu.ram[0xFFFD] = 0xC0  # 11000000

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=2)

        # Verify: (0xFF & 0xC0) ROR with C=0 = 0xC0 ROR = 0x60
        assert nmos_cpu.A == 0x60  # 01100000
        # bit 6 = 1, bit 5 = 1, V = 1 XOR 1 = 0
        assert nmos_cpu.V == 0

    def test_arr_overflow_set(self, nmos_cpu):
        """Test ARR sets overflow when bit 6 XOR bit 5 = 1."""
        nmos_cpu.reset()
        nmos_cpu.A = 0xFF
        nmos_cpu.C = 1

        nmos_cpu.ram[0xFFFC] = instructions.ARR_IMMEDIATE_0x6B
        nmos_cpu.ram[0xFFFD] = 0x40  # 01000000

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=2)

        # Verify: (0xFF & 0x40) ROR with C=1 = 0x40 ROR = 0xA0
        assert nmos_cpu.A == 0xA0  # 10100000
        # bit 6 = 0, bit 5 = 1, V = 0 XOR 1 = 1
        assert nmos_cpu.V == 1


class TestSBXNMOS:
    """Test SBX instruction on NMOS variants (6502, 6502A, 6502C)."""

    def test_sbx_basic_subtract(self, nmos_cpu):
        """Test SBX performs (A & X) - immediate."""
        nmos_cpu.reset()
        nmos_cpu.A = 0xFF
        nmos_cpu.X = 0xFF

        nmos_cpu.ram[0xFFFC] = instructions.SBX_IMMEDIATE_0xCB
        nmos_cpu.ram[0xFFFD] = 0x0F

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=2)

        # Verify: (0xFF & 0xFF) - 0x0F = 0xFF - 0x0F = 0xF0
        assert nmos_cpu.X == 0xF0
        assert nmos_cpu.Z == 0
        assert nmos_cpu.N == 1
        assert nmos_cpu.C == 1  # No borrow (result >= 0)

    def test_sbx_with_borrow(self, nmos_cpu):
        """Test SBX clears carry when result is negative."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x0F
        nmos_cpu.X = 0x0F

        nmos_cpu.ram[0xFFFC] = instructions.SBX_IMMEDIATE_0xCB
        nmos_cpu.ram[0xFFFD] = 0xFF

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=2)

        # Verify: (0x0F & 0x0F) - 0xFF = 0x0F - 0xFF = -240 = 0x10 (wrapped)
        assert nmos_cpu.X == 0x10
        assert nmos_cpu.C == 0  # Borrow occurred

    def test_sbx_zero_result(self, nmos_cpu):
        """Test SBX sets zero flag when result is zero."""
        nmos_cpu.reset()
        nmos_cpu.A = 0xFF
        nmos_cpu.X = 0xFF

        nmos_cpu.ram[0xFFFC] = instructions.SBX_IMMEDIATE_0xCB
        nmos_cpu.ram[0xFFFD] = 0xFF

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=2)

        # Verify: (0xFF & 0xFF) - 0xFF = 0xFF - 0xFF = 0x00
        assert nmos_cpu.X == 0x00
        assert nmos_cpu.Z == 1
        assert nmos_cpu.N == 0
        assert nmos_cpu.C == 1  # No borrow

    def test_sbx_and_operation(self, nmos_cpu):
        """Test SBX properly ANDs A with X before subtraction."""
        nmos_cpu.reset()
        nmos_cpu.A = 0xAA  # 10101010
        nmos_cpu.X = 0x55  # 01010101

        nmos_cpu.ram[0xFFFC] = instructions.SBX_IMMEDIATE_0xCB
        nmos_cpu.ram[0xFFFD] = 0x00

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=2)

        # Verify: (0xAA & 0x55) - 0x00 = 0x00 - 0x00 = 0x00
        assert nmos_cpu.X == 0x00
        assert nmos_cpu.Z == 1


class TestImmediateCMOS:
    """Test immediate mode illegal instructions on CMOS variant (65C02) - act as NOPs."""

    def test_anc_acts_as_nop(self, cmos_cpu):
        """Test ANC acts as NOP on CMOS."""
        cmos_cpu.reset()
        cmos_cpu.A = 0xF0
        cmos_cpu.C = 0

        cmos_cpu.ram[0xFFFC] = instructions.ANC_IMMEDIATE_0x0B
        cmos_cpu.ram[0xFFFD] = 0x0F

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(cycles=2)

        assert cmos_cpu.A == 0xF0
        assert cmos_cpu.C == 0

    def test_alr_acts_as_nop(self, cmos_cpu):
        """Test ALR acts as NOP on CMOS."""
        cmos_cpu.reset()
        cmos_cpu.A = 0xFF

        cmos_cpu.ram[0xFFFC] = instructions.ALR_IMMEDIATE_0x4B
        cmos_cpu.ram[0xFFFD] = 0x0F

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(cycles=2)

        assert cmos_cpu.A == 0xFF

    def test_arr_acts_as_nop(self, cmos_cpu):
        """Test ARR acts as NOP on CMOS."""
        cmos_cpu.reset()
        cmos_cpu.A = 0x7F
        cmos_cpu.C = 1

        cmos_cpu.ram[0xFFFC] = instructions.ARR_IMMEDIATE_0x6B
        cmos_cpu.ram[0xFFFD] = 0xFF

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(cycles=2)

        assert cmos_cpu.A == 0x7F
        assert cmos_cpu.C == 1

    def test_sbx_acts_as_nop(self, cmos_cpu):
        """Test SBX acts as NOP on CMOS."""
        cmos_cpu.reset()
        cmos_cpu.A = 0xFF
        cmos_cpu.X = 0xFF

        cmos_cpu.ram[0xFFFC] = instructions.SBX_IMMEDIATE_0xCB
        cmos_cpu.ram[0xFFFD] = 0x0F

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(cycles=2)

        assert cmos_cpu.X == 0xFF
