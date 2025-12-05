#!/usr/bin/env python3
"""
SID (Sound Interface Device - 6581/8580) emulation for C64.

This is a minimal implementation for diagnostic compatibility.
It stores register values and provides proper read behavior.

Register Map:
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

On the real SID, reading write-only registers returns the last
value written to ANY SID register (due to data bus capacitance).
"""

from __future__ import annotations

import logging


class SID:
    """
    SID (6581/8580) chip emulation.

    VARIANT: 6581 - Original NMOS SID (C64 breadbin, early C64C)
    VARIANT: 8580 - Later CMOS SID (late C64C, C128)

    The 8580 has slightly different filter characteristics and
    different behavior for some edge cases, but for diagnostic
    purposes they are functionally identical.
    """

    def __init__(self) -> None:
        self.log = logging.getLogger("c64.sid")

        # All 29 SID registers (25 write-only + 4 read-only)
        self.registers = [0] * 29

        # Last value written to any register (for write-only register reads)
        self.last_written = 0

        # Paddle positions (0-255, 255 = no paddle/fully right)
        self.pot_x = 0xFF
        self.pot_y = 0xFF

        # Oscillator 3 and Envelope 3 output (read-only registers)
        # These would normally come from actual sound synthesis
        self.osc3_output = 0
        self.env3_output = 0

    def reset(self) -> None:
        """Reset SID to initial state."""
        self.registers = [0] * 29
        self.last_written = 0
        self.osc3_output = 0
        self.env3_output = 0

    def read(self, addr: int) -> int:
        """Read SID register.

        Args:
            addr: Full address ($D400-$D41F)

        Returns:
            Register value
        """
        reg = addr & 0x1F  # SID has 32 addresses, but only 29 registers

        if reg < 25:
            # Write-only registers: return last written value
            # (Real SID returns last bus value due to capacitance)
            return self.last_written

        if reg == 25:  # POTX ($D419)
            return self.pot_x

        if reg == 26:  # POTY ($D41A)
            return self.pot_y

        if reg == 27:  # OSC3 ($D41B)
            return self.osc3_output

        if reg == 28:  # ENV3 ($D41C)
            return self.env3_output

        # Registers 29-31 are mirrors or unused
        return self.last_written

    def write(self, addr: int, value: int) -> None:
        """Write SID register.

        Args:
            addr: Full address ($D400-$D41F)
            value: Value to write (0-255)
        """
        reg = addr & 0x1F

        # Store the value (for later reads of write-only registers)
        self.last_written = value

        if reg < 25:
            # Store in register array for potential future use
            self.registers[reg] = value

        # Read-only registers (25-28) ignore writes
