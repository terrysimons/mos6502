#!/usr/bin/env python3
"""CPU core for the mos6502."""

import contextlib
import logging
from typing import TYPE_CHECKING, Literal, Self

from bitarray.util import ba2int

from mos6502 import exceptions
from mos6502 import flags
from mos6502 import instructions
from mos6502 import memory
from mos6502 import registers
from mos6502.memory import Byte
from mos6502.memory import RAM
from mos6502.memory import Word

if TYPE_CHECKING:
    from mos6502.registers import Registers


INFINITE_CYCLES: Literal[4294967295] = 0xFFFFFFFF


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

    def __init__(self: Self) -> Self:
        """Instantiate a mos6502 CPU core."""
        super().__init__()
        self.endianness: str = "little"

        # As a convenience for code simplification we can set the default endianness
        # for newly created Byte/Word/etc... objects here
        memory.ENDIANNESS = self.endianness

        self._registers: Registers = registers.Registers(endianness=self.endianness)
        self._flags: Byte = Byte()
        self.ram: RAM = RAM(endianness=self.endianness)
        self.cycles = 0
        self.cycles_executed: Literal[0] = 0

    def __enter__(self: Self) -> Self:
        """With entrypoint."""
        return self

    def __exit__(self: Self, *args: list, **kwargs: dict) -> None:
        """With exitpoint."""

    def tick(self: Self, cycles: int) -> int:
        """
        Tick {cycles} cycles.

        Raises mos6502.exceptions.CPUCycleExhaustionError if the cycles parameter passed
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
                raise exceptions.CPUCycleExhaustionError(
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

        Increments self.PC by 1.

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

    def execute(self: Self, cycles: int = 1) -> int:  # noqa: C901, PLR0915
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
            if self.cycles <= 0:
                raise exceptions.CPUCycleExhaustionError(
                    f"Exhausted available CPU cycles after {self.cycles_executed} "
                    f"executed cycles with {self.cycles} remaining.",
                )

            instruction: Byte = self.fetch_byte()

            # self.log.debug(

            instruction_bytes: int = 0

            machine_code = []
            operand: memory.MemoryUnit = 0
            assembly = ""
            instruction_cycle_count: int = 0
            if instruction.value in instructions.InstructionSet.map:
                instruction_map: int = instructions.InstructionSet.map[instruction.value]

                instruction_bytes: int = int(instruction_map["bytes"])

                instruction_cycle_count = instruction_map["cycles"]

                with contextlib.suppress(ValueError):
                    instruction_cycle_count: int = int(instruction_map["cycles"])

                # Subtract 1 for the instruction
                for i in range(instruction_bytes - 1):
                    machine_code.append(int(self.ram[self.PC + i]))

                if len(machine_code) > 2:
                    raise exceptions.MachineCodeExecutionException(
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

            match instruction:
                # ''' Execute ADC '''
                case instructions.ADC_IMMEDIATE_0x69:
                    pass
                case instructions.ADC_ZEROPAGE_0x65:
                    pass
                case instructions.ADC_ZEROPAGE_X_0x75:
                    pass
                case instructions.ADC_ABSOLUTE_0x6D:
                    pass
                case instructions.ADC_ABSOLUTE_X_0x7D:
                    pass
                case instructions.ADC_ABSOLUTE_Y_0x79:
                    pass
                case instructions.ADC_INDEXED_INDIRECT_X_0x61:
                    pass
                case instructions.ADC_INDIRECT_INDEXED_Y_0x71:
                    pass

                # ''' Execute AND '''

                # ''' Execute ASL '''

                # ''' Execute BBC '''

                # ''' Execute BCS '''

                # ''' Excecute BEQ '''

                # ''' Execute BIT '''

                # BMI
                # BNE
                # BPL
                # ''' Execute BRK '''
                case instructions.BRK_IMPLIED_0x00:
                    # VARIANT: 6502 - D (decimal) flag is NOT cleared by BRK or any interrupt (IRQ, NMI, RESET)
                    # VARIANT: 6502A - D (decimal) flag is NOT cleared by BRK or any interrupt (IRQ, NMI, RESET)
                    # VARIANT: 65C02 - D (decimal) flag IS cleared by BRK and all interrupts (IRQ, NMI, RESET)
                    # This implementation follows the NMOS 6502/6502A behavior (does not clear D flag)

                    # BRK pushes PC+2, then SR (with B flag set), then sets I flag
                    # Total: 7 cycles (1 for fetch + 2 for write_word + 1 for write_byte + 3 for overhead)
                    # BRK is documented as pushing PC+2, but after fetch_byte(), PC is already +1
                    # So we push PC (current value, which is already original PC+1)
                    self.write_word(address=self.S - 1, data=self.PC)
                    self.S -= 2

                    # Push status register with B flag set
                    # Create a copy of flags with B flag set
                    status_with_break: Byte = Byte(self._flags.value | (1 << flags.B))
                    self.write_byte(address=self.S, data=status_with_break)
                    self.S -= 1

                    # Set interrupt disable flag
                    self.I = flags.ProcessorStatusFlags.I[flags.I]

                    # Load PC from IRQ vector at 0xFFFE/0xFFFF
                    # (In a real system, this would jump to the interrupt handler)
                    # For our emulator, we'll raise an exception instead
                    # We've spent 4 cycles so far (1 fetch + 2 write_word + 1 write_byte)
                    # Need 3 more to total 7
                    self.spend_cpu_cycles(cost=3)

                    self.log.info("i")
                    self.log.debug(f"{instructions.InstructionSet(int(instruction)).name}")

                    raise exceptions.CPUBreakError(
                        f"BRK instruction executed at PC=0x{self.PC - 1:04X}",
                    )

                # BVC
                # BVS
                # CLC
                case instructions.CLC_IMPLIED_0x18:
                    self.C = 0
                    self.log.info("i")
                    self.spend_cpu_cycles(1)

                # CLD
                case instructions.CLD_IMPLIED_0xD8:
                    self.D = 0
                    self.log.info("i")
                    self.spend_cpu_cycles(1)

                # CLI
                case instructions.CLI_IMPLIED_0x58:
                    self.I = 0
                    self.log.info("i")
                    self.spend_cpu_cycles(1)

                # CLV
                case instructions.CLV_IMPLIED_0xB8:
                    self.V = 0
                    self.log.info("i")
                    self.spend_cpu_cycles(1)

                # SEC
                case instructions.SEC_IMPLIED_0x38:
                    self.C = 1
                    self.log.info("i")
                    self.spend_cpu_cycles(1)

                # SED
                case instructions.SED_IMPLIED_0xF8:
                    self.D = 1
                    self.log.info("i")
                    self.spend_cpu_cycles(1)

                # SEI
                case instructions.SEI_IMPLIED_0x78:
                    self.I = 1
                    self.log.info("i")
                    self.spend_cpu_cycles(1)

                # TAX
                case instructions.TAX_IMPLIED_0xAA:
                    self.X = self.A
                    self.set_load_status_flags(register_name="X")
                    self.log.info("i")
                    self.spend_cpu_cycles(1)

                # TAY
                case instructions.TAY_IMPLIED_0xA8:
                    self.Y = self.A
                    self.set_load_status_flags(register_name="Y")
                    self.log.info("i")
                    self.spend_cpu_cycles(1)

                # TSX
                case instructions.TSX_IMPLIED_0xBA:
                    self.X = self.S & 0xFF
                    self.set_load_status_flags(register_name="X")
                    self.log.info("i")
                    self.spend_cpu_cycles(1)

                # TXA
                case instructions.TXA_IMPLIED_0x8A:
                    self.A = self.X
                    self.set_load_status_flags(register_name="A")
                    self.log.info("i")
                    self.spend_cpu_cycles(1)

                # TXS
                case instructions.TXS_IMPLIED_0x9A:
                    self.S = 0x100 | self.X
                    self.log.info("i")
                    self.spend_cpu_cycles(1)

                # TYA
                case instructions.TYA_IMPLIED_0x98:
                    self.A = self.Y
                    self.set_load_status_flags(register_name="A")
                    self.log.info("i")
                    self.spend_cpu_cycles(1)

                # CMP
                # CPX
                # CPY
                # DEC

                # DEX
                case instructions.DEX_IMPLIED_0xCA:
                    self.X = (self.X - 1) & 0xFF
                    self.set_load_status_flags(register_name="X")
                    self.log.info("i")
                    self.spend_cpu_cycles(1)

                # DEY
                case instructions.DEY_IMPLIED_0x88:
                    self.Y = (self.Y - 1) & 0xFF
                    self.set_load_status_flags(register_name="Y")
                    self.log.info("i")
                    self.spend_cpu_cycles(1)

                # EOR
                # INC

                # INX
                case instructions.INX_IMPLIED_0xE8:
                    self.X = (self.X + 1) & 0xFF
                    self.set_load_status_flags(register_name="X")
                    self.log.info("i")
                    self.spend_cpu_cycles(1)

                # INY
                case instructions.INY_IMPLIED_0xC8:
                    self.Y = (self.Y + 1) & 0xFF
                    self.set_load_status_flags(register_name="Y")
                    self.log.info("i")
                    self.spend_cpu_cycles(1)

                # JMP
                case instructions.JMP_ABSOLUTE_0x4C:
                    jump_address: Word = self.fetch_word()
                    self.PC = jump_address
                    self.log.info("i")
                    # No additional cycles - fetch_word already spent 2

                case instructions.JMP_INDIRECT_0x6C:
                    indirect_address: Word = self.fetch_word()

                    # VARIANT: 6502/6502A - Page boundary bug
                    # If indirect_address is 0xXXFF, the 6502 wraps within the page
                    # instead of crossing to the next page for the high byte.
                    # Example: JMP ($10FF) reads low byte from $10FF and high byte
                    # from $1000 (not $1100 as expected).
                    # VARIANT: 65C02 - Bug fixed, correctly reads across page boundary

                    if (indirect_address & 0xFF) == 0xFF:
                        # Page boundary bug: wrap within same page
                        low_byte: Byte = self.read_byte(address=indirect_address)
                        high_byte: Byte = self.read_byte(address=indirect_address & 0xFF00)
                        jump_address: Word = Word((high_byte << 8) | low_byte)
                    else:
                        # Normal case: read word normally
                        jump_address: Word = self.read_word(address=indirect_address)

                    self.PC = jump_address
                    self.log.info("i")
                    # No additional cycles - fetch_word already spent 2, read operations spent 2

                # ''' Execute JSR '''
                case instructions.JSR_ABSOLUTE_0x20:
                    subroutine_address: Word = self.fetch_word()

                    # The stack is top-down, so starts at 0x1FF, so we need to
                    # write to S - 1
                    self.write_word(address=self.S - 1, data=self.PC + 1)

                    # Since we wrote a word, we need to decrement by 2
                    # so our stack pointer would be 0xFD if it started at 0xFF here
                    self.S -= 2
                    self.PC = subroutine_address
                    self.spend_cpu_cycles(cost=1)

                    self.log.info("i")

                    self.log.debug(
                        f"{instructions.InstructionSet(int(instruction)).name}: "
                        f"{hex(subroutine_address)}",
                    )

                # ''' Execute Load Immediate '''
                case instructions.LDA_IMMEDIATE_0xA9:
                    self.execute_load_immediate(
                        instruction=instruction,
                        register_name="A",
                    )

                case instructions.LDX_IMMEDIATE_0xA2:
                    self.execute_load_immediate(
                        instruction=instruction,
                        register_name="X",
                    )

                case instructions.LDY_IMMEDIATE_0xA0:
                    self.execute_load_immediate(
                        instruction=instruction,
                        register_name="Y",
                    )

                # ''' Execute Load Zero Page '''
                case instructions.LDA_ZEROPAGE_0xA5:
                    self.execute_load_zeropage(
                        instruction=instruction,
                        register_name="A",
                        offset_register_name=None,
                    )

                case instructions.LDX_ZEROPAGE_0xA6:
                    self.execute_load_zeropage(
                        instruction=instruction,
                        register_name="X",
                        offset_register_name=None,
                    )

                case instructions.LDY_ZEROPAGE_0xA4:
                    self.execute_load_zeropage(
                        instruction=instruction,
                        register_name="Y",
                        offset_register_name=None,
                    )

                # ''' Execute Load Zero Page X '''
                case instructions.LDY_ZEROPAGE_X_0xB4:
                    self.execute_load_zeropage(
                        instruction=instruction,
                        register_name="Y",
                        offset_register_name="X",
                    )

                case instructions.LDA_ZEROPAGE_X_0xB5:
                    self.execute_load_zeropage(
                        instruction=instruction,
                        register_name="A",
                        offset_register_name="X",
                    )

                # ''' Execute Load Zero Page Y '''
                case instructions.LDX_ZEROPAGE_Y_0xB6:
                    self.execute_load_zeropage(
                        instruction=instruction,
                        register_name="X",
                        offset_register_name="Y",
                    )

                # ''' Execute Loada Absolute '''
                case instructions.LDA_ABSOLUTE_0xAD:
                    self.execute_load_absolute(
                        instruction=instruction,
                        register_name="A",
                        offset_register_name=None,
                    )

                case instructions.LDX_ABSOLUTE_0xAE:
                    self.execute_load_absolute(
                        instruction=instruction,
                        register_name="X",
                        offset_register_name=None,
                    )

                case instructions.LDY_ABSOLUTE_0xAC:
                    self.execute_load_absolute(
                        instruction=instruction,
                        register_name="Y",
                        offset_register_name=None,
                    )

                case instructions.LDA_ABSOLUTE_X_0xBD:
                    self.execute_load_absolute(
                        instruction=instruction,
                        register_name="A",
                        offset_register_name="X",
                    )

                case instructions.LDA_ABSOLUTE_Y_0xB9:
                    self.execute_load_absolute(
                        instruction=instruction,
                        register_name="A",
                        offset_register_name="Y",
                    )

                case instructions.LDX_ABSOLUTE_Y_0xBE:
                    self.execute_load_absolute(
                        instruction=instruction,
                        register_name="X",
                        offset_register_name="Y",
                    )

                case instructions.LDY_ABSOLUTE_X_0xBC:
                    self.execute_load_absolute(
                        instruction=instruction,
                        register_name="Y",
                        offset_register_name="X",
                    )

                # ''' Execute Indexed Indirect '''
                case instructions.LDA_INDEXED_INDIRECT_X_0xA1:
                    self.execute_load_indexed_indirect(
                        instruction=instruction,
                        register_name="A",
                    )

                # ''' Execute Indirect Indexed'''
                case instructions.LDA_INDIRECT_INDEXED_Y_0xB1:
                    self.execute_load_indirect_indexed(
                        instruction=instruction,
                        register_name="A",
                    )

                # ''' LSR '''
                # NOP
                case instructions.NOP_IMPLIED_0xEA:
                    self.log.info("i")
                    self.spend_cpu_cycles(cost=1)
                # ORA
                # PHA
                # PHP
                # PLA
                # PLP
                # ROL
                # ROR
                # RTI
                # '''RTS'''
                case instructions.RTS_IMPLIED_0x60:
                    self.log.info("i")
                    self.spend_cpu_cycles(cost=1)
                    self.PC = self.read_word(address=self.S + 1)
                    self.S += 2
                # SBC
                # SEC
                # SED
                # SEI
                # ''' STA '''
                case instructions.STA_ZEROPAGE_0x85:
                    self.execute_store_zeropage(
                        instruction=instruction,
                        register_name="A",
                        offset_register_name=None,
                    )

                case instructions.STA_ZEROPAGE_X_0x95:
                    self.execute_store_zeropage(
                        instruction=instruction,
                        register_name="A",
                        offset_register_name="X",
                    )

                case instructions.STA_ABSOLUTE_0x8D:
                    self.execute_store_absolute(
                        instruction=instruction,
                        register_name="A",
                        offset_register_name=None,
                    )

                case instructions.STA_ABSOLUTE_X_0x9D:
                    self.execute_store_absolute(
                        instruction=instruction,
                        register_name="A",
                        offset_register_name="X",
                    )

                case instructions.STA_ABSOLUTE_Y_0x99:
                    self.execute_store_absolute(
                        instruction=instruction,
                        register_name="A",
                        offset_register_name="Y",
                    )

                case instructions.STA_INDEXED_INDIRECT_X_0x81:
                    self.execute_store_indexed_indirect(
                        instruction=instruction,
                        register_name="A",
                    )

                case instructions.STA_INDIRECT_INDEXED_Y_0x91:
                    self.execute_store_indirect_indexed(
                        instruction=instruction,
                        register_name="A",
                    )

                # ''' STX '''
                case instructions.STX_ABSOLUTE_0x8E:
                    self.execute_store_absolute(
                        instruction=instruction,
                        register_name="X",
                        offset_register_name=None,
                    )

                case instructions.STX_ZEROPAGE_0x86:
                    self.execute_store_zeropage(
                        instruction=instruction,
                        register_name="X",
                        offset_register_name=None,
                    )

                case instructions.STX_ZEROPAGE_Y_0x96:
                    self.execute_store_zeropage(
                        instruction=instruction,
                        register_name="X",
                        offset_register_name="Y",
                    )

                # ''' STY '''
                case instructions.STY_ABSOLUTE_0x8C:
                    self.execute_store_absolute(
                        instruction=instruction,
                        register_name="Y",
                        offset_register_name=None,
                    )

                case instructions.STY_ZEROPAGE_0x84:
                    self.execute_store_zeropage(
                        instruction=instruction,
                        register_name="Y",
                        offset_register_name=None,
                    )

                case instructions.STY_ZEROPAGE_X_0x94:
                    self.execute_store_zeropage(
                        instruction=instruction,
                        register_name="Y",
                        offset_register_name="X",
                    )

                # TAX
                # TAY
                # TSX
                # TXA
                # TXS
                # TYA

                # ''' Illegal Opcodes '''

                # ALR
                # ANC
                # ANC2
                # ANE
                # ARR
                # DCP
                # ISC
                # LAS
                # LAX
                # LXA
                # RLA
                # RRA
                # SAX
                # SBX
                # SHA
                # SHX
                # SHY
                # SLO
                # SRE
                # TAS
                # USBC
                # JAM

                # ''' Unhandled Instruction '''
                case _:
                    self.log.error(f"ILLEGAL INSTRUCTION: {instruction} ({instruction:02X})")

    def push_pc_to_stack(self: Self) -> None:
        """Push the PC to the stack."""

    def reset(self: Self) -> None:
        """
        Reset the CPU.

        It is necessary to call this method before executing instructions.

        The PC and S need to be set up.
        This also clears CPU flags and registers and initializes RAM to 0s.
        """
        self.log.info("Reset")
        self.PC: Word = Word(0xFFFC, endianness=self.endianness)
        self.S: Word = Word(0x01FF, endianness=self.endianness)

        # CPU Status Flags
        #
        # Note we use a full byte per status flag
        # to optimize the operations that occur
        # on them.  See flags.py
        self.C: Byte = Byte(0x00, endianness=self.endianness)
        self.Z: Byte = Byte(0x00, endianness=self.endianness)
        self.I: Byte = Byte(0x00, endianness=self.endianness)
        self.D: Byte = Byte(0x00, endianness=self.endianness)
        self.B: Byte = Byte(0x00, endianness=self.endianness)
        self.V: Byte = Byte(0x00, endianness=self.endianness)
        self.N: Byte = Byte(0x00, endianness=self.endianness)

        # 1 Byte Registers
        self.A: Byte = Byte(0x0, endianness=self.endianness)
        self.X: Byte = Byte(0x0, endianness=self.endianness)
        self.Y: Byte = Byte(0x0, endianness=self.endianness)

        self.ram.initialize()

    @property
    def flags(self: Self) -> Byte:
        """
        Return the CPU flags register.

        Returns
        -------
            Byte()
        """
        self.log.debug(f"Flags -> 0x{self._flags:02X}")
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
        self.log.info(f"PC -> 0x{self._registers.PC:04X}")
        self._registers.PC = Word(PC)

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
        self.log.info(f"S -> 0x{self._registers.S:02X}")
        self._registers.S = Word(S & 511)

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
        self.log.info(f"A -> 0x{self._registers.A:02X}")
        self._registers.A = A

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
        self.log.info(f"X -> 0x{self._registers.X:02X}")
        self._registers.X = X

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
        self.log.info(f"Y -> 0x{self._registers.Y:02X}")
        self._registers.Y = Y

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
        except exceptions.CPUCycleExhaustionError:
            log.info(f"Used: {cpu.cycles_executed} cycles")

        log.info(cpu)


if __name__ == "__main__":
    main()
