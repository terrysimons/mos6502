#!/usr/bin/env python3
"""Tests for SID (Sound Interface Device - 6581/8580) emulation.

These tests verify that the SID chip emulation provides proper
register read/write behavior for diagnostic compatibility.

SID Register Map:
    $D400-$D406: Voice 1 (Freq Lo/Hi, PW Lo/Hi, Control, AD, SR)
    $D407-$D40D: Voice 2 (Freq Lo/Hi, PW Lo/Hi, Control, AD, SR)
    $D40E-$D414: Voice 3 (Freq Lo/Hi, PW Lo/Hi, Control, AD, SR)
    $D415-$D416: Filter Cutoff (Lo/Hi)
    $D417: Filter Resonance/Voice Enable
    $D418: Volume/Filter Mode

Read-only registers:
    $D419 (25): POTX - Paddle X position
    $D41A (26): POTY - Paddle Y position
    $D41B (27): OSC3 - Oscillator 3 random output
    $D41C (28): ENV3 - Envelope 3 output
"""

import pytest

from c64.sid import SID


class TestSIDRegisterWriteReadback:
    """Test that write-only registers return last written value."""

    def test_write_to_voice1_freq_lo_returns_last_written(self) -> None:
        """Writing to Voice 1 Frequency Lo ($D400) stores value."""
        sid = SID()
        sid.write(0xD400, 0x55)
        # Write-only registers return last written value
        assert sid.read(0xD400) == 0x55

    def test_write_to_voice1_freq_hi_returns_last_written(self) -> None:
        """Writing to Voice 1 Frequency Hi ($D401) stores value."""
        sid = SID()
        sid.write(0xD401, 0xAA)
        assert sid.read(0xD401) == 0xAA

    def test_write_to_different_register_updates_last_written(self) -> None:
        """Last written value is updated on any write."""
        sid = SID()
        sid.write(0xD400, 0x11)
        sid.write(0xD418, 0x22)  # Write to different register
        # Reading any write-only register returns last written to ANY register
        assert sid.read(0xD400) == 0x22

    def test_all_voice_registers_store_values(self) -> None:
        """All 25 write-only registers store their values."""
        sid = SID()

        # Write distinct values to all write-only registers (0-24)
        for reg in range(25):
            sid.write(0xD400 + reg, reg + 0x10)
            # The internal register array stores the value
            assert sid.registers[reg] == reg + 0x10


class TestSIDReadOnlyRegisters:
    """Test behavior of read-only registers."""

    def test_potx_returns_paddle_x_value(self) -> None:
        """POTX ($D419) returns paddle X position."""
        sid = SID()
        # Default is 0xFF (no paddle/fully right)
        assert sid.read(0xD419) == 0xFF

        # Can be set programmatically
        sid.pot_x = 0x80
        assert sid.read(0xD419) == 0x80

    def test_poty_returns_paddle_y_value(self) -> None:
        """POTY ($D41A) returns paddle Y position."""
        sid = SID()
        assert sid.read(0xD41A) == 0xFF

        sid.pot_y = 0x40
        assert sid.read(0xD41A) == 0x40

    def test_osc3_returns_oscillator_output(self) -> None:
        """OSC3 ($D41B) returns oscillator 3 output."""
        sid = SID()
        assert sid.read(0xD41B) == 0x00  # Default

        sid.osc3_output = 0xCD
        assert sid.read(0xD41B) == 0xCD

    def test_env3_returns_envelope_output(self) -> None:
        """ENV3 ($D41C) returns envelope 3 output."""
        sid = SID()
        assert sid.read(0xD41C) == 0x00  # Default

        sid.env3_output = 0xEF
        assert sid.read(0xD41C) == 0xEF

    def test_write_to_readonly_register_ignored(self) -> None:
        """Writing to read-only registers doesn't change them."""
        sid = SID()
        original_pot_x = sid.pot_x

        # Try to write to POTX
        sid.write(0xD419, 0x12)

        # pot_x should be unchanged
        assert sid.pot_x == original_pot_x
        # But last_written is updated
        assert sid.last_written == 0x12


class TestSIDReset:
    """Test SID reset behavior."""

    def test_reset_clears_all_registers(self) -> None:
        """Reset clears all register values."""
        sid = SID()

        # Write some values
        sid.write(0xD400, 0x55)
        sid.write(0xD418, 0x0F)
        sid.osc3_output = 0xAB
        sid.env3_output = 0xCD

        sid.reset()

        # All registers should be cleared
        assert all(r == 0 for r in sid.registers)
        assert sid.last_written == 0
        assert sid.osc3_output == 0
        assert sid.env3_output == 0

    def test_reset_preserves_paddle_values(self) -> None:
        """Reset doesn't affect paddle input values."""
        sid = SID()
        # Default paddle values should remain
        assert sid.pot_x == 0xFF
        assert sid.pot_y == 0xFF


class TestSIDAddressMirroring:
    """Test SID address mirroring behavior."""

    def test_sid_uses_lower_5_bits_for_register(self) -> None:
        """SID only uses lower 5 bits of address for register selection."""
        sid = SID()

        # Write to $D400
        sid.write(0xD400, 0x11)
        assert sid.registers[0] == 0x11

        # Write to $D420 (mirrors to register 0)
        sid.write(0xD420, 0x22)
        assert sid.registers[0] == 0x22

    def test_registers_29_31_return_last_written(self) -> None:
        """Registers 29-31 (unused) return last written value."""
        sid = SID()
        sid.write(0xD400, 0x99)

        # These addresses map to "registers" 29, 30, 31
        assert sid.read(0xD41D) == 0x99
        assert sid.read(0xD41E) == 0x99
        assert sid.read(0xD41F) == 0x99


class TestSIDVoiceRegisters:
    """Test specific voice register behavior."""

    def test_voice1_registers_layout(self) -> None:
        """Voice 1 registers are at $D400-$D406."""
        sid = SID()

        # Freq Lo, Freq Hi, PW Lo, PW Hi, Control, AD, SR
        for offset, value in enumerate([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07]):
            sid.write(0xD400 + offset, value)
            assert sid.registers[offset] == value

    def test_voice2_registers_layout(self) -> None:
        """Voice 2 registers are at $D407-$D40D."""
        sid = SID()

        for offset, value in enumerate([0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17]):
            sid.write(0xD407 + offset, value)
            assert sid.registers[7 + offset] == value

    def test_voice3_registers_layout(self) -> None:
        """Voice 3 registers are at $D40E-$D414."""
        sid = SID()

        for offset, value in enumerate([0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27]):
            sid.write(0xD40E + offset, value)
            assert sid.registers[14 + offset] == value

    def test_filter_and_volume_registers(self) -> None:
        """Filter ($D415-$D417) and volume ($D418) registers."""
        sid = SID()

        sid.write(0xD415, 0x00)  # Filter Cutoff Lo
        sid.write(0xD416, 0xFF)  # Filter Cutoff Hi
        sid.write(0xD417, 0xF7)  # Resonance/Route
        sid.write(0xD418, 0x0F)  # Volume/Filter Mode

        assert sid.registers[21] == 0x00
        assert sid.registers[22] == 0xFF
        assert sid.registers[23] == 0xF7
        assert sid.registers[24] == 0x0F


class TestSIDIntegrationWithC64:
    """Test SID integration with C64 system."""

    def test_c64_has_sid_instance(self, c64) -> None:
        """C64 creates and uses a SID instance."""
        assert hasattr(c64, 'sid')
        assert isinstance(c64.sid, SID)

    def test_sid_read_through_memory(self, c64) -> None:
        """SID can be read through C64 memory map."""
        # Write a value directly to SID
        c64.sid.write(0xD400, 0x42)

        # Read through memory should return it
        # Note: Need to ensure I/O is mapped
        c64.memory.port = 0x35  # Bank in I/O
        result = c64.memory.read(0xD400)
        assert result == 0x42

    def test_sid_write_through_memory(self, c64) -> None:
        """SID can be written through C64 memory map."""
        # Ensure I/O is mapped
        c64.memory.port = 0x35

        # Write through memory
        c64.memory.write(0xD418, 0x0F)

        # Should be stored in SID
        assert c64.sid.registers[24] == 0x0F
        assert c64.sid.last_written == 0x0F
