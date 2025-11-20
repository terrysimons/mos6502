#!/usr/bin/env python3
"""EOR (Exclusive-OR Memory with Accumulator) instruction."""
from mos6502.instructions import InstructionOpcode

# https://masswerk.at/6502/6502_instruction_set.html#EOR
# Exclusive-OR Memory with Accumulator
#
# A EOR M -> A
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	EOR #oper	49	2	2
# zeropage	EOR oper	45	2	3
# zeropage,X	EOR oper,X	55	2	4
# absolute	EOR oper	4D	3	4
# absolute,X	EOR oper,X	5D	3	4*
# absolute,Y	EOR oper,Y	59	3	4*
# (indirect,X)	EOR (oper,X)	41	2	6
# (indirect),Y	EOR (oper),Y	51	2	5*

EOR_IMMEDIATE_0x49 = InstructionOpcode(
    0x49,
    "mos6502.instructions.logic._eor",
    "eor_immediate_0x49"
)

EOR_ZEROPAGE_0x45 = InstructionOpcode(
    0x45,
    "mos6502.instructions.logic._eor",
    "eor_zeropage_0x45"
)

EOR_ZEROPAGE_X_0x55 = InstructionOpcode(
    0x55,
    "mos6502.instructions.logic._eor",
    "eor_zeropage_x_0x55"
)

EOR_ABSOLUTE_0x4D = InstructionOpcode(
    0x4D,
    "mos6502.instructions.logic._eor",
    "eor_absolute_0x4d"
)

EOR_ABSOLUTE_X_0x5D = InstructionOpcode(
    0x5D,
    "mos6502.instructions.logic._eor",
    "eor_absolute_x_0x5d"
)

EOR_ABSOLUTE_Y_0x59 = InstructionOpcode(
    0x59,
    "mos6502.instructions.logic._eor",
    "eor_absolute_y_0x59"
)

EOR_INDEXED_INDIRECT_X_0x41 = InstructionOpcode(
    0x41,
    "mos6502.instructions.logic._eor",
    "eor_indexed_indirect_x_0x41"
)

EOR_INDIRECT_INDEXED_Y_0x51 = InstructionOpcode(
    0x51,
    "mos6502.instructions.logic._eor",
    "eor_indirect_indexed_y_0x51"
)


def add_eor_to_instruction_set_enum(instruction_set_class) -> None:
    """Add EOR instructions to the InstructionSet enum dynamically."""
    class PseudoEnumMember(int):
        def __new__(cls, value, name):
            obj = int.__new__(cls, value)
            obj._name = name
            obj._value_ = value
            return obj

        @property
        def name(self):
            return self._name

        @property
        def value(self):
            return self._value_

    for value, name in [
        (EOR_IMMEDIATE_0x49, 'EOR_IMMEDIATE_0x49'),
        (EOR_ZEROPAGE_0x45, 'EOR_ZEROPAGE_0x45'),
        (EOR_ZEROPAGE_X_0x55, 'EOR_ZEROPAGE_X_0x55'),
        (EOR_ABSOLUTE_0x4D, 'EOR_ABSOLUTE_0x4D'),
        (EOR_ABSOLUTE_X_0x5D, 'EOR_ABSOLUTE_X_0x5D'),
        (EOR_ABSOLUTE_Y_0x59, 'EOR_ABSOLUTE_Y_0x59'),
        (EOR_INDEXED_INDIRECT_X_0x41, 'EOR_INDEXED_INDIRECT_X_0x41'),
        (EOR_INDIRECT_INDEXED_Y_0x51, 'EOR_INDIRECT_INDEXED_Y_0x51'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_eor_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register EOR instructions in the InstructionSet."""
    add_eor_to_instruction_set_enum(instruction_set_class)

    from mos6502.memory import Byte
    from mos6502 import flags
    eor_can_modify_flags: Byte = Byte()
    eor_can_modify_flags[flags.N] = 1
    eor_can_modify_flags[flags.Z] = 1

    instruction_map[EOR_IMMEDIATE_0x49] = {
        "addressing": "immediate",
        "assembler": "EOR #{oper}",
        "opc": EOR_IMMEDIATE_0x49,
        "bytes": "2",
        "cycles": "2",
        "flags": eor_can_modify_flags,
    }

    instruction_map[EOR_ZEROPAGE_0x45] = {
        "addressing": "zeropage",
        "assembler": "EOR {oper}",
        "opc": EOR_ZEROPAGE_0x45,
        "bytes": "2",
        "cycles": "3",
        "flags": eor_can_modify_flags,
    }

    instruction_map[EOR_ZEROPAGE_X_0x55] = {
        "addressing": "zeropage,X",
        "assembler": "EOR {oper},X",
        "opc": EOR_ZEROPAGE_X_0x55,
        "bytes": "2",
        "cycles": "4",
        "flags": eor_can_modify_flags,
    }

    instruction_map[EOR_ABSOLUTE_0x4D] = {
        "addressing": "absolute",
        "assembler": "EOR {oper}",
        "opc": EOR_ABSOLUTE_0x4D,
        "bytes": "3",
        "cycles": "4",
        "flags": eor_can_modify_flags,
    }

    instruction_map[EOR_ABSOLUTE_X_0x5D] = {
        "addressing": "absolute,X",
        "assembler": "EOR {oper},X",
        "opc": EOR_ABSOLUTE_X_0x5D,
        "bytes": "3",
        "cycles": "4*",
        "flags": eor_can_modify_flags,
    }

    instruction_map[EOR_ABSOLUTE_Y_0x59] = {
        "addressing": "absolute,Y",
        "assembler": "EOR {oper},Y",
        "opc": EOR_ABSOLUTE_Y_0x59,
        "bytes": "3",
        "cycles": "4*",
        "flags": eor_can_modify_flags,
    }

    instruction_map[EOR_INDEXED_INDIRECT_X_0x41] = {
        "addressing": "(indirect,X)",
        "assembler": "EOR ({oper},X)",
        "opc": EOR_INDEXED_INDIRECT_X_0x41,
        "bytes": "2",
        "cycles": "6",
        "flags": eor_can_modify_flags,
    }

    instruction_map[EOR_INDIRECT_INDEXED_Y_0x51] = {
        "addressing": "(indirect),Y",
        "assembler": "EOR ({oper}),Y",
        "opc": EOR_INDIRECT_INDEXED_Y_0x51,
        "bytes": "2",
        "cycles": "5*",
        "flags": eor_can_modify_flags,
    }


__all__ = [
    'EOR_IMMEDIATE_0x49',
    'EOR_ZEROPAGE_0x45',
    'EOR_ZEROPAGE_X_0x55',
    'EOR_ABSOLUTE_0x4D',
    'EOR_ABSOLUTE_X_0x5D',
    'EOR_ABSOLUTE_Y_0x59',
    'EOR_INDEXED_INDIRECT_X_0x41',
    'EOR_INDIRECT_INDEXED_Y_0x51',
    'register_eor_instructions',
]
