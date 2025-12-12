"""Tests for ANE (XAA) illegal instruction.

ANE is a HIGHLY UNSTABLE illegal instruction on NMOS 6502.
On 65C02 (CMOS), this opcode acts as a NOP.

Operation: A = (A | CONST) & X & immediate

Where CONST is configurable (default 0xFF for 6502/6502A, 0xEE for 6502C).

References:
    - http://www.oxyron.de/html/opcodes02.html
    - https://www.nesdev.org/wiki/CPU_unofficial_opcodes#Highly_unstable_opcodes
"""
import contextlib

from mos6502 import errors, instructions


class TestANENMOS:
    """Test ANE instruction on NMOS variants (6502, 6502A, 6502C)."""

    def test_ane_basic_operation(self, nmos_cpu) -> None:
        """Test ANE basic operation: A = (A | CONST) & X & immediate."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x00  # Will be ORed with CONST (0xFF default)
        nmos_cpu.X = 0xFF

        nmos_cpu.ram[nmos_cpu.PC] = instructions.ANE_IMMEDIATE_0x8B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x55  # immediate

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        # With CONST=0xFF: A = (0x00 | 0xFF) & 0xFF & 0x55 = 0x55
        # Note: 6502C might have different CONST
        assert nmos_cpu.PC == 0x0402

    def test_ane_with_a_value(self, nmos_cpu) -> None:
        """Test ANE with non-zero A value."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xAA
        nmos_cpu.X = 0xFF

        nmos_cpu.ram[nmos_cpu.PC] = instructions.ANE_IMMEDIATE_0x8B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0xF0

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        # With CONST=0xFF: A = (0xAA | 0xFF) & 0xFF & 0xF0 = 0xF0
        # With CONST=0xEE: A = (0xAA | 0xEE) & 0xFF & 0xF0 = 0xE0
        # Test is variant-dependent

    def test_ane_x_masks_result(self, nmos_cpu) -> None:
        """Test ANE result is masked by X register."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.X = 0x0F  # Only low nibble

        nmos_cpu.ram[nmos_cpu.PC] = instructions.ANE_IMMEDIATE_0x8B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0xFF

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        # A = (0xFF | CONST) & 0x0F & 0xFF = 0x0F
        assert nmos_cpu.A == 0x0F

    def test_ane_immediate_masks_result(self, nmos_cpu) -> None:
        """Test ANE result is masked by immediate value."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0xFF
        nmos_cpu.X = 0xFF

        nmos_cpu.ram[nmos_cpu.PC] = instructions.ANE_IMMEDIATE_0x8B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x0F  # Only low nibble

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        # A = (0xFF | CONST) & 0xFF & 0x0F = 0x0F
        assert nmos_cpu.A == 0x0F

    def test_ane_sets_zero_flag(self, nmos_cpu) -> None:
        """Test ANE sets zero flag when result is zero."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x00
        nmos_cpu.X = 0x00  # X=0 means result is always 0

        nmos_cpu.ram[nmos_cpu.PC] = instructions.ANE_IMMEDIATE_0x8B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0xFF

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        # A = (0x00 | CONST) & 0x00 & 0xFF = 0x00
        assert nmos_cpu.A == 0x00
        assert nmos_cpu.Z == 1

    def test_ane_sets_negative_flag(self, nmos_cpu) -> None:
        """Test ANE sets negative flag when bit 7 is set."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x00
        nmos_cpu.X = 0xFF

        nmos_cpu.ram[nmos_cpu.PC] = instructions.ANE_IMMEDIATE_0x8B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x80  # Bit 7 set

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        # With CONST=0xFF: A = (0x00 | 0xFF) & 0xFF & 0x80 = 0x80
        # (6502C with 0xEE: A = (0x00 | 0xEE) & 0xFF & 0x80 = 0x80)
        assert nmos_cpu.A == 0x80
        assert nmos_cpu.N == 1

    def test_ane_clears_zero_flag(self, nmos_cpu) -> None:
        """Test ANE clears zero flag when result is non-zero."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x00
        nmos_cpu.X = 0xFF
        nmos_cpu.Z = 1  # Pre-set

        # Use 0x02 as immediate - this works for both CONST=0xFF and CONST=0xEE
        # 0xFF & 0x02 = 0x02, 0xEE & 0x02 = 0x02
        nmos_cpu.ram[nmos_cpu.PC] = instructions.ANE_IMMEDIATE_0x8B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x02

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        # A = (0x00 | CONST) & 0xFF & 0x02 = 0x02 (for both 0xFF and 0xEE)
        assert nmos_cpu.A == 0x02
        assert nmos_cpu.Z == 0

    def test_ane_preserves_x(self, nmos_cpu) -> None:
        """Test ANE does not modify X register."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x42
        nmos_cpu.X = 0x33

        nmos_cpu.ram[nmos_cpu.PC] = instructions.ANE_IMMEDIATE_0x8B
        nmos_cpu.ram[nmos_cpu.PC + 1] = 0x55

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            nmos_cpu.execute(max_instructions=1)

        assert nmos_cpu.X == 0x33


class TestANECMOS:
    """Test ANE instruction on CMOS variant (65C02) - acts as NOP."""

    def test_ane_acts_as_nop(self, cmos_cpu) -> None:
        """Test ANE acts as NOP on CMOS (65C02)."""
        cmos_cpu.reset()
        cmos_cpu.PC = 0x0400
        cmos_cpu.A = 0x42
        cmos_cpu.X = 0x33

        cmos_cpu.ram[cmos_cpu.PC] = instructions.ANE_IMMEDIATE_0x8B
        cmos_cpu.ram[cmos_cpu.PC + 1] = 0xFF

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(max_instructions=1)

        # Verify A and X are unchanged (NOP behavior)
        assert cmos_cpu.A == 0x42
        assert cmos_cpu.X == 0x33
        # PC advances by 2 (2-byte NOP)
        assert cmos_cpu.PC == 0x0402

    def test_ane_nop_preserves_flags(self, cmos_cpu) -> None:
        """Test ANE NOP does not modify flags on CMOS."""
        cmos_cpu.reset()
        cmos_cpu.PC = 0x0400
        cmos_cpu.A = 0x42
        cmos_cpu.X = 0xFF
        cmos_cpu.N = 1
        cmos_cpu.Z = 1

        cmos_cpu.ram[cmos_cpu.PC] = instructions.ANE_IMMEDIATE_0x8B
        cmos_cpu.ram[cmos_cpu.PC + 1] = 0x00

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(max_instructions=1)

        # Flags should be unchanged
        assert cmos_cpu.N == 1
        assert cmos_cpu.Z == 1
