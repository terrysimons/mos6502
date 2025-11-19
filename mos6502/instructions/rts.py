#!/usr/bin/env python3
"""RTS (Return from Subroutine) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#RTS
# Return from Subroutine
#
# pull PC, PC+1 -> PC
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	RTS	60	1	6
RTS_IMPLIED_0x60: Literal[96] = 0x60


def add_rts_to_instruction_set_enum(instruction_set_class) -> None:
    """Add RTS instruction to the InstructionSet enum dynamically."""
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

    rts_member = PseudoEnumMember(RTS_IMPLIED_0x60, 'RTS_IMPLIED_0x60')
    instruction_set_class._value2member_map_[RTS_IMPLIED_0x60] = rts_member
    setattr(instruction_set_class, 'RTS_IMPLIED_0x60', RTS_IMPLIED_0x60)


def register_rts_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register RTS instruction in the InstructionSet.

    Note: RTS doesn't have a map entry because it's handled as a special case
    in core.py execute() method.
    """
    # Add to enum
    add_rts_to_instruction_set_enum(instruction_set_class)


__all__ = ['RTS_IMPLIED_0x60', 'register_rts_instructions']
