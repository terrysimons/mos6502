#!/usr/bin/env python3
"""PHP (Push Processor Status on Stack) instruction."""
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#PHP
# Push Processor Status on Stack
#
# push P
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	PHP	08	1	3
PHP_IMPLIED_0x08 = InstructionOpcode(
    0x08,
    "mos6502.instructions.stack._php",
    "php_implied_0x08"
)


def add_php_to_instruction_set_enum(instruction_set_class) -> None:
    """Add PHP instruction to the InstructionSet enum dynamically."""
    class PseudoEnumMember:
        """MicroPython-compatible pseudo-enum member."""
        __slots__ = ('_value_', '_name')

        def __init__(self, value, name):
            self._value_ = int(value)
            self._name = name

        @property
        def name(self):
            return self._name

        @property
        def value(self):
            return self._value_

        def __int__(self):
            return self._value_

        def __eq__(self, other):
            if isinstance(other, int):
                return self._value_ == other
            return NotImplemented

        def __hash__(self):
            return hash(self._value_)

    php_member = PseudoEnumMember(PHP_IMPLIED_0x08, "PHP_IMPLIED_0x08")
    instruction_set_class._value2member_map_[PHP_IMPLIED_0x08] = php_member
    setattr(instruction_set_class, "PHP_IMPLIED_0x08", PHP_IMPLIED_0x08)


def register_php_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register PHP instruction in the InstructionSet."""
    add_php_to_instruction_set_enum(instruction_set_class)

    # PHP doesn't modify any flags
    php_implied_0x08_can_modify_flags: Byte = Byte()
    instruction_map[PHP_IMPLIED_0x08] = {
        "addressing": "implied",
        "assembler": "PHP",
        "opc": PHP_IMPLIED_0x08,
        "bytes": "1",
        "cycles": "3",
        "flags": php_implied_0x08_can_modify_flags,
    }


__all__ = ["PHP_IMPLIED_0x08", "register_php_instructions"]
