"""Tests for ISC (Increment and Subtract with Carry) illegal instruction.

ISC is a stable illegal instruction on NMOS 6502 that increments a memory
location and then subtracts the result from the accumulator with carry. On
CMOS 65C02, it acts as a NOP.

Operation: M = M + 1, A = A - M - (1 - C)

Opcodes:
    $E7 - ISC Zero Page (5 cycles)
    $F7 - ISC Zero Page,X (6 cycles)
    $E3 - ISC (Indirect,X) (8 cycles)
    $F3 - ISC (Indirect),Y (8 cycles)
    $EF - ISC Absolute (6 cycles)
    $FF - ISC Absolute,X (7 cycles)
    $FB - ISC Absolute,Y (7 cycles)

Flags: N, Z, C, V (same as SBC)

References:
    - https://masswerk.at/6502/6502_instruction_set.html#ISC
    - http://www.oxyron.de/html/opcodes02.html
"""
import contextlib

from mos6502 import errors, instructions


class TestISCNMOS:
    """Test ISC instruction on NMOS variants (6502, 6502A, 6502C)."""

    def test_isc_zeropage_increments_and_subtracts(self, nmos_cpu) -> None:
        """Test ISC zero page increments memory and subtracts from A."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x50
        nmos_cpu.C = 1  # No borrow
        nmos_cpu.ram[0x10] = 0x2F  # Will increment to 0x30

        nmos_cpu.ram[0xFFFC] = instructions.ISC_ZEROPAGE_0xE7
        nmos_cpu.ram[0xFFFD] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory was incremented: 0x2F + 1 = 0x30
        assert nmos_cpu.ram[0x10] == 0x30
        # Verify subtraction: A = 0x50 - 0x30 - 0 = 0x20
        assert nmos_cpu.A == 0x20
        # Verify flags
        assert nmos_cpu.Z == 0  # Not zero
        assert nmos_cpu.C == 1  # No borrow (A >= M)
        assert nmos_cpu.N == 0  # Positive result
        assert nmos_cpu.V == 0  # No overflow
        assert nmos_cpu.cycles_executed == 5

    def test_isc_with_borrow(self, nmos_cpu) -> None:
        """Test ISC with carry clear (borrow set)."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x50
        nmos_cpu.C = 0  # Borrow is set
        nmos_cpu.ram[0x20] = 0x2F  # Will increment to 0x30

        nmos_cpu.ram[0xFFFC] = instructions.ISC_ZEROPAGE_0xE7
        nmos_cpu.ram[0xFFFD] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory was incremented
        assert nmos_cpu.ram[0x20] == 0x30
        # Verify subtraction with borrow: A = 0x50 - 0x30 - 1 = 0x1F
        assert nmos_cpu.A == 0x1F
        assert nmos_cpu.C == 1  # No borrow in result

    def test_isc_sets_carry_when_a_less(self, nmos_cpu) -> None:
        """Test ISC clears carry flag when result requires borrow."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x30
        nmos_cpu.C = 1  # No borrow initially
        nmos_cpu.ram[0x30] = 0x4F  # Will increment to 0x50

        nmos_cpu.ram[0xFFFC] = instructions.ISC_ZEROPAGE_0xE7
        nmos_cpu.ram[0xFFFD] = 0x30

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory was incremented
        assert nmos_cpu.ram[0x30] == 0x50
        # Verify subtraction: A = 0x30 - 0x50 - 0 = 0xE0 (with wrap)
        assert nmos_cpu.A == 0xE0
        assert nmos_cpu.Z == 0  # Not zero
        assert nmos_cpu.C == 0  # Borrow needed (A < M)
        assert nmos_cpu.N == 1  # Negative result (bit 7 set)

    def test_isc_sets_zero_flag(self, nmos_cpu) -> None:
        """Test ISC sets zero flag when result is zero."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x31
        nmos_cpu.C = 1  # No borrow
        nmos_cpu.ram[0x40] = 0x30  # Will increment to 0x31

        nmos_cpu.ram[0xFFFC] = instructions.ISC_ZEROPAGE_0xE7
        nmos_cpu.ram[0xFFFD] = 0x40

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory was incremented
        assert nmos_cpu.ram[0x40] == 0x31
        # Verify subtraction: A = 0x31 - 0x31 - 0 = 0x00
        assert nmos_cpu.A == 0x00
        assert nmos_cpu.Z == 1  # Zero
        assert nmos_cpu.C == 1  # No borrow
        assert nmos_cpu.N == 0  # Not negative

    def test_isc_overflow_flag(self, nmos_cpu) -> None:
        """Test ISC sets overflow flag appropriately."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x50  # Positive
        nmos_cpu.C = 1  # No borrow
        nmos_cpu.ram[0x50] = 0x9F  # Will increment to 0xA0 (negative in signed)

        nmos_cpu.ram[0xFFFC] = instructions.ISC_ZEROPAGE_0xE7
        nmos_cpu.ram[0xFFFD] = 0x50

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory was incremented
        assert nmos_cpu.ram[0x50] == 0xA0
        # Verify overflow flag is set (pos - neg = neg overflow)
        assert nmos_cpu.V == 1

    def test_isc_wrap_around_ff(self, nmos_cpu) -> None:
        """Test ISC wraps 0xFF to 0x00 during increment."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x00
        nmos_cpu.C = 1  # No borrow
        nmos_cpu.ram[0x60] = 0xFF  # Will wrap to 0x00

        nmos_cpu.ram[0xFFFC] = instructions.ISC_ZEROPAGE_0xE7
        nmos_cpu.ram[0xFFFD] = 0x60

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory wrapped: 0xFF + 1 = 0x00
        assert nmos_cpu.ram[0x60] == 0x00
        # Verify subtraction: A = 0x00 - 0x00 - 0 = 0x00
        assert nmos_cpu.A == 0x00
        assert nmos_cpu.Z == 1  # Zero
        assert nmos_cpu.C == 1  # No borrow

    def test_isc_zeropage_x(self, nmos_cpu) -> None:
        """Test ISC zero page,X with offset."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x50
        nmos_cpu.X = 0x05
        nmos_cpu.C = 1
        nmos_cpu.ram[0x15] = 0x1F  # At $10 + $05, will increment to 0x20

        nmos_cpu.ram[0xFFFC] = instructions.ISC_ZEROPAGE_X_0xF7
        nmos_cpu.ram[0xFFFD] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=6)

        # Verify memory at $15 was incremented
        assert nmos_cpu.ram[0x15] == 0x20
        # Verify subtraction: A = 0x50 - 0x20 - 0 = 0x30
        assert nmos_cpu.A == 0x30
        assert nmos_cpu.cycles_executed == 6

    def test_isc_absolute(self, nmos_cpu) -> None:
        """Test ISC absolute addressing."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x80
        nmos_cpu.C = 1
        nmos_cpu.ram[0x4567] = 0x2F  # Will increment to 0x30

        nmos_cpu.ram[0xFFFC] = instructions.ISC_ABSOLUTE_0xEF
        nmos_cpu.ram[0xFFFD] = 0x67
        nmos_cpu.ram[0xFFFE] = 0x45

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=6)

        # Verify memory was incremented
        assert nmos_cpu.ram[0x4567] == 0x30
        # Verify subtraction: A = 0x80 - 0x30 - 0 = 0x50
        assert nmos_cpu.A == 0x50
        assert nmos_cpu.cycles_executed == 6

    def test_isc_absolute_x(self, nmos_cpu) -> None:
        """Test ISC absolute,X addressing."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x50
        nmos_cpu.X = 0x10
        nmos_cpu.C = 1
        nmos_cpu.ram[0x1234 + 0x10] = 0x0F  # Will increment to 0x10

        nmos_cpu.ram[0xFFFC] = instructions.ISC_ABSOLUTE_X_0xFF
        nmos_cpu.ram[0xFFFD] = 0x34
        nmos_cpu.ram[0xFFFE] = 0x12

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=7)

        # Verify memory was incremented
        assert nmos_cpu.ram[0x1244] == 0x10
        # Verify subtraction: A = 0x50 - 0x10 - 0 = 0x40
        assert nmos_cpu.A == 0x40
        assert nmos_cpu.cycles_executed == 7

    def test_isc_absolute_y(self, nmos_cpu) -> None:
        """Test ISC absolute,Y addressing."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x60
        nmos_cpu.Y = 0x20
        nmos_cpu.C = 1
        nmos_cpu.ram[0x2000 + 0x20] = 0x1F  # Will increment to 0x20

        nmos_cpu.ram[0xFFFC] = instructions.ISC_ABSOLUTE_Y_0xFB
        nmos_cpu.ram[0xFFFD] = 0x00
        nmos_cpu.ram[0xFFFE] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=7)

        # Verify memory was incremented
        assert nmos_cpu.ram[0x2020] == 0x20
        # Verify subtraction: A = 0x60 - 0x20 - 0 = 0x40
        assert nmos_cpu.A == 0x40
        assert nmos_cpu.cycles_executed == 7

    def test_isc_indexed_indirect_x(self, nmos_cpu) -> None:
        """Test ISC (indirect,X) addressing."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x70
        nmos_cpu.X = 0x04
        nmos_cpu.C = 1

        # Pointer at $10 + $04 = $14 points to $3000
        nmos_cpu.ram[0x14] = 0x00
        nmos_cpu.ram[0x15] = 0x30
        nmos_cpu.ram[0x3000] = 0x2F  # Will increment to 0x30

        nmos_cpu.ram[0xFFFC] = instructions.ISC_INDEXED_INDIRECT_X_0xE3
        nmos_cpu.ram[0xFFFD] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=8)

        # Verify memory was incremented
        assert nmos_cpu.ram[0x3000] == 0x30
        # Verify subtraction: A = 0x70 - 0x30 - 0 = 0x40
        assert nmos_cpu.A == 0x40
        assert nmos_cpu.cycles_executed == 8

    def test_isc_indirect_indexed_y(self, nmos_cpu) -> None:
        """Test ISC (indirect),Y addressing."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x80
        nmos_cpu.Y = 0x10
        nmos_cpu.C = 1

        # Pointer at $20 points to $4000, + Y = $4010
        nmos_cpu.ram[0x20] = 0x00
        nmos_cpu.ram[0x21] = 0x40
        nmos_cpu.ram[0x4010] = 0x3F  # Will increment to 0x40

        nmos_cpu.ram[0xFFFC] = instructions.ISC_INDIRECT_INDEXED_Y_0xF3
        nmos_cpu.ram[0xFFFD] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=8)

        # Verify memory was incremented
        assert nmos_cpu.ram[0x4010] == 0x40
        # Verify subtraction: A = 0x80 - 0x40 - 0 = 0x40
        assert nmos_cpu.A == 0x40
        assert nmos_cpu.cycles_executed == 8


class TestISCCMOS:
    """Test ISC instruction on CMOS variant (65C02) - acts as NOP."""

    def test_isc_acts_as_nop(self, cmos_cpu) -> None:
        """Test ISC acts as NOP on CMOS (65C02)."""
        cmos_cpu.reset()
        cmos_cpu.A = 0x50
        cmos_cpu.C = 1
        cmos_cpu.ram[0x10] = 0x2F

        cmos_cpu.ram[0xFFFC] = instructions.ISC_ZEROPAGE_0xE7
        cmos_cpu.ram[0xFFFD] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(cycles=5)

        # Verify memory is unchanged (NOP behavior)
        assert cmos_cpu.ram[0x10] == 0x2F
        # Verify A is unchanged
        assert cmos_cpu.A == 0x50
        # Verify no flags are modified
        assert cmos_cpu.Z == 0
        assert cmos_cpu.N == 0
        assert cmos_cpu.C == 1  # Unchanged
        assert cmos_cpu.V == 0
        assert cmos_cpu.cycles_executed == 5
