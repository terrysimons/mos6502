#!/usr/bin/env python3
"""Flags for the mos6502 CPU."""

import logging
from typing import Self

from mos6502.bitarray_factory import bitarray, int2ba

from mos6502.memory import Byte

# Dedicated logger for flag modifications
flag_logger = logging.getLogger("mos6502.cpu.flags")

# Bit index into flags bitarray
C: int = 0x07
Z: int = 0x06
I: int = 0x05  # noqa: E741
D: int = 0x04
B: int = 0x03
_: int = 0x02
V: int = 0x01
N: int = 0x00

# Flag names for logging
FLAG_NAMES = {
    0x00: "N",
    0x01: "V",
    0x02: "_",
    0x03: "B",
    0x04: "D",
    0x05: "I",
    0x06: "Z",
    0x07: "C",
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
    # Extract individual flag bits from flags_value
    n_bit = (flags_value >> N) & 1
    v_bit = (flags_value >> V) & 1
    b_bit = (flags_value >> B) & 1
    d_bit = (flags_value >> D) & 1
    i_bit = (flags_value >> I) & 1
    z_bit = (flags_value >> Z) & 1
    c_bit = (flags_value >> C) & 1

    return (
        f"{'N' if n_bit else 'n'}"
        f"{'V' if v_bit else 'v'}"
        "-"  # Unused flag
        f"{'B' if b_bit else 'b'}"
        f"{'D' if d_bit else 'd'}"
        f"{'I' if i_bit else 'i'}"
        f"{'Z' if z_bit else 'z'}"
        f"{'C' if c_bit else 'c'}"
    )


class FlagsRegister(Byte):
    """A Byte that logs all individual flag bit modifications."""

    def __init__(self: Self, value: int = 0, endianness: str = "little") -> None:
        """Initialize FlagsRegister with tracking for change detection."""
        super().__init__(value, endianness)
        self._last_logged_value: int = value

    def __setitem__(self: Self, index: int, value: int) -> None:
        """Set a flag bit, but only if it's different. Log only on change."""
        # Get current value of this bit
        old_bit_value = int(self._value[index])
        new_bit_value = int(value) if isinstance(value, int) else int(value._value[index])  # noqa: SLF001

        # Early return if no change - saves cycles!
        if old_bit_value == new_bit_value:
            return

        # Call parent to actually set the value
        super().__setitem__(index, value)

        # Only log if the overall flags value changed since last log
        # This prevents logging the same value multiple times
        if self.value != self._last_logged_value:
            flag_logger.info(f"⎿ {format_flags(self.value)} (0x{self.value:02X})")
            self._last_logged_value = self.value


class ProcessorStatusFlags:
    """Flags for the mos6502 CPU."""

    # Simplifies tests
    SET_ZERO = bitarray([0] * 8, endian="little")
    SET_ONE = bitarray([1] * 8, endian="little")

    # Carry Flag - 0 == False, 1 == True
    C = int2ba(1 << C, endian="little")

    # Zero Flag - 0 == Result not zero, 1 == Result zero
    Z = int2ba(1 << Z, endian="little")

    # IRQ Disable Flag - 0 == Enable, 1 == Disable
    I = int2ba(1 << I, endian="little")  # noqa: E741

    # Decimal Mode Flag - 0 == False, 1 == True
    D = int2ba(1 << D, endian="little")

    # Break Command Flag - 0 == No break, 1 == Break
    B = int2ba(1 << B, endian="little")

    # Unused
    _ = int2ba(1 << _, endian="little")

    # Overflow Flag - 0 == False, 1 == True
    V = int2ba(1 << V, endian="little")

    # Negative Flag - 0 == Positive, 1 == Negative
    N = int2ba(1 << N, endian="little")


class ProcessorStatusFlagsInterface:
    """CPU interface for the mos6502 CPU flags."""

    @property
    def C(self: Self) -> bool:  # noqa: N802
        """C is True if the CPU.C flag non-zero."""
        return self._flags[C] & ProcessorStatusFlags.C[C]

    @C.setter
    def C(self: Self, flag: int) -> None:  # noqa: N802
        """Set the C flag to {flag}."""
        self._flags[C] = flag

    @property
    def Z(self: Self) -> bool:  # noqa: N802
        """Z is True if the CPU.Z flag non-zero."""
        return self._flags[Z] & ProcessorStatusFlags.Z[Z]

    @Z.setter
    def Z(self: Self, flag: bitarray) -> None:  # noqa: N802
        """Set the Z flag to {flag}."""
        self._flags[Z] = flag

    @property
    def I(self: Self) -> bool:  # noqa: E743 N802
        """I is True if the CPU.I flag non-zero."""
        return self._flags[I] & ProcessorStatusFlags.I[I]

    @I.setter
    def I(self: Self, flag: bitarray) -> None:  # noqa: E743 N802
        """Set the I flag to {flag}."""
        self._flags[I] = flag

    @property
    def D(self: Self) -> bool:  # noqa: N802
        """D is True if the CPU.D flag non-zero."""
        return self._flags[D] & ProcessorStatusFlags.D[D]

    @D.setter
    def D(self: Self, flag: bitarray) -> None:  # noqa: N802
        """Set the D flag to {flag}."""
        self._flags[D] = flag

    @property
    def B(self: Self) -> bool:  # noqa: N802
        """B is True if the CPU.B flag non-zero."""
        return self._flags[B] & ProcessorStatusFlags.B[B]

    @B.setter
    def B(self: Self, flag: bitarray) -> None:  # noqa: N802
        """Set the B flag to {flag}."""
        self._flags[B] = flag

    @property
    def V(self: Self) -> bool:  # noqa: N802
        """V is True if the CPU.V flag non-zero."""
        return self._flags[V] & ProcessorStatusFlags.V[V]

    @V.setter
    def V(self: Self, flag: bitarray) -> None:  # noqa: N802
        """Set the V flag to {flag}."""
        self._flags[V] = flag

    @property
    def N(self: Self) -> bool:  # noqa: N802
        """N is True if the CPU.N flag non-zero."""
        return self._flags[N] & ProcessorStatusFlags.N[N]

    @N.setter
    def N(self: Self, flag: bitarray) -> None:  # noqa: N802
        """Set the N flag to {flag}."""
        self._flags[N] = flag
