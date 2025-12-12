"""Tests for JAM (KIL, HLT) illegal instruction.

JAM halts the CPU on NMOS 6502. On real hardware, a reset is required to recover.
On 65C02 (CMOS), JAM opcodes act as 1-byte, 1-cycle NOPs.

There are 12 JAM opcodes:
0x02, 0x12, 0x22, 0x32, 0x42, 0x52, 0x62, 0x72, 0x92, 0xB2, 0xD2, 0xF2

References:
    - http://www.oxyron.de/html/opcodes02.html
    - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""
import contextlib

import pytest

from mos6502 import errors, instructions


class TestJAMNMOS:
    """Test JAM instruction on NMOS variants (6502, 6502A, 6502C)."""

    @pytest.mark.parametrize("opcode", [
        instructions.JAM_IMPLIED_0x02,
        instructions.JAM_IMPLIED_0x12,
        instructions.JAM_IMPLIED_0x22,
        instructions.JAM_IMPLIED_0x32,
        instructions.JAM_IMPLIED_0x42,
        instructions.JAM_IMPLIED_0x52,
        instructions.JAM_IMPLIED_0x62,
        instructions.JAM_IMPLIED_0x72,
        instructions.JAM_IMPLIED_0x92,
        instructions.JAM_IMPLIED_0xB2,
        instructions.JAM_IMPLIED_0xD2,
        instructions.JAM_IMPLIED_0xF2,
    ])
    def test_jam_halts_cpu(self, nmos_cpu, opcode) -> None:
        """Test JAM halts the CPU and raises CPUHaltError."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.ram[nmos_cpu.PC] = opcode

        with pytest.raises(errors.CPUHaltError) as exc_info:
            nmos_cpu.execute(max_instructions=1)

        # Verify exception contains correct information
        assert exc_info.value.opcode == opcode
        assert exc_info.value.address == 0x0400

    @pytest.mark.parametrize("opcode", [
        instructions.JAM_IMPLIED_0x02,
        instructions.JAM_IMPLIED_0x12,
        instructions.JAM_IMPLIED_0x22,
        instructions.JAM_IMPLIED_0x32,
        instructions.JAM_IMPLIED_0x42,
        instructions.JAM_IMPLIED_0x52,
        instructions.JAM_IMPLIED_0x62,
        instructions.JAM_IMPLIED_0x72,
        instructions.JAM_IMPLIED_0x92,
        instructions.JAM_IMPLIED_0xB2,
        instructions.JAM_IMPLIED_0xD2,
        instructions.JAM_IMPLIED_0xF2,
    ])
    def test_jam_sets_halted_flag(self, nmos_cpu, opcode) -> None:
        """Test JAM sets the halted flag on CPU."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.ram[nmos_cpu.PC] = opcode

        assert nmos_cpu.halted is False

        with pytest.raises(errors.CPUHaltError):
            nmos_cpu.execute(max_instructions=1)

        assert nmos_cpu.halted is True

    def test_jam_reset_clears_halted(self, nmos_cpu) -> None:
        """Test reset() clears the halted flag."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.ram[nmos_cpu.PC] = instructions.JAM_IMPLIED_0x02

        with pytest.raises(errors.CPUHaltError):
            nmos_cpu.execute(max_instructions=1)

        assert nmos_cpu.halted is True

        # Reset should clear the halted flag
        nmos_cpu.reset()
        assert nmos_cpu.halted is False

    def test_jam_cannot_execute_after_halt(self, nmos_cpu) -> None:
        """Test cannot execute instructions after JAM halts CPU."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.ram[nmos_cpu.PC] = instructions.JAM_IMPLIED_0x02

        with pytest.raises(errors.CPUHaltError):
            nmos_cpu.execute(max_instructions=1)

        # Trying to execute again should raise error
        with pytest.raises(errors.CPUHaltError) as exc_info:
            nmos_cpu.execute(max_instructions=1)

        assert "halted" in str(exc_info.value).lower()

    def test_jam_preserves_registers(self, nmos_cpu) -> None:
        """Test JAM does not modify A, X, Y registers."""
        nmos_cpu.reset()
        nmos_cpu.PC = 0x0400
        nmos_cpu.A = 0x42
        nmos_cpu.X = 0x33
        nmos_cpu.Y = 0x77
        nmos_cpu.ram[nmos_cpu.PC] = instructions.JAM_IMPLIED_0x02

        with pytest.raises(errors.CPUHaltError):
            nmos_cpu.execute(max_instructions=1)

        assert nmos_cpu.A == 0x42
        assert nmos_cpu.X == 0x33
        assert nmos_cpu.Y == 0x77


class TestJAMCMOS:
    """Test JAM instruction on CMOS variant (65C02) - acts as NOP."""

    @pytest.mark.parametrize("opcode", [
        instructions.JAM_IMPLIED_0x02,
        instructions.JAM_IMPLIED_0x12,
        instructions.JAM_IMPLIED_0x22,
        instructions.JAM_IMPLIED_0x32,
        instructions.JAM_IMPLIED_0x42,
        instructions.JAM_IMPLIED_0x52,
        instructions.JAM_IMPLIED_0x62,
        instructions.JAM_IMPLIED_0x72,
        instructions.JAM_IMPLIED_0x92,
        instructions.JAM_IMPLIED_0xB2,
        instructions.JAM_IMPLIED_0xD2,
        instructions.JAM_IMPLIED_0xF2,
    ])
    def test_jam_acts_as_nop(self, cmos_cpu, opcode) -> None:
        """Test JAM acts as NOP on CMOS (65C02)."""
        cmos_cpu.reset()
        cmos_cpu.PC = 0x0400
        cmos_cpu.A = 0x42
        cmos_cpu.X = 0x33
        cmos_cpu.Y = 0x77
        cmos_cpu.ram[cmos_cpu.PC] = opcode

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(max_instructions=1)

        # Verify CPU is not halted
        assert cmos_cpu.halted is False
        # Verify registers unchanged
        assert cmos_cpu.A == 0x42
        assert cmos_cpu.X == 0x33
        assert cmos_cpu.Y == 0x77
        # Verify PC advanced by 1
        assert cmos_cpu.PC == 0x0401

    @pytest.mark.parametrize("opcode", [
        instructions.JAM_IMPLIED_0x02,
        instructions.JAM_IMPLIED_0x12,
        instructions.JAM_IMPLIED_0x22,
        instructions.JAM_IMPLIED_0x32,
        instructions.JAM_IMPLIED_0x42,
        instructions.JAM_IMPLIED_0x52,
        instructions.JAM_IMPLIED_0x62,
        instructions.JAM_IMPLIED_0x72,
        instructions.JAM_IMPLIED_0x92,
        instructions.JAM_IMPLIED_0xB2,
        instructions.JAM_IMPLIED_0xD2,
        instructions.JAM_IMPLIED_0xF2,
    ])
    def test_jam_nop_preserves_flags(self, cmos_cpu, opcode) -> None:
        """Test JAM NOP does not modify flags on CMOS."""
        cmos_cpu.reset()
        cmos_cpu.PC = 0x0400
        cmos_cpu.N = 1
        cmos_cpu.Z = 1
        cmos_cpu.C = 1
        cmos_cpu.V = 1
        cmos_cpu.ram[cmos_cpu.PC] = opcode

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(max_instructions=1)

        assert cmos_cpu.N == 1
        assert cmos_cpu.Z == 1
        assert cmos_cpu.C == 1
        assert cmos_cpu.V == 1

    def test_jam_nop_can_execute_multiple(self, cmos_cpu) -> None:
        """Test multiple JAM NOPs can execute in sequence on CMOS."""
        cmos_cpu.reset()
        cmos_cpu.PC = 0x0400
        cmos_cpu.A = 0x55

        # Three consecutive JAM NOPs
        cmos_cpu.ram[cmos_cpu.PC] = instructions.JAM_IMPLIED_0x02
        cmos_cpu.ram[cmos_cpu.PC + 1] = instructions.JAM_IMPLIED_0x12
        cmos_cpu.ram[cmos_cpu.PC + 2] = instructions.JAM_IMPLIED_0x22

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cmos_cpu.execute(max_instructions=3)

        assert cmos_cpu.PC == 0x0403
        assert cmos_cpu.A == 0x55
        assert cmos_cpu.halted is False
