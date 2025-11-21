#!/usr/bin/env python3
"""CLI (Clear Interrupt Disable Bit) instruction."""
from mos6502 import flags
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#CLI
# Clear Interrupt Disable Bit
#
# 0 -> I
# N	Z	C	I	D	V
# -	-	-	0	-	-
# addressing	assembler	opc	bytes	cycles
# implied	CLI	58	1	2
CLI_IMPLIED_0x58 = InstructionOpcode(
    0x58,
    "mos6502.instructions.flags._cli",
    "cli_implied_0x58"
)


def add_cli_to_instruction_set_enum(instruction_set_class) -> None:
    """Add CLI instruction to the InstructionSet enum dynamically."""
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

    cli_member = PseudoEnumMember(CLI_IMPLIED_0x58, "CLI_IMPLIED_0x58")
    instruction_set_class._value2member_map_[CLI_IMPLIED_0x58] = cli_member
    setattr(instruction_set_class, "CLI_IMPLIED_0x58", CLI_IMPLIED_0x58)


def register_cli_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register CLI instruction in the InstructionSet."""
    # Add to enum
    add_cli_to_instruction_set_enum(instruction_set_class)

    # Add to map
    cli_implied_0x58_can_modify_flags: Byte = Byte()
    cli_implied_0x58_can_modify_flags[flags.I] = True
    instruction_map[CLI_IMPLIED_0x58] = {
        "addressing": "implied",
        "assembler": "CLI",
        "opc": CLI_IMPLIED_0x58,
        "bytes": "1",
        "cycles": "2",
        "flags": cli_implied_0x58_can_modify_flags,
    }


__all__ = ["CLI_IMPLIED_0x58", "register_cli_instructions"]
