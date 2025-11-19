#!/usr/bin/env python3
"""
mos6502 Registers.

This module implements the mos6502 register set.
"""
from typing import Self

import mos6502
import mos6502.memory
from mos6502.memory import Byte, Word

ZERO_BYTE: Byte = Byte(0x00)
ZERO_WORD: Word = Word(0x00)
class Registers:
    """The mos6502 register set."""

    def __init__(
        self: Self,
        endianness: str = mos6502.memory.ENDIANNESS,
        PC: int = ZERO_WORD,  # noqa: N803
        S: int = ZERO_WORD,  # noqa: N803
        A: int = ZERO_BYTE,  # noqa: N803
        X: int = ZERO_BYTE,  # noqa: N803
        Y: int = ZERO_BYTE,  # noqa: N803
    ) -> None:
        """
        Return a mos6502 register instance.

        Parameters
        ----------
            endianness: the endianness of the architecture - "big" or "little" (default=little)
            PC: the mos6502 program counter
            S: the mos6502 stack pointer
            A: the mos6502 accumulator
            X: the mos6502 X index register
            Y: the mos6502 Y index register
        """
        super().__init__()
        self.endianness = endianness

        # We recast the values here with <Byte|Word>.value to ensure proper
        # endianness
        self._PC: Word = Word(value=PC.value, endianness=self.endianness)

        # S is 8-bit in hardware, but it is convenient to be 16-bit here.
        #
        # Only holds an offset of 255 values starting at 0x100 - 0x1FF
        # We mask the value with 0xFF as a @property.
        self._S: Word = Word(S.value, endianness=self.endianness)
        self._A: Byte = Byte(A.value, endianness=self.endianness)
        self._X: Byte = Byte(X.value, endianness=self.endianness)
        self._Y: Byte = Byte(Y.value, endianness=self.endianness)

    @property
    def PC(self: Self) -> int:  # noqa: N802
        """Return the PC register as an int."""
        return self._PC.value & 0xFFFF

    @PC.setter
    def PC(self: Self, PC: int) -> None:  # noqa: N802, N803
        """Set the PC register as an int with the correct endianness."""
        value: int = PC & 0xFFFF

        value: Word = Word(value=value, endianness=self.endianness)

        self._PC = value

    @property
    def S(self: Self) -> int:  # noqa: N802
        """Return the PC register as an int."""
        # S is 8-bits, so mask off.
        #
        # This simplifies handling overflow with bitarrays.
        return self._S.value & 0x1FF

    @S.setter
    def S(self: Self, S: int) -> None:  # noqa: N802, N803
        """Set the S register."""
        # S is 8-bits, so mask off.
        #
        # This simplifies handling overflow with bitarrays.
        value: int = S & 0x1FF

        value: Word = Word(value=value, endianness=self.endianness)

        self._S: Word = value

    @property
    def A(self: Self) -> int:  # noqa: N802
        """Return the A register."""
        return self._A.value & 0xFF

    @A.setter
    def A(self: Self, A: int) -> None:  # noqa: N802, N803
        """Set the A register."""
        value: int = A & 0xFF

        value: Byte = Byte(value=value)

        self._A = value

    @property
    def X(self: Self) -> int:  # noqa: N802
        """Return the X register."""
        return self._X.value & 0xFF

    @X.setter
    def X(self: Self, X: int) -> None:  # noqa: N802, N803
        """Set the X register."""
        value: int = X & 0xFF

        value: Byte = Byte(value)

        self._X = value

    @property
    def Y(self: Self) -> int:  # noqa: N802
        """Return the Y register."""
        return self._Y.value & 0xFF

    @Y.setter
    def Y(self: Self, Y: int) -> None:  # noqa: N802, N803
        """Set the Y register."""
        value: int = Y & 0xFF

        value: Byte = Byte(value=value, endianness=self.endianness)

        self._Y = value
