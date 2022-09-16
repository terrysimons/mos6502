#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mos6502 Registers.

This module implements the mos6502 register set.
"""

import mos6502
import mos6502.memory
from mos6502.memory import Byte, Word


class Registers:
    """The mos6502 register set."""

    def __init__(self,
                 endianness=mos6502.memory.ENDIANNESS,
                 PC=Word(0x00),
                 SP=Word(0x00),
                 A=Byte(0x00),
                 X=Byte(0x00),
                 Y=Byte(0x00)):
        """
        Return a mos6502 register instance.

        Parameters:
            endianness: the endianness of the architecture - "big" or "little" (default=little)
            PC: the mos6502 program counter
            SP: the mos6502 stack pointer
            A: the mos6502 accumulator
            X: the mos6502 X index register
            Y: the mos6502 Y index register
        """
        super().__init__()
        self.endianness = endianness

        # We recast the values here with <Byte|Word>.value to ensure proper
        # endianness
        self._PC: Word = Word(value=PC.value, endianness=self.endianness)

        # SP is 8-bit in hardware, but it is convenient to be 16-bit here.
        #
        # Only holds an offset of 255 values starting at 0x100 - 0x1FF
        # We mask the value with 0xFF as a @property.
        self._SP: Word = Word(SP.value, endianness=self.endianness)
        self._A: Byte = Byte(A.value, endianness=self.endianness)
        self._X: Byte = Byte(X.value, endianness=self.endianness)
        self._Y: Byte = Byte(Y.value, endianness=self.endianness)

    @property
    def PC(self) -> int:
        """Return the PC register as an int."""
        return self._PC.value & 0xFFFF

    @PC.setter
    def PC(self, PC) -> None:
        """Set the PC register as an int with the correct endianness."""
        value: int = PC & 0xFFFF

        value: Word = Word(value=value, endianness=self.endianness)

        self._PC = value

    @property
    def SP(self) -> int:
        """Return the PC register as an int."""
        # SP is 8-bits, so mask off.
        #
        # This simplifies handling overflow with bitarrays.
        return self._SP.value & 0xFF

    @SP.setter
    def SP(self, SP) -> None:
        """Set the SP register."""
        # SP is 8-bits, so mask off.
        #
        # This simplifies handling overflow with bitarrays.
        value: int = SP & 0xFF

        value: Word = Word(value=value, endianness=self.endianness)

        self._SP = value

    @property
    def A(self) -> int:
        """Return the A register."""
        return self._A.value & 0xFF

    @A.setter
    def A(self, A) -> None:
        """Set the A register."""
        value: int = A & 0xFF

        value: Byte = Byte(value=value)

        self._A = value

    @property
    def X(self) -> int:
        """Return the X register."""
        return self._X.value & 0xFF

    @X.setter
    def X(self, X) -> None:
        """Set the X register."""
        value: int = X & 0xFF

        value: Byte = Byte(value)

        self._X = value

    @property
    def Y(self) -> int:
        """Return the Y register."""
        return self._Y.value & 0xFF

    @Y.setter
    def Y(self, Y) -> None:
        """Set the Y register."""
        value: int = Y & 0xFF

        value: Byte = Byte(value=value, endianness=self.endianness)

        self._Y = value
