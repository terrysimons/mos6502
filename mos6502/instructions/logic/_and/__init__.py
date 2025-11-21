#!/usr/bin/env python3
"""AND (AND Memory with Accumulator) instruction."""
from mos6502.instructions import InstructionOpcode

# https://masswerk.at/6502/6502_instruction_set.html#AND
# AND Memory with Accumulator
#
# A AND M -> A
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	AND #oper	29	2	2
# zeropage	AND oper	25	2	3
# zeropage,X	AND oper,X	35	2	4
# absolute	AND oper	2D	3	4
# absolute,X	AND oper,X	3D	3	4*
# absolute,Y	AND oper,Y	39	3	4*
# (indirect,X)	AND (oper,X)	21	2	6
# (indirect),Y	AND (oper),Y	31	2	5*

AND_IMMEDIATE_0x29 = InstructionOpcode(
    0x29,
    "mos6502.instructions.logic._and",
    "and_immediate_0x29"
)

AND_ZEROPAGE_0x25 = InstructionOpcode(
    0x25,
    "mos6502.instructions.logic._and",
    "and_zeropage_0x25"
)

AND_ZEROPAGE_X_0x35 = InstructionOpcode(
    0x35,
    "mos6502.instructions.logic._and",
    "and_zeropage_x_0x35"
)

AND_ABSOLUTE_0x2D = InstructionOpcode(
    0x2D,
    "mos6502.instructions.logic._and",
    "and_absolute_0x2d"
)

AND_ABSOLUTE_X_0x3D = InstructionOpcode(
    0x3D,
    "mos6502.instructions.logic._and",
    "and_absolute_x_0x3d"
)

AND_ABSOLUTE_Y_0x39 = InstructionOpcode(
    0x39,
    "mos6502.instructions.logic._and",
    "and_absolute_y_0x39"
)

AND_INDEXED_INDIRECT_X_0x21 = InstructionOpcode(
    0x21,
    "mos6502.instructions.logic._and",
    "and_indexed_indirect_x_0x21"
)

AND_INDIRECT_INDEXED_Y_0x31 = InstructionOpcode(
    0x31,
    "mos6502.instructions.logic._and",
    "and_indirect_indexed_y_0x31"
)


def add_and_to_instruction_set_enum(instruction_set_class) -> None:
    """Add AND instructions to the InstructionSet enum dynamically."""
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
        (AND_IMMEDIATE_0x29, "AND_IMMEDIATE_0x29"),
        (AND_ZEROPAGE_0x25, "AND_ZEROPAGE_0x25"),
        (AND_ZEROPAGE_X_0x35, "AND_ZEROPAGE_X_0x35"),
        (AND_ABSOLUTE_0x2D, "AND_ABSOLUTE_0x2D"),
        (AND_ABSOLUTE_X_0x3D, "AND_ABSOLUTE_X_0x3D"),
        (AND_ABSOLUTE_Y_0x39, "AND_ABSOLUTE_Y_0x39"),
        (AND_INDEXED_INDIRECT_X_0x21, "AND_INDEXED_INDIRECT_X_0x21"),
        (AND_INDIRECT_INDEXED_Y_0x31, "AND_INDIRECT_INDEXED_Y_0x31"),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_and_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register AND instructions in the InstructionSet."""
    add_and_to_instruction_set_enum(instruction_set_class)

    from mos6502.memory import Byte
    from mos6502 import flags
    and_can_modify_flags: Byte = Byte()
    and_can_modify_flags[flags.N] = 1
    and_can_modify_flags[flags.Z] = 1

    instruction_map[AND_IMMEDIATE_0x29] = {
        "addressing": "immediate",
        "assembler": "AND #{oper}",
        "opc": AND_IMMEDIATE_0x29,
        "bytes": "2",
        "cycles": "2",
        "flags": and_can_modify_flags,
    }

    instruction_map[AND_ZEROPAGE_0x25] = {
        "addressing": "zeropage",
        "assembler": "AND {oper}",
        "opc": AND_ZEROPAGE_0x25,
        "bytes": "2",
        "cycles": "3",
        "flags": and_can_modify_flags,
    }

    instruction_map[AND_ZEROPAGE_X_0x35] = {
        "addressing": "zeropage,X",
        "assembler": "AND {oper},X",
        "opc": AND_ZEROPAGE_X_0x35,
        "bytes": "2",
        "cycles": "4",
        "flags": and_can_modify_flags,
    }

    instruction_map[AND_ABSOLUTE_0x2D] = {
        "addressing": "absolute",
        "assembler": "AND {oper}",
        "opc": AND_ABSOLUTE_0x2D,
        "bytes": "3",
        "cycles": "4",
        "flags": and_can_modify_flags,
    }

    instruction_map[AND_ABSOLUTE_X_0x3D] = {
        "addressing": "absolute,X",
        "assembler": "AND {oper},X",
        "opc": AND_ABSOLUTE_X_0x3D,
        "bytes": "3",
        "cycles": "4*",
        "flags": and_can_modify_flags,
    }

    instruction_map[AND_ABSOLUTE_Y_0x39] = {
        "addressing": "absolute,Y",
        "assembler": "AND {oper},Y",
        "opc": AND_ABSOLUTE_Y_0x39,
        "bytes": "3",
        "cycles": "4*",
        "flags": and_can_modify_flags,
    }

    instruction_map[AND_INDEXED_INDIRECT_X_0x21] = {
        "addressing": "(indirect,X)",
        "assembler": "AND ({oper},X)",
        "opc": AND_INDEXED_INDIRECT_X_0x21,
        "bytes": "2",
        "cycles": "6",
        "flags": and_can_modify_flags,
    }

    instruction_map[AND_INDIRECT_INDEXED_Y_0x31] = {
        "addressing": "(indirect),Y",
        "assembler": "AND ({oper}),Y",
        "opc": AND_INDIRECT_INDEXED_Y_0x31,
        "bytes": "2",
        "cycles": "5*",
        "flags": and_can_modify_flags,
    }


__all__ = [
    "AND_IMMEDIATE_0x29",
    "AND_ZEROPAGE_0x25",
    "AND_ZEROPAGE_X_0x35",
    "AND_ABSOLUTE_0x2D",
    "AND_ABSOLUTE_X_0x3D",
    "AND_ABSOLUTE_Y_0x39",
    "AND_INDEXED_INDIRECT_X_0x21",
    "AND_INDIRECT_INDEXED_Y_0x31",
    "register_and_instructions",
]
