#!/usr/bin/env python3
"""Pure Python implementation of bitarray interface for mos6502.

This module provides a drop-in replacement for bitarray.bitarray and
bitarray.util functions (ba2int, int2ba) used by the mos6502 emulator.

Usage:
    from mos6502.pybitarray import pybitarray as bitarray
    from mos6502.pybitarray import ba2int, int2ba
"""

from __future__ import annotations

from typing import Literal, Self


class pybitarray:
    """Pure Python implementation of bitarray.bitarray interface.

    Implements only the subset of bitarray functionality used by mos6502:
    - Constructor from int, list, or another pybitarray
    - endian property
    - tobytes() method
    - Bit indexing (__getitem__, __setitem__)
    - Slicing
    - Shift operators (<<, >>)
    - Comparison operators (<, >, <=, >=, ==)
    - len()
    """

    def __init__(
        self: Self,
        initializer: int | list[int] | "pybitarray" = 0,
        *,
        length: int | None = None,
        endian: Literal["little", "big"] = "little",
    ) -> None:
        """Initialize a pybitarray.

        Args:
        ----
            initializer: int value, list of bits, or another pybitarray
            length: number of bits (required for int initializer)
            endian: "little" or "big" endianness

        """
        self._endian: Literal["little", "big"] = endian

        if isinstance(initializer, pybitarray):
            self._bits: list[int] = initializer._bits[:]  # noqa: SLF001
            self._endian = initializer._endian  # noqa: SLF001
        elif isinstance(initializer, list):
            self._bits = initializer[:]
        elif isinstance(initializer, int):
            # Convert int to bits - this should match int2ba behavior
            bit_length = length if length is not None else 8
            self._bits = _int_to_bits(initializer, bit_length, endian)
        else:
            # Default empty bitarray
            self._bits = [0] * (length or 8)

    @property
    def endian(self: Self) -> Literal["little", "big"]:
        """Return the endianness of this bitarray."""
        return self._endian

    def __len__(self: Self) -> int:
        """Return the number of bits."""
        return len(self._bits)

    def __getitem__(self: Self, index: int | slice) -> "pybitarray | int":
        """Get bit(s) at index or slice.

        Returns:
        -------
            int for single index, pybitarray for slice

        """
        if isinstance(index, slice):
            return pybitarray(self._bits[index], endian=self._endian)
        return self._bits[index]

    def __setitem__(self: Self, index: int, value: int) -> None:
        """Set bit at index to value (0 or 1)."""
        self._bits[index] = value & 1

    def __lshift__(self: Self, count: int) -> "pybitarray":
        """Left shift by count bits, preserving length."""
        if count <= 0:
            return pybitarray(self._bits[:], endian=self._endian)
        if count >= len(self._bits):
            return pybitarray([0] * len(self._bits), endian=self._endian)

        # For little-endian: shift means moving bits to higher indices
        # New low bits become 0, high bits fall off
        if self._endian == "little":
            new_bits = [0] * count + self._bits[: len(self._bits) - count]
        else:
            # For big-endian: shift means moving bits to lower indices
            new_bits = self._bits[count:] + [0] * count

        return pybitarray(new_bits, endian=self._endian)

    def __rshift__(self: Self, count: int) -> "pybitarray":
        """Right shift by count bits, preserving length."""
        if count <= 0:
            return pybitarray(self._bits[:], endian=self._endian)
        if count >= len(self._bits):
            return pybitarray([0] * len(self._bits), endian=self._endian)

        # For little-endian: shift means moving bits to lower indices
        # New high bits become 0, low bits fall off
        if self._endian == "little":
            new_bits = self._bits[count:] + [0] * count
        else:
            # For big-endian: shift means moving bits to higher indices
            new_bits = [0] * count + self._bits[: len(self._bits) - count]

        return pybitarray(new_bits, endian=self._endian)

    def __eq__(self: Self, other: object) -> bool:
        """Equality comparison."""
        if isinstance(other, pybitarray):
            return self._bits == other._bits
        if isinstance(other, list):
            return self._bits == other
        return NotImplemented

    def __lt__(self: Self, other: "pybitarray") -> bool:
        """Less than comparison (compares integer values)."""
        if isinstance(other, pybitarray):
            return ba2int(self) < ba2int(other)
        return NotImplemented

    def __le__(self: Self, other: "pybitarray") -> bool:
        """Less than or equal comparison."""
        if isinstance(other, pybitarray):
            return ba2int(self) <= ba2int(other)
        return NotImplemented

    def __gt__(self: Self, other: "pybitarray") -> bool:
        """Greater than comparison."""
        if isinstance(other, pybitarray):
            return ba2int(self) > ba2int(other)
        return NotImplemented

    def __ge__(self: Self, other: "pybitarray") -> bool:
        """Greater than or equal comparison."""
        if isinstance(other, pybitarray):
            return ba2int(self) >= ba2int(other)
        return NotImplemented

    def tobytes(self: Self) -> bytes:
        """Convert bitarray to bytes.

        Returns:
        -------
            bytes representation of the bitarray

        """
        # Pad to multiple of 8 bits
        bits = self._bits[:]
        while len(bits) % 8 != 0:
            bits.append(0)

        result = bytearray()
        for i in range(0, len(bits), 8):
            byte_bits = bits[i : i + 8]
            if self._endian == "little":
                # Little endian: LSB first in each byte
                byte_val = sum(bit << j for j, bit in enumerate(byte_bits))
            else:
                # Big endian: MSB first in each byte
                byte_val = sum(bit << (7 - j) for j, bit in enumerate(byte_bits))
            result.append(byte_val)

        return bytes(result)

    def __repr__(self: Self) -> str:
        """Return string representation."""
        bits_str = "".join(str(b) for b in self._bits)
        return f"pybitarray('{bits_str}', endian='{self._endian}')"

    def __str__(self: Self) -> str:
        """Return string representation of bits."""
        return "".join(str(b) for b in self._bits)


def _int_to_bits(value: int, length: int, endian: Literal["little", "big"]) -> list[int]:
    """Convert an integer to a list of bits.

    Args:
    ----
        value: integer value to convert
        length: number of bits
        endian: "little" or "big"

    Returns:
    -------
        list of bits (0s and 1s)

    """
    # Handle negative values by masking to unsigned
    if value < 0:
        value = value & ((1 << length) - 1)

    bits = []
    for _ in range(length):
        bits.append(value & 1)
        value >>= 1

    if endian == "big":
        bits.reverse()

    return bits


def int2ba(
    value: int,
    length: int = 8,
    endian: Literal["little", "big"] = "little",
) -> pybitarray:
    """Convert an integer to a pybitarray.

    Args:
    ----
        value: integer value to convert
        length: number of bits in result
        endian: "little" or "big" endianness

    Returns:
    -------
        pybitarray representing the value

    """
    return pybitarray(value, length=length, endian=endian)


def ba2int(ba: pybitarray) -> int:
    """Convert a pybitarray to an integer.

    Args:
    ----
        ba: pybitarray to convert

    Returns:
    -------
        integer value

    """
    bits = ba._bits  # noqa: SLF001
    endian = ba._endian  # noqa: SLF001

    result = 0
    if endian == "little":
        # Little endian: bit 0 is LSB
        for i, bit in enumerate(bits):
            result |= bit << i
    else:
        # Big endian: bit 0 is MSB
        for i, bit in enumerate(bits):
            result |= bit << (len(bits) - 1 - i)

    return result
