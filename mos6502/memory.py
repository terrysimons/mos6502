#!/usr/bin/env python3
"""mos6502 Memory."""
import logging
from collections.abc import MutableSequence
from typing import Literal, Self

import bitarray
from bitarray.util import ba2int, int2ba

from mos6502 import exceptions

ENDIANNESS: Literal["little"] = "little"

# TODO:
#
# Wrap memory sections with a class so we can do interesting things with __str__
# class MemoryBytes:
#     def __str__

# class ZeroPage:
#     pass

# class Stack:
#     pass

# class Heap:
#     pass


class MemoryUnit:
    """An base class for dealing with Bytes and Words."""

    log: logging.Logger = logging.getLogger("mos6502.memory")

    def __init__(self: Self, value: int | bitarray.bitarray = 0,
                 endianness: str = ENDIANNESS) -> None:
        """
        Initialize a MemoryUnit.

        Arguments:
        ---------
            value: the value to store in the memory unit (default: 0)
            endianness: the endianness of this memory unit (default: mos6502.memory.ENDIANNESS)
        """
        super().__init__()
        self._overflow: bool = False
        self._underflow: bool = False

        if isinstance(value, type(self)):
            self._value = value._value  # noqa: SLF001
        elif isinstance(value, bitarray.bitarray):
            self._value = value
        else:
            self._value: bitarray.bitarray = int2ba(value, length=self.size_bits, endian=endianness)

    @property
    def size_bits(self: Self) -> Literal[0]:
        """Return the size of bits of this MemoryUnit."""
        return 0

    @property
    def endianness(self: Self) -> str:
        """Return endianness of the architecture - "big" or "little" (default=little)."""
        return self._value.endian

    @property
    def value(self: Self) -> int:
        """Return value of the MemoryUnit as an integer."""
        return ba2int(self._value)

    @property
    def overflow(self: Self) -> bool:
        """Return True if a MemoryUnit + <int|MemoryUnit> overflow occurred on addition."""
        return self._overflow

    @overflow.setter
    def overflow(self: Self, overflow: bool) -> None:
        """Set overflow status."""
        self._overflow = overflow

    @property
    def underflow(self: Self) -> bool:
        """Return True if a MemoryUnit - <int|MemoryUnit> overflow occurred on subtraction."""
        return self._underflow

    @underflow.setter
    def underflow(self: Self, underflow: bool) -> None:
        """Set underflow status."""
        self._underflow = underflow

    def bits(self: Self) -> bitarray.bitarray:
        """Return a bitarray.bitarray of size self.size_bits with endianness self.endianness."""
        return int2ba(self.value, length=self.size_bits, endian=self.endianness)

    @property
    def lowbyte(self: Self) -> bitarray.bitarray:
        """Return the low byte as an int."""
        if self.size_bits >= 8:
            return ba2int(self.bits()[0:8])

        return ba2int(self.bits())

    @property
    def lowbyte_bits(self: Self) -> bitarray.bitarray:
        """Return the low byte of this data type as a bitarray.bitarray or None."""
        if self.size_bits >= 8:
            return self.bits()[0:8]

        return self.bits()

    @property
    def highbyte(self: Self) -> bitarray.bitarray:
        """Return the high byte as an int."""
        if self.size_bits > 8:
            return ba2int(self.bits()[8:])

        return None

    @property
    def highbyte_bits(self: Self) -> bitarray.bitarray:
        """Return the high byte of this data type as a bitarray.bitarray or None."""
        if self.size_bits > 8:
            return self.bits()[8:]

        return None

    """ Math Operators"""
    def __add__(self: Self, rvalue: int | bitarray.bitarray) -> bitarray.bitarray:
        """Add an integer or bitarray to a MemoryUnit."""
        result: MemoryUnit = None

        local_rvalue = rvalue
        self.log.debug(f"Adding {rvalue} to {self._value}")

        # MemoryUnit is the base class for Byte/Word so this
        # gives us a bit of a speedup
        if isinstance(rvalue, MemoryUnit):
            local_rvalue: int = rvalue.value
        elif isinstance(rvalue, bitarray.bitarray):
            local_rvalue: int = ba2int(local_rvalue)

        # If we're adding data to a word and it causes a carry
        # we need to account for the CPU cycles.
        #
        # This gives us slightly better emulator behavior and
        # cleaner code overall since it means we don't have to
        # account for it arbitrarily in each relevant instruction
        self.value + local_rvalue
        initial_msb: bitarray.bitarray = self.highbyte_bits
        if isinstance(self, Word):
            result: Word = Word(self.value + local_rvalue, endianness=self.endianness)

            result_msb: bitarray.bitarray = result.highbyte_bits

            if result_msb > initial_msb:
                result.underflow = False
                result.overflow = True
            elif result_msb < initial_msb:
                result.overflow = False
                result.underflow = True
            else:
                result.overflow = False
                result.underflow = False

        if isinstance(self, Byte):
            try:
                result: Byte = Byte(self.value + local_rvalue, endianness=self.endianness)
            except OverflowError:
                # TODO: Set the carry bit
                result: Word = Word(self.value + local_rvalue, endianness=self.endianness)
                result: Byte = Byte(ba2int(result.lowbyte_bits), endianness=self.endianness)

        return result

        # if isinstance(rvalue, type(self)):
        #     return type(self)(
        #             self.value + rvalue.value,
        #         ),
        # elif isinstance()

        # return int2ba(

    def __sub__(self: Self, rvalue: int | bitarray.bitarray) -> bitarray.bitarray:
        """Subtract an integer or bitarray from a MemoryUnit."""
        if isinstance(rvalue, type(self)):
            return type(self)(
                value=int2ba(
                    ba2int(self.value) - ba2int(rvalue.value),
                ),
                endianness=self.endianness,
            )

        return int2ba(
            ba2int(self.value) - rvalue,
            endian=self.endianness,
        )

    """ Bitwise Operators """
    def __or__(self: Self, rvalue: int | bitarray.bitarray) -> int:
        """Bitwise-OR this MemoryUnit with Byte|Word, bitarray, or int types."""
        # bitarrays are a little bit tricky to work with
        # so we're using a super safe option here.
        if isinstance(rvalue, Byte | Word):
            self.log.critical("Byte or Word")
        elif isinstance(rvalue, bitarray.bitarray):
            self.log.critical("Bitarray")
        elif isinstance(rvalue, int):
            self.log.critical("Int")
        return int.from_bytes(self._value.tobytes(), byteorder=self.endianness) | \
            int.from_bytes(rvalue.tobytes(), byteorder=self.endianness)

    def __and__(self: Self, rvalue: int | bitarray.bitarray) -> int:
        """Bitwise-AND this MemoryUnit with Byte|Word, bitarray, or int types."""
        # bitarrays are a little bit tricky to work with
        # so we're using a super safe option here.

        try:
            int_lvalue: int = self.value
            if isinstance(rvalue, Byte | Word):
                int_rvalue = rvalue.value
            elif isinstance(rvalue, bitarray.bitarray):
                int_rvalue: int = int.from_bytes(rvalue.tobytes(), byteorder=self.endianness)
            elif isinstance(rvalue, int):
                int_rvalue = rvalue
        except Exception:
            raise
        else:
            return int_lvalue & int_rvalue

    def __lshift__(self: Self, rvalue: int | bitarray.bitarray) -> bitarray.bitarray:
        """
        Left-shift rvalue bits.

        Returns: bitarray.bitarray
        """
        return self._value << rvalue

    def __rshift__(self: Self, rvalue: int | bitarray.bitarray) -> bitarray.bitarray:
        """
        Right-shift rvalue bits.

        Returns: bitarray.bitarray
        """
        return self._value >> rvalue

    """ Equality Operators """
    def __lt__(self: Self, value: int | bitarray.bitarray) -> bool:
        """Less than comparison with MemoryUnit."""
        if isinstance(value, bitarray.bitarray):
            return self._value < value

        return self.value < value

    def __gt__(self: Self, value: int | bitarray.bitarray) -> bool:
        """Greater than comparison with MemoryUnit."""
        if isinstance(value, bitarray.bitarray):
            return self._value > value

        return self.value > value

    def __eq__(self: Self, value: int | bitarray.bitarray) -> bool:
        """Equality comparison with MemoryUnit."""
        if isinstance(value, bitarray.bitarray):
            return self._value == value

        return self.value == value

    def __le__(self: Self, value: int | bitarray.bitarray) -> bool:
        """Less than or equal to comparison with MemoryUnit."""
        if isinstance(value, bitarray.bitarray):
            return self._value <= value

        return self.value <= value

    def __ge__(self: Self, value: int | bitarray.bitarray) -> bool:
        """Greater than or equal to comparison with MemoryUnit."""
        if isinstance(value, bitarray.bitarray):
            return self._value >= value

        return self.value >= value

    def __int__(self: Self) -> int:
        """Return this MemoryUnit's value as an integer."""
        return self.value

    def __format__(self: Self, specifier: str) -> str:
        """Return this MemoryUnit as indicated by the format specifier."""
        return f"{self.value:{specifier}}"

    def __repr__(self: Self) -> str:
        """Describe this MemoryUnit in code."""
        return str(
            f"{self.__class__.__name__}("
            f"value={self.value:#02x}, "
            f"size_bits={self.size_bits}, "
            f"endianness={self.endianness}"
            ")",
        )

    def __str__(self: Self) -> str:
        """Describe this MemoryUnit as a hexadecimal value."""
        if isinstance(self.value, bitarray.bitarray):
            return str(hex(ba2int(self.value)))
        else:  # noqa: RET505 (We do some shenanigans)
            return str(hex(self.value))

    """ Index Operators """
    def __index__(self: Self) -> int:
        """Describe this MemoryUnit as an index."""
        return self.value

    def __getitem__(self: Self, index: int) -> bitarray.bitarray:
        """
        Return the specified bit if used as an index.

        Returns: bitarray.bitarray
        """
        if len(self.bits()) >= index:
            return self.bits()[index]

        return self.bits()

    def __delitem__(self: Self, index: int) -> None:
        """Not implemented."""

    def __setitem__(self: Self, index: int, value: int) -> None:
        """Set a bit on this MemoryUnit."""
        if isinstance(value, int):
            self._value[index] = value
        else:
            self._value[index] = value._value[index]  # noqa: SLF001


class Byte(MemoryUnit):
    """Byte MemoryUnit()."""

    log: logging.Logger = logging.getLogger("mos6502.memory.Byte")

    def __init__(self: Self, value: int = 0, endianness: str = ENDIANNESS) -> None:
        """
        Initialize a Byte().

        Arguments:
        ---------
            value: a value between -127 and 255
            endianness: 'big' or 'little' (default: mos6502.memory.ENDIANNESS)
        """
        super().__init__(value=value, endianness=endianness)

    @property
    def size_bits(self: Self) -> Literal[8]:
        """Return the size in bits of this MemoryUnit (8 for Byte())."""
        return 8


class Word(MemoryUnit):
    """Word MemoryUnit()."""

    log: logging.Logger = logging.getLogger("mos6502.memory.Word")

    def __init__(self: Self, value: int = 0, endianness: str = ENDIANNESS) -> None:
        """
        Initialize a Word().

        Arguments:
        ---------
            value: a value between -32767 and 65535
            endianness: 'big' or 'little' (default: mos6502.memory.ENDIANNESS)
        """
        super().__init__(value=value, endianness=endianness)

    @property
    def size_bits(self: Self) -> Literal[16]:
        """Return the size in bits of this MemoryUnit (16 for Word())."""
        return 16


class RAM(MutableSequence):
    """mos6502 RAM (64KB; 256 byte zeropage, 256 byte stack, 65023 heap)."""

    log: logging.Logger = logging.getLogger("mos6502.memory.RAM")

    def __init__(self: Self, endianness: str = ENDIANNESS, save_state: list[list] = None) -> None:
        """Instantiate a mos6502 RAM bank."""
        super().__init__()
        self.zeropage = []
        self.stack = []
        self.heap = []
        self.endianness: str = endianness
        self.initialize()

    def initialize(self: Self) -> None:
        """Initialize the zeropage, stack, and heap to 0x00."""
        self.zeropage: list[Byte] = [
            Byte(endianness=self.endianness),
        ] * 256
        self.stack: list[Byte] = [
            Byte(endianness=self.endianness),
        ] * 256
        self.heap: list[Byte] = [
            Byte(endianness=self.endianness),
        ] * (0x10000 - len(self.zeropage) - len(self.stack))

    def __repr__(self: Self) -> str:
        """Return the code representation of the RAM."""
        ram: list[Byte] = self.zeropage
        ram.extend(self.stack)
        ram.extend(self.heap)
        return f"<{self.__class__.__name__} {ram}>"

    def __len__(self: Self) -> int:
        """Return the length of the RAM."""
        return len(self.zeropage) + len(self.stack) + len(self.heap)

    def __getitem__(self: Self, index: int) -> int:
        """Get the RAM item at index {index}."""
        if index >= 0 and index < 256:
            return self.zeropage[index].value
        if index >= 256 and index < 512:
            return self.stack[index - 256].value
        if index <= 65535:
            return self.heap[index - 512].value

        raise exceptions.InvalidMemoryLocationError(
            f"Invalid memory location: {index} should be between 0 and "
            f"{len(self.zeropage) + len(self.stack) + len(self.heap) - 1}",
        )

    def __delitem__(self: Self, index: int) -> None:
        """Not implemented."""

    def __setitem__(self: Self, index: int, value: int, length: int = 8) -> None:
        """Set the RAM item at index {index} to value {value}."""
        data_type: type[Byte] = Byte

        if length == 16:
            data_type: type[Word] = Word

        try:
            if index >= 0 and index < 256:
                self.zeropage[index] = Byte(
                    value=int2ba(value, length=length, endian=self.endianness),
                    endianness=self.endianness,
                )

            elif index >= 256 and index < 512:
                self.stack[index - 256] = data_type(
                    value=int2ba(value, length=length, endian=self.endianness),
                    endianness=self.endianness,
                )
            elif index <= 65535:
                self.heap[index - 512] = data_type(
                    value=int2ba(value, length=length, endian=self.endianness),
                    endianness=self.endianness,
                )
            else:
                raise exceptions.InvalidMemoryLocationError(  # noqa: TRY301
                    f"Invalid memory location: {index} should be between 0 and "
                    f"{len(self.zeropage) + len(self.stack) + len(self.heap) - 1}",
                )
        except OverflowError:
            self.__setitem__(index=index, value=value, length=length + 8)

    def insert(self: Self, index: int, value: int) -> None:
        """Not implemented."""

    def append(self: Self, value: int) -> None:
        """Not implemented."""

    def memory_section(self: Self, address: int) -> Literal["zeropage", "stack", "heap"]:
        """Return the name of the memory section at location {address}."""
        # ZEROPAGE

        # STACK

        # HEAP

        if address >= 0 and address < 256:
            return "zeropage"
        if address >= 256 and address < 512:
            return "stack"
        if address >= 512 and address <= 0xFFFF:
            return "heap"

        raise exceptions.InvalidMemoryLocationError(
            f"Invalid memory location: {address} should be between 0 and "
            f"{len(self.zeropage) + len(self.stack) + len(self.heap) - 1}",
        )

    def fill(self: Self, data: Byte) -> None:
        """Fill the RAM with {data}."""
        for i in range(len(self)):
            self.write(i, data)

    def read(self: Self, address: Word, size: int = 1) -> list[Byte]:
        """Read size Bytes starting from Word(address)."""
        return [self[address + offset] for offset in range(address, address + size)]

    def write(self: Self, address: Word, data: int) -> None:
        """Write Word(data) to Word(address)."""
        zero_page_start_address: int = 0
        # STACK
        stack_start_address: int = 256
        # HEAP
        ram_start_address: int = 512

        if (data < -127) or (data > 255):
            raise exceptions.InvalidMemoryAssignmentError(
                f"Data must be written one byte at a time, but got data > 1 byte: {data}",
            )

        if address >= zero_page_start_address and address < 256:
            self.zeropage[address] = data
        elif address >= stack_start_address and address < 512:
            self.stack[address - 256] = data
        elif address >= ram_start_address and address <= 0xFFFF:
            self.heap[address - 512] = data
