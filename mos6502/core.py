#!/usr/bin/env python3
"""CPU core for the mos6502."""

from mos6502.compat import contextlib, logging, import_module, TYPE_CHECKING, Callable, Literal, Union, Dict, Tuple

from mos6502.bitarray_factory import ba2int

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

    __slots__ = (
        '_variant',
        'verbose_cycles',
        'endianness',
        '_registers',
        '_flags',
        'ram',
        'cycles',
        'cycles_executed',
        'instructions_executed',
        'instructions_remaining',
        'irq_pending',
        'nmi_pending',
        '_nmi_line_previous',
        'periodic_callback',
        'periodic_callback_interval',
        '_last_periodic_callback_cycle',
        'pc_callback',
        'pre_instruction_callback',
        'post_instruction_callback',
        'pre_tick_callback',
        'post_tick_callback',
        '_opcode_handler_cache',
        'unstable_config',
        'halted',
    )

    log: logging.Logger = logging.getLogger("mos6502.cpu")

    def __init__(
        self,
        cpu_variant: Union[str, variants.CPUVariant]= variants.CPUVariant.NMOS_6502,
        verbose_cycles: bool = False,
    ) -> "MOS6502CPU":
        """Instantiate a mos6502 CPU core.

        Arguments:
        ---------
            cpu_variant: CPU variant to emulate. Can be:
                - CPUVariant enum value
                - String: "6502", "6502A", "6502C", "65C02"
                Defaults to NMOS 6502 for backward compatibility.
            verbose_cycles: If True, emit per-cycle log messages (slow).
                Defaults to False for performance.
        """
        super().__init__()

        # Handle variant parameter
        if isinstance(cpu_variant, str):
            self._variant = variants.CPUVariant.from_string(cpu_variant)
        else:
            self._variant = cpu_variant

        # Configuration for unstable/highly-unstable illegal opcodes
        # Users can override this after creation to customize chip behavior
        self.unstable_config: variants.UnstableOpcodeConfig = variants.UNSTABLE_OPCODE_DEFAULTS.get(
            self._variant.value,
            variants.UnstableOpcodeConfig(ane_const=0xFF, unstable_stores_enabled=True)
        )

        self.verbose_cycles: bool = verbose_cycles
        self.endianness: str = "little"

        # As a convenience for code simplification we can set the default endianness
        # for newly created Byte/Word/etc... objects here
        memory.ENDIANNESS = self.endianness

        self._registers: "Registers" = registers.Registers(endianness=self.endianness)
        from mos6502.flags import FlagsRegister
        self._flags: FlagsRegister = FlagsRegister()
        self.ram: RAM = RAM(endianness=self.endianness)
        self.cycles = 0
        self.cycles_executed: Literal[0] = 0
        self.instructions_executed: int = 0  # Total instructions executed
        self.instructions_remaining: int = 0  # Instructions left to execute

        # Hardware interrupt request line (IRQ pin)
        # Set by external hardware (VIC, CIA, etc.) to request an interrupt
        # Checked by CPU between instructions
        self.irq_pending: bool = False

        # Non-maskable interrupt (NMI pin)
        # Set by external hardware (CIA2 on C64) to request a non-maskable interrupt
        # NMI is edge-triggered: fires on transition from high to low (falling edge)
        # Unlike IRQ, NMI cannot be disabled by the I flag
        self.nmi_pending: bool = False
        self._nmi_line_previous: bool = False  # For edge detection

        # CPU halted flag - set by JAM/KIL instructions
        # When True, CPU execution stops and requires reset
        self.halted: bool = False

        # Optional callback for periodic system updates (e.g., VIC raster counter)
        # Called every N cycles to allow external hardware to update state
        self.periodic_callback: callable = None
        self.periodic_callback_interval: int = 100  # Call every 100 cycles
        self._last_periodic_callback_cycle: int = 0  # Track last callback cycle

        # Optional callback called when PC changes (for breakpoints, monitors, etc.)
        # Signature: pc_callback(new_pc: int) -> None
        # If callback raises StopIteration, execution will stop
        self.pc_callback: callable = None

        # Optional callbacks for instruction execution hooks
        # Useful for debugging, profiling, breakpoints, and generalizing to other CPU cores
        # Signature: callback(cpu, instruction) -> None
        # pre_instruction_callback: Called before each instruction executes
        # post_instruction_callback: Called after each instruction executes
        self.pre_instruction_callback: callable = None
        self.post_instruction_callback: callable = None

        # Optional callbacks for tick (cycle consumption) hooks
        # Useful for synchronizing external hardware (e.g., IEC bus)
        # Signature: callback(cpu, cycles) -> None
        # pre_tick_callback: Called before cycles are consumed
        # post_tick_callback: Called after cycles are consumed
        self.pre_tick_callback: callable = None
        self.post_tick_callback: callable = None

        # Opcode -> handler cache for fast dispatch (per-instance since variant is per-instance)
        # 256-entry list indexed by opcode byte for O(1) array access (faster than dict)
        # None entries indicate illegal opcodes
        self._opcode_handler_cache: list = self._build_opcode_handler_table()

    @property
    def variant(self) -> variants.CPUVariant:
        """Return the CPU variant being emulated."""
        return self._variant

    @property
    def variant_name(self) -> str:
        """Return the CPU variant name as a string."""
        return str(self._variant)

    # Variant handler cache: {(instruction_package_name, function_name, variant): handler}
    _variant_handler_cache: Dict[Tuple[str, str, variants.CPUVariant], Callable[["MOS6502CPU"], None]] = {}

    def _load_variant_handler(
        self,
        instruction_package: str,
        function_name: str,
    ) -> Callable[["MOS6502CPU"], None]:
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
            module = import_module(
                f".{instruction_name}_{variant_name}",
                package=instruction_package,
            )
        except ImportError:
            # Fall back to _6502 (default implementation)
            module = import_module(
                f".{instruction_name}_6502",
                package=instruction_package,
            )

        handler = getattr(module, function_name)
        self._variant_handler_cache[cache_key] = handler
        return handler

    def _build_opcode_handler_table(self) -> list:
        """Build a 256-entry opcode handler table for fast dispatch.

        Pre-populates handlers for all legal opcodes using OPCODE_LOOKUP.
        Illegal opcodes are set to None.

        Returns:
            256-entry list where table[opcode] is the handler function or None
        """
        table = [None] * 256

        for opcode, instruction in instructions.OPCODE_LOOKUP.items():
            if isinstance(instruction, instructions.InstructionOpcode):
                handler = self._load_variant_handler(instruction.package, instruction.function)
                table[opcode] = handler

        return table

    def __enter__(self) -> "MOS6502CPU":
        """With entrypoint."""
        return self

    def __exit__(self, *args: list, **kwargs: dict) -> None:
        """With exitpoint."""

    def tick(self, cycles: int) -> int:
        """
        Tick {cycles} cycles.

        Instructions are atomic - they always consume all cycles needed.
        Cycle exhaustion is checked at instruction boundaries (in execute()).

        Infinite cycles can be used by setting this to mos6502.core.INFINITE_CYCLES

        self.cycles_executed will have the # of executed cycles added to it.
        self.cycles will have {cycles} subtracted from it (can go negative).

        Arguments:
        ---------
            cycles: the number of CPU cycles to consume.

        Returns:
        -------
            The number of cycles remaining (can be negative).
        """
        # Pre-tick callback (for external hardware synchronization)
        if self.pre_tick_callback:
            self.pre_tick_callback(self, cycles)

        # Fast path: batch update when not doing per-cycle logging
        if not self.verbose_cycles:
            self.cycles_executed += cycles
            if self.cycles != INFINITE_CYCLES:
                self.cycles -= cycles
            # Post-tick callback
            if self.post_tick_callback:
                self.post_tick_callback(self, cycles)
            return self.cycles

        # Verbose path: per-cycle logging for debugging
        for _i in range(cycles):
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

        # Post-tick callback
        if self.post_tick_callback:
            self.post_tick_callback(self, cycles)

        return self.cycles

    def spend_cpu_cycles(self, cost: int) -> None:
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
        if self.verbose_cycles:
            self.log.info("*" * cost)
        self.tick(cost)

    def fetch_byte(self) -> int:
        """
        Fetch a byte from RAM[self.PC].

        Increments self.PC by 1.

        Costs 1 CPU cycle.

        Returns
        -------
            int: the byte value located in memory at self.PC
        """
        byte: int = self.ram[self.PC]

        # Use explicit assignment to trigger PC setter (for pc_callback)
        # Setter handles 16-bit wrap via & 0xFFFF masking
        self.PC = self.PC + 1
        self.spend_cpu_cycles(cost=1)

        if self.verbose_cycles:
            addr = self.PC - 1
            self.log.info("f")
            self.log.debug(
                f"Fetch Byte: [{hex(addr)}:{hex(addr)}] "
                f"Byte: 0x{byte:02x} ({byte}) "
                f"lowbyte=0x{byte:02x}@0x{addr:02x} highbyte={None}",
            )

        return byte

    def fetch_word(self) -> int:
        """
        Fetch a word from RAM[self.PC].

        Increments self.PC by 2.

        Costs 2 CPU cycles.

        Returns
        -------
            int: the 16-bit word value located in memory at RAM[self.PC:self.PC + 1]
        """
        addr1: int = self.PC
        lowbyte: int = self.ram[self.PC]
        self.spend_cpu_cycles(cost=1)

        self.PC = self.PC + 1
        addr2: int = self.PC
        highbyte: int = self.ram[self.PC]
        self.spend_cpu_cycles(cost=1)

        self.PC = self.PC + 1

        word: int = (highbyte << 8) | lowbyte

        if self.verbose_cycles:
            self.log.info("ff")
            self.log.debug(
                "Fetch Word: ["
                f"{hex(addr2)}:"
                f"{hex(addr1)}], "
                f"Word: 0x{word:02x} ({word}) "
                f"lowbyte={lowbyte:02x}@0x{addr1:02x} highbyte={highbyte:02x}@0x{addr2:02x}",
            )

        return word

    def read_byte(self, address: int) -> int:
        """
        Read a byte from RAM at location RAM[address].

        Costs 1 CPU cycle.

        Arguments:
        ---------
            address: the address to read from

        Returns:
        -------
            int: the byte value located in memory at RAM[address]
        """
        data: int = self.ram[address]
        self.spend_cpu_cycles(cost=1)
        if self.verbose_cycles:
            memory_section = self.ram.memory_section(address=address)
            self.log.info("r")
            self.log.debug(f"read_byte({memory_section}[0x{address:02x}]): {data}")
        return data

    def peek_byte(self, address: Word) -> Byte:
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

    def write_byte(self, address: Word, data: Byte) -> Byte:
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
        self.spend_cpu_cycles(cost=1)
        if self.verbose_cycles:
            # DEBUG: Log screen writes
            addr_int = int(address) if hasattr(address, '__int__') else address
            if 0x0400 <= addr_int <= 0x07E7:
                self.log.warning(f"*** write_byte SCREEN: addr=${addr_int:04X}, data=${data & 0xFF:02X} ***")
            self.log.info("w")

    def read_word(self, address: Word) -> int:
        """
        Read a 16-bit word from RAM at location RAM[address].

        Costs 2 CPU cycles.

        Arguments:
        ---------
            address: the address to read from

        Returns:
        -------
            int: the 16-bit value located in memory at RAM[address:address+1]
        """
        lowbyte: int = self.ram[int(address)]
        self.spend_cpu_cycles(cost=1)
        highbyte: int = self.ram[int(address) + 1]
        self.spend_cpu_cycles(cost=1)
        data = (highbyte << 8) + lowbyte
        if self.verbose_cycles:
            memory_section = self.ram.memory_section(address=address)
            self.log.info("rr")
            self.log.debug(f"read_word({memory_section}[0x{address:02x}]): 0x{data:04X} ({data})")
        return data

    def read_word_zeropage(self, address: Byte) -> int:
        """
        Read a 16-bit word from zero page at location RAM[address].

        Handles zero page wrap: if address is 0xFF, highbyte comes from 0x00.

        Costs 2 CPU cycles.

        VARIANT: 6502 - Zero page wrap at 0xFF boundary (reads 0xFF and 0x00)
        VARIANT: 65C02 - Same behavior as 6502
        VARIANT: 65C816 - Same behavior in emulation mode

        Arguments:
        ---------
            address: the zero page address to read from (0x00-0xFF)

        Returns:
        -------
            int: the 16-bit value located in memory at RAM[address:address+1]
        """
        lowbyte: int = self.ram[int(address) & 0xFF]
        self.spend_cpu_cycles(cost=1)
        highbyte: int = self.ram[(int(address) + 1) & 0xFF]
        self.spend_cpu_cycles(cost=1)
        data = (highbyte << 8) + lowbyte
        if self.verbose_cycles:
            self.log.info("rr")
            self.log.debug(f"read_word(zeropage[0x{address & 0xFF:02x}]): 0x{data:04X} ({data})")
        return data

    def peek_word(self, address: Word) -> int:
        """
        Read a 16-bit word from RAM at location RAM[address].

        Doesn't use CPU cycles.

        Arguments:
        ---------
            address: the address to read from

        Returns:
        -------
            int: the 16-bit value located in memory at RAM[address:address+1]
        """
        lowbyte: int = self.ram[int(address)]
        highbyte: int = self.ram[int(address) + 1]
        return (highbyte << 8) + lowbyte

    def write_word(self, address: Word, data: Word) -> None:
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
        self.spend_cpu_cycles(cost=1)
        self.ram[address + 1] = highbyte
        self.spend_cpu_cycles(cost=1)
        if self.verbose_cycles:
            self.log.info("ww")

    def read_register(self, register_name: str) -> Union[Byte, Word]:
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

    def write_register(self, register_name: str, data: int) -> None:
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

    def write_register_to_ram(self, register_name: str, address: int) -> None:
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

    def write_ram_to_register(self, address: int, register_name: str) -> None:
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

    def set_store_status_flags(self, register_name: str) -> None:
        """
        Set the status flags for store operations.

        Arguments:
        ---------
            register_name: the name of th register to read to determine status
        """
        # No flag modifications for store instructions

    def set_load_status_flags(self, register_name: str) -> None:
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

    def fetch_zeropage_mode_address(self, offset_register_name: str) -> int:
        """
        Read from RAM @ RAM:ZEROPAGE[PC].

        Increases PC by 1.

        Costs 1 CPU cycle.

        Arguments:
        ---------
            register_name: the name of the register to fetch

        Returns:
        -------
            int: the zeropage address (0x00-0xFF)
        """
        zeropage_address: int = self.fetch_byte()

        if offset_register_name is not None:
            offset_register_value: int = getattr(self, offset_register_name)
            # Zeropage addressing wraps at 0xFF boundary
            zeropage_address = (zeropage_address + offset_register_value) & 0xFF

        return zeropage_address

    def fetch_immediate_mode_address(self) -> int:
        """
        Read from RAM @ RAM[PC].

        Increases PC by 1.

        Costs 1 CPU cycle.

        Returns:
        -------
            int: the byte value at PC
        """
        data: int = self.fetch_byte()

        return data

    def fetch_absolute_mode_address(self, offset_register_name: str) -> int:
        """
        Read from RAM @ RAM[(PC:PC + 1)].

        Increases PC by 2.

        Costs 2 CPU cycles.

        Arguments:
        ---------
            register_name: the name of the register to fetch

        Returns:
        -------
            int: the computed address
        """
        address: int = self.fetch_word()

        if offset_register_name is not None:
            offset_register_value: int = getattr(self, offset_register_name)
            # Check for page boundary crossing (extra cycle if high byte changes)
            page_crossed = (address & 0xFF) + offset_register_value > 0xFF
            address = (address + offset_register_value) & 0xFFFF

            if page_crossed:
                if self.verbose_cycles:
                    self.log.info("o")
                self.spend_cpu_cycles(1)

        return address

    def fetch_indexed_indirect_mode_address(self) -> int:
        """
        Read from RAM @ RAM[(PC:PC + 1) + X].

        Increases PC by 1.

        Costs 3 CPU cycles.

        Arguments:
        ---------
            register_name: the name of the register to fetch

        Returns:
        -------
            int: the computed address
        """
        indirect_address: int = self.fetch_byte()
        offset_register_value: int = self.X

        # Use read_word_zeropage to handle zero page wrap at 0xFF boundary
        address: int = self.read_word_zeropage((indirect_address + offset_register_value) & 0xFF)

        return address

    def fetch_indirect_indexed_mode_address(self) -> int:
        """
        Read from RAM @ RAM:[ZEROPAGE[PC] << 8 + ZEROPAGE[PC + 1] + Y.

        Increases PC by 1.

        Costs 3 CPU cycles.

        Arguments:
        ---------
            register_name: the name of the register to fetch

        Returns:
        -------
            int: the computed address
        """
        indirect_address: int = self.fetch_byte()
        offset_register_value: int = self.Y

        # Use read_word_zeropage to handle zero page wrap at 0xFF boundary
        absolute_address: int = self.read_word_zeropage(indirect_address)

        # Check for page boundary crossing (extra cycle if high byte changes)
        page_crossed = (absolute_address & 0xFF) + offset_register_value > 0xFF
        address: int = (absolute_address + offset_register_value) & 0xFFFF

        if page_crossed:
            if self.verbose_cycles:
                self.log.info("o")
            self.spend_cpu_cycles(1)

        return address

    def execute_load_immediate(self, instruction: instructions.InstructionSet,
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

    def execute_store_zeropage(self, instruction: instructions.InstructionSet,
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

    def execute_load_zeropage(self, instruction: instructions.InstructionSet,
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

    def execute_store_absolute(self, instruction: instructions.InstructionSet,
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

    def execute_load_absolute(self, instruction: instructions.InstructionSet,
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

    def execute_store_indexed_indirect(self, instruction: instructions.InstructionSet,
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

    def execute_load_indexed_indirect(self, instruction: instructions.InstructionSet,
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

    def execute_store_indirect_indexed(self, instruction: instructions.InstructionSet,
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

    def execute_load_indirect_indexed(self, instruction: instructions.InstructionSet,
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

    def _adc_bcd(self, a: int, value: int, carry_in: int) -> Tuple[int, int, int, int]:
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

    def _sbc_bcd(self, a: int, value: int, carry_in: int) -> Tuple[int, int, int, int]:
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

    def execute(self, cycles: int = None, max_instructions: int = None) -> int:  # noqa: C901
        """
        Fetch and execute CPU instructions.

        Can be controlled by either cycle count or instruction count:
        - cycles: Run until approximately this many cycles consumed (may overshoot
          by up to one instruction's worth to maintain atomicity)
        - max_instructions: Run at most this many instructions (precise control)

        If both are specified, stops when either limit is reached.
        If neither is specified, runs 1 instruction.
        Instructions are always atomic - they complete fully before checking limits.

        Arguments:
        ---------
            cycles: the number of cycles to execute. Use mos6502.core.INFINITE_CYCLES
                for long running programs.
            max_instructions: the maximum number of instructions to execute.

        Returns:
        -------
            The number of cycles executed.
        """
        # Determine execution mode
        use_instruction_limit = False
        if max_instructions is not None:
            # Instruction-based control - set cycles to infinite so timing still works
            # but cycle exhaustion won't trigger
            self.instructions_remaining = max_instructions
            self.cycles = INFINITE_CYCLES
            use_instruction_limit = True
        elif cycles is not None:
            # Cycle-based control - set cycles (instructions are atomic, may overshoot)
            self.cycles = cycles
        else:
            # Default: run 1 cycle (backward compatible)
            self.cycles = 1

        # Cache frequently accessed attributes as local variables for speed
        # These are looked up on every iteration, so caching saves attribute access overhead
        verbose_cycles = self.verbose_cycles
        periodic_callback = self.periodic_callback
        periodic_callback_interval = self.periodic_callback_interval
        pre_instruction_callback = self.pre_instruction_callback
        post_instruction_callback = self.post_instruction_callback
        opcode_handler_cache = self._opcode_handler_cache

        # Cache method references to avoid repeated lookups
        fetch_byte = self.fetch_byte
        handle_nmi = self._handle_nmi
        handle_irq = self._handle_irq

        # Cache counters that are only modified in this loop (not by handlers)
        # Write them back before any exception/return
        instructions_executed = self.instructions_executed
        instructions_remaining = self.instructions_remaining if use_instruction_limit else 0

        # Pre-compute whether we can use the fast path (no debug/callbacks)
        use_fast_path = not (verbose_cycles or pre_instruction_callback or post_instruction_callback)

        while True:
            # Check if CPU is halted (by JAM instruction)
            # Halted CPU cannot execute until reset
            if self.halted:
                # Write back cached counters before raising exception
                self.instructions_executed = instructions_executed
                if use_instruction_limit:
                    self.instructions_remaining = instructions_remaining
                raise errors.CPUHaltError(
                    opcode=0x00,  # Unknown - set by JAM instruction
                    address=int(self.PC),
                    message="CPU is halted. Call reset() to recover."
                )

            # Check for cycle exhaustion BEFORE fetching the next instruction
            # This prevents PC from being incremented into the next instruction
            # when we don't have enough cycles to execute it
            if self.cycles <= 0:
                # Write back cached counters before raising exception
                self.instructions_executed = instructions_executed
                if use_instruction_limit:
                    self.instructions_remaining = instructions_remaining
                raise errors.CPUCycleExhaustionError(
                    f"Exhausted available CPU cycles after {self.cycles_executed} "
                    f"executed cycles with {self.cycles} remaining.",
                )

            # Check instruction limit if using instruction-based control
            if use_instruction_limit and instructions_remaining <= 0:
                # Write back cached counters before raising exception
                self.instructions_executed = instructions_executed
                self.instructions_remaining = instructions_remaining
                raise errors.CPUCycleExhaustionError(
                    f"Executed requested instructions after {self.cycles_executed} cycles.",
                )

            instruction_byte: int = fetch_byte()

            # Fast path: use opcode -> handler table when no debug/callbacks needed
            # Direct list indexing is faster than dict.get() - no hash computation
            # Uses pre-computed use_fast_path and cached opcode_handler_cache
            if use_fast_path:
                handler = opcode_handler_cache[instruction_byte]
                if handler is not None:
                    handler(self)
                    instructions_executed += 1
                    if use_instruction_limit:
                        instructions_remaining -= 1
                    if periodic_callback:
                        cycles_since_last = self.cycles_executed - self._last_periodic_callback_cycle
                        if cycles_since_last >= periodic_callback_interval:
                            self._last_periodic_callback_cycle = self.cycles_executed
                            periodic_callback()
                    # NMI check (edge-triggered, higher priority than IRQ)
                    if self.nmi_pending and not self._nmi_line_previous:
                        self._nmi_line_previous = True
                        handle_nmi()
                    elif not self.nmi_pending:
                        self._nmi_line_previous = False
                    # IRQ check (level-triggered, maskable)
                    if self.irq_pending and not self.I:
                        handle_irq()
                    continue

            # Slow path: need full instruction lookup for cache miss, verbose, or callbacks
            instruction = instructions.OPCODE_LOOKUP.get(instruction_byte, instruction_byte)

            # Verbose instruction tracing (only when verbose_cycles is enabled)
            # This entire block is for debug output and NOT needed for execution
            if verbose_cycles:
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
            # Legal instructions are InstructionOpcode objects with package/function metadata
            if isinstance(instruction, instructions.InstructionOpcode):
                # Get handler from pre-built table (faster) or load if somehow missing
                handler = opcode_handler_cache[instruction_byte]
                if handler is None:
                    handler = self._load_variant_handler(instruction.package, instruction.function)
                    opcode_handler_cache[instruction_byte] = handler

                # Pre-instruction callback (for debugging, profiling, breakpoints)
                if pre_instruction_callback:
                    pre_instruction_callback(self, instruction)

                handler(self)

                # Post-instruction callback (for debugging, profiling, state validation)
                if post_instruction_callback:
                    post_instruction_callback(self, instruction)
            else:
                # Illegal instruction - not in OPCODE_LOOKUP, just a raw byte
                self.log.error(f"ILLEGAL INSTRUCTION: {instruction} ({instruction:02X})")
                # Write back cached counters before raising exception
                self.instructions_executed = instructions_executed
                if use_instruction_limit:
                    self.instructions_remaining = instructions_remaining
                raise errors.IllegalCPUInstructionError(
                    f"Illegal instruction: 0x{int(instruction):02X}"
                )

            # Track total instructions executed (using cached local)
            instructions_executed += 1

            # Decrement instruction counter (for instruction-based execution control)
            if use_instruction_limit:
                instructions_remaining -= 1

            # Periodically call system update callback (e.g., VIC raster updates)
            # This allows external hardware to check cycle count and trigger IRQs
            # Use threshold check instead of modulo to avoid missing callbacks when
            # instructions don't land exactly on the interval boundary
            if periodic_callback:
                cycles_since_last = self.cycles_executed - self._last_periodic_callback_cycle
                if cycles_since_last >= periodic_callback_interval:
                    self._last_periodic_callback_cycle = self.cycles_executed
                    periodic_callback()

            # Check for pending NMI between instructions (after instruction completes)
            # NMI is edge-triggered and cannot be masked by the I flag
            # NMI has higher priority than IRQ
            if self.nmi_pending and not self._nmi_line_previous:
                self._nmi_line_previous = True  # Remember we've seen the edge
                handle_nmi()
            elif not self.nmi_pending:
                self._nmi_line_previous = False  # Reset edge detection when line goes high

            # Check for pending hardware IRQ between instructions (after instruction completes)
            # This is when the real 6502 samples the IRQ line
            if self.irq_pending and not self.I:
                handle_irq()

    def _handle_irq(self) -> None:
        """Handle a pending hardware IRQ.

        This implements the 6502 IRQ sequence:
        1. Push PC (2 bytes) to stack
        2. Push P (status register) to stack with B flag clear
        3. Set I flag to disable further interrupts
        4. Load PC from IRQ vector at $FFFE/$FFFF

        Total: 7 cycles

        Note: irq_pending is NOT cleared here. IRQ is level-triggered, meaning
        the /IRQ line stays asserted until the interrupt source (e.g., CIA)
        clears it when its ICR is read. The I flag being set prevents re-entry
        until RTI clears it. Software MUST acknowledge the interrupt.
        """

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
        # Bit 5 (unused) is always set to 1 when pushed
        status = (self._flags.value | 0x20) & ~0x10
        self.ram[self.S] = status
        self.S -= 1
        self.spend_cpu_cycles(1)

        # Set I flag to disable further interrupts
        self.I = 1

        # Load PC from IRQ vector at $FFFE/$FFFF
        irq_vector = self.read_word(0xFFFE)
        old_pc = self.PC
        self.PC = irq_vector

        self.log.info(f"*** IRQ HANDLER CALLED: PC ${old_pc:04X} -> ${irq_vector:04X}, I flag now set ***")

    def _handle_nmi(self) -> None:
        """Handle a pending NMI (Non-Maskable Interrupt).

        This implements the 6502 NMI sequence:
        1. Push PC (2 bytes) to stack
        2. Push P (status register) to stack with B flag clear
        3. Set I flag to disable further IRQ interrupts
        4. Load PC from NMI vector at $FFFA/$FFFB

        Unlike IRQ:
        - NMI uses vector $FFFA/$FFFB (not $FFFE/$FFFF)
        - NMI cannot be masked by the I flag
        - NMI is edge-triggered (handled by execute loop)

        Total: 7 cycles
        """
        # Clear the pending flag
        self.nmi_pending = False

        # Push PC to stack (high byte first)
        pc_high = (self.PC >> 8) & 0xFF
        pc_low = self.PC & 0xFF

        self.ram[self.S] = pc_high
        self.S -= 1
        self.spend_cpu_cycles(1)

        self.ram[self.S] = pc_low
        self.S -= 1
        self.spend_cpu_cycles(1)

        # Push status register with B flag CLEAR (hardware interrupt, not BRK)
        # Bit 5 (unused) is always set to 1 when pushed
        status = (self._flags.value | 0x20) & ~0x10
        self.ram[self.S] = status
        self.S -= 1
        self.spend_cpu_cycles(1)

        # Set I flag to disable further IRQ interrupts
        # (Note: This doesn't prevent another NMI, which is non-maskable)
        self.I = 1

        # Load PC from NMI vector at $FFFA/$FFFB
        nmi_vector = self.read_word(0xFFFA)
        old_pc = self.PC
        self.PC = nmi_vector

        self.log.info(f"*** NMI HANDLER CALLED: PC ${old_pc:04X} -> ${nmi_vector:04X}, I flag now set ***")

    def push_pc_to_stack(self) -> None:
        """Push the PC to the stack."""

    def reset(self) -> None:
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

        # Note: Real 6502 does NOT clear RAM on reset - RAM retains its contents
        # RAM initialization (if needed) should be done before calling reset()
        # or during power-on in the system emulator (e.g., C64.__init__)

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

        # Clear halted flag - CPU can execute again after reset
        self.halted = False

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
    def flags(self) -> Byte:
        """
        Return the CPU flags register.

        Returns
        -------
            Byte()
        """
        return self._flags

    @flags.setter
    def flags(self, flags: int) -> None:
        """
        Set the CPU flags register.

        Arguments:
        ---------
            flags: Byte()

        Returns:
        -------
            None
        """
        if self.verbose_cycles:
            self.log.debug(f"Flags <- 0x{self._flags.flags:02X}")

        setattr(self._flags, flags)
    @property
    def PC(self) -> int:  # noqa: N802
        """
        Return the CPU PC register.

        Returns
        -------
            int (16-bit value)
        """
        if self.verbose_cycles:
            self.log.debug(f"PC <- 0x{self._registers.PC:04X}")
        return self._registers.PC

    @PC.setter
    def PC(self, PC: int) -> None:  # noqa: N802 N803
        """
        Set the CPU PC register.

        Arguments:
        ---------
            PC: int (16-bit value)

        Returns:
        -------
            None
        """
        self._registers.PC = PC & 0xFFFF
        if self.verbose_cycles:
            self.log.info(f"PC -> 0x{self._registers.PC:04X}")

        # Call PC change callback if set
        if self.pc_callback is not None:
            self.pc_callback(self._registers.PC)

    @property
    def S(self) -> int:  # noqa: N802
        """
        Return the CPU S register.

        This register is an 8-bit register, but we store it as 16-bits for convenience.

        This register must be masked with 0xFF when performing instruction offset calculations.

        Returns
        -------
            int (9-bit value: 0x0100-0x01FF)
        """
        if self.verbose_cycles:
            self.log.debug(f"S <- 0x{self._registers.S:02X} ")
        return self._registers.S

    @S.setter
    def S(self, S: int) -> None:  # noqa: N802 N803
        """
        Set the CPU S register.

        The 6502 stack pointer is 8 bits and always addresses page 1 (0x0100-0x01FF).
        The low byte wraps at 0xFF boundary, but the high byte is always 0x01.

        Arguments:
        ---------
            S: int (low byte used, always OR'd with 0x0100)

        Returns:
        -------
            None
        """
        # Stack pointer is 8 bits, always in page 1 (0x0100-0x01FF)
        # Mask to 8 bits and force page 1
        self._registers.S = 0x0100 | (S & 0xFF)
        if self.verbose_cycles:
            self.log.info(f"S -> 0x{self._registers.S & 0xFF:02X}")

    @property
    def A(self) -> int:  # noqa: N802
        """
        Return the CPU A register.

        Returns
        -------
            int (8-bit value)
        """
        if self.verbose_cycles:
            self.log.debug(f"A <- 0x{self._registers.A:02X}")
        return self._registers.A

    @A.setter
    def A(self, A: int) -> None:  # noqa: N802 N803
        """
        Set the CPU A register.

        Arguments:
        ---------
            A: int (8-bit value)

        Returns:
        -------
            None
        """
        self._registers.A = A & 0xFF
        if self.verbose_cycles:
            self.log.info(f"A -> 0x{self._registers.A:02X}")

    @property
    def X(self) -> int:  # noqa: N802
        """
        Return the CPU X register.

        Returns
        -------
            int (8-bit value)
        """
        if self.verbose_cycles:
            self.log.debug(f"X <- 0x{self._registers.X:02X}")
        return self._registers.X

    @X.setter
    def X(self, X: int) -> None:  # noqa: N802 N803
        """
        Set the CPU X register.

        Arguments:
        ---------
            X: int (8-bit value)

        Returns:
        -------
            None
        """
        self._registers.X = X & 0xFF
        if self.verbose_cycles:
            self.log.info(f"X -> 0x{self._registers.X:02X}")

    @property
    def Y(self) -> int:  # noqa: N802
        """
        Return the CPU Y register.

        Returns
        -------
            int (8-bit value)
        """
        if self.verbose_cycles:
            self.log.debug(f"Y <- 0x{self._registers.Y:02X}")
        return self._registers.Y

    @Y.setter
    def Y(self, Y: int) -> None:  # noqa: N802 N803
        """
        Set the CPU Y register.

        Arguments:
        ---------
            Y: int (8-bit value)

        Returns:
        -------
            None
        """
        self._registers.Y = Y & 0xFF
        if self.verbose_cycles:
            self.log.info(f"Y -> 0x{self._registers.Y:02X}")

    def __str__(self) -> str:
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
