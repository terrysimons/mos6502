"""Tests for SHA (AHX, AXA) illegal instruction.

SHA is an UNSTABLE illegal instruction on NMOS 6502.
On 65C02 (CMOS), this opcode acts as a NOP.

Operation: Memory = A & X & (high_byte_of_address + 1)

References:
    - http://www.oxyron.de/html/opcodes02.html
    - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""
import contextlib

from mos6502 import errors, instructions


class TestSHANMOS:
    """Test SHA instruction on NMOS variants (6502, 6502A, 6502C)."""

    def test_sha_absolute_y_basic(self, nmos_cpu) -> None:
        """Test SHA absolute,Y basic operation."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.X = 0xFF
        nmos_cpu.Y = 0x10

        # Address $1200, high byte = $12, so value = 0xFF & 0xFF & ($12 + 1) = $13
        nmos_cpu.ram[nmos_cpu.PC] = instructions.SHA_ABSOLUTE_Y_0x9F
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x00  # Low byte
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0x12  # High byte

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        # Memory at $1200 + $10 = $1210 should have A & X & (high+1)
        assert nmos_cpu.ram[0x1210] == (0xFF & 0xFF & 0x13)
        assert nmos_cpu.PC == 0x0403

    def test_sha_absolute_y_and_masks(self, nmos_cpu) -> None:
        """Test SHA AND operations with different values."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xAA
        nmos_cpu.X = 0x55
        nmos_cpu.Y = 0x00

        # Address $3400, high byte = $34, value = 0xAA & 0x55 & 0x35 = 0x00
        nmos_cpu.ram[nmos_cpu.PC] = instructions.SHA_ABSOLUTE_Y_0x9F
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x00
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0x34

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        # A & X = 0xAA & 0x55 = 0x00, so result is 0
        assert nmos_cpu.ram[0x3400] == 0x00

    def test_sha_indirect_indexed_y_basic(self, nmos_cpu) -> None:
        """Test SHA (indirect),Y basic operation."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.X = 0xFF
        nmos_cpu.Y = 0x05

        # Zero page pointer at $20 points to $2100
        nmos_cpu.ram[0x20] = 0x00  # Low byte
        nmos_cpu.ram[0x21] = 0x21  # High byte = $21

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SHA_INDIRECT_INDEXED_Y_0x93
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        # Memory at $2100 + $05 = $2105 should have A & X & ($21 + 1) = 0xFF & 0xFF & 0x22
        assert nmos_cpu.ram[0x2105] == 0x22
        assert nmos_cpu.PC == 0x0402

    def test_sha_preserves_registers(self, nmos_cpu) -> None:
        """Test SHA does not modify A or X registers."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xAB
        nmos_cpu.X = 0xCD
        nmos_cpu.Y = 0x00

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SHA_ABSOLUTE_Y_0x9F
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x00
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        assert nmos_cpu.A == 0xAB
        assert nmos_cpu.X == 0xCD

    def test_sha_preserves_flags(self, nmos_cpu) -> None:
        """Test SHA does not modify flags."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.X = 0xFF
        nmos_cpu.Y = 0x00
        nmos_cpu.N = 1
        nmos_cpu.Z = 1
        nmos_cpu.C = 1
        nmos_cpu.V = 1

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SHA_ABSOLUTE_Y_0x9F
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x00
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        assert nmos_cpu.N == 1
        assert nmos_cpu.Z == 1
        assert nmos_cpu.C == 1
        assert nmos_cpu.V == 1


class TestSHACMOS:
    """Test SHA instruction on CMOS variant (65C02) - acts as NOP."""

    def test_sha_absolute_y_acts_as_nop(self, cmos_cpu) -> None:
        """Test SHA absolute,Y acts as NOP on CMOS."""
        cmos_cpu.reset()
        cmos_cpu.PC = 0x0400
        cmos_cpu.A = 0xFF
        cmos_cpu.X = 0xFF
        cmos_cpu.Y = 0x10
        cmos_cpu.ram[0x1210] = 0x42  # Pre-set

        cmos_cpu.ram[cmos_cpu.PC] = instructions.SHA_ABSOLUTE_Y_0x9F
        cmos_cpu.ram[cmos_cpu.PC + 1] = 0x00
        cmos_cpu.ram[cmos_cpu.PC + 2] = 0x12

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(max_instructions=1)

        # Memory should be unchanged
        assert cmos_cpu.ram[0x1210] == 0x42
        # Registers unchanged
        assert cmos_cpu.A == 0xFF
        assert cmos_cpu.X == 0xFF
        # PC advances by 3
        assert cmos_cpu.PC == 0x0403

    def test_sha_indirect_indexed_y_acts_as_nop(self, cmos_cpu) -> None:
        """Test SHA (indirect),Y acts as NOP on CMOS."""
        cmos_cpu.reset()
        cmos_cpu.PC = 0x0400
        cmos_cpu.A = 0xFF
        cmos_cpu.X = 0xFF
        cmos_cpu.Y = 0x05

        # Zero page pointer at $20 points to $2100
        cmos_cpu.ram[0x20] = 0x00
        cmos_cpu.ram[0x21] = 0x21
        cmos_cpu.ram[0x2105] = 0x99  # Pre-set

        cmos_cpu.ram[cmos_cpu.PC] = instructions.SHA_INDIRECT_INDEXED_Y_0x93
        cmos_cpu.ram[cmos_cpu.PC + 1] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(max_instructions=1)

        # Memory should be unchanged
        assert cmos_cpu.ram[0x2105] == 0x99
        # PC advances by 2
        assert cmos_cpu.PC == 0x0402
