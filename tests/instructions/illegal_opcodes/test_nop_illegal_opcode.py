"""Tests for illegal NOP instructions.

Illegal NOPs are undocumented NOP variants that exist on both NMOS and CMOS 6502.
They consume operand bytes but do not modify registers or flags.

Categories:
    1-byte implied NOPs (2 cycles): 0x1A, 0x3A, 0x5A, 0x7A, 0xDA, 0xFA
    2-byte immediate NOPs (2 cycles): 0x80, 0x82, 0x89, 0xC2, 0xE2
    2-byte zero page NOPs (3 cycles): 0x04, 0x44, 0x64
    2-byte zero page,X NOPs (4 cycles): 0x14, 0x34, 0x54, 0x74, 0xD4, 0xF4
    3-byte absolute NOP (4 cycles): 0x0C
    3-byte absolute,X NOPs (4+ cycles): 0x1C, 0x3C, 0x5C, 0x7C, 0xDC, 0xFC

References:
    - http://www.oxyron.de/html/opcodes02.html
    - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""
import contextlib

import pytest

from mos6502 import errors, instructions


class TestIllegalNOP1ByteImplied:
    """Test 1-byte implied NOP instructions (2 cycles)."""

    @pytest.mark.parametrize("opcode", [
        instructions.NOP_IMPLIED_0x1A,
        instructions.NOP_IMPLIED_0x3A,
        instructions.NOP_IMPLIED_0x5A,
        instructions.NOP_IMPLIED_0x7A,
        instructions.NOP_IMPLIED_0xDA,
        instructions.NOP_IMPLIED_0xFA,
    ])
    def test_implied_nop_advances_pc_by_1(self, cpu, opcode) -> None:
        """Test 1-byte implied NOP advances PC by 1."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.ram[cpu.PC] = opcode

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        assert cpu.PC == 0x0401

    @pytest.mark.parametrize("opcode", [
        instructions.NOP_IMPLIED_0x1A,
        instructions.NOP_IMPLIED_0x3A,
        instructions.NOP_IMPLIED_0x5A,
        instructions.NOP_IMPLIED_0x7A,
        instructions.NOP_IMPLIED_0xDA,
        instructions.NOP_IMPLIED_0xFA,
    ])
    def test_implied_nop_preserves_registers(self, cpu, opcode) -> None:
        """Test 1-byte implied NOP does not modify registers."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.A = 0x42
        cpu.X = 0x33
        cpu.Y = 0x77
        cpu.ram[cpu.PC] = opcode

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        assert cpu.A == 0x42
        assert cpu.X == 0x33
        assert cpu.Y == 0x77

    @pytest.mark.parametrize("opcode", [
        instructions.NOP_IMPLIED_0x1A,
        instructions.NOP_IMPLIED_0x3A,
        instructions.NOP_IMPLIED_0x5A,
        instructions.NOP_IMPLIED_0x7A,
        instructions.NOP_IMPLIED_0xDA,
        instructions.NOP_IMPLIED_0xFA,
    ])
    def test_implied_nop_preserves_flags(self, cpu, opcode) -> None:
        """Test 1-byte implied NOP does not modify flags."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.N = 1
        cpu.Z = 1
        cpu.C = 1
        cpu.V = 1
        cpu.ram[cpu.PC] = opcode

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        assert cpu.N == 1
        assert cpu.Z == 1
        assert cpu.C == 1
        assert cpu.V == 1


class TestIllegalNOP2ByteImmediate:
    """Test 2-byte immediate NOP instructions (2 cycles)."""

    @pytest.mark.parametrize("opcode", [
        instructions.NOP_IMMEDIATE_0x80,
        instructions.NOP_IMMEDIATE_0x82,
        instructions.NOP_IMMEDIATE_0x89,
        instructions.NOP_IMMEDIATE_0xC2,
        instructions.NOP_IMMEDIATE_0xE2,
    ])
    def test_immediate_nop_advances_pc_by_2(self, cpu, opcode) -> None:
        """Test 2-byte immediate NOP advances PC by 2."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.ram[cpu.PC] = opcode
        cpu.ram[cpu.PC + 1] = 0x42  # operand (ignored)

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        assert cpu.PC == 0x0402

    @pytest.mark.parametrize("opcode", [
        instructions.NOP_IMMEDIATE_0x80,
        instructions.NOP_IMMEDIATE_0x82,
        instructions.NOP_IMMEDIATE_0x89,
        instructions.NOP_IMMEDIATE_0xC2,
        instructions.NOP_IMMEDIATE_0xE2,
    ])
    def test_immediate_nop_preserves_registers(self, cpu, opcode) -> None:
        """Test 2-byte immediate NOP does not modify registers."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.A = 0x42
        cpu.X = 0x33
        cpu.Y = 0x77
        cpu.ram[cpu.PC] = opcode
        cpu.ram[cpu.PC + 1] = 0xFF

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        assert cpu.A == 0x42
        assert cpu.X == 0x33
        assert cpu.Y == 0x77

    @pytest.mark.parametrize("opcode", [
        instructions.NOP_IMMEDIATE_0x80,
        instructions.NOP_IMMEDIATE_0x82,
        instructions.NOP_IMMEDIATE_0x89,
        instructions.NOP_IMMEDIATE_0xC2,
        instructions.NOP_IMMEDIATE_0xE2,
    ])
    def test_immediate_nop_preserves_flags(self, cpu, opcode) -> None:
        """Test 2-byte immediate NOP does not modify flags."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.N = 1
        cpu.Z = 1
        cpu.C = 1
        cpu.V = 1
        cpu.ram[cpu.PC] = opcode
        cpu.ram[cpu.PC + 1] = 0x00

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        assert cpu.N == 1
        assert cpu.Z == 1
        assert cpu.C == 1
        assert cpu.V == 1


class TestIllegalNOP2ByteZeroPage:
    """Test 2-byte zero page NOP instructions (3 cycles)."""

    @pytest.mark.parametrize("opcode", [
        instructions.NOP_ZEROPAGE_0x04,
        instructions.NOP_ZEROPAGE_0x44,
        instructions.NOP_ZEROPAGE_0x64,
    ])
    def test_zeropage_nop_advances_pc_by_2(self, cpu, opcode) -> None:
        """Test 2-byte zero page NOP advances PC by 2."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.ram[cpu.PC] = opcode
        cpu.ram[cpu.PC + 1] = 0x10  # zero page address

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        assert cpu.PC == 0x0402

    @pytest.mark.parametrize("opcode", [
        instructions.NOP_ZEROPAGE_0x04,
        instructions.NOP_ZEROPAGE_0x44,
        instructions.NOP_ZEROPAGE_0x64,
    ])
    def test_zeropage_nop_preserves_registers(self, cpu, opcode) -> None:
        """Test 2-byte zero page NOP does not modify registers."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.A = 0x42
        cpu.X = 0x33
        cpu.Y = 0x77
        cpu.ram[cpu.PC] = opcode
        cpu.ram[cpu.PC + 1] = 0x10
        cpu.ram[0x10] = 0xAB  # Memory at target address

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        assert cpu.A == 0x42
        assert cpu.X == 0x33
        assert cpu.Y == 0x77
        # Memory should also be unchanged
        assert cpu.ram[0x10] == 0xAB

    @pytest.mark.parametrize("opcode", [
        instructions.NOP_ZEROPAGE_0x04,
        instructions.NOP_ZEROPAGE_0x44,
        instructions.NOP_ZEROPAGE_0x64,
    ])
    def test_zeropage_nop_preserves_flags(self, cpu, opcode) -> None:
        """Test 2-byte zero page NOP does not modify flags."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.N = 1
        cpu.Z = 1
        cpu.C = 1
        cpu.V = 1
        cpu.ram[cpu.PC] = opcode
        cpu.ram[cpu.PC + 1] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        assert cpu.N == 1
        assert cpu.Z == 1
        assert cpu.C == 1
        assert cpu.V == 1


class TestIllegalNOP2ByteZeroPageX:
    """Test 2-byte zero page,X NOP instructions (4 cycles)."""

    @pytest.mark.parametrize("opcode", [
        instructions.NOP_ZEROPAGE_X_0x14,
        instructions.NOP_ZEROPAGE_X_0x34,
        instructions.NOP_ZEROPAGE_X_0x54,
        instructions.NOP_ZEROPAGE_X_0x74,
        instructions.NOP_ZEROPAGE_X_0xD4,
        instructions.NOP_ZEROPAGE_X_0xF4,
    ])
    def test_zeropage_x_nop_advances_pc_by_2(self, cpu, opcode) -> None:
        """Test 2-byte zero page,X NOP advances PC by 2."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.X = 0x05
        cpu.ram[cpu.PC] = opcode
        cpu.ram[cpu.PC + 1] = 0x10  # zero page base address

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        assert cpu.PC == 0x0402

    @pytest.mark.parametrize("opcode", [
        instructions.NOP_ZEROPAGE_X_0x14,
        instructions.NOP_ZEROPAGE_X_0x34,
        instructions.NOP_ZEROPAGE_X_0x54,
        instructions.NOP_ZEROPAGE_X_0x74,
        instructions.NOP_ZEROPAGE_X_0xD4,
        instructions.NOP_ZEROPAGE_X_0xF4,
    ])
    def test_zeropage_x_nop_preserves_registers(self, cpu, opcode) -> None:
        """Test 2-byte zero page,X NOP does not modify registers."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.A = 0x42
        cpu.X = 0x05
        cpu.Y = 0x77
        cpu.ram[cpu.PC] = opcode
        cpu.ram[cpu.PC + 1] = 0x10
        cpu.ram[0x15] = 0xCD  # Memory at $10 + X

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        assert cpu.A == 0x42
        assert cpu.X == 0x05
        assert cpu.Y == 0x77
        # Memory should also be unchanged
        assert cpu.ram[0x15] == 0xCD

    @pytest.mark.parametrize("opcode", [
        instructions.NOP_ZEROPAGE_X_0x14,
        instructions.NOP_ZEROPAGE_X_0x34,
        instructions.NOP_ZEROPAGE_X_0x54,
        instructions.NOP_ZEROPAGE_X_0x74,
        instructions.NOP_ZEROPAGE_X_0xD4,
        instructions.NOP_ZEROPAGE_X_0xF4,
    ])
    def test_zeropage_x_nop_preserves_flags(self, cpu, opcode) -> None:
        """Test 2-byte zero page,X NOP does not modify flags."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.X = 0x10
        cpu.N = 1
        cpu.Z = 1
        cpu.C = 1
        cpu.V = 1
        cpu.ram[cpu.PC] = opcode
        cpu.ram[cpu.PC + 1] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        assert cpu.N == 1
        assert cpu.Z == 1
        assert cpu.C == 1
        assert cpu.V == 1


class TestIllegalNOP3ByteAbsolute:
    """Test 3-byte absolute NOP instruction (4 cycles)."""

    def test_absolute_nop_advances_pc_by_3(self, cpu) -> None:
        """Test 3-byte absolute NOP advances PC by 3."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.ram[cpu.PC] = instructions.NOP_ABSOLUTE_0x0C
        cpu.ram[cpu.PC + 1] = 0x34
        cpu.ram[cpu.PC + 2] = 0x12  # Address $1234

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        assert cpu.PC == 0x0403

    def test_absolute_nop_preserves_registers(self, cpu) -> None:
        """Test 3-byte absolute NOP does not modify registers."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.A = 0x42
        cpu.X = 0x33
        cpu.Y = 0x77
        cpu.ram[cpu.PC] = instructions.NOP_ABSOLUTE_0x0C
        cpu.ram[cpu.PC + 1] = 0x34
        cpu.ram[cpu.PC + 2] = 0x12
        cpu.ram[0x1234] = 0xEF  # Memory at target address

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        assert cpu.A == 0x42
        assert cpu.X == 0x33
        assert cpu.Y == 0x77
        # Memory should also be unchanged
        assert cpu.ram[0x1234] == 0xEF

    def test_absolute_nop_preserves_flags(self, cpu) -> None:
        """Test 3-byte absolute NOP does not modify flags."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.N = 1
        cpu.Z = 1
        cpu.C = 1
        cpu.V = 1
        cpu.ram[cpu.PC] = instructions.NOP_ABSOLUTE_0x0C
        cpu.ram[cpu.PC + 1] = 0x00
        cpu.ram[cpu.PC + 2] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        assert cpu.N == 1
        assert cpu.Z == 1
        assert cpu.C == 1
        assert cpu.V == 1


class TestIllegalNOP3ByteAbsoluteX:
    """Test 3-byte absolute,X NOP instructions (4+ cycles)."""

    @pytest.mark.parametrize("opcode", [
        instructions.NOP_ABSOLUTE_X_0x1C,
        instructions.NOP_ABSOLUTE_X_0x3C,
        instructions.NOP_ABSOLUTE_X_0x5C,
        instructions.NOP_ABSOLUTE_X_0x7C,
        instructions.NOP_ABSOLUTE_X_0xDC,
        instructions.NOP_ABSOLUTE_X_0xFC,
    ])
    def test_absolute_x_nop_advances_pc_by_3(self, cpu, opcode) -> None:
        """Test 3-byte absolute,X NOP advances PC by 3."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.X = 0x10
        cpu.ram[cpu.PC] = opcode
        cpu.ram[cpu.PC + 1] = 0x34
        cpu.ram[cpu.PC + 2] = 0x12  # Address $1234 + X

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        assert cpu.PC == 0x0403

    @pytest.mark.parametrize("opcode", [
        instructions.NOP_ABSOLUTE_X_0x1C,
        instructions.NOP_ABSOLUTE_X_0x3C,
        instructions.NOP_ABSOLUTE_X_0x5C,
        instructions.NOP_ABSOLUTE_X_0x7C,
        instructions.NOP_ABSOLUTE_X_0xDC,
        instructions.NOP_ABSOLUTE_X_0xFC,
    ])
    def test_absolute_x_nop_preserves_registers(self, cpu, opcode) -> None:
        """Test 3-byte absolute,X NOP does not modify registers."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.A = 0x42
        cpu.X = 0x10
        cpu.Y = 0x77
        cpu.ram[cpu.PC] = opcode
        cpu.ram[cpu.PC + 1] = 0x34
        cpu.ram[cpu.PC + 2] = 0x12
        cpu.ram[0x1244] = 0xAB  # Memory at $1234 + X

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        assert cpu.A == 0x42
        assert cpu.X == 0x10
        assert cpu.Y == 0x77
        # Memory should also be unchanged
        assert cpu.ram[0x1244] == 0xAB

    @pytest.mark.parametrize("opcode", [
        instructions.NOP_ABSOLUTE_X_0x1C,
        instructions.NOP_ABSOLUTE_X_0x3C,
        instructions.NOP_ABSOLUTE_X_0x5C,
        instructions.NOP_ABSOLUTE_X_0x7C,
        instructions.NOP_ABSOLUTE_X_0xDC,
        instructions.NOP_ABSOLUTE_X_0xFC,
    ])
    def test_absolute_x_nop_preserves_flags(self, cpu, opcode) -> None:
        """Test 3-byte absolute,X NOP does not modify flags."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.X = 0x20
        cpu.N = 1
        cpu.Z = 1
        cpu.C = 1
        cpu.V = 1
        cpu.ram[cpu.PC] = opcode
        cpu.ram[cpu.PC + 1] = 0x00
        cpu.ram[cpu.PC + 2] = 0x30

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        assert cpu.N == 1
        assert cpu.Z == 1
        assert cpu.C == 1
        assert cpu.V == 1

    @pytest.mark.parametrize("opcode", [
        instructions.NOP_ABSOLUTE_X_0x1C,
        instructions.NOP_ABSOLUTE_X_0x3C,
        instructions.NOP_ABSOLUTE_X_0x5C,
        instructions.NOP_ABSOLUTE_X_0x7C,
        instructions.NOP_ABSOLUTE_X_0xDC,
        instructions.NOP_ABSOLUTE_X_0xFC,
    ])
    def test_absolute_x_nop_page_boundary_crossing(self, cpu, opcode) -> None:
        """Test 3-byte absolute,X NOP with page boundary crossing."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.X = 0xFF  # Will cause page crossing with $12FF
        cpu.ram[cpu.PC] = opcode
        cpu.ram[cpu.PC + 1] = 0xFF
        cpu.ram[cpu.PC + 2] = 0x12  # Address $12FF + X = $13FE

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        # PC should still advance by 3
        assert cpu.PC == 0x0403


class TestIllegalNOPChainExecution:
    """Test that multiple illegal NOPs can execute in sequence."""

    def test_multiple_implied_nops_execute(self, cpu) -> None:
        """Test multiple 1-byte implied NOPs execute correctly."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.A = 0x55
        cpu.X = 0x66
        cpu.Y = 0x77

        # Three consecutive illegal NOPs
        cpu.ram[cpu.PC] = instructions.NOP_IMPLIED_0x1A
        cpu.ram[cpu.PC + 1] = instructions.NOP_IMPLIED_0x3A
        cpu.ram[cpu.PC + 2] = instructions.NOP_IMPLIED_0x5A

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=3)

        assert cpu.PC == 0x0403
        assert cpu.A == 0x55
        assert cpu.X == 0x66
        assert cpu.Y == 0x77

    def test_mixed_nop_sizes_execute(self, cpu) -> None:
        """Test mix of 1, 2, and 3-byte NOPs execute correctly."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.A = 0x11
        cpu.X = 0x22
        cpu.Y = 0x33

        # 1-byte NOP at $0400
        cpu.ram[0x0400] = instructions.NOP_IMPLIED_0x1A
        # 2-byte NOP at $0401
        cpu.ram[0x0401] = instructions.NOP_IMMEDIATE_0x80
        cpu.ram[0x0402] = 0xAB
        # 3-byte NOP at $0403
        cpu.ram[0x0403] = instructions.NOP_ABSOLUTE_0x0C
        cpu.ram[0x0404] = 0xCD
        cpu.ram[0x0405] = 0xEF

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=3)

        # Total: 1 + 2 + 3 = 6 bytes
        assert cpu.PC == 0x0406
        assert cpu.A == 0x11
        assert cpu.X == 0x22
        assert cpu.Y == 0x33
