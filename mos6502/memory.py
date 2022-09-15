#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""most6502 Memory."""
from collections.abc import MutableSequence
import logging

import bitarray
from bitarray.util import ba2int, int2ba

from mos6502.exceptions import InvalidMemoryAssignmentException, InvalidMemoryLocationException

ENDIANNESS = 'little'


class MemoryUnit:
    """An base class for dealing with Bytes and Words."""

    log: logging.Logger = logging.getLogger('mos6502.memory')

    def __init__(self, value=0, endianness=ENDIANNESS) -> None:
        """Initialize a MemoryUnit.

        Arguments:
            value: the value to store in the memory unit (default: 0)
            endianness: the endianness of this memory unit (default: mos6502.memory.ENDIANNESS)
        """
        super().__init__()
        self._overflow: bool = False
        self._underflow: bool = False

        if isinstance(value, type(self)):
            self._value = value._value
        elif isinstance(value, bitarray.bitarray):
            self._value = value
        else:
            self._value: bitarray.bitarray = int2ba(value, length=self.size_bits, endian=endianness)

    @property
    def size_bits(self):
        """Return the size of bits of this MemoryUnit."""
        return 0

    @property
    def endianness(self) -> str:
        """Return endianness of the architecture - "big" or "little" (default=little)."""
        return self._value.endian()

    @property
    def value(self) -> int:
        """Return value of the MemoryUnit as an integer."""
        return ba2int(self._value)

    @property
    def overflow(self) -> bool:
        """Return True if a MemoryUnit + <int|MemoryUnit> overflow occurred on addition."""
        return self._overflow

    @overflow.setter
    def overflow(self, overflow):
        """Set overflow status."""
        self._overflow = overflow

    @property
    def underflow(self):
        """Return True if a MemoryUnit - <int|MemoryUnit> overflow occurred on subtraction."""
        return self._underflow

    @overflow.setter
    def underflow(self, underflow):
        """Set underflow status."""
        self._underflow = underflow

    def bits(self) -> bitarray.bitarray:
        """Return a bitarray.bitarray of size self.size_bits with endianness self.endianness."""
        return int2ba(self.value, length=self.size_bits, endian=self.endianness)

    @property
    def lowbyte(self) -> bitarray.bitarray:
        """Return the low byte as an int."""
        if self.size_bits >= 8:
            return ba2int(self.bits()[0:8])

        return ba2int(self.bits())

    @property
    def lowbyte_bits(self) -> bitarray.bitarray:
        """Return the low byte of this data type as a bitarray.bitarray or None."""
        if self.size_bits >= 8:
            return self.bits()[0:8]

        return self.bits()

    @property
    def highbyte(self) -> bitarray.bitarray:
        """Return the high byte as an int."""
        if self.size_bits > 8:
            return ba2int(self.bits()[8:])

        return None

    @property
    def highbyte_bits(self) -> bitarray.bitarray:
        """Return the high byte of this data type as a bitarray.bitarray or None."""
        if self.size_bits > 8:
            return self.bits()[8:]

        return None

    ''' Math Operators'''
    def __add__(self, rvalue) -> bitarray.bitarray:
        """Add an integer or bitarray to a MemoryUnit."""
        result: MemoryUnit = None

        local_rvalue = rvalue
        self.log.debug(f'Adding {rvalue} to {self._value}')

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
        initial_lsb: bitarray.bitarray = self.lowbyte_bits
        initial_msb: bitarray.bitarray = self.highbyte_bits
        if isinstance(self, Word):
            result: Word = Word(self.value + local_rvalue, endianness=self.endianness)

            result_lsb: bitarray.bitarray = result.lowbyte_bits
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
        #         value=int2ba(
        #             self.value + rvalue.value,
        #             endian=self.endianness
        #         ),
        #         endianness=self.endianness
        #     )
        # elif isinstance()

        # return int2ba(
        #     ba2int(self.value) + rvalue,
        #     endian=ENDIANNESS
        # )

    def __sub__(self, rvalue) -> bitarray.bitarray:
        """Subtract an integer or bitarray from a MemoryUnit."""
        if isinstance(rvalue, type(self)):
            return type(self)(
                value=int2ba(
                    ba2int(self.value) - ba2int(rvalue.value),
                ),
                endianness=self.endianness
            )

        return int2ba(
            ba2int(self.value) - rvalue,
            endian=self.endianness
        )

    ''' Bitwise Operators '''
    def __or__(self, rvalue):
        """Bitwise-OR this MemoryUnit with Byte|Word, bitarray, or int types."""
        # bitarrays are a little bit tricky to work with
        # so we're using a super safe option here.
        if isinstance(rvalue, Byte) or isinstance(rvalue, Word):
            self.log.critical("Byte or Word")
        elif isinstance(rvalue, bitarray.bitarray):
            self.log.critical("Bitarray")
        elif isinstance(rvalue, int):
            self.log.critical("Int")
        return int.from_bytes(self._value.tobytes(), byteorder=self.endianness) | \
            int.from_bytes(rvalue.tobytes(), byteorder=self.endianness)

    def __and__(self, rvalue):
        """Bitwise-AND this MemoryUnit with Byte|Word, bitarray, or int types."""
        # bitarrays are a little bit tricky to work with
        # so we're using a super safe option here.

        try:
            int_lvalue = self.value
            if isinstance(rvalue, Byte) or isinstance(rvalue, Word):
                int_rvalue = rvalue.value
            elif isinstance(rvalue, bitarray.bitarray):
                int_rvalue: int = int.from_bytes(rvalue.tobytes(), byteorder=self.endianness)
            elif isinstance(rvalue, int):
                int_rvalue = rvalue
            return int_lvalue & int_rvalue
        except Exception as e:
            raise e

    def __lshift__(self, rvalue):
        """Left-shift rvalue bits."""
        return self._value << rvalue

    def __rshift__(self, rvalue):
        """Right-shift rvalue bits."""
        return self._value >> rvalue

    ''' Equality Operators '''
    def __lt__(self, value) -> bool:
        """Less than comparison with MemoryUnit."""
        if isinstance(value, bitarray.bitarray):
            return self._value < value

        return self.value < value

    def __gt__(self, value) -> bool:
        """Greater than comparison with MemoryUnit."""
        if isinstance(value, bitarray.bitarray):
            return self._value > value

        return self.value > value

    def __eq__(self, value) -> bool:
        """Equality comparison with MemoryUnit."""
        if isinstance(value, bitarray.bitarray):
            return self._value == value

        return self.value == value

    def __le__(self, value) -> bool:
        """Less than or equal to comparison with MemoryUnit."""
        if isinstance(value, bitarray.bitarray):
            return self._value <= value

        return self.value <= value

    def __ge__(self, value) -> bool:
        """Greater than or equal to comparison with MemoryUnit."""
        if isinstance(value, bitarray.bitarray):
            return self._value >= value

        return self.value >= value

    def __int__(self) -> int:
        """Return this MemoryUnit's value as an integer."""
        return self.value

    def __format__(self, specifier):
        """Return this MemoryUnit as indicated by the format specifier."""
        return f'{self.value:{specifier}}'

    def __repr__(self):
        """Describe this MemoryUnit in code."""
        return str(
            f'{self.__class__.__name__}('
            f'value={self.value:#02x}, '
            f'size_bits={self.size_bits}, '
            f'endianness={self.endianness}'
            ')'
        )

    def __str__(self):
        """Describe this MemoryUnit as a hexadecimal value."""
        if isinstance(self.value, bitarray.bitarray):
            return str(hex(ba2int(self.value)))
        else:
            return str(hex(self.value))

    ''' Index Operators '''
    def __index__(self):
        """Describe this MemoryUnit as an index."""
        return self.value

    def __getitem__(self, index):
        """Return the specified bit if used as an index."""
        if len(self.bits()) >= index:
            return self.bits()[index]

        return self.bits()

    def __delitem__(self, index):
        """Not implemented."""
        pass

    def __setitem__(self, index, value):
        """Set a bit on this MemoryUnit."""
        if isinstance(value, int):
            self._value[index] = value
        else:
            self._value[index] = value._value[index]


class Byte(MemoryUnit):
    """Byte MemoryUnit()."""

    log: logging.Logger = logging.getLogger('mos6502.memory.Byte')

    def __init__(self, value=0, endianness=ENDIANNESS) -> None:
        """
        Initialize a Byte().

        Arguments:
            value: a value between -127 and 255
            endianness: 'big' or 'little' (default: mos6502.memory.ENDIANNESS)
        """
        super().__init__(value=value, endianness=endianness)

    @property
    def size_bits(self):
        """Return the size in bits of this MemoryUnit (8 for Byte())."""
        return 8


class Word(MemoryUnit):
    """Word MemoryUnit()."""

    log: logging.Logger = logging.getLogger('mos6502.memory.Word')

    def __init__(self, value=0, endianness=ENDIANNESS):
        """
        Initialize a Word().

        Arguments:
            value: a value between -32767 and 65535
            endianness: 'big' or 'little' (default: mos6502.memory.ENDIANNESS)
        """
        super().__init__(value=value, endianness=endianness)

    @property
    def size_bits(self):
        """Return the size in bits of this MemoryUnit (16 for Word())."""
        return 16


class RAM(MutableSequence):
    """mos6502 RAM (64KB; 256 byte zeropage, 256 byte stack, 65023 heap)."""

    log: logging.Logger = logging.getLogger('mos6502.memory.RAM')

    def __init__(self, endianness=ENDIANNESS, save_state=None) -> None:
        """Instantiate a mos6502 RAM bank."""
        super().__init__()
        self.zeropage = None
        self.stack = None
        self.heap = None
        self.endianness: str = endianness
        self.initialize()

    def initialize(self) -> None:
        """Initialize the zeropage, stack, and heap to 0x00."""
        self.zeropage: list[Byte] = [
            Byte(endianness=self.endianness)
        ] * 256
        self.stack: list[Byte] = [
            Byte(endianness=self.endianness)
        ] * 256
        self.heap: list[Byte] = [
            Byte(endianness=self.endianness)
        ] * (0x10000 - len(self.zeropage) - len(self.stack))

    def __repr__(self) -> str:
        """Return the code representation of the RAM."""
        ram: list[Byte] = self.zeropage
        ram.extend(self.stack)
        ram.extend(self.heap)
        return f"<{self.__class__.__name__} {ram}>"

    def __len__(self) -> int:
        """Return the length of the RAM."""
        return len(self.zeropage) + len(self.stack) + len(self.heap)

    def __getitem__(self, index) -> int:
        """Get the RAM item at index {index}."""
        if index >= 0 and index < 256:
            return self.zeropage[index].value
        elif index >= 256 and index < 512:
            return self.stack[index - 256].value
        elif index <= 65535:
            return self.heap[index - 512].value
        else:
            raise InvalidMemoryLocationException(
                f'Invalid memory location: {index} should be between 0 and '
                f'{len(self.zeropage) + len(self.stack) + len(self.heap) - 1}'
            )

    def __delitem__(self, index) -> None:
        """Not implemented."""
        pass

    def __setitem__(self, index, value, length=8) -> None:
        """Set the RAM item at index {index} to value {value}."""
        data_type: Type[Byte] = Byte

        if length == 16:
            data_type: Type[Word] = Word

        try:
            if index >= 0 and index < 256:
                self.zeropage[index] = Byte(
                    value=int2ba(value, length=length, endian=self.endianness),
                    endianness=self.endianness
                )

            elif index >= 256 and index < 512:
                self.stack[index - 256] = data_type(
                    value=int2ba(value, length=length, endian=self.endianness),
                    endianness=self.endianness
                )
            elif index <= 65535:
                self.heap[index - 512] = data_type(
                    value=int2ba(value, length=length, endian=self.endianness),
                    endianness=self.endianness
                )
            else:
                raise InvalidMemoryLocationException(
                    f'Invalid memory location: {index} should be between 0 and '
                    f'{len(self.zeropage) + len(self.stack) + len(self.heap) - 1}'
                )
        except OverflowError:
            self.__setitem__(index=index, value=value, length=length + 8)

    # def __str__(self):
    #     return str(self._list)

    def insert(self, index, value):
        """Not implemented."""
        pass

    def append(self, value):
        """Not implemented."""
        pass

    def memory_section(self, address):
        """Return the name of the memory section at location {address}."""
        # ZEROPAGE
        zero_page_start_address: int = 0

        # STACK
        stack_start_address: int = 256

        # HEAP
        ram_start_address: int = 512

        if address >= 0 and address < 256:
            return 'zeropage'
        elif address >= 256 and address < 512:
            return 'stack'
        elif address >= 512 and address <= 0xFFFF:
            return 'heap'
        else:
            raise InvalidMemoryLocationException(
                f'Invalid memory location: {address} should be between 0 and '
                f'{len(self.zeropage) + len(self.stack) + len(self.heap) - 1}'
            )

    def fill(self, data: Byte):
        """Fill the RAM with {data}."""
        for i in range(len(self)):
            self.write(i, data)

    def read(self, address: Word, size=1) -> list[Byte]:
        """Read size Bytes starting from Word(address)."""
        return [self[address + offset] for offset in range(address, address + size)]

    def write(self, address: Word, data: int) -> None:
        """Write Word(data) to Word(address)."""
        zero_page_start_address: int = 0
        # STACK
        stack_start_address: int = 256
        # HEAP
        ram_start_address: int = 512

        if (data < -127) or (data > 255):
            raise InvalidMemoryAssignmentException(
                f'Data must be written one byte at a time, but got data > 1 byte: {data}'
            )

        if address >= zero_page_start_address and address < 256:
            self.zeropage[address] = data
        elif address >= stack_start_address and address < 512:
            self.stack[address - 256] = data
        elif address >= ram_start_address and address <= 0xFFFF:
            self.heap[address - 512] = data
