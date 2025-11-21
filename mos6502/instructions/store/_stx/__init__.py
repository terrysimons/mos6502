#!/usr/bin/env python3
"""STX (Store X Register) instruction."""
from mos6502.instructions import InstructionOpcode

# https://masswerk.at/6502/6502_instruction_set.html#STX
# Store X Register in Memory
#
# X -> M
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# zeropage	STX oper	86	2	3
# zeropage,Y	STX oper,Y	96	2	4
# absolute	STX oper	8E	3	4

STX_ZEROPAGE_0x86 = InstructionOpcode(
    0x86,
    "mos6502.instructions.store._stx",
    "stx_zeropage_0x86"
)

STX_ZEROPAGE_Y_0x96 = InstructionOpcode(
    0x96,
    "mos6502.instructions.store._stx",
    "stx_zeropage_y_0x96"
)

STX_ABSOLUTE_0x8E = InstructionOpcode(
    0x8E,
    "mos6502.instructions.store._stx",
    "stx_absolute_0x8e"
)


def add_stx_to_instruction_set_enum(instruction_set_class) -> None:
    """Add STX instructions to the InstructionSet enum dynamically."""
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
        (STX_ZEROPAGE_0x86, "STX_ZEROPAGE_0x86"),
        (STX_ZEROPAGE_Y_0x96, "STX_ZEROPAGE_Y_0x96"),
        (STX_ABSOLUTE_0x8E, "STX_ABSOLUTE_0x8E"),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_stx_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register STX instructions in the InstructionSet."""
    add_stx_to_instruction_set_enum(instruction_set_class)

    from mos6502.memory import Byte
    stx_can_modify_flags: Byte = Byte()
    # STX doesn't modify any flags

    instruction_map[STX_ZEROPAGE_0x86] = {
        "addressing": "zeropage",
        "assembler": "STX {oper}",
        "opc": STX_ZEROPAGE_0x86,
        "bytes": "2",
        "cycles": "3",
        "flags": stx_can_modify_flags,
    }

    instruction_map[STX_ZEROPAGE_Y_0x96] = {
        "addressing": "zeropage,Y",
        "assembler": "STX {oper},Y",
        "opc": STX_ZEROPAGE_Y_0x96,
        "bytes": "2",
        "cycles": "4",
        "flags": stx_can_modify_flags,
    }

    instruction_map[STX_ABSOLUTE_0x8E] = {
        "addressing": "absolute",
        "assembler": "STX {oper}",
        "opc": STX_ABSOLUTE_0x8E,
        "bytes": "3",
        "cycles": "4",
        "flags": stx_can_modify_flags,
    }


__all__ = [
    "STX_ZEROPAGE_0x86",
    "STX_ZEROPAGE_Y_0x96",
    "STX_ABSOLUTE_0x8E",
    "register_stx_instructions",
]
