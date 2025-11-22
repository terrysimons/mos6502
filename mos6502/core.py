#!/usr/bin/env python3
"""CPU core for the mos6502."""

import contextlib
import importlib
import logging
from typing import TYPE_CHECKING, Callable, Generator, Literal, Self

from bitarray.util import ba2int

from mos6502 import errors
from mos6502 import flags
from mos6502 import instructions
from mos6502 import memory
from mos6502 import registers
from mos6502 import variants
from mos6502.instructions import _nop as nop
from mos6502.memory import Byte
from mos6502.memory import RAM
from mos6502.memory import Word

if TYPE_CHECKING:
    from mos6502.registers import Registers


INFINITE_CYCLES: Literal[4294967295] = 0xFFFFFFFF

# Bit masks for byte operations
BYTE_BIT_0_MASK: int = 0x01  # Bit 0 mask
BYTE_BIT_1_MASK: int = 0x02  # Bit 1 mask
BYTE_BIT_2_MASK: int = 0x04  # Bit 2 mask
BYTE_BIT_3_MASK: int = 0x08  # Bit 3 mask
BYTE_BIT_4_MASK: int = 0x10  # Bit 4 mask
BYTE_BIT_5_MASK: int = 0x20  # Bit 5 mask
BYTE_BIT_6_MASK: int = 0x40  # Bit 6 mask
BYTE_BIT_7_MASK: int = 0x80  # Bit 7 mask


# https://skilldrick.github.io/easy6502/
# https://masswerk.at/6502/6502_instruction_set.html
# https://retro64.altervista.org/blog/an-introduction-to-6502-math-addiction-subtraction-and-more/
# https://www.pagetable.com/c64ref/6502/
# http://www.emulator101.com/6502-addressing-modes.html
# https://www.bigmessowires.com/2010/03/27/8-bit-cpu-comparison/
# https://www.youtube.com/watch?v=qJgsuQoy9bc
# http://www.visual6502.org/
# https://melodict.com/6502?fbclid=IwAR2L0JltG97b_F2gKzyu8IGyk_2JKKLUwHV7LQyrNHn4HMIyqLsSRBFyH3Y
# https://web.archive.org/web/20190410054640/http://obelisk.me.uk/6502/registers.html
class MOS6502CPU(flags.ProcessorStatusFlagsInterface):
    """mos6502CPU Core."""

    log: logging.Logger = logging.getLogger("mos6502.cpu")

    def __init__(
        self: Self,
        cpu_variant: str | variants.CPUVariant = variants.CPUVariant.NMOS_6502,
    ) -> Self:
        """Instantiate a mos6502 CPU core.

        Arguments:
        ---------
            cpu_variant: CPU variant to emulate. Can be:
                - CPUVariant enum value
                - String: "6502", "6502A", "6502C", "65C02"
                Defaults to NMOS 6502 for backward compatibility.
        """
        super().__init__()

        # Handle variant parameter
        if isinstance(cpu_variant, str):
            self._variant = variants.CPUVariant.from_string(cpu_variant)
        else:
            self._variant = cpu_variant

        self.endianness: str = "little"

        # As a convenience for code simplification we can set the default endianness
        # for newly created Byte/Word/etc... objects here
        memory.ENDIANNESS = self.endianness

        self._registers: Registers = registers.Registers(endianness=self.endianness)
        from mos6502.flags import FlagsRegister
        self._flags: FlagsRegister = FlagsRegister()
        self.ram: RAM = RAM(endianness=self.endianness)
        self.cycles = 0
        self.cycles_executed: Literal[0] = 0

        # Hardware interrupt request line (IRQ pin)
        # Set by external hardware (VIC, CIA, etc.) to request an interrupt
        # Checked by CPU between instructions
        self.irq_pending: bool = False

        # Optional callback for periodic system updates (e.g., VIC raster counter)
        # Called every N instructions to allow external hardware to update state
        self.periodic_callback: callable = None
        self.periodic_callback_interval: int = 100  # Call every 100 instructions

    @property
    def variant(self: Self) -> variants.CPUVariant:
        """Return the CPU variant being emulated."""
        return self._variant

    @property
    def variant_name(self: Self) -> str:
        """Return the CPU variant name as a string."""
        return str(self._variant)

    # Variant handler cache: {(instruction_package_name, function_name, variant): handler}
    _variant_handler_cache: dict[tuple[str, str, variants.CPUVariant], Callable[[Self], None]] = {}

    def _load_variant_handler(
        self: Self,
        instruction_package: str,
        function_name: str,
    ) -> Callable[[Self], None]:
        """Dynamically load variant-specific handler for an instruction.

        Tries to load <instruction>_<variant>.py, falls back to <instruction>_6502.py if not found.

        Arguments:
        ---------
            instruction_package: Package name (e.g., "mos6502.instructions.nop")
            function_name: Function name to load (e.g., "nop_implied_0xea")

        Returns:
        -------
            The handler function for the specified variant
        """
        cache_key = (instruction_package, function_name, self._variant)
        if cache_key in self._variant_handler_cache:
            return self._variant_handler_cache[cache_key]

        # Convert variant to module name (e.g., CMOS_65C02 -> 65c02)
        variant_name = str(self._variant).lower()

        # Extract instruction name from package (e.g., "mos6502.instructions.nop" -> "nop")
        instruction_name = instruction_package.split(".")[-1]

        # Try to load variant-specific module
        try:
            module = importlib.import_module(
                f".{instruction_name}_{variant_name}",
                package=instruction_package,
            )
        except ImportError:
            # Fall back to _6502 (default implementation)
            module = importlib.import_module(
                f".{instruction_name}_6502",
                package=instruction_package,
            )

        handler = getattr(module, function_name)
        self._variant_handler_cache[cache_key] = handler
        return handler

    @contextlib.contextmanager
    def instruction_variant(
        self: Self,
        opcode: instructions.InstructionOpcode,
    ) -> Generator[Callable[[], None], None, None]:
        """Context manager for executing variant-specific instruction.

        Provides debugging support by wrapping instruction execution with
        entry/exit hooks for logging, state validation, and error handling.

        Arguments:
        ---------
            opcode: The instruction opcode carrying variant metadata

        Yields:
        ------
            A callable instruction that executes the variant-specific implementation

        Example:
        -------
            with self.instruction_variant(instruction) as nop:
                nop()
        """
        # Extract package and function from opcode metadata
        instruction_package = opcode.package  # type: ignore
        function_name = opcode.function  # type: ignore

        # Look up the variant-specific handler
        handler = self._load_variant_handler(instruction_package, function_name)

        # Create a bound callable that doesn't require arguments
        def instruction() -> None:
            handler(self)

        # TODO: Add debug logging here if needed
        # self.log.debug(f"Executing {function_name} (variant: {self.variant_name})")

        try:
            yield instruction
        finally:
            # TODO: Add exit logging/validation here if needed
            # self.log.debug(f"Completed {function_name} (variant: {self.variant_name})")
            pass

    def __enter__(self: Self) -> Self:
        """With entrypoint."""
        return self

    def __exit__(self: Self, *args: list, **kwargs: dict) -> None:
        """With exitpoint."""

    def tick(self: Self, cycles: int) -> int:
        """
        Tick {cycles} cycles.

        Raises mos6502.errors.CPUCycleExhaustionError if the cycles parameter passed
        into the execute function is exhausted.

        Infinite cycles can be used by setting this to mos6502.core.INFINITE_CYCLES

        self.cycles_executed will have the # of executed cycles added to it.
        self.cycles will have {cycles} subtracted from it.

        Arguments:
        ---------
            cycles: the number of CPU cycles to execute before raising an exception.

        Returns:
        -------
            The number of cycles remaining.
        """
        for _i in range(cycles):
            if self.cycles <= 0:
                raise errors.CPUCycleExhaustionError(
                    "Exhausted available CPU cycles after "
                    f"{self.cycles_executed} "
                    f"executed cycles with {self.cycles} remaining.",
                )

            self.cycles_executed += 1

            if self.cycles != INFINITE_CYCLES:
                self.cycles -= 1
                self.log.debug(
                    f"TICK: Executed Cycles: {self.cycles_executed}, "
                    f"Remaining Cycles: {self.cycles}",
                )
            else:
                self.log.debug(
                    f"TICK: Executed Cycles: {self.cycles_executed}, "
                    f"Remaining Cycles: INFINITE",
                )

        return self.cycles

    def spend_cpu_cycles(self: Self, cost: int) -> None:
        """
        Tick the CPU and spend {cost} cycles.

        It's much easier to think about the cycle cost this way.

        Arguments:
        ---------
            cost: the number of cycles to consume

        Returns:
        -------
            None
        """
        for _i in range(cost):
            self.log.info("*")
        self.tick(cost)

    def fetch_byte(self: Self) -> Byte:
        """
        Fetch a Byte() from RAM[self.PC].

        Increments self.PC by 1.

        Costs 1 CPU cycle.

        Returns
        -------
            a Byte() set to the value located in memory at self.PC
        """
        addr: Word = self.PC
        byte: Byte = self.ram[self.PC]

        # TODO: This should be handled in the Word class
        if self.PC < 65535:
            self.PC += 1
        else:
            self.PC = 0
        self.log.info("f")
        self.spend_cpu_cycles(cost=1)

        self.log.debug(
            f"Fetch Byte: [{hex(addr)}:{hex(addr)}] "
            f"Byte: 0x{byte:02x} ({byte}) "
            f"lowbyte=0x{byte:02x}@0x{addr:02x} highbyte={None}",
        )

        return Byte(value=byte, endianness=self.endianness)

    def fetch_word(self: Self) -> Word:
        """
        Fetch a Word() from RAM[self.PC].

        Increments self.PC by 2.

        Costs 2 CPU cycles.

        Returns
        -------
            a Word() set to the value located in memory at RAM[self.PC:self.PC + 1]
        """
        addr1: Word = self.PC
        lowbyte: Byte = self.ram[self.PC]
        self.log.info("f")
        self.spend_cpu_cycles(cost=1)

        self.PC = self.PC + 1
        addr2: Word = self.PC
        highbyte: Byte = self.ram[self.PC]
        self.log.info("f")
        self.spend_cpu_cycles(cost=1)

        self.PC = self.PC + 1

        word = (highbyte << 8) + lowbyte

        self.log.debug(
            "Fetch Word: ["
            f"{hex(addr2)}:"
            f"{hex(addr1)}], "
            f"Word: 0x{word:02x} ({word}) "
            f"highbyte={lowbyte:02x}@0x{addr1:02x} lowbyte={highbyte:02x}@0x{addr2:02x}",
        )

        return Word(value=word, endianness=self.endianness)

    def read_byte(self: Self, address: Word) -> Byte:
        """
        Read a Byte() from RAM at location RAM[address].

        Costs 1 CPU cycle.

        Arguments:
        ---------
            address: the address to read from

        Returns:
        -------
            a Byte() set to the value located in memory at RAM[address]
        """
        memory_section = self.ram.memory_section(address=address)
        data: Byte = self.ram[int(address)]
        self.log.info("r")
        self.spend_cpu_cycles(cost=1)
        self.log.debug(f"read_byte({memory_section}[0x{address:02x}]): {data}")
        return data

    def peek_byte(self: Self, address: Word) -> Byte:
        """
        Read a Byte() from RAM at location RAM[address].

        Doesn't use CPU cycles.

        Arguments:
        ---------
            address: the address to read from

        Returns:
        -------
            a Byte() set to the value located in memory at RAM[address]
        """
        data: Byte = self.ram[int(address)]
        return data

    def write_byte(self: Self, address: Word, data: Byte) -> Byte:
        """
        Write a Byte() to RAM at location RAM[address].

        Costs 1 CPU cycle.

        Arguments:
        ---------
            address: the address to write to
            data: the Byte() to write

        Returns:
        -------
            None
        """
        self.ram[address] = data & 0xFF
        self.log.info("w")
        self.spend_cpu_cycles(cost=1)

    def read_word(self: Self, address: Word) -> Word:
        """
        Read a Word() from RAM at location RAM[address].

        Costs 2 CPU cycles.

        Arguments:
        ---------
            address: the address to read from

        Returns:
        -------
            a Byte() set to the value located in memory at RAM[address]
        """
        memory_section = self.ram.memory_section(address=address)
        lowbyte: Byte = self.ram[int(address)]
        self.log.info("r")
        self.spend_cpu_cycles(cost=1)
        highbyte: Byte = self.ram[int(address) + 1]
        self.log.info("r")
        self.spend_cpu_cycles(cost=1)
        data = (int(highbyte) << 8) + int(lowbyte)
        self.log.debug(f"read_word({memory_section}[0x{address:02x}]): 0x{data:04X} ({data})")
        return Word(data, endianness=self.endianness)

    def peek_word(self: Self, address: Word) -> Word:
        """
        Read a Word() from RAM at location RAM[address].

        Doesn't use CPU cycles.

        Arguments:
        ---------
            address: the address to read from

        Returns:
        -------
            a Byte() set to the value located in memory at RAM[address]
        """
        lowbyte: Byte = self.ram[int(address)]
        highbyte: Byte = self.ram[int(address) + 1]
        data = (int(highbyte) << 8) + int(lowbyte)
        return Word(data, endianness=self.endianness)

    def write_word(self: Self, address: Word, data: Word) -> None:
        """
        Write a Word() to RAM at location RAM[address].

        Costs 2 CPU cycles.

        Arguments:
        ---------
            address: the address to write to
            data: the Word() to write

        Returns:
        -------
            None
        """
        if isinstance(data, int):
            lowbyte = data & 0xFF
            highbyte = (data >> 8) & 0xFF
        else:
            lowbyte: int = ba2int(data.lowbyte_bits)
            highbyte: int = ba2int(data.highbyte_bits)
        self.ram[address] = lowbyte
        self.log.info("w")
        self.spend_cpu_cycles(cost=1)
        self.ram[address + 1] = highbyte
        self.log.info("w")
        self.spend_cpu_cycles(cost=1)

    def read_register(self: Self, register_name: str) -> Byte | Word:
        """
        Read the value of a register.

        Costs 1 CPU cycle.

        Arguments:
        ---------
            register_name: the name of the register to read

        Returns:
        -------
            a MemoryUnit (either Byte() or Word() depending on the register read)
        """
        if register_name == "PC":
            return getattr(self, register_name) & 0xFFFF

        return getattr(self, register_name) & 0xFF

    def write_register(self: Self, register_name: str, data: int) -> None:
        """
        Write a value to a register.

        Costs 1 CPU cycle.

        Arguments:
        ---------
            register_name: the name of the register to write to
            data: the data to write to the register

        Returns:
        -------
            a MemoryUnit (either Byte() or Word() depending on the register read)
        """
        if register_name == "PC":
            setattr(self, register_name, data & 0xFFFF)

        setattr(self, register_name, data & 0xFF)

    def write_register_to_ram(self: Self, register_name: str, address: int) -> None:
        """
        Write a register value to ram.

        Costs 1 CPU cycle for 8-bit registers, 2 cycles for 16-bit registers.

        Arguments:
        ---------
            register_name: the name of the register to write to
            data: the data to write to the register

        Returns:
        -------
            a MemoryUnit (either Byte() or Word() depending on the register read)
        """
        if register_name == "PC":
            self.write_byte(
                address=address,
                data=Byte(getattr(self, register_name)).lowbyte & 0xFF,
            )
            self.write_byte(
                address=address,
                data=Byte(getattr(self, register_name)).highbyte & 0xFF,
            )

        self.write_byte(address=address, data=getattr(self, register_name) & 0xFF)

    def write_ram_to_register(self: Self, address: int, register_name: str) -> None:
        """
        Write a ram value to a register.

        Costs 1 CPU cycle for 8-bit registers, 2 cycles for 16-bit registers.

        Arguments:
        ---------
            register_name: the name of the register to write to
            data: the data to write to the register

        Returns:
        -------
            a MemoryUnit (either Byte() or Word() depending on the register read)
        """
        if register_name == "PC":
            setattr(
                self,
                register_name,
                data=Word(
                    self.read_byte(address + 1) << 8 + self.read_byte(address),
                ),
            )

        setattr(self, register_name, self.fetch_byte(address=address) & 0xFF)

    def set_store_status_flags(self: Self, register_name: str) -> None:
        """
        Set the status flags for store operations.

        Arguments:
        ---------
            register_name: the name of th register to read to determine status
        """
        # No flag modifications for store instructions

    def set_load_status_flags(self: Self, register_name: str) -> None:
        """
        Set the status flags for load operations.

        Arguments:
        ---------
            register_name: the name of th register to read to determine status
        """
        register: Byte = getattr(self, register_name)
        self.Z = flags.ProcessorStatusFlags.Z[flags.Z] \
            if (register == 0x0) else not flags.ProcessorStatusFlags.Z[flags.Z]

        # Set negative flag if bit 7 of A is set
        self.N = flags.ProcessorStatusFlags.N[flags.N] \
            if (register & 128) else not flags.ProcessorStatusFlags.N[flags.N]

    def fetch_zeropage_mode_address(self: Self, offset_register_name: str) -> Byte:
        """
        Read from RAM @ RAM:ZEROPAGE[PC].

        Increases PC by 2.

        Costs 2 CPU cycles.

        Arguments:
        ---------
            register_name: the name of the register to fetch

        Returns:
        -------
            a Word()
        """
        zeropage_address: Byte = self.fetch_byte()

        offset_register_value: Literal[0] = 0
        address: Byte = zeropage_address + offset_register_value

        if offset_register_name is not None:
            offset_register_value: Literal[0] = getattr(self, offset_register_name)

            # This needs to wrap, so mask by 0xFF
            address: Byte = zeropage_address + offset_register_value

        return address

    def fetch_immediate_mode_address(self: Self) -> Byte:
        """
        Read from RAM @ RAM[PC].

        Increases PC by 1.

        Costs 1 CPU cycles.

        Arguments:
        ---------
            register_name: the name of the register to fetch

        Returns:
        -------
            a Word()
        """
        data: Byte = self.fetch_byte()

        return data

    def fetch_absolute_mode_address(self: Self, offset_register_name: str) -> Word:
        """
        Read from RAM @ RAM[(PC:PC + 1)].

        Increases PC by 2.

        Costs 2 CPU cycles.

        Arguments:
        ---------
            register_name: the name of the register to fetch

        Returns:
        -------
            a Word()
        """
        address: Word = self.fetch_word()

        if offset_register_name is not None:
            offset_register_value: Byte = getattr(self, offset_register_name)
            address: Word = address + offset_register_value

            if address.overflow:
                self.log.info("o")
                self.spend_cpu_cycles(1)

        return address

    def fetch_indexed_indirect_mode_address(self: Self) -> Word:
        """
        Read from RAM @ RAM[(PC:PC + 1) + X].

        Increases PC by 1.

        Costs 3 CPU cycles.

        Arguments:
        ---------
            register_name: the name of the register to fetch

        Returns:
        -------
            a Word()
        """
        indirect_address: Byte = self.fetch_byte()
        offset_register_value: Byte = self.X

        address: Word = self.read_word(indirect_address + offset_register_value)

        return address

    def fetch_indirect_indexed_mode_address(self: Self) -> Word:
        """
        Read from RAM @ RAM:[ZEROPAGE[PC] << 8 + ZEROPAGE[PC + 1] + Y.

        Increases PC by 1.

        Costs 3 CPU cycles.

        Arguments:
        ---------
            register_name: the name of the register to fetch

        Returns:
        -------
            a Word()
        """
        indirect_address: Byte = self.fetch_byte()
        offset_register_value: Byte = self.Y

        absolute_address: Word = self.read_word(indirect_address)

        # Note: We add these together this way to ensure
        # an overflow condition
        address: Word = Word(absolute_address) + Byte(offset_register_value)

        if address.overflow:
            self.log.info("o")
            self.spend_cpu_cycles(1)

        return address

    def execute_load_immediate(self: Self, instruction: instructions.InstructionSet,
                               register_name: str) -> None:
        """
        Instruction execution for "immediate LD[A, X, Y] #oper".

        Executes Load Immediate on {register_name} for {instruction}.

        Arguments:
        ---------
            instruction: the load immediate instruction to execute
            register_name: the register to load to

        Returns:
        -------
            None
        """
        # Note: Due to how we handle Byte and Word object, we have to look up the registers by
        # name, otherwise passing them through functions results in the register dereferencing
        # to an integer value.
        #
        # This helps us keep the code super readable by allowing heavy code reuse across instruction
        # types.
        #
        # Just remember to pass register names and dereference in methods if necessary.
        data: Byte = self.fetch_immediate_mode_address()

        setattr(self, register_name, data)
        self.set_load_status_flags(register_name=register_name)

        self.log.debug(
            f"{instructions.InstructionSet(int(instruction)).name}: "
            f"{Byte(value=getattr(self, register_name))}",
        )

    def execute_store_zeropage(self: Self, instruction: instructions.InstructionSet,
                               register_name: str, offset_register_name: str) -> None:
        """
        Instruction execution for store zeropage.

        "zeropage ST[A, X, Y] oper" and "zeropage ST[A, X, Y],[X, Y] oper".

        Executes Store Zeropage on {register_name} for {instruction} using {offset_register_name}.

        Arguments:
        ---------
            instruction: the store zeropage instruction to execute
            register_name: the register to load to
            offset_register_name: the offset register to use for any offset operations.

        Returns:
        -------
            None
        """
        # Note: Due to how we handle Byte and Word object, we have to look up the registers by
        # name, otherwise passing them through functions results in the register dereferencing
        # to an integer value.
        #
        # This helps us keep the code super readable by allowing heavy code reuse across instruction
        # types.
        #
        # Just remember to pass register names and dereference in methods if necessary.
        address: Byte = self.fetch_zeropage_mode_address(offset_register_name=offset_register_name)
        data: Byte = getattr(self, register_name)

        self.write_byte(address=address, data=data)
        setattr(self, register_name, self.read_byte(address=address))

        self.set_store_status_flags(register_name=register_name)

        self.log.debug(f"{instructions.InstructionSet(int(instruction)).name}: {Byte(value=data)}")

    def execute_load_zeropage(self: Self, instruction: instructions.InstructionSet,
                              register_name: str, offset_register_name: str) -> None:
        """
        Instruction execution for load zeropage.

        "zeropage LD[A, X, Y] oper" and "zeropage LD[A, X, Y],[X, Y] oper".

        Executes Load Zeropage on {register_name} for {instruction} using {offset_register_name}.

        Arguments:
        ---------
            instruction: the load zeropage instruction to execute
            register_name: the register to load to
            offset_register_name: the offset register to use for any offset operations.

        Returns:
        -------
            None
        """
        # Note: Due to how we handle Byte and Word object, we have to look up the registers by
        # name, otherwise passing them through functions results in the register dereferencing
        # to an integer value.
        #
        # This helps us keep the code super readable by allowing heavy code reuse across instruction
        # types.
        #
        # Just remember to pass register names and dereference in methods if necessary.
        address: Byte = self.fetch_zeropage_mode_address(offset_register_name=offset_register_name)
        register: Byte = getattr(self, register_name)

        setattr(self, register_name, self.read_byte(address=address))

        self.set_load_status_flags(register_name=register_name)

        self.log.debug(f"{instructions.InstructionSet(int(instruction)).name}: {Byte(value=register)}")

    def execute_store_absolute(self: Self, instruction: instructions.InstructionSet,
                               register_name: str, offset_register_name: str) -> None:
        """
        Instruction execution for store absolute.

        "absolute ST[A, X, Y] oper" and "absolute,[X, Y] ST[A, X, Y] oper,[X, Y]".

        Executes Load Absolute on {register_name} for {instruction} using {offset_register_name}

        Arguments:
        ---------
            instruction: the load absolute instruction to execute
            register_name: the register to load to
            offset_register_name: the offset register to use for any offset operations

        Returns:
        -------
            None
        """
        address: Word = self.fetch_absolute_mode_address(offset_register_name=offset_register_name)
        register: Byte = getattr(self, register_name)

        self.write_byte(address=address & 0xFFFF, data=register)
        self.set_store_status_flags(register_name=register_name)

        self.log.debug(f"{instructions.InstructionSet(int(instruction)).name}: {Byte(value=register)}")

    def execute_load_absolute(self: Self, instruction: instructions.InstructionSet,
                              register_name: str, offset_register_name: str) -> None:
        """
        Instruction execution for load absolute.

        "absolute LD[A, X, Y] oper" and "absolute,[X, Y] LD[A, X, Y] oper,[X, Y]".

        Executes Load Absolute on {register_name} for {instruction} using {offset_register_name}

        Arguments:
        ---------
            instruction: the load absolute instruction to execute
            register_name: the register to load to
            offset_register_name: the offset register to use for any offset operations

        Returns:
        -------
            None
        """
        # Note: Due to how we handle Byte and Word object, we have to look up the registers by
        # name, otherwise passing them through functions results in the register dereferencing
        # to an integer value.
        #
        # This helps us keep the code super readable by allowing heavy code reuse across instruction
        # types.
        #
        # Just remember to pass register names and dereference in methods if necessary.
        address: Word = self.fetch_absolute_mode_address(offset_register_name=offset_register_name)
        register: Byte = getattr(self, register_name)

        setattr(self, register_name, self.read_byte(address=address))
        self.set_load_status_flags(register_name=register_name)

        self.log.debug(f"{instructions.InstructionSet(int(instruction)).name}: {Byte(value=register)}")

    def execute_store_indexed_indirect(self: Self, instruction: instructions.InstructionSet,
                                       register_name: str) -> None:
        """
        Instruction execution for "(indirect,X) ST[A, X, Y] (oper,X)".

        Executes Store Indexed Indirect on {register_name} for {instruction}.

        Arguments:
        ---------
            instruction: the load indexed indirect instruction to execute
            register_name: the name of the register to load to

        Returns:
        -------
            None
        """
        # Note: Due to how we handle Byte and Word object, we have to look up the registers by
        # name, otherwise passing them through functions results in the register dereferencing
        # to an integer value.
        #
        # This helps us keep the code super readable by allowing heavy code reuse across instruction
        # types.
        #
        # Just remember to pass register names and dereference in methods if necessary.
        address: Word = self.fetch_indexed_indirect_mode_address() & 0xFFFF
        data: Byte = self.read_byte(address=address)

        setattr(self, register_name, data)
        self.set_store_status_flags(register_name=register_name)

        self.log.debug(
            f"{instructions.InstructionSet(int(instruction)).name}: "
            f"{Byte(value=self.ram[address])}",
        )

    def execute_load_indexed_indirect(self: Self, instruction: instructions.InstructionSet,
                                      register_name: str) -> None:
        """
        Instruction execution for "(indirect,X) LD[A, X, Y] (oper,X)".

        Executes Load Indexed Indirect on {register_name} for {instruction}.

        Arguments:
        ---------
            instruction: the load indexed indirect instruction to execute
            register_name: the name of the register to load to

        Returns:
        -------
            None
        """
        # Note: Due to how we handle Byte and Word object, we have to look up the registers by
        # name, otherwise passing them through functions results in the register dereferencing
        # to an integer value.
        #
        # This helps us keep the code super readable by allowing heavy code reuse across instruction
        # types.
        #
        # Just remember to pass register names and dereference in methods if necessary.
        address: Word = self.fetch_indexed_indirect_mode_address() & 0xFFFF
        register: Byte = getattr(self, register_name)

        setattr(self, register_name, self.read_byte(address=address))
        self.set_load_status_flags(register_name=register_name)

        self.log.debug(
            f"{instructions.InstructionSet(int(instruction)).name}: "
            f"{Byte(value=register)}",
        )

    def execute_store_indirect_indexed(self: Self, instruction: instructions.InstructionSet,
                                       register_name: str) -> None:
        """
        Instruction execution for "(indirect),Y LD[A, X, Y] (oper),Y".

        Executes Store Indirect Indexed on {register_name} for {instruction}.

        Arguments:
        ---------
            instruction: the load indexed indirect instruction to esxecute
            register_name: the name of the register to load to

        Returns:
        -------
            None
        """
        # Note: Due to how we handle Byte and Word object, we have to look up the registers by
        # name, otherwise passing them through functions results in the register dereferencing
        # to an integer value.
        #
        # This helps us keep the code super readable by allowing heavy code reuse across instruction
        # types.
        #
        # Just remember to pass register names and dereference in methods if necessary.
        address: Word = self.fetch_indirect_indexed_mode_address()

        setattr(self, register_name, self.read_byte(address=address))
        self.set_store_status_flags(register_name=register_name)

        self.log.debug(
            f"{instructions.InstructionSet(int(instruction)).name}: "
            f"{Byte(value=self.ram[address & 0xFFFF])}",
        )

    def execute_load_indirect_indexed(self: Self, instruction: instructions.InstructionSet,
                                      register_name: str) -> None:
        """
        Instruction execution for "(indirect),Y LD[A, X, Y] (oper),Y".

        Executes Load Indirect Indexed on {register_name} for {instruction}.

        Arguments:
        ---------
            instruction: the load indexed indirect instruction to esxecute
            register_name: the name of the register to load to

        Returns:
        -------
            None
        """
        # Note: Due to how we handle Byte and Word object, we have to look up the registers by
        # name, otherwise passing them through functions results in the register dereferencing
        # to an integer value.
        #
        # This helps us keep the code super readable by allowing heavy code reuse across instruction
        # types.
        #
        # Just remember to pass register names and dereference in methods if necessary.
        address: Word = self.fetch_indirect_indexed_mode_address()

        setattr(self, register_name, self.read_byte(address=address))
        self.set_load_status_flags(register_name=register_name)

        register: Byte = getattr(self, register_name)

        self.log.debug(f"{instructions.InstructionSet(int(instruction)).name}: {Byte(value=register)}")

    def _adc_bcd(self: Self, a: int, value: int, carry_in: int) -> tuple[int, int, int, int]:
        """
        Perform BCD (Binary-Coded Decimal) addition.

        Arguments:
            a: Accumulator value (0x00-0xFF)
            value: Value to add (0x00-0xFF)
            carry_in: Carry flag value (0 or 1)

        Returns:
            Tuple of (result, carry_out, overflow, binary_result)

        VARIANT: 6502 - V flag is undefined in BCD mode
        VARIANT: 65C02 - V flag is calculated from binary result before BCD adjustment
        VARIANT: 6502 - N and Z flags are set from BCD result
        VARIANT: 65C02 - N and Z flags are set from binary result
        """
        # Add low nibbles (bits 0-3)
        low_nibble: int = (a & 0x0F) + (value & 0x0F) + carry_in
        half_carry: int = 0

        # Adjust if low nibble > 9
        if low_nibble > 0x09:
            low_nibble += 0x06
            half_carry = 1

        # Add high nibbles (bits 4-7)
        high_nibble: int = ((a >> 4) & 0x0F) + ((value >> 4) & 0x0F) + half_carry

        # Calculate binary result for V flag (65C02 behavior)
        binary_result: int = a + value + carry_in

        # Adjust if high nibble > 9
        carry_out: int = 0
        if high_nibble > 0x09:
            high_nibble += 0x06
            carry_out = 1

        # Combine nibbles
        result: int = ((high_nibble << 4) | (low_nibble & 0x0F)) & 0xFF

        # VARIANT: 6502 - V flag is undefined, we calculate it from binary result
        # VARIANT: 65C02 - V flag is calculated from binary result before BCD adjustment
        overflow: int = 1 if ((a ^ binary_result) & (value ^ binary_result) & BYTE_BIT_7_MASK) else 0

        return result, carry_out, overflow, binary_result

    def _sbc_bcd(self: Self, a: int, value: int, carry_in: int) -> tuple[int, int, int, int]:
        """
        Perform BCD (Binary-Coded Decimal) subtraction.

        Arguments:
            a: Accumulator value (0x00-0xFF)
            value: Value to subtract (0x00-0xFF)
            carry_in: Carry flag value (0 or 1, inverted borrow)

        Returns:
            Tuple of (result, carry_out, overflow, binary_result)

        VARIANT: 6502 - V flag is undefined in BCD mode
        VARIANT: 65C02 - V flag is calculated from binary result before BCD adjustment
        VARIANT: 6502 - N and Z flags are set from BCD result
        VARIANT: 65C02 - N and Z flags are set from binary result
        """
        # Subtract low nibbles (bits 0-3)
        low_nibble: int = (a & 0x0F) - (value & 0x0F) - (1 - carry_in)
        half_borrow: int = 0

        # Adjust if low nibble < 0
        if low_nibble < 0:
            low_nibble -= 0x06
            half_borrow = 1

        # Subtract high nibbles (bits 4-7)
        high_nibble: int = ((a >> 4) & 0x0F) - ((value >> 4) & 0x0F) - half_borrow

        # Calculate binary result for V flag (65C02 behavior)
        binary_result: int = a - value - (1 - carry_in)

        # Adjust if high nibble < 0
        carry_out: int = 1  # No borrow by default
        if high_nibble < 0:
            high_nibble -= 0x06
            carry_out = 0  # Borrow occurred

        # Combine nibbles
        result: int = ((high_nibble << 4) | (low_nibble & 0x0F)) & 0xFF

        # VARIANT: 6502 - V flag is undefined, we calculate it from binary result
        # VARIANT: 65C02 - V flag is calculated from binary result before BCD adjustment
        overflow: int = 1 if ((a ^ value) & (a ^ binary_result) & BYTE_BIT_7_MASK) else 0

        return result, carry_out, overflow, binary_result

    def execute(self: Self, cycles: int = 1) -> int:  # noqa: C901
        """
        Fetch and execute a CPU instruction.

        Arguments:
        ---------
            cycles: the number of cycles to execute.  Used for testing.
                Use mos6502.core.INFINITE_CYCLES for long running programs.

        Returns:
        -------
            The number of cycles executed.
        """
        self.cycles: int = cycles

        while True:
            # Check for cycle exhaustion BEFORE fetching the next instruction
            # This prevents PC from being incremented into the next instruction
            # when we don't have enough cycles to execute it
            if self.cycles <= 0:
                raise errors.CPUCycleExhaustionError(
                    f"Exhausted available CPU cycles after {self.cycles_executed} "
                    f"executed cycles with {self.cycles} remaining.",
                )

            instruction_byte: Byte = self.fetch_byte()

            # Convert to InstructionOpcode if available for variant dispatch
            instruction = instructions.OPCODE_LOOKUP.get(int(instruction_byte), instruction_byte)

            # self.log.debug(

            instruction_bytes: int = 0

            machine_code = []
            operand: memory.MemoryUnit = 0
            assembly = ""
            instruction_cycle_count: int = 0
            if int(instruction) in instructions.InstructionSet.map:
                instruction_map: int = instructions.InstructionSet.map[int(instruction)]

                instruction_bytes: int = int(instruction_map["bytes"])

                instruction_cycle_count = instruction_map["cycles"]

                with contextlib.suppress(ValueError):
                    instruction_cycle_count: int = int(instruction_map["cycles"])

                # Subtract 1 for the instruction
                for i in range(instruction_bytes - 1):
                    # Wrap address to stay within 16-bit address space (0-65535)
                    machine_code.append(int(self.ram[(self.PC + i) & 0xFFFF]))

                if len(machine_code) > 2:
                    raise errors.MachineCodeExecutionException(
                        f"Unsure how to handle: {machine_code}",
                    )

                if len(machine_code) == 0:
                    assembly: str = instruction_map["assembler"]
                    operand: memory.MemoryUnit = None

                if len(machine_code) == 1:
                    operand: memory.MemoryUnit = Byte(
                        value=machine_code[0],
                        endianness=self.endianness,
                    )
                    assembly = instruction_map["assembler"].format(oper=f"0x{operand:02X}")

                if len(machine_code) == 2:
                    low_byte: memory.MemoryUnit = machine_code[0]
                    high_byte: memory.MemoryUnit = machine_code[1]

                    operand: memory.MemoryUnit = Word((high_byte << 8) + low_byte)

                    assembly: str = instruction_map["assembler"].format(oper=f"0x{operand:02X}")

            if operand is not None:
                self.log.info(
                    f"0x{self.PC - 1:02X}: 0x{instruction:02X} "
                    f"0x{operand:02X} \t\t\t {assembly} \t\t\t {instruction_cycle_count}",
                )
            else:
                self.log.info(
                    f"0x{self.PC - 1:02X}: 0x{instruction:02X} ---- "
                    f"\t\t\t {assembly} \t\t\t {instruction_cycle_count}",
                )

            # This automatically invokes the correct opcode handler based on the configured CPU variant.
            # Legal instructions have metadata (package/function), illegal ones don't
            if hasattr(instruction, "package") and hasattr(instruction, "function"):
                with self.instruction_variant(instruction) as execute_instruction_variant:
                    execute_instruction_variant()
            else:
                # Illegal instruction - no metadata found
                self.log.error(f"ILLEGAL INSTRUCTION: {instruction} ({instruction:02X})")
                raise errors.IllegalCPUInstructionError(
                    f"Illegal instruction: 0x{int(instruction):02X}"
                )

            # Periodically call system update callback (e.g., VIC raster updates)
            # This allows external hardware to check cycle count and trigger IRQs
            if self.periodic_callback and (self.cycles_executed % self.periodic_callback_interval == 0):
                self.periodic_callback()

            # Check for pending hardware IRQ between instructions (after instruction completes)
            # This is when the real 6502 samples the IRQ line
            if self.irq_pending and not self.I:
                self._handle_irq()

    def _handle_irq(self: Self) -> None:
        """Handle a pending hardware IRQ.

        This implements the 6502 IRQ sequence:
        1. Push PC (2 bytes) to stack
        2. Push P (status register) to stack with B flag clear
        3. Set I flag to disable further interrupts
        4. Load PC from IRQ vector at $FFFE/$FFFF
        5. Clear the irq_pending flag

        Total: 7 cycles
        """
        # Clear the pending flag first
        self.irq_pending = False

        # Push PC to stack (high byte first)
        pc_high = (self.PC >> 8) & 0xFF
        pc_low = self.PC & 0xFF

        self.ram[self.S] = pc_high
        self.S -= 1
        self.spend_cpu_cycles(1)

        self.ram[self.S] = pc_low
        self.S -= 1
        self.spend_cpu_cycles(1)

        # Push status register with B flag CLEAR (hardware IRQ, not BRK)
        status = self._flags.value & ~0x10
        self.ram[self.S] = status
        self.S -= 1
        self.spend_cpu_cycles(1)

        # Set I flag to disable further interrupts
        self.I = 1

        # Load PC from IRQ vector at $FFFE/$FFFF
        irq_vector = self.read_word(0xFFFE)
        self.PC = irq_vector

        self.log.debug(f"IRQ handled: jumping to ${irq_vector:04X}")

    def push_pc_to_stack(self: Self) -> None:
        """Push the PC to the stack."""

    def reset(self: Self) -> None:
        """
        Reset the CPU.

        It is necessary to call this method before executing instructions.

        This implements the actual 6502 reset sequence:
        - Cycle 1: Internal operations
        - Cycle 2-3: Fetch reset vector from $FFFC/$FFFD
        - Additional cycles for internal setup
        Total: ~7 cycles consumed

        Hardware behavior (NMOS 6502):
        - S set to 0xFD
        - P set to 0x34 (I flag = 1, bit 5 = 1, D = 0)
        - PC loaded from reset vector at $FFFC/$FFFD
        - A, X, Y undefined (we zero them for consistency)
        """
        self.log.info("Reset")

        # Initialize RAM first (before reading reset vector)
        self.ram.initialize()

        # VARIANT: 6502 - Stack pointer set to 0xFD during reset
        # VARIANT: 65C02 - Same behavior as 6502
        # VARIANT: 65C816 - Same behavior as 6502 (8-bit mode)
        # The stack pointer is stored with 0x0100 offset for convenience
        self.S: Word = Word(0x01FD, endianness=self.endianness)

        # VARIANT: 6502 - Status register set to 0x34 on reset
        # VARIANT: 65C02 - Same as 6502 (I=1, bit5=1, D=0)
        # VARIANT: 65C816 - Same in emulation mode
        # Bit 5 is always set (unused bit) - handled by FlagsRegister
        # I flag (bit 2) is set to disable interrupts
        # D flag (bit 3) is cleared (decimal mode off)
        # Other flags are undefined/don't care (we zero them)
        self.C = 0
        self.Z = 0
        self.I = 1  # Interrupts disabled
        self.D = 0  # Decimal mode off
        self.B = 0
        self.V = 0
        self.N = 0

        # 1 Byte Registers - undefined on real hardware, we zero them
        self.A = 0
        self.X = 0
        self.Y = 0

        # VARIANT: 6502 - Reset vector fetch from $FFFC/$FFFD (cycles 2-3)
        # VARIANT: 65C02 - Same as 6502
        # VARIANT: 65C816 - Uses $FFFC/$FFFD in emulation mode
        # Cycle 1: Internal operations (implicit above)
        # Cycles 2-3: Fetch reset vector
        reset_vector_addr = 0xFFFC

        # Fetch low byte of reset vector (cycle 2)
        # Note: We use peek_word which doesn't consume cycles
        # We'll manually account for the reset sequence cycles below
        reset_vector = self.peek_word(reset_vector_addr)

        # Set PC to the reset vector value
        self.PC: Word = Word(reset_vector, endianness=self.endianness)

        # VARIANT: 6502 - Reset sequence consumes 7 cycles total
        # VARIANT: 65C02 - Same as 6502
        # VARIANT: 65C816 - Same in emulation mode
        # Account for reset sequence cycles: 7 total
        # (internal ops + vector fetch + setup)
        self.cycles_executed += 7

        self.log.info(f"Reset complete: PC=${self.PC:04X}, S=${self.S & 0xFF:02X}, P=0x34, 7 cycles consumed")

    @property
    def flags(self: Self) -> Byte:
        """
        Return the CPU flags register.

        Returns
        -------
            Byte()
        """
        return self._flags

    @flags.setter
    def flags(self: Self, flags: int) -> None:
        """
        Set the CPU flags register.

        Arguments:
        ---------
            flags: Byte()

        Returns:
        -------
            None
        """
        self.log.debug(f"Flags <- 0x{self._flags.flags:02X}")

        setattr(self._flags, flags)
    @property
    def PC(self: Self) -> Word:  # noqa: N802
        """
        Return the CPU PC register.

        Returns
        -------
            Word()
        """
        self.log.debug(f"PC <- 0x{self._registers.PC:04X}")
        return self._registers.PC

    @PC.setter
    def PC(self: Self, PC: Word) -> None:  # noqa: N802 N803
        """
        Set the CPU PC register.

        Arguments:
        ---------
            PC: Word()

        Returns:
        -------
            None
        """
        self._registers.PC = Word(PC)
        self.log.info(f"PC -> 0x{self._registers.PC:04X}")

    @property
    def S(self: Self) -> Word:  # noqa: N802
        """
        Return the CPU S register.

        This register is an 8-bit register, but we store it as 16-bits for convenience.

        This register must be masked with 0xFF when performing instruction offset calculations.

        Returns
        -------
            Word()
        """
        self.log.debug(f"S <- 0x{self._registers.S:02X} ")
        return self._registers.S

    @S.setter
    def S(self: Self, S: Word) -> None:  # noqa: N802 N803
        """
        Set the CPU S register.

        Arguments:
        ---------
            S: Byte() or Word() (masked with 0xFF)

        Returns:
        -------
            None
        """
        self._registers.S = Word(S & 511)
        self.log.info(f"S -> 0x{self._registers.S & 0xFF:02X}")

    @property
    def A(self: Self) -> Byte:  # noqa: N802
        """
        Return the CPU A register.

        Returns
        -------
            Byte()
        """
        self.log.debug(f"A <- 0x{self._registers.Y:02X}")
        return self._registers.A

    @A.setter
    def A(self: Self, A: Byte) -> Byte:  # noqa: N802 N803
        """
        Set the CPU A register.

        Arguments:
        ---------
            A: Byte()

        Returns:
        -------
            None
        """
        self._registers.A = A
        self.log.info(f"A -> 0x{self._registers.A:02X}")

    @property
    def X(self: Self) -> Byte:  # noqa: N802
        """
        Return the CPU X register.

        Returns
        -------
            Byte()
        """
        self.log.debug(f"X <- 0x{self._registers.Y:02X}")
        return self._registers.X

    @X.setter
    def X(self: Self, X: Byte) -> None:  # noqa: N802 N803
        """
        Set the CPU X register.

        Arguments:
        ---------
            X: Byte()

        Returns:
        -------
            None
        """
        self._registers.X = X
        self.log.info(f"X -> 0x{self._registers.X:02X}")

    @property
    def Y(self: Self) -> Byte:  # noqa: N802
        """
        Return the CPU Y register.

        Returns
        -------
            Byte()
        """
        self.log.debug(f"Y <- 0x{self._registers.Y:02X}")
        return self._registers.Y

    @Y.setter
    def Y(self: Self, Y: Byte) -> None:  # noqa: N802 N803
        """
        Set the CPU Y register.

        Arguments:
        ---------
            Y: Byte()

        Returns:
        -------
            None
        """
        self._registers.Y = Y
        self.log.info(f"Y -> 0x{self._registers.Y:02X}")

    def __str__(self: Self) -> str:
        """Return the CPU status."""
        description: str = f"{type(self).__name__}\n"
        description += f"\tPC: 0x{self.PC:04X}\n"
        description += f"\tS: 0x{self.S:04X}\n"
        description += f"\tC: {self.C}\n"
        description += f"\tZ: {self.Z}\n"
        description += f"\tI: {self.I}\n"
        description += f"\tD: {self.D}\n"
        description += f"\tB: {self.B}\n"
        description += f"\tV: {self.V}\n"
        description += f"\tN: {self.N}\n"
        description += f"Executed Cycles: {self.cycles_executed}"
        description += "\n"

        return description


def main() -> None:
    """
    Demo program.

    Demonstrates using the CPU in a context manager.

    Loads the JSR instruction and jumps to 0x4242
    then loads 0x23 from 0x4243 using the LDA_IMMEDIATE instruction.
    """
    log: logging.Logger = logging.getLogger("mos6502")
    logging.basicConfig(format="%(message)s", level=logging.INFO)

    with MOS6502CPU() as cpu:
        cpu.reset()
        log.info(cpu)

        cpu.ram.fill(Byte(instructions.NOP_IMPLIED_0xEA))
        # Supported instructions
        # LDA, LDX, LDY - see tests/test_mos6502_LDA_LDX_LDY_instruction.py
        # JSR - see tests/test_mos6502_JMP_JSR_instruction.py

        cpu.C = 1
        cpu.D = 1
        cpu.V = 1
        cpu.I = 1

        # Jump to 0x4242
        # Should be 9 cycles
        cpu.ram[0xFFFC] = instructions.JSR_ABSOLUTE_0x20
        cpu.ram[0xFFFD] = 0x42
        cpu.ram[0xFFFE] = 0x42
        cpu.ram[0x4242] = instructions.LDA_IMMEDIATE_0xA9
        cpu.ram[0x4243] = 0x23
        cpu.ram[0x4244] = instructions.CLC_IMPLIED_0x18
        cpu.ram[0x4245] = instructions.CLD_IMPLIED_0xD8
        cpu.ram[0x4246] = instructions.CLV_IMPLIED_0xB8
        cpu.ram[0x4247] = instructions.CLI_IMPLIED_0x58

        log.info(cpu)

        try:
            cpu.execute(cycles=20)
        except errors.CPUCycleExhaustionError:
            log.info(f"Used: {cpu.cycles_executed} cycles")

        log.info(cpu)


if __name__ == "__main__":
    main()
