#!/usr/bin/env python3
"""Flags for the mos6502 CPU."""

from typing import Self

import bitarray
from bitarray.util import int2ba

# Bit index into flags bitarray
C: int = 0x07
Z: int = 0x06
I: int = 0x05  # noqa: E741
D: int = 0x04
B: int = 0x03
_: int = 0x02
V: int = 0x01
N: int = 0x00


class ProcessorStatusFlags:
    """Flags for the mos6502 CPU."""

    # Simplifies tests
    SET_ZERO: bitarray.bitarray = bitarray.bitarray([0] * 8, endian="little")
    SET_ONE: bitarray.bitarray = bitarray.bitarray([1] * 8, endian="little")

    # Carry Flag - 0 == False, 1 == True
    C: bitarray.bitarray = int2ba(1 << C, endian="little")

    # Zero Flag - 0 == Result not zero, 1 == Result zero
    Z: bitarray.bitarray = int2ba(1 << Z, endian="little")

    # IRQ Disable Flag - 0 == Enable, 1 == Disable
    I: bitarray.bitarray = int2ba(1 << I, endian="little")   # noqa: E741

    # Decimal Mode Flag - 0 == False, 1 == True
    D: bitarray.bitarray = int2ba(1 << D, endian="little")

    # Break Command Flag - 0 == No break, 1 == Break
    B: bitarray.bitarray = int2ba(1 << B, endian="little")

    # Unused
    _: bitarray.bitarray = int2ba(1 << _, endian="little")

    # Overflow Flag - 0 == False, 1 == True
    V: bitarray.bitarray = int2ba(1 << V, endian="little")

    # Negative Flag - 0 == Positive, 1 == Negative
    N: bitarray.bitarray = int2ba(1 << N, endian="little")


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
    def Z(self: Self, flag: bitarray.bitarray) -> None:  # noqa: N802
        """Set the Z flag to {flag}."""
        self._flags[Z] = flag

    @property
    def I(self: Self) -> bool:  # noqa: E743 N802
        """I is True if the CPU.I flag non-zero."""
        return self._flags[I] & ProcessorStatusFlags.I[I]

    @I.setter
    def I(self: Self, flag: bitarray.bitarray) -> None:  # noqa: E743 N802
        """Set the I flag to {flag}."""
        self._flags[I] = flag

    @property
    def D(self: Self) -> bool:  # noqa: N802
        """D is True if the CPU.D flag non-zero."""
        return self._flags[D] & ProcessorStatusFlags.D[D]

    @D.setter
    def D(self: Self, flag: bitarray.bitarray) -> None:  # noqa: N802
        """Set the D flag to {flag}."""
        self._flags[D] = flag

    @property
    def B(self: Self) -> bool:  # noqa: N802
        """B is True if the CPU.B flag non-zero."""
        return self._flags[B] & ProcessorStatusFlags.B[B]

    @B.setter
    def B(self: Self, flag: bitarray.bitarray) -> None:  # noqa: N802
        """Set the B flag to {flag}."""
        self._flags[B] = flag

    @property
    def V(self: Self) -> bool:  # noqa: N802
        """V is True if the CPU.V flag non-zero."""
        return self._flags[V] & ProcessorStatusFlags.V[V]

    @V.setter
    def V(self: Self, flag: bitarray.bitarray) -> None:  # noqa: N802
        """Set the V flag to {flag}."""
        self._flags[V] = flag

    @property
    def N(self: Self) -> bool:  # noqa: N802
        """N is True if the CPU.N flag non-zero."""
        return self._flags[N] & ProcessorStatusFlags.N[N]

    @N.setter
    def N(self: Self, flag: bitarray.bitarray) -> None:  # noqa: N802
        """Set the N flag to {flag}."""
        self._flags[N] = flag
