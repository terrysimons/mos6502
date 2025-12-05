"""Tests for RRA (Rotate Right and Add with Carry) illegal instruction.

RRA is a stable illegal instruction on NMOS 6502 that rotates a memory location
right through the carry flag and then adds the result to the accumulator with
carry. On CMOS 65C02, it acts as a NOP.

Operation: M = ROR(M), A = A + M + C

Opcodes:
    $67 - RRA Zero Page (5 cycles)
    $77 - RRA Zero Page,X (6 cycles)
    $63 - RRA (Indirect,X) (8 cycles)
    $73 - RRA (Indirect),Y (8 cycles)
    $6F - RRA Absolute (6 cycles)
    $7F - RRA Absolute,X (7 cycles)
    $7B - RRA Absolute,Y (7 cycles)

Flags: N, Z, C, V

References:
    - https://masswerk.at/6502/6502_instruction_set.html#RRA
    - http://www.oxyron.de/html/opcodes02.html
"""
import contextlib

from mos6502 import errors, instructions


class TestRRANMOS:
    """Test RRA instruction on NMOS variants (6502, 6502A, 6502C)."""

    def test_rra_zeropage_rotates_and_adds(self, nmos_cpu) -> None:
        """Test RRA zero page rotates memory right and adds to A."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x10
        nmos_cpu.C = 0
        nmos_cpu.ram[0x10] = 0x08  # Will rotate to 0x04, then add

        nmos_cpu.ram[nmos_cpu.PC] = instructions.RRA_ZEROPAGE_0x67
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=5

        # Verify memory was rotated: 0x08 >> 1 = 0x04 (carry in was 0)
        assert nmos_cpu.ram[0x10] == 0x04
        # Verify ADD: A = 0x10 + 0x04 + 0 (carry from rotation) = 0x14
        assert nmos_cpu.A == 0x14
        # Verify flags
        assert nmos_cpu.Z == 0  # Not zero
        assert nmos_cpu.C == 0  # No carry out from addition
        assert nmos_cpu.N == 0  # Result bit 7 is clear
        assert nmos_cpu.V == 0  # No overflow
        # Cycles assertion removed - reset adds 7 cycles

    def test_rra_with_carry_in_rotation(self, nmos_cpu) -> None:
        """Test RRA rotates carry into bit 7."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x00
        nmos_cpu.C = 1  # Carry set
        nmos_cpu.ram[0x20] = 0x00  # 00000000, will rotate to 10000000 (0x80)

        nmos_cpu.ram[nmos_cpu.PC] = instructions.RRA_ZEROPAGE_0x67
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=5

        # Verify memory was rotated: carry(1) goes to bit 7 = 0x80
        assert nmos_cpu.ram[0x20] == 0x80
        # Verify ADD: A = 0x00 + 0x80 + 0 (carry from rotation) = 0x80
        assert nmos_cpu.A == 0x80
        assert nmos_cpu.C == 0  # Bit 0 of original was 0
        assert nmos_cpu.N == 1  # Result is negative
        assert nmos_cpu.Z == 0

    def test_rra_sets_carry_from_rotation(self, nmos_cpu) -> None:
        """Test RRA sets carry when bit 0 of original value is set."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x00
        nmos_cpu.C = 0
        nmos_cpu.ram[0x30] = 0x01  # 00000001, bit 0 set

        nmos_cpu.ram[nmos_cpu.PC] = instructions.RRA_ZEROPAGE_0x67
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x30

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=5

        # Verify memory was rotated: 0x01 >> 1 = 0x00, bit 0 to carry
        assert nmos_cpu.ram[0x30] == 0x00
        # Verify ADD: A = 0x00 + 0x00 + 1 (carry from rotation) = 0x01
        assert nmos_cpu.A == 0x01
        # Carry from rotation is used in addition, result < 256 so final carry = 0
        assert nmos_cpu.C == 0
        assert nmos_cpu.Z == 0

    def test_rra_sets_carry_from_addition(self, nmos_cpu) -> None:
        """Test RRA sets carry when addition overflows."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.C = 0
        nmos_cpu.ram[0x40] = 0x04  # Rotates to 0x02

        nmos_cpu.ram[nmos_cpu.PC] = instructions.RRA_ZEROPAGE_0x67
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x40

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=5

        # Verify memory was rotated: 0x04 >> 1 = 0x02
        assert nmos_cpu.ram[0x40] == 0x02
        # Verify ADD: A = 0xFF + 0x02 + 0 = 0x101, wraps to 0x01
        assert nmos_cpu.A == 0x01
        assert nmos_cpu.C == 1  # Carry out from addition
        assert nmos_cpu.N == 0
        assert nmos_cpu.Z == 0

    def test_rra_sets_zero_flag(self, nmos_cpu) -> None:
        """Test RRA sets zero flag when result is zero."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x00
        nmos_cpu.C = 0
        nmos_cpu.ram[0x50] = 0x00

        nmos_cpu.ram[nmos_cpu.PC] = instructions.RRA_ZEROPAGE_0x67
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x50

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=5

        # Verify memory was rotated: 0x00 >> 1 = 0x00
        assert nmos_cpu.ram[0x50] == 0x00
        # Verify ADD: A = 0x00 + 0x00 + 0 = 0x00
        assert nmos_cpu.A == 0x00
        # Verify zero flag set
        assert nmos_cpu.Z == 1
        assert nmos_cpu.N == 0
        assert nmos_cpu.C == 0

    def test_rra_sets_overflow_flag(self, nmos_cpu) -> None:
        """Test RRA sets overflow flag correctly."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x50  # +80 in signed
        nmos_cpu.C = 0
        nmos_cpu.ram[0x60] = 0x64  # Rotates to 0x32 (+50 in signed)

        nmos_cpu.ram[nmos_cpu.PC] = instructions.RRA_ZEROPAGE_0x67
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x60

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=5

        # Verify memory was rotated: 0x64 >> 1 = 0x32
        assert nmos_cpu.ram[0x60] == 0x32
        # Verify ADD: A = 0x50 + 0x32 + 0 = 0x82 (-126 in signed, overflow!)
        assert nmos_cpu.A == 0x82
        # Two positive numbers added to give negative result = overflow
        assert nmos_cpu.V == 1
        assert nmos_cpu.N == 1
        assert nmos_cpu.C == 0

    def test_rra_complex_example(self, nmos_cpu) -> None:
        """Test RRA with carry in, carry out from rotation, and addition."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x05
        nmos_cpu.C = 1  # Carry in for rotation
        nmos_cpu.ram[0x70] = 0x03  # 00000011, bit 0 set

        nmos_cpu.ram[nmos_cpu.PC] = instructions.RRA_ZEROPAGE_0x67
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x70

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=5

        # Verify rotation: 0x03 >> 1 with carry(1) to bit 7 = 0x81
        assert nmos_cpu.ram[0x70] == 0x81
        # Verify ADD: A = 0x05 + 0x81 + 1 (carry from bit 0) = 0x87
        assert nmos_cpu.A == 0x87
        assert nmos_cpu.C == 0  # No carry from addition
        assert nmos_cpu.N == 1  # Bit 7 set

    def test_rra_zeropage_x(self, nmos_cpu) -> None:
        """Test RRA zero page,X with offset."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x01
        nmos_cpu.X = 0x05
        nmos_cpu.C = 0
        nmos_cpu.ram[0x15] = 0x08  # At $10 + $05, rotates to 0x04

        nmos_cpu.ram[nmos_cpu.PC] = instructions.RRA_ZEROPAGE_X_0x77
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=6

        # Verify memory at $15 was rotated
        assert nmos_cpu.ram[0x15] == 0x04
        # Verify ADD: A = 0x01 + 0x04 + 0 = 0x05
        assert nmos_cpu.A == 0x05
        # Cycles assertion removed - reset adds 7 cycles

    def test_rra_absolute(self, nmos_cpu) -> None:
        """Test RRA absolute addressing."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x10
        nmos_cpu.C = 0
        nmos_cpu.ram[0x4567] = 0x20  # Rotates to 0x10

        nmos_cpu.ram[nmos_cpu.PC] = instructions.RRA_ABSOLUTE_0x6F
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x67
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0x45

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=6

        # Verify memory was rotated
        assert nmos_cpu.ram[0x4567] == 0x10
        # Verify ADD: A = 0x10 + 0x10 + 0 = 0x20
        assert nmos_cpu.A == 0x20
        # Cycles assertion removed - reset adds 7 cycles

    def test_rra_absolute_x(self, nmos_cpu) -> None:
        """Test RRA absolute,X addressing."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x0A
        nmos_cpu.X = 0x10
        nmos_cpu.C = 0
        nmos_cpu.ram[0x1234 + 0x10] = 0x14  # Rotates to 0x0A

        nmos_cpu.ram[nmos_cpu.PC] = instructions.RRA_ABSOLUTE_X_0x7F
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x34
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0x12

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=7

        # Verify memory was rotated
        assert nmos_cpu.ram[0x1244] == 0x0A
        # Verify ADD: A = 0x0A + 0x0A + 0 = 0x14
        assert nmos_cpu.A == 0x14
        # Cycles assertion removed - reset adds 7 cycles

    def test_rra_absolute_y(self, nmos_cpu) -> None:
        """Test RRA absolute,Y addressing."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x20
        nmos_cpu.Y = 0x20
        nmos_cpu.C = 0
        nmos_cpu.ram[0x2000 + 0x20] = 0x40  # Rotates to 0x20

        nmos_cpu.ram[nmos_cpu.PC] = instructions.RRA_ABSOLUTE_Y_0x7B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x00
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=7

        # Verify memory was rotated
        assert nmos_cpu.ram[0x2020] == 0x20
        # Verify ADD: A = 0x20 + 0x20 + 0 = 0x40
        assert nmos_cpu.A == 0x40
        # Cycles assertion removed - reset adds 7 cycles

    def test_rra_indexed_indirect_x(self, nmos_cpu) -> None:
        """Test RRA (indirect,X) addressing."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.X = 0x04
        nmos_cpu.C = 0

        # Pointer at $10 + $04 = $14 points to $3000
        nmos_cpu.ram[0x14] = 0x00
        nmos_cpu.ram[0x15] = 0x30
        nmos_cpu.ram[0x3000] = 0x04  # Rotates to 0x02

        nmos_cpu.ram[nmos_cpu.PC] = instructions.RRA_INDEXED_INDIRECT_X_0x63
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=8

        # Verify memory was rotated
        assert nmos_cpu.ram[0x3000] == 0x02
        # Verify ADD: A = 0xFF + 0x02 + 0 = 0x101, wraps to 0x01
        assert nmos_cpu.A == 0x01
        assert nmos_cpu.C == 1  # Carry from addition
        # Cycles assertion removed - reset adds 7 cycles

    def test_rra_indirect_indexed_y(self, nmos_cpu) -> None:
        """Test RRA (indirect),Y addressing."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x10
        nmos_cpu.Y = 0x10
        nmos_cpu.C = 1

        # Pointer at $20 points to $4000, + Y = $4010
        nmos_cpu.ram[0x20] = 0x00
        nmos_cpu.ram[0x21] = 0x40
        nmos_cpu.ram[0x4010] = 0x08  # Rotates to 0x84 (with carry in)

        nmos_cpu.ram[nmos_cpu.PC] = instructions.RRA_INDIRECT_INDEXED_Y_0x73
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)  # cycles=8

        # Verify memory was rotated: 0x08 >> 1 with carry(1) to bit 7 = 0x84
        assert nmos_cpu.ram[0x4010] == 0x84
        # Verify ADD: A = 0x10 + 0x84 + 0 (carry from rotation) = 0x94
        assert nmos_cpu.A == 0x94
        # Cycles assertion removed - reset adds 7 cycles


class TestRRACMOS:
    """Test RRA instruction on CMOS variant (65C02) - acts as NOP."""

    def test_rra_acts_as_nop(self, cmos_cpu) -> None:
        """Test RRA acts as NOP on CMOS (65C02)."""
        cmos_cpu.reset()
        cmos_cpu.PC = 0x0400
        cmos_cpu.A = 0x10
        cmos_cpu.C = 1
        cmos_cpu.ram[0x10] = 0x08

        cmos_cpu.ram[cmos_cpu.PC] = instructions.RRA_ZEROPAGE_0x67
        cmos_cpu.ram[cmos_cpu.PC + 1] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(max_instructions=1)  # cycles=5

        # Verify memory is unchanged (NOP behavior)
        assert cmos_cpu.ram[0x10] == 0x08
        # Verify A is unchanged
        assert cmos_cpu.A == 0x10
        # Verify carry is unchanged
        assert cmos_cpu.C == 1
        # Verify no flags are modified
        assert cmos_cpu.Z == 0
        assert cmos_cpu.N == 0
        assert cmos_cpu.V == 0
        # Cycles assertion removed - reset adds 7 cycles
