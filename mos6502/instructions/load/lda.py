#!/usr/bin/env python3
"""LDA (Load Accumulator with Memory) instruction."""
from typing import Literal

from mos6502 import flags
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#LDA
#
# Load Accumulator with Memory
#
# M -> A
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	LDA #oper	A9	2	2
# zeropage	LDA oper	A5	2	3
# zeropage,X	LDA oper,X	B5	2	4
# absolute	LDA oper	AD	3	4
# absolute,X	LDA oper,X	BD	3	4*
# absolute,Y	LDA oper,Y	B9	3	4*
# (indirect,X)	LDA (oper,X)	A1	2	6
# (indirect),Y	LDA (oper),Y	B1	2	5*
LDA_IMMEDIATE_0xA9: Literal[169] = 0xA9
LDA_ZEROPAGE_0xA5: Literal[165] = 0xA5
LDA_ZEROPAGE_X_0xB5: Literal[181] = 0xB5
LDA_ABSOLUTE_0xAD: Literal[173] = 0xAD
LDA_ABSOLUTE_X_0xBD: Literal[189] = 0xBD
LDA_ABSOLUTE_Y_0xB9: Literal[185] = 0xB9
LDA_INDEXED_INDIRECT_X_0xA1: Literal[161] = 0xA1
LDA_INDIRECT_INDEXED_Y_0xB1: Literal[177] = 0xB1


def add_lda_to_instruction_set_enum(instruction_set_class) -> None:
    """Add LDA instructions to the InstructionSet enum dynamically."""
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
        (LDA_IMMEDIATE_0xA9, 'LDA_IMMEDIATE_0xA9'),
        (LDA_ZEROPAGE_0xA5, 'LDA_ZEROPAGE_0xA5'),
        (LDA_ZEROPAGE_X_0xB5, 'LDA_ZEROPAGE_X_0xB5'),
        (LDA_ABSOLUTE_0xAD, 'LDA_ABSOLUTE_0xAD'),
        (LDA_ABSOLUTE_X_0xBD, 'LDA_ABSOLUTE_X_0xBD'),
        (LDA_ABSOLUTE_Y_0xB9, 'LDA_ABSOLUTE_Y_0xB9'),
        (LDA_INDEXED_INDIRECT_X_0xA1, 'LDA_INDEXED_INDIRECT_X_0xA1'),
        (LDA_INDIRECT_INDEXED_Y_0xB1, 'LDA_INDIRECT_INDEXED_Y_0xB1'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_lda_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register LDA instructions in the InstructionSet."""
    # Add to enum
    add_lda_to_instruction_set_enum(instruction_set_class)

    # Add to map
    lda_immediate_0xa9_can_modify_flags: Byte = Byte()
    lda_immediate_0xa9_can_modify_flags[flags.N] = True
    lda_immediate_0xa9_can_modify_flags[flags.Z] = True

    instruction_map[LDA_IMMEDIATE_0xA9] = {
        "addressing": "immediate",
        "assembler": "LDA #{oper}",
        "opc": LDA_IMMEDIATE_0xA9,
        "bytes": "2",
        "cycles": "2",
        "flags": lda_immediate_0xa9_can_modify_flags,
    }

    lda_zeropage_0xa5_can_modify_flags: Byte = lda_immediate_0xa9_can_modify_flags
    instruction_map[LDA_ZEROPAGE_0xA5] = {
        "addressing": "zeropage",
        "assembler": "LDA {oper}",
        "opc": LDA_ZEROPAGE_0xA5,
        "bytes": "2",
        "cycles": "3",
        "flags": lda_zeropage_0xa5_can_modify_flags,
    }

    lda_zeropage_x_0xb5_can_modify_flags: Byte = lda_immediate_0xa9_can_modify_flags
    instruction_map[LDA_ZEROPAGE_X_0xB5] = {
        "addressing": "zeropage,X",
        "assembler": "LDA {oper},X",
        "opc": LDA_ZEROPAGE_X_0xB5,
        "bytes": "2",
        "cycles": "4",
        "flags": lda_zeropage_x_0xb5_can_modify_flags,
    }

    lda_absolute_0xad_can_modify_flags: Byte = lda_immediate_0xa9_can_modify_flags
    instruction_map[LDA_ABSOLUTE_0xAD] = {
        "addressing": "absolute",
        "assembler": "LDA {oper}",
        "opc": LDA_ABSOLUTE_0xAD,
        "bytes": "3",
        "cycles": "4",
        "flags": lda_absolute_0xad_can_modify_flags,
    }

    lda_absolute_x_0xbd_can_modify_flags: Byte = lda_immediate_0xa9_can_modify_flags
    instruction_map[LDA_ABSOLUTE_X_0xBD] = {
        "addressing": "absolute,X",
        "assembler": "LDA {oper},X",
        "opc": LDA_ABSOLUTE_X_0xBD,
        "bytes": "3",
        "cycles": "4*",
        "flags": lda_absolute_x_0xbd_can_modify_flags,
    }

    lda_absolute_y_0xb9_can_modify_flags: Byte = lda_immediate_0xa9_can_modify_flags
    instruction_map[LDA_ABSOLUTE_Y_0xB9] = {
        "addressing": "absolute,Y",
        "assembler": "LDA {oper},Y",
        "opc": LDA_ABSOLUTE_Y_0xB9,
        "bytes": "3",
        "cycles": "4*",
        "flags": lda_absolute_y_0xb9_can_modify_flags,
    }

    lda_indexed_indirect_x_0xa1_can_modify_flags: Byte = lda_immediate_0xa9_can_modify_flags
    instruction_map[LDA_INDEXED_INDIRECT_X_0xA1] = {
        "addressing": "(indirect, X)",
        "assembler": "LDA ({oper},X)",
        "opc": LDA_INDEXED_INDIRECT_X_0xA1,
        "bytes": "2",
        "cycles": "6",
        "flags": lda_indexed_indirect_x_0xa1_can_modify_flags,
    }

    lda_indirect_indexed_y_0xb1_can_modify_flags: Byte = lda_immediate_0xa9_can_modify_flags
    instruction_map[LDA_INDIRECT_INDEXED_Y_0xB1] = {
        "addressing": "(indirect), Y",
        "assembler": "LDA ({oper}),Y",
        "opc": LDA_INDIRECT_INDEXED_Y_0xB1,
        "bytes": "2",
        "cycles": "5*",
        "flags": lda_indirect_indexed_y_0xb1_can_modify_flags,
    }


__all__ = [
    'LDA_IMMEDIATE_0xA9',
    'LDA_ZEROPAGE_0xA5',
    'LDA_ZEROPAGE_X_0xB5',
    'LDA_ABSOLUTE_0xAD',
    'LDA_ABSOLUTE_X_0xBD',
    'LDA_ABSOLUTE_Y_0xB9',
    'LDA_INDEXED_INDIRECT_X_0xA1',
    'LDA_INDIRECT_INDEXED_Y_0xB1',
    'register_lda_instructions',
]
