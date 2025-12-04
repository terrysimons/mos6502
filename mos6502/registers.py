#!/usr/bin/env python3
"""
mos6502 Registers.

This module implements the mos6502 register set.

Performance optimization: Registers are stored as plain ints, not Byte/Word objects.
This eliminates object creation and bitarray conversion overhead on every access.
"""
from typing import Self


class Registers:
    """The mos6502 register set.

    All registers are stored as plain Python ints for maximum performance.
    Masking is applied on access to enforce bit widths:
    - PC: 16-bit (0x0000-0xFFFF)
    - S: 9-bit (0x0100-0x01FF) - stack pointer always in page 1
    - A, X, Y: 8-bit (0x00-0xFF)
    """

    __slots__ = ('_PC', '_S', '_A', '_X', '_Y')

    def __init__(
        self: Self,
        endianness: str = "little",  # Kept for API compatibility, not used
        PC: int = 0x0000,  # noqa: N803
        S: int = 0x0000,  # noqa: N803
        A: int = 0x00,  # noqa: N803
        X: int = 0x00,  # noqa: N803
        Y: int = 0x00,  # noqa: N803
    ) -> None:
        """
        Return a mos6502 register instance.

        Parameters
        ----------
            endianness: kept for API compatibility (ignored - registers are just ints)
            PC: the mos6502 program counter (16-bit)
            S: the mos6502 stack pointer (8-bit, but stored with page 1 offset)
            A: the mos6502 accumulator (8-bit)
            X: the mos6502 X index register (8-bit)
            Y: the mos6502 Y index register (8-bit)
        """
        # Store registers as plain ints - no Byte/Word object overhead
        self._PC: int = PC & 0xFFFF
        self._S: int = S & 0x1FF  # 9 bits to include page 1 offset
        self._A: int = A & 0xFF
        self._X: int = X & 0xFF
        self._Y: int = Y & 0xFF

    @property
    def PC(self: Self) -> int:  # noqa: N802
        """Return the PC register as an int (16-bit)."""
        return self._PC

    @PC.setter
    def PC(self: Self, value: int) -> None:  # noqa: N802
        """Set the PC register (16-bit, masked to 0x0000-0xFFFF)."""
        self._PC = value & 0xFFFF

    @property
    def S(self: Self) -> int:  # noqa: N802
        """Return the S (stack pointer) register as an int.

        The stack pointer is 8-bit in hardware but stored with the page 1
        offset (0x0100) for convenience. Returns values in range 0x0100-0x01FF.
        """
        return self._S

    @S.setter
    def S(self: Self, value: int) -> None:  # noqa: N802
        """Set the S register (masked to 9 bits: 0x0100-0x01FF range)."""
        self._S = value & 0x1FF

    @property
    def A(self: Self) -> int:  # noqa: N802
        """Return the A (accumulator) register as an int (8-bit)."""
        return self._A

    @A.setter
    def A(self: Self, value: int) -> None:  # noqa: N802
        """Set the A register (8-bit, masked to 0x00-0xFF)."""
        self._A = value & 0xFF

    @property
    def X(self: Self) -> int:  # noqa: N802
        """Return the X index register as an int (8-bit)."""
        return self._X

    @X.setter
    def X(self: Self, value: int) -> None:  # noqa: N802
        """Set the X register (8-bit, masked to 0x00-0xFF)."""
        self._X = value & 0xFF

    @property
    def Y(self: Self) -> int:  # noqa: N802
        """Return the Y index register as an int (8-bit)."""
        return self._Y

    @Y.setter
    def Y(self: Self, value: int) -> None:  # noqa: N802
        """Set the Y register (8-bit, masked to 0x00-0xFF)."""
        self._Y = value & 0xFF
