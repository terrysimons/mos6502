#!/usr/bin/env python3
"""Tests for NMI (Non-Maskable Interrupt) support.

These tests verify that the CPU properly handles NMI interrupts,
which are used by CIA2 on the C64.

NMI differs from IRQ in several important ways:
- NMI uses vector $FFFA/$FFFB (not $FFFE/$FFFF)
- NMI cannot be masked by the I flag
- NMI is edge-triggered (fires on low-to-high transition)
"""

import pytest

import mos6502
from mos6502 import errors
from mos6502 import instructions


def run_cpu(cpu, max_instructions: int) -> None:
    """Run CPU for a number of instructions, ignoring exhaustion error."""
    try:
        cpu.execute(max_instructions=max_instructions)
    except errors.CPUCycleExhaustionError:
        pass  # Expected when instruction limit reached


class TestNMIPendingAttribute:
    """Test that the nmi_pending attribute exists on CPU."""

    def test_cpu_has_nmi_pending_attribute(self) -> None:
        """CPU should have an nmi_pending attribute for NMI signaling."""
        cpu = mos6502.CPU()
        cpu.reset()

        # This will fail with AttributeError if nmi_pending doesn't exist
        assert hasattr(cpu, "nmi_pending"), "CPU must have nmi_pending attribute"

    def test_nmi_pending_initial_state_is_false(self) -> None:
        """nmi_pending should be False after CPU reset."""
        cpu = mos6502.CPU()
        cpu.reset()

        assert cpu.nmi_pending is False, "nmi_pending should be False after reset"

    def test_nmi_pending_can_be_set(self) -> None:
        """nmi_pending should be settable to True."""
        cpu = mos6502.CPU()
        cpu.reset()

        cpu.nmi_pending = True
        assert cpu.nmi_pending is True, "nmi_pending should be settable to True"


class TestNMIVectorAddress:
    """Test that NMI uses the correct vector address."""

    def test_nmi_uses_vector_at_fffa_fffb(self) -> None:
        """NMI should jump to address stored at $FFFA/$FFFB."""
        cpu = mos6502.CPU()
        cpu.reset()

        # Set up NMI vector to point to $1234
        cpu.ram[0xFFFA] = 0x34  # Low byte
        cpu.ram[0xFFFB] = 0x12  # High byte

        # Put NOP at the NMI handler location
        cpu.ram[0x1234] = instructions.NOP_IMPLIED_0xEA

        # Put a simple program: NOP at $0200
        cpu.ram[0xFFFC] = 0x00  # Reset vector low
        cpu.ram[0xFFFD] = 0x02  # Reset vector high
        cpu.ram[0x0200] = instructions.NOP_IMPLIED_0xEA
        cpu.ram[0x0201] = instructions.NOP_IMPLIED_0xEA

        cpu.reset()

        # Trigger NMI
        cpu.nmi_pending = True

        # Execute one instruction (NOP), then NMI should fire after it completes
        # Then execute the NOP at NMI handler
        run_cpu(cpu, max_instructions=2)

        # PC should now be just after NOP at NMI handler ($1235)
        assert cpu.PC == 0x1235, \
            f"NMI should jump to vector at $FFFA/$FFFB ($1234), but PC is ${cpu.PC:04X}"


class TestNMINotMaskable:
    """Test that NMI cannot be masked by the I flag."""

    def test_nmi_fires_even_when_i_flag_set(self) -> None:
        """NMI should fire even when I flag is set (interrupts disabled)."""
        cpu = mos6502.CPU()
        cpu.reset()

        # Set up NMI vector
        cpu.ram[0xFFFA] = 0x00  # Low byte -> $0300
        cpu.ram[0xFFFB] = 0x03  # High byte

        # NMI handler: just a NOP
        cpu.ram[0x0300] = instructions.NOP_IMPLIED_0xEA

        # Main program at $0200: SEI (set I flag), then NOP
        cpu.ram[0xFFFC] = 0x00  # Reset vector low
        cpu.ram[0xFFFD] = 0x02  # Reset vector high
        cpu.ram[0x0200] = instructions.SEI_IMPLIED_0x78  # Set I flag
        cpu.ram[0x0201] = instructions.NOP_IMPLIED_0xEA

        cpu.reset()

        # Execute SEI to set I flag
        run_cpu(cpu, max_instructions=1)
        assert cpu.I == 1, "I flag should be set after SEI"

        # Trigger NMI
        cpu.nmi_pending = True

        # Execute NOP, NMI fires after, then execute NOP in handler
        run_cpu(cpu, max_instructions=2)

        # PC should be just after NMI handler NOP
        assert cpu.PC == 0x0301, \
            f"NMI should fire even with I flag set, but PC is ${cpu.PC:04X}"


class TestNMIStackBehavior:
    """Test that NMI properly saves state to stack."""

    def test_nmi_pushes_pc_and_status_to_stack(self) -> None:
        """NMI should push PC (2 bytes) and status register to stack."""
        cpu = mos6502.CPU()
        cpu.reset()

        # Set up NMI vector
        cpu.ram[0xFFFA] = 0x00  # Low byte -> $0300
        cpu.ram[0xFFFB] = 0x03  # High byte

        # NMI handler: just a NOP
        cpu.ram[0x0300] = instructions.NOP_IMPLIED_0xEA

        # Main program: NOP at $0200
        cpu.ram[0xFFFC] = 0x00
        cpu.ram[0xFFFD] = 0x02
        cpu.ram[0x0200] = instructions.NOP_IMPLIED_0xEA
        cpu.ram[0x0201] = instructions.NOP_IMPLIED_0xEA

        cpu.reset()

        # Record initial stack pointer
        initial_sp = cpu.S & 0xFF

        # Execute one NOP to get to $0201
        run_cpu(cpu, max_instructions=1)
        assert cpu.PC == 0x0201, f"PC should be $0201 after NOP, got ${cpu.PC:04X}"

        # Trigger NMI
        cpu.nmi_pending = True

        # Execute NOP at $0201, NMI fires after, then execute NOP in handler
        run_cpu(cpu, max_instructions=2)

        # Stack should have 3 bytes pushed (PCH, PCL, P)
        final_sp = cpu.S & 0xFF
        assert final_sp == (initial_sp - 3) & 0xFF, \
            f"Stack pointer should decrease by 3, was ${initial_sp:02X}, now ${final_sp:02X}"

        # Verify return address on stack points back to where we were ($0202)
        # Stack layout: [PCH @ SP+3, PCL @ SP+2, P @ SP+1] with SP pointing below P
        stacked_pcl = cpu.ram[0x0100 | ((final_sp + 2) & 0xFF)]
        stacked_pch = cpu.ram[0x0100 | ((final_sp + 3) & 0xFF)]
        stacked_pc = (stacked_pch << 8) | stacked_pcl

        assert stacked_pc == 0x0202, \
            f"Return address on stack should be $0202, got ${stacked_pc:04X}"


class TestNMISetsIFlag:
    """Test that NMI sets the I flag to prevent nested interrupts."""

    def test_nmi_sets_i_flag(self) -> None:
        """NMI handler should start with I flag set."""
        cpu = mos6502.CPU()
        cpu.reset()

        # Set up NMI vector
        cpu.ram[0xFFFA] = 0x00
        cpu.ram[0xFFFB] = 0x03

        # NMI handler at $0300
        cpu.ram[0x0300] = instructions.NOP_IMPLIED_0xEA

        # Main program with I flag cleared
        cpu.ram[0xFFFC] = 0x00
        cpu.ram[0xFFFD] = 0x02
        cpu.ram[0x0200] = instructions.CLI_IMPLIED_0x58  # Clear I flag
        cpu.ram[0x0201] = instructions.NOP_IMPLIED_0xEA

        cpu.reset()

        # Execute CLI to clear I flag
        run_cpu(cpu, max_instructions=1)
        assert cpu.I == 0, "I flag should be clear after CLI"

        # Trigger NMI
        cpu.nmi_pending = True

        # Execute NOP, NMI fires after
        run_cpu(cpu, max_instructions=1)

        # I flag should now be set (NMI sets it)
        assert cpu.I == 1, "I flag should be set after NMI"


class TestNMIBFlagBehavior:
    """Test that NMI pushes status with B flag clear."""

    def test_nmi_pushes_status_with_b_flag_clear(self) -> None:
        """NMI should push status register with B flag clear (like IRQ, unlike BRK)."""
        cpu = mos6502.CPU()
        cpu.reset()

        # Set up NMI vector
        cpu.ram[0xFFFA] = 0x00
        cpu.ram[0xFFFB] = 0x03

        # NMI handler
        cpu.ram[0x0300] = instructions.NOP_IMPLIED_0xEA

        # Main program
        cpu.ram[0xFFFC] = 0x00
        cpu.ram[0xFFFD] = 0x02
        cpu.ram[0x0200] = instructions.NOP_IMPLIED_0xEA

        cpu.reset()

        # Record initial SP
        initial_sp = cpu.S & 0xFF

        # Trigger NMI
        cpu.nmi_pending = True

        # Execute NOP, NMI fires after
        run_cpu(cpu, max_instructions=1)

        # Check stacked status - B flag (bit 4) should be clear
        # Status is at SP+1 after NMI pushes 3 bytes
        final_sp = cpu.S & 0xFF
        stacked_status = cpu.ram[0x0100 | ((final_sp + 1) & 0xFF)]

        assert (stacked_status & 0x10) == 0, \
            f"B flag in stacked status should be clear for NMI, got ${stacked_status:02X}"
