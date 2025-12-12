"""Tests for illegal SBC instruction (0xEB duplicate).

Opcode 0xEB is an undocumented duplicate of SBC Immediate (0xE9).
It behaves identically on all 6502 variants.

Operation: A = A - M - (1 - C)

References:
    - http://www.oxyron.de/html/opcodes02.html
    - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""
import contextlib

from mos6502 import errors, instructions


class TestSBCIllegal:
    """Test illegal SBC instruction (0xEB) on all variants."""

    def test_sbc_illegal_basic_subtraction(self, cpu) -> None:
        """Test SBC 0xEB basic subtraction with carry set."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.A = 0x50
        cpu.C = 1  # No borrow

        cpu.ram[cpu.PC] = instructions.SBC_IMMEDIATE_0xEB
        cpu.ram[cpu.PC + 1] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        # A = 0x50 - 0x10 - 0 = 0x40
        assert cpu.A == 0x40
        assert cpu.PC == 0x0402
        assert cpu.C == 1  # No borrow occurred
        assert cpu.Z == 0
        assert cpu.N == 0

    def test_sbc_illegal_with_borrow(self, cpu) -> None:
        """Test SBC 0xEB subtraction with borrow (C=0)."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.A = 0x50
        cpu.C = 0  # Borrow from previous operation

        cpu.ram[cpu.PC] = instructions.SBC_IMMEDIATE_0xEB
        cpu.ram[cpu.PC + 1] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        # A = 0x50 - 0x10 - 1 = 0x3F
        assert cpu.A == 0x3F
        assert cpu.C == 1  # No new borrow

    def test_sbc_illegal_sets_zero_flag(self, cpu) -> None:
        """Test SBC 0xEB sets zero flag when result is zero."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.A = 0x42
        cpu.C = 1

        cpu.ram[cpu.PC] = instructions.SBC_IMMEDIATE_0xEB
        cpu.ram[cpu.PC + 1] = 0x42

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        # A = 0x42 - 0x42 = 0x00
        assert cpu.A == 0x00
        assert cpu.Z == 1
        assert cpu.N == 0

    def test_sbc_illegal_sets_negative_flag(self, cpu) -> None:
        """Test SBC 0xEB sets negative flag when bit 7 is set."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.A = 0x00
        cpu.C = 1

        cpu.ram[cpu.PC] = instructions.SBC_IMMEDIATE_0xEB
        cpu.ram[cpu.PC + 1] = 0x01

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        # A = 0x00 - 0x01 = 0xFF (wraps, sets N)
        assert cpu.A == 0xFF
        assert cpu.N == 1
        assert cpu.C == 0  # Borrow occurred

    def test_sbc_illegal_clears_carry_on_borrow(self, cpu) -> None:
        """Test SBC 0xEB clears carry when borrow is needed."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.A = 0x10
        cpu.C = 1

        cpu.ram[cpu.PC] = instructions.SBC_IMMEDIATE_0xEB
        cpu.ram[cpu.PC + 1] = 0x20

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        # A = 0x10 - 0x20 = 0xF0 (wraps)
        assert cpu.A == 0xF0
        assert cpu.C == 0  # Borrow occurred

    def test_sbc_illegal_sets_overflow_positive_to_negative(self, cpu) -> None:
        """Test SBC 0xEB sets overflow on positive - negative = negative."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.A = 0x50  # +80 (positive)
        cpu.C = 1

        cpu.ram[cpu.PC] = instructions.SBC_IMMEDIATE_0xEB
        cpu.ram[cpu.PC + 1] = 0xB0  # -80 (negative, subtracting adds)

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        # 80 - (-80) = 160 = 0xA0 (but 160 > 127, so overflow)
        assert cpu.A == 0xA0
        assert cpu.V == 1  # Overflow: positive - negative = negative result

    def test_sbc_illegal_sets_overflow_negative_to_positive(self, cpu) -> None:
        """Test SBC 0xEB sets overflow on negative - positive = positive."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.A = 0x80  # -128 (negative)
        cpu.C = 1

        cpu.ram[cpu.PC] = instructions.SBC_IMMEDIATE_0xEB
        cpu.ram[cpu.PC + 1] = 0x01  # +1 (positive)

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        # -128 - 1 = -129 (underflow in signed arithmetic)
        assert cpu.A == 0x7F
        assert cpu.V == 1  # Overflow: negative - positive = positive result

    def test_sbc_illegal_no_overflow_same_signs(self, cpu) -> None:
        """Test SBC 0xEB no overflow when signs match."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.A = 0x50  # +80
        cpu.C = 1

        cpu.ram[cpu.PC] = instructions.SBC_IMMEDIATE_0xEB
        cpu.ram[cpu.PC + 1] = 0x30  # +48

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        # 80 - 48 = 32 (0x20)
        assert cpu.A == 0x20
        assert cpu.V == 0

    def test_sbc_illegal_identical_to_0xe9(self, cpu) -> None:
        """Test SBC 0xEB produces identical results to SBC 0xE9."""
        # Run with 0xEB
        cpu.reset()
        cpu.PC = 0x0400
        cpu.A = 0x77
        cpu.C = 1
        cpu.ram[cpu.PC] = instructions.SBC_IMMEDIATE_0xEB
        cpu.ram[cpu.PC + 1] = 0x33

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        result_eb = cpu.A
        carry_eb = cpu.C
        zero_eb = cpu.Z
        negative_eb = cpu.N
        overflow_eb = cpu.V

        # Run with 0xE9
        cpu.reset()
        cpu.PC = 0x0400
        cpu.A = 0x77
        cpu.C = 1
        cpu.ram[cpu.PC] = instructions.SBC_IMMEDIATE_0xE9
        cpu.ram[cpu.PC + 1] = 0x33

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        # Verify both produce identical results
        assert cpu.A == result_eb
        assert cpu.C == carry_eb
        assert cpu.Z == zero_eb
        assert cpu.N == negative_eb
        assert cpu.V == overflow_eb

    def test_sbc_illegal_pc_advances_by_2(self, cpu) -> None:
        """Test SBC 0xEB advances PC by 2 bytes."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.A = 0x50
        cpu.C = 1

        cpu.ram[cpu.PC] = instructions.SBC_IMMEDIATE_0xEB
        cpu.ram[cpu.PC + 1] = 0x10

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        assert cpu.PC == 0x0402

    def test_sbc_illegal_subtract_zero(self, cpu) -> None:
        """Test SBC 0xEB subtracting zero preserves A."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.A = 0x42
        cpu.C = 1

        cpu.ram[cpu.PC] = instructions.SBC_IMMEDIATE_0xEB
        cpu.ram[cpu.PC + 1] = 0x00

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        assert cpu.A == 0x42
        assert cpu.C == 1
        assert cpu.Z == 0

    def test_sbc_illegal_subtract_from_zero(self, cpu) -> None:
        """Test SBC 0xEB subtracting from zero."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.A = 0x00
        cpu.C = 1

        cpu.ram[cpu.PC] = instructions.SBC_IMMEDIATE_0xEB
        cpu.ram[cpu.PC + 1] = 0x01

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(max_instructions=1)

        # 0x00 - 0x01 = 0xFF
        assert cpu.A == 0xFF
        assert cpu.C == 0  # Borrow
        assert cpu.N == 1  # Negative
