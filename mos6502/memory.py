#!/usr/bin/env python3
"""mos6502 Memory.

Performance optimization: MemoryUnit stores values as plain ints, not bitarrays.
Bitarray conversion only happens when explicitly needed for bit operations.
"""
import logging
from collections.abc import MutableSequence
from typing import Literal, Self

from mos6502.bitarray_factory import ba2int, bitarray, int2ba, is_bitarray

from mos6502 import errors

ENDIANNESS: Literal["little"] = "little"


class MemoryUnit:
    """A base class for dealing with Bytes and Words.

    Performance optimization: Values stored as plain ints internally.
    Bitarray conversion only happens when needed for bit operations.
    """

    log: logging.Logger = logging.getLogger("mos6502.memory")

    # Use __slots__ for memory efficiency
    __slots__ = ('_value', '_endianness', '_overflow', '_underflow')

    def __init__(self: Self, value: int | bitarray = 0,
                 endianness: str = ENDIANNESS) -> None:
        """Initialize a MemoryUnit.

        Arguments:
        ---------
            value: the value to store in the memory unit (default: 0)
            endianness: the endianness of this memory unit (default: mos6502.memory.ENDIANNESS)
        """
        self._overflow: bool = False
        self._underflow: bool = False
        self._endianness: str = endianness

        # Store as int internally for performance
        if isinstance(value, type(self)):
            self._value: int = value._value  # noqa: SLF001
        elif is_bitarray(value):
            self._value: int = ba2int(value)
        elif isinstance(value, MemoryUnit):
            self._value: int = value._value  # noqa: SLF001
        else:
            self._value: int = int(value) & self._mask

    @property
    def _mask(self: Self) -> int:
        """Return the bit mask for this MemoryUnit type."""
        return (1 << self.size_bits) - 1 if self.size_bits > 0 else 0

    @property
    def size_bits(self: Self) -> Literal[0]:
        """Return the size of bits of this MemoryUnit."""
        return 0

    @property
    def endianness(self: Self) -> str:
        """Return endianness of the architecture - "big" or "little" (default=little)."""
        return self._endianness

    @property
    def value(self: Self) -> int:
        """Return value of the MemoryUnit as an integer."""
        return self._value

    @value.setter
    def value(self: Self, new_value: int) -> None:
        """Set the value of the MemoryUnit."""
        self._value = int(new_value) & self._mask

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

    def bits(self: Self) -> bitarray:
        """Return a bitarray of size self.size_bits with endianness self.endianness."""
        return int2ba(self._value, length=self.size_bits, endian=self._endianness)

    @property
    def lowbyte(self: Self) -> int:
        """Return the low byte as an int."""
        return self._value & 0xFF

    @property
    def lowbyte_bits(self: Self) -> bitarray:
        """Return the low byte of this data type as a bitarray."""
        return int2ba(self._value & 0xFF, length=8, endian=self._endianness)

    @property
    def highbyte(self: Self) -> int | None:
        """Return the high byte as an int."""
        if self.size_bits > 8:
            return (self._value >> 8) & 0xFF
        return None

    @property
    def highbyte_bits(self: Self) -> bitarray | None:
        """Return the high byte of this data type as a bitarray or None."""
        if self.size_bits > 8:
            return int2ba((self._value >> 8) & 0xFF, length=8, endian=self._endianness)
        return None

    """ Math Operators"""
    def __add__(self: Self, rvalue: int | bitarray) -> "MemoryUnit":
        """Add an integer or bitarray to a MemoryUnit."""
        # Get int value from rvalue
        if isinstance(rvalue, int):
            if rvalue == 0:
                return type(self)(self._value, endianness=self._endianness)
            local_rvalue = rvalue
        elif isinstance(rvalue, MemoryUnit):
            if rvalue._value == 0:  # noqa: SLF001
                return type(self)(self._value, endianness=self._endianness)
            local_rvalue = rvalue._value  # noqa: SLF001
        elif is_bitarray(rvalue):
            local_rvalue = ba2int(rvalue)
            if local_rvalue == 0:
                return type(self)(self._value, endianness=self._endianness)
        else:
            local_rvalue = int(rvalue)

        result: MemoryUnit = None

        # Track overflow/underflow for Words
        if isinstance(self, Word):
            initial_msb = (self._value >> 8) & 0xFF
            new_value = (self._value + local_rvalue) & 0xFFFF
            result = Word(new_value, endianness=self._endianness)
            result_msb = (new_value >> 8) & 0xFF

            if result_msb > initial_msb:
                result.underflow = False
                result.overflow = True
            elif result_msb < initial_msb:
                result.overflow = False
                result.underflow = True
            else:
                result.overflow = False
                result.underflow = False

        elif isinstance(self, Byte):
            new_value = (self._value + local_rvalue) & 0xFF
            result = Byte(new_value, endianness=self._endianness)

        return result

    def __sub__(self: Self, rvalue: int | bitarray) -> "MemoryUnit":
        """Subtract an integer or bitarray from a MemoryUnit."""
        # Get int value from rvalue
        if isinstance(rvalue, int):
            if rvalue == 0:
                return type(self)(self._value, endianness=self._endianness)
            local_rvalue = rvalue
        elif isinstance(rvalue, MemoryUnit):
            if rvalue._value == 0:  # noqa: SLF001
                return type(self)(self._value, endianness=self._endianness)
            local_rvalue = rvalue._value  # noqa: SLF001
        elif is_bitarray(rvalue):
            local_rvalue = ba2int(rvalue)
            if local_rvalue == 0:
                return type(self)(self._value, endianness=self._endianness)
        else:
            local_rvalue = int(rvalue)

        new_value = (self._value - local_rvalue) & self._mask
        return type(self)(new_value, endianness=self._endianness)

    """ Bitwise Operators """
    def __or__(self: Self, rvalue: int | bitarray) -> int:
        """Bitwise-OR this MemoryUnit with Byte|Word, bitarray, or int types."""
        if isinstance(rvalue, MemoryUnit):
            return self._value | rvalue._value  # noqa: SLF001
        elif is_bitarray(rvalue):
            return self._value | ba2int(rvalue)
        elif isinstance(rvalue, int):
            return self._value | rvalue
        else:
            raise TypeError(f"Cannot perform bitwise OR on types {type(self)} and {type(rvalue)}")

    def __and__(self: Self, rvalue: int | bitarray) -> int:
        """Bitwise-AND this MemoryUnit with Byte|Word, bitarray, or int types."""
        if isinstance(rvalue, MemoryUnit):
            return self._value & rvalue._value  # noqa: SLF001
        elif is_bitarray(rvalue):
            return self._value & ba2int(rvalue)
        elif isinstance(rvalue, int):
            return self._value & rvalue
        else:
            raise TypeError(f"Cannot perform bitwise AND on types {type(self)} and {type(rvalue)}")

    def __lshift__(self: Self, rvalue: int) -> int:
        """Left-shift by rvalue bits. Returns int."""
        return self._value << rvalue

    def __rshift__(self: Self, rvalue: int) -> int:
        """Right-shift by rvalue bits. Returns int."""
        return self._value >> rvalue

    """ Equality Operators """
    def __lt__(self: Self, value: int | bitarray) -> bool:
        """Less than comparison with MemoryUnit."""
        if isinstance(value, MemoryUnit):
            return self._value < value._value  # noqa: SLF001
        elif is_bitarray(value):
            return self._value < ba2int(value)
        return self._value < value

    def __gt__(self: Self, value: int | bitarray) -> bool:
        """Greater than comparison with MemoryUnit."""
        if isinstance(value, MemoryUnit):
            return self._value > value._value  # noqa: SLF001
        elif is_bitarray(value):
            return self._value > ba2int(value)
        return self._value > value

    def __eq__(self: Self, value: int | bitarray) -> bool:
        """Equality comparison with MemoryUnit."""
        if isinstance(value, MemoryUnit):
            return self._value == value._value  # noqa: SLF001
        elif is_bitarray(value):
            return self._value == ba2int(value)
        return self._value == value

    def __le__(self: Self, value: int | bitarray) -> bool:
        """Less than or equal to comparison with MemoryUnit."""
        if isinstance(value, MemoryUnit):
            return self._value <= value._value  # noqa: SLF001
        elif is_bitarray(value):
            return self._value <= ba2int(value)
        return self._value <= value

    def __ge__(self: Self, value: int | bitarray) -> bool:
        """Greater than or equal to comparison with MemoryUnit."""
        if isinstance(value, MemoryUnit):
            return self._value >= value._value  # noqa: SLF001
        elif is_bitarray(value):
            return self._value >= ba2int(value)
        return self._value >= value

    def __int__(self: Self) -> int:
        """Return this MemoryUnit's value as an integer."""
        return self._value

    def __format__(self: Self, specifier: str) -> str:
        """Return this MemoryUnit as indicated by the format specifier."""
        return f"{self._value:{specifier}}"

    def __repr__(self: Self) -> str:
        """Describe this MemoryUnit in code."""
        return str(
            f"{self.__class__.__name__}("
            f"value={self._value:#02x}, "
            f"size_bits={self.size_bits}, "
            f"endianness={self._endianness}"
            ")",
        )

    def __str__(self: Self) -> str:
        """Describe this MemoryUnit as a hexadecimal value."""
        return str(hex(self._value))

    """ Index Operators """
    def __index__(self: Self) -> int:
        """Describe this MemoryUnit as an index."""
        return self._value

    def __getitem__(self: Self, index: int) -> int:
        """Return the specified bit value (0 or 1)."""
        return (self._value >> index) & 1

    def __delitem__(self: Self, index: int) -> None:
        """Not implemented."""

    def __setitem__(self: Self, index: int, value: int) -> None:
        """Set a bit on this MemoryUnit."""
        if isinstance(value, MemoryUnit):
            bit_value = value._value & 1  # noqa: SLF001
        else:
            bit_value = 1 if value else 0

        if bit_value:
            self._value |= (1 << index)
        else:
            self._value &= ~(1 << index)


class Byte(MemoryUnit):
    """Byte MemoryUnit().

    Uses flyweight pattern: cached instances are returned for values 0-255
    when using default endianness. This avoids object creation overhead
    for the common case.
    """

    log: logging.Logger = logging.getLogger("mos6502.memory.Byte")

    # Flyweight cache: pre-created Byte instances for values 0-255
    # Populated lazily on first access to avoid circular import issues
    _flyweight_cache: list["Byte"] | None = None

    def __new__(cls, value: int = 0, endianness: str = ENDIANNESS) -> "Byte":
        """Return cached Byte for common values, or create new instance.

        Flyweight pattern: reuse cached instances for values 0-255 with
        default endianness. This eliminates object creation overhead for
        the vast majority of Byte instantiations.
        """
        # Use flyweight cache for default endianness values 0-255
        if endianness == ENDIANNESS:
            # Normalize value to 0-255 range
            normalized = int(value) & 0xFF if not isinstance(value, MemoryUnit) else value._value & 0xFF

            # Initialize cache on first use
            if cls._flyweight_cache is None:
                cls._initialize_flyweight_cache()

            return cls._flyweight_cache[normalized]

        # Non-default endianness: create new instance
        instance = super().__new__(cls)
        return instance

    @classmethod
    def _initialize_flyweight_cache(cls) -> None:
        """Initialize the flyweight cache with Byte instances 0-255."""
        # Create cache list first to avoid recursion
        cls._flyweight_cache = [None] * 256

        # Create instances directly without going through __new__
        for i in range(256):
            instance = super().__new__(cls)
            # Initialize directly to avoid __init__ overhead during cache build
            instance._value = i
            instance._endianness = ENDIANNESS
            instance._overflow = False
            instance._underflow = False
            cls._flyweight_cache[i] = instance

    def __init__(self: Self, value: int = 0, endianness: str = ENDIANNESS) -> None:
        """Initialize a Byte().

        Note: For flyweight instances (default endianness, values 0-255),
        __init__ is called but the instance is already fully initialized
        from the cache. We skip re-initialization for cached instances.

        Arguments:
        ---------
            value: a value between -127 and 255
            endianness: 'big' or 'little' (default: mos6502.memory.ENDIANNESS)
        """
        # Skip init for cached flyweight instances (already initialized)
        if endianness == ENDIANNESS and Byte._flyweight_cache is not None:
            # Check if this is a cached instance by seeing if value matches
            normalized = int(value) & 0xFF if not isinstance(value, MemoryUnit) else value._value & 0xFF
            if self is Byte._flyweight_cache[normalized]:
                return

        # Non-cached instance: full initialization
        super().__init__(value=value, endianness=endianness)

    @property
    def size_bits(self: Self) -> Literal[8]:
        """Return the size in bits of this MemoryUnit (8 for Byte())."""
        return 8

    @property
    def _mask(self: Self) -> int:
        """Return the bit mask for Byte (0xFF)."""
        return 0xFF


class Word(MemoryUnit):
    """Word MemoryUnit()."""

    log: logging.Logger = logging.getLogger("mos6502.memory.Word")

    def __init__(self: Self, value: int = 0, endianness: str = ENDIANNESS) -> None:
        """Initialize a Word().

        Arguments:
        ---------
            value: a value between -32767 and 65535 (automatically masked to 16 bits)
            endianness: 'big' or 'little' (default: mos6502.memory.ENDIANNESS)
        """
        super().__init__(value=value, endianness=endianness)

    @property
    def size_bits(self: Self) -> Literal[16]:
        """Return the size in bits of this MemoryUnit (16 for Word())."""
        return 16

    @property
    def _mask(self: Self) -> int:
        """Return the bit mask for Word (0xFFFF)."""
        return 0xFFFF


class RAM(MutableSequence):
    """mos6502 RAM (64KB; 256 byte zeropage, 256 byte stack, 65024 byte heap)."""

    log: logging.Logger = logging.getLogger("mos6502.memory.RAM")

    def __init__(self: Self, endianness: str = ENDIANNESS, save_state: list[list] = None) -> None:
        """Instantiate a mos6502 RAM bank."""
        super().__init__()
        self.endianness: str = endianness
        self.memory_handler = None  # Optional external memory handler (for C64 banking, etc.)
        self._data: bytearray = bytearray()  # Will be initialized in initialize()
        self.initialize()

    def initialize(self: Self) -> None:
        """Initialize RAM to 0xFF (typical power-on state)."""
        # Real 6502 RAM contains unpredictable values on power-up
        # Using 0xFF avoids accidental BRK (0x00) execution

        # If there's a memory handler (e.g., C64 banking), skip initialization
        # to preserve any ROM data that was written before the handler was installed
        if self.memory_handler is not None:
            return

        # Flat bytearray for performance - eliminates branching on every access
        self._data: bytearray = bytearray([0xFF] * 0x10000)

    @property
    def zeropage(self: Self) -> memoryview:
        """Zero page ($0000-$00FF) as a view into the flat RAM array."""
        return memoryview(self._data)[0x0000:0x0100]

    @property
    def stack(self: Self) -> memoryview:
        """Stack page ($0100-$01FF) as a view into the flat RAM array."""
        return memoryview(self._data)[0x0100:0x0200]

    @property
    def heap(self: Self) -> memoryview:
        """Main memory ($0200-$FFFF) as a view into the flat RAM array."""
        return memoryview(self._data)[0x0200:0x10000]

    @property
    def data(self: Self) -> bytearray:
        """Direct access to flat RAM array for performance-critical code."""
        return self._data

    def __repr__(self: Self) -> str:
        """Return the code representation of the RAM."""
        return f"<{self.__class__.__name__} {len(self)} bytes>"

    def __len__(self: Self) -> int:
        """Return the length of the RAM."""
        return 0x10000  # 64KB

    def __getitem__(self: Self, index: int) -> int:
        """Get the RAM item at index {index}."""
        # Delegate to external memory handler if set (e.g., C64 banking)
        if self.memory_handler is not None:
            return self.memory_handler.read(index)

        # Direct flat array access - no branching
        return self._data[index]

    def __delitem__(self: Self, index: int) -> None:
        """Not implemented."""

    def __setitem__(self: Self, index: int, value: int, length: int = 8) -> None:
        """Set the RAM item at index {index} to value {value}."""
        # Delegate to external memory handler if set (e.g., C64 banking)
        if self.memory_handler is not None:
            self.memory_handler.write(index, value)
            return

        # Extract int value if passed a MemoryUnit
        if isinstance(value, MemoryUnit):
            int_value = value._value  # noqa: SLF001
        else:
            int_value = int(value) & 0xFF

        # Direct flat array access - no branching
        self._data[index] = int_value

    def insert(self: Self, index: int, value: int) -> None:
        """Not implemented."""

    def append(self: Self, value: int) -> None:
        """Not implemented."""

    def memory_section(self: Self, address: int) -> Literal["zeropage", "stack", "heap"]:
        """Return the name of the memory section at location {address}."""
        if address >= 0 and address < 256:
            return "zeropage"
        if address >= 256 and address < 512:
            return "stack"
        if address >= 512 and address <= 0xFFFF:
            return "heap"

        raise errors.InvalidMemoryLocationError(
            f"Invalid memory location: {address} should be between 0 and 65535",
        )

    def fill(self: Self, data: int) -> None:
        """Fill the RAM with {data}."""
        int_data = data._value if isinstance(data, MemoryUnit) else int(data) & 0xFF  # noqa: SLF001
        # Use efficient slice assignment instead of per-byte loop
        self._data[:] = bytes([int_data]) * 0x10000

    def read(self: Self, address: int, size: int = 1) -> list[int]:
        """Read size Bytes starting from address."""
        return [self[address + offset] for offset in range(size)]

    def write(self: Self, address: int, data: int) -> None:
        """Write a byte to address."""
        # Extract int value if passed a MemoryUnit
        if isinstance(data, MemoryUnit):
            int_data = data._value  # noqa: SLF001
        else:
            int_data = int(data)

        if (int_data < -127) or (int_data > 255):
            raise errors.InvalidMemoryAssignmentError(
                f"Data must be written one byte at a time, but got data > 1 byte: {int_data}",
            )

        self[address] = int_data & 0xFF
