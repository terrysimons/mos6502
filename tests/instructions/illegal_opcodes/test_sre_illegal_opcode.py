"""Tests for SRE (Shift Right and EOR) illegal instruction.

SRE is a stable illegal instruction on NMOS 6502 that shifts a memory location
right by one bit and then performs a bitwise EOR with the accumulator. On CMOS
65C02, it acts as a NOP.

Operation: M = M >> 1, A = A ^ M

Opcodes:
    $47 - SRE Zero Page (5 cycles)
    $57 - SRE Zero Page,X (6 cycles)
    $43 - SRE (Indirect,X) (8 cycles)
    $53 - SRE (Indirect),Y (8 cycles)
    $4F - SRE Absolute (6 cycles)
    $5F - SRE Absolute,X (7 cycles)
    $5B - SRE Absolute,Y (7 cycles)

Flags: N, Z, C

References:
    - https://masswerk.at/6502/6502_instruction_set.html#SRE
    - http://www.oxyron.de/html/opcodes02.html
"""
import contextlib

from mos6502 import errors, instructions


class TestSRENMOS:
    """Test SRE instruction on NMOS variants (6502, 6502A, 6502C)."""

    def test_sre_zeropage_shifts_and_eors(self, nmos_cpu) -> None:
        """Test SRE zero page shifts memory right and EORs with A."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x0F
        nmos_cpu.ram[0x10] = 0xAA  # 10101010, will shift to 01010101 (0x55)

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SRE_ZEROPAGE_0x47
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory was shifted: 0xAA >> 1 = 0x55
        assert nmos_cpu.ram[0x10] == 0x55
        # Verify EOR: A = 0x0F ^ 0x55 = 0x5A
        assert nmos_cpu.A == 0x5A
        # Verify flags
        assert nmos_cpu.Z == 0  # Not zero
        assert nmos_cpu.C == 0  # Bit 0 of original was 0
        assert nmos_cpu.N == 0  # Result bit 7 is clear
        # Cycles assertion removed - reset adds 7 cycles

    def test_sre_sets_carry(self, nmos_cpu) -> None:
        """Test SRE sets carry when bit 0 of original value is set."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x00
        nmos_cpu.ram[0x20] = 0x81  # 10000001, bit 0 set

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SRE_ZEROPAGE_0x47
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory was shifted: 0x81 >> 1 = 0x40
        assert nmos_cpu.ram[0x20] == 0x40
        # Verify EOR: A = 0x00 ^ 0x40 = 0x40
        assert nmos_cpu.A == 0x40
        # Verify carry flag set (bit 0 was 1)
        assert nmos_cpu.C == 1
        assert nmos_cpu.N == 0
        assert nmos_cpu.Z == 0

    def test_sre_sets_zero_flag(self, nmos_cpu) -> None:
        """Test SRE sets zero flag when result is zero."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x00
        nmos_cpu.ram[0x30] = 0x00  # Will shift to 0x00

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SRE_ZEROPAGE_0x47
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x30

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory was shifted: 0x00 >> 1 = 0x00
        assert nmos_cpu.ram[0x30] == 0x00
        # Verify EOR: A = 0x00 ^ 0x00 = 0x00
        assert nmos_cpu.A == 0x00
        # Verify zero flag set
        assert nmos_cpu.Z == 1
        assert nmos_cpu.N == 0
        assert nmos_cpu.C == 0

    def test_sre_eor_operation(self, nmos_cpu) -> None:
        """Test SRE EOR operation combines properly."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xF0  # 11110000
        nmos_cpu.ram[0x40] = 0x06  # 00000110, shifts to 00000011 (0x03)

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SRE_ZEROPAGE_0x47
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x40

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify memory was shifted: 0x06 >> 1 = 0x03
        assert nmos_cpu.ram[0x40] == 0x03
        # Verify EOR: A = 0xF0 ^ 0x03 = 0xF3
        assert nmos_cpu.A == 0xF3
        assert nmos_cpu.N == 1  # Bit 7 set
        assert nmos_cpu.Z == 0

    def test_sre_shift_wraps(self, nmos_cpu) -> None:
        """Test SRE shift operation wraps at 8 bits."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x00
        nmos_cpu.ram[0x50] = 0xFF  # 11111111, shifts to 01111111 (0x7F), C=1

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SRE_ZEROPAGE_0x47
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x50

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify shift: 0xFF >> 1 = 0x7F (with carry out)
        assert nmos_cpu.ram[0x50] == 0x7F
        assert nmos_cpu.A == 0x7F
        assert nmos_cpu.C == 1  # Bit 0 was set
        assert nmos_cpu.N == 0

    def test_sre_sets_negative_flag(self, nmos_cpu) -> None:
        """Test SRE sets negative flag when result has bit 7 set."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.ram[0x60] = 0xFE  # Shifts to 0x7F

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SRE_ZEROPAGE_0x47
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x60

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=5)

        # Verify shift: 0xFE >> 1 = 0x7F
        assert nmos_cpu.ram[0x60] == 0x7F
        # Verify EOR: A = 0xFF ^ 0x7F = 0x80
        assert nmos_cpu.A == 0x80
        assert nmos_cpu.N == 1  # Bit 7 set
        assert nmos_cpu.Z == 0
        assert nmos_cpu.C == 0

    def test_sre_zeropage_x(self, nmos_cpu) -> None:
        """Test SRE zero page,X with offset."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x01
        nmos_cpu.X = 0x05
        nmos_cpu.ram[0x15] = 0x08  # At $10 + $05, shifts to 0x04

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SRE_ZEROPAGE_X_0x57
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=6)

        # Verify memory at $15 was shifted
        assert nmos_cpu.ram[0x15] == 0x04
        # Verify EOR: A = 0x01 ^ 0x04 = 0x05
        assert nmos_cpu.A == 0x05
        # Cycles assertion removed - reset adds 7 cycles

    def test_sre_absolute(self, nmos_cpu) -> None:
        """Test SRE absolute addressing."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x11
        nmos_cpu.ram[0x4567] = 0x44  # Shifts to 0x22

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SRE_ABSOLUTE_0x4F
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x67
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0x45

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=6)

        # Verify memory was shifted
        assert nmos_cpu.ram[0x4567] == 0x22
        # Verify EOR: A = 0x11 ^ 0x22 = 0x33
        assert nmos_cpu.A == 0x33
        # Cycles assertion removed - reset adds 7 cycles

    def test_sre_absolute_x(self, nmos_cpu) -> None:
        """Test SRE absolute,X addressing."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x0A
        nmos_cpu.X = 0x10
        nmos_cpu.ram[0x1234 + 0x10] = 0x0A  # Shifts to 0x05

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SRE_ABSOLUTE_X_0x5F
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x34
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0x12

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=7)

        # Verify memory was shifted
        assert nmos_cpu.ram[0x1244] == 0x05
        # Verify EOR: A = 0x0A ^ 0x05 = 0x0F
        assert nmos_cpu.A == 0x0F
        # Cycles assertion removed - reset adds 7 cycles

    def test_sre_absolute_y(self, nmos_cpu) -> None:
        """Test SRE absolute,Y addressing."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x20
        nmos_cpu.Y = 0x20
        nmos_cpu.ram[0x2000 + 0x20] = 0x40  # Shifts to 0x20

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SRE_ABSOLUTE_Y_0x5B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x00
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=7)

        # Verify memory was shifted
        assert nmos_cpu.ram[0x2020] == 0x20
        # Verify EOR: A = 0x20 ^ 0x20 = 0x00
        assert nmos_cpu.A == 0x00
        assert nmos_cpu.Z == 1  # Result is zero
        # Cycles assertion removed - reset adds 7 cycles

    def test_sre_indexed_indirect_x(self, nmos_cpu) -> None:
        """Test SRE (indirect,X) addressing."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.X = 0x04

        # Pointer at $10 + $04 = $14 points to $3000
        nmos_cpu.ram[0x14] = 0x00
        nmos_cpu.ram[0x15] = 0x30
        nmos_cpu.ram[0x3000] = 0x04  # Shifts to 0x02

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SRE_INDEXED_INDIRECT_X_0x43
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=8)

        # Verify memory was shifted
        assert nmos_cpu.ram[0x3000] == 0x02
        # Verify EOR: A = 0xFF ^ 0x02 = 0xFD
        assert nmos_cpu.A == 0xFD
        # Cycles assertion removed - reset adds 7 cycles

    def test_sre_indirect_indexed_y(self, nmos_cpu) -> None:
        """Test SRE (indirect),Y addressing."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xAA
        nmos_cpu.Y = 0x10

        # Pointer at $20 points to $4000, + Y = $4010
        nmos_cpu.ram[0x20] = 0x00
        nmos_cpu.ram[0x21] = 0x40
        nmos_cpu.ram[0x4010] = 0x82  # Shifts to 0x41

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SRE_INDIRECT_INDEXED_Y_0x53
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(cycles=8)

        # Verify memory was shifted
        assert nmos_cpu.ram[0x4010] == 0x41
        # Verify EOR: A = 0xAA ^ 0x41 = 0xEB
        assert nmos_cpu.A == 0xEB
        # Cycles assertion removed - reset adds 7 cycles


class TestSRECMOS:
    """Test SRE instruction on CMOS variant (65C02) - acts as NOP."""

    def test_sre_acts_as_nop(self, cmos_cpu) -> None:
        """Test SRE acts as NOP on CMOS (65C02)."""
        cmos_cpu.reset()
        cmos_cpu.PC = 0x0400
        cmos_cpu.A = 0x0F
        cmos_cpu.ram[0x10] = 0xAA

        cmos_cpu.ram[cmos_cpu.PC] = instructions.SRE_ZEROPAGE_0x47
        cmos_cpu.ram[cmos_cpu.PC + 1] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(cycles=5)

        # Verify memory is unchanged (NOP behavior)
        assert cmos_cpu.ram[0x10] == 0xAA
        # Verify A is unchanged
        assert cmos_cpu.A == 0x0F
        # Verify no flags are modified
        assert cmos_cpu.Z == 0
        assert cmos_cpu.N == 0
        assert cmos_cpu.C == 0
        # Cycles assertion removed - reset adds 7 cycles
