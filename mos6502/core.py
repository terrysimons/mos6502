#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CPU core for the mos6502."""

import logging

import bitarray
from bitarray.util import int2ba, ba2int

from mos6502.exceptions import CPUCycleExhaustionException
import mos6502.flags as flags
import mos6502.instructions as instructions
import mos6502.registers as registers
import mos6502.memory as memory
from mos6502.memory import Byte, Word, RAM

INFINITE_CYCLES = 0xFFFFFFFF


# https://www.pagetable.com/c64ref/6502/
# http://www.emulator101.com/6502-addressing-modes.html
# https://www.bigmessowires.com/2010/03/27/8-bit-cpu-comparison/
# https://www.youtube.com/watch?v=qJgsuQoy9bc
# http://www.visual6502.org/
# https://melodict.com/6502?fbclid=IwAR2L0JltG97b_F2gKzyu8IGyk_2JKKLUwHV7LQyrNHn4HMIyqLsSRBFyH3Y
# https://web.archive.org/web/20190410054640/http://obelisk.me.uk/6502/registers.html
class MOS6502CPU(flags.ProcessorStatusFlagsInterface):
    """mos6502CPU Core."""

    log: logging.Logger = logging.getLogger('mos6502.cpu')

    def __init__(self) -> None:
        """Instantiate a mos6502 CPU core."""
        super().__init__()
        self.endianness: str = 'little'

        # As a convenience for code simplification we can set the default endianness
        # for newly created Byte/Word/etc... objects here
        memory.ENDIANNESS = self.endianness

        self._registers = registers.Registers(endianness=self.endianness)
        self._flags: Byte = Byte()
        self.ram = RAM(endianness=self.endianness)
        self.cycles = 0
        self.cycles_executed = 0
        self.reset()

    def __enter__(self):
        """With entrypoint."""
        return self

    def __exit__(self, *args, **kwargs) -> None:
        """With exitpoint."""
        pass

    def tick(self, cycles) -> int:
        """
        Tick {cycles} cycles.

        Raises mos6502.exceptions.CPUCycleExhaustionException if the cycles parameter passed
        into the execute function is exhausted.

        Infinite cycles can be used by setting this to mos6502.core.INFINITE_CYCLES

        self.executed_cycles will have the # of executed cycles added to it.
        self.cycles will have {cycles} subtracted from it.

        Arguments:
            cycles: the number of CPU cycles to execute before raising an exception.

        Returns:
            The number of cycles remaining.
        """
        for i in range(cycles):
            if self.cycles <= 0:
                raise CPUCycleExhaustionException(
                    f'Exhausted available CPU cycles after {self.cycles_executed} executed cycles.'
                )

            self.cycles_executed += 1

            if self.cycles != INFINITE_CYCLES:
                self.cycles -= 1
                self.log.debug(
                    f'TICK: Executed Cycles: {self.cycles_executed}, '
                    f'Remaining Cycles: {self.cycles}'
                )
            else:
                self.log.debug(
                    f'TICK: Executed Cycles: {self.cycles_executed}, '
                    f'Remaining Cycles: INFINITE'
                )

        return self.cycles

    def spend_cpu_cycles(self, cost) -> None:
        """
        Tick the CPU and spend {cost} cycles.

        It's much easier to think about the cycle cost this way.

        Arguments:
            cost: the number of cycles to consume
        """
        self.tick(cost)

    def fetch_byte(self) -> Byte:
        """
        Fetch a Byte() from RAM[self.PC].

        Increments self.PC by 1.

        Costs 1 CPU cycle.

        Returns:
            a Byte() set to the value located in memory at self.PC
        """
        addr: Word = self.PC
        byte: Byte = self.ram[self.PC]
        self.PC += 1
        self.spend_cpu_cycles(cost=1)

        self.log.debug(
            f'Fetch Byte: [{hex(addr)}:{hex(addr)}] '
            f'Byte: 0x{byte:02x} ({byte}) '
            f'lowbyte=0x{byte:02x}@0x{addr:02x} highbyte={None}'
        )

        return Byte(value=byte, endianness=self.endianness)

    def fetch_word(self) -> Word:
        """
        Fetch a Word() from RAM[self.PC].

        Increments self.PC by 1.

        Costs 2 CPU cycles.

        Returns:
            a Word() set to the value located in memory at RAM[self.PC:self.PC + 1]
        """
        addr1: Word = self.PC
        lowbyte: Byte = self.ram[self.PC]
        self.spend_cpu_cycles(cost=1)

        self.PC = self.PC + 1
        addr2: Word = self.PC
        highbyte: Byte = self.ram[self.PC]
        self.spend_cpu_cycles(cost=1)

        word = (highbyte << 8) + lowbyte

        self.log.debug(
            'Fetch Word: ['
            f'{hex(addr2)}:'
            f'{hex(addr1)}], '
            f'Word: 0x{word:02x} ({word}) '
            f'highbyte={lowbyte:02x}@0x{addr1:02x} lowbyte={highbyte:02x}@0x{addr2:02x}'
        )

        return Word(value=word, endianness=self.endianness)

    def read_byte(self, address: Word) -> Byte:
        """
        Read a Byte() from RAM at location RAM[address].

        Costs 1 CPU cycle.

        Arguments:
            address: the address to read from

        Returns:
            a Byte() set to the value located in memory at RAM[address]
        """
        memory_section = self.ram.memory_section(address=address)
        data: Byte = self.ram[int(address)]
        self.spend_cpu_cycles(cost=1)
        self.log.debug(f'read_byte({memory_section}[0x{address:02x}]): {data}')
        return data

    def write_byte(self, address: Word, data: Byte) -> Byte:
        """
        Write a Byte() to RAM at location RAM[address].

        Costs 1 CPU cycle.

        Arguments:
            address: the address to write to
            data: the Byte() to write

        Returns:
            None
        """
        self.ram[address] = 0xFF & data
        self.spend_cpu_cycles(cost=1)

    def read_word(self, address: Word) -> Word:
        """
        Read a Word() from RAM at location RAM[address].

        Costs 2 CPU cycles.

        Arguments:
            address: the address to read from

        Returns:
            a Byte() set to the value located in memory at RAM[address]
        """
        memory_section = self.ram.memory_section(address=address)
        lowbyte: Byte = self.ram[int(address)]
        self.spend_cpu_cycles(cost=1)
        highbyte: Byte = self.ram[int(address) + 1]
        self.spend_cpu_cycles(cost=1)
        data = (int(highbyte) << 8) + int(lowbyte)
        self.log.debug(f'read_word({memory_section}[0x{address:02x}]): {data}')
        return Word(data, endianness=self.endianness)

    def write_word(self, address: Word, data: Word) -> None:
        """
        Write a Word() to RAM at location RAM[address].

        Costs 2 CPU cycles.

        Arguments:
            address: the address to write to
            data: the Word() to write

        Returns:
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

    def set_load_status_flags(self, register_name) -> None:
        """Set the status flags for load operations.

        Arguments:
            register_name: the name of th register to read to determine status
        """
        register: Byte = getattr(self, register_name)
        self.Z = flags.ProcessorStatusFlags.Z[flags.Z] \
            if (register == 0x0) else not flags.ProcessorStatusFlags.Z[flags.Z]

        # Set negative flag if bit 7 of A is set
        self.N = flags.ProcessorStatusFlags.N[flags.N] \
            if (register & 128) else not flags.ProcessorStatusFlags.N[flags.N]

    def execute_load_immediate(self, instruction, register_name) -> None:
        """
        Instruction execution for "immediate LD[A, X, Y] #oper".

        Executes Load Immediate on {register_name} for {instruction}.

        Arguments:
            instruction: the load immediate instruction to execute
            register_name: the register to load to

        Returns:
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

        setattr(self, register_name, self.fetch_byte())
        self.set_load_status_flags(register_name=register_name)

        self.log.debug(
            f'{instructions.InstructionSet(instruction).name}: '
            f'{Byte(value=getattr(self, register_name))}'
        )

    def execute_load_zeropage(self, instruction, register_name, offset_register_name) -> None:
        """
        Instruction execution for load zeropage.

        "zeropage LD[A, X, Y] oper" and "zeropage LD[A, X, Y],[X, Y] oper".

        Executes Load Zeropage on {register_name} for {instruction} using {offset_register_name}.

        Arguments:
            instruction: the load immediate instruction to execute
            register_name: the register to load to
            offset_register_name: the offset register to use for any offset operations.

        Returns:
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
        register: Byte = getattr(self, register_name)
        zeropage_address: Byte | None = self.fetch_byte()

        offset_register_value = 0
        address: Byte = zeropage_address + offset_register_value

        if offset_register_name is not None:
            offset_register_value = getattr(self, offset_register_name)

            # This needs to wrap, so mask by 0xFF
            address: Byte = zeropage_address + offset_register_value

        setattr(self, register_name, self.read_byte(address=address))

        self.set_load_status_flags(register_name=register_name)

        self.log.debug(f'{instructions.InstructionSet(instruction).name}: {Byte(value=register)}')

    def execute_load_absolute(self, instruction, register_name, offset_register_name) -> None:
        """
        Instruction execution for load absolute.

        "absolute LD[A, X, Y] oper" and "absolute,[X, Y] LD[A, X, Y] oper,[X, Y]".

        Executes Load Absolute on {register_name} for {instruction} using {offset_register_name}

        Arguments:
            instruction: the load absolute instruction to execute
            register_name: the register to load to
            offset_register_name: the offset register to use for any offset operations

        Returns:
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
        register: Byte = getattr(self, register_name)
        absolute_address: Word | None = self.fetch_word()

        address: Word = absolute_address
        if offset_register_name is not None:
            offset_register_value = getattr(self, offset_register_name)
            address: Word = absolute_address + offset_register_value

            if address.overflow:
                self.spend_cpu_cycles(1)
        else:
            address: Word = absolute_address

        setattr(self, register_name, self.read_byte(address=address))
        self.set_load_status_flags(register_name=register_name)

        self.log.debug(f'{instructions.InstructionSet(instruction).name}: {Byte(value=register)}')

    def execute_load_indexed_indirect(self, instruction, register_name) -> None:
        """
        Instruction execution for "(indirect,X) LD[A, X, Y] (oper,X)".

        Executes Load Indexed Indirect on {register_name} for {instruction}.

        Arguments:
            instruction: the load indexed indirect instruction to execute
            register_name: the name of the register to load to

        Returns:
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
        register: Byte = getattr(self, register_name)
        indirect_address: Byte = self.fetch_byte()
        offset_register_value = getattr(self, 'X')

        address = self.read_word(indirect_address + offset_register_value)

        setattr(self, register_name, self.read_byte(address=address))
        self.set_load_status_flags(register_name=register_name)

        self.log.debug(f'{instructions.InstructionSet(instruction).name}: {Byte(value=register)}')

    def execute_load_indirect_indexed(self, instruction, register_name) -> None:
        """
        Instruction execution for "(indirect),Y LD[A, X, Y] (oper),Y".

        Executes Load Indirect Indexed on {register_name} for {instruction}.

        Arguments:
            instruction: the load indexed indirect instruction to esxecute
            register_name: the name of the register to load to

        Returns:
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
        register: Byte = getattr(self, register_name)
        indirect_address: Byte = self.fetch_byte()
        offset_register_value = getattr(self, 'Y')

        absolute_address = self.read_word(indirect_address)

        # Note: We add these together this way to ensure
        # an overflow condition
        address: Word = Word(absolute_address) + Byte(offset_register_value)

        if address.overflow:
            self.spend_cpu_cycles(1)

        setattr(self, register_name, self.read_byte(address=address))
        self.set_load_status_flags(register_name=register_name)

        self.log.debug(f'{instructions.InstructionSet(instruction).name}: {Byte(value=register)}')

    def execute(self, cycles=1) -> int:
        """
        Fetch and execute a CPU instruction.

        Arguments:
            cycles: the number of cycles to execute.  Used for testing.
                Use mos6502.core.INFINITE_CYCLES for long running programs.

        Returns:
            The number of cycles executed.
        """
        self.cycles: int = cycles

        while self.cycles > 0:
            instruction: Byte = self.fetch_byte()

            self.log.debug(
                f'Got instruction 0x{instruction:02x} @ {hex(self.PC - 1)}: '
                f'{instructions.InstructionSet(instruction).name}'
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
                # AND_IMMEDIATE_0x29 = 0x29
                # AND_ZEROPAGE_0x25 = 0x25
                # AND_ZEROPAGE_X_0x35 = 0x35
                # AND_ABSOLUTE_0x2D = 0x2D
                # AND_ABSOLUTE_X_0x3D = 0x3D
                # AND_ABSOLUTE_Y_0x39 = 0x39
                # AND_INDEXED_INDIRECT_X_0x21 = 0x21
                # AND_INDIRECT_INDEXED_Y_0x31 = 0x31

                # ''' Execute ASL '''
                # ASL_ACCUMULATOR_0x0A = 0x0A
                # ASL_ZEROPAGE_0x06 = 0x06
                # ASL_ZEROPAGE_X_0x16 = 0x16
                # ASL_ABSOLUTE_0x0E = 0x0E
                # ASL_ABSOLUTE_X_0x1E = 0x1E

                # ''' Execute BBC '''
                # BBC_RELATIVE_0x90 = 0x90

                # ''' Execute BCS '''
                # BCS_RELATIVE_0xB0 = 0xB0

                # ''' Excecute BEQ '''
                # BEQ_RELATIVE_0xF0 = 0xF0

                # ''' Execute BIT '''
                # BIT_ZEROPAGE_0x24 = 0x24
                # BIT_ABSOLUTE_0x2C = 0x2C

                # BMI
                # BNE
                # BPL
                # BRK
                # BVC
                # BVS
                # CLC
                # CLD
                # CLI
                # CLV
                # CMP
                # CPX
                # CPY
                # DEC
                # DEX
                # DEY
                # EOR
                # INC
                # INX
                # INY
                # JMP

                # ''' Execute JSR '''
                case instructions.JSR_ABSOLUTE_0x20:
                    subroutine_address: Word = self.fetch_word()

                    self.write_word(address=self.SP, data=self.PC - 1)

                    # TODO: Need to increment the stack pointer some where here??

                    self.ram[self.SP] = self.PC - 1
                    self.PC = subroutine_address
                    self.spend_cpu_cycles(cost=1)

                    self.log.debug(
                        f'{instructions.InstructionSet(instruction).name}: '
                        f'{hex(subroutine_address)}'
                    )

                # ''' Execute Load Immediate '''
                case instructions.LDA_IMMEDIATE_0xA9:
                    self.execute_load_immediate(
                        instruction=instruction,
                        register_name='A'
                    )

                case instructions.LDX_IMMEDIATE_0xA2:
                    self.execute_load_immediate(
                        instruction=instruction,
                        register_name='X'
                    )

                case instructions.LDY_IMMEDIATE_0xA0:
                    self.execute_load_immediate(
                        instruction=instruction,
                        register_name='Y'
                    )

                # ''' Execute Load Zero Page '''
                case instructions.LDA_ZEROPAGE_0xA5:
                    self.execute_load_zeropage(
                        instruction=instruction,
                        register_name='A',
                        offset_register_name=None
                    )

                case instructions.LDX_ZEROPAGE_0xA6:
                    self.execute_load_zeropage(
                        instruction=instruction,
                        register_name='X',
                        offset_register_name=None
                    )

                case instructions.LDY_ZEROPAGE_0xA4:
                    self.execute_load_zeropage(
                        instruction=instruction,
                        register_name='Y',
                        offset_register_name=None
                    )

                # ''' Execute Load Zero Page X '''
                case instructions.LDY_ZEROPAGE_X_0xB4:
                    self.execute_load_zeropage(
                        instruction=instruction,
                        register_name='Y',
                        offset_register_name='X'
                    )

                case instructions.LDA_ZEROPAGE_X_0xB5:
                    self.execute_load_zeropage(
                        instruction=instruction,
                        register_name='A',
                        offset_register_name='X'
                    )

                # ''' Execute Load Zero Page Y '''
                case instructions.LDX_ZEROPAGE_Y_0xB6:
                    self.execute_load_zeropage(
                        instruction=instruction,
                        register_name='X',
                        offset_register_name='Y'
                    )

                # ''' Execute Loada Absolute '''
                case instructions.LDA_ABSOLUTE_0xAD:
                    self.execute_load_absolute(
                        instruction=instruction,
                        register_name='A',
                        offset_register_name=None
                    )

                case instructions.LDX_ABSOLUTE_0xAE:
                    self.execute_load_absolute(
                        instruction=instruction,
                        register_name='X',
                        offset_register_name=None
                    )

                case instructions.LDY_ABSOLUTE_0xAC:
                    self.execute_load_absolute(
                        instruction=instruction,
                        register_name='Y',
                        offset_register_name=None
                    )

                case instructions.LDA_ABSOLUTE_X_0xBD:
                    self.execute_load_absolute(
                        instruction=instruction,
                        register_name='A',
                        offset_register_name='X'
                    )

                case instructions.LDA_ABSOLUTE_Y_0xB9:
                    self.execute_load_absolute(
                        instruction=instruction,
                        register_name='A',
                        offset_register_name='Y'
                    )

                case instructions.LDX_ABSOLUTE_Y_0xBE:
                    self.execute_load_absolute(
                        instruction=instruction,
                        register_name='X',
                        offset_register_name='Y'
                    )

                case instructions.LDY_ABSOLUTE_X_0xBC:
                    self.execute_load_absolute(
                        instruction=instruction,
                        register_name='Y',
                        offset_register_name='X'
                    )

                # ''' Execute Indexed Indirect '''
                case instructions.LDA_INDEXED_INDIRECT_X_0xA1:
                    self.execute_load_indexed_indirect(
                        instruction=instruction,
                        register_name='A'
                    )

                # ''' Execute Indirect Indexed'''
                case instructions.LDA_INDIRECT_INDEXED_Y_0xB1:
                    self.execute_load_indirect_indexed(
                        instruction=instruction,
                        register_name='A'
                    )

                # ''' LSR '''
                # NOP
                # ORA
                # PHA
                # PHP
                # PLA
                # PLP
                # ROL
                # ROR
                # RTI
                # RTS
                # SBC
                # SEC
                # SED
                # SEI
                # STA
                # STX
                # STY
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
                    self.log.error(f'ILLEGAL INSTRUCTION: {instruction} ({instruction:02X})')

            self.spend_cpu_cycles(cost=1)

        return self.cycles_executed

    def reset(self):
        """
        Reset the CPU.

        It is necessary to call this method before executing instructions.

        The PC and SP need to be set up.
        This also clears CPU flags and registers and initializes RAM to 0s.
        """
        self.log.debug("Reset")
        self.PC: Word = Word(0xFFFC, endianness=self.endianness)
        self.SP: Word = Word(0x0100, endianness=self.endianness)

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
    def flags(self) -> Byte:
        """
        Return the CPU flags register.

        Returns:
            Byte()
        """
        return getattr(self, '_flags')

    @flags.setter
    def flags(self, flags) -> None:
        """
        Set the CPU flags register.

        Arguments:
            flags: Byte()
        """
        setattr(self._flags, flags)

    @property
    def PC(self) -> Word:
        """
        Return the CPU PC register.

        Returns:
            Word()
        """
        return getattr(self._registers, 'PC')

    @PC.setter
    def PC(self, PC) -> None:
        """
        Set the CPU PC register.

        Arguments:
            PC: Word()
        """
        setattr(self._registers, 'PC', Word(PC))

    @property
    def SP(self) -> Byte:
        """
        Return the CPU SP register.

        This register is an 8-bit register, but we store it as 16-bits for convenience.

        This register must be masked with 0xFF when performing instruction offset calculations.

        Returns:
            Word()
        """
        return getattr(self._registers, 'SP')

    @SP.setter
    def SP(self, SP) -> None:
        """
        Set the CPU SP register.

        Arguments:
            SP: Word()
        """
        setattr(self._registers, 'SP', Word(SP))

    @property
    def A(self) -> Byte:
        """
        Return the CPU A register.

        Returns:
            Byte()
        """
        return getattr(self._registers, 'A')

    @A.setter
    def A(self, A) -> Byte:
        """
        Set the CPU A register.

        Arguments:
            A: Byte()
        """
        setattr(self._registers, 'A', A)

    @property
    def X(self) -> Byte:
        """
        Return the CPU X register.

        Returns:
            Byte()
        """
        return getattr(self._registers, 'X')

    @X.setter
    def X(self, X) -> None:
        """
        Set the CPU X register.

        Arguments:
            X: Byte()
        """
        setattr(self._registers, 'X', X)

    @property
    def Y(self) -> Byte:
        """
        Return the CPU Y register.

        Returns:
            Byte()
        """
        return getattr(self._registers, 'Y')

    @Y.setter
    def Y(self, Y) -> None:
        """
        Set the CPU Y register.

        Arguments:
            Y: Byte()
        """
        setattr(self._registers, 'Y', Y)

    def __str__(self):
        """Return the CPU status."""
        description = f"{type(self).__name__}\n"
        description += f"\tPC: {hex(int.from_bytes(self.PC, byteorder=self.endianness))}\n"
        description += f"\tSP: {hex(int.from_bytes(self.SP, byteorder=self.endianness))}\n"
        description += f"\tC: {self.C[flags.C]}\n"
        description += f"\tZ: {self.Z[flags.Z]}\n"
        description += f"\tI: {self.I[flags.I]}\n"
        description += f"\tD: {self.D[flags.D]}\n"
        description += f"\tB: {self.B[flags.B]}\n"
        description += f"\tV: {self.V[flags.V]}\n"
        description += f"\tN: {self.N[flags.N]}\n"

        return description


def main() -> None:
    """
    Demo program.

    Demonstrates using the CPU in a context manager.

    Loads the JSR instruction and jumps to 0x4242
    then loads 0x23 from 0x4243 using the LDA_IMMEDIATE instruction.
    """
    log: logging.Logger = logging.getLogger('mos6502')
    logging.basicConfig(format='%(message)s', level=logging.DEBUG)

    with MOS6502CPU() as cpu:
        cpu.reset()
        # Supported instructions
        # LDA, LDX, LDY - see tests/test_mos6502_LDA_LDX_LDY_instruction.py
        # JSR - see tests/test_mos6502_JMP_JSR_instruction.py

        # Jump to 0x4242
        # Should be 9 cycles
        cpu.ram[0xFFFC] = instructions.JSR_ABSOLUTE_0x20
        cpu.ram[0xFFFD] = 0x42
        cpu.ram[0xFFFE] = 0x42
        cpu.ram[0x4242] = instructions.LDA_IMMEDIATE_0xA9
        cpu.ram[0x4243] = 0x23

        try:
            cpu.execute(cycles=INFINITE_CYCLES)
        except instructions.IllegalCPUInstructionException:
            log.debug(f'Used: {cpu.cycles_executed} cycles')


if __name__ == '__main__':
    main()
