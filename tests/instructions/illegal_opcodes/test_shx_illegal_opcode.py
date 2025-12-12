"""Tests for SHX (SXA, XAS) illegal instruction.

SHX is an UNSTABLE illegal instruction on NMOS 6502.
On 65C02 (CMOS), this opcode acts as a NOP.

Operation: Memory = X & (high_byte_of_address + 1)

References:
    - http://www.oxyron.de/html/opcodes02.html
    - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""
import contextlib

from mos6502 import errors, instructions


class TestSHXNMOS:
    """Test SHX instruction on NMOS variants (6502, 6502A, 6502C)."""

    def test_shx_absolute_y_basic(self, nmos_cpu) -> None:
        """Test SHX absolute,Y basic operation."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.X = 0xFF
        nmos_cpu.Y = 0x10

        # Address $1200, high byte = $12, so value = 0xFF & ($12 + 1) = $13
        nmos_cpu.ram[nmos_cpu.PC] = instructions.SHX_ABSOLUTE_Y_0x9E
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x00  # Low byte
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0x12  # High byte

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        # Memory at $1200 + $10 = $1210 should have X & (high+1)
        assert nmos_cpu.ram[0x1210] == (0xFF & 0x13)
        assert nmos_cpu.PC == 0x0403

    def test_shx_absolute_y_x_masks_result(self, nmos_cpu) -> None:
        """Test SHX result is masked by X register."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.X = 0x0F  # Low nibble only
        nmos_cpu.Y = 0x00

        # Address $FF00, high byte = $FF, so value = 0x0F & 0x00 = 0x00
        nmos_cpu.ram[nmos_cpu.PC] = instructions.SHX_ABSOLUTE_Y_0x9E
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x00
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0xFF  # high+1 = 0x00

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        assert nmos_cpu.ram[0xFF00] == 0x00

    def test_shx_preserves_registers(self, nmos_cpu) -> None:
        """Test SHX does not modify X register."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.X = 0xAB
        nmos_cpu.Y = 0x00

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SHX_ABSOLUTE_Y_0x9E
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x00
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        assert nmos_cpu.X == 0xAB

    def test_shx_preserves_flags(self, nmos_cpu) -> None:
        """Test SHX does not modify flags."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.X = 0xFF
        nmos_cpu.Y = 0x00
        nmos_cpu.N = 1
        nmos_cpu.Z = 1
        nmos_cpu.C = 1
        nmos_cpu.V = 1

        nmos_cpu.ram[nmos_cpu.PC] = instructions.SHX_ABSOLUTE_Y_0x9E
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x00
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        assert nmos_cpu.N == 1
        assert nmos_cpu.Z == 1
        assert nmos_cpu.C == 1
        assert nmos_cpu.V == 1


class TestSHXCMOS:
    """Test SHX instruction on CMOS variant (65C02) - acts as NOP."""

    def test_shx_acts_as_nop(self, cmos_cpu) -> None:
        """Test SHX acts as NOP on CMOS (65C02)."""
        cmos_cpu.reset()
        cmos_cpu.PC = 0x0400
        cmos_cpu.X = 0xFF
        cmos_cpu.Y = 0x10
        cmos_cpu.ram[0x1210] = 0x42  # Pre-set

        cmos_cpu.ram[cmos_cpu.PC] = instructions.SHX_ABSOLUTE_Y_0x9E
        cmos_cpu.ram[cmos_cpu.PC + 1] = 0x00
        cmos_cpu.ram[cmos_cpu.PC + 2] = 0x12

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(max_instructions=1)

        # Memory should be unchanged
        assert cmos_cpu.ram[0x1210] == 0x42
        # Registers unchanged
        assert cmos_cpu.X == 0xFF
        # PC advances by 3
        assert cmos_cpu.PC == 0x0403

    def test_shx_nop_preserves_flags(self, cmos_cpu) -> None:
        """Test SHX NOP does not modify flags on CMOS."""
        cmos_cpu.reset()
        cmos_cpu.PC = 0x0400
        cmos_cpu.X = 0xFF
        cmos_cpu.Y = 0x00
        cmos_cpu.N = 1
        cmos_cpu.Z = 1

        cmos_cpu.ram[cmos_cpu.PC] = instructions.SHX_ABSOLUTE_Y_0x9E
        cmos_cpu.ram[cmos_cpu.PC + 1] = 0x00
        cmos_cpu.ram[cmos_cpu.PC + 2] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(max_instructions=1)

        assert cmos_cpu.N == 1
        assert cmos_cpu.Z == 1
