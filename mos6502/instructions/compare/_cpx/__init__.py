#!/usr/bin/env python3
"""CPX (Compare X Register) instruction."""
from mos6502.instructions import InstructionOpcode

# https://masswerk.at/6502/6502_instruction_set.html#CPX
# Compare X Register with Memory
#
# X - M (affects flags only, doesn't store result)
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	CPX #oper	E0	2	2
# zeropage	CPX oper	E4	2	3
# absolute	CPX oper	EC	3	4

CPX_IMMEDIATE_0xE0 = InstructionOpcode(
    0xE0,
    "mos6502.instructions.compare._cpx",
    "cpx_immediate_0xe0"
)

CPX_ZEROPAGE_0xE4 = InstructionOpcode(
    0xE4,
    "mos6502.instructions.compare._cpx",
    "cpx_zeropage_0xe4"
)

CPX_ABSOLUTE_0xEC = InstructionOpcode(
    0xEC,
    "mos6502.instructions.compare._cpx",
    "cpx_absolute_0xec"
)


def add_cpx_to_instruction_set_enum(instruction_set_class) -> None:
    """Add CPX instructions to the InstructionSet enum dynamically."""
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
        (CPX_IMMEDIATE_0xE0, 'CPX_IMMEDIATE_0xE0'),
        (CPX_ZEROPAGE_0xE4, 'CPX_ZEROPAGE_0xE4'),
        (CPX_ABSOLUTE_0xEC, 'CPX_ABSOLUTE_0xEC'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_cpx_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register CPX instructions in the InstructionSet."""
    add_cpx_to_instruction_set_enum(instruction_set_class)

    from mos6502.memory import Byte
    from mos6502 import flags
    cpx_can_modify_flags: Byte = Byte()
    cpx_can_modify_flags[flags.N] = 1
    cpx_can_modify_flags[flags.Z] = 1
    cpx_can_modify_flags[flags.C] = 1

    instruction_map[CPX_IMMEDIATE_0xE0] = {
        "addressing": "immediate",
        "assembler": "CPX #{oper}",
        "opc": CPX_IMMEDIATE_0xE0,
        "bytes": "2",
        "cycles": "2",
        "flags": cpx_can_modify_flags,
    }

    instruction_map[CPX_ZEROPAGE_0xE4] = {
        "addressing": "zeropage",
        "assembler": "CPX {oper}",
        "opc": CPX_ZEROPAGE_0xE4,
        "bytes": "2",
        "cycles": "3",
        "flags": cpx_can_modify_flags,
    }

    instruction_map[CPX_ABSOLUTE_0xEC] = {
        "addressing": "absolute",
        "assembler": "CPX {oper}",
        "opc": CPX_ABSOLUTE_0xEC,
        "bytes": "3",
        "cycles": "4",
        "flags": cpx_can_modify_flags,
    }


__all__ = [
    'CPX_IMMEDIATE_0xE0',
    'CPX_ZEROPAGE_0xE4',
    'CPX_ABSOLUTE_0xEC',
    'register_cpx_instructions',
]
