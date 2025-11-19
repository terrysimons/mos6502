#!/usr/bin/env python3
"""NOP (No Operation) instruction."""
from typing import Literal

from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#NOP
# No Operation
#
# ---
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	NOP	EA	1	2
NOP_IMPLIED_0xEA: Literal[234] = 0xEA


def add_nop_to_instruction_set_enum(instruction_set_class) -> None:
    """Add NOP instruction to the InstructionSet enum dynamically."""
    # Add NOP as enum member
    instruction_set_class._value2member_map_[NOP_IMPLIED_0xEA] = NOP_IMPLIED_0xEA
    setattr(instruction_set_class, 'NOP_IMPLIED_0xEA', NOP_IMPLIED_0xEA)


def register_nop_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register NOP instruction in the InstructionSet map."""
    # Add to enum
    add_nop_to_instruction_set_enum(instruction_set_class)

    # Add to map
    nop_implied_0xea_can_modify_flags: Byte = Byte()
    instruction_map[NOP_IMPLIED_0xEA] = {
        "addressing": "implied",
        "assembler": "NOP",
        "opc": NOP_IMPLIED_0xEA,
        "bytes": "1",
        "cycles": "2",
        "flags": nop_implied_0xea_can_modify_flags,
    }


__all__ = ['NOP_IMPLIED_0xEA', 'register_nop_instructions']
