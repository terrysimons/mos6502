#!/usr/bin/env python3
"""TXS (Transfer Index X to Stack Register) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#TXS
# Transfer Index X to Stack Register
#
# X -> S
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	TXS	9A	1	2
TXS_IMPLIED_0x9A: Literal[154] = 0x9A


def add_txs_to_instruction_set_enum(instruction_set_class) -> None:
    """Add TXS instruction to the InstructionSet enum dynamically."""
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

    txs_member = PseudoEnumMember(TXS_IMPLIED_0x9A, 'TXS_IMPLIED_0x9A')
    instruction_set_class._value2member_map_[TXS_IMPLIED_0x9A] = txs_member
    setattr(instruction_set_class, 'TXS_IMPLIED_0x9A', TXS_IMPLIED_0x9A)


def register_txs_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register TXS instruction in the InstructionSet.

    Note: TXS doesn't have a map entry because it's handled as a special case
    in core.py execute() method.
    """
    add_txs_to_instruction_set_enum(instruction_set_class)


__all__ = ['TXS_IMPLIED_0x9A', 'register_txs_instructions']
