"""Tests for RLA (Rotate Left and AND) illegal instruction.

RLA is a stable illegal instruction on NMOS 6502 that rotates a memory location
left through the carry flag and then performs a bitwise AND with the accumulator.
On CMOS 65C02, it acts as a NOP.

Operation: M = ROL(M), A = A & M

Opcodes:
    $27 - RLA Zero Page (5 cycles)
    $37 - RLA Zero Page,X (6 cycles)
    $23 - RLA (Indirect,X) (8 cycles)
    $33 - RLA (Indirect),Y (8 cycles)
    $2F - RLA Absolute (6 cycles)
    $3F - RLA Absolute,X (7 cycles)
    $3B - RLA Absolute,Y (7 cycles)

Flags: N, Z, C

References:
    - https://masswerk.at/6502/6502_instruction_set.html#RLA
    - http://www.oxyron.de/html/opcodes02.html
"""
import contextlib

from mos6502 import errors, instructions


class TestRLANMOS:
    """Test RLA instruction on NMOS variants (6502, 6502A, 6502C)."""

    def test_rla_zeropage_rotates_and_ands(self, nmos_cpu):
        """Test RLA zero page rotates memory left and ANDs with A."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x0F
        nmos_cpu.C = 0
        nmos_cpu.ram[0x10] = 0x55  # 01010101, will rotate to 10101010 (0xAA)

        nmos_cpu.ram[0xFFFC] = instructions.RLA_ZEROPAGE_0x27
        nmos_cpu.ram[0xFFFD] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory was rotated: 0x55 << 1 = 0xAA (carry in was 0)
        assert nmos_cpu.ram[0x10] == 0xAA
        # Verify AND: A = 0x0F & 0xAA = 0x0A
        assert nmos_cpu.A == 0x0A
        # Verify flags
        assert nmos_cpu.Z == 0  # Not zero
        assert nmos_cpu.C == 0  # Bit 7 of original was 0
        assert nmos_cpu.N == 0  # Result bit 7 is clear
        assert nmos_cpu.cycles_executed == 5

    def test_rla_with_carry_in(self, nmos_cpu):
        """Test RLA rotates carry into bit 0."""
        nmos_cpu.reset()
        nmos_cpu.A = 0xFF
        nmos_cpu.C = 1  # Set carry
        nmos_cpu.ram[0x20] = 0x00  # 00000000, will rotate to 00000001

        nmos_cpu.ram[0xFFFC] = instructions.RLA_ZEROPAGE_0x27
        nmos_cpu.ram[0xFFFD] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory was rotated: 0x00 << 1 | carry_in = 0x01
        assert nmos_cpu.ram[0x20] == 0x01
        # Verify AND: A = 0xFF & 0x01 = 0x01
        assert nmos_cpu.A == 0x01
        assert nmos_cpu.C == 0  # Bit 7 of original was 0
        assert nmos_cpu.N == 0
        assert nmos_cpu.Z == 0

    def test_rla_sets_carry(self, nmos_cpu):
        """Test RLA sets carry when bit 7 of original value is set."""
        nmos_cpu.reset()
        nmos_cpu.A = 0xFF
        nmos_cpu.C = 0
        nmos_cpu.ram[0x30] = 0x81  # 10000001, bit 7 set

        nmos_cpu.ram[0xFFFC] = instructions.RLA_ZEROPAGE_0x27
        nmos_cpu.ram[0xFFFD] = 0x30

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory was rotated: 0x81 << 1 = 0x02
        assert nmos_cpu.ram[0x30] == 0x02
        # Verify AND: A = 0xFF & 0x02 = 0x02
        assert nmos_cpu.A == 0x02
        # Verify carry flag set (bit 7 was 1)
        assert nmos_cpu.C == 1
        assert nmos_cpu.N == 0
        assert nmos_cpu.Z == 0

    def test_rla_sets_zero_flag(self, nmos_cpu):
        """Test RLA sets zero flag when result is zero."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x00
        nmos_cpu.C = 0
        nmos_cpu.ram[0x40] = 0x55  # Will rotate to 0xAA

        nmos_cpu.ram[0xFFFC] = instructions.RLA_ZEROPAGE_0x27
        nmos_cpu.ram[0xFFFD] = 0x40

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory was rotated: 0x55 << 1 = 0xAA
        assert nmos_cpu.ram[0x40] == 0xAA
        # Verify AND: A = 0x00 & 0xAA = 0x00
        assert nmos_cpu.A == 0x00
        # Verify zero flag set
        assert nmos_cpu.Z == 1
        assert nmos_cpu.N == 0
        assert nmos_cpu.C == 0

    def test_rla_and_operation(self, nmos_cpu):
        """Test RLA AND operation combines properly."""
        nmos_cpu.reset()
        nmos_cpu.A = 0xF0  # 11110000
        nmos_cpu.C = 0
        nmos_cpu.ram[0x50] = 0x55  # 01010101, rotates to 10101010 (0xAA)

        nmos_cpu.ram[0xFFFC] = instructions.RLA_ZEROPAGE_0x27
        nmos_cpu.ram[0xFFFD] = 0x50

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory was rotated: 0x55 << 1 = 0xAA
        assert nmos_cpu.ram[0x50] == 0xAA
        # Verify AND: A = 0xF0 & 0xAA = 0xA0
        assert nmos_cpu.A == 0xA0
        assert nmos_cpu.N == 1  # Bit 7 set
        assert nmos_cpu.Z == 0
        assert nmos_cpu.C == 0

    def test_rla_rotate_with_carry_in_and_out(self, nmos_cpu):
        """Test RLA rotate with both carry in and carry out."""
        nmos_cpu.reset()
        nmos_cpu.A = 0xFF
        nmos_cpu.C = 1  # Carry in
        nmos_cpu.ram[0x60] = 0x80  # 10000000, bit 7 set

        nmos_cpu.ram[0xFFFC] = instructions.RLA_ZEROPAGE_0x27
        nmos_cpu.ram[0xFFFD] = 0x60

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify rotate: 0x80 << 1 | carry_in = 0x01
        assert nmos_cpu.ram[0x60] == 0x01
        # Verify AND: A = 0xFF & 0x01 = 0x01
        assert nmos_cpu.A == 0x01
        assert nmos_cpu.C == 1  # Bit 7 was set
        assert nmos_cpu.N == 0
        assert nmos_cpu.Z == 0

    def test_rla_zeropage_x(self, nmos_cpu):
        """Test RLA zero page,X with offset."""
        nmos_cpu.reset()
        nmos_cpu.A = 0xFF
        nmos_cpu.X = 0x05
        nmos_cpu.C = 0
        nmos_cpu.ram[0x15] = 0x04  # At $10 + $05, rotates to 0x08

        nmos_cpu.ram[0xFFFC] = instructions.RLA_ZEROPAGE_X_0x37
        nmos_cpu.ram[0xFFFD] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=6)

        # Verify memory at $15 was rotated
        assert nmos_cpu.ram[0x15] == 0x08
        # Verify AND: A = 0xFF & 0x08 = 0x08
        assert nmos_cpu.A == 0x08
        assert nmos_cpu.cycles_executed == 6

    def test_rla_absolute(self, nmos_cpu):
        """Test RLA absolute addressing."""
        nmos_cpu.reset()
        nmos_cpu.A = 0xF0
        nmos_cpu.C = 0
        nmos_cpu.ram[0x4567] = 0x33  # Rotates to 0x66

        nmos_cpu.ram[0xFFFC] = instructions.RLA_ABSOLUTE_0x2F
        nmos_cpu.ram[0xFFFD] = 0x67
        nmos_cpu.ram[0xFFFE] = 0x45

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=6)

        # Verify memory was rotated
        assert nmos_cpu.ram[0x4567] == 0x66
        # Verify AND: A = 0xF0 & 0x66 = 0x60
        assert nmos_cpu.A == 0x60
        assert nmos_cpu.cycles_executed == 6

    def test_rla_absolute_x(self, nmos_cpu):
        """Test RLA absolute,X addressing."""
        nmos_cpu.reset()
        nmos_cpu.A = 0xFF
        nmos_cpu.X = 0x10
        nmos_cpu.C = 1
        nmos_cpu.ram[0x1234 + 0x10] = 0x02  # Rotates to 0x05 (with carry in)

        nmos_cpu.ram[0xFFFC] = instructions.RLA_ABSOLUTE_X_0x3F
        nmos_cpu.ram[0xFFFD] = 0x34
        nmos_cpu.ram[0xFFFE] = 0x12

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=7)

        # Verify memory was rotated
        assert nmos_cpu.ram[0x1244] == 0x05
        # Verify AND: A = 0xFF & 0x05 = 0x05
        assert nmos_cpu.A == 0x05
        assert nmos_cpu.cycles_executed == 7

    def test_rla_absolute_y(self, nmos_cpu):
        """Test RLA absolute,Y addressing."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x0F
        nmos_cpu.Y = 0x20
        nmos_cpu.C = 0
        nmos_cpu.ram[0x2000 + 0x20] = 0x44  # Rotates to 0x88

        nmos_cpu.ram[0xFFFC] = instructions.RLA_ABSOLUTE_Y_0x3B
        nmos_cpu.ram[0xFFFD] = 0x00
        nmos_cpu.ram[0xFFFE] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=7)

        # Verify memory was rotated
        assert nmos_cpu.ram[0x2020] == 0x88
        # Verify AND: A = 0x0F & 0x88 = 0x08
        assert nmos_cpu.A == 0x08
        assert nmos_cpu.cycles_executed == 7

    def test_rla_indexed_indirect_x(self, nmos_cpu):
        """Test RLA (indirect,X) addressing."""
        nmos_cpu.reset()
        nmos_cpu.A = 0xFF
        nmos_cpu.X = 0x04
        nmos_cpu.C = 0

        # Pointer at $10 + $04 = $14 points to $3000
        nmos_cpu.ram[0x14] = 0x00
        nmos_cpu.ram[0x15] = 0x30
        nmos_cpu.ram[0x3000] = 0x11  # Rotates to 0x22

        nmos_cpu.ram[0xFFFC] = instructions.RLA_INDEXED_INDIRECT_X_0x23
        nmos_cpu.ram[0xFFFD] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=8)

        # Verify memory was rotated
        assert nmos_cpu.ram[0x3000] == 0x22
        # Verify AND: A = 0xFF & 0x22 = 0x22
        assert nmos_cpu.A == 0x22
        assert nmos_cpu.cycles_executed == 8

    def test_rla_indirect_indexed_y(self, nmos_cpu):
        """Test RLA (indirect),Y addressing."""
        nmos_cpu.reset()
        nmos_cpu.A = 0xAA
        nmos_cpu.Y = 0x10
        nmos_cpu.C = 1

        # Pointer at $20 points to $4000, + Y = $4010
        nmos_cpu.ram[0x20] = 0x00
        nmos_cpu.ram[0x21] = 0x40
        nmos_cpu.ram[0x4010] = 0x40  # Rotates to 0x81 (with carry in)

        nmos_cpu.ram[0xFFFC] = instructions.RLA_INDIRECT_INDEXED_Y_0x33
        nmos_cpu.ram[0xFFFD] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=8)

        # Verify memory was rotated
        assert nmos_cpu.ram[0x4010] == 0x81
        # Verify AND: A = 0xAA & 0x81 = 0x80
        assert nmos_cpu.A == 0x80
        assert nmos_cpu.cycles_executed == 8


class TestRLACMOS:
    """Test RLA instruction on CMOS variant (65C02) - acts as NOP."""

    def test_rla_acts_as_nop(self, cmos_cpu):
        """Test RLA acts as NOP on CMOS (65C02)."""
        cmos_cpu.reset()
        cmos_cpu.A = 0x0F
        cmos_cpu.C = 1
        cmos_cpu.ram[0x10] = 0x55

        cmos_cpu.ram[0xFFFC] = instructions.RLA_ZEROPAGE_0x27
        cmos_cpu.ram[0xFFFD] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(cycles=5)

        # Verify memory is unchanged (NOP behavior)
        assert cmos_cpu.ram[0x10] == 0x55
        # Verify A is unchanged
        assert cmos_cpu.A == 0x0F
        # Verify carry is unchanged
        assert cmos_cpu.C == 1
        # Verify no flags are modified
        assert cmos_cpu.Z == 0
        assert cmos_cpu.N == 0
        assert cmos_cpu.cycles_executed == 5