#!/usr/bin/env python3
"""ORA (OR Memory with Accumulator) instruction."""
from mos6502.instructions import InstructionOpcode

# https://masswerk.at/6502/6502_instruction_set.html#ORA
# OR Memory with Accumulator
#
# A OR M -> A
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	ORA #oper	09	2	2
# zeropage	ORA oper	05	2	3
# zeropage,X	ORA oper,X	15	2	4
# absolute	ORA oper	0D	3	4
# absolute,X	ORA oper,X	1D	3	4*
# absolute,Y	ORA oper,Y	19	3	4*
# (indirect,X)	ORA (oper,X)	01	2	6
# (indirect),Y	ORA (oper),Y	11	2	5*

ORA_IMMEDIATE_0x09 = InstructionOpcode(
    0x09,
    "mos6502.instructions.logic._ora",
    "ora_immediate_0x09"
)

ORA_ZEROPAGE_0x05 = InstructionOpcode(
    0x05,
    "mos6502.instructions.logic._ora",
    "ora_zeropage_0x05"
)

ORA_ZEROPAGE_X_0x15 = InstructionOpcode(
    0x15,
    "mos6502.instructions.logic._ora",
    "ora_zeropage_x_0x15"
)

ORA_ABSOLUTE_0x0D = InstructionOpcode(
    0x0D,
    "mos6502.instructions.logic._ora",
    "ora_absolute_0x0d"
)

ORA_ABSOLUTE_X_0x1D = InstructionOpcode(
    0x1D,
    "mos6502.instructions.logic._ora",
    "ora_absolute_x_0x1d"
)

ORA_ABSOLUTE_Y_0x19 = InstructionOpcode(
    0x19,
    "mos6502.instructions.logic._ora",
    "ora_absolute_y_0x19"
)

ORA_INDEXED_INDIRECT_X_0x01 = InstructionOpcode(
    0x01,
    "mos6502.instructions.logic._ora",
    "ora_indexed_indirect_x_0x01"
)

ORA_INDIRECT_INDEXED_Y_0x11 = InstructionOpcode(
    0x11,
    "mos6502.instructions.logic._ora",
    "ora_indirect_indexed_y_0x11"
)


def add_ora_to_instruction_set_enum(instruction_set_class) -> None:
    """Add ORA instructions to the InstructionSet enum dynamically."""
    class PseudoEnumMember(int):
        def __new__(cls, value, name) -> "InstructionSet":
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
        (ORA_IMMEDIATE_0x09, "ORA_IMMEDIATE_0x09"),
        (ORA_ZEROPAGE_0x05, "ORA_ZEROPAGE_0x05"),
        (ORA_ZEROPAGE_X_0x15, "ORA_ZEROPAGE_X_0x15"),
        (ORA_ABSOLUTE_0x0D, "ORA_ABSOLUTE_0x0D"),
        (ORA_ABSOLUTE_X_0x1D, "ORA_ABSOLUTE_X_0x1D"),
        (ORA_ABSOLUTE_Y_0x19, "ORA_ABSOLUTE_Y_0x19"),
        (ORA_INDEXED_INDIRECT_X_0x01, "ORA_INDEXED_INDIRECT_X_0x01"),
        (ORA_INDIRECT_INDEXED_Y_0x11, "ORA_INDIRECT_INDEXED_Y_0x11"),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_ora_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register ORA instructions in the InstructionSet."""
    add_ora_to_instruction_set_enum(instruction_set_class)

    from mos6502.memory import Byte
    from mos6502 import flags
    ora_can_modify_flags: Byte = Byte()
    ora_can_modify_flags[flags.N] = 1
    ora_can_modify_flags[flags.Z] = 1

    instruction_map[ORA_IMMEDIATE_0x09] = {
        "addressing": "immediate",
        "assembler": "ORA #{oper}",
        "opc": ORA_IMMEDIATE_0x09,
        "bytes": "2",
        "cycles": "2",
        "flags": ora_can_modify_flags,
    }

    instruction_map[ORA_ZEROPAGE_0x05] = {
        "addressing": "zeropage",
        "assembler": "ORA {oper}",
        "opc": ORA_ZEROPAGE_0x05,
        "bytes": "2",
        "cycles": "3",
        "flags": ora_can_modify_flags,
    }

    instruction_map[ORA_ZEROPAGE_X_0x15] = {
        "addressing": "zeropage,X",
        "assembler": "ORA {oper},X",
        "opc": ORA_ZEROPAGE_X_0x15,
        "bytes": "2",
        "cycles": "4",
        "flags": ora_can_modify_flags,
    }

    instruction_map[ORA_ABSOLUTE_0x0D] = {
        "addressing": "absolute",
        "assembler": "ORA {oper}",
        "opc": ORA_ABSOLUTE_0x0D,
        "bytes": "3",
        "cycles": "4",
        "flags": ora_can_modify_flags,
    }

    instruction_map[ORA_ABSOLUTE_X_0x1D] = {
        "addressing": "absolute,X",
        "assembler": "ORA {oper},X",
        "opc": ORA_ABSOLUTE_X_0x1D,
        "bytes": "3",
        "cycles": "4*",
        "flags": ora_can_modify_flags,
    }

    instruction_map[ORA_ABSOLUTE_Y_0x19] = {
        "addressing": "absolute,Y",
        "assembler": "ORA {oper},Y",
        "opc": ORA_ABSOLUTE_Y_0x19,
        "bytes": "3",
        "cycles": "4*",
        "flags": ora_can_modify_flags,
    }

    instruction_map[ORA_INDEXED_INDIRECT_X_0x01] = {
        "addressing": "(indirect,X)",
        "assembler": "ORA ({oper},X)",
        "opc": ORA_INDEXED_INDIRECT_X_0x01,
        "bytes": "2",
        "cycles": "6",
        "flags": ora_can_modify_flags,
    }

    instruction_map[ORA_INDIRECT_INDEXED_Y_0x11] = {
        "addressing": "(indirect),Y",
        "assembler": "ORA ({oper}),Y",
        "opc": ORA_INDIRECT_INDEXED_Y_0x11,
        "bytes": "2",
        "cycles": "5*",
        "flags": ora_can_modify_flags,
    }


__all__ = [
    "ORA_IMMEDIATE_0x09",
    "ORA_ZEROPAGE_0x05",
    "ORA_ZEROPAGE_X_0x15",
    "ORA_ABSOLUTE_0x0D",
    "ORA_ABSOLUTE_X_0x1D",
    "ORA_ABSOLUTE_Y_0x19",
    "ORA_INDEXED_INDIRECT_X_0x01",
    "ORA_INDIRECT_INDEXED_Y_0x11",
    "register_ora_instructions",
]
