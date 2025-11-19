#!/usr/bin/env python3
"""PHP (Push Processor Status on Stack) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#PHP
# Push Processor Status on Stack
#
# The status register will be pushed with the break
# flag and bit 5 set to 1.
#
# push SR
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	PHP	08	1	3
PHP_IMPLIED_0x08: Literal[8] = 0x08


def add_php_to_instruction_set_enum(instruction_set_class) -> None:
    """Add PHP instruction to the InstructionSet enum dynamically."""
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

    php_member = PseudoEnumMember(PHP_IMPLIED_0x08, 'PHP_IMPLIED_0x08')
    instruction_set_class._value2member_map_[PHP_IMPLIED_0x08] = php_member
    setattr(instruction_set_class, 'PHP_IMPLIED_0x08', PHP_IMPLIED_0x08)


def register_php_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register PHP instruction in the InstructionSet.

    Note: PHP doesn't have a map entry because it's handled as a special case
    in core.py execute() method.
    """
    # Add to enum
    add_php_to_instruction_set_enum(instruction_set_class)


__all__ = ['PHP_IMPLIED_0x08', 'register_php_instructions']
