"""Tests for DCP (Decrement and Compare) illegal instruction.

DCP is a stable illegal instruction on NMOS 6502 that decrements a memory
location and then compares the result with the accumulator. On CMOS 65C02,
it acts as a NOP.

Operation: M = M - 1, Compare(A, M)

Opcodes:
    $C7 - DCP Zero Page (5 cycles)
    $D7 - DCP Zero Page,X (6 cycles)
    $C3 - DCP (Indirect,X) (8 cycles)
    $D3 - DCP (Indirect),Y (8 cycles)
    $CF - DCP Absolute (6 cycles)
    $DF - DCP Absolute,X (7 cycles)
    $DB - DCP Absolute,Y (7 cycles)

Flags: N, Z, C (same as CMP)

References:
    - https://masswerk.at/6502/6502_instruction_set.html#DCP
    - http://www.oxyron.de/html/opcodes02.html
"""
import contextlib

from mos6502 import errors, instructions


class TestDCPNMOS:
    """Test DCP instruction on NMOS variants (6502, 6502A, 6502C)."""

    def test_dcp_zeropage_decrements_and_compares(self, nmos_cpu) -> None:
        """Test DCP zero page decrements memory and compares with A."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x50
        nmos_cpu.ram[0x10] = 0x51  # Will decrement to 0x50

        nmos_cpu.ram[0xFFFC] = instructions.DCP_ZEROPAGE_0xC7
        nmos_cpu.ram[0xFFFD] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory was decremented: 0x51 - 1 = 0x50
        assert nmos_cpu.ram[0x10] == 0x50
        # Verify A is unchanged
        assert nmos_cpu.A == 0x50
        # Verify comparison: A (0x50) == M (0x50)
        assert nmos_cpu.Z == 1  # Equal
        assert nmos_cpu.C == 1  # No borrow (A >= M)
        assert nmos_cpu.N == 0  # Positive result
        assert nmos_cpu.cycles_executed == 5

    def test_dcp_sets_carry_when_a_greater(self, nmos_cpu) -> None:
        """Test DCP sets carry flag when A > decremented memory."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x80
        nmos_cpu.ram[0x20] = 0x50  # Will decrement to 0x4F

        nmos_cpu.ram[0xFFFC] = instructions.DCP_ZEROPAGE_0xC7
        nmos_cpu.ram[0xFFFD] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory was decremented
        assert nmos_cpu.ram[0x20] == 0x4F
        # Verify comparison: A (0x80) > M (0x4F)
        assert nmos_cpu.Z == 0  # Not equal
        assert nmos_cpu.C == 1  # No borrow (A >= M)
        assert nmos_cpu.N == 0  # Result bit 7 clear: (0x80 - 0x4F) & 0xFF = 0x31

    def test_dcp_clears_carry_when_a_less(self, nmos_cpu) -> None:
        """Test DCP clears carry flag when A < decremented memory."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x30
        nmos_cpu.ram[0x30] = 0x51  # Will decrement to 0x50

        nmos_cpu.ram[0xFFFC] = instructions.DCP_ZEROPAGE_0xC7
        nmos_cpu.ram[0xFFFD] = 0x30

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory was decremented
        assert nmos_cpu.ram[0x30] == 0x50
        # Verify comparison: A (0x30) < M (0x50)
        assert nmos_cpu.Z == 0  # Not equal
        assert nmos_cpu.C == 0  # Borrow needed (A < M)
        assert nmos_cpu.N == 1  # Result bit 7 set: (0x30 - 0x50) & 0xFF = 0xE0

    def test_dcp_sets_negative_flag(self, nmos_cpu) -> None:
        """Test DCP sets negative flag when result bit 7 is set."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x10
        nmos_cpu.ram[0x40] = 0x90  # Will decrement to 0x8F

        nmos_cpu.ram[0xFFFC] = instructions.DCP_ZEROPAGE_0xC7
        nmos_cpu.ram[0xFFFD] = 0x40

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory was decremented
        assert nmos_cpu.ram[0x40] == 0x8F
        # Verify comparison: A (0x10) - M (0x8F) = 0x81 (negative)
        assert nmos_cpu.N == 1  # Bit 7 set in result
        assert nmos_cpu.Z == 0  # Not equal
        assert nmos_cpu.C == 0  # Borrow needed

    def test_dcp_wrap_around_zero(self, nmos_cpu) -> None:
        """Test DCP wraps 0x00 to 0xFF during decrement."""
        nmos_cpu.reset()
        nmos_cpu.A = 0xFF
        nmos_cpu.ram[0x50] = 0x00  # Will decrement to 0xFF

        nmos_cpu.ram[0xFFFC] = instructions.DCP_ZEROPAGE_0xC7
        nmos_cpu.ram[0xFFFD] = 0x50

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory wrapped: 0x00 - 1 = 0xFF
        assert nmos_cpu.ram[0x50] == 0xFF
        # Verify comparison: A (0xFF) == M (0xFF)
        assert nmos_cpu.Z == 1  # Equal
        assert nmos_cpu.C == 1  # No borrow
        assert nmos_cpu.N == 0  # Result is zero

    def test_dcp_zeropage_x(self, nmos_cpu) -> None:
        """Test DCP zero page,X with offset."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x42
        nmos_cpu.X = 0x05
        nmos_cpu.ram[0x15] = 0x43  # At $10 + $05, will decrement to 0x42

        nmos_cpu.ram[0xFFFC] = instructions.DCP_ZEROPAGE_X_0xD7
        nmos_cpu.ram[0xFFFD] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=6)

        # Verify memory at $15 was decremented
        assert nmos_cpu.ram[0x15] == 0x42
        # Verify comparison: A (0x42) == M (0x42)
        assert nmos_cpu.Z == 1
        assert nmos_cpu.C == 1
        assert nmos_cpu.cycles_executed == 6

    def test_dcp_absolute(self, nmos_cpu) -> None:
        """Test DCP absolute addressing."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x20
        nmos_cpu.ram[0x4567] = 0x30  # Will decrement to 0x2F

        nmos_cpu.ram[0xFFFC] = instructions.DCP_ABSOLUTE_0xCF
        nmos_cpu.ram[0xFFFD] = 0x67
        nmos_cpu.ram[0xFFFE] = 0x45

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=6)

        # Verify memory was decremented
        assert nmos_cpu.ram[0x4567] == 0x2F
        # Verify comparison: A (0x20) < M (0x2F)
        assert nmos_cpu.Z == 0
        assert nmos_cpu.C == 0  # Borrow needed
        assert nmos_cpu.N == 1  # (0x20 - 0x2F) & 0xFF = 0xF1
        assert nmos_cpu.cycles_executed == 6

    def test_dcp_absolute_x(self, nmos_cpu) -> None:
        """Test DCP absolute,X addressing."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x50
        nmos_cpu.X = 0x10
        nmos_cpu.ram[0x1234 + 0x10] = 0x51  # Will decrement to 0x50

        nmos_cpu.ram[0xFFFC] = instructions.DCP_ABSOLUTE_X_0xDF
        nmos_cpu.ram[0xFFFD] = 0x34
        nmos_cpu.ram[0xFFFE] = 0x12

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=7)

        # Verify memory was decremented
        assert nmos_cpu.ram[0x1244] == 0x50
        assert nmos_cpu.Z == 1
        assert nmos_cpu.cycles_executed == 7

    def test_dcp_absolute_y(self, nmos_cpu) -> None:
        """Test DCP absolute,Y addressing."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x60
        nmos_cpu.Y = 0x20
        nmos_cpu.ram[0x2000 + 0x20] = 0x61  # Will decrement to 0x60

        nmos_cpu.ram[0xFFFC] = instructions.DCP_ABSOLUTE_Y_0xDB
        nmos_cpu.ram[0xFFFD] = 0x00
        nmos_cpu.ram[0xFFFE] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=7)

        # Verify memory was decremented
        assert nmos_cpu.ram[0x2020] == 0x60
        assert nmos_cpu.Z == 1
        assert nmos_cpu.cycles_executed == 7

    def test_dcp_indexed_indirect_x(self, nmos_cpu) -> None:
        """Test DCP (indirect,X) addressing."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x70
        nmos_cpu.X = 0x04

        # Pointer at $10 + $04 = $14 points to $3000
        nmos_cpu.ram[0x14] = 0x00
        nmos_cpu.ram[0x15] = 0x30
        nmos_cpu.ram[0x3000] = 0x71  # Will decrement to 0x70

        nmos_cpu.ram[0xFFFC] = instructions.DCP_INDEXED_INDIRECT_X_0xC3
        nmos_cpu.ram[0xFFFD] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=8)

        # Verify memory was decremented
        assert nmos_cpu.ram[0x3000] == 0x70
        assert nmos_cpu.Z == 1
        assert nmos_cpu.cycles_executed == 8

    def test_dcp_indirect_indexed_y(self, nmos_cpu) -> None:
        """Test DCP (indirect),Y addressing."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x80
        nmos_cpu.Y = 0x10

        # Pointer at $20 points to $4000, + Y = $4010
        nmos_cpu.ram[0x20] = 0x00
        nmos_cpu.ram[0x21] = 0x40
        nmos_cpu.ram[0x4010] = 0x81  # Will decrement to 0x80

        nmos_cpu.ram[0xFFFC] = instructions.DCP_INDIRECT_INDEXED_Y_0xD3
        nmos_cpu.ram[0xFFFD] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=8)

        # Verify memory was decremented
        assert nmos_cpu.ram[0x4010] == 0x80
        assert nmos_cpu.Z == 1
        assert nmos_cpu.cycles_executed == 8


class TestDCPCMOS:
    """Test DCP instruction on CMOS variant (65C02) - acts as NOP."""

    def test_dcp_acts_as_nop(self, cmos_cpu) -> None:
        """Test DCP acts as NOP on CMOS (65C02)."""
        cmos_cpu.reset()
        cmos_cpu.A = 0x50
        cmos_cpu.ram[0x10] = 0x51

        cmos_cpu.ram[0xFFFC] = instructions.DCP_ZEROPAGE_0xC7
        cmos_cpu.ram[0xFFFD] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(cycles=5)

        # Verify memory is unchanged (NOP behavior)
        assert cmos_cpu.ram[0x10] == 0x51
        # Verify A is unchanged
        assert cmos_cpu.A == 0x50
        # Verify no flags are modified
        assert cmos_cpu.Z == 0
        assert cmos_cpu.N == 0
        assert cmos_cpu.C == 0
        assert cmos_cpu.cycles_executed == 5
