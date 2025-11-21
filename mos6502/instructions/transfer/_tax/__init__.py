#!/usr/bin/env python3
"""TAX (Transfer Accumulator to Index X) instruction."""
from mos6502 import flags
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#TAX
# Transfer Accumulator to Index X
#
# A -> X
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	TAX	AA	1	2
TAX_IMPLIED_0xAA = InstructionOpcode(
    0xAA,
    "mos6502.instructions.transfer._tax",
    "tax_implied_0xaa"
)


def add_tax_to_instruction_set_enum(instruction_set_class) -> None:
    """Add TAX instruction to the InstructionSet enum dynamically."""
    # Create a pseudo-enum member that has a .name attribute
    # We can't create a true enum member after class definition, but we can
    # create an object that behaves like one for lookup purposes
    class PseudoEnumMember(int):
        def __new__(cls, value, name) -> "InstructionSet":
            obj = int.__new__(cls, value)
            obj._name = name
            obj._value_ = value
            return obj

        @property
        def name(self) -> str:
            return self._name

        @property
        def value(self) -> int:
            return self._value_

    tax_member = PseudoEnumMember(TAX_IMPLIED_0xAA, "TAX_IMPLIED_0xAA")
    instruction_set_class._value2member_map_[TAX_IMPLIED_0xAA] = tax_member
    setattr(instruction_set_class, "TAX_IMPLIED_0xAA", TAX_IMPLIED_0xAA)


def register_tax_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register TAX instruction in the InstructionSet."""
    # Add to enum
    add_tax_to_instruction_set_enum(instruction_set_class)

    # Add to map
    tax_implied_0xaa_can_modify_flags: Byte = Byte()
    tax_implied_0xaa_can_modify_flags[flags.N] = True
    tax_implied_0xaa_can_modify_flags[flags.Z] = True
    instruction_map[TAX_IMPLIED_0xAA] = {
        "addressing": "implied",
        "assembler": "TAX",
        "opc": TAX_IMPLIED_0xAA,
        "bytes": "1",
        "cycles": "2",
        "flags": tax_implied_0xaa_can_modify_flags,
    }


__all__ = ["TAX_IMPLIED_0xAA", "register_tax_instructions"]
