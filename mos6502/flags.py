#!/usr/bin/env python3
"""Flags for the mos6502 CPU.

Performance optimization: Flags are stored as a plain int, not a bitarray.
Bit operations use simple masking instead of bitarray indexing.
"""

import logging
from typing import Self

# Dedicated logger for flag modifications
flag_logger = logging.getLogger("mos6502.cpu.flags")

# Bit positions (from LSB, matching 6502 status register layout)
# Status register layout: NV-BDIZC (bit 7 to bit 0)
C: int = 0  # Carry
Z: int = 1  # Zero
I: int = 2  # IRQ Disable  # noqa: E741
D: int = 3  # Decimal Mode
B: int = 4  # Break Command
_: int = 5  # Unused (always 1)
V: int = 6  # Overflow
N: int = 7  # Negative

# Bit masks for each flag
C_MASK: int = 1 << C  # 0x01
Z_MASK: int = 1 << Z  # 0x02
I_MASK: int = 1 << I  # 0x04
D_MASK: int = 1 << D  # 0x08
B_MASK: int = 1 << B  # 0x10
_MASK: int = 1 << _   # 0x20
V_MASK: int = 1 << V  # 0x40
N_MASK: int = 1 << N  # 0x80

# Flag names for logging
FLAG_NAMES = {
    0: "C",
    1: "Z",
    2: "I",
    3: "D",
    4: "B",
    5: "_",
    6: "V",
    7: "N",
}


def format_flags(flags_value: int) -> str:
    """Format flags register as NV-BDIZC string (uppercase=set, lowercase=clear).

    Args:
    ----
        flags_value: The flags register value (0x00-0xFF)

    Returns:
    -------
        Formatted string like "Nv-Bdizc" or "NV-BDIZC"

    """
    return (
        f"{'N' if flags_value & N_MASK else 'n'}"
        f"{'V' if flags_value & V_MASK else 'v'}"
        "-"  # Unused flag
        f"{'B' if flags_value & B_MASK else 'b'}"
        f"{'D' if flags_value & D_MASK else 'd'}"
        f"{'I' if flags_value & I_MASK else 'i'}"
        f"{'Z' if flags_value & Z_MASK else 'z'}"
        f"{'C' if flags_value & C_MASK else 'c'}"
    )


class FlagsRegister:
    """Int-based flags register with change logging.

    Stores the 6502 processor status register as a plain int for performance.
    Provides indexed access via __getitem__/__setitem__ for compatibility.
    """

    __slots__ = ('_value', '_last_logged_value')

    def __init__(self: Self, value: int = 0, endianness: str = "little") -> None:
        """Initialize FlagsRegister.

        Args:
            value: Initial flags value (0x00-0xFF), or a FlagsRegister to copy
            endianness: Ignored, kept for API compatibility
        """
        if isinstance(value, FlagsRegister):
            self._value: int = value._value
        elif hasattr(value, 'value'):
            # Handle Byte or other objects with .value
            self._value: int = int(value.value) & 0xFF
        else:
            self._value: int = int(value) & 0xFF
        self._last_logged_value: int = self._value

    @property
    def value(self: Self) -> int:
        """Return the flags register value as an int (0x00-0xFF)."""
        return self._value

    @value.setter
    def value(self: Self, new_value: int) -> None:
        """Set the flags register value."""
        self._value = int(new_value) & 0xFF

    def __getitem__(self: Self, bit_index: int) -> int:
        """Get a flag bit by index. Returns 0 or 1."""
        return (self._value >> bit_index) & 1

    def __setitem__(self: Self, bit_index: int, bit_value: int) -> None:
        """Set a flag bit by index.

        Args:
            bit_index: Bit position (0-7)
            bit_value: New value (0 or non-zero for 1)
        """
        # Normalize to 0 or 1
        new_bit = 1 if bit_value else 0
        old_bit = (self._value >> bit_index) & 1

        # Early return if no change
        if old_bit == new_bit:
            return

        # Update the bit
        if new_bit:
            self._value |= (1 << bit_index)
        else:
            self._value &= ~(1 << bit_index)

        # Log if overall value changed since last log
        if self._value != self._last_logged_value:
            flag_logger.info(f"⎿ {format_flags(self._value)} (0x{self._value:02X})")
            self._last_logged_value = self._value

    def __int__(self: Self) -> int:
        """Return the flags value as an int."""
        return self._value

    def __and__(self: Self, other: int) -> int:
        """Bitwise AND with an int."""
        return self._value & other

    def __or__(self: Self, other: int) -> int:
        """Bitwise OR with an int."""
        return self._value | other

    def __eq__(self: Self, other: object) -> bool:
        """Compare equality with another FlagsRegister or int."""
        if isinstance(other, FlagsRegister):
            return self._value == other._value
        if isinstance(other, int):
            return self._value == other
        return NotImplemented

    def __repr__(self: Self) -> str:
        """Return a string representation."""
        return f"FlagsRegister(0x{self._value:02X})"


# Legacy compatibility - these were used for bitarray operations
# Now we use simple bit masks instead
class ProcessorStatusFlags:
    """Legacy flag constants for compatibility.

    These are kept for any code that references ProcessorStatusFlags.C, etc.
    The actual values are just the bit masks now.
    """

    # These return 1 for the bit position (for compatibility with old code)
    C = type('FlagBit', (), {'__getitem__': lambda s, i: 1})()
    Z = type('FlagBit', (), {'__getitem__': lambda s, i: 1})()
    I = type('FlagBit', (), {'__getitem__': lambda s, i: 1})()  # noqa: E741
    D = type('FlagBit', (), {'__getitem__': lambda s, i: 1})()
    B = type('FlagBit', (), {'__getitem__': lambda s, i: 1})()
    V = type('FlagBit', (), {'__getitem__': lambda s, i: 1})()
    N = type('FlagBit', (), {'__getitem__': lambda s, i: 1})()

    # SET_ZERO returns 0, SET_ONE returns 1 (for legacy test compatibility)
    SET_ZERO = type('SetZero', (), {'__getitem__': lambda s, i: 0})()
    SET_ONE = type('SetOne', (), {'__getitem__': lambda s, i: 1})()


class ProcessorStatusFlagsInterface:
    """CPU interface for the mos6502 CPU flags.

    Provides property access to individual flags via the CPU's _flags attribute.
    """

    __slots__ = ()  # No instance attributes - just property accessors

    @property
    def C(self: Self) -> bool:  # noqa: N802
        """C is True if the Carry flag is set."""
        return bool(self._flags[C])

    @C.setter
    def C(self: Self, flag: int) -> None:  # noqa: N802
        """Set the Carry flag."""
        self._flags[C] = flag

    @property
    def Z(self: Self) -> bool:  # noqa: N802
        """Z is True if the Zero flag is set."""
        return bool(self._flags[Z])

    @Z.setter
    def Z(self: Self, flag: int) -> None:  # noqa: N802
        """Set the Zero flag."""
        self._flags[Z] = flag

    @property
    def I(self: Self) -> bool:  # noqa: E743 N802
        """I is True if the IRQ Disable flag is set."""
        return bool(self._flags[I])

    @I.setter
    def I(self: Self, flag: int) -> None:  # noqa: E743 N802
        """Set the IRQ Disable flag."""
        self._flags[I] = flag

    @property
    def D(self: Self) -> bool:  # noqa: N802
        """D is True if the Decimal Mode flag is set."""
        return bool(self._flags[D])

    @D.setter
    def D(self: Self, flag: int) -> None:  # noqa: N802
        """Set the Decimal Mode flag."""
        self._flags[D] = flag

    @property
    def B(self: Self) -> bool:  # noqa: N802
        """B is True if the Break flag is set."""
        return bool(self._flags[B])

    @B.setter
    def B(self: Self, flag: int) -> None:  # noqa: N802
        """Set the Break flag."""
        self._flags[B] = flag

    @property
    def V(self: Self) -> bool:  # noqa: N802
        """V is True if the Overflow flag is set."""
        return bool(self._flags[V])

    @V.setter
    def V(self: Self, flag: int) -> None:  # noqa: N802
        """Set the Overflow flag."""
        self._flags[V] = flag

    @property
    def N(self: Self) -> bool:  # noqa: N802
        """N is True if the Negative flag is set."""
        return bool(self._flags[N])

    @N.setter
    def N(self: Self, flag: int) -> None:  # noqa: N802
        """Set the Negative flag."""
        self._flags[N] = flag
