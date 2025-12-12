"""Tests for TAS (XAS, SHS) illegal instruction.

TAS is an UNSTABLE illegal instruction on NMOS 6502.
On 65C02 (CMOS), this opcode acts as a NOP.

Operation:
1. S = A & X (store A AND X into stack pointer)
2. Memory = A & X & (high_byte_of_address + 1)

References:
    - http://www.oxyron.de/html/opcodes02.html
    - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""
import contextlib

from mos6502 import errors, instructions


class TestTASNMOS:
    """Test TAS instruction on NMOS variants (6502, 6502A, 6502C)."""

    def test_tas_basic_operation(self, nmos_cpu) -> None:
        """Test TAS basic operation: sets S and stores to memory."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.X = 0xFF
        nmos_cpu.Y = 0x10

        # Address $1200, high byte = $12
        nmos_cpu.ram[nmos_cpu.PC] = instructions.TAS_ABSOLUTE_Y_0x9B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x00  # Low byte
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0x12  # High byte

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        # S = A & X = 0xFF & 0xFF = 0xFF (stored with 0x100 offset internally = 0x1FF)
        assert (nmos_cpu.S & 0xFF) == 0xFF

        # Memory at $1210 = A & X & (high+1) = 0xFF & 0xFF & 0x13 = 0x13
        assert nmos_cpu.ram[0x1210] == 0x13
        assert nmos_cpu.PC == 0x0403

    def test_tas_stack_pointer_update(self, nmos_cpu) -> None:
        """Test TAS updates stack pointer to A & X."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xAA
        nmos_cpu.X = 0x55
        nmos_cpu.Y = 0x00

        nmos_cpu.ram[nmos_cpu.PC] = instructions.TAS_ABSOLUTE_Y_0x9B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x00
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        # S = A & X = 0xAA & 0x55 = 0x00
        assert (nmos_cpu.S & 0xFF) == 0x00

    def test_tas_memory_store(self, nmos_cpu) -> None:
        """Test TAS stores A & X & (high+1) to memory."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x0F
        nmos_cpu.X = 0xFF
        nmos_cpu.Y = 0x00

        # Address $2000, high byte = $20, value = 0x0F & 0xFF & 0x21 = 0x01
        nmos_cpu.ram[nmos_cpu.PC] = instructions.TAS_ABSOLUTE_Y_0x9B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x00
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        assert nmos_cpu.ram[0x2000] == 0x01

    def test_tas_preserves_a_and_x(self, nmos_cpu) -> None:
        """Test TAS does not modify A or X registers."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xAB
        nmos_cpu.X = 0xCD
        nmos_cpu.Y = 0x00

        nmos_cpu.ram[nmos_cpu.PC] = instructions.TAS_ABSOLUTE_Y_0x9B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x00
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        assert nmos_cpu.A == 0xAB
        assert nmos_cpu.X == 0xCD

    def test_tas_preserves_flags(self, nmos_cpu) -> None:
        """Test TAS does not modify flags."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.X = 0xFF
        nmos_cpu.Y = 0x00
        nmos_cpu.N = 1
        nmos_cpu.Z = 1
        nmos_cpu.C = 1
        nmos_cpu.V = 1

        nmos_cpu.ram[nmos_cpu.PC] = instructions.TAS_ABSOLUTE_Y_0x9B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x00
        nmos_cpu.ram[nmos_cpu.PC + 2] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        assert nmos_cpu.N == 1
        assert nmos_cpu.Z == 1
        assert nmos_cpu.C == 1
        assert nmos_cpu.V == 1


class TestTASCMOS:
    """Test TAS instruction on CMOS variant (65C02) - acts as NOP."""

    def test_tas_acts_as_nop(self, cmos_cpu) -> None:
        """Test TAS acts as NOP on CMOS (65C02)."""
        cmos_cpu.reset()
        cmos_cpu.PC = 0x0400
        cmos_cpu.A = 0xFF
        cmos_cpu.X = 0xFF
        cmos_cpu.Y = 0x10
        original_s = cmos_cpu.S
        cmos_cpu.ram[0x1210] = 0x42  # Pre-set

        cmos_cpu.ram[cmos_cpu.PC] = instructions.TAS_ABSOLUTE_Y_0x9B
        cmos_cpu.ram[cmos_cpu.PC + 1] = 0x00
        cmos_cpu.ram[cmos_cpu.PC + 2] = 0x12

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(max_instructions=1)

        # Memory should be unchanged
        assert cmos_cpu.ram[0x1210] == 0x42
        # Registers unchanged
        assert cmos_cpu.A == 0xFF
        assert cmos_cpu.X == 0xFF
        # Stack pointer unchanged
        assert cmos_cpu.S == original_s
        # PC advances by 3
        assert cmos_cpu.PC == 0x0403

    def test_tas_nop_preserves_flags(self, cmos_cpu) -> None:
        """Test TAS NOP does not modify flags on CMOS."""
        cmos_cpu.reset()
        cmos_cpu.PC = 0x0400
        cmos_cpu.A = 0xFF
        cmos_cpu.X = 0xFF
        cmos_cpu.Y = 0x00
        cmos_cpu.N = 1
        cmos_cpu.Z = 1

        cmos_cpu.ram[cmos_cpu.PC] = instructions.TAS_ABSOLUTE_Y_0x9B
        cmos_cpu.ram[cmos_cpu.PC + 1] = 0x00
        cmos_cpu.ram[cmos_cpu.PC + 2] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(max_instructions=1)

        assert cmos_cpu.N == 1
        assert cmos_cpu.Z == 1
