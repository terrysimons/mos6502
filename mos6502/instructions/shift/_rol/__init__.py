#!/usr/bin/env python3
"""ROL (Rotate Left) instruction."""
from mos6502.instructions import InstructionOpcode

# https://masswerk.at/6502/6502_instruction_set.html#ROL
# Rotate Left
#
# Rotate One Bit Left (Memory or Accumulator)
# C <- [76543210] <- C
#
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# accumulator	ROL A	2A	1	2
# zeropage	ROL oper	26	2	5
# zeropage,X	ROL oper,X	36	2	6
# absolute	ROL oper	2E	3	6
# absolute,X	ROL oper,X	3E	3	7

ROL_ACCUMULATOR_0x2A = InstructionOpcode(
    0x2A,
    "mos6502.instructions.shift._rol",
    "rol_accumulator_0x2a"
)

ROL_ZEROPAGE_0x26 = InstructionOpcode(
    0x26,
    "mos6502.instructions.shift._rol",
    "rol_zeropage_0x26"
)

ROL_ZEROPAGE_X_0x36 = InstructionOpcode(
    0x36,
    "mos6502.instructions.shift._rol",
    "rol_zeropage_x_0x36"
)

ROL_ABSOLUTE_0x2E = InstructionOpcode(
    0x2E,
    "mos6502.instructions.shift._rol",
    "rol_absolute_0x2e"
)

ROL_ABSOLUTE_X_0x3E = InstructionOpcode(
    0x3E,
    "mos6502.instructions.shift._rol",
    "rol_absolute_x_0x3e"
)


def add_rol_to_instruction_set_enum(instruction_set_class) -> None:
    """Add ROL instructions to the InstructionSet enum dynamically."""
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
        (ROL_ACCUMULATOR_0x2A, "ROL_ACCUMULATOR_0x2A"),
        (ROL_ZEROPAGE_0x26, "ROL_ZEROPAGE_0x26"),
        (ROL_ZEROPAGE_X_0x36, "ROL_ZEROPAGE_X_0x36"),
        (ROL_ABSOLUTE_0x2E, "ROL_ABSOLUTE_0x2E"),
        (ROL_ABSOLUTE_X_0x3E, "ROL_ABSOLUTE_X_0x3E"),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_rol_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register ROL instructions in the InstructionSet."""
    add_rol_to_instruction_set_enum(instruction_set_class)

    from mos6502.memory import Byte
    from mos6502 import flags
    rol_can_modify_flags: Byte = Byte()
    rol_can_modify_flags[flags.N] = 1
    rol_can_modify_flags[flags.Z] = 1
    rol_can_modify_flags[flags.C] = 1

    instruction_map[ROL_ACCUMULATOR_0x2A] = {
        "addressing": "accumulator",
        "assembler": "ROL A",
        "opc": ROL_ACCUMULATOR_0x2A,
        "bytes": "1",
        "cycles": "2",
        "flags": rol_can_modify_flags,
    }

    instruction_map[ROL_ZEROPAGE_0x26] = {
        "addressing": "zeropage",
        "assembler": "ROL {oper}",
        "opc": ROL_ZEROPAGE_0x26,
        "bytes": "2",
        "cycles": "5",
        "flags": rol_can_modify_flags,
    }

    instruction_map[ROL_ZEROPAGE_X_0x36] = {
        "addressing": "zeropage,X",
        "assembler": "ROL {oper},X",
        "opc": ROL_ZEROPAGE_X_0x36,
        "bytes": "2",
        "cycles": "6",
        "flags": rol_can_modify_flags,
    }

    instruction_map[ROL_ABSOLUTE_0x2E] = {
        "addressing": "absolute",
        "assembler": "ROL {oper}",
        "opc": ROL_ABSOLUTE_0x2E,
        "bytes": "3",
        "cycles": "6",
        "flags": rol_can_modify_flags,
    }

    instruction_map[ROL_ABSOLUTE_X_0x3E] = {
        "addressing": "absolute,X",
        "assembler": "ROL {oper},X",
        "opc": ROL_ABSOLUTE_X_0x3E,
        "bytes": "3",
        "cycles": "7",
        "flags": rol_can_modify_flags,
    }


__all__ = [
    "ROL_ACCUMULATOR_0x2A",
    "ROL_ZEROPAGE_0x26",
    "ROL_ZEROPAGE_X_0x36",
    "ROL_ABSOLUTE_0x2E",
    "ROL_ABSOLUTE_X_0x3E",
    "register_rol_instructions",
]
