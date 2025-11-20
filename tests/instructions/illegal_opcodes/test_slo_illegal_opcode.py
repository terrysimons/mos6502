"""Tests for SLO (Shift Left and OR) illegal instruction.

SLO is a stable illegal instruction on NMOS 6502 that shifts a memory location
left by one bit and then performs a bitwise OR with the accumulator. On CMOS
65C02, it acts as a NOP.

Operation: M = M << 1, A = A | M

Opcodes:
    $07 - SLO Zero Page (5 cycles)
    $17 - SLO Zero Page,X (6 cycles)
    $03 - SLO (Indirect,X) (8 cycles)
    $13 - SLO (Indirect),Y (8 cycles)
    $0F - SLO Absolute (6 cycles)
    $1F - SLO Absolute,X (7 cycles)
    $1B - SLO Absolute,Y (7 cycles)

Flags: N, Z, C

References:
    - https://masswerk.at/6502/6502_instruction_set.html#SLO
    - http://www.oxyron.de/html/opcodes02.html
"""
import contextlib

from mos6502 import errors, instructions


class TestSLONMOS:
    """Test SLO instruction on NMOS variants (6502, 6502A, 6502C)."""

    def test_slo_zeropage_shifts_and_ors(self, nmos_cpu):
        """Test SLO zero page shifts memory left and ORs with A."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x0F
        nmos_cpu.ram[0x10] = 0x55  # 01010101, will shift to 10101010 (0xAA)

        nmos_cpu.ram[0xFFFC] = instructions.SLO_ZEROPAGE_0x07
        nmos_cpu.ram[0xFFFD] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory was shifted: 0x55 << 1 = 0xAA
        assert nmos_cpu.ram[0x10] == 0xAA
        # Verify OR: A = 0x0F | 0xAA = 0xAF
        assert nmos_cpu.A == 0xAF
        # Verify flags
        assert nmos_cpu.Z == 0  # Not zero
        assert nmos_cpu.C == 0  # Bit 7 of original was 0
        assert nmos_cpu.N == 1  # Result bit 7 is set
        assert nmos_cpu.cycles_executed == 5

    def test_slo_sets_carry(self, nmos_cpu):
        """Test SLO sets carry when bit 7 of original value is set."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x00
        nmos_cpu.ram[0x20] = 0x81  # 10000001, bit 7 set

        nmos_cpu.ram[0xFFFC] = instructions.SLO_ZEROPAGE_0x07
        nmos_cpu.ram[0xFFFD] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory was shifted: 0x81 << 1 = 0x02
        assert nmos_cpu.ram[0x20] == 0x02
        # Verify OR: A = 0x00 | 0x02 = 0x02
        assert nmos_cpu.A == 0x02
        # Verify carry flag set (bit 7 was 1)
        assert nmos_cpu.C == 1
        assert nmos_cpu.N == 0
        assert nmos_cpu.Z == 0

    def test_slo_sets_zero_flag(self, nmos_cpu):
        """Test SLO sets zero flag when result is zero."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x00
        nmos_cpu.ram[0x30] = 0x00  # Will shift to 0x00

        nmos_cpu.ram[0xFFFC] = instructions.SLO_ZEROPAGE_0x07
        nmos_cpu.ram[0xFFFD] = 0x30

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory was shifted: 0x00 << 1 = 0x00
        assert nmos_cpu.ram[0x30] == 0x00
        # Verify OR: A = 0x00 | 0x00 = 0x00
        assert nmos_cpu.A == 0x00
        # Verify zero flag set
        assert nmos_cpu.Z == 1
        assert nmos_cpu.N == 0
        assert nmos_cpu.C == 0

    def test_slo_or_operation(self, nmos_cpu):
        """Test SLO OR operation combines properly."""
        nmos_cpu.reset()
        nmos_cpu.A = 0xF0  # 11110000
        nmos_cpu.ram[0x40] = 0x03  # 00000011, shifts to 00000110 (0x06)

        nmos_cpu.ram[0xFFFC] = instructions.SLO_ZEROPAGE_0x07
        nmos_cpu.ram[0xFFFD] = 0x40

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory was shifted: 0x03 << 1 = 0x06
        assert nmos_cpu.ram[0x40] == 0x06
        # Verify OR: A = 0xF0 | 0x06 = 0xF6
        assert nmos_cpu.A == 0xF6
        assert nmos_cpu.N == 1  # Bit 7 set
        assert nmos_cpu.Z == 0

    def test_slo_shift_wraps(self, nmos_cpu):
        """Test SLO shift operation wraps at 8 bits."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x00
        nmos_cpu.ram[0x50] = 0xFF  # 11111111, shifts to 11111110 (0xFE), C=1

        nmos_cpu.ram[0xFFFC] = instructions.SLO_ZEROPAGE_0x07
        nmos_cpu.ram[0xFFFD] = 0x50

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify shift: 0xFF << 1 = 0xFE (with carry out)
        assert nmos_cpu.ram[0x50] == 0xFE
        assert nmos_cpu.A == 0xFE
        assert nmos_cpu.C == 1  # Bit 7 was set
        assert nmos_cpu.N == 1

    def test_slo_zeropage_x(self, nmos_cpu):
        """Test SLO zero page,X with offset."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x01
        nmos_cpu.X = 0x05
        nmos_cpu.ram[0x15] = 0x04  # At $10 + $05, shifts to 0x08

        nmos_cpu.ram[0xFFFC] = instructions.SLO_ZEROPAGE_X_0x17
        nmos_cpu.ram[0xFFFD] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=6)

        # Verify memory at $15 was shifted
        assert nmos_cpu.ram[0x15] == 0x08
        # Verify OR: A = 0x01 | 0x08 = 0x09
        assert nmos_cpu.A == 0x09
        assert nmos_cpu.cycles_executed == 6

    def test_slo_absolute(self, nmos_cpu):
        """Test SLO absolute addressing."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x11
        nmos_cpu.ram[0x4567] = 0x22  # Shifts to 0x44

        nmos_cpu.ram[0xFFFC] = instructions.SLO_ABSOLUTE_0x0F
        nmos_cpu.ram[0xFFFD] = 0x67
        nmos_cpu.ram[0xFFFE] = 0x45

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=6)

        # Verify memory was shifted
        assert nmos_cpu.ram[0x4567] == 0x44
        # Verify OR: A = 0x11 | 0x44 = 0x55
        assert nmos_cpu.A == 0x55
        assert nmos_cpu.cycles_executed == 6

    def test_slo_absolute_x(self, nmos_cpu):
        """Test SLO absolute,X addressing."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x0A
        nmos_cpu.X = 0x10
        nmos_cpu.ram[0x1234 + 0x10] = 0x05  # Shifts to 0x0A

        nmos_cpu.ram[0xFFFC] = instructions.SLO_ABSOLUTE_X_0x1F
        nmos_cpu.ram[0xFFFD] = 0x34
        nmos_cpu.ram[0xFFFE] = 0x12

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=7)

        # Verify memory was shifted
        assert nmos_cpu.ram[0x1244] == 0x0A
        # Verify OR: A = 0x0A | 0x0A = 0x0A
        assert nmos_cpu.A == 0x0A
        assert nmos_cpu.cycles_executed == 7

    def test_slo_absolute_y(self, nmos_cpu):
        """Test SLO absolute,Y addressing."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x20
        nmos_cpu.Y = 0x20
        nmos_cpu.ram[0x2000 + 0x20] = 0x10  # Shifts to 0x20

        nmos_cpu.ram[0xFFFC] = instructions.SLO_ABSOLUTE_Y_0x1B
        nmos_cpu.ram[0xFFFD] = 0x00
        nmos_cpu.ram[0xFFFE] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=7)

        # Verify memory was shifted
        assert nmos_cpu.ram[0x2020] == 0x20
        # Verify OR: A = 0x20 | 0x20 = 0x20
        assert nmos_cpu.A == 0x20
        assert nmos_cpu.cycles_executed == 7

    def test_slo_indexed_indirect_x(self, nmos_cpu):
        """Test SLO (indirect,X) addressing."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x01
        nmos_cpu.X = 0x04

        # Pointer at $10 + $04 = $14 points to $3000
        nmos_cpu.ram[0x14] = 0x00
        nmos_cpu.ram[0x15] = 0x30
        nmos_cpu.ram[0x3000] = 0x02  # Shifts to 0x04

        nmos_cpu.ram[0xFFFC] = instructions.SLO_INDEXED_INDIRECT_X_0x03
        nmos_cpu.ram[0xFFFD] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=8)

        # Verify memory was shifted
        assert nmos_cpu.ram[0x3000] == 0x04
        # Verify OR: A = 0x01 | 0x04 = 0x05
        assert nmos_cpu.A == 0x05
        assert nmos_cpu.cycles_executed == 8

    def test_slo_indirect_indexed_y(self, nmos_cpu):
        """Test SLO (indirect),Y addressing."""
        nmos_cpu.reset()
        nmos_cpu.A = 0x08
        nmos_cpu.Y = 0x10

        # Pointer at $20 points to $4000, + Y = $4010
        nmos_cpu.ram[0x20] = 0x00
        nmos_cpu.ram[0x21] = 0x40
        nmos_cpu.ram[0x4010] = 0x04  # Shifts to 0x08

        nmos_cpu.ram[0xFFFC] = instructions.SLO_INDIRECT_INDEXED_Y_0x13
        nmos_cpu.ram[0xFFFD] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=8)

        # Verify memory was shifted
        assert nmos_cpu.ram[0x4010] == 0x08
        # Verify OR: A = 0x08 | 0x08 = 0x08
        assert nmos_cpu.A == 0x08
        assert nmos_cpu.cycles_executed == 8


class TestSLOCMOS:
    """Test SLO instruction on CMOS variant (65C02) - acts as NOP."""

    def test_slo_acts_as_nop(self, cmos_cpu):
        """Test SLO acts as NOP on CMOS (65C02)."""
        cmos_cpu.reset()
        cmos_cpu.A = 0x0F
        cmos_cpu.ram[0x10] = 0x55

        cmos_cpu.ram[0xFFFC] = instructions.SLO_ZEROPAGE_0x07
        cmos_cpu.ram[0xFFFD] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(cycles=5)

        # Verify memory is unchanged (NOP behavior)
        assert cmos_cpu.ram[0x10] == 0x55
        # Verify A is unchanged
        assert cmos_cpu.A == 0x0F
        # Verify no flags are modified
        assert cmos_cpu.Z == 0
        assert cmos_cpu.N == 0
        assert cmos_cpu.C == 0
        assert cmos_cpu.cycles_executed == 5